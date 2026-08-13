"""fusion.py -- the pure fusion math behind the determinacy gate. stdlib only.

Separated from `determinacy_gate.py` so the gate's `evaluate` reads as
"fuse -> decide" and the fusion policy can be tested on its own. These functions
know nothing about substrates or `BoundReading`; they operate on plain floats, so
the subtle agreement-vs-drain behaviour lives in one small, independently
checkable place.
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple


def combine_independent(confidences: Sequence[float]) -> float:
    """Combine independent bound confidences into one determinacy score.

    Uses the complement-of-product (noisy-OR) rule: each read chips away at the
    residual doubt. Two independent reads at 0.8 give 1 - 0.2*0.2 = 0.96. This
    rewards corroboration without ever exceeding 1, and a single weak read never
    forces determinacy down on its own.
    """
    doubt = 1.0
    for c in confidences:
        doubt *= (1.0 - max(0.0, min(1.0, c)))
    return 1.0 - doubt


def weighted_mean(values: Sequence[float], weights: Sequence[float]) -> Optional[float]:
    """Confidence-weighted mean, or None if the weights sum to <= 0."""
    wsum = sum(weights)
    if wsum <= 0.0:
        return None
    return sum(v * w for v, w in zip(values, weights)) / wsum


def fuse_ground(reads: Sequence[Tuple[float, float]]) -> Tuple[Optional[float], float]:
    """Fuse the grounding layer. `reads` is a sequence of (value, confidence).

    Returns (state_estimate, determinacy): the confidence-weighted mean of the
    values, and the noisy-OR combination of their confidences.
    """
    values = [v for v, _ in reads]
    confidences = [c for _, c in reads]
    return weighted_mean(values, confidences), combine_independent(confidences)


def contradiction_drain(reads: Sequence[Tuple[float, float]], state: float,
                        tolerance: float) -> float:
    """Score PREDICT reads *against* the fused ground and return the max drain.

    `reads` is a sequence of (value, confidence). A read within one `tolerance`
    width of `state` agrees and contributes no drain (it corroborates but must
    not manufacture determinacy the ground did not earn). A read beyond it drains
    in proportion to its confidence and distance -- a saturating penalty so far,
    confident contradictions hurt most:

        drain = confidence * (1 - 1 / (distance / tolerance))

    The overall drain is the worst single contradiction, in [0, 1).
    """
    conflict = 0.0
    for value, confidence in reads:
        dist = abs(value - state) / tolerance
        if dist > 1.0:
            conflict = max(conflict, confidence * (1.0 - 1.0 / dist))
    return conflict
