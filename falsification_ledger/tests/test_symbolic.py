"""Tests for the safe logical-form evaluator. stdlib unittest only.

Run:  python -m unittest falsification_ledger.tests.test_symbolic
"""

import unittest

from ..symbolic import LogicalFormError, evaluate_logical_form as ev


class TestGrammar(unittest.TestCase):
    def test_arithmetic_and_comparison(self):
        self.assertTrue(ev("a * x + b == 6", {"a": 2.0, "x": 3.0, "b": 0.0}))
        self.assertFalse(ev("a * x == 7", {"a": 2.0, "x": 3.0}))

    def test_chained_comparison(self):
        self.assertTrue(ev("0 < a <= 10", {"a": 5.0}))
        self.assertFalse(ev("0 < a <= 10", {"a": 11.0}))

    def test_boolean_ops(self):
        self.assertTrue(ev("a > 0 and b > 0", {"a": 1.0, "b": 2.0}))
        self.assertFalse(ev("a > 0 and b > 0", {"a": 1.0, "b": -1.0}))
        self.assertTrue(ev("a > 0 or b > 0", {"a": -1.0, "b": 2.0}))

    def test_whitelisted_calls(self):
        self.assertTrue(ev("abs(residual) <= tol", {"residual": -0.3, "tol": 0.5}))
        self.assertTrue(ev("max(a, b) == 3", {"a": 1.0, "b": 3.0}))
        self.assertTrue(ev("min(a, b) == 1", {"a": 1.0, "b": 3.0}))

    def test_unary_not(self):
        self.assertTrue(ev("not a > 5", {"a": 1.0}))


class TestSafety(unittest.TestCase):
    def test_rejects_unknown_name(self):
        with self.assertRaises(LogicalFormError):
            ev("mystery > 0", {"a": 1.0})

    def test_rejects_attribute_access(self):
        with self.assertRaises(LogicalFormError):
            ev("a.__class__ == 1", {"a": 1.0})

    def test_rejects_subscript(self):
        with self.assertRaises(LogicalFormError):
            ev("data[0] > 0", {"data": [1, 2]})

    def test_rejects_non_whitelisted_call(self):
        with self.assertRaises(LogicalFormError):
            ev('__import__("os")', {})
        with self.assertRaises(LogicalFormError):
            ev("open('x')", {})

    def test_rejects_syntax_error(self):
        with self.assertRaises(LogicalFormError):
            ev("a >", {"a": 1.0})


if __name__ == "__main__":
    unittest.main()
