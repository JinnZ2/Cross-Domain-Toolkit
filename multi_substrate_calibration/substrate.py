"""substrate.py -- the plug-and-play intake contract for a new sensing substrate.

stdlib only. No framework, no I/O assumptions. A "substrate" is anything that
emits a read about the world: a thermal probe, an acoustic array, a market feed,
a model's own logits. The determinacy gate does not care what the substrate is
made of -- it only cares that every substrate speaks the same three-part
contract below, so heterogeneous feeds become commensurable and route into Le
(the epsilon-determinacy layer) without the gate being rewritten.

THE CONTRACT (what a new substrate MUST provide)
------------------------------------------------
1. SHAPE. Every read is a `SubstrateReading`: a value in a stated frame, a
   timestamp, a native confidence in [0, 1], a role, and provenance. Same shape
   for a thermocouple and a cascade forecaster. That fixed shape is what makes
   the gate substrate-agnostic.

2. ROLE. A substrate serves exactly one of two grounding roles:
     GROUND  -- a direct sensorimotor read of the current state ("what is").
     PREDICT -- a cascade/forecast read of a future or latent state ("what will
                be, if the current dynamics hold").
   The gate fuses GROUND reads to establish the present and treats PREDICT reads
   as claims to be checked against that present. Mixing the two blindly is how a
   forecast masquerades as an observation; the role tag prevents it.

3. CONFIDENCE BINDING. A raw sensor confidence is not comparable across
   substrates -- a thermocouple's "0.9" and a forecaster's "0.9" mean different
   things. Each substrate supplies a `bind()` calibration that maps its native
   confidence into the SHARED confidence frame by folding in the substrate's
   demonstrated reliability (its track record). After binding, a 0.9 from any
   substrate means the same thing: "if I act on this, I am wrong ~10% of the
   time." Only bound confidence enters the gate.

To add a substrate: subclass `Substrate`, implement `read()`, declare `role`,
`modality`, and a `Calibration`. That is the entire integration surface.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional, Sequence


class Role(Enum):
    """Which grounding layer a substrate feeds."""

    GROUND = "ground"      # direct sensorimotor read of the present state
    PREDICT = "predict"    # cascade / forecast read of a latent or future state


@dataclass(frozen=True)
class SubstrateReading:
    """The fixed shape every substrate must emit. This is the only currency the
    determinacy gate accepts."""

    value: float                      # the measured/predicted quantity, native units
    native_confidence: float          # substrate's own confidence in [0, 1]
    role: Role                        # GROUND or PREDICT
    modality: str                     # "thermal", "acoustic", "logit", ...
    units: str                        # "K", "dB", "nat", ... (documentation frame)
    timestamp: float = field(default_factory=time.time)
    provenance: dict = field(default_factory=dict)  # sensor id, location, raw payload

    def __post_init__(self) -> None:
        if not 0.0 <= self.native_confidence <= 1.0:
            raise ValueError(
                f"native_confidence must be in [0, 1], got {self.native_confidence}"
            )


@dataclass
class Calibration:
    """The confidence-binding contract, made concrete.

    `reliability` is the substrate's demonstrated hit rate in the shared frame
    (e.g. from a held-out Brier score: reliability = 1 - Brier). `warp` is an
    optional monotonic reshaping of the substrate's native confidence curve
    (identity by default). Binding composes the two so that a native confidence
    is discounted by how much the substrate has actually earned trust.

    bound = reliability * warp(native_confidence)

    This keeps the map monotonic in native confidence and bounded in [0, 1],
    and guarantees an unproven substrate (reliability -> 0) cannot dominate the
    gate no matter how loudly it reports certainty.
    """

    reliability: float = 1.0                     # demonstrated hit rate in [0, 1]
    warp: Callable[[float], float] = lambda c: c  # monotonic reshape of native curve

    def __post_init__(self) -> None:
        if not 0.0 <= self.reliability <= 1.0:
            raise ValueError(f"reliability must be in [0, 1], got {self.reliability}")

    def bind(self, native_confidence: float) -> float:
        """Map a native confidence into the shared confidence frame."""
        c = float(self.warp(native_confidence))
        c = min(1.0, max(0.0, c))
        return self.reliability * c


@dataclass
class BoundReading:
    """A SubstrateReading after confidence binding. This is what the gate fuses."""

    reading: SubstrateReading
    bound_confidence: float

    @property
    def value(self) -> float:
        return self.reading.value

    @property
    def role(self) -> Role:
        return self.reading.role


class Substrate:
    """Base class for a sensing substrate. Subclass and implement `read()`.

    Integration surface (all a new substrate needs to declare):
      - modality:    str tag for the physical/informational channel
      - role:        Role.GROUND or Role.PREDICT
      - units:       documentation frame for the value
      - calibration: Calibration carrying the confidence-binding contract
      - read():      returns a SubstrateReading

    Everything downstream -- fusion, the Le determinacy decision -- is handled
    by the gate and never needs to know what this substrate is.
    """

    modality: str = "abstract"
    role: Role = Role.GROUND
    units: str = "arb"

    def __init__(self, calibration: Optional[Calibration] = None) -> None:
        self.calibration = calibration or Calibration()

    def read(self) -> SubstrateReading:  # pragma: no cover - abstract
        raise NotImplementedError("a substrate must implement read()")

    def bound_read(self) -> BoundReading:
        """Read and immediately bind confidence into the shared frame. This is the
        method the gate calls; subclasses should not override it."""
        r = self.read()
        if r.role is not self.role:
            raise ValueError(
                f"reading role {r.role} disagrees with declared substrate role {self.role}"
            )
        if r.modality != self.modality:
            raise ValueError(
                f"reading modality {r.modality!r} disagrees with declared {self.modality!r}"
            )
        return BoundReading(reading=r, bound_confidence=self.calibration.bind(r.native_confidence))


def make_reading(
    substrate: Substrate,
    value: float,
    native_confidence: float,
    provenance: Optional[dict] = None,
) -> SubstrateReading:
    """Helper so substrate authors don't have to restate role/modality/units on
    every read -- they come from the substrate's own declaration."""
    return SubstrateReading(
        value=value,
        native_confidence=native_confidence,
        role=substrate.role,
        modality=substrate.modality,
        units=substrate.units,
        provenance=provenance or {},
    )
