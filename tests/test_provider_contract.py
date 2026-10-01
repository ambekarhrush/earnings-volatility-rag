from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app import market
from app.desk_models import DeskRequest
from app.market import DataUnavailable


@pytest.fixture
def provider_request(monkeypatch):
    monkeypatch.setenv("MARKETDATA_TOKEN", "test-token-not-a-secret")
    market._cache.clear()
    return DeskRequest(mode="marketdata", event_date="2026-10-29", expiration="2026-10-30")


def test_provider_request_budget_and_original_fetch_time(monkeypatch, provider_request):
    now = datetime(2026, 10, 1, 16, tzinfo=UTC)
    payload = {
        "s": "ok",
        "optionSymbol": ["AAPL261030C00100000", "AAPL261030P00100000"],
        "side": ["call", "put"],
        "strike": [100, 100],
        "bid": [4.1, 3.7],
        "ask": [4.3, 3.9],
        "updated": [now.timestamp() - 86400] * 2,
        "underlyingPrice": [100, 100],
    }
    requests = []

    def send(_client, url, **kwargs):
        requests.append(kwargs)
        assert url == "https://api.marketdata.app/v1/options/chain/AAPL/"
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.Client, "get", send)
    first = market.get_snapshot(provider_request, now)
    second = market.get_snapshot(provider_request, now + timedelta(minutes=5))
    assert len(requests) == 1
    assert requests[0]["params"] == {"expiration": "2026-10-30", "strikeLimit": 1}
    assert first.fetched_at == second.fetched_at == now
    assert first.call.quote_time == second.call.quote_time


@pytest.mark.parametrize("code", [401, 403, 429, 500])
def test_provider_errors_are_not_prices(monkeypatch, provider_request, code):
    def send(_client, url, **kwargs):
        return httpx.Response(code, json={"s": "error"}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.Client, "get", send)
    with pytest.raises(DataUnavailable):
        market.get_snapshot(provider_request, datetime(2026, 10, 1, 16, tzinfo=UTC))
    assert market._cache == {}
