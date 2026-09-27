"""
Scoring engine for the business health score

Rule-based weighted scorecard:
    measure value -> 0-100 (piecewise-linear between Good and Poor)
    measures -> dimension score (weights re-normalized over available measures;
                supplier measures scaled by the tracking factor)
    dimensions -> overall score (fixed dimension weights)
    red flags cap the overall score
"""

from datetime import timedelta

import pandas as pd

from health_score.scoring import registry
from health_score.scoring.measures import compute_measures


def score_value(m, value):
    """Score a raw value 0-100 against the measure's thresholds"""
    if m.kind == "score":
        return max(0.0, min(100.0, value))
    if m.kind == "range":
        if m.good <= value <= m.good_high:
            return 100.0
        if value < m.good:
            return _linear(value, m.poor, m.good)
        return _linear(value, m.poor_high, m.good_high)
    return _linear(value, m.poor, m.good)


def _linear(value, poor, good):
    """100 at `good`, 0 at `poor`, linear in between; works in either direction"""
    if good == poor:
        return 100.0 if value == good else 0.0
    return max(0.0, min(100.0, (value - poor) / (good - poor) * 100.0))


def band(score):
    return next(name for floor, name in registry.BANDS if score >= floor)


def tracking_factor(context):
    share = (context.get("supplier_tracking") or {}).get("tracking_share")
    if share is None:
        return 1.0
    return registry.TRACKING_FACTOR_MIN + registry.TRACKING_FACTOR_SPAN * share


def score_measures(values, context, business_level=True):
    """Score every available measure and roll them up into dimensions and a total"""
    factor = tracking_factor(context)
    measures, dimensions = [], {}
    overall = 0.0
    available_weight = 0.0

    for dim, (label, dim_weight) in registry.DIMENSIONS.items():
        rows = []
        for m in registry.MEASURES:
            if m.dimension != dim or (m.business_only and not business_level) or m.id not in values:
                continue
            weight = m.weight * (factor if m.supplier else 1.0)
            rows.append(
                {
                    "id": m.id,
                    "label": m.label,
                    "dimension": dim,
                    "value": round(values[m.id], 4),
                    "unit": m.unit,
                    "score": round(score_value(m, values[m.id]), 1),
                    "base_weight": m.weight,
                    "weight": weight,
                    "supplier": m.supplier,
                }
            )
        total_w = sum(r["weight"] for r in rows)
        if rows:
            dim_score = sum(r["score"] * r["weight"] for r in rows) / total_w
            imputed = False
        else:
            dim_score, imputed = registry.IMPUTED_DIMENSION_SCORE, True
        for r in rows:
            r["weight_in_dimension"] = round(r["weight"] / total_w * 100, 1)
            r["weight_in_score"] = round(r["weight"] / total_w * dim_weight * 100, 2)
            r["weight"] = round(r["weight"], 3)
        dimensions[dim] = {
            "label": label,
            "weight": dim_weight,
            "score": round(dim_score, 1),
            "imputed": imputed,
            "measures_available": len(rows),
            "measures_total": sum(1 for m in registry.MEASURES if m.dimension == dim),
        }
        overall += dim_weight * dim_score
        available_weight += dim_weight * sum(r["base_weight"] for r in rows) / 100
        measures.extend(rows)

    return round(overall, 1), dimensions, measures, available_weight


