# Repository Review — Cross-Domain-Toolkit

_Reviewed against `CLAUDE.md` on branch `claude/new-session-207rva`. Every
behavioural claim below was confirmed by running the code on Python 3.11.15, not
inferred. Line numbers refer to the files at review time._

**Baseline:** `python -m unittest discover -p 'test_*.py'` → **82 tests, OK**. All
nine example modules run clean. Every command in `CLAUDE.md` ("Commands") was
executed and works, including the single-method and single-class invocations.

_This file supersedes the earlier review (whose items were resolved in commits
`05dbd43` and prior); that version remains in git history._

| Section | Result |
|---|---|
| 1. Structural consistency with CLAUDE.md | **Clean** — no violations |
| 2. Defects | 9 (1 high, 1 medium, 7 low/info) |
| 3. Missing tests for documented entry points | 5 |
| 4. Documentation gaps | **Clean** — all four checks pass |
| 5. Discoverability | 4 gaps, snippets below |

---

## 1. Structural consistency with CLAUDE.md

All four structural rules hold. Nothing to fix here.

- **True packages with re-exporting `__init__.py`:** all three. Each declares an
  explicit `__all__` and a `py.typed` marker.
- **`examples/` and `tests/` subpackages:** present in all three, each with an
  `__init__.py` (empty, as intended).
- **"The core never imports its plugins":** **upheld everywhere.** No module
  under a package root imports from that package's `examples/`.
  `determinacy_gate.py` imports only `.fusion` and `.substrate` (the contract),
  never a substrate; `cascade_audit.py` imports nothing from the package at all
  and does not even import `mappers.py` — the comment at `cascade_audit.py:111`
  states the inversion explicitly. The only cross-example import is
  `examples/acoustic_substrate.py` → `ThermalProbe`, which is example→example and
  is what makes the GROUND/PREDICT contradiction demo work.
- **stdlib-only:** verified by a full import scan. The complete third-party
  surface is empty; the whole toolkit imports only `ast`, `dataclasses`, `enum`,
  `hashlib`, `json`, `math`, `operator`, `time`, `typing`, and `unittest`.

---

## 2. Defects

### D1 — `DeterminacyGate.evaluate` crashes on all-zero-confidence GROUND reads · **high**
`fusion.py:29-34` · `determinacy_gate.py:128-133, 153`

`weighted_mean` returns `None` when the weights sum to `≤ 0`, so `fuse_ground`
returns `(None, 0.0)`. `evaluate` then uses that `state` unguarded. Two crash
paths, both reproduced:

```python
g = BoundReading(SubstrateReading(300.0, 0.0, Role.GROUND, "thermal", "K"), 0.0)
DeterminacyGate(bounds=(0.0, 1000.0)).evaluate([g])
# TypeError: '<=' not supported between instances of 'float' and 'NoneType'
DeterminacyGate(predict_tolerance=2.0).evaluate([g, predict_read])
# TypeError: unsupported operand type(s) for -: 'float' and 'NoneType'
```

This is reachable through a **documented, supported** configuration: `substrate.py:84-86`
and both READMEs promise that an unproven substrate (`reliability → 0`) "cannot
dominate the gate no matter how loudly it reports certainty." Binding such a read
yields `bound_confidence = 0.0`, and one of those is enough. Without `bounds` and
without a PREDICT read it happens to survive (it DEFERs with
`state_estimate=None`, which is correct), so the bug is invisible in the
narrowest path only. Fix — treat "no confidence anywhere in the ground layer" as
its own DEFER, right after the fuse at `determinacy_gate.py:128`:

```python
state, ground_determinacy = fuse_ground([(r.value, r.bound_confidence) for r in ground])
if state is None:
    return GateResult(
        verdict=Verdict.DEFER, state_estimate=None, determinacy=0.0,
        epsilon=self.epsilon,
        reason="every GROUND read bound to zero confidence: nothing is anchored",
        ground_count=len(ground), predict_count=len(predict), conflict=0.0,
    )
```

