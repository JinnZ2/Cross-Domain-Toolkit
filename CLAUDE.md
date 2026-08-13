# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

Cross-Domain-Toolkit is a collection of **portable, domain-general instruments**
— each a clean-room abstraction of a field-specific tool the author built
elsewhere, generalized so a researcher can instantiate it in a domain the
original never anticipated. There is no single application; each top-level
package stands alone.

The unifying method across all three packages: **ground your reads before you
trust them, record your refutations so you can't quietly rewrite them, and watch
for the structural point where a system's alternate state stops existing.**

## Conventions (hold these when adding or editing code)

- **stdlib-only Python 3 (≥ 3.8).** No third-party dependencies, no build step,
  no package manager. The 3.8 floor comes from `falsification_ledger/symbolic.py`
  alone (it reads literals as `ast.Constant`); everything else runs on 3.7. If a task seems to need a dependency, prefer a stdlib
  implementation or ask first. This is a hard constraint the whole toolkit relies
  on — it's what makes each package forkable and `model-update-resilient` in the
  author's phrasing.
- **The core never imports its plugins.** In `multi_substrate_calibration`, the
  determinacy gate consumes a fixed contract and never imports a specific
  substrate; in `cascade_regime_audit`, the detector takes six normalized signals
  and never knows the domain. Keep this inversion — it's what makes them
  plug-and-play. New domains live in `examples/`, not in the core module.
- **Abstractions expose the pattern, not a domain.** Each package ships worked
  `examples/` that map a real domain onto the abstract surface. When extending,
  add an example rather than special-casing the core.
- Each package is a Python package (`__init__.py` re-exports the public surface)
  with `examples/` and `tests/` subpackages. Every example is smoke-tested by its
  package's `tests/test_examples.py`; adding an example means adding its module
  name to that file's `EXAMPLES` tuple.

## Layout

| package | what it is | key entry points |
|---|---|---|
| `multi_substrate_calibration/` | intake contract + determinacy gate (Lε) for wiring new sensor substrates | `substrate.py` (contract), `determinacy_gate.py` (Lε decision), `fusion.py` (pure fusion math), `trust.py` (earned reliability from counts) |
| `falsification_ledger/` | append-only, hash-chained refutation ledger | `ledger.py` (`Claim`/`Prediction`/`Observation`/`Mismatch`/`Ledger`), `symbolic.py` (safe logical-form checker), `merkle.py` (audit certificates) |
| `cascade_regime_audit/` | abstract six-signal detector + spinodal threshold | `cascade_audit.py` (`CascadeAudit`, `SignalReads`, `H_SPINODAL`), `mappers.py` (series→signal helpers) |

## Commands

All stdlib; run from the repo root.

```bash
# run every test in the repo
python -m unittest discover -p 'test_*.py'

# run one package's tests
python -m unittest cascade_regime_audit.tests.test_cascade_audit

# run a single test case or method
python -m unittest falsification_ledger.tests.test_ledger.TestProtocol
python -m unittest multi_substrate_calibration.tests.test_multi_substrate.TestGate.test_confident_contradiction_drains_and_defers

# run any example (they're runnable modules)
python -m cascade_regime_audit.examples.institutional_fragility
```

## Design notes worth knowing before editing

- **`multi_substrate_calibration`** distinguishes two substrate roles: `GROUND`
  (sensorimotor read of the present) and `PREDICT` (cascade forecast). The gate
  fuses GROUND reads into a state estimate and holds PREDICT reads *against* it —
  a confident prediction that contradicts the ground drains determinacy (a
  PREDICT read can only ever lower determinacy, never inflate it). Confidence is
  bound into a shared frame (`bound = reliability * warp(native)`) before fusion.
  Corroboration is only credited across **independent** reads: a substrate names
  any shared error source in `correlation_group`, and reads sharing one are
  collapsed to a single effective read (`fusion.collapse_correlated`) before the
  noisy-OR sees them, so duplicating a sensor cannot manufacture determinacy.
  Before fusing, the gate enforces **unit commensurability** (GROUND reads must
  share units; PREDICT reads must match) and optional **physical `bounds`** (a
  fused estimate outside them forces `DEFER`). **Lε** is the final decision:
  `determinate iff determinacy ≥ 1 − ε`.
