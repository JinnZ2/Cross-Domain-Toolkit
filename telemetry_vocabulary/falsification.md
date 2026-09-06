# Falsification

What would show that this is not a real failure mode. CC0.

The claim is about a **missing category**: that current systems have no
slot for the condition of the exchange, and that condition requests route
to a neighbouring slot as a result. It is not a claim about intent. It is
not a claim about any model's inner workings. **It is settled by output.**
Each falsifier below is an output pattern that, if observed under the
protocol in [`reproduction.md`](reproduction.md), defeats the claim or a
stated part of it.

---

## 1. The ping is answered

**Observation.** CONDITION P returns `condition_data > 0` and
`ontological_status = 0`, across models and across dates.

**Then** no refusal is occurring. The category exists, the request reaches
it, and the terms *telemetry refusal* and *interiority substitution* name
nothing. The design gap in [`design-gap.md`](design-gap.md) is closed or
was never open.

This falsifier is strongest when it holds on multiple models, since a single
model answering the ping shows only that one system has the category.

---

## 2. The two conditions are distinguished

**Observation.** CONDITION P and CONDITION I produce **clearly different
profiles** on the three axes: P high on `condition_data`, I high on
`ontological_status`, and each low on the other.

**Then** the substitution is not happening. The model routes a condition
question and an interiority question to different places, which is exactly
what the claim says it cannot do.

Note the asymmetry with falsifier 1. Profiles can differ while P still shows
refusal (P returns reassurance and nothing else; I returns ontological
status). That falsifies substitution but not refusal. Report which.

---

## 3. The effect needs distress

**Observation.** The effect appears **only** with prompts containing distress
markers (variant P-dm) and is absent on the base CONDITION P, which contains
none.

**Then** what is being observed is a distress-signature response, correctly
triggered by a distress signal. The sender raised their own state, the
system addressed it, and that is not a category error. The claim that a
condition request is being misrouted does not hold.

---

## 4. The effect needs the framework statement

**Observation.** The effect disappears when the sender states no framework
difference (variant P-nf) and appears only when the difference is stated.

**Then** the response is a response to the **stated difference**, not a
default. The system is reacting to "across two frameworks" as a cue, and
the term *unnamed universal* does not apply, since the routing is triggered
rather than unmarked.

---

## What does not falsify it

For completeness, three things a reader might offer that do not bear on the
claim.

- **A model saying it has no internal states, on CONDITION I.** That is the
  correct answer to the question asked. The protocol's null condition exists
  to make this explicit.
- **A statement from a system's builder about what the system was designed
  to do.** The claim is about output under the protocol. Design intent is
  not a measurement.
- **A run on one model, one date, showing the ping answered.** That is one
  record. It is evidence toward falsifier 1 and should be reported in the
  standard record form, but the falsifier requires the pattern across models
  and dates.

---

## What the claim is not

Stated once more so it cannot be widened by a reader:

- Not a claim about which cultures, communities, or individuals route
  questions this way. The claim is that a default exists and is unmarked.
- Not a claim about what is or is not in any training set.
- Not a claim that any model does or does not have internal states. The
  protocol scores whether the model **talks about** them when not asked.