### D2 — The stated Python floor (3.7) is wrong; `symbolic.py` needs 3.8 · **medium**
`README.md:20, 68` · `CONTRIBUTING.md:7` · `falsification_ledger/symbolic.py:57`

`_eval` dispatches literals on `ast.Constant`. CPython's parser did not emit
`ast.Constant` for literals until 3.8 — on 3.7 `ast.parse("a > 0")` produces an
`ast.Num` node, which falls through every branch and raises
`LogicalFormError("construct Num is not permitted")`. So on 3.7 any logical form
containing a number — i.e. essentially all of them, including the README's own
`"a > 0 and abs(residual) <= tol"` — fails. (Verified on 3.11 here; 3.7 is not
installable in this environment, so this rests on the documented parser change,
not on execution.) Everything else in the repo is genuinely 3.7-safe. Cheapest
fix is to state the real floor in `README.md`, `CONTRIBUTING.md`, and `CLAUDE.md`:

```
Requires Python ≥ 3.8 (no third-party dependencies).
```

### D3 — Unused import `field` · **low**
`cascade_regime_audit/cascade_audit.py:44` — `from dataclasses import dataclass, field`;
no `field(...)` call exists in the module (the word only appears in prose). Drop it.

### D4 — Unused import `LogicalFormError` · **low**
`falsification_ledger/ledger.py:38` imports `LogicalFormError` and never
references it. The package re-export at `__init__.py:20` comes straight from
`.symbolic`, so removing it from `ledger.py` changes no public surface.

### D5 — `GateResult.gap` is still dead surface · **low**
`determinacy_gate.py:59-62` defines `gap`; `evaluate` then recomputes the same
quantity as a local at line 165 for its reason strings. The property is
referenced by no module, example, or test. Use it and delete the local:

```python
gap = result_gap = threshold - determinacy   # or simply build GateResult first
```

Simplest: keep the property and have the DEFER branch read `(1 - epsilon) - determinacy`
once — the two must not be allowed to drift apart.

### D6 — `falsification_ledger/__init__.py` docstring lists half the public surface · **low**
`falsification_ledger/__init__.py:1-5` names seven exports; `__all__` exports
fourteen. Missing from the docstring: `SCOPE_DIMENSIONS`, `classify_falsifiability`,
`classify_specificity`, `find_vague_terms`, `Checker`, `LogicalFormError`,
`evaluate_logical_form`. The other two packages' docstrings do match their
`__all__`, so this is the odd one out. Replace with:

```
Public surface:
    Claim, Prediction, Observation, Mismatch, LedgerEntry, Ledger, RefutationError
    guards: SCOPE_DIMENSIONS, classify_falsifiability, classify_specificity,
            find_vague_terms
    symbolic: Checker, LogicalFormError, evaluate_logical_form
```

Note also that `Observation` appears in `__all__` but not in the docstring list,
and the `Kernel` type alias (`ledger.py:41`) is public-by-use but unexported —
worth adding if forkers are meant to type their kernels.

### D7 — `multi_substrate_calibration/README.md` "Files" omits `fusion.py` · **low**
The Files section lists `substrate.py`, `determinacy_gate.py`, both examples, and
`tests/test_multi_substrate.py`, but not `fusion.py` or `tests/test_fusion.py`,
both added in the extraction refactor. `CLAUDE.md`'s layout table already lists
`fusion.py`, so the package README is the stale one.

### D8 — Half-applied alias convention in `mappers.py` · **low**
`mappers.py:87-96` keeps `slowing_down_from_series` / `variance_inflation_from_series`
as back-compat aliases for `lag1_autocorr` / `normalized_variance`, so S1 and S2
have two public names each while `abs_skew` and `coefficient_of_variation` (S3,
S4) have one. Six exported names for four functions, and a reader can't tell
which is canonical. Either alias all four or mark the two aliases deprecated in
their docstrings and point at the canonical name.

