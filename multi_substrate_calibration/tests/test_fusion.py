"""Tests for the pure fusion math. stdlib unittest only.

Run:  python -m unittest multi_substrate_calibration.tests.test_fusion
"""

import unittest

from ..fusion import (
    collapse_correlated,
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


class TestCollapseCorrelated(unittest.TestCase):
    def test_ungrouped_reads_pass_through_independent(self):
        reads = [(1.0, 0.8, ""), (2.0, 0.6, ""), (3.0, 0.4, "")]
        self.assertEqual(collapse_correlated(reads),
                         [(1.0, 0.8), (2.0, 0.6), (3.0, 0.4)])

    def test_shared_group_collapses_to_one_effective_read(self):
        reads = [(10.0, 0.8, "rail-a"), (10.0, 0.8, "rail-a")]
        collapsed = collapse_correlated(reads)
        self.assertEqual(len(collapsed), 1)
        self.assertEqual(collapsed[0], (10.0, 0.8))   # best of the group, not combined

    def test_group_confidence_is_the_best_member_not_the_product(self):
        collapsed = collapse_correlated([(5.0, 0.5, "g"), (5.0, 0.9, "g")])
        self.assertEqual(collapsed[0][1], 0.9)

    def test_group_value_is_the_confidence_weighted_centre(self):
        collapsed = collapse_correlated([(0.0, 0.1, "g"), (10.0, 0.9, "g")])
        self.assertAlmostEqual(collapsed[0][0], 9.0)

    def test_groups_are_independent_of_each_other(self):
        reads = [(1.0, 0.8, "a"), (1.0, 0.8, "a"), (1.0, 0.8, "b")]
        collapsed = collapse_correlated(reads)
        self.assertEqual(len(collapsed), 2)
        self.assertAlmostEqual(combine_independent([c for _, c in collapsed]), 0.96)

    def test_first_seen_group_order_is_preserved(self):
        reads = [(3.0, 0.5, "z"), (1.0, 0.5, "a"), (3.0, 0.5, "z")]
        self.assertEqual([v for v, _ in collapse_correlated(reads)], [3.0, 1.0])

    def test_all_zero_confidence_group_falls_back_to_plain_mean(self):
        collapsed = collapse_correlated([(2.0, 0.0, "g"), (4.0, 0.0, "g")])
        self.assertEqual(collapsed, [(3.0, 0.0)])

    def test_empty(self):
        self.assertEqual(collapse_correlated([]), [])


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
