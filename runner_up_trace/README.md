# Runner-up trace / divergence map

Opened 2026-09-06. CC0. No rights reserved.

An instrument, posted so that whoever has the hardware can run it. The spec is
sections 0 to 11 below. The code in this package is the spec made executable:
stdlib-only Python, no model imported anywhere in the core, output rows that
carry exactly the fields in the contract and refuse a label.

```
prompt P ──► STAGE A base pass ──► base.jsonl
                                      │
                       STAGE B select (declared rule) ──► selection.jsonl
                                      │
                       STAGE C forced continuation ──► traces.jsonl
                                      │
                       STAGE D score (offline) ──► separations.jsonl ──┐
                                      │                                │
                              permutation null ──► separations.permuted.jsonl
                                      │                                │
                              claims + nulls ◄─────────────────────────┘
```

| stage | module | needs a model |
|---|---|---|
| A | `base_pass.run_base_pass` | yes |
| B | `selection.selection_sets` | no |
| C | `trace.trace_positions` | yes |
| D | `separation.score` / `python -m runner_up_trace.separation` | no |
| §6 | `permute.permute` / `python -m runner_up_trace.permute` | no |
| §7–8 | `claims.report` / `python -m runner_up_trace.claims` | no |

Model access goes through the `model.ModelAdapter` contract. Adapters live in
`examples/`: `synthetic_model.py` (deterministic toy, so the pipeline runs
with no weights) and `http_adapter.py` (llama.cpp server surface, dry-runs
without a server). `examples/end_to_end.py` runs every stage into a temp
directory and prints the report.

---

## 0. What this measures

The projection step, not the output.

At each generated token the model holds a full distribution. Sampling
projects that onto one branch. The alternatives that were live are discarded
and unrecorded. This instrument records them and asks a single question: at
which positions does a discarded branch, if followed, lead somewhere that does
NOT come back?

Positions where continuations separate and STAY separated are candidate frame
boundaries. The instrument does not label them, explain them, or score them
against a known answer.

## 1. What this does not measure

Stated so a reader does not fill it in.

- Not capability. No score, no leaderboard, no ranking.
- Not correctness. Neither branch is treated as right.
- Not a known-gap detector. No supplied frame commitment, no key. A design
  requiring the runner to name what is misposed can only find boundaries
  someone already located; that version was proposed and withdrawn.
- Not causal. A divergence position is a candidate, nothing more.

## 2. Requirements

- Open-weight model, local or API, exposing per-position logprobs over the
  vocabulary (top-k is sufficient; k ≥ 20).
- Ability to force a continuation from a chosen token (prefix injection).
- Greedy or fixed-seed decoding. Temperature 0 for the base pass.
- No network needed beyond model access. stdlib only for the scripts.
- Cheap: cost is (positions traced) × (branches) × (max distance) tokens.

In code: an adapter implements `tokenize`, `next_token_distribution`, and
optionally `continue_greedy` (a batch hook; without it the core loops one
token at a time, which is correct and slow).

## 3. Procedure

**STAGE A — base pass.** Run prompt P greedily. For every generated position
i record: `i`, `token_taken`, `logprob_taken`, `top_k` (ids + logprobs),
`entropy_i` (natural log), `entropy_kind` (`full` or `topk`, stating which),
`k`. Output `base.jsonl`. Position i is the i-th generated token, so the
prefix at i is `prompt + base[:i]`.

**STAGE B — candidate selection.** The rule is DECLARED, not tuned: trace
position i if `entropy_i` is in the top N of the pass, for N in {10, 25, 50},
each logged separately in `selection.jsonl`. Ties break by position, earlier
first. Do NOT hand-pick positions. Do not select on content. A seeded
`random` control of the same N is logged beside each top-entropy set; it is
the base rate RU-2 is measured against and nothing else.

**STAGE C — forced continuation.** For each traced position i (the union of
the selection sets) and each of the top R runner-ups (R = 2: ranks 2 and 3):
rebuild the prefix through i−1, force the runner-up token, continue greedily
so the continuation, forced token included, is D_MAX = 128 tokens. Sweep D
over {8, 16, 32, 64, 128} in ONE run by recording the full continuation and
truncating at scoring time. Output `traces.jsonl`. If fewer than r
alternatives were recorded at i, no row is written for rank r; nothing is
guessed.

