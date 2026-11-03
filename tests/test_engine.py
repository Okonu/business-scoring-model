"""Unit tests for the methodology: scales, weights, credibility, red flags and shop network"""

import pytest

from health_score.scoring import band, registry, score_value
from health_score.scoring.aggregation import blend, credibility, score_scorecard, tracking_factor
from health_score.scoring.engine import confidence, publishable
from health_score.scoring.red_flags import overall_cap, red_flags
from health_score.scoring.shops import shop_network

M = registry.MEASURES_BY_ID


@pytest.mark.parametrize(
    ("measure", "value", "expected"),
    [
        ("revenue_growth", 0.05, 100),
        ("revenue_growth", -0.25, 0),
        ("revenue_growth", -0.10, 50),
        ("revenue_growth", 0.50, 100),
        ("yoy_growth", 0.10, 100),
        ("yoy_growth", -0.25, 0),
        ("dso", 45, 100),
        ("dso", 63, 60),
        ("dso", 90, 0),
        ("cash_realization", 0.88, 80),
        ("cash_runway", 2, 100),
        ("cash_runway", 0.5, 0),
        ("ar_wadpd", 30, 0),
        ("cei", 0.80, 100),
        ("staff_cost_ratio", 0.30, 100),
        ("staff_cost_ratio", 0.50, 0),
        ("top_customer_share", 0.10, 100),
        ("top_customer_share", 0.50, 0),
        ("customer_hhi", 0.25, 0),
        ("tenure", 48, 100),
        ("tenure", 12, 0),
        ("tenure", 30, 50),
        ("staff_turnover", 0.30, 100),
        ("stockout_rate", 0.20, 0),
        ("reconciliation_recency", 90, 0),
        ("stock_cover", 30, 100),
        ("stock_cover", 3, 0),
        ("stock_cover", 180, 0),
        ("stock_cover", 120, 50),
        ("tax_compliance", 75, 75),
    ],
)
def test_score_value_uses_methodology_thresholds(measure, value, expected):
    assert score_value(M[measure], value) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("sector", "good", "poor"),
    [("food_service", 0.60, 0.40), ("retail_wholesale", 0.25, 0.05), ("services", 0.50, 0.20), ("other", 0.35, 0.05)],
)
def test_gross_margin_thresholds_by_sector(sector, good, poor):
    assert score_value(M["gross_margin"], good, sector) == 100
    assert score_value(M["gross_margin"], poor, sector) == 0


@pytest.mark.parametrize(
    ("business_type", "sector"),
    [
        ("Salon & Spa", "services"),
        ("massage_parlour", "services"),
        ("fast_food", "food_service"),
        ("Barber shop", "services"),
        ("Restaurant", "food_service"),
        ("Coffee shop", "food_service"),
        ("Hardware store", "retail_wholesale"),
        ("Retail", "retail_wholesale"),
        (None, "other"),
    ],
)
def test_sector_comes_from_business_type(business_type, sector):
    assert registry.sector_of(business_type) == sector


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (100, "Strong"),
        (80, "Strong"),
        (79.9, "Healthy"),
        (65, "Healthy"),
        (50, "Watch"),
        (35, "Weak"),
        (0, "Distressed"),
    ],
)
def test_band(score, expected):
    assert band(score) == expected


def test_dimension_weights_match_methodology():
    weights = {dim: weight for dim, (_, weight) in registry.DIMENSIONS.items()}
    assert weights == {
        "sales": 0.20,
        "cash": 0.25,
        "profit": 0.15,
        "customers": 0.12,
        "operations": 0.18,
        "formality": 0.10,
    }


def test_measure_weights_sum_to_100_per_dimension():
    for dim in registry.DIMENSIONS:
        assert sum(m.weight for m in registry.MEASURES if m.dimension == dim) == pytest.approx(100)


def test_ecosystem_depth_is_not_a_measure():
    assert "ecosystem_depth" not in M


@pytest.mark.parametrize(("share", "expected"), [(None, 1.0), (0.0, 0.75), (0.5, 1.0), (1.0, 1.25)])
def test_tracking_factor(share, expected):
    assert tracking_factor({"supplier_tracking": {"tracking_share": share}}) == pytest.approx(expected)


@pytest.mark.parametrize(("share", "expected"), [(0.0, 0.0), (0.06, 0.12), (0.25, 0.5), (0.5, 1.0), (0.9, 1.0)])
def test_credibility(share, expected):
    assert credibility(share) == pytest.approx(expected)


def test_thin_dimension_is_pulled_toward_the_peer_median():
    rows = [{"score": 100.0, "weight": 6, "base_weight": 6}]
    measured, c, score = blend(rows)
    assert measured == 100
    assert c == pytest.approx(0.12)
    assert score == pytest.approx(0.12 * 100 + 0.88 * 50)


def test_dimension_with_half_its_weight_counts_in_full():
    rows = [{"score": 80.0, "weight": 19, "base_weight": 19}, {"score": 60.0, "weight": 31, "base_weight": 31}]
    _, c, score = blend(rows)
    assert c == 1.0
    assert score == pytest.approx((19 * 80 + 31 * 60) / 50)


def test_worked_example_cash_dimension():
    values = {"cash_realization": 0.88, "ar_severe_overdue": 0.12, "dso": 63, "cei": 0.62, "cash_runway": 0.8}
    card = score_scorecard(values, {"sector": "retail_wholesale"})
    cash = card.dimensions["cash"]
    assert cash["measured_share"] == pytest.approx(0.57)
    assert cash["score"] == pytest.approx(60.0)


