"""cascade_audit.py -- a domain-agnostic cascade-regime detector. stdlib only.

Ports the logic of a field-specific `cascade_regime_audit` into an abstract
instrument you instantiate in *your* domain -- model-collapse detection,
institutional fragility, ecosystem tipping, a fear cascade -- by supplying six
observables and one control parameter. It does not make your model smarter; it
puts the orthogonal frame beside it: "is this system approaching a saddle-node
where the alternative state stops existing?"

TWO INDEPENDENT READS, KEPT SEPARATE
------------------------------------
1. SIX-SIGNAL DETECTOR (statistical early warning). Six generic signatures of a
   system being driven toward a critical transition. Each is normalized to a
   [0, 1] pressure. You map your domain's observables onto them; you do not
   re-derive them.

     S1  critical slowing down   -- lag-1 autocorrelation rises; the system
                                    recovers from perturbation ever slower.
     S2  variance inflation      -- fluctuation amplitude grows near the tipping.
     S3  skew toward the alt well-- the distribution leans toward the other state.
     S4  flickering / bimodality -- dwell times split; the system jumps states.
     S5  coherence-under-contradiction -- when perturbed, coherence RISES instead
                                    of falling: the system is sealing/defending,
                                    not updating. A locked system, not a healthy
                                    one. (Rising coherence under contradiction is
                                    a RED signal, not reassurance.)
     S6  diversity collapse       -- units synchronize; effective degrees of
                                    freedom fall; independent buffers vanish.

2. SPINODAL THRESHOLD (structural). Independent of the statistics: a control
   parameter `h_eff` (net forcing / consolidation ratio). Past the spinodal the
   minority well disappears by a saddle-node bifurcation and escape is no longer
   reversible -- the early-warning signals stop being warnings and become
   history. Canonical cusp value:  h* = 2 / sqrt(27) ~= 0.3849.

The audit reports BOTH and only calls a regime a cascade when the statistical
pressure is high AND the structure is at/over the spinodal. High signals below
the spinodal = stressed but recoverable; over the spinodal = committed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Sequence

# The cusp-catastrophe spinodal: |h_eff| beyond this and the minority well is
# gone (saddle-node). Same constant used in the field-collapse kernel this
# abstraction generalizes.
H_SPINODAL = 2.0 / math.sqrt(27.0)  # ~= 0.384900


class Regime(Enum):
    STABLE = "stable"              # low pressure, below spinodal
    STRESSED = "stressed"         # high pressure, still below spinodal (recoverable)
    COMMITTED = "committed"       # over the spinodal: alt state gone (irreversible)
    CASCADE = "cascade"           # high pressure AND over the spinodal


SIGNAL_NAMES = (
    "critical_slowing_down",
    "variance_inflation",
    "skew_to_alt_well",
    "flickering",
    "coherence_under_contradiction",
    "diversity_collapse",
)


@dataclass
class SignalReads:
    """The six pressures, each in [0, 1]. Instantiate by mapping your domain's
    observables onto these fields. Anything you cannot measure, leave at 0.0 and
    it simply abstains (it never fabricates a warning)."""

    critical_slowing_down: float = 0.0
    variance_inflation: float = 0.0
    skew_to_alt_well: float = 0.0
    flickering: float = 0.0
    coherence_under_contradiction: float = 0.0
    diversity_collapse: float = 0.0

    def as_dict(self) -> Dict[str, float]:
        return {n: getattr(self, n) for n in SIGNAL_NAMES}

    def __post_init__(self) -> None:
        for n in SIGNAL_NAMES:
            v = getattr(self, n)
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"signal {n} must be in [0, 1], got {v}")


@dataclass
class AuditResult:
    regime: Regime
    pressure: float                 # aggregate statistical pressure in [0, 1]
    h_eff: float                    # control parameter (net forcing)
    over_spinodal: bool
    spinodal: float
    signals: Dict[str, float]
    fired: List[str]                # signals above the fire threshold
    note: str

    @property
    def distance_to_spinodal(self) -> float:
        """Signed slack: positive = margin remaining, negative = past it."""
        return self.spinodal - abs(self.h_eff)


# --- helpers for mapping raw time series onto the six signals ---------------

def _lag1_autocorr(series: Sequence[float]) -> float:
    n = len(series)
    if n < 3:
        return 0.0
    mean = sum(series) / n
    num = sum((series[i] - mean) * (series[i - 1] - mean) for i in range(1, n))
    den = sum((x - mean) ** 2 for x in series)
    if den == 0:
        return 0.0
    return max(0.0, min(1.0, num / den))


def _normalized_variance(series: Sequence[float], baseline_var: float) -> float:
    n = len(series)
    if n < 2 or baseline_var <= 0:
        return 0.0
    mean = sum(series) / n
    var = sum((x - mean) ** 2 for x in series) / (n - 1)
    # Map the variance ratio (current / baseline) onto [0, 1] with 1 - 1/ratio:
    # at baseline (ratio = 1) pressure is 0; it rises as variance inflates and
    # saturates toward 1 (ratio = 2 -> 0.5, ratio = 4 -> 0.75, ratio = 10 -> 0.9).
    # This is a smooth, unitless stand-in for the variance-inflation early-warning
    # signal; swap in a domain-specific calibration if you have one.
    ratio = var / baseline_var
    return max(0.0, min(1.0, 1.0 - 1.0 / ratio)) if ratio > 0 else 0.0


def slowing_down_from_series(series: Sequence[float]) -> float:
    """Convenience: map a residual series onto S1 via lag-1 autocorrelation."""
    return _lag1_autocorr(series)


def variance_inflation_from_series(series: Sequence[float], baseline_var: float) -> float:
    """Convenience: map a residual series onto S2 against a known baseline var."""
    return _normalized_variance(series, baseline_var)


class CascadeAudit:
    """The instrument. Instantiate once per domain with your thresholds, then
    call `audit(signals, h_eff)` each time you have a fresh read.

    `fire_threshold` -- a single signal above this counts as "fired".
    `pressure_threshold` -- aggregate pressure above this is "high".
    `spinodal` -- override the cusp default if your system's normalized forcing
                  uses a different scale.
    `weights` -- optional per-signal weights (default: equal).
    """

    def __init__(self, fire_threshold: float = 0.6, pressure_threshold: float = 0.5,
                 spinodal: float = H_SPINODAL,
                 weights: Optional[Dict[str, float]] = None) -> None:
        for name, val in (("fire_threshold", fire_threshold),
                          ("pressure_threshold", pressure_threshold)):
            if not 0.0 <= val <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {val}")
        if spinodal <= 0.0:
            raise ValueError(f"spinodal must be > 0, got {spinodal}")
        if weights is not None:
            unknown = set(weights) - set(SIGNAL_NAMES)
            if unknown:
                raise ValueError(
                    f"unknown signal weights {sorted(unknown)}; "
                    f"valid names are {list(SIGNAL_NAMES)}"
                )
            if sum(weights.get(n, 0.0) for n in SIGNAL_NAMES) <= 0.0:
                raise ValueError("weights over the six signals must sum to > 0")
        self.fire_threshold = fire_threshold
        self.pressure_threshold = pressure_threshold
        self.spinodal = spinodal
        self.weights = weights or {n: 1.0 for n in SIGNAL_NAMES}

    def _pressure(self, signals: SignalReads) -> float:
        d = signals.as_dict()
        wsum = sum(self.weights.get(n, 0.0) for n in SIGNAL_NAMES)
        if wsum <= 0:
            return 0.0
        return sum(d[n] * self.weights.get(n, 0.0) for n in SIGNAL_NAMES) / wsum

    def audit(self, signals: SignalReads, h_eff: float) -> AuditResult:
        pressure = self._pressure(signals)
        over = abs(h_eff) >= self.spinodal
        high = pressure >= self.pressure_threshold
        fired = [n for n, v in signals.as_dict().items() if v >= self.fire_threshold]

        if high and over:
            regime, note = Regime.CASCADE, (
                "high early-warning pressure AND past the spinodal: the alternate "
                "state is gone and the transition is running. Warnings are now history."
            )
        elif over:
            regime, note = Regime.COMMITTED, (
                "past the spinodal: the minority well has vanished (saddle-node). "
                "Statistics look calm only because there is nothing left to fluctuate toward."
            )
        elif high:
            regime, note = Regime.STRESSED, (
                "high early-warning pressure but still below the spinodal: stressed "
                "and recoverable. This is the actionable window."
            )
        else:
            regime, note = Regime.STABLE, "low pressure, structural margin intact."

        return AuditResult(
            regime=regime,
            pressure=pressure,
            h_eff=h_eff,
            over_spinodal=over,
            spinodal=self.spinodal,
            signals=signals.as_dict(),
            fired=fired,
            note=note,
        )
