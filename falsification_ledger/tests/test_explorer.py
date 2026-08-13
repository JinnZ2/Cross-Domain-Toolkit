"""Tests for the claim explorer. stdlib unittest only.

The half of this module that matters most is the half that refuses, so most of
these tests assert that no edit was proposed.

Run:  python -m unittest falsification_ledger.tests.test_explorer
"""

import unittest

from ..explorer import (
    PATTERNS,
    ClaimExplorer,
    Signature,
    classify_residuals,
    diagnose,
)
from ..ledger import Claim, Ledger


def linear(params, condition):
    return params["a"] * condition + params["b"]


def ledger(a=2.0, b=0.0):
    return Ledger(linear, Claim("y = a x + b", {"a": a, "b": b}))


def drive(led, oracle, conditions, tolerance=0.5):
    for c in conditions:
        led.record(condition=c, observed=oracle(c), tolerance=tolerance)
    return led


class TestClassifier(unittest.TestCase):
    """The classifier reads (condition, predicted, observed, residual, tol)."""

    def rows(self, pairs, tol=0.5):
        return [(c, p, o, o - p, tol) for c, p, o in pairs]

    def test_no_rows_is_unknown(self):
        self.assertEqual(classify_residuals([])[0], Signature.UNKNOWN)

    def test_all_inside_tolerance_is_holding(self):
        rows = self.rows([(1, 2.0, 2.1), (2, 4.0, 3.9)])
        self.assertEqual(classify_residuals(rows)[0], Signature.HOLDING)

    def test_one_refuted_row_has_no_shape(self):
        self.assertEqual(classify_residuals(self.rows([(1, 2.0, 9.0)]))[0],
                         Signature.UNKNOWN)

    def test_constant_ratio_is_scale(self):
        rows = self.rows([(1, 2.0, 5.0), (2, 4.0, 10.0), (3, 6.0, 15.0)])
        self.assertEqual(classify_residuals(rows)[0], Signature.SCALE)

    def test_constant_offset_is_bias(self):
        rows = self.rows([(1, 2.0, 9.0), (2, 4.0, 11.0), (3, 6.0, 13.0)])
        self.assertEqual(classify_residuals(rows)[0], Signature.BIAS)

    def test_monotone_signed_error_is_curvature(self):
        # A linear claim against a quadratic reality crosses zero, so the
        # magnitudes dip while the signed error runs away. Reading magnitudes
        # would miss this, which is the commonest case there is.
        rows = self.rows([(1, 2.0, 1.0), (2, 4.0, 4.0), (3, 6.0, 9.0),
                          (4, 8.0, 16.0)])
        self.assertEqual(classify_residuals(rows)[0], Signature.CURVATURE)

    def test_clean_split_is_threshold(self):
        rows = self.rows([(1, 2.0, 2.0), (2, 4.0, 4.0), (3, 6.0, 15.0),
                          (4, 8.0, 30.0)])
        self.assertEqual(classify_residuals(rows)[0], Signature.THRESHOLD)

    def test_an_inlier_among_failures_is_not_a_threshold(self):
        # A regime boundary is a clean split. One in-tolerance point sitting in
        # the middle of failures is scatter.
        rows = self.rows([(1, 2.0, 9.0), (2, 4.0, 4.0), (3, 6.0, 15.0),
                          (4, 8.0, 30.0)])
        self.assertNotEqual(classify_residuals(rows)[0], Signature.THRESHOLD)

    def test_alternating_sign_is_oscillation(self):
        rows = self.rows([(1, 2.0, 4.0), (2, 4.0, 2.0), (3, 6.0, 8.0),
                          (4, 8.0, 6.0), (5, 10.0, 12.0)])
        self.assertEqual(classify_residuals(rows)[0], Signature.OSCILLATION)

    def test_straddling_zero_and_barely_out_is_noise(self):
        rows = self.rows([(1, 2.0, 2.6), (2, 4.0, 3.45), (3, 6.0, 5.38),
                          (4, 8.0, 8.58), (5, 10.0, 10.61)])
        self.assertEqual(classify_residuals(rows)[0], Signature.NOISE)

    def test_non_scalar_conditions_still_classify(self):
        # physics_ledger uses tuple conditions; trend analysis needs a number,
        # so shapes that need an axis abstain rather than crash.
        rows = [((1.0, 2.0), 2.0, 9.0, 7.0, 0.5),
                ((3.0, 4.0), 4.0, 11.0, 7.0, 0.5),
                ((5.0, 6.0), 6.0, 13.0, 7.0, 0.5)]
        self.assertEqual(classify_residuals(rows)[0], Signature.BIAS)