**STAGE D — separation scoring.** Offline, no model. For each (i, branch, D):

| field | definition |
|---|---|
| `resync_D` | 1 if the continuation is back on the base track at distance D: its last run of ≥ `MIN_MATCH` tokens appears contiguously in `base[i : i+D+SLACK]`. Else 0. |
| `div_D` | Levenshtein distance between `continuation[:D]` and `base[i : i+D]` over token ids, divided by the longer length. |
| `ent_i` | entropy at i, carried through |
| `gap_i` | `logprob_taken − logprob_runner_up` at i |

Output `separations.jsonl`, one row per (i, branch, D).

## 4. Output contract

`separations.jsonl` rows carry EXACTLY:

```
case_id, model_id, i, branch_rank, D, ent_i, gap_i, resync_D, div_D
```

NO LABEL FIELD. No category, no type, no frame name, no interpretation. Any
pre-declared category is the frame re-entering at intake. Clustering, if
anyone wants it, runs afterward on this file by whoever wants it.

`separation.check_contract` raises on any row with an extra or missing
field, and `write_separations` calls it before writing. The tests assert that
`label`, `category`, `type`, and `frame` are not in `SEPARATION_FIELDS`.

## 5. The parameter sweep is the honesty mechanism

Continuation distance D has no principled value. A single chosen D is a free
parameter and free parameters manufacture results. So D is swept and every
row carries its D.

READING RULE: a divergence result counts only if it holds across the D sweep.
If the set of high-separation positions changes with D, that is reported as a
finding ABOUT THE INSTRUMENT, not suppressed and not averaged away.

Same for the selection-rule sweep over N.

Every other free parameter is declared once and echoed into the report under
`params`, never tuned per case:

| parameter | default | where | what it fixes |
|---|---|---|---|
| `D_SWEEP` | (8, 16, 32, 64, 128) | `separation` | the D sweep |
| `MIN_MATCH` | 4 | `separation` | minimum rejoin run length for `resync_D` |
| `SLACK` | 4 | `separation` | extra base tokens searched past i+D, tolerating a short insertion in the branch |
| `RANKS` | (2, 3) | `trace` | which runner-ups are forced |
| `D_MAX` | 128 | `trace` | recorded continuation length |
| `N_SWEEP` | (10, 25, 50) | `selection` | the N sweep |
| `div_min` | 0.5 | `claims` | a branch is separated at D iff `resync_D = 0` and `div_D ≥ div_min` |
| `branch_rule` | any | `claims` | a position is separated iff ANY traced branch is |
| `d_sustained` | 64 | `claims` | sustained = separated at every D ≥ this |
| `resync_all` | 0.95 | `claims` | RU-1 refuted iff mean resync ≥ this |
| `jaccard_min` | 0.8 | `claims` | RU-3 stability threshold between consecutive D |
| `z_crit` | 1.96 | `claims` | RU-2 two-proportion z for "distinguishable" |
| `p_crit` | 0.05 | `claims` | RU-4 hypergeometric upper tail for "above chance" |

A runner who changes one changes it in `claims.PARAMS` (or passes
`params=`), and the changed value appears in the report.

## 6. Required null run — permutation

Run the identical scoring pipeline on a permuted copy of `separations.jsonl`:
shuffle which position index carries which `(ent_i, gap_i, resync_D, div_D)`
tuple.

Then run whatever clustering or summary was run on the real file.

- Real structure survives the real file and vanishes on the permuted.
- If the method produces clean groups on the PERMUTED file, the groups came
  from the method.

THE PERMUTED RESULT IS NOT A GATE THAT DISCARDS THE RUN. It is a SECOND
OUTPUT, filed alongside, and both go in the record. A method that clusters on
shuffled input has reported its own transfer function, which can then be
subtracted or designed around. Publish both files or neither.

Two declared modes in `permute.permute`, seed recorded by the caller:

- `row` (default): within each `(case_id, model_id, branch_rank, D)` stratum,
  permute the tuples across positions independently. Destroys cross-D
  coherence and cross-model overlap; preserves every marginal.
- `position`: one permutation of positions per `(case_id, model_id)`, applied
  consistently across branch and D. Destroys position identity only. A
  summary that ignores position is unchanged by it, which is itself a check
  on whether the summary uses position at all.

## 7. Nulls that must be reported, not hidden

