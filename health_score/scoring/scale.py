"""Turn a raw measure value into a 0-100 score, and a score into a band"""

from health_score.scoring import registry


def linear(value, poor, good):
    """100 at `good`, 0 at `poor`, a straight line between; works in either direction"""
    if good == poor:
        return 100.0 if value == good else 0.0
    return max(0.0, min(100.0, (value - poor) / (good - poor) * 100.0))


def thresholds(measure, sector="other"):
    if measure.sector_thresholds:
        return registry.GROSS_MARGIN_BY_SECTOR.get(sector, registry.GROSS_MARGIN_BY_SECTOR["other"])
    return measure.good, measure.poor


def score_value(measure, value, sector="other"):
    if measure.kind == "score":
        return max(0.0, min(100.0, value))
    if measure.kind == "range":
        if measure.good <= value <= measure.good_high:
            return 100.0
        if value < measure.good:
            return linear(value, measure.poor, measure.good)
        return linear(value, measure.poor_high, measure.good_high)
    good, poor = thresholds(measure, sector)
    return linear(value, poor, good)


def is_scored(measure):
    return measure.kind != "benchmark"


def band(score):
    return next(name for floor, name in registry.BANDS if score >= floor)
