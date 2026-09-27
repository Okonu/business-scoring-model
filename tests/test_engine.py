"""Unit tests for measure scoring, bands and weights"""

import pytest

from health_score.scoring import registry, score_value
from health_score.scoring.engine import band, tracking_factor

M = registry.MEASURES_BY_ID


@pytest.mark.parametrize(
    ("measure", "value", "expected"),
    [
        ("revenue_growth", 0.10, 100),  # at Good
        ("revenue_growth", -0.30, 0),  # at Poor
        ("revenue_growth", -0.10, 50),  # halfway
        ("revenue_growth", 0.50, 100),  # better than Good is capped
        ("dso", 30, 100),  # lower is better
        ("dso", 200, 0),
        ("stock_cover", 30, 100),  # inside the good range
        ("stock_cover", 3, 0),
        ("stock_cover", 180, 0),
        ("stock_cover", 120, 50),
        ("ecosystem_depth", 80, 80),  # already a score
    ],
)
def test_score_value(measure, value, expected):
    assert score_value(M[measure], value) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("score", "expected"),
    [(100, "Strong"), (80, "Strong"), (79.9, "Healthy"), (50, "Watch"), (35, "Weak"), (0, "Distressed")],
)
def test_band(score, expected):
    assert band(score) == expected


def test_weights_sum_to_100_per_dimension():
    for dim in registry.DIMENSIONS:
        assert sum(m.weight for m in registry.MEASURES if m.dimension == dim) == pytest.approx(100)
    assert sum(w for _, w in registry.DIMENSIONS.values()) == pytest.approx(1)


@pytest.mark.parametrize(("share", "expected"), [(None, 1.0), (0.0, 0.75), (0.5, 1.0), (1.0, 1.25)])
def test_tracking_factor(share, expected):
    assert tracking_factor({"supplier_tracking": {"tracking_share": share}}) == pytest.approx(expected)
