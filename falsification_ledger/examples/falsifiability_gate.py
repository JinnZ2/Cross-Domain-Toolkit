"""falsifiability_gate.py -- the falsifiability features, end to end.

Shows the three guards that turn "I have a claim" into "I have a *falsifiable*
claim, on the record":

  1. A claim must name, up front, what would refute it (`refutation_set`), or a
     strict ledger refuses to open on it.
  2. An extraordinary claim is held to a higher bar (more than one refuting
     condition) -- a mechanical Sagan standard.
  3. The escape-hatch detector flags a claim that is repeatedly re-parameterized
     to dodge refutation without ever surviving a clean observation.

Run:  python -m falsification_ledger.examples.falsifiability_gate
"""

from __future__ import annotations

from ..ledger import (
    Claim, Ledger, RefutationError,
    classify_falsifiability, classify_specificity, find_vague_terms,
)


def kernel(params, condition):
    return params["a"] * condition


def main():
    # 1. An unfalsifiable, under-specified claim is rejected by a strict ledger.
    vague = Claim("the system is basically fine", {"a": 1.0})
    print("vague claim falsifiable?", classify_falsifiability(vague)["falsifiable"])
    print("vague claim specific?  ", classify_specificity(vague)["specific"],
          "| hedge words:", find_vague_terms(vague.statement))
    try:
        Ledger(kernel, vague, strict_falsifiable=True, strict_scope=True)
    except RefutationError as e:
        print("strict ledger refused it:", e)

    # 2. A falsifiable, scoped claim opens fine; both persist across updates.
    claim = Claim(
        "output scales linearly: y = a*x",
        {"a": 2.0},
        refutation_set=["y deviates > 0.5 from a*x at any tested x"],
        reference_class="token-level logits, prompts under 512 tokens",
        scope={"temporal": "within one training run",
               "spatial": "this model family",
               "ontological": "next-token logit magnitude"},
    )
    led = Ledger(kernel, claim, strict_falsifiable=True, strict_scope=True)
    print("\nfalsifiable + scoped claim opened.")
    print("  refutation_set:", led.claim.refutation_set)
    print("  reference_class:", led.claim.reference_class)

    # 3. Drive it toward the escape-hatch pattern: reality is quadratic, so a
    #    linear claim keeps getting refuted and re-parameterized without ever
    #    holding up.
    for x in (2.0, 3.0, 4.0):
        observed = x * x  # truly quadratic
        e = led.record(x, observed, tolerance=0.5, source="bench")
        print(f"  x={x}: pred={e.prediction.value:.1f} obs={observed:.1f} "
              f"refuted={e.mismatch.refuted}")
        if e.mismatch.refuted:
            led.refute({"a": observed / x}, rationale=f"entry {e.index}: refit slope")

    hatch = led.escape_hatch_flag()
    print("\nescape-hatch flag:", hatch["flag"],
          "| rate", hatch["escape_hatch_rate"],
          "| thin versions", hatch["thin_survival_versions"])
    print("survival by version:", led.survival_by_version())
    print("history intact:", led.verify())
    print("\nLesson: refit velocity this high means the *form* is wrong "
          "(linear vs quadratic), not the parameter. The ledger makes that visible.")


if __name__ == "__main__":
    main()
