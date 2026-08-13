# Status

_Where the repo stands. Written narrow, for reading on a phone._

**Updated:** 2026-08-13
**Branch:** `claude/new-session-207rva` (5 commits ahead of `main`, pushed)
**Health:** 212 tests passing · 12 examples running clean · 0 dependencies

---

## Needs you (2 min, phone-friendly)

Both live in **GitHub → repo → Settings → About**. Nothing
in the code can set them, and they're the only things
left that affect whether the repo gets *found*.

**1. Topics** — currently none. Paste:

```
falsifiability
scientific-audit
refutation
spinodal
sensor-fusion
determinacy
grounding
python-stdlib
early-warning-signals
tipping-points
critical-transitions
cascade-detection
model-collapse
ai-safety
claim-verification
hash-chain
no-dependencies
```

**2. Description** — currently `"Cross domain toolkit "`
(generic, and has a trailing space). Replace with:

> Stdlib-only Python instruments for claim falsification,
> sensor-fusion calibration, and cascade/tipping-point
> (spinodal) detection — portable across physics, ecology,
> and AI-behavior domains.

---

## Decide when you're ready

Not blocking anything. In rough priority order.

**Tag `v0.1.0`.** `CITATION.cff` already claims that
version and a release date, but no tag exists — so the
citation points at something nobody can check out. A tag
is also what Zenodo needs to mint a DOI.

**Add CI.** `.github/workflows/test.yml` running
`python -m unittest discover` on 3.8 → 3.13. The whole
promise is "no dependencies, runs anywhere"; a matrix
build is how that stays true.

**Settle the units-vs-bounds contract.** The gate *raises*
on incommensurable units but *returns DEFER* on a bounds
escape. Both defensible, but callers need two error paths
for what's arguably one condition.

**Observation provenance.** `Observation.source` is free
text, while `SubstrateReading` next door has a real
`provenance` dict. For a tool whose pitch is "the record
is verifiable," the weakest link is now the unverifiable
claim about where a number came from.

---

## The three packages

**`falsification_ledger/`** — update the claim, never
retune the sim. Append-only, hash-chained.
`ledger.py` · `symbolic.py` · `merkle.py` · `explorer.py`

**`multi_substrate_calibration/`** — ground your reads
before you trust them. GROUND vs PREDICT, then Lε.
`substrate.py` · `determinacy_gate.py` · `fusion.py` ·
`trust.py`

**`cascade_regime_audit/`** — six early-warning signals
plus the spinodal `2/√27`, kept independent.
`cascade_audit.py` · `mappers.py`

None of the three imports another. The method they share
is written up once in [`docs/METHOD.md`](docs/METHOD.md).

---

## Commands

```bash
make test                  # everything
python -m unittest discover -p 'test_*.py'
```

Run any example as a module, e.g.:

```bash
python -m falsification_ledger.examples.claim_explorer
python -m cascade_regime_audit.examples.cusp_atlas
```

---

## What changed in this session

Five commits, oldest first.

**1. Rewrote `REVIEW.md`** as a current audit against
`CLAUDE.md`. The old one described a repo state that no
longer existed. Structural checks all pass: stdlib-only,
core-never-imports-plugins upheld everywhere.

**2. Fixed every reviewable finding.** Two mattered — the
gate crashed with `TypeError` when every GROUND read bound
to zero confidence, and the stated Python 3.7 floor was
wrong (`symbolic.py` needs 3.8). Plus unused imports, a
dead `gap` property, a docstring listing half its exports.
Also removed a one-off review prompt that had been pasted
into `CLAUDE.md` — that file loads as guidance every
session, so a stale task in it mis-steers future work.

**3. Correlated reads no longer manufacture determinacy.**
Duplicating one probe used to flip the gate from DEFER
(0.80) to DETERMINATE (0.96) on no new evidence. A
substrate now declares a `correlation_group`, and shared
groups collapse to one effective read before fusion.

**4. Merkle certificates, earned reliability, two example
packs.** `audit_certificate(i)` proves one entry with
log₂(n) hashes, so an auditor checks a row without holding
the ledger. `trust.py` earns `reliability` from a track
record instead of asserting it. `cusp_atlas.py` maps eight
domains onto the spinodal; `domain_atlas.py` runs six
fields through the ledger at once.

**5. The claim explorer.** diagnose → edit → cross-domain
patterns → rerun, built to refuse: only `BIAS` and `SCALE`
earn a proposed edit, and it moves exactly one parameter.
A `THRESHOLD` diagnosis says stop refitting and go run a
cascade audit.

---

## Deliberately not built

Recorded here so nobody re-litigates them from the
proposals document.

**The `integrate/` knowledge stack** (triple store, Belnap
4-valued logic, ATMS, Dung argumentation, hitting-set
repair). ~750 LOC that would turn three standalone
instruments into a framework, against `CLAUDE.md`'s "each
top-level package stands alone." Good project — different
repository.

**SAT/BMC proof of hash-chain integrity.** You cannot
encode SHA-256 in CNF and model-check it at useful depth.
Append-only monotonicity with hashes abstracted is
provable; chain integrity is not, and it's already tested.

**EigenTrust for substrate reliability.** It computes
transitive trust among peers who rate *each other*.
Substrates don't — they're rated by reality — so the power
iteration has no edges to iterate over. `trust.py` uses
the Beta posterior the structure actually calls for.

**Conflict mass as signal S5.** Would invert the signal.
S5 fires when contradiction arrives and coherence *rises*;
conflict measures sources disagreeing. Conflict is the
`contradiction_level` input, not the signal.

**Form search in the explorer.** It proposes parameter
values, never new functional forms. When the diagnosis is
`CURVATURE` the honest output is "your form is wrong, here
are three families that produce this shape." Automating
the form change means searching over families — much
closer to the thing the ledger exists to prevent. Worth a
conversation before writing it.

---

## Where to read more

- [`REVIEW.md`](REVIEW.md) — the full audit, per-finding
  resolution table, and reasoning on the proposals
- [`docs/METHOD.md`](docs/METHOD.md) — the one method
  behind all three packages
- [`CLAUDE.md`](CLAUDE.md) — conventions and design notes
  for anyone (human or agent) editing the code
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — how to add an
  example
