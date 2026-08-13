"""Tests for the pure fusion math. stdlib unittest only.

Run:  python -m unittest multi_substrate_calibration.tests.test_fusion
"""

import unittest

from ..fusion import (
    combine_independent,
    contradiction_drain,
    fuse_ground,
    weighted_mean,
)


class TestCombine(unittest.TestCase):
    def test_noisy_or_rewards_corroboration(self):
        self.assertAlmostEqual(combine_independent([0.8, 0.8]), 0.96)
        self.assertGreater(combine_independent([0.8, 0.8]), combine_independent([0.8]))

    def test_empty_is_zero(self):
        self.assertEqual(combine_independent([]), 0.0)

    def test_clamps_out_of_range(self):
        self.assertEqual(combine_independent([1.5]), 1.0)
        self.assertEqual(combine_independent([-0.5]), 0.0)


class TestWeightedMean(unittest.TestCase):
    def test_pulls_toward_high_weight(self):
        self.assertLess(weighted_mean([10.0, 20.0], [0.9, 0.1]), 15.0)

    def test_zero_weight_returns_none(self):
        self.assertIsNone(weighted_mean([1.0], [0.0]))


class TestFuseGround(unittest.TestCase):
    def test_returns_state_and_determinacy(self):
        state, det = fuse_ground([(5.0, 0.8), (5.0, 0.8)])
        self.assertAlmostEqual(state, 5.0)
        self.assertAlmostEqual(det, 0.96)


class TestContradictionDrain(unittest.TestCase):
    def test_agreement_no_drain(self):
        self.assertEqual(contradiction_drain([(5.0, 0.9)], 5.0, 1.0), 0.0)

    def test_far_confident_contradiction_drains_most(self):
        near = contradiction_drain([(7.0, 0.9)], 5.0, 1.0)
        far = contradiction_drain([(50.0, 0.9)], 5.0, 1.0)
        self.assertGreater(far, near)
        self.assertLess(far, 0.9)  # saturating: approaches but never reaches conf

    def test_worst_single_contradiction_wins(self):
        drain = contradiction_drain([(6.0, 0.5), (50.0, 0.9)], 5.0, 1.0)
        self.assertEqual(drain, contradiction_drain([(50.0, 0.9)], 5.0, 1.0))


if __name__ == "__main__":
    unittest.main()
