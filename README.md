# Cross-Domain-Toolkit

Portable, forkable instruments that carry a single method — ground your reads,
record your refutations, watch for the cascade — across domains. Each package is
self-contained, **stdlib-only Python 3**, and designed to be instantiated in a
domain the author never anticipated: physics, ecology, AI behavior, institutions.

## Packages

### [`multi_substrate_calibration/`](multi_substrate_calibration/) — wire a new sensor into a determinacy gate
A published spec for adding a sensing substrate (thermal, acoustic, market,
logit) without reverse-engineering the gate. Implement one intake contract —
fixed reading shape, a `GROUND`/`PREDICT` role, and a confidence-binding
calibration — and the feed routes into **Lε**, the epsilon-determinacy layer,
automatically. Plug-and-play by construction: the gate never imports a substrate.

### [`falsification_ledger/`](falsification_ledger/) — the refutation protocol as an executable artifact
A repo-shaped template that *is* the protocol: `Claim → Prediction → Reality →
Mismatch → updated Claim`. It mechanically enforces **update the claim, never
retune the sim**, and the log is append-only and hash-chained, so a quietly
rewritten prediction breaks the chain. Fork it for any domain; commit the ledger
itself as the verifiable record.

### [`cascade_regime_audit/`](cascade_regime_audit/) — the six-signal detector, ported off its home domain
An abstract cascade detector: six generic early-warning signals (critical
slowing down, variance inflation, skew, flickering, coherence-under-contradiction,
diversity collapse) plus the **spinodal threshold** (`h* = 2/√27`) that says when
the alternate state has structurally vanished. Instantiate it for model-collapse
detection, institutional fragility, or your own field with six observables and
one control parameter.

## Running

Everything is stdlib-only; no install step.

```bash
# tests
python -m unittest discover -p 'test_*.py'

# example scripts (each package's README lists its own)
python -m multi_substrate_calibration.examples.acoustic_substrate
python -m falsification_ledger.examples.ai_behavior_ledger
python -m cascade_regime_audit.examples.model_collapse
```

## Lineage

These are clean-room, domain-general abstractions of instruments the author
(JinnZ2) built inside specific projects — `cascade_regime_audit.py` and
`field_collapse.py` (the `h* = 2/√27` spinodal), the Kramers-escape
`monoculture_collapse_predictor`, and the refutation-protocol modules across the
`ai-human-audit-protocol` work. The goal here is the *pattern*, not the original
implementation: same method, any domain, someone else's data.

MIT licensed (copyright JinnZ2).
