"""Request and response schemas for the HTTP API"""

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class Credentials(BaseModel):
    """BASEPOINT login for the business. Used for this request only; never stored."""

    company_code: str = Field(..., min_length=3, max_length=64, examples=["XXXX-000000"])
    pin: SecretStr = Field(..., min_length=1, max_length=64)
    username: str | None = Field(None, max_length=128, description="Only if the account needs a username")


class ScoreRequest(Credentials):
    as_of_date: date | None = Field(None, description="Reference date; defaults to today (UTC)")


class Business(BaseModel):
    id: str | None
    name: str | None
    company_code: str | None
    business_type: str | None
    business_size: str | None
    base_currency: str
    modules_enabled: list[str]


class Dimension(BaseModel):
    label: str
    weight: float
    score: float
    imputed: bool
    measures_available: int
    measures_total: int


class Measure(BaseModel):
    id: str
    label: str
    dimension: str
    value: float
    unit: str
    score: float
    base_weight: float
    weight: float
    weight_in_dimension: float
    weight_in_score: float
    supplier: bool


class MeasureUnavailable(BaseModel):
    id: str
    label: str
    dimension: str


class RedFlag(BaseModel):
    flag: str
    detail: str
    cap: float


class Driver(BaseModel):
    measure: str
    score: float
    impact: float


class Drivers(BaseModel):
    positive: list[Driver]
    negative: list[Driver]


class Shop(BaseModel):
    model_config = ConfigDict(extra="allow")

    shop_id: str
    name: str | None
    pos_mode: str | None
    status: str
    revenue_t12m: float
    revenue_share: float
    revenue_t3m: float
    revenue_p3m: float
    declining: bool
    score: float | None
    band: str | None


class ScoredAs(BaseModel):
    user: str | None
    is_admin: bool | None
    note: str | None


class CoverageRow(BaseModel):
    endpoint: str
    calls: int
    ok: int
    records: int
    errors: list[str]


class ScoreResponse(BaseModel):
    engine_version: str
    as_of: date
    scored_at: str
    status: str = Field(..., description="scored, insufficient_data or data_unavailable")
    score: float | None
    score_uncapped: float
    band: str
    confidence: str
    products_used: list[str] | None
    measure_weight_available: float
    business: Business
    dimensions: dict[str, Dimension]
    measures: list[Measure]
    measures_not_available: list[MeasureUnavailable]
    red_flags: list[RedFlag]
    drivers: Drivers
    shops: list[Shop]
    shop_network: dict[str, Any] | None
    aging: dict[str, dict[str, float]]
    context: dict[str, Any]
    data_coverage: list[CoverageRow]
    data_warnings: list[str]
    record_counts: dict[str, int]
    scored_as: ScoredAs
    duration_seconds: float


class Health(BaseModel):
    status: str
    version: str
    engine_version: str