class TestRefusals(unittest.TestCase):
    def test_holding_claim_gets_no_edit(self):
        led = drive(ledger(), lambda c: 2.0 * c, [1.0, 2.0, 3.0])
        d = diagnose(led, linear)
        self.assertFalse(d.edit_warranted)
        self.assertIn("not refuted", d.refusal)

    def test_curvature_gets_no_edit(self):
        led = drive(ledger(), lambda c: c * c, [1.0, 2.0, 3.0, 4.0, 5.0])
        d = diagnose(led, linear)
        self.assertEqual(d.signature, Signature.CURVATURE)
        self.assertFalse(d.edit_warranted)
        self.assertIn("not a parameter problem", d.refusal)

    def test_threshold_gets_no_edit_and_points_at_the_audit(self):
        def reality(c):
            return 2.0 * c if c <= 3.0 else 2.0 * c + 9.0 * (c - 3.0) ** 2
        led = drive(ledger(), reality, [1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        d = diagnose(led, linear)
        self.assertEqual(d.signature, Signature.THRESHOLD)
        self.assertFalse(d.edit_warranted)
        self.assertTrue(any("cascade_regime_audit" in p.try_this
                            for p in d.patterns))

    def test_oscillation_gets_no_edit(self):
        led = drive(ledger(),
                    lambda c: 2.0 * c + (2.0 if int(c) % 2 else -2.0),
                    [1.0, 2.0, 3.0, 4.0, 5.0])
        d = diagnose(led, linear)
        self.assertEqual(d.signature, Signature.OSCILLATION)
        self.assertFalse(d.edit_warranted)

    def test_no_kernel_means_diagnosis_only(self):
        led = drive(ledger(), lambda c: 5.0 * c, [1.0, 2.0, 3.0])
        d = diagnose(led)
        self.assertEqual(d.signature, Signature.SCALE)
        self.assertFalse(d.edit_warranted)
        self.assertIn("no kernel", d.refusal)

    def test_escape_hatch_pattern_stops_further_suggestions(self):
        # Two supersessions, neither surviving anything: the form is wrong.
        led = ledger()
        for _ in range(2):
            led.record(condition=1.0, observed=99.0, tolerance=0.5)
            led.refute({"a": led.claim.params["a"] + 1.0, "b": 0.0},
                       rationale="synthetic thrash")
        led.record(condition=1.0, observed=99.0, tolerance=0.5)
        led.record(condition=2.0, observed=198.0, tolerance=0.5)
        d = diagnose(led, linear)
        self.assertFalse(d.edit_warranted)
        self.assertIn("escape-hatch", d.refusal)

    def test_one_supersession_is_not_yet_a_pattern(self):
        # A claim refuted once and answered once is the protocol working.
        led = ledger()
        led.record(condition=1.0, observed=5.0, tolerance=0.5)
        led.refute({"a": 4.0, "b": 0.0}, rationale="answered once")
        drive(led, lambda c: 5.0 * c, [1.0, 2.0, 3.0])
        d = diagnose(led, linear)
        self.assertIsNone(d.refusal)
        self.assertTrue(d.edit_warranted)


class TestProposals(unittest.TestCase):
    def test_scale_proposal_recovers_the_true_gain(self):
        led = drive(ledger(), lambda c: 5.0 * c, [1.0, 2.0, 3.0, 4.0])
        d = diagnose(led, linear)
        self.assertEqual(d.signature, Signature.SCALE)
        self.assertEqual(d.proposed_param, "a")
        self.assertAlmostEqual(d.proposed_params["a"], 5.0, places=6)

    def test_bias_proposal_recovers_the_true_offset(self):
        led = drive(ledger(), lambda c: 2.0 * c + 7.0, [1.0, 2.0, 3.0, 4.0])
        d = diagnose(led, linear)
        self.assertEqual(d.signature, Signature.BIAS)
        self.assertEqual(d.proposed_param, "b")
        self.assertAlmostEqual(d.proposed_params["b"], 7.0, places=6)

    def test_only_one_parameter_ever_moves(self):
        # Moving one named number with a reason is a correction; moving all of
        # them until the residuals go quiet is fitting.
        led = drive(ledger(), lambda c: 5.0 * c, [1.0, 2.0, 3.0, 4.0])
        d = diagnose(led, linear)
        changed = [k for k, v in d.proposed_params.items()
                   if v != led.claim.params[k]]
        self.assertEqual(len(changed), 1)

    def test_a_kernel_that_raises_does_not_crash_the_search(self):
        def fragile(params, condition):
            if params["a"] > 100.0:
                raise ZeroDivisionError("nope")
            return params["a"] * condition
        led = Ledger(fragile, Claim("y = a x", {"a": 2.0}))
        drive(led, lambda c: 5.0 * c, [1.0, 2.0, 3.0])
        self.assertAlmostEqual(diagnose(led, fragile).proposed_params["a"], 5.0,
                               places=6)


class TestExploreLoop(unittest.TestCase):
    def test_scale_error_converges(self):
        led = ledger()
        trace = ClaimExplorer(led, linear, lambda c: 5.0 * c,
                              [1.0, 2.0, 3.0, 4.0], tolerance=0.5).explore()
        self.assertTrue(trace.converged)
        self.assertAlmostEqual(led.claim.params["a"], 5.0, places=6)

    def test_wrong_form_halts_without_touching_the_claim(self):
        led = ledger()
        trace = ClaimExplorer(led, linear, lambda c: c * c,
                              [1.0, 2.0, 3.0, 4.0, 5.0], tolerance=0.5).explore()
        self.assertFalse(trace.converged)
        self.assertIn("curvature", trace.outcome)
        self.assertEqual(led.claim.version, 1)   # never re-parameterized

    def test_history_survives_the_whole_exploration(self):
        led = ledger()
        ClaimExplorer(led, linear, lambda c: 5.0 * c, [1.0, 2.0, 3.0],
                      tolerance=0.5).explore()
        self.assertTrue(led.verify())

    def test_every_round_is_on_the_record(self):
        led = ledger()
        trace = ClaimExplorer(led, linear, lambda c: 5.0 * c, [1.0, 2.0],
                              tolerance=0.5).explore()
        self.assertGreater(len(led.entries), 0)
        self.assertGreaterEqual(len(trace.rounds), 1)
        for claim in led.claim_history[1:]:
            self.assertIn("explorer round", claim.rationale)

    def test_max_rounds_is_respected(self):
        # A moving target: nothing converges, so the loop must stop itself.
        state = {"n": 0}

        def moving(condition):
            state["n"] += 1
            return 2.0 * condition + state["n"] * 13.0
        trace = ClaimExplorer(ledger(), linear, moving, [1.0, 2.0, 3.0],
                              tolerance=0.5).explore(max_rounds=3)
        self.assertLessEqual(len(trace.rounds), 3)
        self.assertFalse(trace.converged)

    def test_summary_is_printable(self):
        led = ledger()
        trace = ClaimExplorer(led, linear, lambda c: 5.0 * c, [1.0, 2.0],
                              tolerance=0.5).explore()
        self.assertIn("outcome:", trace.summary())

    def test_rejects_bad_construction(self):
        with self.assertRaises(ValueError):
            ClaimExplorer(ledger(), linear, lambda c: c, [1.0], tolerance=0.0)
        with self.assertRaises(ValueError):
            ClaimExplorer(ledger(), linear, lambda c: c, [], tolerance=0.5)


class TestPatternCatalogue(unittest.TestCase):
    def test_every_diagnosable_signature_has_patterns(self):
        for signature in (Signature.BIAS, Signature.SCALE, Signature.CURVATURE,
                          Signature.THRESHOLD, Signature.OSCILLATION,
                          Signature.NOISE):
            with self.subTest(signature=signature):
                self.assertTrue(PATTERNS.get(signature))

    def test_patterns_name_fields_and_a_next_move(self):
        for patterns in PATTERNS.values():
            for p in patterns:
                self.assertTrue(p.shape and p.fields and p.try_this)


if __name__ == "__main__":
    unittest.main()
