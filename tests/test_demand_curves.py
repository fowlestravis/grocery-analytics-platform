"""Tests for the power-form demand curve math in scripts/generate_demand_curves.py."""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))

from generate_demand_curves import (  # noqa: E402
    analytical_optimum,
    calibrate_scale,
    demand_units,
    margin,
    price_grid,
)

# (avg_price, avg_daily_units, elasticity, cost) spanning inelastic to highly elastic
CASES = [
    (3.48, 196.73, -0.935, 2.02),   # 2% Milk
    (7.38, 148.00, -1.047, 4.93),   # Green Tea, barely elastic
    (2.45, 73.06, -1.835, 1.50),    # Coffee Beans
    (5.25, 113.38, -2.565, 3.57),   # Cookies
]
ELASTIC_CASES = [c for c in CASES if c[2] < -1]


@pytest.mark.parametrize("avg_price, avg_units, eps, cost", CASES)
def test_units_at_average_price_match_calibration(avg_price, avg_units, eps, cost):
    scale = calibrate_scale(avg_price, avg_units, eps)
    assert demand_units(avg_price, scale, eps) == pytest.approx(avg_units, rel=1e-9)


@pytest.mark.parametrize("avg_price, avg_units, eps, cost", CASES)
def test_units_decrease_as_price_increases(avg_price, avg_units, eps, cost):
    scale = calibrate_scale(avg_price, avg_units, eps)
    units = demand_units(price_grid(cost + 0.01, avg_price * 2), scale, eps)
    assert np.all(np.diff(units) < 0)


@pytest.mark.parametrize("avg_price, avg_units, eps, cost", ELASTIC_CASES)
def test_analytical_optimum_matches_numerical_argmax(avg_price, avg_units, eps, cost):
    scale = calibrate_scale(avg_price, avg_units, eps)
    p_star = analytical_optimum(cost, eps)
    # Fine grid well past the optimum (Green Tea's sits near 22 × cost)
    fine = np.arange(cost + 0.0001, p_star * 2, 0.0001)
    numerical = fine[np.argmax(margin(fine, scale, eps, cost))]
    assert abs(numerical - p_star) < 0.01


def test_no_analytical_optimum_when_inelastic():
    assert analytical_optimum(2.02, -0.935) is None
    assert analytical_optimum(2.02, -1.0) is None
