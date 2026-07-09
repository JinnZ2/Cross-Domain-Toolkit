# Repository Review — Cross-Domain-Toolkit

_Reviewed at branch `claude/claude-md-docs-h2hwb5`. All line numbers refer to the
files as they existed **at review time**. Behavioural findings were confirmed by
running the code, not inferred._

> **Resolution status (updated after fixes).** All of Section 1 (inconsistencies),
> all of Section 3 (code audit), all of Section 2 (markdown gaps), and most of
> Section 6 (discoverability) have been addressed in follow-up commits; the test
> suite grew from 22 to 46 cases. Finding 3.3 was fixed with a defensive copy
> rather than `MappingProxyType` (the latter breaks `dataclasses.asdict`, which
> the ledger's `digest()`/`to_json()` rely on — verified empirically).
>
> **Section 5 — now largely implemented.** 5.2 grounding: the gate enforces unit
> commensurability and optional physical `bounds` (a fused estimate outside them
> DEFERs). 5.4 falsifiability: `Claim.refutation_set` + `is_falsifiable` +
> `classify_falsifiability`, a `strict_falsifiable` ledger mode, an
> `extraordinary`-claim higher bar, and an `escape_hatch_flag()` /
> `survival_by_version()` refutation-velocity detector. 5.3 semantic ambiguity:
> `Claim.scope` + `reference_class`, `classify_specificity` / `find_vague_terms`,
> and a `strict_scope` ledger mode (see `examples/falsifiability_gate.py`). Still
> open by design: 5.1 symbolic logical-form extraction / solver connection.
>
> Still open (larger changes, not yet done): the Section 4 structural refactors
> beyond `CONTRIBUTING.md`/`Makefile` (4.1, 4.3, 4.4, 4.6). Line numbers below
> are pre-fix and may have shifted. Section 6 topics still require a manual
> GitHub setting.

## Findings summary

| Section | Findings |
|---|---|
| 1. Inconsistencies | 4 |
| 2. Markdown Information Gaps | 7 |
| 3. Code Audit | 10 |
| 4. Organizational Structure | 6 |
| 5. Limitations Mitigation | 5 items (0 fully addressed, 4 partial, ~8 sub-items missing) |
| 6. Discoverability & Crawler Optimization | 9 |

---

## 1. Inconsistencies

**1.1 — Unused import `Sequence`** · `multi_substrate_calibration/substrate.py:42`
`from typing import Callable, Optional, Sequence` — `Sequence` is never
referenced in the file. Fix:
```python
from typing import Callable, Optional
```

**1.2 — Documented contract contradicts actual behaviour: agreeing PREDICT reads
raise determinacy** · `multi_substrate_calibration/determinacy_gate.py:14-17,
133, 139`
The module docstring states PREDICT reads "are NOT fused into the present" and a
prediction is only ever a *drain*, never "a boost." But an agreeing prediction is
added to `agree_conf` (line 133) and folded into `_combine_independent` (line
139), which **raises** determinacy. Confirmed empirically:

| reads | determinacy | verdict |
|---|---|---|
| one GROUND @ conf 0.7 | 0.70 | DEFER |
| same GROUND + agreeing PREDICT @ 0.9 | 0.97 | **DETERMINATE** |

A forecast that merely agrees with a single weak ground read flips the gate from
"defer" to "act" — precisely the "forecast laundered into an observation" the
design says it prevents. Either document that agreement corroborates (and soften
the docstring), or cap agreement so it cannot exceed what the ground earned:
```python
determinacy = ground_determinacy
if agree_conf:
    # corroboration may reassure, but must not manufacture determinacy the
    # ground layer did not itself establish
    determinacy = min(1.0, ground_determinacy + (1.0 - ground_determinacy)
                      * max(agree_conf) * 0.5)   # or drop the boost entirely
determinacy *= (1.0 - conflict)
```

**1.3 — `GateResult.gap` is dead surface** · `determinacy_gate.py:58-61`
The `gap` property is defined but never used in any `reason` string, example, or
test. Either surface it in the DEFER reason (`f"...gap {result.gap:.3f}"`) or
remove it. Currently it silently duplicates logic already implied by
`determinacy` and `epsilon`.

**1.4 — Duplicate identically-named example helper** · `cascade_regime_audit/examples/model_collapse.py:16`
and `cascade_regime_audit/examples/institutional_fragility.py:16`
Both define `def read_signals(...)` with the same name but different bodies. Not a
runtime conflict (separate modules), but it invites copy-paste confusion. Minor;
consider `read_model_signals` / `read_institution_signals` for grep-ability.

---

## 2. Markdown Information Gaps

**2.1 — No stated minimum Python version.** README and CLAUDE.md say "stdlib-only
Python 3" but the code uses `from __future__ import annotations` and dataclasses
(3.7+) and f-strings (3.6+). _Intent:_ tell a forker what interpreter they need.
Add "Requires Python ≥ 3.7 (no third-party dependencies)" to the README Running
section.

**2.2 — `predict_tolerance` semantics undocumented.** `multi_substrate_calibration/README.md`
mentions the gate but never states that `predict_tolerance` must be positive, is
in the units of the ground state's scale, and controls the agree/drain boundary.
_Intent:_ a user wiring a PREDICT substrate needs this to set the knob. Document
it alongside `epsilon`.

**2.3 — Agreement-boost behaviour not mentioned in package README.** Tied to
finding 1.2: the README says predictions are "held against" the ground but omits
that an agreeing prediction raises determinacy. _Intent:_ the README should match
whatever behaviour is settled on.

**2.4 — Lineage references have no links.** `README.md` "Lineage" and
`CLAUDE.md` "Lineage" name `JinnZ2/JinnZ2`, `field_collapse.py`,
`ai-human-audit-protocol`, `monoculture_collapse_predictor` but link to none of
them. _Intent:_ let a reader follow the sources of truth. Add URLs.

**2.5 — Helper functions documented but never demonstrated.** `cascade_regime_audit/README.md`
advertises `slowing_down_from_series` and `variance_inflation_from_series`, but
no example calls them. _Intent:_ show the raw-series → signal mapping. Add a short
snippet or an example that feeds a time series.

**2.6 — No CONTRIBUTING / CHANGELOG.** For a toolkit explicitly meant to be
forked and extended ("New domains live in `examples/`"), there is no note on how
to add an example, run tests, or what "done" looks like. _Intent:_ smooth
onboarding. A 10-line `CONTRIBUTING.md` would suffice (see 4.5).

**2.7 — Hash-chain guarantee is overstated without a caveat.** `falsification_ledger/README.md`
("a quietly rewritten prediction breaks the chain") is true for a *partial* edit,
but a holder with write access can recompute the entire chain from any point —
there is no signature or external anchor. _Intent:_ be honest about the threat
model. Add: "The chain is tamper-**evident** against edits to existing history,
not tamper-**proof**: a party who can rewrite the whole file can rebuild every
hash. For non-repudiation, sign `verify()`'s head hash or anchor it externally."

---

## 3. Code Audit

**3.1 — `predict_tolerance` is not validated; ≤ 0 silently breaks the gate**
· `multi_substrate_calibration/determinacy_gate.py:95-99, 131` — **bug (high)**
`__init__` validates `epsilon` but not `predict_tolerance`. Confirmed: with
`predict_tolerance=-2.0`, a PREDICT read of 500 against a ground state of 5
yields `determinacy=1.0, conflict=0.0, verdict=DETERMINATE` — a gross
contradiction reported as certainty. With `predict_tolerance=0.0`, line 131's
`... if self.predict_tolerance else 0.0` sets `dist=0`, so **every** prediction
counts as perfect agreement. Fix:
```python
def __init__(self, epsilon: float = 0.1, predict_tolerance: float = 1.0) -> None:
    if not 0.0 < epsilon < 1.0:
        raise ValueError(f"epsilon must be in (0, 1), got {epsilon}")
    if predict_tolerance <= 0.0:
        raise ValueError(f"predict_tolerance must be > 0, got {predict_tolerance}")
    self.epsilon = epsilon
    self.predict_tolerance = predict_tolerance
```
Then line 131 simplifies to `dist = abs(p.value - state) / self.predict_tolerance`.

**3.2 — Agreeing prediction can manufacture determinacy** · `determinacy_gate.py:133,139`
— **logic bug (medium)**. See finding 1.2 for the confirmed DEFER→DETERMINATE
flip and the suggested cap.

**3.3 — `Claim` is `frozen=True` but `params` is a mutable dict** · `falsification_ledger/ledger.py:41-56`
— **integrity gap (medium)**. `frozen=True` blocks attribute reassignment but not
in-place mutation: `led.claim.params["g"] = 999` bypasses the refutation protocol
for the live (not-yet-recorded) claim. Recorded entries are protected by the hash
chain, but the invariant "params only change via `refute()`" is not enforced on
the current claim. Fix: store params behind a read-only view.
```python
from types import MappingProxyType
def __post_init__(self):
    object.__setattr__(self, "params", MappingProxyType(dict(self.params)))
```
(then `refute`/`restate` already pass a fresh `dict(new_params)`).

**3.4 — `CascadeAudit.__init__` validates nothing** · `cascade_regime_audit/cascade_audit.py:157-163`
— **robustness (medium)**. `fire_threshold`, `pressure_threshold`, and
`spinodal` accept any float; there's no check they're in `[0, 1]` (thresholds) or
`> 0` (spinodal). A caller passing `pressure_threshold=50` silently never fires
`STRESSED`/`CASCADE`. Fix: add range checks mirroring `SignalReads.__post_init__`.

**3.5 — Unknown/typo'd weight keys are silently dropped** · `cascade_audit.py:163,167,170`
— **silent failure (low/medium)**. `self.weights.get(n, 0.0)` iterates over
`SIGNAL_NAMES`, so a weights dict with a misspelled key (`"vareince_inflation"`)
contributes nothing and is never flagged; the mistyped signal just gets weight 0.
Fix: validate keys on construction.
```python
if weights:
    unknown = set(weights) - set(SIGNAL_NAMES)
    if unknown:
        raise ValueError(f"unknown signal weights: {sorted(unknown)}")
```

**3.6 — All-zero weights yield `pressure=0` with no warning** · `cascade_audit.py:167-170`
— **robustness (low)**. `weights={n: 0 for n in ...}` returns pressure 0.0 for any
signal, quietly disabling the detector. The `wsum <= 0` guard prevents a
ZeroDivisionError but masks the misconfiguration. Consider raising instead of
returning 0.

**3.7 — `restate()` has no test coverage** · `falsification_ledger/ledger.py:223-239`
— **missing test (medium)**. It is part of the public surface (referenced by
docstring) yet exercised by no test. It also mutates `self._claims[-1]` after
`refute()` appended it; a regression here would silently corrupt claim history.
Add a test asserting version/parent/statement and `verify()` still True.

**3.8 — Thin test coverage on error and serialization paths** · **missing tests (medium)**.
No test covers: negative/zero `predict_tolerance` (3.1); `Ledger.to_json()`
round-trip / determinism; `variance_inflation_from_series`; the `provenance`
plumbing in `make_reading`; `CascadeAudit` threshold validation. These are the
paths most likely to regress silently.

**3.9 — `_normalized_variance` mapping is arbitrary and undocumented** · `cascade_audit.py`
`variance_inflation_from_series` → `1 - 1/ratio` — **maintainability (low)**. The
squashing curve is not derived or explained; a maintainer can't tell whether
`0.5` at `ratio=2` is intentional. Add a one-line rationale or cite the
early-warning literature it approximates.

**3.10 — No security issues found in the conventional sense.** stdlib-only; no
`eval`/`exec`, no subprocess, no network, no file writes, no deserialization of
untrusted input, no secrets. `json.dumps(..., default=str)` on the ledger is
safe. The only "security-adjacent" concern is the ledger threat model
(non-repudiation), covered in 2.7.

---

## 4. Organizational Structure Suggestions

**4.1 — Split `multi_substrate_calibration` fusion math out of the gate.** The
`_combine_independent` / `_weighted_mean` helpers plus the PREDICT scoring in
`determinacy_gate.py:64-140` mix _fusion policy_ with _decision policy_. Extract
fusion into `fusion.py` so the Lε decision in `DeterminacyGate.evaluate` reads as
"fuse → decide." _Why:_ the agreement-vs-drain logic (findings 1.2/3.2) is where
the subtle bugs live; isolating it makes it independently testable.

**4.2 — Add a top-level `tests/` aggregation or a `Makefile`/`tox.ini`.** Tests
live under each package (`*/tests/`), which is fine, but there is no single
canonical entry beyond the discover command. A 3-line `Makefile`
(`test:` → `python -m unittest discover -p 'test_*.py'`) lowers onboarding
friction. _Why:_ new contributors look for `make test` first.

**4.3 — Promote the shared "refutation protocol" vocabulary into one place.** All
three packages narrate the same philosophy (ground / refute / cascade) in prose
headers. A short `docs/METHOD.md` (or a top-of-repo section) stating the shared
method once, with each package linking to it, removes the triplicated
explanation. _Why:_ single source of truth; the packages already gesture at a
unifying idea.

**4.4 — Consider a `py.typed` marker + consistent type exports.** The code is
fully type-hinted but ships no `py.typed`, so downstream type-checkers ignore it.
Adding an empty `py.typed` to each package makes the toolkit typecheck-friendly
for forkers. _Why:_ cheap, and the annotations are already there.

**4.5 — Add minimal `CONTRIBUTING.md` describing the "add an example" workflow.**
The design rule "new domains live in `examples/`, not the core" is stated in
CLAUDE.md but not where a contributor looks. _Why:_ codifies the one architectural
constraint that keeps the core plugin-free.

**4.6 — Keep `examples/` runnable but move reusable mapping helpers up.**
`slowing_down_from_series` / `variance_inflation_from_series` live in the core
(good), but the per-example `read_signals` mappers (findings 1.4) are the real
reusable pattern. Consider a `cascade_regime_audit/mappers.py` with documented,
tested reference mappers, leaving examples as thin drivers. _Why:_ examples become
demonstrations, not the only home for mapping logic.

---

## 5. Limitations Mitigation Checklist

_Treating the toolkit as an AI-grounding / claim-verification system
(`falsification_ledger` + `multi_substrate_calibration` are the relevant cores)._

### 5.1 Symbolic–Subsymbolic Gap — **MISSING**
- Explicit extraction of logical form: **missing.** `Claim.statement` is free
  text (`ledger.py:44`); nothing parses it.
- Connection to symbolic solvers: **missing.**
- _Recommendation:_ add an optional `logical_form` field and a solver hook:
  ```python
  @dataclass(frozen=True)
  class Claim:
      statement: str
      params: Dict[str, float]
      logical_form: Optional[str] = None   # e.g. "forall x: R(x) = k * f(x)"
      ...
  # and a pluggable checker: Callable[[str], bool] the ledger can call before record()
  ```

### 5.2 Grounding Problem — **PARTIALLY ADDRESSED** _(units + bounds now implemented; see banner)_
- Units/dimensions checked: **partial.** `SubstrateReading.units` exists
  (`substrate.py:61`) but is a documentation string only — never validated or
  reconciled across fused reads. Two GROUND reads in different units fuse
  silently.
- Lower-layer constraints enforced: **missing.** No mechanism prevents a fused
  estimate from violating a physical bound.
- Meta-grounding flag for revolutionary claims: **missing.**
- _Recommendation:_ enforce unit agreement in `DeterminacyGate.evaluate` before
  fusing (`{r.reading.units for r in ground}` must be size 1, else raise), and add
  a `bounds: Optional[Tuple[float,float]]` to the gate that DEFERs if the estimate
  escapes. For revolutionary claims, add a `Claim.extraordinary: bool` that
  requires a higher refutation bar.

### 5.3 Semantic Ambiguity — **NOW ADDRESSED** _(scope + reference_class + vague-term detector + strict_scope; see banner)_
- Vague terms quantified: **missing.** No mechanism forces "high", "fragile",
  etc. into numbers (the cascade signals are numeric, but the _claims_ are not).
- Scope (temporal/spatial/ontological) explicit: **missing.** `Claim` carries no
  scope; `condition` is arbitrary.
- Reference class specified: **missing.**
- _Recommendation:_ add structured `scope: Dict[str, str]` and a required
  `reference_class: str` to `Claim`; reject claims lacking them if a strict flag
  is set.

### 5.4 Falsifiability Paradox — **NOW ADDRESSED** _(refutation_set + classifier + strict mode + escape-hatch; see banner)_
- Enumerate a refutation-observation set: **partial.** The ledger tests one
  observation at a time against a tolerance (`ledger.py:171-193`) but never asks
  the claim to _enumerate in advance_ what would refute it.
- Escape-hatch detector: **missing.** Nothing detects a claim being repeatedly
  re-parameterized to dodge every refutation (unbounded `refute()` chains are
  allowed).
- Falsifiable/unfalsifiable classifier: **missing.**
- _Recommendation:_ require a `refutation_set: List[condition]` on `Claim` and
  refuse to open a ledger for a claim with an empty one (an unfalsifiable claim);
  track a "refutation velocity" and warn when a claim is updated more often than
  it survives (the escape-hatch signal).

### 5.5 Formal Verification vs. Complexity — **PARTIALLY ADDRESSED**
- Formal proof scoped: **missing.** The hash chain is integrity, not proof.
- Background knowledge accessible: **missing.** No knowledge base is wired in.
- Probabilistic fallback with confidence: **addressed.** `DeterminacyGate`
  produces a `determinacy` score and the Lε decision is an explicit probabilistic
  gate (`determinacy_gate.py:139-145`); the ledger records tolerances. This is the
  one sub-item genuinely covered.
- _Recommendation:_ keep the determinacy/Lε path as the probabilistic fallback,
  and scope any future formal check to the `logical_form` from 5.1 so proof is
  attempted only where a formal form exists, with the determinacy score as the
  documented fallback everywhere else.

---

## 6. Discoverability & Crawler Optimization

**6.1 — "What is this?" summary: PARTIAL.** The README opens with a good one-liner
but it is prose-dense and light on high-signal keywords a crawler indexes
(e.g. "early-warning signals", "critical transition", "tipping point",
"calibration", "sensor fusion", "provenance"). Add a keyworded lead sentence:
```markdown
> **Cross-Domain-Toolkit** — stdlib-only Python instruments for **claim
> falsification**, **sensor-fusion calibration**, and **cascade / tipping-point
> (spinodal) detection**, portable across physics, ecology, and AI-behavior
> domains.
```

**6.2 — Repository topics: NOT SET (add via GitHub UI/API).** Suggested topics:
`python`, `stdlib`, `falsification`, `early-warning-signals`, `tipping-points`,
`critical-transitions`, `sensor-fusion`, `calibration`, `ai-safety`,
`claim-verification`, `spinodal`, `cascade-detection`.

**6.3 — `KEYWORDS.md`: MISSING.** Ready to paste as `KEYWORDS.md`:
```markdown
# Keywords
falsification ledger, refutation protocol, claim verification, hash-chained
audit log, sensor fusion, multi-substrate calibration, confidence binding,
determinacy gate, epsilon-determinacy, grounding vs prediction, cascade regime
audit, six-signal early-warning detector, critical slowing down, variance
inflation, flickering, diversity collapse, spinodal threshold (2/sqrt(27)),
saddle-node bifurcation, tipping point, model collapse detection, institutional
fragility, AI grounding, stdlib-only Python.
```

**6.4 — `CITATION.cff`: MISSING.** Ready to paste as `CITATION.cff`:
```yaml
cff-version: 1.2.0
message: "If you use this toolkit, please cite it."
title: "Cross-Domain-Toolkit"
abstract: "Portable, stdlib-only Python instruments for claim falsification,
  sensor-fusion calibration, and cascade/tipping-point detection."
authors:
  - family-names: "JinnZ2"
    name-particle: ""
repository-code: "https://github.com/JinnZ2/Cross-Domain-Toolkit"
license: MIT
version: "0.1.0"
date-released: "2026-07-08"
keywords:
  - falsification
  - early-warning-signals
  - tipping-points
  - sensor-fusion
  - ai-grounding
```

**6.5 — "Why This Matters" / urgency statement: MISSING.** Ready to paste into the
README:
```markdown
## Why this matters
Systems fail quietly: a model trained on its own output loses diversity before
its metrics move; an institution consolidates authority before it visibly breaks;
a claim gets retuned to fit noise instead of being refuted. These tools make each
of those moments **legible and on-the-record** — grounded reads, tamper-evident
refutations, and a structural signal for when the alternative state is already
gone.
```

**6.6 — Structured metadata (YAML frontmatter / JSON-LD): MISSING.** Ready to
paste at the very top of `README.md` (many crawlers parse leading frontmatter):
```markdown
---
title: Cross-Domain-Toolkit
description: Stdlib-only Python for claim falsification, sensor-fusion
  calibration, and cascade/tipping-point detection.
keywords: [falsification, early-warning-signals, tipping-points, sensor-fusion,
  ai-grounding, spinodal]
license: MIT
language: Python
---
```

**6.7 — Public API one-liner import: PARTIAL.** Package READMEs show imports, but
the top-level README has no single copy-paste line. Add:
```markdown
## Quick import
```python
from falsification_ledger import Claim, Ledger
from multi_substrate_calibration import DeterminacyGate, Substrate, Role
from cascade_regime_audit import CascadeAudit, SignalReads, H_SPINODAL
```
```

**6.8 — Open license clearly marked: ADDRESSED.** `LICENSE` (MIT) is present and
the README states "MIT licensed (copyright JinnZ2)." Consider adding an SPDX tag
(`SPDX-License-Identifier: MIT`) to each module header for machine detection.

**6.9 — Anonymous feedback mechanism (issue templates): MISSING.** Ready to paste
as `.github/ISSUE_TEMPLATE/feedback.md`:
```markdown
---
name: Feedback / question
about: Ask a question, report a domain that didn't map cleanly, or flag a bug
title: "[feedback] "
labels: feedback
---
**What were you trying to do?**

**Which package?** (multi_substrate_calibration / falsification_ledger / cascade_regime_audit)

**What happened vs. what you expected?**

**Minimal example (optional):**
```

_Optional GitHub Pages site: not present; not required for a repo this size, but
the package READMEs are already Pages-ready if desired._

---

_End of review._
