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

**Threat model — read this.** The chain is tamper-**evident** against edits to
existing history, not tamper-**proof**: a party who can rewrite the whole file
can recompute every hash from any point forward, and there is no signature or
external anchor to stop them. For non-repudiation, sign the head hash
(`led.entries[-1].hash`) with a key the author doesn't control, or periodically
anchor it somewhere append-only outside the repo (a timestamping service, a
commit in a separate audited repo). Within a single trusted working copy, the
chain does its job: it catches accidental or after-the-fact edits.

## The structures

| structure | role |
|---|---|
| `Claim` | statement + params + `version` + `parent` + `rationale` + `refutation_set` + `extraordinary` + `scope` + `reference_class` + `logical_form` |
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

## Falsifiability guards

A refutation ledger is only as honest as the claims it accepts. Three optional
guards close the usual escape routes:

- **Up-front refutation set.** `Claim(..., refutation_set=[...])` names the
  observations that would refute the claim *before* you see the data.
  `claim.is_falsifiable` and `classify_falsifiability(claim)` report whether a
  claim commits to any. Open the ledger with `Ledger(..., strict_falsifiable=True)`
  to *refuse* an unfalsifiable claim outright (a `RefutationError`), at
  construction and at every `refute()`.
- **Extraordinary claims, higher bar.** `Claim(..., extraordinary=True)` marks a
  claim that overturns lower-layer knowledge; strict mode then requires **more
  than one** refuting condition — a mechanical Sagan standard.
- **Escape-hatch detector.** `led.escape_hatch_flag()` catches the pathology the
  protocol most fears: a claim re-parameterized again and again to dodge every
  refutation without ever surviving a clean observation. It returns a `flag`, the
  `escape_hatch_rate`, and the offending versions; `led.survival_by_version()`
  shows how many clean observations each version withstood. A high rate means the
  *form* of the claim is wrong, not its parameters.
- **Semantic specificity.** `Claim(..., reference_class=..., scope={...})` answers
  "true of what, where, when?": `reference_class` names the population the claim
  ranges over, and `scope` pins it along the canonical dimensions (`temporal`,
  `spatial`, `ontological`). `claim.is_specific` and `classify_specificity(claim)`
  report on it (the latter also lists missing scope dimensions and any hedge words
  via `find_vague_terms`). Open the ledger with `strict_scope=True` to refuse an
  under-specified claim, at construction and at every update.
- **Machine-checkable logical form.** `Claim(..., logical_form="...")` bridges the
  natural-language statement to something the ledger can *test*. Each `record()`
  checks the form against that row's own numbers (params + `predicted` / `observed`
  / `residual` / `tol`, with a scalar condition also bound as `x`) and stores the
  verdict as `entry.logical_ok` — part of the hash chain, and **independent** of
  the numeric tolerance, so a row can pass the tolerance yet violate the form
  (e.g. the fit stays exact while the claimed positive slope goes negative). The
  default checker is a safe stdlib evaluator (`evaluate_logical_form`) over a
  restricted grammar — arithmetic, comparisons (chained ok), `and`/`or`/`not`,
  and `abs`/`min`/`max` — that raises `LogicalFormError` on anything else (no
  `eval`, no attribute/subscript/import access). To go beyond arithmetic, pass
  your own solver: `Ledger(..., checker=my_z3_backend)` — `Checker` is just
  `Callable[[str, dict], bool]`. `strict_symbolic=True` refuses a claim with no
  logical form.

## Worked forks

- `examples/physics_ledger.py` — projectile range; recovers the true `g`.
- `examples/ecology_ledger.py` — logistic growth; recovers the true carrying
  capacity `K`.
- `examples/ai_behavior_ledger.py` — a model's refusal-rate threshold; the case
  the protocol most exists for.
- `examples/falsifiability_gate.py` — the three guards end to end: a strict
  ledger refusing a vague claim, and the escape-hatch detector catching a
  linear claim that reality keeps refuting because reality is quadratic.
- `examples/symbolic_form.py` — a machine-checkable `logical_form`; the symbolic
  read (`logical_ok`) flags a violated positive-slope invariant even while the
  numeric tolerance check is green.

Tests: `python -m unittest falsification_ledger.tests.test_ledger`
