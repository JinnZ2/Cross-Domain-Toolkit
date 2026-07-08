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

- **stdlib-only Python 3.** No third-party dependencies, no build step, no
  package manager. If a task seems to need a dependency, prefer a stdlib
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
  with `examples/` and `tests/` subpackages.

## Layout

| package | what it is | key entry points |
|---|---|---|
| `multi_substrate_calibration/` | intake contract + determinacy gate (Lε) for wiring new sensor substrates | `substrate.py` (contract), `determinacy_gate.py` (fusion + Lε decision) |
| `falsification_ledger/` | append-only, hash-chained refutation ledger | `ledger.py` (`Claim`/`Prediction`/`Observation`/`Mismatch`/`Ledger`) |
| `cascade_regime_audit/` | abstract six-signal detector + spinodal threshold | `cascade_audit.py` (`CascadeAudit`, `SignalReads`, `H_SPINODAL`) |

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
  refutation.
- **`cascade_regime_audit`** keeps the *statistical* read (six signals →
  aggregate pressure) and the *structural* read (`h_eff` vs the spinodal `2/√27`)
  independent, because they fail in opposite directions. The `COMMITTED` regime
  is the important one: signals go quiet *after* the alternate state is already
  gone, so signals-alone would misread it as recovery.

## Lineage (for fidelity when extending)

The math and vocabulary trace to the author's other repos: `cascade_regime_audit.py`
and `field_collapse.py` (`H_SPINODAL = 2/√27`) in
[`JinnZ2/JinnZ2`](https://github.com/JinnZ2/JinnZ2), the Kramers-escape
`monoculture_collapse_predictor`, and the refutation-protocol modules in
[`JinnZ2/ai-human-audit-protocol`](https://github.com/JinnZ2/ai-human-audit-protocol).
Those are the sources of truth for the underlying models; this repo is their
portable generalization.
and `field_collapse.py` (`H_SPINODAL = 2/√27`) in `JinnZ2/JinnZ2`, the
Kramers-escape `monoculture_collapse_predictor`, and the refutation-protocol
modules in `JinnZ2/ai-human-audit-protocol`. Those are the sources of truth for
the underlying models; this repo is their portable generalization.


Review this repository against its CLAUDE.md and produce REVIEW.md.
Focus on:

1. **Structural consistency with CLAUDE.md:**
   - Are all three packages true Python packages with __init__.py re-exporting public surfaces?
   - Do examples/ and tests/ subpackages exist for each?
   - Is the "core never imports plugins" rule upheld across all modules? Flag any violation.
   - Are there any imports of third-party libraries? (stdlib-only is a hard constraint.)

2. **README & discoverability:**
   - Does the README concisely explain what all three packages do, with one-line summaries?
   - Missing: CITATION.cff, KEYWORDS.txt, repository topics, "Why This Matters" statement, license badge. Provide ready-to-paste snippets for each.
   - Is the public API import example clear for all three entry points?

3. **Obvious inconsistencies:**
   - Duplicate or conflicting docstrings, mismatched function signatures, broken internal links.
   - Inconsistent naming conventions across packages.
   - Missing tests for documented entry points.

4. **Documentation gaps:**
   - Does each package have at least one worked example in examples/ that maps a real domain onto the abstract surface?
   - Is the "refutation protocol" clearly described in falsification_ledger's README or module docstring?
   - Are the six signals in cascade_regime_audit named and explained?

5. **Repository topics suggestion:** 
   Propose topics like: `falsifiability`, `scientific-audit`, `refutation`, `spinodal`, `sensor-fusion`, `determinacy`, `grounding`, `python-stdlib`.

Keep sections concise. Output the full REVIEW.md.
