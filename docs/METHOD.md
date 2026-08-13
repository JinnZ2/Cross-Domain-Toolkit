# The method

All three packages in this toolkit are the same discipline wearing three faces.
Stated once:

> **Ground your reads before you trust them, record your refutations so you can't
> quietly rewrite them, and watch for the structural point where a system's
> alternate state stops existing.**

Each package implements one clause of that sentence, and each is a clean-room,
domain-general abstraction of a field-specific instrument (see the repo README's
Lineage section). The point is the *pattern*, not any one domain — you instantiate
it in yours.

## 1. Ground your reads before you trust them — `multi_substrate_calibration`

A read is not evidence until you know what it's worth. The gate separates two
roles a substrate can play — **GROUND** (a sensorimotor read of *what is*) and
**PREDICT** (a forecast of *what will be*) — and refuses to let a forecast
masquerade as an observation. Confidence is *bound* into a shared frame before
fusion (`bound = reliability · warp(native)`), so a "0.9" from any substrate means
the same thing. Reads must be commensurable (shared units) and physically
possible (optional bounds) before they fuse. The final call is **Lε**: act only
when determinacy ≥ 1 − ε; otherwise DEFER and say why.

## 2. Record your refutations so you can't quietly rewrite them — `falsification_ledger`

The one rule: **update the claim, never retune the sim.** A claim carries its
params; the sim is a fixed kernel. When reality lands outside tolerance, the only
legal move is to supersede the claim with a new, on-the-record version — you
cannot reach back and edit a prediction to fit. The log is append-only and
hash-chained, so any later edit is detectable. Optional guards make the honesty
mechanical: an up-front `refutation_set` (what would refute this?), a
specificity check (`scope` + `reference_class` — true of what, where, when?), a
machine-checkable `logical_form`, and an escape-hatch detector that flags a claim
re-parameterized to dodge every refutation without ever surviving a clean test.

## 3. Watch for where the alternate state stops existing — `cascade_regime_audit`

Some failures are quiet: the early-warning signals go silent *after* the
alternate stable state is already gone. So the audit keeps two independent reads.
The **six-signal detector** (critical slowing down, variance inflation, skew,
flickering, coherence-under-contradiction, diversity collapse) is the statistical
read. The **spinodal threshold** (`h* = 2/√27`) is the structural read: past it,
the minority well has vanished by a saddle-node bifurcation and recovery is no
longer possible. High signals *below* the spinodal is stressed-but-recoverable;
*past* it is committed. Reporting both is what stops "it went quiet" from being
misread as "it recovered."

## Why one method, three packages

They fail in different directions and so are useful separately, but they compose:
ground a read (1), record the claim you make from it and how it breaks (2), and
watch whether the system you're reading is approaching the point of no return (3).
Each package is stdlib-only and forkable on its own; this document is the through-line.
