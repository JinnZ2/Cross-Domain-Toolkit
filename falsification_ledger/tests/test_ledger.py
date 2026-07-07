"""Tests for the falsification ledger. stdlib unittest only.

Run:  python -m unittest falsification_ledger.tests.test_ledger
"""

import unittest

from ..ledger import Claim, Ledger, RefutationError


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


if __name__ == "__main__":
    unittest.main()
