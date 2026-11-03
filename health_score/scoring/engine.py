"""Score a business: measures, shops, scorecard, red flags, publishing rules and confidence"""

from health_score.scoring import registry
from health_score.scoring.aggregation import score_scorecard
from health_score.scoring.measures import compute_measures
from health_score.scoring.red_flags import overall_cap, red_flags
from health_score.scoring.report import (
    aging,
    drivers,
    jsonable,
    pending_benchmarks,
    sort_measures,
    unavailable_measures,
)
from health_score.scoring.scale import band
from health_score.scoring.shops import score_shops, shop_network

HIGH_CONFIDENCE_HISTORY_DAYS = 365
MEDIUM_CONFIDENCE_HISTORY_DAYS = 180
HIGH_CONFIDENCE_MEASURED_WEIGHT = 0.60


def score_business(data, include_shops=True):
    values, context = compute_measures(data, business_level=True)
    shops = score_shops(data) if include_shops else []
    network = shop_network(shops)
    if network is not None:
        values["shop_network"] = network["score"]

    card = score_scorecard(values, context)
    flags = red_flags(values, context, shops)
    final = min(card.overall, overall_cap(flags))
    imputed = [dim for dim, info in card.dimensions.items() if info["imputed"]]
    published = publishable(context["history_days"], imputed)

    return {
        "score": round(final, 1) if published else None,
        "score_uncapped": card.overall,
        "band": band(final) if published else "Insufficient data",
        "status": "scored" if published else "insufficient_data",
        "confidence": confidence(context["history_days"], imputed, card.available_weight),
        "products_used": context["products_in_use"],
        "measure_weight_available": round(card.available_weight, 3),
        "dimensions": card.dimensions,
        "measures": sort_measures(card.measures),
        "measures_not_available": unavailable_measures(values),
        "measures_pending_benchmark": pending_benchmarks(values),
        "red_flags": flags,
        "drivers": drivers(card.measures),
        "shops": shops,
        "shop_network": network,
        "aging": {"receivables": aging(data, "ar_aging"), "payables": aging(data, "ap_aging")},
        "context": jsonable(context),
    }


def publishable(history_days, imputed):
    return history_days >= registry.MIN_ACTIVITY_DAYS and len(imputed) <= registry.MAX_IMPUTED_DIMENSIONS


def confidence(history_days, imputed, available_weight):
    if (
        not imputed
        and history_days >= HIGH_CONFIDENCE_HISTORY_DAYS
        and available_weight >= HIGH_CONFIDENCE_MEASURED_WEIGHT
    ):
        return "High"
    if len(imputed) <= registry.MAX_IMPUTED_DIMENSIONS and history_days >= MEDIUM_CONFIDENCE_HISTORY_DAYS:
        return "Medium"
    return "Low"
