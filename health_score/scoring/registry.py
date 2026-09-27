"""
Measure registry for the business health score

Defines the dimensions, every measure, and their weights and thresholds. It
mirrors docs/methodology/business-health-score.md. Weights and thresholds are
draft values; change them here, not in the measure code. Changing any of them
requires a new ENGINE_VERSION, so results from different versions can be told apart.

Measure kinds:
    higher - bigger is better; scores 100 at `good`, 0 at `poor`
    lower  - smaller is better; scores 100 at `good`, 0 at `poor`
    range  - best inside [good_low, good_high], 0 outside [poor_low, poor_high]
    score  - the measure already returns a 0-100 score
"""

from dataclasses import dataclass

ENGINE_VERSION = "0.2.0"

DIMENSIONS = {
    "sales": ("Sales performance", 0.22),
    "cash": ("Cash, collections and payables", 0.22),
    "profit": ("Profitability and cost control", 0.13),
    "customers": ("Customer and revenue base", 0.13),
    "operations": ("Operational stability", 0.18),
    "formality": ("Formality and compliance", 0.12),
}

BANDS = [(80, "Strong"), (65, "Healthy"), (50, "Watch"), (35, "Weak"), (0, "Distressed")]

# Imputed value for a dimension with no measures, until peer medians exist
IMPUTED_DIMENSION_SCORE = 50.0

# Supplier measures: weight x (0.75 + 0.5 x share of purchases from tier 2-3 suppliers)
TRACKING_FACTOR_MIN = 0.75
TRACKING_FACTOR_SPAN = 0.5

# Supplier tracking tier -> traceability index points
TIER_POINTS = {0: 0, 1: 40, 2: 75, 3: 100}

# Ecosystem depth: BASE products actively used -> score
ECOSYSTEM_SCORES = {1: 40, 2: 60, 3: 80, 4: 100}

RAMP_UP_DAYS = 90
MIN_ACTIVITY_DAYS = 90
CASH_BUSINESS_CREDIT_SHARE = 0.05
WALK_IN_IDENTIFIED_SHARE = 0.20
# Purchase-pattern measures need at least this many POs or bills in 12 months
MIN_PURCHASE_DOCUMENTS = 3


@dataclass(frozen=True)
class Measure:
    id: str
    label: str
    dimension: str
    weight: float
    kind: str
    good: float | None = None
    poor: float | None = None
    good_high: float | None = None
    poor_high: float | None = None
    unit: str = ""
    supplier: bool = False
    business_only: bool = False


