"""claim_explorer.py -- diagnose a refutation, then decide whether to edit at all.

Run:  python -m falsification_ledger.examples.claim_explorer

`domain_atlas.py` shows six claims meeting reality and four of them being
refuted. This example picks the loop up from there: given a refuted claim, what
*kind* of wrong is it, and does that kind warrant new numbers?

The four cases below are the four answers. Two are repairs -- a gain and an
offset, where the claim's shape was right and one number was not, and the
explorer recovers the true value and the claim converges. Two are refusals: a
form that cannot absorb the error however you tune it, and a claim being read
across a regime boundary. In those the claim is left exactly as it was, at
version 1, because the honest move is to restate it rather than to walk it away
from the refutation.

The last case is the interesting one. A residual that holds on one side of a
control value and breaks on the other is not a mis-parameterization; it is a
system that changed regime. That is the point to stop refitting and go ask
`cascade_regime_audit` whether the alternate state still exists. The explorer
names that handoff and does not make it -- the packages stay standalone.
"""

from __future__ import annotations

from ..explorer import ClaimExplorer
from ..ledger import Claim, Ledger


def linear(params, condition):
    """The fixed sim. It never changes -- that is the whole rule."""
    return params["a"] * condition + params["b"]


def opening_claim() -> Claim:
    return Claim(
        statement="response is linear in dose with slope 2 through the origin",
        params={"a": 2.0, "b": 0.0},
        refutation_set=[
            "measured response at any dose outside tolerance of a*x + b",
            "response is not monotone in dose",
            "a refit slope outside [1.5, 2.5]",
        ],
        scope={"temporal": "one assay run", "spatial": "a single plate",
               "ontological": "normalized fluorescence response"},
        reference_class="wells on the plate at doses between 1 and 6 units",
        logical_form="a > 0 and predicted >= b",
    )


# Four realities the opening claim will meet. Only the first two are the claim's
# parameters being wrong; the other two are the claim's *form* being wrong.
def gain_error(dose):
    """The shape is right; the slope is not."""
    return 5.0 * dose


def offset_error(dose):
    """The slope is right; the claim starts from the wrong place."""
    return 2.0 * dose + 7.0


def wrong_form(dose):
    """Reality is quadratic. No slope makes a line into a parabola."""
    return dose * dose


def regime_change(dose):
    """Linear up to dose 3, then something else takes over."""
    return 2.0 * dose if dose <= 3.0 else 2.0 * dose + 9.0 * (dose - 3.0) ** 2


CASES = (
    ("gain error", gain_error, [1.0, 2.0, 3.0, 4.0]),
    ("offset error", offset_error, [1.0, 2.0, 3.0, 4.0]),
    ("wrong form", wrong_form, [1.0, 2.0, 3.0, 4.0, 5.0]),
    ("regime change", regime_change, [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]),
)


def main() -> None:
    print("Four refuted claims. The explorer proposes new numbers for two of")
    print("them and refuses for the other two.\n")

    for name, reality, doses in CASES:
        led = Ledger(linear, opening_claim())
        trace = ClaimExplorer(led, linear, reality, doses, tolerance=0.5).explore()
        final = trace.rounds[-1].diagnosis

        print("=" * 72)
        print(f"{name}   ->   {trace.outcome}")
        print(f"  claim v{led.claim.version}: "
              f"a = {led.claim.params['a']:.4g}, b = {led.claim.params['b']:.4g}"
              f"   (chain verifies: {led.verify()})")

        first = trace.rounds[0].diagnosis
        print(f"  diagnosis: {first.signature.value} -- {first.detail}")
        if first.refusal:
            print(f"  REFUSED: {first.refusal}")

        if final.patterns:
            print("  cross-domain patterns with this signature:")
            for p in final.patterns:
                print(f"    * {p.shape}")
                print(f"      seen in: {', '.join(p.fields)}")
                print(f"      try:     {p.try_this}")
        print()

    print("=" * 72)
    print("The two refusals left their claims at version 1. That is the point:")
    print("a tool that always has another parameter to offer is an escape-hatch")
    print("machine, and the ledger has a detector for exactly that pathology.")


if __name__ == "__main__":
    main()
