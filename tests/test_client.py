"""BASEPOINT client login handling, with the HTTP session replaced"""

import pytest
import requests

from health_score.basepoint import AuthenticationError, BasepointUnavailableError, FSSClient

TENANT_RAW = {
    "_id": "t1",
    "name": "Test Business",
    "tenant_code": "TEST-000001",
    "db_host": "secret-host",
    "db_password": "secret-password",
    "modules": {"pos": True, "accounting": False},
    "accounting_settings": {"base_currency": "KES"},
}


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body

    def json(self):
        if self._body is None:
            raise ValueError("no JSON")
        return self._body


def client_with(responses):
    """A client whose POSTs return the given responses in order"""
    client = FSSClient(base_url="https://example.invalid")
    queue = list(responses)

    def post(url, **kwargs):
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    client.session.post = post
    return client


def test_login_keeps_only_whitelisted_tenant_fields():
    client = client_with(
        [
            FakeResponse(200, {"data": {"success": True, "data": TENANT_RAW}}),
            FakeResponse(200, {"Token": "tok", "name": "admin", "role": "admin", "isAdmin": True}),
        ]
    )
    tenant, user = client.login("TEST-000001", "1234")
    assert tenant["tenant_code"] == "TEST-000001"
    assert tenant["modules"] == {"pos": True, "accounting": False}
    assert "db_host" not in tenant and "db_password" not in tenant
    assert "secret" not in str(tenant)
    assert user == {"name": "admin", "role": "admin", "is_admin": True}
    assert client.session.headers["Authorization"] == "Bearer tok"


def test_unknown_company_code_is_an_authentication_error():
    # BASEPOINT answers an unknown code with HTTP 500 wrapping a 404
    client = client_with([FakeResponse(500, {"error": "Failed to verify tenant: Request failed with status code 404"})])
    with pytest.raises(AuthenticationError, match="Company code"):
        client.login("NOPE-999999", "1234")


def test_wrong_pin_is_an_authentication_error():
    client = client_with(
        [
            FakeResponse(200, {"data": {"success": True, "data": TENANT_RAW}}),
            FakeResponse(401, {"message": "Invalid PIN"}),
        ]
    )
    with pytest.raises(AuthenticationError, match="Login failed"):
        client.login("TEST-000001", "0000")


@pytest.mark.parametrize(
    "response",
    [FakeResponse(502, None), FakeResponse(500, {"error": "database down"}), requests.ConnectionError("down")],
)
def test_outage_is_unavailable(response):
    client = client_with([response])
    with pytest.raises(BasepointUnavailableError):
        client.login("TEST-000001", "1234")
