"""explorer.py -- diagnose a refutation, propose a repair, look across domains.

stdlib only, and domain-blind: it reads residuals, never fields.

    diagnose  ->  edit (maybe)  ->  cross-domain patterns  ->  rerun

THE DANGER THIS MODULE IS BUILT AGAINST
---------------------------------------
An automated "the claim was refuted, so adjust it and try again" loop is, in
shape, an escape-hatch machine: exactly the pathology `Ledger.escape_hatch_flag`
exists to catch. A tool that always has a new parameter to suggest will walk any
claim away from any refutation for ever, and the ledger will faithfully record a
long history of a claim that never once survived a test.

So the useful half of this module is the half that says **no**. It refuses to
propose an edit when the residuals say the claim's *form* is wrong rather than
its parameters, refuses when the claim is already being re-parameterized without
surviving anything, and refuses when the misses look like noise against a
tolerance that is simply too tight. Those refusals are findings, not failures --
"stop turning this knob" is the most useful thing an explorer can tell you.

WHAT THE RESIDUALS ARE ASKED
----------------------------
Given the entries recorded against the current claim version, the residual
sequence has a shape, and the shape says what kind of wrong the claim is:

    HOLDING     every entry inside tolerance -- nothing to diagnose
    NOISE       residuals straddle zero, no trend: the claim may be fine and the
                tolerance too tight
    BIAS        residuals share a sign and a rough magnitude: an offset is off
    SCALE       observed/predicted is roughly constant but not 1: a gain is off
    CURVATURE   residuals grow with the condition and the ratio drifts: the
                exponent or the functional form is wrong
    THRESHOLD   small residuals on one side of a condition, large on the other:
                a regime the claim does not model
    OSCILLATION residual sign alternates: a periodic term is missing

Only BIAS and SCALE earn a proposed parameter edit, because only they are
consistent with "the form is right and a number is off." The rest return no
edit, on purpose.

CROSS-DOMAIN PATTERNS
---------------------
Each signature carries a catalogue of the shapes that *usually* produce it, and
the fields where each shape is canonical -- saturating growth is a carrying
capacity in ecology, Michaelis-Menten in enzyme kinetics, and market saturation
in adoption curves, and a claim showing CURVATURE against a linear form may want
any of them. The catalogue is **annotation, never dispatch**: nothing in this
module branches on a domain, and the diagnosis is computed from numbers alone.

The THRESHOLD signature is the interesting seam. A claim whose residuals jump at
a control value is not mis-parameterized; it is being read across a regime
boundary. That is the point at which to stop refitting and go ask
`cascade_regime_audit` whether the system has a fold. This module names that
handoff in plain text and does not import it -- the packages stay standalone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .ledger import Ledger, RefutationError

# Reality, asked for a condition. The explorer's only source of new observations.
Oracle = Callable[[Any], float]


class Signature(Enum):
    """The shape of a residual sequence."""

    HOLDING = "holding"
    NOISE = "noise"
    BIAS = "bias"
    SCALE = "scale"
    CURVATURE = "curvature"
    THRESHOLD = "threshold"
    OSCILLATION = "oscillation"
    UNKNOWN = "unknown"


# Signatures whose diagnosis is "a number is off", i.e. the only ones where
# proposing a parameter edit is a repair rather than an evasion.
_PARAMETRIC = (Signature.BIAS, Signature.SCALE)


@dataclass(frozen=True)
class CrossDomainPattern:
    """A shape that produces a given residual signature, and where it is known.

    `fields` is annotation for a human -- the places this shape is already
    named and studied -- not a dispatch key. `try_this` is the concrete next
    move on the claim.
    """

    shape: str
    fields: Tuple[str, ...]
    try_this: str


# The catalogue. Keyed by signature; every entry is advisory.
PATTERNS: Dict[Signature, Tuple[CrossDomainPattern, ...]] = {
    Signature.BIAS: (
        CrossDomainPattern(
            "constant offset / uncorrected datum",
            ("survey levelling", "instrument zeroing", "index rebasing"),
            "add or move an additive term; check the measurement's zero point",
        ),
        CrossDomainPattern(
            "omitted background term",
            ("spectroscopy baselines", "epidemiological importation",
             "accounting accruals"),
            "the process has a floor the claim starts from zero",
        ),
    ),
    Signature.SCALE: (
        CrossDomainPattern(
            "unit or gain error",
            ("metrology", "sensor calibration", "currency and deflator series"),
            "check the units on both sides before touching the parameter",
        ),
        CrossDomainPattern(
            "wrong normalisation constant",
            ("Gutenberg-Richter productivity a", "allometric coefficients",
             "scaling-law prefactors"),
            "refit the multiplicative constant on all observations, not the last",
        ),
    ),
    Signature.CURVATURE: (
        CrossDomainPattern(
            "saturating growth: linear near zero, flattening at a ceiling",
            ("logistic carrying capacity", "Michaelis-Menten kinetics",
             "market adoption", "learning curves"),
            "replace the form with a saturating one and refit; a ceiling is a "
            "parameter the current form does not have",
        ),
        CrossDomainPattern(
            "power law rather than linear",
            ("neural scaling laws", "allometry", "earthquake magnitude-frequency"),
            "fit an exponent; a linear claim cannot absorb one by moving a slope",
        ),
        CrossDomainPattern(
            "compounding / exponential growth",
            ("epidemic early phase", "debt dynamics", "population growth"),
            "the process compounds and the claim adds; change the form",
        ),
    ),
    Signature.THRESHOLD: (
        CrossDomainPattern(
            "regime boundary: the claim is right on one side only",
            ("phase transitions", "structural buckling", "fishery collapse",
             "credit-market freezes"),
            "STOP refitting. Find the control parameter, and audit whether the "
            "system has crossed a fold -- see cascade_regime_audit, whose "
            "h_eff/spinodal read answers exactly this question",
        ),
        CrossDomainPattern(
            "censoring or a detection limit",
            ("catalogue completeness magnitude", "assay limits of detection",
             "survey top-coding"),
            "the break may be in the instrument, not the world; check where the "
            "data stops being able to see",
        ),
    ),
    Signature.OSCILLATION: (
        CrossDomainPattern(
            "missing periodic term",
            ("seasonality", "tidal and diurnal forcing", "business cycles"),
            "add the period the claim ignores before touching anything else",
        ),
        CrossDomainPattern(
            "predator-prey / delayed feedback",
            ("Lotka-Volterra", "control loops with lag", "inventory bullwhip"),
            "a lag term, not a coefficient",
        ),
    ),
    Signature.NOISE: (
        CrossDomainPattern(
            "tolerance tighter than the measurement",
            ("any field with a stated instrument precision",),
            "the claim may be fine. Justify the tolerance from the measurement "
            "error before re-parameterizing anything",
        ),
    ),
}


@dataclass(frozen=True)
class Diagnosis:
    """What the residuals say, and whether an edit is warranted."""

    signature: Signature
    detail: str
    rows: int
    proposed_params: Optional[Dict[str, float]] = None
    proposed_param: Optional[str] = None
    patterns: Tuple[CrossDomainPattern, ...] = ()
    refusal: Optional[str] = None

    @property
    def edit_warranted(self) -> bool:
        return self.proposed_params is not None

    def summary(self) -> str:
        head = f"{self.signature.value}: {self.detail}"
        if self.refusal:
            # A holding claim is not a refusal to act on a problem; it is the
            # absence of one. Saying "REFUSED" there would read as a complaint.
            label = "note" if self.signature is Signature.HOLDING else "REFUSED"
            return f"{head}\n  {label}: {self.refusal}"
        if self.proposed_param:
            return f"{head}\n  propose: {self.proposed_param} -> " \
                   f"{self.proposed_params[self.proposed_param]:.6g}"
        return head


@dataclass
class Round:
    """One diagnose -> edit -> rerun cycle."""

    index: int
    diagnosis: Diagnosis
    applied: bool
    claim_version: int
    worst_normalized_residual: float


@dataclass
class Exploration:
    """The trace of a whole exploration, and why it stopped."""

    rounds: List[Round] = field(default_factory=list)
    outcome: str = "not started"

    @property
    def converged(self) -> bool:
        return self.outcome == "converged"

    def summary(self) -> str:
        lines = [f"outcome: {self.outcome}", ""]
        for r in self.rounds:
            lines.append(f"round {r.index} (claim v{r.claim_version}, "
                         f"worst |r|/tol {r.worst_normalized_residual:.2f})")
            lines.append("  " + r.diagnosis.summary().replace("\n", "\n  "))
        return "\n".join(lines)


# --- residual shape analysis ------------------------------------------------

def _rows(led: Ledger) -> List[Tuple[Any, float, float, float, float]]:
    """(condition, predicted, observed, residual, tolerance) for the current claim."""
    return [
        (e.prediction.condition, e.prediction.value, e.observation.value,
         e.mismatch.residual, e.mismatch.tolerance)
        for e in led.entries if e.claim.version == led.claim.version
    ]


def _scalar(condition: Any) -> Optional[float]:
    """A condition usable as an x-axis, or None if it is not a bare number."""
    if isinstance(condition, bool):
        return None
    if isinstance(condition, (int, float)):
        return float(condition)
    return None


def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _spread(xs: Sequence[float]) -> float:
    """Coefficient of variation, or inf when the mean is ~0 and the values are not."""
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    var = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    sd = var ** 0.5
    if abs(m) < 1e-12:
        return float("inf") if sd > 1e-12 else 0.0
    return sd / abs(m)


def _sign_changes(xs: Sequence[float]) -> int:
    changes = 0
    for a, b in zip(xs, xs[1:]):
        if a * b < 0:
            changes += 1
    return changes


def classify_residuals(rows: Sequence[Tuple[Any, float, float, float, float]]
                       ) -> Tuple[Signature, str]:
    """The whole diagnostic core: a residual sequence in, a shape out.

    Deliberately made of plain arithmetic on normalized residuals. Nothing here
    knows what field produced the numbers, which is what lets the same routine
    read a fishery and a scaling law.
    """
    if not rows:
        return Signature.UNKNOWN, "no observations recorded against this claim"

    normalized = [res / tol if tol > 0 else 0.0 for _, _, _, res, tol in rows]
    worst = max(abs(n) for n in normalized)
    if worst <= 1.0:
        return Signature.HOLDING, "every observation is inside tolerance"

    if len(rows) < 2:
        return (Signature.UNKNOWN,
                "one refuted observation: a shape needs at least two to have")

    residuals = [res for _, _, _, res, _ in rows]
    predicted = [p for _, p, _, _, _ in rows]
    same_sign = all(r > 0 for r in residuals) or all(r < 0 for r in residuals)

    # Order by the condition when it is a number, so "trend" means something.
    xs = [_scalar(c) for c, _, _, _, _ in rows]
    ordered = None
    if all(x is not None for x in xs):
        ordered = sorted(zip(xs, normalized, residuals, predicted))

    # THRESHOLD -- the claim holds on one contiguous side of the condition axis
    # and fails on the other. It has to be a clean split: an in-tolerance point
    # sitting in the middle of failures is scatter, not a regime boundary.
    if ordered is not None and len(ordered) >= 3:
        inside = [abs(n) <= 1.0 for _, n, _, _ in ordered]
        for k in range(1, len(inside)):
            if all(inside[:k]) and not any(inside[k:]):
                return (Signature.THRESHOLD,
                        f"holds up to condition ~{ordered[k - 1][0]:.6g} and "
                        "breaks beyond it; the claim is being read across a "
                        "regime boundary")
            if not any(inside[:k]) and all(inside[k:]):
                return (Signature.THRESHOLD,
                        f"breaks below condition ~{ordered[k][0]:.6g} and holds "
                        "beyond it; the claim is being read across a regime "
                        "boundary")

    # OSCILLATION -- the sign keeps flipping along the condition axis.
    seq = [r for _, _, r, _ in ordered] if ordered is not None else residuals
    if len(seq) >= 4 and _sign_changes(seq) >= len(seq) - 2:
        return (Signature.OSCILLATION,
                "residual sign alternates along the condition: a periodic or "
                "delayed term is missing")

    # NOISE -- straddles zero, no direction, and not badly out.
    if not same_sign and worst <= 2.0:
        return (Signature.NOISE,
                "residuals straddle zero and none is badly out: this may be "
                "measurement noise against too tight a tolerance")

    # SCALE -- observed/predicted is roughly constant and not 1.
    ratios = [obs / p for _, p, obs, _, _ in rows if abs(p) > 1e-12]
    if len(ratios) == len(rows) and ratios:
        mean_ratio = _mean(ratios)
        if _spread(ratios) < 0.15 and abs(mean_ratio - 1.0) > 0.05:
            return (Signature.SCALE,
                    f"observed/predicted is a near-constant {mean_ratio:.4g}: "
                    "a multiplicative constant is wrong, the shape is not")

    # BIAS -- one sign, one rough magnitude, and not proportional to prediction.
    if same_sign and _spread([abs(r) for r in residuals]) < 0.35:
        return (Signature.BIAS,
                f"residuals share a sign and a size (~{_mean(residuals):.4g}): "
                "an additive offset is wrong, the shape is not")

    # CURVATURE -- the *signed* error runs monotonically with the condition. It
    # has to be signed: a linear claim against a quadratic reality crosses zero
    # somewhere, so the magnitudes dip even as the error runs away in one
    # direction. Reading magnitudes here would miss the commonest case there is.
    if ordered is not None and len(ordered) >= 3:
        signed = [n for _, n, _, _ in ordered]
        rising = all(b >= a for a, b in zip(signed, signed[1:]))
        falling = all(b <= a for a, b in zip(signed, signed[1:]))
        if (rising or falling) and abs(signed[-1] - signed[0]) > 2.0:
            return (Signature.CURVATURE,
                    "error runs monotonically with the condition and not by a "
                    "constant factor: the exponent or the functional form is wrong")

    return (Signature.UNKNOWN,
            "residuals are out of tolerance with no clean shape; more "
            "observations, or a look at the raw data, before any edit")


# --- proposing an edit (only where the form is not in question) -------------

def _sse(kernel, params: Dict[str, float],
         rows: Sequence[Tuple[Any, float, float, float, float]]) -> float:
    """Total squared normalized residual under a candidate parameter set."""
    total = 0.0
    for condition, _, observed, _, tolerance in rows:
        try:
            predicted = float(kernel(dict(params), condition))
        except Exception:
            return float("inf")
        total += ((predicted - observed) / tolerance) ** 2 if tolerance > 0 else 0.0
    return total


def _propose_single_param(kernel, params: Dict[str, float],
                          rows: Sequence[Tuple[Any, float, float, float, float]]
                          ) -> Optional[Tuple[str, Dict[str, float]]]:
    """Search for ONE parameter whose change explains the observations.

    One, not several. Moving a single named number with a stated reason is a
    correction; moving all of them until the residuals go quiet is fitting, and
    the difference is the whole point of the ledger. The search uses only kernel
    evaluations, so it stays domain-blind.
    """
    if not params:
        return None
    base = _sse(kernel, params, rows)

    # The two principled candidates come from the residuals themselves: the mean
    # observed/predicted ratio (what a gain error would need) and the mean
    # residual (what an offset would need). The geometric grid is only there to
    # catch the cases those two miss.
    ratios = [obs / p for _, p, obs, _, _ in rows if abs(p) > 1e-12]
    mean_ratio = _mean(ratios) if len(ratios) == len(rows) and ratios else None
    mean_residual = _mean([r for _, _, _, r, _ in rows])
    multipliers = [0.25, 0.5, 0.75, 0.9, 1.1, 1.25, 1.5, 2.0, 3.0, 4.0]
    if mean_ratio is not None and mean_ratio > 0:
        multipliers.extend((mean_ratio, 1.0 / mean_ratio))

    best: Optional[Tuple[float, str, float]] = None
    for name, value in params.items():
        candidates: List[float] = []
        if abs(value) > 1e-12:
            candidates.extend(value * m for m in multipliers)
        # Additive candidates, so a parameter sitting at zero can still move.
        step = abs(mean_residual) or 1.0
        candidates.extend(value + step * k
                          for k in (-2.0, -1.0, -0.5, 0.5, 1.0, 2.0))
        candidates.extend((value - mean_residual, value + mean_residual))

        for candidate in candidates:
            trial = dict(params)
            trial[name] = candidate
            score = _sse(kernel, trial, rows)
            if best is None or score < best[0]:
                best = (score, name, candidate)

    if best is None or best[0] >= base:
        return None

    # Refine the winning parameter locally. The coarse grid finds the basin; a
    # few bisection passes land in it, so the proposal is the value the evidence
    # actually implies rather than the nearest grid point to it.
    score, name, value = best
    span = abs(value - params[name]) or abs(value) or 1.0
    for _ in range(40):
        span /= 2.0
        for trial_value in (value - span, value + span):
            trial = dict(params)
            trial[name] = trial_value
            trial_score = _sse(kernel, trial, rows)
            if trial_score < score:
                score, value = trial_score, trial_value
        if span < 1e-12:
            break

    # Require a real improvement, not a rounding win.
    if score > base * 0.5:
        return None
    proposed = dict(params)
    proposed[name] = value
    return name, proposed


def diagnose(led: Ledger, kernel=None, min_survival: int = 1,
             min_supersessions: int = 2) -> Diagnosis:
    """Read the current claim's residuals and say what kind of wrong it is.

    Pass `kernel` (the same one the ledger runs) to have a parameter edit
    proposed where one is warranted; omit it for diagnosis only.
    `min_supersessions` is how many superseded versions it takes before the
    escape-hatch pattern counts as a pattern rather than a single answered
    refutation.
    """
    rows = _rows(led)
    signature, detail = classify_residuals(rows)
    patterns = PATTERNS.get(signature, ())

    if signature is Signature.HOLDING:
        return Diagnosis(signature, detail, len(rows), patterns=patterns,
                         refusal="the claim is not refuted; there is nothing to "
                                 "repair and repairing it anyway is retuning")

    # An already-thrashing claim gets no more suggestions, whatever the shape.
    # One supersession is the protocol working as designed -- a claim was
    # refuted and answered. A *pattern* needs repetition, so this only bites
    # from the second superseded version on.
    hatch = led.escape_hatch_flag(min_survival=min_survival)
    if hatch["flag"] and len(hatch["superseded_versions"]) >= min_supersessions:
        return Diagnosis(
            signature, detail, len(rows), patterns=patterns,
            refusal=(
                f"escape-hatch pattern: versions {hatch['thin_survival_versions']} "
                f"were superseded without surviving {min_survival} clean "
                "observation(s). The form is wrong, not the parameters -- stop "
                "re-parameterizing and restate the claim"
            ),
        )

    if signature not in _PARAMETRIC:
        return Diagnosis(
            signature, detail, len(rows), patterns=patterns,
            refusal=(
                f"a {signature.value} signature is not a parameter problem; "
                "proposing new numbers here would walk the claim away from a "
                "refutation it has not answered"
            ),
        )

    if kernel is None:
        return Diagnosis(signature, detail, len(rows), patterns=patterns,
                         refusal="no kernel supplied; cannot evaluate a proposal")

    found = _propose_single_param(kernel, dict(led.claim.params), rows)
    if found is None:
        return Diagnosis(
            signature, detail, len(rows), patterns=patterns,
            refusal="no single parameter accounts for the observations; that "
                    "the shape looked parametric does not make it so",
        )
    name, proposed = found
    return Diagnosis(signature, detail, len(rows), proposed_params=proposed,
                     proposed_param=name, patterns=patterns)


# --- the loop ---------------------------------------------------------------

class ClaimExplorer:
    """Diagnose -> edit -> look across domains -> rerun, with the brakes on.

        explorer = ClaimExplorer(led, kernel, oracle, conditions, tolerance)
        trace = explorer.explore()
        print(trace.summary())

    `oracle` is reality: a callable taking a condition and returning what
    actually happened. Every round re-observes the same `conditions`, so a
    proposed edit is tested against the evidence that refuted its predecessor
    rather than against fresh data chosen after the fact.
    """

    def __init__(self, ledger: Ledger, kernel, oracle: Oracle,
                 conditions: Sequence[Any], tolerance: float,
                 min_survival: int = 1, min_supersessions: int = 2) -> None:
        if tolerance <= 0:
            raise ValueError(f"tolerance must be > 0, got {tolerance}")
        if not conditions:
            raise ValueError("need at least one condition to explore")
        self.ledger = ledger
        self.kernel = kernel
        self.oracle = oracle
        self.conditions = list(conditions)
        self.tolerance = tolerance
        self.min_survival = min_survival
        self.min_supersessions = min_supersessions

    def observe(self) -> float:
        """Record every condition against the current claim; return worst |r|/tol."""
        worst = 0.0
        for condition in self.conditions:
            entry = self.ledger.record(
                condition=condition, observed=float(self.oracle(condition)),
                tolerance=self.tolerance, source="explorer",
            )
            worst = max(worst, abs(entry.mismatch.residual) / self.tolerance)
        return worst

    def explore(self, max_rounds: int = 5) -> Exploration:
        """Run the loop until the claim holds, or until it should stop."""
        trace = Exploration()
        for i in range(max_rounds):
            worst = self.observe()
            diagnosis = diagnose(self.ledger, self.kernel, self.min_survival,
                                 self.min_supersessions)
            version = self.ledger.claim.version

            if diagnosis.signature is Signature.HOLDING:
                trace.rounds.append(Round(i, diagnosis, False, version, worst))
                trace.outcome = "converged"
                return trace

            if not diagnosis.edit_warranted:
                trace.rounds.append(Round(i, diagnosis, False, version, worst))
                trace.outcome = f"halted: {diagnosis.signature.value}"
                return trace

            try:
                self.ledger.refute(
                    diagnosis.proposed_params,
                    rationale=(
                        f"explorer round {i}: {diagnosis.signature.value} "
                        f"signature over {diagnosis.rows} observations "
                        f"({diagnosis.detail}); moved {diagnosis.proposed_param}"
                    ),
                )
                applied = True
            except RefutationError:
                # The ledger's own gate refused -- it is the authority, not us.
                applied = False
            trace.rounds.append(Round(i, diagnosis, applied, version, worst))
            if not applied:
                trace.outcome = "halted: the ledger refused the update"
                return trace

        trace.outcome = f"exhausted after {max_rounds} rounds without converging"
        return trace
