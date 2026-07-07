"""Multi-substrate calibration protocol.

Public surface:
    Substrate, SubstrateReading, BoundReading, Calibration, Role, make_reading
    DeterminacyGate, GateResult, Verdict
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
]
