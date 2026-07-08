"""ledger.py -- an executable falsification ledger. stdlib only.

A ledger you can fork for any domain -- physics, ecology, AI behavior -- and get
the same discipline: the refutation protocol, made mechanical.

    Claim  ->  Prediction  ->  Reality  ->  Mismatch  ->  (updated Claim)

THE ONE RULE THIS FILE ENFORCES
-------------------------------
When reality disagrees with a prediction you **update the claim, never retune
the sim**. Concretely:

  * The *sim* is a pure kernel function `predict(params, condition) -> value`.
    It is fixed for a domain. The ledger never edits a recorded prediction.
  * The *claim* carries the params. When a mismatch lands outside tolerance, the
    only legal move is to register a NEW claim version with new params and a
    stated rationale. The old version, its predictions, and the mismatch that
    refuted it stay in the record forever.

The log is append-only and hash-chained (like a tiny blockchain, stdlib hashlib
only), so "I quietly rewrote the prediction to match" is detectable: any edit to
history breaks the chain. That is what makes this an *artifact* and not a
notebook -- the refutation history is verifiable, not asserted.

Fork it: define your kernel `predict(params, condition)`, write your first
`Claim`, and drive `Ledger.record(...)` with real observations. Everything else
is domain-independent.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional

# A kernel is a pure function of (params, condition) -> predicted value.
Kernel = Callable[[Dict[str, float], Any], float]


@dataclass(frozen=True)
class Claim:
    """A falsifiable claim: a statement plus the params its predictions run on.

    `version` increments on each refutation. `parent` links to the version this
    one replaced (None for the first). `rationale` is why the update happened --
    it must cite the mismatch, never "to fit the data" in the hand-tuning sense.

    `refutation_set` names, *in advance*, the observations that would refute the
    claim -- the conditions you commit to testing before you see the data. A
    claim that cannot name a single one is unfalsifiable (see `is_falsifiable`
    and `classify_falsifiability`); the ledger can refuse to open on one in
    strict mode. `extraordinary=True` marks a revolutionary claim that overturns
    lower-layer knowledge; strict mode holds it to a higher bar (more refutation
    conditions), a mechanical Sagan standard.
    """

    statement: str
    params: Dict[str, float]
    version: int = 1
    parent: Optional[int] = None
    rationale: str = "initial claim"
    created_at: float = field(default_factory=time.time)
    refutation_set: List[Any] = field(default_factory=list)
    extraordinary: bool = False

    def __post_init__(self) -> None:
        # Defensive copies: a caller who keeps a reference to the dict/list they
        # passed in must not be able to mutate a claim out from under a recorded
        # entry (which would silently retune the sim). Recorded history is
        # additionally protected by the hash chain.
        object.__setattr__(self, "params", dict(self.params))
        object.__setattr__(self, "refutation_set", list(self.refutation_set))

    @property
    def is_falsifiable(self) -> bool:
        """A claim is falsifiable iff it commits, up front, to at least one
        observation that would refute it."""
        return len(self.refutation_set) > 0


def classify_falsifiability(claim: "Claim") -> Dict[str, Any]:
    """Classify a claim as falsifiable or not, with a reason. A tiny, honest
    heuristic -- it checks that the claim names refuting observations up front,
    and (for extraordinary claims) that it names more than one."""
    if not claim.is_falsifiable:
        return {
            "falsifiable": False,
            "reason": "no refutation_set: the claim names nothing that would refute it",
        }
    if claim.extraordinary and len(claim.refutation_set) < 2:
        return {
            "falsifiable": False,
            "reason": (
                "extraordinary claim with a single refutation condition; an "
                "extraordinary claim should expose more than one way to be wrong"
            ),
        }
    return {
        "falsifiable": True,
        "reason": f"{len(claim.refutation_set)} refutation condition(s) declared",
    }


@dataclass(frozen=True)
class Prediction:
    """A prediction derived from a claim for a specific condition. Immutable."""

    claim_version: int
    condition: Any
    value: float
    tolerance: float  # how far reality may fall before the claim is refuted


@dataclass(frozen=True)
class Observation:
    """Reality. What actually happened under `condition`."""

    condition: Any
    value: float
    source: str = "unspecified"
    observed_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class Mismatch:
    """The gap between prediction and reality."""

    residual: float          # observed - predicted
    tolerance: float
    within_tolerance: bool

    @property
    def refuted(self) -> bool:
        return not self.within_tolerance


@dataclass
class LedgerEntry:
    """One immutable row: claim version, prediction, reality, mismatch, and the
    hash chain link that makes the row tamper-evident."""

    index: int
    claim: Claim
    prediction: Prediction
    observation: Observation
    mismatch: Mismatch
    prev_hash: str
    hash: str = ""
    recorded_at: float = field(default_factory=time.time)

    def digest(self) -> str:
        payload = {
            "index": self.index,
            "claim": asdict(self.claim),
            "prediction": asdict(self.prediction),
            "observation": asdict(self.observation),
            "mismatch": asdict(self.mismatch),
            "prev_hash": self.prev_hash,
            "recorded_at": self.recorded_at,
        }
        blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()


class RefutationError(Exception):
    """Raised when someone tries to break the protocol -- e.g. advancing the
    claim without a genuine refutation, or editing recorded history."""


class Ledger:
    """The append-only falsification ledger.

    Usage per domain:
        led = Ledger(kernel=my_predict, claim=Claim("...", {"k": 1.0}))
        entry = led.record(condition=..., observed=..., tolerance=..., source=...)
        if entry.mismatch.refuted:
            led.refute(new_params={"k": 1.4}, rationale="entry %d ..." % entry.index)
    """

    GENESIS_HASH = "0" * 64

    def __init__(self, kernel: Kernel, claim: Claim,
                 strict_falsifiable: bool = False) -> None:
        if claim.version != 1 or claim.parent is not None:
            raise ValueError("initial claim must be version 1 with no parent")
        self.strict_falsifiable = strict_falsifiable
        self._require_falsifiable(claim)
        self._kernel = kernel
        self._claim = claim
        self._entries: List[LedgerEntry] = []
        self._claims: List[Claim] = [claim]

    def _require_falsifiable(self, claim: Claim) -> None:
        """In strict mode, refuse to work with an unfalsifiable claim. This is the
        falsifiability gate: a claim that names nothing that would refute it (or
        an extraordinary claim that names too little) cannot enter the ledger."""
        if not self.strict_falsifiable:
            return
        verdict = classify_falsifiability(claim)
        if not verdict["falsifiable"]:
            raise RefutationError(f"unfalsifiable claim rejected: {verdict['reason']}")

    # --- reads ---
    @property
    def claim(self) -> Claim:
        return self._claim

    @property
    def entries(self) -> List[LedgerEntry]:
        return list(self._entries)

    @property
    def claim_history(self) -> List[Claim]:
        return list(self._claims)

    def predict(self, condition: Any, tolerance: float) -> Prediction:
        """Run the fixed sim under the current claim's params. Pure; records
        nothing."""
        value = float(self._kernel(dict(self._claim.params), condition))
        return Prediction(
            claim_version=self._claim.version,
            condition=condition,
            value=value,
            tolerance=tolerance,
        )

    # --- the append-only write ---
    def record(self, condition: Any, observed: float, tolerance: float,
               source: str = "unspecified") -> LedgerEntry:
        """Predict, confront with reality, append an immutable entry. This never
        edits the sim or a past prediction -- it only appends."""
        prediction = self.predict(condition, tolerance)
        observation = Observation(condition=condition, value=float(observed), source=source)
        residual = observation.value - prediction.value
        mismatch = Mismatch(
            residual=residual,
            tolerance=tolerance,
            within_tolerance=abs(residual) <= tolerance,
        )
        prev_hash = self._entries[-1].hash if self._entries else self.GENESIS_HASH
        entry = LedgerEntry(
            index=len(self._entries),
            claim=self._claim,
            prediction=prediction,
            observation=observation,
            mismatch=mismatch,
            prev_hash=prev_hash,
        )
        entry.hash = entry.digest()
        self._entries.append(entry)
        return entry

    # --- the only legal way to move the claim ---
    def refute(self, new_params: Dict[str, float], rationale: str) -> Claim:
        """Advance the claim to a new version. Legal ONLY when the most recent
        entry actually refuted the current claim. This is the mechanism that
        forces "update the claim, never retune the sim": you cannot reach in and
        change a prediction, you can only supersede the claim, on the record.
        """
        if not self._entries:
            raise RefutationError("nothing observed yet; no refutation to answer")
        last = self._entries[-1]
        if last.claim.version != self._claim.version:
            raise RefutationError("most recent entry does not test the current claim")
        if not last.mismatch.refuted:
            raise RefutationError(
                "most recent entry is within tolerance; the claim is not refuted, "
                "so you may not retune it (that would be fitting the sim to noise)"
            )
        new_claim = Claim(
            statement=self._claim.statement,
            params=dict(new_params),
            version=self._claim.version + 1,
            parent=self._claim.version,
            rationale=rationale,
            # the falsification conditions persist across a parameter update
            refutation_set=list(self._claim.refutation_set),
            extraordinary=self._claim.extraordinary,
        )
        self._require_falsifiable(new_claim)
        self._claim = new_claim
        self._claims.append(new_claim)
        return new_claim

    def restate(self, statement: str, new_params: Dict[str, float],
                rationale: str) -> Claim:
        """Like `refute`, but also revises the claim's wording -- for when the
        mismatch shows the claim was not just mis-parameterized but mis-stated.
        Same precondition: the last entry must have refuted the current claim."""
        base = self.refute(new_params, rationale)
        revised = Claim(
            statement=statement,
            params=base.params,
            version=base.version,
            parent=base.parent,
            rationale=rationale,
            created_at=base.created_at,
            refutation_set=list(base.refutation_set),
            extraordinary=base.extraordinary,
        )
        self._claim = revised
        self._claims[-1] = revised
        return revised

    # --- verification: the point of the hash chain ---
    def verify(self) -> bool:
        """Return True iff the recorded history is intact -- no entry edited, no
        prediction quietly retuned, no row deleted."""
        prev = self.GENESIS_HASH
        for i, e in enumerate(self._entries):
            if e.index != i or e.prev_hash != prev or e.digest() != e.hash:
                return False
            prev = e.hash
        return True

    # --- escape-hatch detection (the falsifiability paradox in practice) ---
    def survival_by_version(self) -> Dict[int, int]:
        """How many within-tolerance observations each claim version survived
        before it was superseded (or, for the current version, so far). A version
        that keeps getting refuted after surviving 0 tests is being retuned to
        dodge refutation rather than genuinely holding up."""
        survival: Dict[int, int] = {c.version: 0 for c in self._claims}
        for e in self._entries:
            if e.mismatch.within_tolerance:
                survival[e.claim.version] = survival.get(e.claim.version, 0) + 1
        return survival

    def escape_hatch_flag(self, min_survival: int = 1) -> Dict[str, Any]:
        """Detect the escape-hatch pattern: a claim repeatedly superseded without
        ever surviving `min_survival` clean observations. Returns a flag plus the
        superseded versions that failed to clear the bar. High incidence means the
        claim is being re-parameterized to escape every refutation -- the
        practical face of the falsifiability paradox.
        """
        survival = self.survival_by_version()
        superseded = [c.version for c in self._claims if c.version != self._claim.version]
        thin = [v for v in superseded if survival.get(v, 0) < min_survival]
        rate = (len(thin) / len(superseded)) if superseded else 0.0
        return {
            "flag": bool(superseded) and rate >= 0.5,
            "superseded_versions": superseded,
            "thin_survival_versions": thin,
            "escape_hatch_rate": rate,
            "min_survival": min_survival,
        }

    # --- serialization: commit the ledger as data ---
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(
            {
                "claim_history": [asdict(c) for c in self._claims],
                "entries": [
                    {
                        "index": e.index,
                        "claim_version": e.claim.version,
                        "prediction": asdict(e.prediction),
                        "observation": asdict(e.observation),
                        "mismatch": asdict(e.mismatch),
                        "prev_hash": e.prev_hash,
                        "hash": e.hash,
                        "recorded_at": e.recorded_at,
                    }
                    for e in self._entries
                ],
            },
            indent=indent,
            default=str,
        )
