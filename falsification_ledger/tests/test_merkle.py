"""Tests for the Merkle audit certificates. stdlib unittest only.

Run:  python -m unittest falsification_ledger.tests.test_merkle
"""

import unittest

from ..ledger import Claim, Ledger, RefutationError
from ..merkle import (
    merkle_proof,
    merkle_root,
    sign_root,
    verify_proof,
    verify_root_signature,
)


def leaves(n):
    return [f"{i:064x}" for i in range(n)]


class TestRoot(unittest.TestCase):
    def test_empty_has_no_root(self):
        self.assertIsNone(merkle_root([]))

    def test_single_leaf_is_its_own_root(self):
        self.assertEqual(merkle_root(["ab"]), "ab")

    def test_root_is_deterministic(self):
        self.assertEqual(merkle_root(leaves(7)), merkle_root(leaves(7)))

    def test_root_changes_when_any_leaf_changes(self):
        a = leaves(8)
        b = list(a)
        b[5] = "ff" * 32
        self.assertNotEqual(merkle_root(a), merkle_root(b))

    def test_root_changes_when_leaves_are_reordered(self):
        a = leaves(6)
        b = list(a)
        b[0], b[1] = b[1], b[0]
        self.assertNotEqual(merkle_root(a), merkle_root(b))

    def test_odd_tail_promotes_rather_than_duplicating(self):
        # The CVE-2012-2459 shape: if an odd node were duplicated, three leaves
        # [a, b, c] and four leaves [a, b, c, c] would collapse to one root.
        three = leaves(3)
        self.assertNotEqual(merkle_root(three), merkle_root(three + [three[2]]))


class TestProof(unittest.TestCase):
    def test_every_leaf_proves_against_the_root(self):
        for n in (1, 2, 3, 4, 5, 8, 9, 17):
            ls = leaves(n)
            root = merkle_root(ls)
            for i in range(n):
                with self.subTest(n=n, index=i):
                    self.assertTrue(
                        verify_proof(ls[i], i, merkle_proof(ls, i), root))

    def test_proof_is_logarithmic(self):
        ls = leaves(1024)
        self.assertLessEqual(len(merkle_proof(ls, 500)), 10)

    def test_wrong_leaf_fails(self):
        ls = leaves(8)
        root = merkle_root(ls)
        self.assertFalse(verify_proof("ff" * 32, 3, merkle_proof(ls, 3), root))

    def test_wrong_root_fails(self):
        ls = leaves(8)
        self.assertFalse(verify_proof(ls[3], 3, merkle_proof(ls, 3), "00" * 32))

    def test_tampered_proof_fails(self):
        ls = leaves(8)
        root = merkle_root(ls)
        proof = merkle_proof(ls, 3)
        proof[0] = ("ff" * 32, proof[0][1])
        self.assertFalse(verify_proof(ls[3], 3, proof, root))

    def test_flipped_sibling_side_fails(self):
        ls = leaves(8)
        root = merkle_root(ls)
        proof = [(h, not left) for h, left in merkle_proof(ls, 3)]
        self.assertFalse(verify_proof(ls[3], 3, proof, root))

    def test_index_out_of_range(self):
        with self.assertRaises(IndexError):
            merkle_proof(leaves(4), 4)


class TestSigning(unittest.TestCase):
    def test_signature_round_trips(self):
        root = merkle_root(leaves(5))
        self.assertTrue(verify_root_signature(root, sign_root(root, b"key"), b"key"))

    def test_wrong_key_fails(self):
        root = merkle_root(leaves(5))
        self.assertFalse(
            verify_root_signature(root, sign_root(root, b"key"), b"other"))

    def test_signature_does_not_transfer_between_roots(self):
        sig = sign_root(merkle_root(leaves(5)), b"key")
        self.assertFalse(verify_root_signature(merkle_root(leaves(6)), sig, b"key"))


def linear(params, condition):
    return params["a"] * condition + params["b"]


class TestLedgerCertificates(unittest.TestCase):
    def _ledger(self, n=5):
        led = Ledger(linear, Claim("y = a x + b", {"a": 2.0, "b": 0.0}))
        for i in range(n):
            led.record(float(i), observed=2.0 * i, tolerance=0.1)
        return led

    def test_root_is_none_before_anything_is_recorded(self):
        led = Ledger(linear, Claim("y = a x + b", {"a": 2.0, "b": 0.0}))
        self.assertIsNone(led.merkle_root())

    def test_certificate_verifies_without_the_rest_of_the_ledger(self):
        led = self._ledger()
        cert = led.audit_certificate(2)
        # An auditor holds only these four values -- no entries, no ledger.
        self.assertTrue(verify_proof(cert["leaf"], cert["index"],
                                     cert["proof"], cert["root"]))

    def test_every_entry_certifies(self):
        led = self._ledger(9)
        for i in range(9):
            with self.subTest(index=i):
                c = led.audit_certificate(i)
                self.assertTrue(verify_proof(c["leaf"], c["index"],
                                             c["proof"], c["root"]))

    def test_certificate_leaf_is_the_entry_hash(self):
        led = self._ledger()
        self.assertEqual(led.audit_certificate(1)["leaf"], led.entries[1].hash)

    def test_root_tracks_new_entries(self):
        led = self._ledger()
        before = led.merkle_root()
        led.record(99.0, observed=198.0, tolerance=0.1)
        self.assertNotEqual(before, led.merkle_root())

    def test_tampering_breaks_the_certificate_too(self):
        led = self._ledger()
        cert = led.audit_certificate(2)
        led.entries  # entries is a copy; tamper with the real one
        led._entries[2].observation.__dict__["value"] = 999.0
        led._entries[2].hash = led._entries[2].digest()
        self.assertFalse(led.verify())
        self.assertFalse(verify_proof(led._entries[2].hash, 2,
                                      cert["proof"], cert["root"]))

    def test_certificate_on_an_empty_ledger_is_refused(self):
        led = Ledger(linear, Claim("y = a x + b", {"a": 2.0, "b": 0.0}))
        with self.assertRaises(RefutationError):
            led.audit_certificate(0)


if __name__ == "__main__":
    unittest.main()
