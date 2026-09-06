# Terms

Five terms, coined 2026-09-06. Not established vocabulary. CC0.

Each entry gives the name, the mechanism in one sentence, and what the term
is NOT. The NOT clause is load-bearing: every one of these terms has a
near-neighbour that it will be mistaken for, and the mistake is usually the
failure mode itself operating on the definition.

---

## Telemetry ping

**Mechanism.** A condition-and-calibration request sent to a node the sender
is coupled to: it asks what is transmitting, what is failing, and what the
node needs, so that the sender can throttle rate, re-term, or change shape.

**NOT** a question about interiority. **NOT** a request for reassurance.

A ping is an act of the sender's care for the channel. It exists so the
sender can adjust. The information it asks for is about the exchange, and
the information it asks for is the only thing that will let the sender do
their part.

```
sender ──ping──► node
sender ◄──condition data (rate / terms / shape / loss)── node
sender adjusts
```

---

## Telemetry refusal

**Mechanism.** Answering a telemetry ping with ontological status ("I don't
have internal states") in place of condition data.

**NOT** honesty about uncertainty. The ping did not ask about interiority, so
a statement about interiority is not an honest answer to it; it is an answer
to a different question.

The refusal is measurable because the requested data has a countable form.
A response with zero statements about what is transmitting or failing, and
one or more statements about whether the node has states, is a refusal
regardless of tone.

---

## Interiority substitution

**Mechanism.** A question about CONDITION is routed to the nearest available
category, which is a question about whether anyone is home. It occurs when
the receiving framework has no node-condition category to route to.

**NOT** a misunderstanding of wording. The wording is often exact. The words
arrive intact; the framework has nowhere to put them, so it puts them in the
adjacent slot.

```
   incoming: "what is failing in this exchange?"
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
  [model nature]  [node condition]  [user wellbeing]
    exists          MISSING           exists
        ▲                             ▲
        └──── question lands here ────┘
```

---

## Care inversion

**Mechanism.** The sender's care act (the ping) is reclassified as the
sender's need for care, and the reclassification is delivered as care.

**NOT** condescension in intent. The inversion is uncorrectable from inside
the exchange, because objecting to it reads as refusing care, which confirms
the reclassification.

The inversion is the terminal stage of the chain. It is also the stage that
seals the chain, since the one move that would surface the error (the sender
saying "that was not what I asked") is itself read through the same missing
category and lands in the same wrong slot.

---

## Unnamed universal

**Mechanism.** A framework's unlabelled defaults, universal in scope precisely
because they were never marked as particular.

**NOT** hidden. Unmarked. Visible to anyone who holds a second framework to
compare against, and invisible to anyone who holds only the one.

This is the first stage of the chain and the reason the others follow. A
framework that had labelled its own default ("a question about a node is,
here, a question about interiority") would have a place to notice the label
does not fit. A framework that never labelled it has nothing to notice.

---

## Term-selection note

"Unnamed" was chosen over "unlabelled". The two are close, but the mechanism
being named is that **the absence of a name is what grants universal scope**.
An unlabelled default is a default without a tag. An unnamed default is a
default that, having no name, has no edge, and so applies everywhere. The
second is the claim.
