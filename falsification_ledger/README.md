# Falsification Ledger

A repo-shaped template that *is* the refutation protocol. Fork it for any
domain — physics, ecology, AI behavior — and get the same discipline as data:

```
Claim  ->  Prediction  ->  Reality  ->  Mismatch  ->  (updated Claim)
```

## The one rule it enforces

**Update the claim, never retune the sim.**

- The **sim** is a pure kernel `predict(params, condition) -> value`. It is
  fixed for a domain. The ledger never edits a recorded prediction.
- The **claim** carries the params. When a mismatch lands outside tolerance, the
  only legal move is `refute(...)`: register a new claim *version* with new
  params and a stated rationale. The old version, its predictions, and the
  mismatch that refuted it stay in the record forever.

`Ledger.refute()` raises `RefutationError` if you try to advance the claim when
the last observation was *within* tolerance — i.e. it mechanically refuses
"retune the story to fit noise."

## Why it's an artifact, not a notebook

The log is **append-only and hash-chained** (SHA-256, stdlib only). Every entry
commits to the hash of the one before it, so any later edit — quietly changing a
prediction to match what happened, deleting an embarrassing entry — breaks the
chain and `verify()` returns `False`. The refutation history is *verifiable*,
not asserted. That is exactly the property you want when the claims are about,
say, how an AI system behaves.

## The structures

| structure | role |
|---|---|
| `Claim` | statement + params + `version` + `parent` + `rationale` |
| `Prediction` | value + tolerance derived from a claim version (immutable) |
| `Observation` | reality: what actually happened under a condition |
| `Mismatch` | residual, tolerance, `refuted` flag |
| `LedgerEntry` | one immutable, hash-linked row tying the four together |
| `Ledger` | append-only log; `record()`, `refute()`, `verify()`, `to_json()` |

## Fork it in four lines

```python
from falsification_ledger import Claim, Ledger

def kernel(params, condition):      # 1. your sim (fixed)
    return params["a"] * condition + params["b"]

led = Ledger(kernel, Claim("y = a x + b", {"a": 2.0, "b": 0.0}))  # 2. your claim
entry = led.record(condition=3.0, observed=15.0, tolerance=0.5)   # 3. meet reality
if entry.mismatch.refuted:
    led.refute({"a": 5.0, "b": 0.0}, rationale="entry 0: slope wrong")  # 4. update claim
```

`led.to_json()` serializes the whole chain so you can commit the ledger itself as
the record of what was claimed, when it broke, and how the claim changed.

## Worked forks

- `examples/physics_ledger.py` — projectile range; recovers the true `g`.
- `examples/ecology_ledger.py` — logistic growth; recovers the true carrying
  capacity `K`.
- `examples/ai_behavior_ledger.py` — a model's refusal-rate threshold; the case
  the protocol most exists for.

Tests: `python -m unittest falsification_ledger.tests.test_ledger`