def test_missing_dimension_is_imputed_at_the_peer_median():
    card = score_scorecard({"cash_realization": 0.95}, {})
    assert card.dimensions["sales"]["imputed"] is True
    assert card.dimensions["sales"]["score"] == registry.PEER_MEDIAN_DEFAULT


def test_benchmark_measures_are_not_scored():
    card = score_scorecard({"revenue_per_staff": 1_000_000, "capacity_utilization": 5}, {})
    assert not card.measures


def test_weights_in_score_reconcile_with_the_overall_score():
    values = {"cash_realization": 0.9, "revenue_growth": 0.0, "tenure": 30, "gross_margin": 0.3, "receipting": 0.8}
    card = score_scorecard(values, {"sector": "other"})
    measured = sum(r["score"] * r["weight_in_score"] / 100 for r in card.measures)
    imputed = sum(
        info["weight"] * (1 - info["credibility"]) * registry.PEER_MEDIAN_DEFAULT for info in card.dimensions.values()
    )
    assert measured + imputed == pytest.approx(card.overall, abs=0.15)


@pytest.mark.parametrize(
    ("history", "imputed", "expected"),
    [(90, [], True), (89, [], False), (400, ["sales"], True), (400, ["sales", "cash"], False)],
)
def test_publishable(history, imputed, expected):
    assert publishable(history, imputed) is expected


@pytest.mark.parametrize(
    ("history", "imputed", "available", "expected"),
    [(400, [], 0.7, "High"), (400, [], 0.5, "Medium"), (200, ["sales"], 0.7, "Medium"), (100, [], 0.9, "Low")],
)
def test_confidence(history, imputed, available, expected):
    assert confidence(history, imputed, available) == expected


def _context(**inputs):
    base = {"history_days": 400, "revenue_t3m": 100.0, "revenue_p3m": 100.0}
    flag_inputs = {k: inputs.pop(k) for k in list(inputs) if k not in base}
    return {**base, **inputs, "red_flag_inputs": flag_inputs}


def _flags(values=None, shops=None, **context):
    return {f["flag"]: f["cap"] for f in red_flags(values or {}, _context(**context), shops or [])}


def test_no_red_flags_for_a_steady_business():
    assert _flags() == {}


def test_revenue_collapse_needs_the_quarter_fall():
    assert _flags(revenue_t3m=50.0) == {"Revenue collapse": 40}
    assert _flags(revenue_t3m=51.0) == {}


def test_revenue_collapse_with_15_months_also_needs_the_year_on_year_fall():
    assert _flags(revenue_t3m=50.0, revenue_same_quarter_last_year=60.0) == {}
    assert _flags(revenue_t3m=50.0, revenue_same_quarter_last_year=100.0) == {"Revenue collapse": 40}


@pytest.mark.parametrize(
    ("values", "inputs", "flag", "cap"),
    [
        ({}, {"missed_payroll": True}, "Missed payroll", 40),
        ({}, {"ap_severe_share": 0.5}, "Severe supplier arrears", 40),
        ({"cash_runway": 0.6}, {}, "Cash exhaustion", 45),
        ({}, {"ar_severe_share": 0.4}, "Receivables write-off risk", 50),
        ({"top_customer_share": 0.7}, {}, "Single-customer dependence", 55),
    ],
)
def test_red_flag_conditions_and_caps(values, inputs, flag, cap):
    assert _flags(values, **inputs) == {flag: cap}


@pytest.mark.parametrize(
    ("values", "inputs"),
    [
        ({"cash_runway": 0.7}, {}),
        ({}, {"ar_severe_share": 0.39}),
        ({}, {"ap_severe_share": 0.49}),
        ({"top_customer_share": 0.69}, {}),
    ],
)
def test_red_flags_stay_off_below_their_lines(values, inputs):
    assert _flags(values, **inputs) == {}


def _shop(name, share, t12, t3=100.0, p3=100.0, status="established", score=70.0):
    return {
        "name": name,
        "status": status,
        "revenue_share": share,
        "revenue_t12m": t12,
        "revenue_t3m": t3,
        "revenue_p3m": p3,
        "declining": p3 > 0 and t3 / p3 - 1 <= registry.SHOP_DECLINE,
        "score": score,
    }


def test_flagship_collapse_and_widespread_decline():
    shops = [_shop("Main", 0.6, 600, t3=40), _shop("Branch", 0.4, 400, t3=80)]
    assert _flags(shops=shops) == {"Flagship shop collapse": 45, "Widespread shop decline": 55}


def test_lowest_cap_applies():
    assert overall_cap([{"cap": 55}, {"cap": 40}, {"cap": 45}]) == 40
    assert overall_cap([]) == 100


def test_shop_network_uses_table_10_thresholds():
    network = shop_network([_shop("A", 0.5, 500), _shop("B", 0.5, 500)])
    assert network["parts"]["top_shop_share"]["score"] == 100
    flagship = shop_network([_shop("A", 0.9, 900), _shop("B", 0.1, 100)])
    assert flagship["parts"]["top_shop_share"]["score"] == 0
    dormant = shop_network([_shop("A", 0.5, 500), _shop("B", 0.5, 500, status="dormant")])
    assert dormant["parts"]["dormant_shop_share"]["value"] == 0.5
    assert dormant["parts"]["dormant_shop_share"]["score"] == 0


def test_shop_network_needs_two_mature_shops():
    assert shop_network([_shop("A", 1.0, 1000), _shop("B", 0.0, 0, status="new")]) is None
