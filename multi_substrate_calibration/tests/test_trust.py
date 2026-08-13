"""Tests for earned reliability. stdlib unittest only.

Run:  python -m unittest multi_substrate_calibration.tests.test_trust
"""

import unittest

from ..trust import (
    earned_reliability,
    eligible_for_ground,
    rank_substrates,
    reliability_interval,
)


class TestEarnedReliability(unittest.TestCase):
    def test_no_record_sits_at_the_prior(self):
        # Silence costs something: an untested substrate is not trusted at 1.0,
        # which is what Calibration() defaults to when reliability is asserted.
        self.assertEqual(earned_reliability(0, 0), 0.5)

    def test_a_perfect_short_record_is_not_perfect_reliability(self):
        self.assertAlmostEqual(earned_reliability(2, 0), 0.75)

    def test_a_perfect_long_record_approaches_one(self):
        self.assertGreater(earned_reliability(200, 0), 0.99)
        self.assertLess(earned_reliability(200, 0), 1.0)

    def test_evidence_moves_it_monotonically(self):
        rising = [earned_reliability(h, 10 - h) for h in range(11)]
        self.assertEqual(rising, sorted(rising))

    def test_misses_pull_it_down(self):
        self.assertLess(earned_reliability(5, 15), earned_reliability(15, 5))

    def test_always_within_the_unit_interval(self):
        for hits, misses in ((0, 0), (0, 500), (500, 0), (7, 3)):
            r = earned_reliability(hits, misses)
            self.assertGreaterEqual(r, 0.0)
            self.assertLessEqual(r, 1.0)

    def test_wider_prior_demands_more_evidence(self):
        weak = earned_reliability(3, 0)
        skeptical = earned_reliability(3, 0, prior_hits=5.0, prior_misses=5.0)
        self.assertLess(skeptical, weak)

    def test_negative_counts_rejected(self):
        with self.assertRaises(ValueError):
            earned_reliability(-1, 0)

    def test_improper_prior_rejected(self):
        with self.assertRaises(ValueError):
            earned_reliability(1, 1, prior_hits=0.0)


class TestInterval(unittest.TestCase):
    def test_thin_record_gives_a_wide_interval(self):
        lo_thin, hi_thin = reliability_interval(3, 1)
        lo_thick, hi_thick = reliability_interval(300, 100)
        self.assertGreater(hi_thin - lo_thin, hi_thick - lo_thick)

    def test_interval_brackets_the_mean(self):
        lo, hi = reliability_interval(20, 5)
        self.assertLessEqual(lo, earned_reliability(20, 5))
        self.assertGreaterEqual(hi, earned_reliability(20, 5))

    def test_clamped_to_the_unit_interval(self):
        lo, hi = reliability_interval(500, 0)
        self.assertGreaterEqual(lo, 0.0)
        self.assertLessEqual(hi, 1.0)


class TestEligibility(unittest.TestCase):
    def test_untested_substrate_cannot_anchor(self):
        self.assertFalse(eligible_for_ground(0, 0))

    def test_short_perfect_record_is_still_too_short(self):
        # 3/3 looks perfect and is three observations.
        self.assertFalse(eligible_for_ground(3, 0))

    def test_earned_record_qualifies(self):
        self.assertTrue(eligible_for_ground(18, 2))

    def test_long_bad_record_disqualifies(self):
        self.assertFalse(eligible_for_ground(5, 40))

    def test_floor_is_configurable(self):
        self.assertTrue(eligible_for_ground(6, 4, floor=0.5))
        self.assertFalse(eligible_for_ground(6, 4, floor=0.9))


class TestRanking(unittest.TestCase):
    def test_ranks_a_fleet_independently(self):
        ranked = rank_substrates({"a": (20, 0), "b": (10, 10), "c": (0, 20)})
        self.assertGreater(ranked["a"], ranked["b"])
        self.assertGreater(ranked["b"], ranked["c"])

    def test_one_substrate_does_not_affect_another(self):
        alone = rank_substrates({"a": (7, 3)})["a"]
        crowded = rank_substrates({"a": (7, 3), "b": (99, 0), "c": (0, 99)})["a"]
        self.assertEqual(alone, crowded)

    def test_empty_fleet(self):
        self.assertEqual(rank_substrates({}), {})


if __name__ == "__main__":
    unittest.main()
