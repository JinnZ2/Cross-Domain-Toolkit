"""mappers.py -- reference mappers from raw time series onto the six signals.

stdlib only. The detector in `cascade_audit.py` is deliberately domain-blind: it
takes six normalized `[0, 1]` pressures and does not care where they came from.
These functions are the *reference* way to compute a few of those pressures from
a plain numeric series, so a domain author can reuse tested mappers instead of
re-deriving them inside every example. They are optional -- map your own
observables however you like -- but each returns a value already normalized to
`[0, 1]`, ready to drop into `SignalReads`.
"""

from __future__ import annotations

from typing import Sequence


def lag1_autocorr(series: Sequence[float]) -> float:
    """Lag-1 autocorrelation of a residual series, clamped to [0, 1].

    Rising lag-1 autocorrelation is the classic critical-slowing-down signature:
    the system takes longer to forget a perturbation as it nears a transition.
    """
    n = len(series)
    if n < 3:
        return 0.0
    mean = sum(series) / n
    num = sum((series[i] - mean) * (series[i - 1] - mean) for i in range(1, n))
    den = sum((x - mean) ** 2 for x in series)
    if den == 0:
        return 0.0
    return max(0.0, min(1.0, num / den))


def normalized_variance(series: Sequence[float], baseline_var: float) -> float:
    """Map the variance ratio (current / baseline) onto [0, 1] via 1 - 1/ratio.

    At baseline (ratio = 1) pressure is 0; it rises as variance inflates and
    saturates toward 1 (ratio = 2 -> 0.5, ratio = 4 -> 0.75, ratio = 10 -> 0.9).
    A smooth, unitless stand-in for variance inflation; swap in a domain-specific
    calibration if you have one.
    """
    n = len(series)
    if n < 2 or baseline_var <= 0:
        return 0.0
    mean = sum(series) / n
    var = sum((x - mean) ** 2 for x in series) / (n - 1)
    ratio = var / baseline_var
    return max(0.0, min(1.0, 1.0 - 1.0 / ratio)) if ratio > 0 else 0.0


def abs_skew(series: Sequence[float]) -> float:
    """Absolute skewness of the series, squashed into [0, 1] via |g1| / (1 + |g1|).

    Distributions leaning toward the alternate state grow skewed; this returns a
    directionless magnitude, so pair it with domain knowledge of which tail is the
    alternate well when you assign it to `skew_to_alt_well`.
    """
    n = len(series)
    if n < 3:
        return 0.0
    mean = sum(series) / n
    m2 = sum((x - mean) ** 2 for x in series) / n
    if m2 == 0:
        return 0.0
    m3 = sum((x - mean) ** 3 for x in series) / n
    g1 = m3 / (m2 ** 1.5)
    return abs(g1) / (1.0 + abs(g1))


def coefficient_of_variation(series: Sequence[float]) -> float:
    """Coefficient of variation (std / |mean|), squashed into [0, 1].

    A cheap flicker/instability proxy: a series that swings widely relative to its
    own level is jumping around rather than sitting in one well.
    """
    n = len(series)
    if n < 2:
        return 0.0
    mean = sum(series) / n
    if mean == 0:
        return 0.0
    var = sum((x - mean) ** 2 for x in series) / (n - 1)
    cv = (var ** 0.5) / abs(mean)
    return max(0.0, min(1.0, cv))


# --- back-compat aliases matching the original public names -----------------

def slowing_down_from_series(series: Sequence[float]) -> float:
    """Map a residual series onto S1 (critical slowing down) via lag-1 autocorr."""
    return lag1_autocorr(series)


def variance_inflation_from_series(series: Sequence[float], baseline_var: float) -> float:
    """Map a residual series onto S2 (variance inflation) against a baseline var."""
    return normalized_variance(series, baseline_var)