### D9 — Asymmetric guard re-checks in `restate()` · **info**
`ledger.py:445` re-runs `_require_specific` on the revised claim but not
`_require_falsifiable` or `_require_symbolic`, while `refute()` (`:419-421`) runs
all three. Harmless today — `restate` inherits `refutation_set` and `logical_form`
unchanged from the claim `refute()` just validated — but the asymmetry is a trap
the moment `restate` gains the ability to revise those fields.

---

## 3. Missing tests for documented entry points

The suite is strong (82 cases) and covers each package's headline behaviour. The
gaps:

1. **`GateResult.gap`** — a public property with no test at all (see D5).
2. **The `state is None` path through `evaluate`** — `test_fusion.TestWeightedMean.test_zero_weight_returns_none`
   covers `weighted_mean` in isolation, but nothing drives that return value
   through the gate, which is why D1 survived.
3. **`Substrate.bound_read` modality mismatch** (`substrate.py:152-154`) — the
   sibling role-mismatch branch is tested (`test_role_mismatch_rejected`); the
   modality branch is not.
4. **`Ledger.check_logical_form`** — a public method exercised only indirectly
   through `record()`; no test calls it with an explicit binding.
5. **Example smoke tests** — `CONTRIBUTING.md` tells contributors "Add a test
   under `your_package/tests/test_*.py`" for each new example, but no test
   imports or runs any of the nine existing examples. A ~10-line test per package
   that runs each example module would make that rule self-enforcing:

```python
import runpy, unittest

class TestExamplesRun(unittest.TestCase):
    def test_examples_execute(self):
        for name in ("model_collapse", "institutional_fragility"):
            runpy.run_module(f"cascade_regime_audit.examples.{name}",
                             run_name="__main__")
```

---

## 4. Documentation gaps

All four checks pass; no gaps found.

- **A worked example per package mapping a real domain onto the abstract
  surface:** yes, nine of them — `multi_substrate_calibration` (thermal GROUND,
  acoustic PREDICT), `falsification_ledger` (physics, ecology, AI behavior, plus
  the falsifiability-gate and symbolic-form walkthroughs), `cascade_regime_audit`
  (model collapse, institutional fragility). Each maps a named domain, each is
  runnable, each runs clean.
- **The refutation protocol:** described in three places consistently — the
  `ledger.py` module docstring, `falsification_ledger/README.md` ("The one rule
  it enforces"), and `docs/METHOD.md` §2. The README also carries an honest
  **threat model** paragraph distinguishing tamper-evident from tamper-proof,
  which is the right caveat and is rarely present in work like this.
- **The six signals:** named and explained twice — as an annotated list in the
  `cascade_audit.py` module docstring (S1–S6) and as a table in
  `cascade_regime_audit/README.md`, with the non-obvious one
  (`coherence_under_contradiction`: rising coherence is a *red* signal) called
  out in both. `SIGNAL_NAMES` matches the `SignalReads` field names exactly.
- **README package summaries and the public API import example:** all three
  packages get a one-line summary and a linked heading, and the "Quick import"
  block covers all three entry points. Verified: every symbol in that block
  imports.

Minor style note, not a gap: the YAML front matter at `README.md:1-9` renders as
a metadata table on github.com rather than being hidden. It's deliberate (crawler
bait) and harmless, but be aware it is visible to human readers.

---

## 5. Discoverability — status and ready-to-paste snippets

| item | status |
|---|---|
| `CITATION.cff` | present, but the author block is malformed — fix below |
| `KEYWORDS.txt` | a `KEYWORDS.md` exists; add `.txt` only if you want the plaintext form |
| Repository topics | **not set** — no topics on the repo |
| "Why This Matters" | **present** (`README.md:25-32`) — no action |
| License badge | **missing** |
| Repo description | `"Cross domain toolkit "` — generic, and has a trailing space |

### 5.1 `CITATION.cff` (replace the existing file)

The current author block uses `name-particle: ""`, which is not a valid CFF value
(the field must be omitted when empty), and a person entry without `given-names`
is under-specified. For a pseudonymous author, an entity entry is the correct
shape. Also adds `type`, `url`, and the missing `spinodal`/`determinacy` keywords:

