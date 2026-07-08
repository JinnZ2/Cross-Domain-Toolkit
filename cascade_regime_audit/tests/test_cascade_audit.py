"""Tests for the abstract cascade-regime audit. stdlib unittest only.

Run:  python -m unittest cascade_regime_audit.tests.test_cascade_audit
"""

import math
import unittest

from ..cascade_audit import (
    CascadeAudit,
    H_SPINODAL,
    Regime,
    SignalReads,
    slowing_down_from_series,
    variance_inflation_from_series,
)


class TestSpinodalConstant(unittest.TestCase):
    def test_cusp_value(self):
        self.assertAlmostEqual(H_SPINODAL, 2.0 / math.sqrt(27.0))
        self.assertAlmostEqual(H_SPINODAL, 0.384900, places=5)


class TestSignals(unittest.TestCase):
    def test_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            SignalReads(critical_slowing_down=1.5)

    def test_missing_signals_abstain(self):
        # a partly-instrumented domain still runs; zeros just don't add pressure
        audit = CascadeAudit()
        r = audit.audit(SignalReads(variance_inflation=0.8), h_eff=0.1)
        self.assertLess(r.pressure, 0.5)


class TestRegimes(unittest.TestCase):
    def setUp(self):
        self.audit = CascadeAudit(fire_threshold=0.6, pressure_threshold=0.5)
        self.hot = SignalReads(0.8, 0.8, 0.8, 0.8, 0.8, 0.8)
        self.cold = SignalReads(0.1, 0.1, 0.1, 0.1, 0.1, 0.1)

    def test_stable(self):
        r = self.audit.audit(self.cold, h_eff=0.1)
        self.assertEqual(r.regime, Regime.STABLE)

    def test_stressed_below_spinodal(self):
        r = self.audit.audit(self.hot, h_eff=0.2)
        self.assertEqual(r.regime, Regime.STRESSED)
        self.assertFalse(r.over_spinodal)
        self.assertGreater(r.distance_to_spinodal, 0.0)

    def test_committed_calm_stats_past_spinodal(self):
        r = self.audit.audit(self.cold, h_eff=0.5)
        self.assertEqual(r.regime, Regime.COMMITTED)
        self.assertTrue(r.over_spinodal)

    def test_cascade_hot_and_past_spinodal(self):
        r = self.audit.audit(self.hot, h_eff=0.5)
        self.assertEqual(r.regime, Regime.CASCADE)
        self.assertEqual(len(r.fired), 6)
        self.assertLess(r.distance_to_spinodal, 0.0)

    def test_weights_shift_pressure(self):
        # weighting only the coherence-under-contradiction signal
        w = {n: 0.0 for n in SignalReads().as_dict()}
        w["coherence_under_contradiction"] = 1.0
        audit = CascadeAudit(weights=w)
        sig = SignalReads(coherence_under_contradiction=0.9)
        self.assertAlmostEqual(audit.audit(sig, 0.1).pressure, 0.9)


class TestConstruction(unittest.TestCase):
    def test_out_of_range_thresholds_rejected(self):
        with self.assertRaises(ValueError):
            CascadeAudit(fire_threshold=1.5)
        with self.assertRaises(ValueError):
            CascadeAudit(pressure_threshold=-0.1)

    def test_nonpositive_spinodal_rejected(self):
        with self.assertRaises(ValueError):
            CascadeAudit(spinodal=0.0)

    def test_unknown_weight_key_rejected(self):
        with self.assertRaises(ValueError):
            CascadeAudit(weights={"vareince_inflation": 1.0})  # typo

    def test_all_zero_weights_rejected(self):
        with self.assertRaises(ValueError):
            CascadeAudit(weights={n: 0.0 for n in SignalReads().as_dict()})


class TestHelpers(unittest.TestCase):
    def test_slowing_down_high_for_persistent_series(self):
        rising = [1.0, 1.1, 1.15, 1.22, 1.3, 1.4]
        noisy = [1.0, -1.0, 1.0, -1.0, 1.0, -1.0]
        self.assertGreater(slowing_down_from_series(rising),
                           slowing_down_from_series(noisy))

    def test_variance_inflation_rises_with_variance(self):
        baseline = [0.0, 1.0, 0.0, 1.0, 0.0, 1.0]  # var ~0.3
        bvar = 0.3
        calm = variance_inflation_from_series([0.5, 0.5, 0.5, 0.5], bvar)
        wild = variance_inflation_from_series([-5.0, 5.0, -5.0, 5.0], bvar)
        self.assertEqual(calm, 0.0)
        self.assertGreater(wild, 0.5)
        self.assertLessEqual(wild, 1.0)


if __name__ == "__main__":
    unittest.main()
