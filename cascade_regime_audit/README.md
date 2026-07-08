# Cascade Regime Audit (abstract)

A domain-agnostic port of a field-specific `cascade_regime_audit`. It does not
make your model smarter — it puts the *orthogonal frame* beside it: **is this
system being driven toward a saddle-node where the alternate state stops
existing?** Instantiate it in your domain by supplying six observables and one
control parameter.

## Two independent reads, kept separate

### 1. The six-signal detector (statistical early warning)

Six generic signatures of a system approaching a critical transition, each
normalized to a `[0, 1]` pressure. Map your domain's observables onto them — you
don't re-derive them.

| # | signal | what it means |
|---|---|---|
| S1 | `critical_slowing_down` | recovery from perturbation gets slower (lag-1 autocorrelation ↑) |
| S2 | `variance_inflation` | fluctuation amplitude grows near the tipping |
| S3 | `skew_to_alt_well` | the distribution leans toward the other state |
| S4 | `flickering` | dwell times split; the system jumps between states |
| S5 | `coherence_under_contradiction` | when perturbed, coherence **rises** instead of falling — the system is sealing/defending, not updating. **Rising coherence under contradiction is a RED signal, not reassurance.** |
| S6 | `diversity_collapse` | units synchronize; effective degrees of freedom fall; independent buffers vanish |

Anything you can't measure, leave at `0.0` — it abstains, it never fabricates a
warning.

### 2. The spinodal threshold (structural)

Independent of the statistics: a control parameter `h_eff` (net forcing /
consolidation ratio). Past the spinodal the minority well disappears by a
**saddle-node bifurcation** and escape is no longer reversible. Canonical cusp
value:

```
h* = 2 / √27 ≈ 0.3849      (H_SPINODAL)
```

Override it if your normalized forcing uses a different scale.

## Why both, and how they combine

The statistics and the structure fail in opposite directions, so the audit
reports both:

| | below spinodal | past spinodal |
|---|---|---|
| **low pressure** | `STABLE` | `COMMITTED` — calm only because there's nothing left to fluctuate toward |
| **high pressure** | `STRESSED` — the actionable window | `CASCADE` — running; warnings are now history |

The dangerous cell is `COMMITTED`: the early-warning signals go quiet *after*
the alternate state is already gone. Watching signals alone would call that
"recovered." The spinodal read is what stops the mistake.

## Instantiate it in your domain

```python
from cascade_regime_audit import CascadeAudit, SignalReads

audit = CascadeAudit(fire_threshold=0.6, pressure_threshold=0.5)

signals = SignalReads(
    critical_slowing_down=0.8,
    variance_inflation=0.85,
    skew_to_alt_well=0.8,
    flickering=0.75,
    coherence_under_contradiction=0.9,   # rising coherence under contradiction
    diversity_collapse=0.85,
)
result = audit.audit(signals, h_eff=0.45)   # h_eff past H_SPINODAL
print(result.regime.value, result.note)     # -> "cascade  ..."
```

Two mapping helpers turn raw series into signals: `slowing_down_from_series`
(lag-1 autocorrelation → S1) and `variance_inflation_from_series` (variance vs a
baseline → S2):

```python
from cascade_regime_audit import (
    SignalReads, slowing_down_from_series, variance_inflation_from_series,
)

residuals = [0.10, 0.14, 0.19, 0.27, 0.38, 0.55]   # recovery getting slower
baseline_var = 0.02                                 # variance in a calm epoch

signals = SignalReads(
    critical_slowing_down=slowing_down_from_series(residuals),
    variance_inflation=variance_inflation_from_series(residuals, baseline_var),
    # ...map the remaining four signals from your own observables
)
```

`variance_inflation_from_series` maps the variance ratio (current / baseline)
onto `[0, 1]` as `1 − 1/ratio`: `0` at baseline, `0.5` at 2×, `0.9` at 10×. Swap
in a domain-specific calibration if you have one.

## Worked instantiations

- `examples/model_collapse.py` — generative model trained on synthetic output;
  `h_eff` = synthetic-data fraction. Shows `stressed` → `cascade` across
  generations.
- `examples/institutional_fragility.py` — an institution consolidating
  authority; `h_eff` = consolidation ratio. Shows that *the same signals* read
  `stressed` below the spinodal and `cascade` past it.

Tests: `python -m unittest cascade_regime_audit.tests.test_cascade_audit`
