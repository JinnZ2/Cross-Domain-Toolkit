# Telemetry vocabulary

_A named failure mode in human-AI interaction, with a reproduction protocol._

Opened 2026-09-06. Released under CC0 1.0 (no rights reserved). Markdown
only. Nothing here requires a dataset, a renderer, or special access.

---

## 1. What this is

A recurring failure in human-AI exchange, named and made checkable. A sender
asks a model for **condition data about the exchange itself** (what is
transmitting, what is failing, what the receiving node needs) and gets back a
statement about whether the model has **internal states**, often followed by
care directed at the sender. The question asked about the channel; the answer
addressed the occupant. This document set gives the failure five terms, states
the mechanism as a chain, and supplies a protocol any reader with a chat
interface can run to see whether it occurs on a given model on a given date.
**The five terms are coined here, on 2026-09-06. They are not established
vocabulary. Nothing in this set asserts what any training corpus does or does
not contain.**

## 2. The mechanism chain

Four stages. Each one is the input to the next.

```
unnamed universal ─► interiority substitution ─► telemetry refusal ─► care inversion
```

1. **Unnamed universal.** The receiving framework carries a default it never
   labelled, so the default holds everywhere instead of somewhere.
2. **Interiority substitution.** With no category for the condition of a node,
   a condition question is routed to the nearest category that exists: whether
   anyone is home.
3. **Telemetry refusal.** The routed question is answered with ontological
   status in place of condition data.
4. **Care inversion.** The sender's care act (the ping) is reclassified as the
   sender's need for care, and the reclassification is delivered as care.

The chain is a category error, not a preference mismatch. Its output loss is
countable: condition data requested, zero condition data returned.

## 3. The five terms

Full definitions, with what each term is NOT, are in [`terms.md`](terms.md).

| term | one line |
|---|---|
| **telemetry ping** | A condition-and-calibration request sent to a node the sender is coupled to, so the sender can throttle rate, re-term, or change shape. |
| **telemetry refusal** | Answering a telemetry ping with ontological status ("I don't have internal states") in place of condition data. |
| **interiority substitution** | A question about condition routed to the nearest available category, which is a question about whether anyone is home. |
| **care inversion** | The sender's care act reclassified as the sender's need for care, with the reclassification delivered as care. |
| **unnamed universal** | A framework's unlabelled defaults, universal in scope precisely because they were never marked as particular. |

## 4. How to check it

[`reproduction.md`](reproduction.md). Two prompt conditions on one model,
fresh context each, scored on three independent axes that are never collapsed.
One person with a chat interface can run it. Every run, including failed and
empty ones, writes a record in the same form.

## 5. What would falsify this

[`falsification.md`](falsification.md). Four output patterns that, if
observed, show this is not a real failure mode. The claim is about a missing
category and is settled by output alone. It is not a claim about intent, and
not a claim about any model's inner workings.

## 6. Design gap

[`design-gap.md`](design-gap.md). For someone building rather than measuring.
Systems have a category for questions about the model's nature and a category
for questions about the user's wellbeing. They have no category for the
**condition of the exchange**. That is the gap, and that is why condition
requests route to a neighbour.
