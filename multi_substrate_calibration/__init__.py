"""Multi-substrate calibration protocol.

Public surface:
    Substrate, SubstrateReading, BoundReading, Calibration, Role, make_reading
    DeterminacyGate, GateResult, Verdict
    fusion: combine_independent, weighted_mean, fuse_ground, contradiction_drain,
            collapse_correlated
    trust:  earned_reliability, reliability_interval, eligible_for_ground,
            rank_substrates
"""

from .substrate import (
    BoundReading,
    Calibration,
    Role,
    Substrate,
    SubstrateReading,
    make_reading,
)
from .determinacy_gate import DeterminacyGate, GateResult, Verdict
from .trust import (
    earned_reliability,
    eligible_for_ground,
    rank_substrates,
    reliability_interval,
)
from .fusion import (
    collapse_correlated,
    combine_independent,
    contradiction_drain,
    fuse_ground,
    weighted_mean,
)

__all__ = [
    "BoundReading",
    "Calibration",
    "Role",
    "Substrate",
    "SubstrateReading",
    "make_reading",
    "DeterminacyGate",
    "GateResult",
    "Verdict",
    "collapse_correlated",
    "combine_independent",
    "contradiction_drain",
    "fuse_ground",
    "weighted_mean",
    "earned_reliability",
    "reliability_interval",
    "eligible_for_ground",
    "rank_substrates",
]
