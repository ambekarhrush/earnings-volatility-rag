import copy
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from pydantic_ai.models.test import TestModel

from app.agent import generate_opinion, validate_citations
from app.desk_models import DeskRequest, Opinion
from app.main import app
from app.market import DataUnavailable, parse_chain
from app.research import research_pack
from app.risk import price, solve_iv

client = TestClient(app)
NOW = datetime(2026, 10, 1, 16, tzinfo=UTC)


@pytest.fixture
def desk_request():
    return DeskRequest(event_date="2026-10-29", expiration="2026-10-30")


@pytest.fixture
def chain():
    return {
        "s": "ok",
        "optionSymbol": ["AAPL261030C00100000", "AAPL261030P00100000"],
        "side": ["call", "put"],
        "strike": [100, 100],
        "bid": [4.1, 3.7],
        "ask": [4.3, 3.9],
        "updated": [NOW.timestamp() - 86400] * 2,
        "underlyingPrice": [100, 100],
        "volume": [10, 12],
        "openInterest": [500, 600],
    }


def test_actual_provider_response_is_delayed_not_live(chain, desk_request):
    snapshot = parse_chain(chain, desk_request, NOW)
    assert snapshot.feed == "delayed"
    assert snapshot.spot_time == NOW - timedelta(days=1)
    assert snapshot.call.symbol == "AAPL261030C00100000"


@pytest.mark.parametrize(
    "field,values",
    [
        ("ask", [3.9, 3.9]),
        ("bid", [0, 3.7]),
        ("updated", [NOW.timestamp() + 600] * 2),
        ("underlyingPrice", [100, 102]),
        ("updated", [NOW.timestamp(), NOW.timestamp() - 1000]),
        ("optionSymbol", ["AAPL1261030C00100000", "AAPL1261030P00100000"]),
    ],
)
def test_invalid_market_observations_rejected(chain, desk_request, field, values):
    chain[field] = values
    with pytest.raises(DataUnavailable):
        parse_chain(chain, desk_request, NOW)


def test_stale_quote_flag(chain, desk_request):
    chain["updated"] = [NOW.timestamp() - 4 * 86400] * 2
    assert parse_chain(chain, desk_request, NOW).stale


def test_after_close_expiry_must_follow_event():
    with pytest.raises(ValidationError):
        DeskRequest(event_date="2026-10-30", expiration="2026-10-30")


def test_iv_solver_recovers_known_volatility():
    for kind in ("call", "put"):
        premium = price(100, 102, 0.1, 0.04, 0.38, kind, 0.01)
        assert solve_iv(premium, 100, 102, 0.1, 0.04, kind, 0.01) == pytest.approx(0.38)


def test_iv_solver_rejects_impossible_price():
    with pytest.raises(ValueError):
        solve_iv(200, 100, 100, 0.1, 0.04, "call")


def test_initial_is_real_evidence_and_hypothetical_prices(monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("No model call on page load")

    monkeypatch.setattr("app.desk.generate_opinion", no_network)
    response = client.get("/api/desk/initial")
    assert response.status_code == 200
    brief = response.json()
    assert brief["market"]["feed"] == "hypothetical"
    assert all("apple.com" in item["url"] for item in brief["evidence"])
    assert brief["analytics"]["max_loss"] == pytest.approx(821.30)
    assert min(row["expiry_pnl"] for row in brief["analytics"]["curve"]) >= -821.30
    assert brief["experiment"]["status"] == "not_run"


def test_missing_key_never_substitutes_demo_quotes(monkeypatch):
    monkeypatch.delenv("MARKETDATA_TOKEN", raising=False)
    request = client.get("/api/desk/initial").json()["request"]
    request["mode"] = "marketdata"
    response = client.post("/api/desk/brief", json=request)
    assert response.status_code == 503
    assert "MARKETDATA_TOKEN" in response.json()["detail"]


def test_other_ticker_never_inherits_apple_thesis():
    request = client.get("/api/desk/initial").json()["request"]
    request["ticker"] = "MSFT"
    brief = client.post("/api/desk/brief", json=request).json()
    assert brief["evidence"] == []
    assert brief["opinion"]["stance"] == "insufficient_data"
    assert brief["fundamentals"] == []


def test_document_enters_frozen_pack_and_export():
    response = client.post(
        "/api/desk/documents",
        data={"published": "2026-01-01"},
        files={
            "file": (
                "research.md",
                b"Revenue may slow. Source: analyst assumption.",
                "text/markdown",
            )
        },
    )
    assert response.status_code == 200
    document = response.json()
    initial = client.get("/api/desk/initial").json()
    request = initial["request"]
    request["document_ids"] = [document["id"]]
    brief = client.post("/api/desk/brief", json=request).json()
    assert brief["experiment"]["evidence_hash"] != initial["experiment"]["evidence_hash"]
    assert document in brief["evidence"]
    assert client.get(f"/api/desk/snapshots/{brief['id']}").json() == brief


def test_future_document_rejected():
    response = client.post(
        "/api/desk/documents",
        data={"published": "2099-01-01"},
        files={"file": ("future.txt", b"Future claims", "text/plain")},
    )
    request = client.get("/api/desk/initial").json()["request"]
    request["document_ids"] = [response.json()["id"]]
    assert client.post("/api/desk/brief", json=request).status_code == 422


def test_unknown_citations_rejected():
    opinion = research_pack("AAPL").editorial.model_copy(deep=True)
    opinion.rationale[0].evidence_ids = ["FABRICATED-SOURCE"]
    with pytest.raises(ValueError):
        validate_citations(opinion, {"AAPL-Q3-MARGIN"})


def test_pydantic_ai_structured_output_with_test_model():
    research = research_pack("AAPL")
    pack = {"evidence": [e.model_dump(mode="json") for e in research.evidence]}
    result = generate_opinion(
        pack, test_model=TestModel(custom_output_args=research.editorial.model_dump())
    )
    assert Opinion.model_validate(result["opinion"]) == research.editorial
    assert result["latency_seconds"] >= 0


def test_pydantic_ai_retries_then_rejects_invalid_citations():
    opinion = copy.deepcopy(research_pack("AAPL").editorial.model_dump())
    opinion["rationale"][0]["evidence_ids"] = ["UNSEEN"]
    with pytest.raises(DataUnavailable):
        generate_opinion({"evidence": []}, test_model=TestModel(custom_output_args=opinion))
