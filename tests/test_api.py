from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_brief_is_auditable():
    response = client.get("/api/brief/ACME")
    assert response.status_code == 200
    data = response.json()
    assert data["implied_move_pct"] == 8.0
    assert data["synthesis_mode"] == "deterministic"
    assert len(data["case"]["evidence"]) == 3
    assert len(data["limitations"]) >= 3


def test_unknown_case_is_404():
    assert client.get("/api/brief/UNKNOWN").status_code == 404
