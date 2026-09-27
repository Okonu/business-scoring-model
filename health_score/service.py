"""
Scoring service: authenticate, collect, score, return

This is the only entry point the API and the web page use. It is stateless:
every call logs in to BASEPOINT, collects the business's data and scores it.
Credentials are used for the call only and are never stored or logged.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime

from health_score.basepoint import FSSClient, collect
from health_score.scoring import ENGINE_VERSION, score_business
from health_score.settings import Settings

logger = logging.getLogger(__name__)

# Endpoints whose failure means sales may be missing
SALES_ENDPOINTS = {"/orders [monthly]", "/accounting/invoices", "/accounting/sales-receipts", "/shops"}


@dataclass(frozen=True)
class Credentials:
    company_code: str
    pin: str
    username: str | None = None

    def __repr__(self) -> str:  # never print the PIN
        return f"Credentials(company_code={self.company_code!r}, username={self.username!r})"


class ScoringService:
    def __init__(self, settings: Settings, client_factory: Callable[..., FSSClient] = FSSClient):
        self.settings = settings
        self.client_factory = client_factory

    def score(self, credentials: Credentials, as_of: date | None = None) -> dict:
        """
        Score a business as at `as_of` (default: today, UTC)

        Returns:
            dict: the full result (see api.schemas.ScoreResponse)

        Raises:
            AuthenticationError: company code or credentials rejected
            BasepointUnavailableError: BASEPOINT could not be reached
        """
        started = time.monotonic()
        client = self.client_factory(base_url=self.settings.fss_api_url, timeout=self.settings.fss_timeout_seconds)
        tenant, user = client.login(credentials.company_code.strip(), credentials.pin, credentials.username)
        logger.info("Scoring business %s", tenant.get("tenant_code"))

        as_of = as_of or datetime.now(UTC).date()
        data = collect(client, tenant, user, as_of.isoformat())
        result = score_business(data)
        _annotate(result, tenant, user, data, client.coverage, time.monotonic() - started)
        return result


def _business_block(tenant: dict) -> dict:
    return {
        "id": tenant.get("_id"),
        "name": tenant.get("name"),
        "company_code": tenant.get("tenant_code"),
        "business_type": tenant.get("business_type_name"),
        "business_size": tenant.get("business_size"),
        "base_currency": tenant.get("base_currency") or "KES",
        "modules_enabled": [k for k, on in (tenant.get("modules") or {}).items() if on],
    }


def _annotate(result: dict, tenant: dict, user: dict, data, calls: list, duration: float) -> None:
    """Add business details, data coverage and metadata to an engine result"""
    coverage = _coverage(calls)
    warnings = [
        f"{row['endpoint']}: {row['calls'] - row['ok']} of {row['calls']} requests failed"
        + (f" ({'; '.join(row['errors'])})" if row["errors"] else "")
        for row in coverage
        if row["ok"] < row["calls"]
    ]
    sales_failed = any(row["endpoint"] in SALES_ENDPOINTS and row["ok"] < row["calls"] for row in coverage)
    if sales_failed and result["status"] == "insufficient_data":
        # Sales are missing because BASEPOINT failed to return them, not because there are none
        result["status"], result["band"] = "data_unavailable", "Data unavailable"

    result.update(
        {
            "business": _business_block(tenant),
            "scored_as": {
                "user": user.get("name"),
                "is_admin": user.get("is_admin"),
                "note": None
                if user.get("is_admin")
                else "Non-admin login: data may be limited to the shops this user can see",
            },
            "as_of": data.as_of.date().isoformat(),
            "scored_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "engine_version": ENGINE_VERSION,
            "data_coverage": coverage,
            "data_warnings": warnings,
            "record_counts": {name: int(len(df)) for name, df in data.tables.items()},
            "duration_seconds": round(duration, 1),
        }
    )


def _coverage(calls: list) -> list[dict]:
    """One row per endpoint: calls made, how many succeeded, records returned"""
    by_endpoint: dict[str, dict] = {}
    for c in calls:
        row = by_endpoint.setdefault(
            c["endpoint"], {"endpoint": c["endpoint"], "calls": 0, "ok": 0, "records": 0, "errors": set()}
        )
        row["calls"] += 1
        if c["status"] == 200:
            row["ok"] += 1
            row["records"] += c["records"] or 0
        elif c["error"]:
            row["errors"].add(str(c["error"]))
    rows = sorted(by_endpoint.values(), key=lambda r: r["endpoint"])
    return [{**row, "errors": sorted(row["errors"])[:3]} for row in rows]
