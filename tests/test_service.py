"""Scoring service with a fake BASEPOINT client"""

from datetime import date

import pytest

from health_score.basepoint import AuthenticationError
from health_score.service import Credentials, ScoringService
from health_score.settings import Settings
from tests.conftest import FakeClient


def service_for(lists, pin="1234"):
    return ScoringService(Settings(), client_factory=lambda **_: FakeClient(lists, pin=pin))


def test_score_returns_full_result(business_lists):
    result = service_for(business_lists).score(Credentials("TEST-000001", "1234"), date(2026, 9, 26))
    assert result["status"] == "scored"
    assert result["business"]["company_code"] == "TEST-000001"
    assert result["as_of"] == "2026-09-26"
    assert result["engine_version"]
    assert result["data_coverage"] and result["data_warnings"] == []
    for key in ("dimensions", "measures", "shops", "aging", "red_flags", "drivers", "record_counts"):
        assert key in result


def test_wrong_pin_is_rejected(business_lists):
    with pytest.raises(AuthenticationError):
        service_for(business_lists).score(Credentials("TEST-000001", "0000"))


def test_credentials_repr_hides_pin():
    assert "1234" not in repr(Credentials("TEST-000001", "1234"))