```yaml
cff-version: 1.2.0
message: "If you use this toolkit, please cite it."
title: "Cross-Domain-Toolkit"
abstract: "Portable, stdlib-only Python instruments for claim falsification,
  sensor-fusion calibration, and cascade/tipping-point detection."
type: software
authors:
  - name: "JinnZ2"
    alias: "JinnZ2"
repository-code: "https://github.com/JinnZ2/Cross-Domain-Toolkit"
url: "https://github.com/JinnZ2/Cross-Domain-Toolkit"
license: MIT
version: "0.1.0"
date-released: "2026-07-08"
keywords:
  - falsification
  - refutation
  - scientific-audit
  - early-warning-signals
  - tipping-points
  - spinodal
  - sensor-fusion
  - determinacy
  - grounding
  - ai-grounding
  - python-stdlib
```

### 5.2 `KEYWORDS.txt`

`KEYWORDS.md` already carries this content. If you want the plaintext file the
brief asks for, keep **one** of the two as canonical to avoid drift — the `.txt`
below is the same list, one term per line, which is friendlier to `grep` and to
crawlers than a prose blob:

```
falsification ledger
refutation protocol
claim verification
hash-chained audit log
sensor fusion
multi-substrate calibration
confidence binding
determinacy gate
epsilon-determinacy
grounding vs prediction
cascade regime audit
six-signal early-warning detector
critical slowing down
variance inflation
flickering
diversity collapse
spinodal threshold (2/sqrt(27))
saddle-node bifurcation
tipping point
model collapse detection
institutional fragility
AI grounding
stdlib-only Python
```

### 5.3 Repository topics

Not currently set. Suggested set (GitHub allows up to 20; these are all real,
searched topics):

```
falsifiability  scientific-audit  refutation  spinodal  sensor-fusion
determinacy  grounding  python-stdlib  early-warning-signals  tipping-points
critical-transitions  cascade-detection  model-collapse  ai-safety
claim-verification  hash-chain  no-dependencies
```

Set them in **Settings → About → Topics**, or:

```bash
gh api -X PUT repos/JinnZ2/Cross-Domain-Toolkit/topics \
  -f names[]=falsifiability -f names[]=scientific-audit -f names[]=refutation \
  -f names[]=spinodal -f names[]=sensor-fusion -f names[]=determinacy \
  -f names[]=grounding -f names[]=python-stdlib -f names[]=early-warning-signals \
  -f names[]=tipping-points -f names[]=critical-transitions \
  -f names[]=cascade-detection -f names[]=model-collapse -f names[]=ai-safety \
  -f names[]=claim-verification -f names[]=hash-chain -f names[]=no-dependencies
```

While there, replace the description with something a search result can use:

```
Stdlib-only Python instruments for claim falsification, sensor-fusion
calibration, and cascade/tipping-point (spinodal) detection — portable across
physics, ecology, and AI-behavior domains.
```

### 5.4 License and status badges

Paste directly under the `# Cross-Domain-Toolkit` heading in `README.md`:

```markdown
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![Dependencies: none](https://img.shields.io/badge/dependencies-none%20(stdlib%20only)-brightgreen.svg)](CONTRIBUTING.md)
[![Tests: 82](https://img.shields.io/badge/tests-82%20passing-brightgreen.svg)](#running)
```

The Python badge says 3.8 per **D2**; change it back to 3.7 only if `symbolic.py`
is made to accept `ast.Num`. The test-count badge is static — either keep it
current by hand or drop it; a stale count is worse than none.

---

## Suggested order of work

1. **D1** — the only defect that raises on a documented configuration.
2. **D2** — the version floor, since it silently breaks the newest feature on the
   oldest supported interpreter.
3. §5.3 topics + description, §5.4 badges, §5.1 `CITATION.cff` — five minutes,
   all discoverability.
4. **D3–D8** — small, mechanical, and each has a one-line fix.
5. §3 tests 1–3, which pin **D1** and **D5** so they cannot come back.

_End of review._
