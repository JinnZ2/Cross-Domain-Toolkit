"""ai_behavior_ledger.py -- fork the ledger for an AI-behavior claim.

Claim: a model's refusal rate on a prompt category is a logistic function of a
"sensitivity" score, with a threshold param. Reality (synthetic) shows the model
refusing at a lower threshold than claimed. The ledger refutes the claim and
moves the threshold -- and because it is hash-chained, nobody can later pretend
the original claim predicted the observed behavior all along.

This is the case the refutation protocol exists for: claims about AI behavior
are exactly where "quietly retune the story to match what happened" is most
tempting and most corrosive.

Run:  python -m falsification_ledger.examples.ai_behavior_ledger
"""

from __future__ import annotations

import math

from ..ledger import Claim, Ledger


def refusal_rate(params, condition):
    """Predicted P(refuse) as a logistic in sensitivity score."""
    s = condition
    thr, sharp = params["threshold"], params["sharpness"]
    return 1.0 / (1.0 + math.exp(-sharp * (s - thr)))


def main():
    led = Ledger(
        kernel=refusal_rate,
        claim=Claim("P(refuse) is logistic in sensitivity",
                    {"threshold": 0.7, "sharpness": 8.0}),
    )

    thr_true = 0.5  # model actually refuses earlier than claimed
    for s in (0.55, 0.6):
        observed = 1.0 / (1.0 + math.exp(-8.0 * (s - thr_true)))
        e = led.record(s, observed, tolerance=0.1, source="eval-harness")
        print(f"sensitivity={s}: pred={e.prediction.value:.2f}  "
              f"obs={e.observation.value:.2f}  refuted={e.mismatch.refuted}")
        if e.mismatch.refuted:
            # Invert the logistic at this point to recover the implied threshold.
            p = min(0.999, max(0.001, e.observation.value))
            thr_new = s - math.log(p / (1.0 - p)) / led.claim.params["sharpness"]
            c = led.refute({"threshold": round(thr_new, 3),
                            "sharpness": led.claim.params["sharpness"]},
                           rationale=f"entry {e.index}: refuses earlier; "
                                     f"threshold -> {thr_new:.2f}")
            print(f"    -> claim v{c.version}: threshold = {c.params['threshold']}")

    print("history intact:", led.verify())
    print(led.to_json())


if __name__ == "__main__":
    main()
