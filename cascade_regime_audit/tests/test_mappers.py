"""Tests for the reference series->signal mappers. stdlib unittest only.

Run:  python -m unittest cascade_regime_audit.tests.test_mappers
"""

import unittest

from ..cascade_audit import SignalReads
from ..mappers import (
    abs_skew,
    coefficient_of_variation,
    lag1_autocorr,
    normalized_variance,
    sealing_under_contradiction,
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

    def test_sealing_needs_contradiction_to_respond_to(self):
        # A serene system that was never challenged is not evidence of sealing.
        self.assertEqual(
            sealing_under_contradiction(coherence_baseline=0.5,
                                        coherence_under_contradiction=1.0,
                                        contradiction_level=0.0), 0.0)

    def test_coherence_rising_under_contradiction_fires(self):
        s5 = sealing_under_contradiction(0.5, 0.9, 1.0)
        self.assertAlmostEqual(s5, 0.8)          # rose 0.4 of its 0.5 headroom

    def test_coherence_falling_under_contradiction_is_healthy(self):
        # The system met a contradiction and came apart a little while it worked
        # out which part of itself was wrong. That is not the pathology.
        self.assertEqual(sealing_under_contradiction(0.8, 0.4, 1.0), 0.0)

    def test_coherence_holding_is_not_sealing(self):
        self.assertEqual(sealing_under_contradiction(0.6, 0.6, 1.0), 0.0)

    def test_weak_contradiction_scales_the_signal_down(self):
        strong = sealing_under_contradiction(0.5, 0.9, 1.0)
        weak = sealing_under_contradiction(0.5, 0.9, 0.25)
        self.assertAlmostEqual(weak, strong * 0.25)

    def test_total_prior_agreement_has_no_headroom(self):
        # A system already at 1.0 cannot rise; that is S6's pathology, not S5's.
        self.assertEqual(sealing_under_contradiction(1.0, 1.0, 1.0), 0.0)

    def test_output_is_a_normalized_pressure(self):
        for base, under, level in ((0.0, 1.0, 1.0), (0.1, 0.99, 1.0),
                                   (0.5, 0.51, 0.9), (0.2, 0.2, 0.3)):
            v = sealing_under_contradiction(base, under, level)
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)

    def test_out_of_range_inputs_rejected(self):
        for args in ((1.5, 0.5, 0.5), (0.5, -0.1, 0.5), (0.5, 0.5, 2.0)):
            with self.assertRaises(ValueError):
                sealing_under_contradiction(*args)

    def test_feeds_the_detector_as_signal_five(self):
        s5 = sealing_under_contradiction(0.55, 0.95, 0.8)
        reads = SignalReads(coherence_under_contradiction=s5)
        self.assertEqual(reads.as_dict()["coherence_under_contradiction"], s5)

    def test_coefficient_of_variation(self):
        self.assertEqual(coefficient_of_variation([5.0, 5.0, 5.0]), 0.0)
        self.assertGreater(coefficient_of_variation([1.0, 5.0, 1.0, 5.0]), 0.0)


if __name__ == "__main__":
    unittest.main()
