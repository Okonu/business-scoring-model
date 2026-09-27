"""
Read-only client for the BASEPOINT / FSS API

Logs in as a user of one business and fetches data with that user's token.
Credentials and the token live only on the client instance; nothing is
written to disk or logged.
"""

import concurrent.futures as cf
import logging
import threading
import time

import requests

from health_score.basepoint.errors import AuthenticationError, BasepointUnavailableError

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.hospitality.reliatech.co.ke"

# Business fields kept from POST /tenants/verify. The endpoint also returns
# database credentials, so only these fields are ever read from it.
TENANT_FIELDS = [
    "_id",
    "name",
    "tenant_code",
    "business_size",
    "business_type_name",
    "createdAt",
    "subscription_status",
    "subscription_cycle",
    "next_billing_date",
    "is_subscription_active",
    "is_active",
    "is_vat_enabled",
    "solution",
    "fmcg_enabled",
]
MODULE_SETTINGS = ["bandu_settings", "mteja_settings", "dala_settings", "etims_settings"]


class FSSClient:
    """Authenticated, read-only access to one business's data"""

    def __init__(self, base_url=None, timeout=90, retries=1):
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self.session = requests.Session()
        # Many requests run in parallel; keep a connection for each
        adapter = requests.adapters.HTTPAdapter(pool_connections=4, pool_maxsize=32)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.coverage = []
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ auth

    def login(self, company_code, pin, username=None):
        """
        Verify the company code, then log in with a PIN (and username if given)

        Returns:
            tuple: (tenant, user) with only non-sensitive fields
        """
        try:
            resp = self.session.post(
                f"{self.base_url}/tenants/verify",
                json={"companyCode": company_code},
                timeout=self.timeout,
            )
        except requests.RequestException as e:
            raise BasepointUnavailableError(f"BASEPOINT is unreachable: {type(e).__name__}") from e
        if resp.status_code >= 500:
            raise BasepointUnavailableError(f"BASEPOINT returned HTTP {resp.status_code}")
        body = _json(resp)
        data = (body or {}).get("data") or {}
        tenant_raw = data.get("data") if isinstance(data.get("data"), dict) else data
        if resp.status_code != 200 or not tenant_raw.get("_id"):
            raise AuthenticationError("Company code not recognised")
        tenant = _extract_tenant(tenant_raw)

        credentials = {"pin": str(pin)}
        if username:
            credentials["username"] = username
        try:
            resp = self.session.post(
                f"{self.base_url}/users/login",
                json=credentials,
                headers={"companycode": company_code},
                timeout=self.timeout,
            )
        except requests.RequestException as e:
            raise BasepointUnavailableError(f"BASEPOINT is unreachable: {type(e).__name__}") from e
        if resp.status_code >= 500:
            raise BasepointUnavailableError(f"BASEPOINT returned HTTP {resp.status_code}")
        body = _json(resp) or {}
        token = body.get("Token") or body.get("token")
        if resp.status_code != 200 or not token:
            raise AuthenticationError("Login failed for this company code")

        self.session.headers.update({"Authorization": f"Bearer {token}", "companycode": company_code})
        user = {
            "name": body.get("name"),
            "role": body.get("role"),
            "is_admin": bool(body.get("isAdmin")),
        }
        return tenant, user

    # ----------------------------------------------------------------- reads

    def get(self, path, params=None, label=None):
        """GET a path; returns parsed JSON or None, and records coverage"""
        label = label or path
        started = time.monotonic()
        for attempt in range(self.retries + 1):
            try:
                resp = self.session.get(f"{self.base_url}{path}", params=params, timeout=self.timeout)
                body = _json(resp)
                status = resp.status_code
                error = None if status == 200 else _error_text(resp, body)
            except requests.RequestException as e:
                body, status, error = None, None, type(e).__name__
            # Retry gateway errors and timeouts only
            if status is not None and status < 500:
                break
            if attempt < self.retries:
                time.sleep(2)

        ok = status == 200 and body is not None
        self._record(label, status, _count(body) if ok else 0, error, started)
        return body if ok else None

    def get_list(self, path, params=None, key=None, label=None, page_size=500, max_pages=200):
        """
        GET a collection and return its records as a list

        Handles bare lists, {key: [...]}, {data: [...]} and paginated
        responses ({page, totalPages} / {currentPage, totalPages}); later pages
        are fetched in parallel.
        """
        params = dict(params or {})
        body = self.get(path, params, label)
        if body is None:
            return []
        records = _records(body, key)

        total_pages = _total_pages(body)
        if total_pages and total_pages > 1:
            params["limit"] = page_size
            first = self.get(path, {**params, "page": 1}, label)
            if first is None:
                return records
            records = _records(first, key)
            total_pages = min(_total_pages(first) or total_pages, max_pages)
            with cf.ThreadPoolExecutor(6) as ex:
                pages = ex.map(lambda n: self.get(path, {**params, "page": n}, label), range(2, total_pages + 1))
                for more in pages:
                    if more is not None:
                        records.extend(_records(more, key))
        return records

    def _record(self, label, status, records, error, started):
        with self._lock:
            self.coverage.append(
                {
                    "endpoint": label,
                    "status": status,
                    "records": records,
                    "error": error,
                    "ms": int((time.monotonic() - started) * 1000),
                }
            )


# ---------------------------------------------------------------- helpers


def _json(resp):
    try:
        return resp.json()
    except ValueError:
        return None


def _error_text(resp, body):
    if isinstance(body, dict):
        return str(body.get("message") or body.get("error") or "")[:160]
    return f"HTTP {resp.status_code}"


def _extract_tenant(raw):
    """Copy only the whitelisted business fields"""
    tenant = {k: raw.get(k) for k in TENANT_FIELDS}
    tenant["modules"] = {k: bool(v) for k, v in (raw.get("modules") or {}).items() if isinstance(v, bool)}
    tenant["module_enabled_at"] = {
        k.replace("_settings", ""): (raw.get(k) or {}).get("enabled_at")
        for k in MODULE_SETTINGS
        if isinstance(raw.get(k), dict)
    }
    tenant["base_currency"] = (raw.get("accounting_settings") or {}).get("base_currency")
    tenant["subscription_name"] = (raw.get("subscription_id") or {}).get("name")
    tenant["current_subscription_status"] = (raw.get("current_subscription") or {}).get("status")
    return tenant


def _records(body, key=None):
    if isinstance(body, list):
        return body
    if not isinstance(body, dict):
        return []
    if key and isinstance(body.get(key), list):
        return body[key]
    data = body.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if key and isinstance(data.get(key), list):
            return data[key]
        for v in data.values():
            if isinstance(v, list) and (not v or isinstance(v[0], dict)):
                return v
    for v in body.values():
        if isinstance(v, list) and (not v or isinstance(v[0], dict)):
            return v
    return []


def _total_pages(body):
    if isinstance(body, dict):
        for k in ("totalPages", "total_pages"):
            if isinstance(body.get(k), int):
                return body[k]
        pagination = body.get("pagination") or {}
        if isinstance(pagination, dict) and isinstance(pagination.get("totalPages"), int):
            return pagination["totalPages"]
    return None


def _count(body):
    if isinstance(body, dict):
        for k in ("total", "totalItems", "count"):
            if isinstance(body.get(k), int):
                return body[k]
    return len(_records(body)) if body is not None else 0