M = Measure
MEASURES = [
    # -- Sales performance
    M("daily_txn_volume", "Transactions per trading day", "sales", 10, "higher", 50, 2, unit="/day"),
    M("daily_txn_value", "Revenue per trading day", "sales", 10, "higher", 50_000, 1_000, unit="KES/day"),
    M(
        "revenue_growth",
        "Revenue growth, last 3 months vs previous 3",
        "sales",
        14,
        "higher",
        0.10,
        -0.30,
        unit="ratio",
    ),
    M("yoy_growth", "Revenue growth vs same 3 months last year", "sales", 8, "higher", 0.10, -0.30, unit="ratio"),
    M("revenue_volatility", "Monthly revenue volatility (CV)", "sales", 12, "lower", 0.15, 0.60, unit="cv"),
    M("trading_continuity", "Months with revenue, last 12", "sales", 6, "higher", 12, 6, unit="months"),
    M("trading_days", "Share of days with sales, last 3 months", "sales", 6, "higher", 0.85, 0.30, unit="ratio"),
    M("txn_count_trend", "Transaction count trend", "sales", 6, "higher", 0.05, -0.30, unit="ratio"),
    M("avg_txn_value_trend", "Average transaction value trend", "sales", 4, "higher", 0.0, -0.25, unit="ratio"),
    M("revenue_leakage", "Discounts and voids share of gross sales", "sales", 7, "lower", 0.03, 0.20, unit="ratio"),
    M("refund_rate", "Refunds share of revenue", "sales", 4, "lower", 0.01, 0.10, unit="ratio"),
    M("recurring_share", "Recurring revenue share", "sales", 5, "higher", 0.30, 0.0, unit="ratio"),
    M("forward_bookings", "Bookings next 30 days vs last 30", "sales", 3, "higher", 1.0, 0.5, unit="x"),
    M("target_attainment", "Sales target attainment", "sales", 3, "higher", 1.0, 0.6, unit="ratio"),
    M("lead_conversion", "Lead conversion rate", "sales", 2, "higher", 0.25, 0.05, unit="ratio"),
    # -- Cash, collections and payables
    M("cash_realization", "Cash received / revenue", "cash", 19, "higher", 0.95, 0.60, unit="ratio"),
    M("ar_severe_overdue", "Receivables 60+ days past due", "cash", 11, "lower", 0.05, 0.40, unit="ratio"),
    M("dso", "Days sales outstanding", "cash", 11, "lower", 30, 120, unit="days"),
    M("ar_wadpd", "Receivables weighted days past due", "cash", 6, "lower", 5, 60, unit="days"),
    M("cei", "Collection effectiveness index", "cash", 6, "higher", 0.90, 0.50, unit="ratio"),
    M("aging_drift", "Change in receivables 60+ share, 3 months", "cash", 4, "lower", 0.0, 0.20, unit="ratio"),
    M("cash_runway", "Cash runway", "cash", 10, "higher", 3, 0.5, unit="months", business_only=True),
    M("credit_limit_breach", "Customers over credit limit", "cash", 3, "lower", 0.05, 0.30, unit="ratio"),
    M("rent_collection", "Rent collection rate", "cash", 7, "higher", 0.95, 0.60, unit="ratio"),
    M("plan_collection", "Payment-plan collection rate", "cash", 3, "higher", 0.95, 0.60, unit="ratio"),
    M("gift_card_liability", "Gift card liability / monthly revenue", "cash", 2, "lower", 0.05, 0.50, unit="ratio"),
    M("ap_severe_overdue", "Bills 60+ days past due", "cash", 7, "lower", 0.05, 0.40, unit="ratio", supplier=True),
    M("bills_on_time", "Bills paid on time", "cash", 7, "higher", 0.90, 0.40, unit="ratio", supplier=True),
    M("dpo_vs_terms", "Days payable / agreed supplier terms", "cash", 4, "lower", 1.1, 2.5, unit="x", supplier=True),
    # -- Profitability and cost control
    M("gross_margin", "Gross margin", "profit", 24, "higher", 0.35, 0.05, unit="ratio"),
    M("net_margin", "Net margin", "profit", 23, "higher", 0.10, -0.10, unit="ratio"),
    M("staff_cost_ratio", "Staff cost / revenue", "profit", 14, "lower", 0.25, 0.60, unit="ratio"),
    M("cost_discipline", "Expense growth minus revenue growth", "profit", 9, "lower", 0.0, 0.25, unit="ratio"),
    M("revenue_per_staff", "Monthly revenue per staff member", "profit", 9, "higher", 150_000, 15_000, unit="KES"),
    M("maintenance_ratio", "Maintenance cost / rent", "profit", 9, "lower", 0.05, 0.25, unit="ratio"),
    M("commission_ratio", "Commissions / property sales", "profit", 4, "lower", 0.03, 0.10, unit="ratio"),
    M(
        "purchase_alignment",
        "Purchases / cost of tracked stock sold",
        "profit",
        8,
        "range",
        0.8,
        0.3,
        good_high=1.2,
        poor_high=2.5,
        unit="x",
        supplier=True,
    ),
    # -- Customer and revenue base
    M("top_customer_share", "Top customer share of revenue", "customers", 16, "lower", 0.15, 0.60, unit="ratio"),
    M("customer_retention", "Customer retention", "customers", 16, "higher", 0.70, 0.20, unit="ratio"),
    M(
        "active_customer_trend",
        "Active customer (or transaction) trend",
        "customers",
        10,
        "higher",
        0.05,
        -0.30,
        unit="ratio",
    ),
    M("customer_hhi", "Revenue concentration (HHI)", "customers", 7, "lower", 0.10, 0.40, unit="hhi"),
    M("txn_breadth", "Largest single sale share of revenue", "customers", 10, "lower", 0.05, 0.40, unit="ratio"),
    M("product_concentration", "Top product share of revenue", "customers", 8, "lower", 0.20, 0.70, unit="ratio"),
    M("new_customer_trend", "New customers trend", "customers", 8, "higher", 0.0, -0.50, unit="ratio"),
    M("visit_trend", "Customer visit trend", "customers", 6, "higher", 0.0, -0.30, unit="ratio"),
    M("satisfaction", "Average feedback rating", "customers", 7, "higher", 4.3, 3.0, unit="/5"),
    M(
        "loyalty_engagement",
        "Revenue from loyalty and subscription customers",
        "customers",
        5,
        "higher",
        0.20,
        0.0,
        unit="ratio",
    ),
    M("at_risk_share", "Revenue from at-risk or churned customers", "customers", 7, "lower", 0.05, 0.30, unit="ratio"),
    # -- Operational stability
    M("tenure", "Business tenure", "operations", 8, "higher", 36, 6, unit="months"),
    M("staff_trend", "Staff count trend, 6 months", "operations", 6, "higher", 0.0, -0.40, unit="ratio"),
    M("staff_turnover", "Staff turnover, 12 months", "operations", 6, "lower", 0.15, 0.60, unit="ratio"),
    M("payroll_regularity", "Payroll regularity, 6 months", "operations", 8, "higher", 1.0, 0.5, unit="ratio"),
    M("shift_regularity", "Trading days with an opened shift", "operations", 5, "higher", 0.90, 0.40, unit="ratio"),
    M("key_person", "Top staff member's share of sales", "operations", 5, "lower", 0.40, 0.90, unit="ratio"),
    M("stockout_rate", "Selling items below minimum stock", "operations", 6, "lower", 0.05, 0.30, unit="ratio"),
    M("inventory_turnover", "Inventory turnover", "operations", 6, "higher", 6, 1, unit="x"),
    M("dead_stock", "Stock unsold for 90 days", "operations", 3, "lower", 0.10, 0.50, unit="ratio"),
    M("catalogue_activity", "Share of products sold, 3 months", "operations", 3, "higher", 0.60, 0.15, unit="ratio"),
    M("capacity_utilization", "Orders per table per trading day", "operations", 3, "higher", 3, 0.2, unit="/table/day"),
    M("occupancy", "Unit occupancy", "operations", 6, "higher", 0.90, 0.50, unit="ratio"),
    M("maintenance_backlog", "Maintenance tickets open 30+ days", "operations", 3, "lower", 0.10, 0.50, unit="ratio"),
    M("shop_network", "Shop network", "operations", 8, "score", 75, 40, unit="score", business_only=True),
    M("unplanned_leave", "Unplanned leave share of working days", "operations", 2, "lower", 0.02, 0.10, unit="ratio"),
    M("asset_trend", "Asset base trend, 12 months", "operations", 2, "higher", 0.0, -0.30, unit="ratio"),
    M(
        "supplier_concentration",
        "Top supplier share of purchases",
        "operations",
        5,
        "lower",
        0.30,
        0.80,
        unit="ratio",
        supplier=True,
    ),
    M("fill_rate", "Purchase order fill rate", "operations", 4, "higher", 0.95, 0.60, unit="ratio", supplier=True),
    M(
        "procurement_regularity",
        "Months with purchases, 6 months",
        "operations",
        2,
        "higher",
        1.0,
        0.33,
        unit="ratio",
        supplier=True,
    ),
    M(
        "sell_through",
        "Sell-through of supplier-tracked stock",
        "operations",
        5,
        "higher",
        0.80,
        0.30,
        unit="ratio",
        supplier=True,
    ),
    M(
        "stock_cover",
        "Days of sales covered by tracked stock",
        "operations",
        4,
        "range",
        14,
        3,
        good_high=60,
        poor_high=180,
        unit="days",
        supplier=True,
    ),
    # -- Formality and compliance
    M("digital_payment_share", "Digital payment share", "formality", 18, "higher", 0.70, 0.10, unit="ratio"),
    M(
        "tax_compliance",
        "VAT / eTIMS registration and verification",
        "formality",
        15,
        "score",
        unit="score",
        business_only=True,
    ),
    M("receipting", "Sales with a receipt issued", "formality", 8, "higher", 0.95, 0.50, unit="ratio"),
    M(
        "bookkeeping_regularity",
        "Months with journal entries, 6 months",
        "formality",
        11,
        "higher",
        1.0,
        0.33,
        unit="ratio",
    ),
    M("reconciliation_recency", "Days since last bank reconciliation", "formality", 7, "lower", 35, 120, unit="days"),
    M(
        "statutory_compliance",
        "Payroll runs with statutory deductions",
        "formality",
        8,
        "higher",
        1.0,
        0.5,
        unit="ratio",
    ),
    M(
        "platform_standing",
        "BASEPOINT subscription standing",
        "formality",
        8,
        "score",
        unit="score",
        business_only=True,
    ),
    M("ecosystem_depth", "BASE products actively used", "formality", 15, "score", unit="score", business_only=True),
    M(
        "traceability",
        "Supply-chain traceability index",
        "formality",
        10,
        "higher",
        80,
        10,
        unit="index",
        supplier=True,
    ),
]

MEASURES_BY_ID = {m.id: m for m in MEASURES}


def _check_weights():
    for dim in DIMENSIONS:
        total = sum(m.weight for m in MEASURES if m.dimension == dim)
        if abs(total - 100) > 1e-9:
            raise ValueError(f"Measure weights for {dim} sum to {total}, not 100")
    if abs(sum(w for _, w in DIMENSIONS.values()) - 1.0) > 1e-9:
        raise ValueError("Dimension weights must sum to 1")


_check_weights()
