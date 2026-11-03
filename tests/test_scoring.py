"""Collector, measures and engine together on synthetic BASEPOINT data"""

import pytest

from health_score.scoring import registry, score_business
from tests.conftest import TENANT, collect_data, make_business, make_purchase_order


def test_healthy_duka_business(business_lists):
    data = collect_data(business_lists)
    r = score_business(data)

    assert r["status"] == "scored"
    assert r["products_used"] == ["duka"]
    assert 0 <= r["score"] <= 100
    assert len(data.table("transactions")) == len(data.table("orders"))
    ids = {m["id"] for m in r["measures"]}
    assert not ids & {"ap_severe_overdue", "bills_on_time", "net_margin", "rent_collection"}
    scores = {m["id"]: m["score"] for m in r["measures"]}
    assert scores["revenue_volatility"] >= 90 and scores["trading_continuity"] == 100
    assert scores["revenue_growth"] >= 70
    assert scores["daily_txn_volume"] < 20 and scores["daily_txn_value"] < 20
    assert not r["red_flags"]
    assert sum(1 for s in r["shops"] if s["score"] is not None) == 2
    assert r["shop_network"] is not None
    assert r["context"]["sector"] == "retail_wholesale"


def test_engine_version_and_measure_count():
    assert registry.ENGINE_VERSION == "0.3.0"
    assert len(registry.MEASURES) == 77


def test_revenue_collapse_caps_score():
    r = score_business(collect_data(make_business(decline_last_90=True)))
    assert "Revenue collapse" in [f["flag"] for f in r["red_flags"]]
    assert r["score"] <= 40 < r["score_uncapped"]


def test_measure_weights_renormalized_within_dimensions(business_lists):
    r = score_business(collect_data(business_lists))
    for dim in r["dimensions"]:
        rows = [m for m in r["measures"] if m["dimension"] == dim]
        if rows:
            assert sum(m["weight_in_dimension"] for m in rows) == pytest.approx(100, abs=0.5)


def test_overall_score_reconciles_with_dimensions(business_lists):
    r = score_business(collect_data(business_lists))
    total = sum(info["weight"] * info["score"] for info in r["dimensions"].values())
    assert total == pytest.approx(r["score_uncapped"], abs=0.15)


def test_thin_dimensions_are_blended_with_the_peer_median(business_lists):
    r = score_business(collect_data(business_lists))
    for info in r["dimensions"].values():
        if info["imputed"]:
            assert info["score"] == registry.PEER_MEDIAN_DEFAULT
        elif info["measured_share"] < registry.CREDIBILITY_FULL_WEIGHT:
            expected = info["credibility"] * info["measured_score"] + (1 - info["credibility"]) * 50
            assert info["credibility"] < 1
            assert info["score"] == pytest.approx(expected, abs=0.1)


def test_benchmark_measures_are_reported_but_not_scored(business_lists):
    r = score_business(collect_data(business_lists))
    assert "revenue_per_staff" in {m["id"] for m in r["measures_pending_benchmark"]}
    assert "revenue_per_staff" not in {m["id"] for m in r["measures"]}


def test_using_more_products_adds_no_points(business_lists):
    r = score_business(collect_data(business_lists))
    assert "ecosystem_depth" not in {m["id"] for m in r["measures"] + r["measures_not_available"]}


def test_insufficient_history():
    r = score_business(collect_data(make_business(days=40)))
    assert r["status"] == "insufficient_data"
    assert r["score"] is None


def test_supplier_measures_need_minimum_purchase_documents():
    lists = make_business()
    assert score_business(collect_data(lists))["context"]["supplier_tracking"]["has_supplier_data"] is False

    lists["/product-inventory"][0]["supplier_id"] = "s1"
    pattern = {"supplier_concentration", "fill_rate", "sell_through", "traceability"}

    lists["/purchase-orders"] = [make_purchase_order(1, 60)]
    one_po = score_business(collect_data(lists))
    assert not pattern & {m["id"] for m in one_po["measures"]}

    lists["/purchase-orders"] = [make_purchase_order(n, 30 + 30 * n) for n in range(3)]
    three_pos = score_business(collect_data(lists))
    assert pattern <= {m["id"] for m in three_pos["measures"]}
    assert three_pos["context"]["purchase_base_met"] is True
    assert three_pos["context"]["supplier_tracking"]["tier_counts"]["2"] == 1


def test_supplier_measures_need_purchases_of_5_percent_of_revenue():
    lists = make_business()
    lists["/product-inventory"][0]["supplier_id"] = "s1"
    lists["/purchase-orders"] = [make_purchase_order(n, 30 + 30 * n, quantity=5) for n in range(3)]
    r = score_business(collect_data(lists))
    assert r["context"]["purchase_base_met"] is False
    assert not {m["id"] for m in r["measures"] if m["supplier"] and not registry.MEASURES_BY_ID[m["id"]].payables}


@pytest.mark.parametrize(("tenant", "expected"), [({}, 0.0), ({"is_vat_enabled": True}, 50.0)])
def test_tax_compliance_scores_registration(monkeypatch, business_lists, tenant, expected):
    monkeypatch.setitem(TENANT, "is_vat_enabled", tenant.get("is_vat_enabled", False))
    r = score_business(collect_data(business_lists))
    assert {m["id"]: m["value"] for m in r["measures"]}["tax_compliance"] == expected


def test_orders_fetched_by_month_are_deduplicated(business_lists):
    data = collect_data(business_lists)
    assert len(data.table("orders")) == len(business_lists["/orders"])
