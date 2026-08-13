"""Tests for the cusp-atlas domain mappers. stdlib unittest only.

The point of these mappers is calibration: each domain's own critical value must
land exactly on the detector's spinodal. That is the property worth pinning --
the rest is arithmetic.

Run:  python -m unittest cascade_regime_audit.tests.test_cusp_atlas
"""

import math
import unittest

from ..cascade_audit import H_SPINODAL, CascadeAudit, SignalReads
from ..examples.cusp_atlas import (
    allee_ratio,
    buckling_ratio,
    fishery_ratio,
    fracture_ratio,
    h_eff_from_ratio,
    semenov_ratio,
    thermohaline_ratio,
    van_der_waals_ratio,
    voltage_stability_ratio,
)


class TestScaleMapping(unittest.TestCase):
    def test_critical_ratio_lands_exactly_on_the_spinodal(self):
        self.assertAlmostEqual(h_eff_from_ratio(1.0), H_SPINODAL)

    def test_below_critical_is_below_the_spinodal(self):
        self.assertLess(h_eff_from_ratio(0.99), H_SPINODAL)

    def test_above_critical_is_past_the_spinodal(self):
        self.assertGreater(h_eff_from_ratio(1.01), H_SPINODAL)

    def test_monotonic(self):
        vals = [h_eff_from_ratio(r / 10.0) for r in range(0, 20)]
        self.assertEqual(vals, sorted(vals))

    def test_negative_ratio_clamps_to_zero(self):
        self.assertEqual(h_eff_from_ratio(-3.0), 0.0)

    def test_the_detector_agrees_at_the_boundary(self):
        audit = CascadeAudit()
        quiet = SignalReads()
        self.assertTrue(audit.audit(quiet, h_eff_from_ratio(1.0)).over_spinodal)
        self.assertFalse(audit.audit(quiet, h_eff_from_ratio(0.999)).over_spinodal)


class TestDomainCriticality(unittest.TestCase):
    """Each mapper must return 1.0 exactly at its field's own critical value."""

    def test_buckling_at_euler_load(self):
        e, i, length = 2.0e11, 8.3e-6, 6.0
        p_cr = (math.pi ** 2) * e * i / (length ** 2)
        self.assertAlmostEqual(buckling_ratio(p_cr, e, i, length), 1.0)

    def test_buckling_end_condition_matters(self):
        # A cantilever (K=2) buckles at a quarter of the pinned-pinned load.
        args = dict(youngs_modulus=2.0e11, second_moment=8.3e-6, length=6.0)
        pinned = buckling_ratio(1.0e5, end_condition=1.0, **args)
        cantilever = buckling_ratio(1.0e5, end_condition=2.0, **args)
        self.assertAlmostEqual(cantilever, 4.0 * pinned)

    def test_van_der_waals_critical_isotherm(self):
        self.assertEqual(van_der_waals_ratio(1.0), 0.0)
        self.assertEqual(van_der_waals_ratio(1.4), 0.0)   # supercritical
        self.assertGreater(van_der_waals_ratio(0.7), 0.0)

    def test_semenov_at_the_ignition_criterion(self):
        # psi_cr = 1/e; construct a release rate that hits it exactly.
        removal, activation, ambient = 42.0, 9500.0, 310.0
        theta = activation / ambient
        release = (1.0 / math.e) * removal * ambient * theta
        self.assertAlmostEqual(semenov_ratio(release, removal, activation, ambient),
                               1.0)

    def test_thermohaline_at_critical_flux(self):
        self.assertAlmostEqual(thermohaline_ratio(0.35, 0.35), 1.0)

    def test_allee_at_the_threshold(self):
        self.assertAlmostEqual(allee_ratio(500.0, 500.0), 1.0)

    def test_allee_inverts_because_the_danger_is_downward(self):
        # Falling *below* the threshold is what is critical, so the ratio rises
        # as the population falls.
        self.assertGreater(allee_ratio(250.0, 500.0), 1.0)
        self.assertLess(allee_ratio(2000.0, 500.0), 1.0)

    def test_allee_extinct_population_is_past_recovery(self):
        self.assertGreater(allee_ratio(0.0, 500.0), 1.0)

    def test_voltage_at_the_nose(self):
        self.assertAlmostEqual(voltage_stability_ratio(1.0, 1.0), 1.0)

    def test_fracture_at_toughness(self):
        self.assertAlmostEqual(fracture_ratio(52.0, 52.0), 1.0)

    def test_fishery_at_maximum_sustainable_yield(self):
        r, k = 0.42, 10000.0
        self.assertAlmostEqual(fishery_ratio(r * k / 4.0, r, k), 1.0)

    def test_fishery_msy_is_the_fold_not_a_safe_target(self):
        r, k = 0.42, 10000.0
        audit = CascadeAudit()
        at_msy = audit.audit(SignalReads(), h_eff_from_ratio(fishery_ratio(r * k / 4.0, r, k)))
        self.assertTrue(at_msy.over_spinodal)


class TestDegenerateInputs(unittest.TestCase):
    def test_zero_critical_values_do_not_divide_by_zero(self):
        self.assertEqual(thermohaline_ratio(1.0, 0.0), 0.0)
        self.assertEqual(voltage_stability_ratio(1.0, 0.0), 0.0)
        self.assertEqual(fracture_ratio(1.0, 0.0), 0.0)
        self.assertEqual(fishery_ratio(1.0, 0.0, 0.0), 0.0)
        self.assertEqual(semenov_ratio(1.0, 0.0, 1.0, 1.0), 0.0)
        self.assertEqual(buckling_ratio(1.0, 0.0, 0.0, 1.0), 0.0)


if __name__ == "__main__":
    unittest.main()
