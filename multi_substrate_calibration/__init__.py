"""Multi-substrate calibration protocol.

Public surface:
    Substrate, SubstrateReading, BoundReading, Calibration, Role, make_reading
    DeterminacyGate, GateResult, Verdict
    fusion: combine_independent, weighted_mean, fuse_ground, contradiction_drain
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
from .fusion import (
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
    "combine_independent",
    "contradiction_drain",
    "fuse_ground",
    "weighted_mean",
]
