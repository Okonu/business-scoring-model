"""HTTP API"""

from fastapi.testclient import TestClient

from health_score.api.app import create_app
from health_score.service import ScoringService
from health_score.settings import Settings
from tests.conftest import FakeClient

BODY = {"company_code": "TEST-000001", "pin": "1234", "as_of_date": "2026-09-26"}


def client_for(lists, **settings):
    s = Settings(**settings)
    service = ScoringService(s, client_factory=lambda **_: FakeClient(lists))
    return TestClient(create_app(s, service))


def test_health(business_lists):
    r = client_for(business_lists).get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_score_returns_everything_the_page_shows(business_lists):
    r = client_for(business_lists).post("/v1/scores", json=BODY)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "scored" and body["band"]
    assert set(body["dimensions"]) == {"sales", "cash", "profit", "customers", "operations", "formality"}
    assert body["measures"] and body["shops"] and body["data_coverage"]
    assert "1234" not in r.text


def test_wrong_pin_returns_401(business_lists):
    r = client_for(business_lists).post("/v1/scores", json={**BODY, "pin": "0000"})
    assert r.status_code == 401


def test_invalid_request_returns_422(business_lists):
    r = client_for(business_lists).post("/v1/scores", json={"company_code": "X"})
    assert r.status_code == 422


def test_api_key_enforced_when_configured(business_lists):
    client = client_for(business_lists, api_keys="secret-key")
    assert client.post("/v1/scores", json=BODY).status_code == 401
    assert client.post("/v1/scores", json=BODY, headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.post("/v1/scores", json=BODY, headers={"X-API-Key": "secret-key"}).status_code == 200
