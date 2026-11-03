"""Explanations and serialisation for a scoring result"""

import pandas as pd

from health_score.scoring import registry
from health_score.scoring.scale import is_scored

NEUTRAL_SCORE = 50
TOP_DRIVERS = 3


def drivers(measures):
    """Strongest positive and negative contributions relative to a neutral 50"""
    impact = sorted(
        (
            {
                "measure": row["label"],
                "score": row["score"],
                "impact": round((row["score"] - NEUTRAL_SCORE) * row["weight_in_score"] / 100, 2),
            }
            for row in measures
        ),
        key=lambda d: d["impact"],
    )
    return {
        "positive": [d for d in reversed(impact) if d["impact"] > 0][:TOP_DRIVERS],
        "negative": [d for d in impact if d["impact"] < 0][:TOP_DRIVERS],
    }


def unavailable_measures(values):
    return [{"id": m.id, "label": m.label, "dimension": m.dimension} for m in registry.MEASURES if m.id not in values]


def pending_benchmarks(values):
    return [
        {"id": m.id, "label": m.label, "dimension": m.dimension, "value": round(values[m.id], 4), "unit": m.unit}
        for m in registry.MEASURES
        if not is_scored(m) and m.id in values
    ]


def sort_measures(measures):
    order = list(registry.DIMENSIONS)
    return sorted(measures, key=lambda r: (order.index(r["dimension"]), -r["weight_in_score"]))


def aging(data, report):
    totals = {}
    for aging_report in (data.reports.get(report) or {}).values():
        for bucket, amount in ((aging_report or {}).get("summary") or {}).items():
            if isinstance(amount, (int, float)):
                totals[bucket] = round(totals.get(bucket, 0) + amount, 2)
    return totals


def jsonable(obj):
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if hasattr(obj, "item"):
        return obj.item()
    return obj
