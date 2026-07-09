"""symbolic_form.py -- attach a machine-checkable logical form to a claim.

Bridges the natural-language `statement` to something the ledger can actually
test. Each record checks the claim's `logical_form` against the row's own numbers
(params + predicted/observed/residual) using the safe stdlib evaluator, and
stores the verdict on the entry -- independent of the numeric tolerance check.

The example shows the two reads coming apart: a claim whose form asserts the
slope is positive stays numerically exact while the *form* is violated, because
the fitted slope went negative. A plugged-in solver (Z3, etc.) would slot into
the same `checker=` hook for richer forms.

Run:  python -m falsification_ledger.examples.symbolic_form
"""

from __future__ import annotations

from ..ledger import Claim, Ledger


def kernel(params, condition):
    return params["a"] * condition + params["b"]


def main():
    # The claim asserts, symbolically: the model IS y = a*x + b (structure) AND
    # the slope is positive (a domain invariant), AND the fit stays within tol.
    claim = Claim(
        "output is a positive-slope affine map of x",
        {"a": 2.0, "b": 0.0},
        logical_form="predicted == a*x + b and a > 0 and abs(residual) <= tol",
        refutation_set=["predicted deviates from a*x+b", "slope a goes non-positive"],
    )
    led = Ledger(kernel, claim, strict_symbolic=True)

    # Reality: the true relationship has a NEGATIVE slope. The linear kernel can
    # be refit to match the numbers, but doing so drives a < 0 -- so the numeric
    # check passes while the symbolic invariant (a > 0) fails.
    a_true, b_true = -1.5, 4.0
    for x in (1.0, 2.0, 3.0):
        observed = a_true * x + b_true
        e = led.record(x, observed, tolerance=0.5, source="bench")
        print(f"x={x}: pred={e.prediction.value:+.2f} obs={observed:+.2f} "
              f"within_tol={e.mismatch.within_tolerance} logical_ok={e.logical_ok}")
        if e.mismatch.refuted:
            # refit the slope from this point; b held for simplicity
            a_new = (observed - led.claim.params["b"]) / x
            led.refute({"a": a_new, "b": led.claim.params["b"]},
                       rationale=f"entry {e.index}: refit slope to {a_new:.2f}")

    print("\nFinal slope a =", round(led.claim.params["a"], 2))
    print("history intact:", led.verify())
    print("Lesson: the numbers can be satisfied while the *form* is violated. "
          "logical_ok=False flags that the claimed structure (positive slope) is "
          "wrong even when the tolerance check is green.")


if __name__ == "__main__":
    main()
