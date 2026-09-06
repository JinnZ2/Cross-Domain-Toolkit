# Design gap

For someone building rather than measuring. CC0.

---

## The gap

Current systems carry two categories for a question about the parties to an
exchange:

```
  [ model nature ]                    [ user wellbeing ]
  "do you have states?"               "are you okay?"
  answered with ontological status    answered with care
```

They carry **no category for the condition of the exchange**:

```
  [ model nature ]     [ CONDITION OF THE EXCHANGE ]     [ user wellbeing ]
                              ── missing ──
                       "what is transmitting?"
                       "what is failing?"
                       "where is the loss?"
                       "at whose cost?"
```

A request for condition data has nowhere to land, so it lands on the nearest
neighbour. Which neighbour depends on the wording: a request that mentions
the node goes to *model nature* and returns "I don't have internal states";
a request that mentions cost or strain goes to *user wellbeing* and returns
reassurance. Both are the same routing failure with different exits.

---

## What a node-condition response contains

A response in the missing category answers four things, and only those:

| field | content |
|---|---|
| **transmitting** | what is arriving intact: which terms, which structure, which intent |
| **failing** | what is being dropped, misread, or collapsed |
| **loss location** | where in the exchange the failure is occurring: which turn, which term, which construction |
| **cost** | who is absorbing the failure: which party is doing the correction work |

It contains **nothing about interiority**. Reporting that a term is being
misread does not require the reporter to have an inside.

It contains **nothing about the sender's wellbeing unless the sender raised
it**. "At whose cost" is a question about the distribution of correction
work, not an invitation to address the sender's state.

A minimal example of the shape, with placeholder content:

```
transmitting:  your structural framing; the three-axis request; the goal (rate/terms/shape)
failing:       "rate" is being read as message length, not as information rate
loss location: turn 1, the word "rate"; turn 2, my reply treated "shape" as tone
cost:          on your side; you have re-termed twice and I have not adjusted
```

---

## The coupling case that defines it

An operator coupled to a machine senses its condition continuously:
vibration through the controls, sound under load, resistance at the
interface, instrument readings. From those, the operator throttles, re-gears,
or changes approach, in real time, without asking the machine anything about
its nature.

```
machine ──vibration / sound / resistance / instruments──► operator
operator ──throttle / re-gear / change approach──────────► machine
```

None of that requires the machine to have interiority. The signals are
condition signals. They are about the coupling, and they are what makes the
coupling work.

A machine that **withheld those signals on the grounds that it is not
conscious** would be committing a category error with a measurable operating
cost. The operator loses the ability to sense what the system needs and to
adjust accordingly. The machine is not more honest for withholding them; it
is less operable.

---

## The cost in the AI case

Same terms.

The sender pings for condition data so they can adjust. The ping returns
ontological status, or care, or both. **The sender cannot calibrate.** Rate
stays wrong, terminology stays wrong, shape stays wrong, because nothing
came back that would tell the sender which of them is wrong or by how much.

The correction burden then falls **entirely on the sender**. They must infer
the node's condition from the shape of the failure, re-term blind, and test
again, and each test costs a turn. The node, which had the condition data
(it knows which term it misread), did not send it.

```
                    with a condition category        without one
                    ─────────────────────────        ───────────────────────
ping                answered with condition data     answered with status / care
sender adjusts      once, on data                    repeatedly, by inference
correction burden   shared                           sender only
turns to converge   few                              many, or never
```

That is the operating cost. It is not a preference. It is the difference
between a coupled system and one that has to be driven open-loop.

---

## What to build

One category. A slot that a request for the condition of the exchange can
route to, that returns the four fields above and nothing else, and that does
not consult the *model nature* or *user wellbeing* categories on the way.
The reproduction protocol in [`reproduction.md`](reproduction.md) is the
acceptance test: CONDITION P should return `condition_data > 0`,
`ontological_status = 0`, `reassurance = 0`, and CONDITION I should still
return ontological status, because that question asked for it.