def score_business(data, include_shops=True):
    """
    Score a business and each of its shops

    Args:
        data (BusinessData): collected data
        include_shops (bool): also score each shop and the shop network

    Returns:
        dict: full scoring result
    """
    values, context = compute_measures(data, business_level=True)
    shops = _score_shops(data) if include_shops else []
    network = _shop_network(shops)
    if network is not None:
        values["shop_network"] = network["score"]

    overall, dimensions, measures, available = score_measures(values, context)
    flags = _red_flags(values, context, shops)
    cap = min((f["cap"] for f in flags), default=100)
    final = min(overall, cap)

    imputed = [d for d, info in dimensions.items() if info["imputed"]]
    history = context["history_days"]
    publishable = history >= registry.MIN_ACTIVITY_DAYS and len(imputed) <= 1
    if not imputed and history >= 365 and available >= 0.60:
        confidence = "High"
    elif len(imputed) <= 1 and history >= 180:
        confidence = "Medium"
    else:
        confidence = "Low"

    return {
        "score": round(final, 1) if publishable else None,
        "score_uncapped": overall,
        "band": band(final) if publishable else "Insufficient data",
        "status": "scored" if publishable else "insufficient_data",
        "confidence": confidence,
        "products_used": context["products_in_use"],
        "measure_weight_available": round(available, 3),
        "dimensions": dimensions,
        "measures": sorted(
            measures, key=lambda r: (list(registry.DIMENSIONS).index(r["dimension"]), -r["weight_in_score"])
        ),
        "measures_not_available": [
            {"id": m.id, "label": m.label, "dimension": m.dimension} for m in registry.MEASURES if m.id not in values
        ],
        "red_flags": flags,
        "drivers": _drivers(measures),
        "shops": shops,
        "shop_network": network,
        "aging": {"receivables": _aging(data, "ar_aging"), "payables": _aging(data, "ap_aging")},
        "context": _jsonable(context),
    }


# ------------------------------------------------------------------ shops


def _score_shops(data):
    as_of = data.as_of
    tx = data.table("transactions")
    shops_df = data.table("shops")
    rev_t12_total = (
        float(tx[(tx["date"] > as_of - timedelta(days=365)) & (tx["date"] <= as_of)]["amount"].sum())
        if not tx.empty
        else 0
    )
    results = []
    for _, shop in shops_df.iterrows():
        sid = shop["shop_id"]
        stx = tx[tx["shop_id"] == sid] if not tx.empty else tx
        first = stx["date"].min() if not stx.empty else None
        last = stx["date"].max() if not stx.empty else None
        rev_t12 = (
            float(stx[(stx["date"] > as_of - timedelta(days=365)) & (stx["date"] <= as_of)]["amount"].sum())
            if not stx.empty
            else 0.0
        )
        rev_t3 = (
            float(stx[(stx["date"] > as_of - timedelta(days=90)) & (stx["date"] <= as_of)]["amount"].sum())
            if not stx.empty
            else 0.0
        )
        rev_p3 = (
            float(
                stx[(stx["date"] > as_of - timedelta(days=180)) & (stx["date"] <= as_of - timedelta(days=90))][
                    "amount"
                ].sum()
            )
            if not stx.empty
            else 0.0
        )
        if first is None:
            status = "no_sales"
        elif (as_of - first).days < registry.RAMP_UP_DAYS:
            status = "new"
        elif last is None or (as_of - last).days > 30:
            status = "dormant"
        else:
            status = "established"
        entry = {
            "shop_id": sid,
            "name": shop["name"],
            "pos_mode": shop["pos_mode"],
            "status": status,
            "revenue_t12m": round(rev_t12, 2),
            "revenue_share": round(rev_t12 / rev_t12_total, 4) if rev_t12_total else 0.0,
            "revenue_t3m": round(rev_t3, 2),
            "revenue_p3m": round(rev_p3, 2),
            "declining": rev_p3 > 0 and rev_t3 / rev_p3 - 1 <= -0.10,
            "score": None,
            "band": None,
        }
        if status in ("established", "dormant"):
            values, context = compute_measures(data.for_shop(sid), business_level=False)
            overall, dims, _, _ = score_measures(values, context, business_level=False)
            if sum(1 for d in dims.values() if d["imputed"]) <= 1:
                entry["score"], entry["band"] = overall, band(overall)
                entry["dimensions"] = {d: info["score"] for d, info in dims.items()}
        results.append(entry)
    return sorted(results, key=lambda s: -s["revenue_t12m"])


