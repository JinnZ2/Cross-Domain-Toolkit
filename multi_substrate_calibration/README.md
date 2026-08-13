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
| `correlation_group` | name of an error source shared with another substrate; `""` = independent |
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
  single weak read can force it down. Corroboration only counts across
  *independent* reads: see below.
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

### Independence: corroboration has to be earned

The noisy-OR rule treats every read as a fresh chance to have been wrong, which
is only true when the reads *could have failed separately*. Two thermocouples on
one power rail, two forecasters trained on one corpus, two feeds derived from one
upstream source — poll them both and a naive noisy-OR reports `0.96` determinacy
on `0.8` of evidence. A gate whose whole purpose is refusing unearned certainty
would be manufacturing it.

So a substrate declares any error source it shares:

```python
class RailProbe(Substrate):
    modality, role, units = "thermal", Role.GROUND, "K"
    correlation_group = "rail-a"        # "" (the default) means independent
```

Reads in one group are collapsed to a **single effective read** before fusion —
their confidence-weighted centre, carrying the group's *best* confidence, not
their combination. Independent reads are untouched and corroborate exactly as
before. The result reports what happened:

```python
res.ground_count            # 3 reads arrived
res.effective_ground_count  # 2 independent ones survived the collapse
res.collapsed_reads         # 1 was absorbed as a duplicate
```

Perfectly correlated reads carry one read's worth of information however many of
them there are. Partial correlation is the caller's to model — split the group,
or discount the members' `reliability`.

### Earned reliability: where the number comes from

`Calibration.reliability` is asserted by the caller, which is a problem for a
package whose whole pitch is that an unproven substrate can't dominate the gate —
if reliability is asserted, "unproven" is exactly what nobody has to admit to.
`trust.py` closes that loop from a substrate's track record:

```python
from multi_substrate_calibration import earned_reliability, eligible_for_ground

probe.calibration = Calibration(reliability=earned_reliability(hits=18, misses=2))
eligible_for_ground(hits=18, misses=2)      # -> True
eligible_for_ground(hits=3, misses=0)       # -> False: three observations
```

The estimator is the Beta posterior mean `(hits + 1) / (hits + misses + 2)`, so
2/2 earns `0.75` rather than `1.0` and no record at all sits at `0.5` — silence
costs something. `reliability_interval` reports how thin the record is, which is
what separates "0.75 because it's mediocre" from "0.75 because we've barely
watched it."

These functions take **counts, not ledgers**. Where the track record lives — a
falsification ledger, a CSV, a held-out eval — is yours; this package never
imports it, which is what keeps it forkable on its own.

### Grounding guards (unit commensurability + physical bounds)

Before it fuses anything, the gate enforces that the reads are actually
groundable:

- **Unit commensurability.** All GROUND reads must share `units`, and any PREDICT
  read must match the ground's units — fusing `K` with `°C` silently produces a
  meaningless estimate, so the gate raises `ValueError` rather than average them.
- **Lower-layer bounds.** Pass `DeterminacyGate(bounds=(lo, hi))` and a fused
  estimate that escapes the physically possible range forces a `DEFER` with an
  explaining reason — the reads are *incoherent*, not merely uncertain, and no
  amount of confidence should certify an impossible state.

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
- `determinacy_gate.py` — substrate-agnostic routing + the Lε decision.
- `fusion.py` — the pure fusion math (`combine_independent`, `weighted_mean`,
  `fuse_ground`, `contradiction_drain`, `collapse_correlated`), split out so the
  gate reads as "collapse → fuse → decide" and the agreement-vs-drain policy is
  testable on its own.
- `trust.py` — earned reliability from a track record (`earned_reliability`,
  `reliability_interval`, `eligible_for_ground`, `rank_substrates`). Takes counts,
  never a ledger.
- `examples/thermal_substrate.py` — a GROUND substrate, end to end.
- `examples/acoustic_substrate.py` — a PREDICT substrate; shows a contradicting
  forecast draining determinacy.
- `tests/test_multi_substrate.py`, `tests/test_fusion.py`, `tests/test_trust.py`,
  `tests/test_examples.py` — `python -m unittest discover -p 'test_*.py'`
