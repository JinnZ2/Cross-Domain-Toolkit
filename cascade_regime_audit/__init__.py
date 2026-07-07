"""Abstract cascade-regime audit: six-signal detector + spinodal threshold.

Public surface:
    CascadeAudit, SignalReads, AuditResult, Regime, H_SPINODAL, SIGNAL_NAMES
    slowing_down_from_series, variance_inflation_from_series
"""

from .cascade_audit import (
    AuditResult,
    CascadeAudit,
    H_SPINODAL,
    Regime,
    SIGNAL_NAMES,
    SignalReads,
    slowing_down_from_series,
    variance_inflation_from_series,
)

__all__ = [
    "AuditResult",
    "CascadeAudit",
    "H_SPINODAL",
    "Regime",
    "SIGNAL_NAMES",
    "SignalReads",
    "slowing_down_from_series",
    "variance_inflation_from_series",
]
