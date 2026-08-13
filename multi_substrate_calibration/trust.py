"""trust.py -- turn a substrate's track record into an earned reliability.

stdlib only, and domain-blind on purpose: these functions take counts, not
ledgers. A substrate's record of being right lives wherever the caller keeps it
-- a falsification ledger, a CSV, a held-out evaluation -- and this module never
imports any of them. That inversion is what keeps the calibration package
forkable on its own.

WHY THIS EXISTS
---------------
`Calibration.reliability` is a number the caller asserts. The whole point of
binding confidence is that an unproven substrate cannot dominate the gate, but
if reliability is asserted rather than earned, "unproven" is exactly the thing
nobody has to admit to. These helpers close that loop: hand them how often a
substrate was right, and they hand back the reliability it has actually earned.

THE ESTIMATOR
-------------
A hit rate of 1.0 from two observations is not evidence of a perfect substrate;
it is evidence of two observations. The Laplace/Beta posterior mean

    reliability = (hits + a) / (hits + misses + a + b)

with a uniform Beta(1, 1) prior (a = b = 1) says so: 2/2 earns 0.75, not 1.0,
and 200/200 earns 0.995. A substrate with no record at all sits at the prior
mean, 0.5, rather than at the 1.0 that `Calibration()` currently defaults to --
so silence costs something, which is the point.

    trust  = earned_reliability(hits, misses)
    probe.calibration = Calibration(reliability=trust)

`eligible_for_ground` is the policy on top: a substrate whose earned reliability
sits below a floor should not be anchoring anyone's present state, however
loudly it reports certainty.
"""

from __future__ import annotations

from typing import Dict, Tuple


def earned_reliability(hits: int, misses: int,
                       prior_hits: float = 1.0,
                       prior_misses: float = 1.0) -> float:
    """Posterior-mean reliability from a substrate's track record.

    `hits` are the reads that landed within tolerance, `misses` the ones that
    did not. The default Beta(1, 1) prior is uniform: with no record at all the
    answer is 0.5, and evidence moves it from there. Widen the prior
    (`prior_hits=5, prior_misses=5`) to demand more evidence before trust moves.
    """
    if hits < 0 or misses < 0:
        raise ValueError(f"counts must be >= 0, got hits={hits}, misses={misses}")
    if prior_hits <= 0.0 or prior_misses <= 0.0:
        raise ValueError("prior counts must be > 0 (a proper Beta prior)")
    return (hits + prior_hits) / (hits + misses + prior_hits + prior_misses)


def reliability_interval(hits: int, misses: int, width: float = 2.0,
                         prior_hits: float = 1.0,
                         prior_misses: float = 1.0) -> Tuple[float, float]:
    """A normal-approximation credible interval around `earned_reliability`.

    `width` is in posterior standard deviations (2.0 ~= 95%). The interval is
    what distinguishes "0.75 because it is mediocre" from "0.75 because we have
    barely watched it": a thin record gives a wide interval. Clamped to [0, 1],
    where the approximation degrades near the ends.
    """
    mean = earned_reliability(hits, misses, prior_hits, prior_misses)
    a = hits + prior_hits
    b = misses + prior_misses
    n = a + b
    sd = (a * b / (n * n * (n + 1.0))) ** 0.5
    return (max(0.0, mean - width * sd), min(1.0, mean + width * sd))


def eligible_for_ground(hits: int, misses: int, floor: float = 0.6,
                        min_observations: int = 5) -> bool:
    """Has this substrate earned the right to anchor a present-state estimate?

    Two conditions, both necessary: enough observations to have been tested at
    all, and an earned reliability at or above `floor`. A substrate failing
    either should feed the gate as PREDICT (where it can only ever drain
    determinacy) or not at all -- never as GROUND, where it would be voting on
    what is real.
    """
    if hits + misses < min_observations:
        return False
    return earned_reliability(hits, misses) >= floor


def rank_substrates(records: Dict[str, Tuple[int, int]]) -> Dict[str, float]:
    """Earned reliability for a whole fleet: {name: (hits, misses)} -> {name: r}.

    Deliberately *not* a transitive-trust computation. Substrates do not rate
    each other -- there is no peer graph here, no endorsements to propagate, and
    so nothing for a power iteration to iterate over. Each substrate is rated by
    reality, independently, and the honest aggregate is the per-substrate
    posterior. Anything fancier would be machinery without a matching structure.
    """
    return {name: earned_reliability(h, m) for name, (h, m) in records.items()}
