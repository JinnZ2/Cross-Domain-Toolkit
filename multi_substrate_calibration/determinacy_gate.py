"""determinacy_gate.py -- fuse bound reads and route them through Le.

stdlib only. This is the substrate-agnostic core. It never imports a specific
substrate; it only consumes the `BoundReading` contract from substrate.py. Add
a thermal probe, an acoustic array, or a market feed and this file does not
change -- that is the whole point of the intake contract.

TWO GROUNDING LAYERS
--------------------
GROUND reads (sensorimotor "what is") are fused into a single present-state
estimate with a confidence-weighted mean; their confidences combine into a
determinacy score.

PREDICT reads (cascade "what will be") are NOT fused into the present. They are
held up against the fused GROUND state and scored by agreement. A confident
prediction that contradicts the ground is a determinacy *drain*, not a boost --
this is what stops a forecast from being laundered into an observation.

Le -- THE EPSILON-DETERMINACY LAYER
-----------------------------------
Le is the decision layer. It asks one question: is the fused determinacy within
epsilon of certainty?

    determinate  iff  determinacy >= 1 - epsilon

epsilon is the caller's tolerance for acting on incomplete grounding. A tight
epsilon (0.02) means "act only when nearly certain"; a loose one (0.3) means
"act on a working hypothesis." When indeterminate, Le returns DEFER with the
reason and the gap, so the caller knows whether to gather more GROUND reads,
resolve a GROUND/PREDICT conflict, or widen epsilon.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence

from .substrate import BoundReading, Role


class Verdict(Enum):
    DETERMINATE = "determinate"      # act
    DEFER = "defer"                  # indeterminate: gather more / resolve conflict


@dataclass
class GateResult:
    verdict: Verdict
    state_estimate: Optional[float]  # fused GROUND value, None if no ground reads
    determinacy: float               # fused determinacy in [0, 1]
    epsilon: float
    reason: str
    ground_count: int
    predict_count: int
    conflict: float                  # 0 = predictions agree with ground, 1 = max drain

    @property
    def gap(self) -> float:
        """How far determinacy sits below the (1 - epsilon) threshold. 0 if met."""
        return max(0.0, (1.0 - self.epsilon) - self.determinacy)


def _combine_independent(confidences: Sequence[float]) -> float:
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


def _weighted_mean(values: Sequence[float], weights: Sequence[float]) -> Optional[float]:
    wsum = sum(weights)
    if wsum <= 0.0:
        return None
    return sum(v * w for v, w in zip(values, weights)) / wsum


class DeterminacyGate:
    """Fuses bound reads across substrates and applies the Le decision.

    The gate is stateless per call: hand it a batch of BoundReadings and it
    returns a GateResult. `predict_tolerance` sets the band (in units of the
    ground state's own scale) within which a PREDICT read is considered to agree
    with the fused ground; beyond it, the prediction's confidence is converted
    into a determinacy drain proportional to the disagreement.
    """

    def __init__(self, epsilon: float = 0.1, predict_tolerance: float = 1.0) -> None:
        if not 0.0 < epsilon < 1.0:
            raise ValueError(f"epsilon must be in (0, 1), got {epsilon}")
        self.epsilon = epsilon
        self.predict_tolerance = predict_tolerance

    def evaluate(self, reads: Sequence[BoundReading]) -> GateResult:
        ground = [r for r in reads if r.role is Role.GROUND]
        predict = [r for r in reads if r.role is Role.PREDICT]

        if not ground:
            return GateResult(
                verdict=Verdict.DEFER,
                state_estimate=None,
                determinacy=0.0,
                epsilon=self.epsilon,
                reason="no GROUND reads: nothing anchors the present state",
                ground_count=0,
                predict_count=len(predict),
                conflict=0.0,
            )

        # --- Fuse the grounding layer (sensorimotor "what is"). ---
        state = _weighted_mean(
            [r.value for r in ground],
            [r.bound_confidence for r in ground],
        )
        ground_determinacy = _combine_independent([r.bound_confidence for r in ground])

        # --- Score the prediction layer against the fused ground. ---
        # A prediction that lands within predict_tolerance of the ground state
        # corroborates it (small boost, capped). A prediction that lands outside
        # drains determinacy in proportion to its own confidence and its distance.
        conflict = 0.0
        agree_conf: List[float] = []
        for p in predict:
            dist = abs(p.value - state) / self.predict_tolerance if self.predict_tolerance else 0.0
            if dist <= 1.0:
                agree_conf.append(p.bound_confidence * (1.0 - dist))
            else:
                # saturating drain: far, confident contradictions hurt most
                drain = p.bound_confidence * (1.0 - 1.0 / dist)
                conflict = max(conflict, drain)

        determinacy = _combine_independent([ground_determinacy, *agree_conf])
        determinacy *= (1.0 - conflict)  # contradiction pulls the whole result down

        threshold = 1.0 - self.epsilon
        if determinacy >= threshold:
            verdict = Verdict.DETERMINATE
            reason = "determinacy within epsilon of certainty"
        else:
            verdict = Verdict.DEFER
            if conflict > 0.0:
                reason = (
                    "PREDICT read contradicts fused GROUND state "
                    f"(conflict drain {conflict:.3f}); resolve before acting"
                )
            else:
                reason = "insufficient grounding; add GROUND reads or widen epsilon"

        return GateResult(
            verdict=verdict,
            state_estimate=state,
            determinacy=determinacy,
            epsilon=self.epsilon,
            reason=reason,
            ground_count=len(ground),
            predict_count=len(predict),
            conflict=conflict,
        )
