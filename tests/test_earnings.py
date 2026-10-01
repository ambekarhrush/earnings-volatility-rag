from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient

from app import earnings
from app.earnings import (
    EarningsEvent,
    EarningsProfile,
    EarningsResult,
    get_earnings_profile,
    parse_calendar,
    parse_history,
)
from app.main import app
from app.market import DataUnavailable

client = TestClient(app)

SAMPLE_CALENDAR_CSV = """symbol,name,reportDate,fiscalDateEnding,estimate,currency,timeOfTheDay
AAPL,Apple Inc,2026-07-30,2026-06-30,1.40,USD,after close
AAPL,Apple Inc,2026-10-29,2026-09-30,1.55,USD,after close
AAPL,Apple Inc,2027-01-28,2026-12-31,2.10,USD,after close
MSFT,Microsoft Corp,2026-10-22,2026-09-30,3.10,USD,after close
"""

SAMPLE_HISTORY_JSON = {
    "symbol": "AAPL",
    "annualEarnings": [],
    "quarterlyEarnings": [
        {
            "fiscalDateEnding": "2026-06-30",
            "reportedDate": "2026-07-30",
            "reportedEPS": "1.40",
            "estimatedEPS": "1.35",
            "surprise": "0.05",
            "surprisePercentage": "3.7037",
        },
        {
            "fiscalDateEnding": "2026-03-31",
            "reportedDate": "2026-05-02",
            "reportedEPS": "1.53",
            "estimatedEPS": "1.50",
            "surprise": "0.03",
            "surprisePercentage": "2.0",
        },
    ],
}


def test_parse_calendar_picks_nearest_future_date():
    today = date(2026, 8, 1)
    event = parse_calendar(SAMPLE_CALENDAR_CSV, "AAPL", today=today)
    assert event is not None
    assert event.symbol == "AAPL"
    assert event.report_date == date(2026, 10, 29)
    assert event.estimate == 1.55
    assert event.currency == "USD"
    assert event.session == "after close"


def test_parse_calendar_no_upcoming_returns_none():
    today = date(2028, 1, 1)
    event = parse_calendar(SAMPLE_CALENDAR_CSV, "AAPL", today=today)
    assert event is None


def test_parse_calendar_unknown_symbol_returns_none():
    today = date(2026, 8, 1)
    assert parse_calendar(SAMPLE_CALENDAR_CSV, "NVDA", today=today) is None


def test_parse_history_extracts_quarterly_records():
    results = parse_history(SAMPLE_HISTORY_JSON, "AAPL")
    assert len(results) == 2
    assert results[0].fiscal_date_ending == date(2026, 6, 30)
    assert results[0].reported_date == date(2026, 7, 30)
    assert results[0].reported_eps == 1.40
    assert results[0].estimated_eps == 1.35
    assert results[0].surprise == 0.05
    assert results[0].surprise_percentage == pytest.approx(3.7037)


def test_parse_history_mismatched_symbol_raises():
    with pytest.raises(DataUnavailable, match="did not match"):
        parse_history(SAMPLE_HISTORY_JSON, "MSFT")


def test_missing_api_key_raises_unavailable(monkeypatch):
    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
    with earnings._lock:
        earnings._cache.clear()
    with pytest.raises(DataUnavailable, match="Add ALPHA_VANTAGE_API_KEY"):
        get_earnings_profile("AAPL")


def test_get_earnings_profile_success_and_cache(monkeypatch):
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "test-av-key")
    with earnings._lock:
        earnings._cache.clear()

    calls = []

    def mock_get(_client, url, **kwargs):
        params = kwargs.get("params", {})
        calls.append(params.get("function"))
        if params.get("function") == "EARNINGS_CALENDAR":
            return httpx.Response(200, text=SAMPLE_CALENDAR_CSV, request=httpx.Request("GET", url))
        if params.get("function") == "EARNINGS":
            return httpx.Response(200, json=SAMPLE_HISTORY_JSON, request=httpx.Request("GET", url))
        return httpx.Response(404, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.Client, "get", mock_get)

    profile = get_earnings_profile("AAPL")
    assert profile.symbol == "AAPL"
    assert profile.provider == "Alpha Vantage"
    assert profile.next_event is not None
    assert len(profile.history) == 2
    assert len(calls) == 2

    # Second call should hit the in-memory cache
    cached = get_earnings_profile("AAPL")
    assert cached.symbol == "AAPL"
    assert len(calls) == 2  # No extra HTTP calls made


@pytest.mark.parametrize("status_code", [401, 403, 429])
def test_provider_http_errors_raise_unavailable(monkeypatch, status_code):
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "test-av-key")
    with earnings._lock:
        earnings._cache.clear()

    def mock_get(_client, url, **kwargs):
        return httpx.Response(status_code, text="Error", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.Client, "get", mock_get)
    with pytest.raises(DataUnavailable):
        get_earnings_profile("AAPL")


def test_provider_rate_limit_note_raises_unavailable(monkeypatch):
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "test-av-key")
    with earnings._lock:
        earnings._cache.clear()

    def mock_get(_client, url, **kwargs):
        return httpx.Response(
            200,
            json={
                "Note": "Thank you for using Alpha Vantage! Our standard API call frequency is 5 calls per minute."
            },
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx.Client, "get", mock_get)
    with pytest.raises(DataUnavailable, match="Alpha Vantage: Thank you"):
        get_earnings_profile("AAPL")


def test_api_status_reports_earnings_flag(monkeypatch):
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "mock-key")
    status = client.get("/api/desk/status").json()
    assert status["earnings"] is True

    monkeypatch.delenv("ALPHA_VANTAGE_API_KEY", raising=False)
    status_off = client.get("/api/desk/status").json()
    assert status_off["earnings"] is False


def test_api_earnings_endpoint_validation_and_fetch(monkeypatch):
    assert client.get("/api/desk/earnings/TOOLONGTICKERNAME").status_code == 422
    assert client.get("/api/desk/earnings/123BAD").status_code == 422

    dummy_profile = EarningsProfile(
        symbol="AAPL",
        fetched_at="2026-10-01",
        next_event=EarningsEvent(
            symbol="AAPL",
            name="Apple Inc",
            report_date=date(2026, 10, 29),
            estimate=1.55,
        ),
        history=[
            EarningsResult(
                fiscal_date_ending=date(2026, 6, 30),
                reported_date=date(2026, 7, 30),
                reported_eps=1.40,
                estimated_eps=1.35,
                surprise=0.05,
                surprise_percentage=3.7,
            )
        ],
        note="Test note",
    )
    monkeypatch.setattr("app.desk.get_earnings_profile", lambda _sym: dummy_profile)

    res = client.get("/api/desk/earnings/AAPL")
    assert res.status_code == 200
    data = res.json()
    assert data["symbol"] == "AAPL"
    assert data["next_event"]["report_date"] == "2026-10-29"

    # Brief incorporates the profile
    req = client.get("/api/desk/initial").json()["request"]
    req["event_date"] = "2026-10-29"
    req["expiration"] = "2026-10-30"
    brief = client.post("/api/desk/brief", json=req).json()
    assert "earnings" in brief
    assert brief["event_note"] == "Alpha Vantage calendar date; verify with issuer IR."
