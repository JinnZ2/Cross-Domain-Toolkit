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

    def __init__(self, value, native, role=Role.GROUND, reliability=1.0,
                 correlation_group=""):
        super().__init__(Calibration(reliability=reliability))
        self.role = role
        self.correlation_group = correlation_group
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

    def test_modality_mismatch_rejected(self):
        # The sibling check to role: a reading tagged with a modality the
        # substrate never declared cannot enter the gate either.
        class Mislabelled(Substrate):
            modality = "thermal"
            role = Role.GROUND

            def read(self):
                return SubstrateReading(1.0, 0.9, Role.GROUND, "acoustic", "u")

        with self.assertRaises(ValueError):
            Mislabelled().bound_read()


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

    def test_gap_reports_shortfall_and_matches_the_reason(self):
        gate = DeterminacyGate(epsilon=0.1)
        deferred = gate.evaluate([_Stub(5.0, 0.5).bound_read()])
        self.assertAlmostEqual(deferred.gap, 0.4)          # (1 - 0.1) - 0.5
        self.assertIn(f"gap {deferred.gap:.3f}", deferred.reason)
        determinate = gate.evaluate([_Stub(5.0, 0.99).bound_read()])
        self.assertEqual(determinate.gap, 0.0)             # met: no shortfall


class TestCorrelatedGround(unittest.TestCase):
    """Corroboration must be earned by reads that could have failed separately.
    A substrate declaring a shared error source cannot buy determinacy twice."""

    def test_duplicated_read_does_not_flip_the_verdict(self):
        # The defect this guards: two probes on one power rail read 0.8, and
        # noisy-OR turned that into 0.96 -- DEFER became DETERMINATE on no new
        # evidence at all.
        gate = DeterminacyGate(epsilon=0.1)
        rail = [_Stub(300.0, 0.8, correlation_group="rail-a").bound_read()
                for _ in range(2)]
        res = gate.evaluate(rail)
        self.assertAlmostEqual(res.determinacy, 0.8)
        self.assertEqual(res.verdict, Verdict.DEFER)

    def test_polling_the_same_group_harder_changes_nothing(self):
        gate = DeterminacyGate(epsilon=0.1)
        one = gate.evaluate([_Stub(300.0, 0.8, correlation_group="g").bound_read()])
        many = gate.evaluate([_Stub(300.0, 0.8, correlation_group="g").bound_read()
                              for _ in range(8)])
        self.assertAlmostEqual(many.determinacy, one.determinacy)

    def test_independent_reads_still_corroborate(self):
        # The fix must not punish genuine independence: ungrouped reads keep the
        # noisy-OR credit they have always had.
        gate = DeterminacyGate(epsilon=0.1)
        res = gate.evaluate([_Stub(300.0, 0.8).bound_read(),
                             _Stub(300.0, 0.8).bound_read()])
        self.assertAlmostEqual(res.determinacy, 0.96)
        self.assertEqual(res.verdict, Verdict.DETERMINATE)

    def test_distinct_groups_are_independent_of_each_other(self):
        gate = DeterminacyGate(epsilon=0.1)
        res = gate.evaluate([
            _Stub(300.0, 0.8, correlation_group="rail-a").bound_read(),
            _Stub(300.0, 0.8, correlation_group="rail-a").bound_read(),
            _Stub(300.0, 0.8, correlation_group="rail-b").bound_read(),
        ])
        self.assertAlmostEqual(res.determinacy, 0.96)

    def test_counts_report_what_was_collapsed(self):
        gate = DeterminacyGate(epsilon=0.1)
        res = gate.evaluate([
            _Stub(300.0, 0.8, correlation_group="g").bound_read(),
            _Stub(300.0, 0.8, correlation_group="g").bound_read(),
            _Stub(300.0, 0.7).bound_read(),
        ])
        self.assertEqual(res.ground_count, 3)
        self.assertEqual(res.effective_ground_count, 2)
        self.assertEqual(res.collapsed_reads, 1)

    def test_nothing_collapsed_when_all_independent(self):
        gate = DeterminacyGate(epsilon=0.1)
        res = gate.evaluate([_Stub(1.0, 0.5).bound_read() for _ in range(3)])
        self.assertEqual(res.effective_ground_count, 3)
        self.assertEqual(res.collapsed_reads, 0)

    def test_group_still_pulls_the_state_estimate(self):
        # Collapsing confidence must not throw away the reads' information about
        # *where* the state is.
        gate = DeterminacyGate(epsilon=0.1)
        res = gate.evaluate([
            _Stub(10.0, 0.9, correlation_group="g").bound_read(),
            _Stub(20.0, 0.1, correlation_group="g").bound_read(),
        ])
        self.assertAlmostEqual(res.state_estimate, 11.0)

    def test_correlation_group_rides_on_the_reading(self):
        r = _Stub(1.0, 0.5, correlation_group="shared-clock").bound_read()
        self.assertEqual(r.correlation_group, "shared-clock")
        self.assertEqual(r.reading.correlation_group, "shared-clock")

    def test_default_is_independent(self):
        self.assertEqual(_Stub(1.0, 0.5).bound_read().correlation_group, "")


class TestZeroConfidenceGround(unittest.TestCase):
    """An unproven substrate (reliability -> 0) binds to zero confidence. There is
    then no weight to average, so there is no state estimate -- the gate must
    DEFER on that rather than crash or invent a state."""

    def _unproven(self, value, role=Role.GROUND):
        return _Stub(value, 1.0, role=role, reliability=0.0).bound_read()

    def test_defers_with_no_state_estimate(self):
        res = DeterminacyGate(epsilon=0.1).evaluate([self._unproven(300.0)])
        self.assertEqual(res.verdict, Verdict.DEFER)
        self.assertIsNone(res.state_estimate)
        self.assertEqual(res.determinacy, 0.0)
        self.assertIn("zero confidence", res.reason)

    def test_bounds_check_does_not_crash(self):
        gate = DeterminacyGate(epsilon=0.1, bounds=(0.0, 1000.0))
        self.assertEqual(gate.evaluate([self._unproven(300.0)]).verdict, Verdict.DEFER)

    def test_prediction_scoring_does_not_crash(self):
        gate = DeterminacyGate(epsilon=0.1, predict_tolerance=2.0)
        res = gate.evaluate([
            self._unproven(300.0),
            _Stub(500.0, 0.9, role=Role.PREDICT).bound_read(),
        ])
        self.assertEqual(res.verdict, Verdict.DEFER)
        self.assertEqual(res.predict_count, 1)

    def test_one_earned_read_still_anchors(self):
        # The zero-confidence path must not swallow a ground layer that has any
        # earned weight at all.
        gate = DeterminacyGate(epsilon=0.1)
        res = gate.evaluate([self._unproven(300.0), _Stub(310.0, 0.95).bound_read()])
        self.assertEqual(res.state_estimate, 310.0)


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
