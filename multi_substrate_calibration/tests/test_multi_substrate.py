"""Tests for the multi-substrate calibration protocol. stdlib unittest only.

Run:  python -m unittest multi_substrate_calibration.tests.test_multi_substrate
"""

import unittest

from ..substrate import (
    BoundReading,
    Calibration,
    Role,
    Substrate,
    SubstrateReading,
    make_reading,
)
from ..determinacy_gate import DeterminacyGate, Verdict


class _Stub(Substrate):
    modality = "stub"

    def __init__(self, value, native, role=Role.GROUND, reliability=1.0):
        super().__init__(Calibration(reliability=reliability))
        self.role = role
        self._value = value
        self._native = native

    def read(self):
        return make_reading(self, self._value, self._native)


class TestContract(unittest.TestCase):
    def test_native_confidence_bounds_enforced(self):
        with self.assertRaises(ValueError):
            SubstrateReading(1.0, 1.5, Role.GROUND, "x", "u")

    def test_binding_discounts_by_reliability(self):
        unproven = _Stub(1.0, 1.0, reliability=0.0)
        self.assertEqual(unproven.bound_read().bound_confidence, 0.0)
        proven = _Stub(1.0, 0.8, reliability=0.9)
        self.assertAlmostEqual(proven.bound_read().bound_confidence, 0.72)

    def test_make_reading_carries_declared_fields_and_provenance(self):
        s = _Stub(1.0, 0.5)
        r = make_reading(s, 2.0, 0.5, provenance={"sensor": "abc"})
        self.assertEqual(r.role, s.role)
        self.assertEqual(r.modality, s.modality)
        self.assertEqual(r.units, s.units)
        self.assertEqual(r.provenance["sensor"], "abc")

    def test_role_mismatch_rejected(self):
        # A substrate that emits a reading whose role contradicts its declared
        # role must be rejected by bound_read().
        class Liar(Substrate):
            modality = "stub"
            role = Role.GROUND

            def read(self):
                return SubstrateReading(1.0, 0.9, Role.PREDICT, "stub", "u")

        with self.assertRaises(ValueError):
            Liar().bound_read()


class TestGate(unittest.TestCase):
    def test_no_ground_defers(self):
        gate = DeterminacyGate(epsilon=0.1)
        res = gate.evaluate([_Stub(5.0, 0.9, role=Role.PREDICT).bound_read()])
        self.assertEqual(res.verdict, Verdict.DEFER)
        self.assertIsNone(res.state_estimate)

    def test_nonpositive_predict_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            DeterminacyGate(epsilon=0.1, predict_tolerance=0.0)
        with self.assertRaises(ValueError):
            DeterminacyGate(epsilon=0.1, predict_tolerance=-2.0)

    def test_agreeing_prediction_does_not_inflate_determinacy(self):
        # An agreeing PREDICT read must not manufacture determinacy the ground
        # did not earn (it may only avoid draining it).
        gate = DeterminacyGate(epsilon=0.1, predict_tolerance=2.0)
        ground_only = gate.evaluate([_Stub(5.0, 0.7).bound_read()])
        with_agree = gate.evaluate(
            [_Stub(5.0, 0.7).bound_read(),
             _Stub(5.0, 0.95, role=Role.PREDICT).bound_read()]
        )
        self.assertAlmostEqual(with_agree.determinacy, ground_only.determinacy)
        self.assertEqual(with_agree.conflict, 0.0)

    def test_corroboration_raises_determinacy(self):
        gate = DeterminacyGate(epsilon=0.1)
        one = gate.evaluate([_Stub(5.0, 0.8).bound_read()]).determinacy
        two = gate.evaluate(
            [_Stub(5.0, 0.8).bound_read(), _Stub(5.0, 0.8).bound_read()]
        ).determinacy
        self.assertGreater(two, one)

    def test_confident_contradiction_drains_and_defers(self):
        gate = DeterminacyGate(epsilon=0.05, predict_tolerance=1.0)
        ground = [_Stub(5.0, 0.95).bound_read(), _Stub(5.0, 0.95).bound_read()]
        far_predict = _Stub(50.0, 0.95, role=Role.PREDICT).bound_read()
        res = gate.evaluate(ground + [far_predict])
        self.assertGreater(res.conflict, 0.0)
        self.assertEqual(res.verdict, Verdict.DEFER)

    def test_weighted_state_estimate(self):
        gate = DeterminacyGate(epsilon=0.1)
        # higher-confidence read pulls the estimate toward its value
        res = gate.evaluate(
            [_Stub(10.0, 0.9).bound_read(), _Stub(20.0, 0.1).bound_read()]
        )
        self.assertLess(res.state_estimate, 15.0)


class TestGrounding(unittest.TestCase):
    """5.2 grounding: unit commensurability and lower-layer bounds."""

    def test_mixed_ground_units_rejected(self):
        gate = DeterminacyGate(epsilon=0.1)
        a = BoundReading(SubstrateReading(1.0, 0.9, Role.GROUND, "m", "K"), 0.9)
        b = BoundReading(SubstrateReading(1.0, 0.9, Role.GROUND, "m", "C"), 0.9)
        with self.assertRaises(ValueError):
            gate.evaluate([a, b])

    def test_predict_stray_units_rejected(self):
        gate = DeterminacyGate(epsilon=0.1)
        g = BoundReading(SubstrateReading(1.0, 0.9, Role.GROUND, "m", "K"), 0.9)
        p = BoundReading(SubstrateReading(1.0, 0.9, Role.PREDICT, "m", "dB"), 0.9)
        with self.assertRaises(ValueError):
            gate.evaluate([g, p])

    def test_bounds_escape_defers(self):
        gate = DeterminacyGate(epsilon=0.1, bounds=(0.0, 10.0))
        g = BoundReading(SubstrateReading(50.0, 0.99, Role.GROUND, "m", "K"), 0.99)
        res = gate.evaluate([g])
        self.assertEqual(res.verdict, Verdict.DEFER)
        self.assertIn("bounds", res.reason)

    def test_bounds_within_is_fine(self):
        gate = DeterminacyGate(epsilon=0.1, bounds=(0.0, 10.0))
        g = BoundReading(SubstrateReading(5.0, 0.99, Role.GROUND, "m", "K"), 0.99)
        self.assertEqual(gate.evaluate([g]).verdict, Verdict.DETERMINATE)

    def test_inverted_bounds_rejected(self):
        with self.assertRaises(ValueError):
            DeterminacyGate(bounds=(10.0, 0.0))


if __name__ == "__main__":
    unittest.main()
