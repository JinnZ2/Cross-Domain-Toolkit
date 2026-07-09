"""symbolic.py -- a safe, stdlib-only checker for a claim's logical form.

This closes the symbolic/subsymbolic gap at the ledger's edge: a `Claim` can
carry a `logical_form` -- a machine-checkable statement of what it asserts, over
its params and the observed data -- and the ledger can *check* it, not just
eyeball it. No third-party dependency: the default checker evaluates a
restricted, side-effect-free grammar (arithmetic + comparison + boolean) with
Python's `ast`, never `eval`.

    evaluate_logical_form("a > 0 and abs(residual) <= tol", binding) -> bool

The grammar is deliberately small and total. It refuses anything it does not
recognise (calls other than the whitelisted `abs`/`min`/`max`, attribute access,
subscripts, names not in the binding, ...) by raising `LogicalFormError`. That
refusal is the point: an unparseable form is reported, never silently passed.

To go beyond arithmetic -- quantifiers, real proof -- plug in your own solver.
`Checker` is just `Callable[[str, Dict[str, Any]], bool]`, so
`Ledger(..., checker=my_z3_backend)` wires the same slot to Z3 or any prover you
like; the ledger records whatever it returns.
"""

from __future__ import annotations

import ast
import operator
from typing import Any, Callable, Dict

# A checker maps (logical_form, variable binding) -> does the form hold?
Checker = Callable[[str, Dict[str, Any]], bool]


class LogicalFormError(ValueError):
    """Raised when a logical form uses a construct outside the safe grammar, or
    references a name absent from the binding."""


_BIN_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
}
_UNARY_OPS = {
    ast.UAdd: operator.pos, ast.USub: operator.neg, ast.Not: operator.not_,
}
_CMP_OPS = {
    ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt,
    ast.GtE: operator.ge, ast.Eq: operator.eq, ast.NotEq: operator.ne,
}
# The only calls allowed -- pure, total scalar helpers.
_FUNCS = {"abs": abs, "min": min, "max": max}


def _eval(node: ast.AST, binding: Dict[str, Any]) -> Any:
    if isinstance(node, ast.Expression):
        return _eval(node.body, binding)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in binding:
            return binding[node.id]
        raise LogicalFormError(f"unknown name {node.id!r} (not in binding)")
    if isinstance(node, ast.BoolOp):
        vals = [_eval(v, binding) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(vals)
        return any(vals)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval(node.operand, binding))
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval(node.left, binding),
                                       _eval(node.right, binding))
    if isinstance(node, ast.Compare):
        left = _eval(node.left, binding)
        for op, right_node in zip(node.ops, node.comparators):
            if type(op) not in _CMP_OPS:
                raise LogicalFormError(f"comparison {type(op).__name__} not allowed")
            right = _eval(right_node, binding)
            if not _CMP_OPS[type(op)](left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCS:
            raise LogicalFormError("only abs/min/max calls are allowed")
        if node.keywords:
            raise LogicalFormError("keyword arguments are not allowed")
        args = [_eval(a, binding) for a in node.args]
        return _FUNCS[node.func.id](*args)
    raise LogicalFormError(f"construct {type(node).__name__} is not permitted")


def evaluate_logical_form(form: str, binding: Dict[str, Any]) -> bool:
    """Evaluate a logical form against a binding and return whether it holds.

    Restricted grammar: numbers, names from `binding`, + - * / // % **, unary
    +/-/not, comparisons (chained allowed), and/or, and abs/min/max calls.
    Anything else raises `LogicalFormError`.
    """
    try:
        tree = ast.parse(form, mode="eval")
    except SyntaxError as e:
        raise LogicalFormError(f"could not parse logical form: {e}") from e
    return bool(_eval(tree, binding))