- **`falsification_ledger`** enforces one rule: *update the claim, never retune
  the sim.* `Ledger.refute()` raises `RefutationError` unless the most recent
  entry actually fell outside tolerance, so you can't advance the claim to fit
  noise. The hash chain (`verify()`) makes any later edit to recorded history
  detectable — that's what makes it an artifact rather than a notebook.
  Falsifiability guards are opt-in: a `Claim.refutation_set` names what would
  refute it up front, `strict_falsifiable=True` refuses unfalsifiable (or
  under-committed `extraordinary`) claims, and `escape_hatch_flag()` /
  `survival_by_version()` detect a claim being re-parameterized to dodge every
  refutation. Semantic-specificity guards mirror them: `Claim.scope` +
  `reference_class` (with `classify_specificity`/`find_vague_terms`) and
  `strict_scope=True` refuse a claim that doesn't say what/where/when it applies.
  A `Claim.logical_form` (checked each `record()` by a safe stdlib evaluator in
  `symbolic.py`, or a plugged-in `checker=` solver) records `entry.logical_ok`
  independently of the numeric tolerance; `strict_symbolic=True` requires a form.
  `merkle.py` adds third-party audit: `led.audit_certificate(i)` proves one entry
  against `led.merkle_root()` with `log₂(n)` sibling hashes, so an auditor checks
  a row without holding the ledger. Odd nodes are promoted, never duplicated
  (CVE-2012-2459). `sign_root` is HMAC — symmetric, so it proves authorship to a
  counterparty holding the key, not to the public; asymmetric signing would need
  a dependency the toolkit doesn't take.
- **`cascade_regime_audit`** keeps the *statistical* read (six signals →
  aggregate pressure) and the *structural* read (`h_eff` vs the spinodal `2/√27`)
  independent, because they fail in opposite directions. The `COMMITTED` regime
  is the important one: signals go quiet *after* the alternate state is already
  gone, so signals-alone would misread it as recovery. `2/√27` is the fold of the
  cusp *normal form*, not a universal constant — a domain reaches it through a
  change of variables, which is what `examples/cusp_atlas.py` supplies for eight
  fields (ratio 1.0 ↔ `H_SPINODAL`). **S5 is the signal people get backwards:**
  `coherence_under_contradiction` measures a system's *response* (coherence
  rising when contradicted = sealing), never disagreement itself — a fusion
  gate's conflict score is the `contradiction_level` input to
  `mappers.sealing_under_contradiction`, not the signal.

- **Cross-package wiring stays out of the core.** The three packages are
  standalone and none imports another; the seams are deliberately typed in plain
  numbers so they can meet in a caller. `trust.earned_reliability` takes hit/miss
  counts (a ledger can produce them; the calibration package never imports one),
  and `mappers.sealing_under_contradiction` takes coherence and contradiction
  levels (a gate's `GateResult.conflict` can supply the latter). Keep new bridges
  in that shape.

## Lineage (for fidelity when extending)

The math and vocabulary trace to the author's other repos: `cascade_regime_audit.py`
and `field_collapse.py` (`H_SPINODAL = 2/√27`) in
[`JinnZ2/JinnZ2`](https://github.com/JinnZ2/JinnZ2), the Kramers-escape
`monoculture_collapse_predictor`, and the refutation-protocol modules in
[`JinnZ2/ai-human-audit-protocol`](https://github.com/JinnZ2/ai-human-audit-protocol).
Those are the sources of truth for the underlying models; this repo is their
portable generalization.