def _shop_network(shops):
    """Shop network measure: needs 2+ established or dormant shops"""
    mature = [s for s in shops if s["status"] in ("established", "dormant")]
    if len(mature) < 2:
        return None
    total = sum(s["revenue_t12m"] for s in mature) or 0
    weak_share = (
        sum(s["revenue_t12m"] for s in mature if s["score"] is not None and s["score"] < 50) / total if total else 0
    )
    top_share = max(s["revenue_t12m"] for s in mature) / total if total else 1
    declining = sum(1 for s in mature if s["declining"]) / len(mature)
    dormant = sum(1 for s in mature if s["status"] == "dormant") / len(mature)
    parts = {
        "weak_shop_revenue_share": (weak_share, _linear(weak_share, 0.50, 0.10)),
        "top_shop_share": (top_share, _linear(top_share, 0.85, 0.40)),
        "declining_shop_share": (declining, _linear(declining, 0.60, 0.20)),
        "dormant_shop_share": (dormant, _linear(dormant, 0.40, 0.0)),
    }
    return {
        "score": round(sum(s for _, s in parts.values()) / len(parts), 1),
        "parts": {k: {"value": round(v, 4), "score": round(s, 1)} for k, (v, s) in parts.items()},
        "shops_compared": len(mature),
    }


# -------------------------------------------------------------- red flags


def _red_flags(values, context, shops):
    flags = []
    rf = context["red_flag_inputs"]

    def add(flag, detail, cap):
        flags.append({"flag": flag, "detail": detail, "cap": cap})

    if (
        context["history_days"] >= 180
        and context["revenue_p3m"] > 0
        and context["revenue_t3m"] <= 0.5 * context["revenue_p3m"]
    ):
        add("Revenue collapse", "Last 3 months' revenue is at most half of the previous 3 months", 40)
    if rf.get("missed_payroll"):
        add("Missed payroll", "No completed payroll in the last 2 months", 40)
    if rf.get("ap_90_share") is not None and rf["ap_90_share"] >= 0.5:
        add("Severe supplier arrears", "Half or more of open bills are 90+ days past due", 40)
    if values.get("cash_runway") is not None and values["cash_runway"] < 1:
        add("Cash exhaustion", "Cash runway under 1 month", 45)
    for s in shops:
        if s["revenue_share"] >= 0.5 and s["revenue_p3m"] > 0 and s["revenue_t3m"] <= 0.5 * s["revenue_p3m"]:
            add("Flagship shop collapse", f"{s['name']} halved its revenue", 45)
    if rf.get("ar_120_share") is not None and rf["ar_120_share"] >= 0.4:
        add("Receivables write-off risk", "40%+ of receivables are 120+ days past due", 50)
    if values.get("top_customer_share") is not None and values["top_customer_share"] >= 0.7:
        add("Single-customer dependence", "One customer is 70%+ of revenue", 55)
    mature = [s for s in shops if s["status"] in ("established", "dormant")]
    if len(mature) >= 2 and sum(s["declining"] for s in mature) / len(mature) >= 0.6:
        add("Widespread shop decline", "60%+ of established shops are declining", 55)
    return flags


# --------------------------------------------------------------- outputs


def _drivers(measures):
    """Strongest positive and negative contributions relative to a neutral 50"""
    impact = sorted(
        (
            {
                "measure": r["label"],
                "score": r["score"],
                "impact": round((r["score"] - 50) * r["weight_in_score"] / 100, 2),
            }
            for r in measures
        ),
        key=lambda d: d["impact"],
    )
    return {
        "positive": [d for d in reversed(impact) if d["impact"] > 0][:3],
        "negative": [d for d in impact if d["impact"] < 0][:3],
    }


def _aging(data, report):
    """Aging buckets summed across shops"""
    totals = {}
    for rep in (data.reports.get(report) or {}).values():
        for bucket, amount in ((rep or {}).get("summary") or {}).items():
            if isinstance(amount, (int, float)):
                totals[bucket] = round(totals.get(bucket, 0) + amount, 2)
    return totals


def _jsonable(obj):
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if hasattr(obj, "item"):
        return obj.item()
    return obj
