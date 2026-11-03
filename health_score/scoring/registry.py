"""Methodology constants: dimensions, measures, thresholds, red flags and bands"""

import re
from dataclasses import dataclass

ENGINE_VERSION = "0.3.0"

DIMENSIONS = {
    "sales": ("Sales performance", 0.20),
    "cash": ("Cash, collections and payables", 0.25),
    "profit": ("Profitability and cost control", 0.15),
    "customers": ("Customer and revenue base", 0.12),
    "operations": ("Operational stability", 0.18),
    "formality": ("Formality and compliance", 0.10),
}

PEER_MEDIAN_DEFAULT = 50.0
CREDIBILITY_FULL_WEIGHT = 0.50
MIN_ACTIVITY_DAYS = 90
MAX_IMPUTED_DIMENSIONS = 1

RAMP_UP_DAYS = 90
TREND_MIN_HISTORY_DAYS = 180
YOY_MIN_HISTORY_DAYS = 455
SEVERE_OVERDUE_DAYS = 90
CASH_BUSINESS_CREDIT_SHARE = 0.05
WALK_IN_IDENTIFIED_SHARE = 0.20
BOOKS_COVERAGE_MIN = 0.80
ITEM_COST_COVERAGE_MIN = 0.80

TIER_POINTS = {0: 0, 1: 40, 2: 75, 3: 100}
TRACKING_FACTOR_MIN = 0.75
TRACKING_FACTOR_SPAN = 0.50
MIN_PURCHASE_DOCUMENTS = 3
MIN_PURCHASE_SHARE_OF_REVENUE = 0.05

BANDS = [(80, "Strong"), (65, "Healthy"), (50, "Watch"), (35, "Weak"), (0, "Distressed")]

BENCHMARK_MIN_FIRMS = 30
BENCHMARK_PERCENTILES = (75, 10)

GROSS_MARGIN_BY_SECTOR = {
    "food_service": (0.60, 0.40),
    "retail_wholesale": (0.25, 0.05),
    "services": (0.50, 0.20),
    "other": (0.35, 0.05),
}

SECTOR_PATTERNS = {
    "food_service": re.compile(
        r"restaurant|caf[eé]|coffee|\bbar\b|pub|lounge|hotel|food|bakery|catering|eatery|kitchen|butchery", re.I
    ),
    "services": re.compile(
        r"salon|spa\b|massage|parlou?r|nail|hair|cosmetic|barber|beauty|clinic|medical|dental|consult|professional|service|laundry|gym|fitness|"
        r"school|agency|legal|\blaw|account|garage|repair|studio|real estate|property",
        re.I,
    ),
    "retail_wholesale": re.compile(
        r"retail|wholesale|shop|store|supermarket|mini ?mart|hardware|pharmacy|chemist|boutique|electronic|"
        r"distribut|agrovet|liquor|wines",
        re.I,
    ),
}


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
    basis: str = "C"
    supplier: bool = False
    payables: bool = False
    business_only: bool = False
    sector_thresholds: bool = False


M = Measure

