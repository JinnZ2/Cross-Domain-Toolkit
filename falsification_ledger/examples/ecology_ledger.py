"""ecology_ledger.py -- fork the ledger for a population-dynamics claim.

Claim: a population grows logistically toward carrying capacity K at rate r.
Reality (synthetic) carries a lower K than claimed. The ledger records the
overshoot, refutes the claim, and lowers K -- the growth *model* is untouched.

Run:  python -m falsification_ledger.examples.ecology_ledger
"""

from __future__ import annotations

from ..ledger import Claim, Ledger


def logistic_next(params, condition):
    """One-step logistic prediction. condition = current population N."""
    n = condition
    r, k = params["r"], params["K"]
    return n + r * n * (1.0 - n / k)


def main():
    led = Ledger(
        kernel=logistic_next,
        claim=Claim("population grows logistically to K", {"r": 0.8, "K": 1000.0}),
    )

    k_true = 600.0
    r_true = 0.8
    n = 300.0
    for step in range(4):
        observed = n + r_true * n * (1.0 - n / k_true)
        e = led.record(n, observed, tolerance=15.0, source="field-census")
        print(f"step {step}: N={n:.0f}  pred={e.prediction.value:.0f}  "
              f"obs={e.observation.value:.0f}  refuted={e.mismatch.refuted}")
        if e.mismatch.refuted:
            # Solve for the K consistent with this observation; update the claim.
            r = led.claim.params["r"]
            growth = e.observation.value - n
            k_new = r * n * n / (r * n - growth) if (r * n - growth) != 0 else led.claim.params["K"]
            c = led.refute({"r": r, "K": round(k_new, 1)},
                           rationale=f"entry {e.index}: overshoot; K -> {k_new:.0f}")
            print(f"    -> claim v{c.version}: K = {c.params['K']}")
        n = observed

    print("history intact:", led.verify())
    print("final claim:", led.claim.version, led.claim.params)


if __name__ == "__main__":
    main()
