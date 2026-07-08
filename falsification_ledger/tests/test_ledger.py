"""Tests for the falsification ledger. stdlib unittest only.

Run:  python -m unittest falsification_ledger.tests.test_ledger
"""

import json
import unittest

from ..ledger import Claim, Ledger, RefutationError, classify_falsifiability


def linear(params, condition):
    return params["a"] * condition + params["b"]


class TestProtocol(unittest.TestCase):
    def _ledger(self):
        return Ledger(linear, Claim("y = a x + b", {"a": 2.0, "b": 0.0}))

    def test_within_tolerance_is_not_refuted(self):
        led = self._ledger()
        e = led.record(3.0, observed=6.05, tolerance=0.2)
        self.assertFalse(e.mismatch.refuted)

    def test_cannot_refute_a_claim_that_holds(self):
        led = self._ledger()
        led.record(3.0, observed=6.0, tolerance=0.2)  # perfect fit
        with self.assertRaises(RefutationError):
            led.refute({"a": 3.0, "b": 0.0}, rationale="no reason")

    def test_refutation_advances_version_and_keeps_history(self):
        led = self._ledger()
        e = led.record(3.0, observed=15.0, tolerance=0.5)  # way off
        self.assertTrue(e.mismatch.refuted)
        c = led.refute({"a": 5.0, "b": 0.0}, rationale="entry 0: slope wrong")
        self.assertEqual(c.version, 2)
        self.assertEqual(c.parent, 1)
        # the refuting entry still records the OLD claim, forever
        self.assertEqual(led.entries[0].claim.version, 1)

    def test_cannot_refute_before_any_observation(self):
        led = self._ledger()
        with self.assertRaises(RefutationError):
            led.refute({"a": 1.0, "b": 0.0}, rationale="premature")

    def test_hash_chain_detects_tampering(self):
        led = self._ledger()
        led.record(3.0, observed=15.0, tolerance=0.5)
        led.refute({"a": 5.0, "b": 0.0}, rationale="entry 0")
        led.record(2.0, observed=10.0, tolerance=0.5)
        self.assertTrue(led.verify())
        # quietly retune a past prediction to fit reality -> chain breaks, because
        # the stored hash was computed over the original value.
        object.__setattr__(led._entries[0].prediction, "value", 15.0)
        self.assertFalse(led.verify())

    def test_new_claim_changes_future_predictions_only(self):
        led = self._ledger()
        led.record(3.0, observed=15.0, tolerance=0.5)
        led.refute({"a": 5.0, "b": 0.0}, rationale="entry 0")
        pred = led.predict(3.0, tolerance=0.5)
        self.assertEqual(pred.value, 15.0)  # uses new params
        self.assertEqual(pred.claim_version, 2)

    def test_restate_revises_statement_and_keeps_history_intact(self):
        led = self._ledger()
        led.record(3.0, observed=15.0, tolerance=0.5)
        c = led.restate("y = a x + b (revised)", {"a": 5.0, "b": 0.0},
                        rationale="entry 0: form was mis-stated")
        self.assertEqual(c.version, 2)
        self.assertEqual(c.parent, 1)
        self.assertEqual(c.statement, "y = a x + b (revised)")
        self.assertEqual(led.claim_history[-1].statement, "y = a x + b (revised)")
        self.assertEqual(len(led.claim_history), 2)
        self.assertTrue(led.verify())

    def test_restate_requires_a_refutation(self):
        led = self._ledger()
        led.record(3.0, observed=6.0, tolerance=0.2)  # within tolerance
        with self.assertRaises(RefutationError):
            led.restate("new", {"a": 3.0, "b": 0.0}, rationale="no reason")

    def test_to_json_round_trips_and_reflects_history(self):
        led = self._ledger()
        led.record((3.0), observed=15.0, tolerance=0.5)
        led.refute({"a": 5.0, "b": 0.0}, rationale="entry 0")
        led.record(2.0, observed=10.0, tolerance=0.5)
        data = json.loads(led.to_json())
        self.assertEqual(len(data["entries"]), 2)
        self.assertEqual(len(data["claim_history"]), 2)
        self.assertEqual(data["entries"][0]["hash"], led.entries[0].hash)
        self.assertEqual(data["entries"][1]["prev_hash"], led.entries[0].hash)

    def test_external_dict_mutation_does_not_alter_claim(self):
        params = {"a": 2.0, "b": 0.0}
        led = Ledger(linear, Claim("y = a x + b", params))
        params["a"] = 999.0  # mutate the dict we passed in
        self.assertEqual(led.claim.params["a"], 2.0)


