"""Collector + measures + engine on synthetic BASEPOINT data"""

from health_score.scoring import score_business
from tests.conftest import collect_data, make_business, make_purchase_order


def test_healthy_duka_business(business_lists):
    data = collect_data(business_lists)
    r = score_business(data)

    assert r["status"] == "scored"
    assert r["products_used"] == ["duka"]
    assert 0 <= r["score"] <= 100
    # POS-generated invoices are the same sales as the orders
    assert len(data.table("transactions")) == len(data.table("orders"))
    ids = {m["id"] for m in r["measures"]}
    assert not ids & {"ap_severe_overdue", "bills_on_time", "net_margin", "rent_collection"}
    scores = {m["id"]: m["score"] for m in r["measures"]}
    assert scores["revenue_volatility"] >= 90 and scores["trading_continuity"] == 100
    assert scores["revenue_growth"] >= 70
    # Small scale (4 sales, KES 4,000 a day) scores low on the scale measures
    assert scores["daily_txn_volume"] < 20 and scores["daily_txn_value"] < 20
    assert not r["red_flags"]
    assert sum(1 for s in r["shops"] if s["score"] is not None) == 2
    assert r["shop_network"] is not None


def test_revenue_collapse_caps_score():
    r = score_business(collect_data(make_business(decline_last_90=True)))
    assert "Revenue collapse" in [f["flag"] for f in r["red_flags"]]
    assert r["score"] <= 40 < r["score_uncapped"]


def test_measure_weights_renormalized_within_dimensions(business_lists):
    r = score_business(collect_data(business_lists))
    for dim in r["dimensions"]:
        rows = [m for m in r["measures"] if m["dimension"] == dim]
        if rows:
            assert abs(sum(m["weight_in_dimension"] for m in rows) - 100) < 0.5


def test_insufficient_history():
    r = score_business(collect_data(make_business(days=40)))
    assert r["status"] == "insufficient_data"
    assert r["score"] is None


def test_supplier_measures_need_minimum_purchases():
    lists = make_business()
    assert score_business(collect_data(lists))["context"]["supplier_tracking"]["has_supplier_data"] is False

    lists["/product-inventory"][0]["supplier_id"] = "s1"
    pattern = {"supplier_concentration", "fill_rate", "sell_through"}

    lists["/purchase-orders"] = [make_purchase_order(1, 60)]
    one_po = score_business(collect_data(lists))
    assert not pattern & {m["id"] for m in one_po["measures"]}

    lists["/purchase-orders"] = [make_purchase_order(n, 30 + 30 * n) for n in range(3)]
    three_pos = score_business(collect_data(lists))
    assert pattern <= {m["id"] for m in three_pos["measures"]}
    assert three_pos["context"]["supplier_tracking"]["tier_counts"]["2"] == 1


def test_orders_fetched_by_month_are_deduplicated(business_lists):
    # The fake client returns every order for each monthly request
    data = collect_data(business_lists)
    assert len(data.table("orders")) == len(business_lists["/orders"])
