"""physics_ledger.py -- fork the ledger for a physics claim.

Claim: a projectile's range follows R = (v^2/g) sin(2*theta), with g the only
free param. We predict ranges, confront them with (synthetic) reality measured
on a body where g is actually larger, watch the claim get refuted, and update
g -- never the formula, never a past prediction.

Run:  python -m falsification_ledger.examples.physics_ledger
"""

from __future__ import annotations

import math

from ..ledger import Claim, Ledger


def range_kernel(params, condition):
    v, theta = condition
    g = params["g"]
    return (v * v / g) * math.sin(2.0 * theta)


def main():
    led = Ledger(
        kernel=range_kernel,
        claim=Claim("projectile range = (v^2/g) sin(2 theta)", {"g": 9.81}),
    )

    # Reality: this body actually has g = 12.0 (say, a spun habitat).
    g_true = 12.0
    conditions = [(20.0, math.radians(45)), (25.0, math.radians(30))]
    for v, theta in conditions:
        observed = (v * v / g_true) * math.sin(2.0 * theta)
        e = led.record((v, theta), observed, tolerance=1.0, source="rangefinder")
        print(f"v={v} theta={math.degrees(theta):.0f}  "
              f"pred={e.prediction.value:.2f}  obs={e.observation.value:.2f}  "
              f"residual={e.mismatch.residual:+.2f}  refuted={e.mismatch.refuted}")
        if e.mismatch.refuted:
            # Update the CLAIM (g), never the kernel. Fit g from this one reality.
            v_, th_ = e.prediction.condition
            g_new = (v_ * v_ * math.sin(2.0 * th_)) / e.observation.value
            c = led.refute({"g": g_new},
                           rationale=f"entry {e.index}: range short; g -> {g_new:.2f}")
            print(f"    -> claim v{c.version}: g = {c.params['g']:.2f}")

    print("history intact:", led.verify())
    print("final claim:", led.claim.version, led.claim.params)


if __name__ == "__main__":
    main()