class TestFalsifiability(unittest.TestCase):
    def test_classifier(self):
        vague = Claim("vague", {"a": 1.0})
        testable = Claim("testable", {"a": 1.0}, refutation_set=["obs>5 at x=2"])
        self.assertFalse(vague.is_falsifiable)
        self.assertTrue(testable.is_falsifiable)
        self.assertFalse(classify_falsifiability(vague)["falsifiable"])
        self.assertTrue(classify_falsifiability(testable)["falsifiable"])

    def test_extraordinary_needs_more_than_one_condition(self):
        thin = Claim("revolution", {"a": 1.0}, refutation_set=["one"], extraordinary=True)
        thick = Claim("revolution", {"a": 1.0},
                      refutation_set=["one", "two"], extraordinary=True)
        self.assertFalse(classify_falsifiability(thin)["falsifiable"])
        self.assertTrue(classify_falsifiability(thick)["falsifiable"])

    def test_strict_mode_rejects_unfalsifiable_claim(self):
        with self.assertRaises(RefutationError):
            Ledger(linear, Claim("vague", {"a": 2.0, "b": 0.0}),
                   strict_falsifiable=True)

    def test_strict_mode_accepts_falsifiable_claim(self):
        led = Ledger(linear, Claim("y = a x + b", {"a": 2.0, "b": 0.0},
                                   refutation_set=["y != 6 at x=3"]),
                     strict_falsifiable=True)
        self.assertTrue(led.claim.is_falsifiable)

    def test_refutation_set_propagates_across_refute(self):
        led = Ledger(linear, Claim("y = a x + b", {"a": 2.0, "b": 0.0},
                                   refutation_set=["y != 6 at x=3"]),
                     strict_falsifiable=True)
        led.record(3.0, observed=15.0, tolerance=0.5)
        c2 = led.refute({"a": 5.0, "b": 0.0}, rationale="entry 0")
        self.assertEqual(c2.refutation_set, ["y != 6 at x=3"])


class TestEscapeHatch(unittest.TestCase):
    def test_flags_repeated_thin_refutations(self):
        led = Ledger(linear, Claim("y = a x + b", {"a": 1.0, "b": 0.0}))
        for i in range(3):
            led.record(2.0, observed=1e6, tolerance=0.5)  # always way off
            led.refute({"a": float(i), "b": 0.0}, rationale=f"entry {i}")
        flag = led.escape_hatch_flag()
        self.assertTrue(flag["flag"])
        self.assertEqual(flag["escape_hatch_rate"], 1.0)
        self.assertEqual(flag["thin_survival_versions"], [1, 2, 3])

    def test_no_flag_when_versions_survive(self):
        led = Ledger(linear, Claim("y = a x + b", {"a": 2.0, "b": 0.0}))
        led.record(3.0, observed=6.0, tolerance=0.5)   # survives
        led.record(4.0, observed=8.0, tolerance=0.5)   # survives
        led.record(5.0, observed=99.0, tolerance=0.5)  # refuted
        led.refute({"a": 19.8, "b": 0.0}, rationale="entry 2")
        flag = led.escape_hatch_flag()
        self.assertFalse(flag["flag"])
        self.assertEqual(led.survival_by_version()[1], 2)


if __name__ == "__main__":
    unittest.main()
