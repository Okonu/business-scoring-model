"""Shop-level scores and the shop network measure (methodology table 10)"""

from datetime import timedelta

from health_score.scoring import registry
from health_score.scoring.aggregation import score_scorecard
from health_score.scoring.measures import compute_measures
from health_score.scoring.scale import band, linear

MATURE = ("established", "dormant")


def score_shops(data):
    tx = data.table("transactions")
    total_t12 = _revenue(tx, data.as_of, 365)
    shops = [_shop(data, shop, tx, total_t12) for _, shop in data.table("shops").iterrows()]
    return sorted(shops, key=lambda s: -s["revenue_t12m"])


def mature_shops(shops):
    return [s for s in shops if s["status"] in MATURE]


def shop_network(shops):
    mature = mature_shops(shops)
    if len(mature) < registry.MIN_SHOPS_FOR_NETWORK:
        return None
    total = sum(s["revenue_t12m"] for s in mature)
    observed = {
        "weak_shop_revenue_share": (
            sum(s["revenue_t12m"] for s in mature if s["score"] is not None and s["score"] < registry.WEAK_SHOP_SCORE)
            / total
            if total
            else 0.0
        ),
        "top_shop_share": max(s["revenue_t12m"] for s in mature) / total if total else 1.0,
        "declining_shop_share": sum(1 for s in mature if s["declining"]) / len(mature),
        "dormant_shop_share": sum(1 for s in mature if s["status"] == "dormant") / len(mature),
    }
    parts = {
        name: {"value": round(value, 4), "score": round(_part_score(name, value), 1)}
        for name, value in observed.items()
    }
    return {
        "score": round(sum(p["score"] for p in parts.values()) / len(parts), 1),
        "parts": parts,
        "shops_compared": len(mature),
    }


def _part_score(name, value):
    good, poor = registry.SHOP_NETWORK[name]
    return linear(value, poor, good)


def _revenue(tx, as_of, days, until_days=0):
    if tx.empty:
        return 0.0
    window = tx[(tx["date"] > as_of - timedelta(days=days)) & (tx["date"] <= as_of - timedelta(days=until_days))]
    return float(window["amount"].sum())


def _status(first, last, as_of):
    if first is None:
        return "no_sales"
    if (as_of - first).days < registry.RAMP_UP_DAYS:
        return "new"
    if (as_of - last).days > registry.SHOP_DORMANT_DAYS:
        return "dormant"
    return "established"


def _shop(data, shop, tx, total_t12):
    as_of = data.as_of
    shop_tx = tx[tx["shop_id"] == shop["shop_id"]] if not tx.empty else tx
    first = shop_tx["date"].min() if not shop_tx.empty else None
    last = shop_tx["date"].max() if not shop_tx.empty else None
    t12, t3, p3 = _revenue(shop_tx, as_of, 365), _revenue(shop_tx, as_of, 90), _revenue(shop_tx, as_of, 180, 90)
    entry = {
        "shop_id": shop["shop_id"],
        "name": shop["name"],
        "pos_mode": shop["pos_mode"],
        "status": _status(first, last, as_of),
        "revenue_t12m": round(t12, 2),
        "revenue_share": round(t12 / total_t12, 4) if total_t12 else 0.0,
        "revenue_t3m": round(t3, 2),
        "revenue_p3m": round(p3, 2),
        "declining": p3 > 0 and t3 / p3 - 1 <= registry.SHOP_DECLINE,
        "score": None,
        "band": None,
    }
    if entry["status"] in MATURE:
        entry.update(_shop_score(data.for_shop(shop["shop_id"])))
    return entry


def _shop_score(shop_data):
    values, context = compute_measures(shop_data, business_level=False)
    card = score_scorecard(values, context, business_level=False)
    if sum(1 for d in card.dimensions.values() if d["imputed"]) > registry.MAX_IMPUTED_DIMENSIONS:
        return {}
    return {
        "score": card.overall,
        "band": band(card.overall),
        "dimensions": {dim: info["score"] for dim, info in card.dimensions.items()},
    }
