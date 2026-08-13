"""Tests for the reference series->signal mappers. stdlib unittest only.

Run:  python -m unittest cascade_regime_audit.tests.test_mappers
"""

import unittest

from ..mappers import (
    abs_skew,
    coefficient_of_variation,
    lag1_autocorr,
    normalized_variance,
)


class TestMappers(unittest.TestCase):
    def test_lag1_autocorr_range_and_short_series(self):
        self.assertEqual(lag1_autocorr([1.0]), 0.0)          # too short
        persistent = lag1_autocorr([1.0, 1.1, 1.2, 1.3, 1.4])
        alternating = lag1_autocorr([1.0, -1.0, 1.0, -1.0, 1.0])
        self.assertGreater(persistent, alternating)
        self.assertGreaterEqual(persistent, 0.0)
        self.assertLessEqual(persistent, 1.0)

    def test_normalized_variance_baseline_is_zero(self):
        self.assertEqual(normalized_variance([1.0, 1.0, 1.0], 0.3), 0.0)

    def test_normalized_variance_rises_and_saturates(self):
        v = normalized_variance([-5.0, 5.0, -5.0, 5.0], 0.3)
        self.assertGreater(v, 0.5)
        self.assertLessEqual(v, 1.0)

    def test_abs_skew_symmetric_is_low(self):
        symmetric = abs_skew([-2.0, -1.0, 0.0, 1.0, 2.0])
        skewed = abs_skew([0.0, 0.0, 0.0, 0.0, 10.0])
        self.assertLess(symmetric, skewed)
        self.assertGreaterEqual(symmetric, 0.0)
        self.assertLessEqual(skewed, 1.0)

    def test_coefficient_of_variation(self):
        self.assertEqual(coefficient_of_variation([5.0, 5.0, 5.0]), 0.0)
        self.assertGreater(coefficient_of_variation([1.0, 5.0, 1.0, 5.0]), 0.0)


if __name__ == "__main__":
    unittest.main()