MEASURES = [
    M("daily_txn_volume", "Transactions per trading day", "sales", 8, "higher", 50, 2, unit="/day"),
    M("daily_txn_value", "Revenue per trading day", "sales", 10, "higher", 50_000, 1_000, unit="KES/day"),
    M("revenue_growth", "Revenue growth, T3M vs P3M", "sales", 10, "higher", 0.05, -0.25, unit="ratio", basis="S"),
    M("yoy_growth", "Year-on-year growth", "sales", 12, "higher", 0.10, -0.25, unit="ratio", basis="S"),
    M("revenue_volatility", "Monthly revenue volatility (CV, T12M)", "sales", 12, "lower", 0.15, 0.60, unit="cv"),
    M("trading_continuity", "Months with sales, T12M", "sales", 8, "higher", 12, 6, unit="months"),
    M("trading_days", "Trading days share, T3M", "sales", 6, "higher", 0.85, 0.30, unit="ratio"),
    M("txn_count_trend", "Transaction count trend", "sales", 6, "higher", 0.05, -0.25, unit="ratio", basis="S"),
    M("avg_txn_value_trend", "Average transaction value trend", "sales", 4, "higher", 0.0, -0.25, unit="ratio"),
    M("revenue_leakage", "Revenue leakage (discounts, voids)", "sales", 7, "lower", 0.03, 0.20, unit="ratio"),
    M("refund_rate", "Refunds and credit notes", "sales", 4, "lower", 0.01, 0.10, unit="ratio"),
    M("recurring_share", "Recurring revenue share", "sales", 5, "higher", 0.30, 0.0, unit="ratio"),
    M("forward_bookings", "Forward bookings ratio", "sales", 3, "higher", 1.0, 0.5, unit="x"),
    M("target_attainment", "Sales target attainment", "sales", 3, "higher", 1.0, 0.6, unit="ratio"),
    M("lead_conversion", "Lead conversion rate, T6M", "sales", 2, "higher", 0.25, 0.05, unit="ratio"),
    M("cash_realization", "Cash realization", "cash", 19, "higher", 0.95, 0.60, unit="ratio", basis="E"),
    M("ar_severe_overdue", "Receivables 90+ days past due", "cash", 11, "lower", 0.05, 0.40, unit="ratio", basis="S"),
    M("dso", "Days sales outstanding", "cash", 9, "lower", 45, 90, unit="days", basis="B"),
    M("ar_wadpd", "Weighted average days past due", "cash", 6, "lower", 5, 30, unit="days", basis="S"),
    M("cei", "Collection effectiveness index", "cash", 6, "higher", 0.80, 0.50, unit="ratio", basis="B"),
    M("aging_drift", "Aging drift (3-month change)", "cash", 4, "lower", 0.0, 0.20, unit="ratio"),
    M("cash_runway", "Cash runway", "cash", 12, "higher", 2, 0.5, unit="months", basis="E", business_only=True),
    M("credit_limit_breach", "Customers over credit limit", "cash", 3, "lower", 0.05, 0.30, unit="ratio"),
    M("rent_collection", "Rent collection rate, T3M", "cash", 7, "higher", 0.95, 0.60, unit="ratio", basis="B"),
    M("plan_collection", "Payment-plan collection", "cash", 3, "higher", 0.95, 0.60, unit="ratio", basis="B"),
    M("gift_card_liability", "Gift-card liability / monthly revenue", "cash", 2, "lower", 0.05, 0.50, unit="ratio"),
    M(
        "ap_severe_overdue",
        "Bills 90+ days past due",
        "cash",
        7,
        "lower",
        0.05,
        0.40,
        unit="ratio",
        basis="S",
        supplier=True,
        payables=True,
    ),
    M(
        "bills_on_time",
        "Bills paid on time, T6M",
        "cash",
        7,
        "higher",
        0.90,
        0.40,
        unit="ratio",
        basis="B",
        supplier=True,
        payables=True,
    ),
    M(
        "dpo_vs_terms",
        "DPO / agreed supplier terms",
        "cash",
        4,
        "lower",
        1.1,
        2.5,
        unit="x",
        basis="B",
        supplier=True,
        payables=True,
    ),
    M("gross_margin", "Gross margin", "profit", 24, "higher", unit="ratio", basis="B", sector_thresholds=True),
    M("net_margin", "Net margin", "profit", 23, "higher", 0.10, -0.10, unit="ratio", basis="B"),
    M("staff_cost_ratio", "Staff cost / revenue", "profit", 17, "lower", 0.30, 0.50, unit="ratio", basis="B"),
    M("cost_discipline", "Cost discipline (expense vs revenue growth)", "profit", 9, "lower", 0.0, 0.25, unit="ratio"),
    M("revenue_per_staff", "Revenue per staff member", "profit", 6, "benchmark", unit="KES"),
    M("maintenance_ratio", "Maintenance cost / rent income", "profit", 9, "lower", 0.05, 0.25, unit="ratio"),
    M("commission_ratio", "Commission cost / property sales", "profit", 4, "lower", 0.03, 0.10, unit="ratio"),
    M(
        "purchase_alignment",
        "Purchase-to-sales alignment",
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
    M("top_customer_share", "Top customer's share of revenue", "customers", 16, "lower", 0.10, 0.50, basis="S"),
    M("customer_retention", "Customer retention, T3M", "customers", 18, "higher", 0.70, 0.20, basis="E"),
    M("active_customer_trend", "Active-customer trend", "customers", 10, "higher", 0.05, -0.25, basis="S"),
    M("customer_hhi", "Revenue concentration (HHI)", "customers", 5, "lower", 0.10, 0.25, unit="hhi", basis="S"),
    M("txn_breadth", "Transaction breadth (largest sale's share)", "customers", 10, "lower", 0.05, 0.40),
    M("product_concentration", "Product concentration (top product)", "customers", 8, "lower", 0.20, 0.70),
    M("new_customer_trend", "New customers per month, trend", "customers", 8, "higher", 0.0, -0.50),
    M("visit_trend", "Customer visit trend", "customers", 6, "higher", 0.0, -0.30),
    M("satisfaction", "Customer satisfaction (1-5)", "customers", 7, "higher", 4.3, 3.0, unit="/5"),
    M("loyalty_engagement", "Loyalty engagement share", "customers", 5, "higher", 0.20, 0.0),
    M("at_risk_share", "At-risk revenue share", "customers", 7, "lower", 0.05, 0.30),
    M("tenure", "Business tenure", "operations", 10, "higher", 48, 12, unit="months", basis="E"),
    M("staff_trend", "Staff count trend (6 months)", "operations", 6, "higher", 0.0, -0.40),
    M("staff_turnover", "Staff turnover, T12M", "operations", 6, "lower", 0.30, 0.80, basis="E"),
    M("payroll_regularity", "Payroll regularity, T6M", "operations", 8, "higher", 1.0, 0.5, basis="S"),
    M("shift_regularity", "Shift regularity", "operations", 5, "higher", 0.90, 0.40),
    M("key_person", "Key-person dependence", "operations", 5, "lower", 0.40, 0.90),
    M("stockout_rate", "Stock-out rate", "operations", 6, "lower", 0.05, 0.20, basis="E"),
    M("inventory_turnover", "Inventory turnover", "operations", 6, "higher", 6, 1, unit="x", basis="B"),
    M("dead_stock", "Dead stock (unsold 90 days)", "operations", 3, "lower", 0.10, 0.50),
    M("catalogue_activity", "Catalogue activity", "operations", 3, "higher", 0.60, 0.15),
    M("capacity_utilization", "Capacity utilization", "operations", 3, "benchmark", unit="/table/day"),
    M("occupancy", "Occupancy (units)", "operations", 6, "higher", 0.90, 0.50, basis="B"),
    M("maintenance_backlog", "Maintenance backlog", "operations", 3, "lower", 0.10, 0.50),
    M("shop_network", "Shop network (2+ shops)", "operations", 6, "score", unit="score", business_only=True),
    M("unplanned_leave", "Unplanned leave", "operations", 2, "lower", 0.02, 0.10),
    M("asset_trend", "Asset base trend", "operations", 2, "higher", 0.0, -0.30),
    M("supplier_concentration", "Supplier concentration", "operations", 5, "lower", 0.30, 0.80, supplier=True),
    M("fill_rate", "Delivery fill rate", "operations", 4, "higher", 0.95, 0.60, basis="B", supplier=True),
    M("procurement_regularity", "Procurement regularity", "operations", 2, "higher", 1.0, 0.33, supplier=True),
    M("sell_through", "Sell-through of tracked stock", "operations", 5, "higher", 0.80, 0.30, basis="B", supplier=True),
    M(
        "stock_cover",
        "Stock cover of tracked stock",
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
    M("digital_payment_share", "Digital payment share", "formality", 20, "higher", 0.70, 0.10),
    M("tax_compliance", "Tax registration and eTIMS", "formality", 20, "score", basis="S", business_only=True),
    M("receipting", "Receipting (sales with a receipt)", "formality", 10, "higher", 0.95, 0.50, basis="S"),
    M("bookkeeping_regularity", "Bookkeeping regularity, T6M", "formality", 14, "higher", 1.0, 0.33, basis="S"),
    M("reconciliation_recency", "Bank reconciliation recency", "formality", 9, "lower", 35, 90, unit="days", basis="B"),
    M("statutory_compliance", "Statutory payroll compliance", "formality", 12, "higher", 1.0, 0.5, basis="S"),
    M("platform_standing", "Platform standing", "formality", 5, "score", business_only=True),
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

SHOP_NETWORK = {
    "weak_shop_revenue_share": (0.10, 0.50),
    "top_shop_share": (0.50, 0.90),
    "declining_shop_share": (0.20, 0.60),
    "dormant_shop_share": (0.0, 0.40),
}
SHOP_DECLINE = -0.10
SHOP_DORMANT_DAYS = 30
WEAK_SHOP_SCORE = 50
MIN_SHOPS_FOR_NETWORK = 2

CAPS = {
    "revenue_collapse": 40,
    "missed_payroll": 40,
    "severe_supplier_arrears": 40,
    "cash_exhaustion": 45,
    "flagship_collapse": 45,
    "receivables_write_off": 50,
    "single_customer": 55,
    "widespread_shop_decline": 55,
}
COLLAPSE_RATIO = 0.50
CASH_EXHAUSTION_MONTHS = 0.67
WRITE_OFF_SHARE = 0.40
SINGLE_CUSTOMER_SHARE = 0.70
SUPPLIER_ARREARS_SHARE = 0.50
FLAGSHIP_SHARE = 0.50
WIDESPREAD_DECLINE_SHARE = 0.60
PAYROLL_GAP_DAYS = 61


def sector_of(business_type):
    """Gross-margin sector for a tenant business type"""
    text = str(business_type or "").replace("_", " ")
    return next((sector for sector, pattern in SECTOR_PATTERNS.items() if pattern.search(text)), "other")


def validate():
    """Fail fast on an inconsistent registry"""
    for dim in DIMENSIONS:
        total = sum(m.weight for m in MEASURES if m.dimension == dim)
        if abs(total - 100) > 1e-9:
            raise ValueError(f"Measure weights for {dim} sum to {total}, not 100")
    if abs(sum(w for _, w in DIMENSIONS.values()) - 1.0) > 1e-9:
        raise ValueError("Dimension weights must sum to 1")
    if len(MEASURES_BY_ID) != len(MEASURES):
        raise ValueError("Measure ids must be unique")


validate()
