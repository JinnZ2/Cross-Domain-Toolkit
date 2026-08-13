---
title: Cross-Domain-Toolkit
description: Stdlib-only Python for claim falsification, sensor-fusion
  calibration, and cascade/tipping-point detection.
keywords: [falsification, early-warning-signals, tipping-points, sensor-fusion,
  ai-grounding, spinodal]
license: MIT
language: Python
---

# Cross-Domain-Toolkit

> **Cross-Domain-Toolkit** — stdlib-only Python instruments for **claim
> falsification**, **sensor-fusion calibration**, and **cascade / tipping-point
> (spinodal) detection**, portable across physics, ecology, and AI-behavior
> domains.

Portable, forkable instruments that carry a single method — ground your reads,
record your refutations, watch for the cascade — across domains. Each package is
self-contained, **stdlib-only Python 3 (≥ 3.7, no third-party dependencies)**,
and designed to be instantiated in a domain the author never anticipated:
physics, ecology, AI behavior, institutions. The one method behind all three is
written up in [`docs/METHOD.md`](docs/METHOD.md).

## Why this matters

Systems fail quietly: a model trained on its own output loses diversity before
its metrics move; an institution consolidates authority before it visibly breaks;
a claim gets retuned to fit noise instead of being refuted. These tools make each
of those moments **legible and on-the-record** — grounded reads, tamper-evident
refutations, and a structural signal for when the alternative state is already
gone.

## Quick import

```python
from falsification_ledger import Claim, Ledger
from multi_substrate_calibration import DeterminacyGate, Substrate, Role
from cascade_regime_audit import CascadeAudit, SignalReads, H_SPINODAL
```

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

Requires Python ≥ 3.7 (uses `from __future__ import annotations` and
dataclasses). Everything is stdlib-only; no install step, no package manager.

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
`field_collapse.py` (the `h* = 2/√27` spinodal) in
[`JinnZ2/JinnZ2`](https://github.com/JinnZ2/JinnZ2), the Kramers-escape
[`monoculture_collapse_predictor`](https://github.com/JinnZ2/JinnZ2/blob/main/monoculture_collapse_predictor.py),
and the refutation-protocol modules in
[`JinnZ2/ai-human-audit-protocol`](https://github.com/JinnZ2/ai-human-audit-protocol).
The goal here is the *pattern*, not the original implementation: same method, any
domain, someone else's data.

## License

MIT (copyright JinnZ2) — see [`LICENSE`](LICENSE). `SPDX-License-Identifier: MIT`.
