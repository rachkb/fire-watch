"""Boundary tests for the risk rules (SRS 3.4). Run: python -m pytest tests -v"""
import pytest

from firewatch.inference.risk import get_risk_level


@pytest.mark.parametrize("cls, conf, expected", [
    # Fire
    ("Fire", 1.00, "High"),
    ("Fire", 0.80, "High"),          # 80% is inclusive
    ("Fire", 0.79, "Medium"),
    ("Fire", 0.60, "Medium"),        # 60% is inclusive
    ("Fire", 0.59, "Uncertain"),
    # Smoke
    ("Smoke", 0.80, "Medium"),
    ("Smoke", 0.79, "Low"),
    ("Smoke", 0.60, "Low"),
    ("Smoke", 0.59, "Uncertain"),
    # Non-Fire
    ("Non-Fire", 0.99, "None"),
    ("Non-Fire", 0.60, "None"),
    ("Non-Fire", 0.59, "Uncertain"),  # low confidence overrides the class (REQ-4.2)
    # Extremes and bad input
    ("Fire", 0.0, "Uncertain"),
    ("Banana", 0.95, "Uncertain"),    # unknown class never produces a real risk level
])
def test_risk_levels(cls, conf, expected):
    assert get_risk_level(cls, conf) == expected


def test_accepts_numpy_float():
    np = pytest.importorskip("numpy")             # Keras returns np.float32
    assert get_risk_level("Fire", np.float32(0.9)) == "High"