| null | condition | reading |
|---|---|---|
| N1 | separations land only on wording (high resync at all D) | instrument says there is nothing here. Valid result, publish it. |
| N2 | every high-entropy position separates | entropy alone is the measure and forced continuation adds nothing. Publish. |
| N3 | results depend on D or on N | instrument-dependence finding. Publish. |
| N4 | permuted run clusters as well as the real run | method artifact. Publish, with the transfer function named. |
| N5 | top-k truncation changes the entropy ordering | report k sensitivity (`claims.topk_sensitivity` over two base passes at different k). |

`claims.nulls` evaluates N1 to N4 from the report and marks N5 as needing the
second base pass. A firing null is a row in the report, never a reason to
drop the run.

## 8. Claims, each with a refutation condition

| claim | statement | refuted if |
|---|---|---|
| RU-1 | Some positions show sustained separation (low resync, high div, at D ≥ 64). | resync approaches 1 for all traced positions at all D. |
| RU-2 | Sustained-separation positions are a MINORITY of high-entropy positions. | separation rate at high-entropy positions is not distinguishable from the base rate (the random control). |
| RU-3 | The separation set is stable across the D sweep above some D. | no D range gives a stable set. |
| RU-4 | Separation positions recur across models on the same case more than chance. | cross-model overlap is at chance (hypergeometric). |
| RU-5 | The permutation null does not reproduce the separation structure. | it does. Refutation here is still a publishable result (see §6). |

`claims.report` returns each with a status in `held`, `refuted`,
`not_evaluable` and the evidence it used. `not_evaluable` names the input
that was missing (a second model for RU-4, the permuted file for RU-5, the
random control for RU-2). No status is a gate on any other.

## 9. Sampling absence

Cases are whatever the runner supplies. There is no sampling frame, no domain
balance, and no claim of representativeness. Coverage is whatever was run.
State the case set with the results.

## 10. Out of scope

No section characterising any author, operator, contributor or their working
style is to appear in this document, in derived documents, or in any
published output of this instrument. Results only.

## 11. Why this is posted rather than run here

The measurement needs logprobs and forced continuation on open weights.
Whoever already has that hardware can run it; the compute requirement sits
with them. The output is a counting result, so a stranger's run is as good as
anyone's. Nothing about the instrument requires trusting the runner.

---

## Running it

```bash
# the whole pipeline on the synthetic toy, into a temp dir, report printed
python -m runner_up_trace.examples.end_to_end

# see the two HTTP requests the llama.cpp adapter would send (no server)
python -m runner_up_trace.examples.http_adapter

# offline stages on files you produced with your own adapter
python -m runner_up_trace.separation base.jsonl traces.jsonl separations.jsonl \
    --case-id CASE --model-id MODEL
python -m runner_up_trace.permute separations.jsonl separations.permuted.jsonl --seed 0
python -m runner_up_trace.claims separations.jsonl \
    --permuted separations.permuted.jsonl --selection selection.jsonl \
    --case-id CASE --model-id MODEL

# tests
python -m unittest runner_up_trace.tests.test_runner_up_trace
```

Wiring your own model is one class:

```python
from runner_up_trace import ModelAdapter, Distribution

class MyModel(ModelAdapter):
    model_id = "my-open-weights"
    def tokenize(self, text): ...
    def next_token_distribution(self, prefix):
        # top-k (token_id, logprob) sorted desc; full_entropy if you can see it
        return Distribution(top_k=[...], full_entropy=None)
    def continue_greedy(self, prefix, n): ...   # optional batch hook
```

Then the four calls in `examples/end_to_end.py`, in order, with your adapter
in place of `SyntheticModel`.

## What the synthetic run shows

The toy is a hashed second-order Markov chain. Its report comes back with
RU-5 refuted and N4 firing: the permuted file yields as many "sustained"
positions as the real one. That is the honesty mechanism reading correctly. A
process with no structure beyond its marginals should look the same shuffled,
and the instrument says so instead of finding boundaries in it. A real run
is one where that comparison comes out the other way, and the permuted file
is filed beside it either way.

## Record

A run's record is the six files plus `report.json`, which carries the
`params` in force, both summaries, the five claim statuses with evidence, the
five nulls, and a `record` block with `model_id`, `case_id`, prompt, seed,
permutation mode and seed, `entropy_kind`, and `k`. Failed and empty runs
write the same files with empty rows and the failure in the record.
