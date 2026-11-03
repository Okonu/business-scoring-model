"""Measures to dimension scores to an overall score (methodology section 2.1)"""

from dataclasses import dataclass

from health_score.scoring import registry
from health_score.scoring.scale import is_scored, score_value


@dataclass(frozen=True)
class Scorecard:
    overall: float
    dimensions: dict
    measures: list
    available_weight: float


def tracking_factor(context):
    share = (context.get("supplier_tracking") or {}).get("tracking_share")
    if share is None:
        return 1.0
    return registry.TRACKING_FACTOR_MIN + registry.TRACKING_FACTOR_SPAN * share


def credibility(measured_share):
    """Buhlmann credibility: full at half the dimension's weight measured, less below it"""
    return min(1.0, measured_share / registry.CREDIBILITY_FULL_WEIGHT)


def applicable(measure, values, business_level):
    return measure.id in values and is_scored(measure) and (business_level or not measure.business_only)


def score_scorecard(values, context, business_level=True):
    factor = tracking_factor(context)
    sector = context.get("sector", "other")
    dimensions, measures = {}, []
    overall = available = 0.0
    for dim, (label, dim_weight) in registry.DIMENSIONS.items():
        rows = [
            _measure_row(m, values[m.id], factor, sector)
            for m in registry.MEASURES
            if m.dimension == dim and applicable(m, values, business_level)
        ]
        measured, c, score = blend(rows)
        _attach_weights(rows, dim_weight, c)
        dimensions[dim] = _dimension(dim, label, dim_weight, rows, measured, c, score)
        measures.extend(rows)
        overall += dim_weight * score
        available += dim_weight * _measured_share(rows)
    return Scorecard(round(overall, 1), dimensions, measures, available)


def _measure_row(measure, value, factor, sector):
    return {
        "id": measure.id,
        "label": measure.label,
        "dimension": measure.dimension,
        "value": round(value, 4),
        "unit": measure.unit,
        "score": round(score_value(measure, value, sector), 1),
        "base_weight": measure.weight,
        "weight": measure.weight * (factor if measure.supplier else 1.0),
        "supplier": measure.supplier,
        "basis": measure.basis,
    }


def blend(rows):
    """Weighted measure average, pulled toward the peer median when little of the dimension is measured"""
    if not rows:
        return None, 0.0, registry.PEER_MEDIAN_DEFAULT
    measured = sum(r["score"] * r["weight"] for r in rows) / sum(r["weight"] for r in rows)
    c = credibility(_measured_share(rows))
    return measured, c, c * measured + (1 - c) * registry.PEER_MEDIAN_DEFAULT


def _measured_share(rows):
    return sum(r["base_weight"] for r in rows) / 100


def _dimension(dim, label, dim_weight, rows, measured, c, score):
    return {
        "label": label,
        "weight": dim_weight,
        "score": round(score, 1),
        "measured_score": round(measured, 1) if measured is not None else None,
        "credibility": round(c, 3),
        "measured_share": round(_measured_share(rows), 3),
        "imputed": not rows,
        "measures_available": len(rows),
        "measures_total": sum(1 for m in registry.MEASURES if m.dimension == dim),
    }


def _attach_weights(rows, dim_weight, c):
    total_weight = sum(r["weight"] for r in rows)
    for r in rows:
        share = r["weight"] / total_weight
        r["weight_in_dimension"] = round(share * 100, 1)
        r["weight_in_score"] = round(share * c * dim_weight * 100, 2)
        r["weight"] = round(r["weight"], 3)
