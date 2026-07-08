# Multi-Substrate Calibration Protocol

A published spec for wiring a **new sensing substrate** into a determinacy gate
without reverse-engineering the gate. Implement one small contract and your
thermal, acoustic, market, or logit feed routes into **Lε** (the
epsilon-determinacy layer) automatically. Plug-and-play by construction: the
gate never imports a substrate, so adding one changes zero lines of gate code.

## The intake pattern (what a new sensor feed must look like)

Every substrate emits reads in **one fixed shape**, the `SubstrateReading`:

| field | meaning |
|---|---|
| `value` | the measured or predicted quantity, in native units |
| `native_confidence` | the substrate's own confidence, in `[0, 1]` |
| `role` | `GROUND` (sensorimotor read of *what is*) or `PREDICT` (cascade forecast of *what will be*) |
| `modality` | channel tag: `"thermal"`, `"acoustic"`, `"logit"`, … |
| `units` | documentation frame for `value` |
| `timestamp` / `provenance` | when, and where from |

That fixed shape is what makes the gate substrate-agnostic — a thermocouple and
a cascade forecaster are indistinguishable to it once they speak this shape.

## The confidence-binding contract

A raw `0.9` from a thermocouple and a `0.9` from a forecaster are **not
comparable**. Each substrate supplies a `Calibration` that binds its native
confidence into the shared frame:

```
bound = reliability * warp(native_confidence)
```

- `reliability` — the substrate's demonstrated hit rate (e.g. `1 − Brier` on
  held-out data). An unproven substrate (`reliability → 0`) **cannot dominate
  the gate** no matter how loudly it reports certainty.
- `warp` — an optional monotonic reshaping of the native confidence curve
  (identity by default).

Only **bound** confidence enters the gate, so heterogeneous feeds become
commensurable: after binding, `0.9` from any substrate means the same thing —
"act on this and you're wrong ~10% of the time."

## Two grounding layers, and how they route to Lε

- **GROUND** reads are fused into a single present-state estimate
  (confidence-weighted mean) and their bound confidences combine by a
  noisy-OR rule into a **determinacy score** — corroboration raises it, and no
  single weak read can force it down.
- **PREDICT** reads are **not** averaged into the present, and they can only ever
  *lower* determinacy, never raise it. They are held against the fused ground: a
  forecast within `predict_tolerance` passes without penalty (it corroborates but
  adds no determinacy the ground did not itself earn); a confident forecast that
  *contradicts* the ground becomes a determinacy **drain**. This is what stops a
  forecast from being laundered into an observation.

`predict_tolerance` (default `1.0`) is the agree/drain boundary, expressed in the
units of the ground state's own scale, and **must be > 0** — the gate rejects a
non-positive value at construction. A PREDICT read within one tolerance-width of
the fused ground agrees; beyond it, the drain grows with both the read's bound
confidence and its distance.

**Lε** then asks one question:

```
determinate  iff  determinacy ≥ 1 − ε
```

`ε` is your tolerance for acting on incomplete grounding. Tight `ε` (0.02) =
"act only when nearly certain"; loose `ε` (0.3) = "act on a working hypothesis."
When indeterminate, Lε returns `DEFER` with a reason and the gap (how far
determinacy fell short of `1 − ε`), telling you whether to gather more GROUND
reads, resolve a GROUND/PREDICT conflict, or widen `ε`.

## Adding a substrate (the entire integration surface)

```python
from multi_substrate_calibration import Substrate, Role, Calibration, make_reading

class ThermalProbe(Substrate):
    modality, role, units = "thermal", Role.GROUND, "K"
    def __init__(self, snr):
        super().__init__(Calibration(reliability=0.95))
        self.snr = snr
    def read(self):
        native = self.snr / (self.snr + 1.0)
        return make_reading(self, 300.0 + self._adc(), native)
```

Then feed it to the gate — which never had to know thermal existed:

```python
from multi_substrate_calibration import DeterminacyGate
gate = DeterminacyGate(epsilon=0.1, predict_tolerance=2.0)
result = gate.evaluate([probe_a.bound_read(), probe_b.bound_read()])
# result.verdict -> Verdict.DETERMINATE / DEFER
```

## Files

- `substrate.py` — the intake contract: `SubstrateReading`, `Role`,
  `Calibration`, `Substrate`, `make_reading`.
- `determinacy_gate.py` — substrate-agnostic fusion + the Lε decision.
- `examples/thermal_substrate.py` — a GROUND substrate, end to end.
- `examples/acoustic_substrate.py` — a PREDICT substrate; shows a contradicting
  forecast draining determinacy.
- `tests/test_multi_substrate.py` — `python -m unittest
  multi_substrate_calibration.tests.test_multi_substrate`
