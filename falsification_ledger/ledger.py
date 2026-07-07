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
    """

    statement: str
    params: Dict[str, float]
    version: int = 1
    parent: Optional[int] = None
    rationale: str = "initial claim"
    created_at: float = field(default_factory=time.time)


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

    def __init__(self, kernel: Kernel, claim: Claim) -> None:
        if claim.version != 1 or claim.parent is not None:
            raise ValueError("initial claim must be version 1 with no parent")
        self._kernel = kernel
        self._claim = claim
        self._entries: List[LedgerEntry] = []
        self._claims: List[Claim] = [claim]

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
        )
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
