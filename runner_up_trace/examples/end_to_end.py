"""The whole instrument on the synthetic model, files and all.

    base.jsonl -> selection.jsonl -> traces.jsonl -> separations.jsonl
                                                  -> separations.permuted.jsonl
                                                  -> report.json

Runs in a temporary directory and prints the report. Every threshold the
report used is echoed in `params`. The synthetic model is plumbing, so the
claim statuses printed here say nothing about any language model; they show
what a run looks like and that the permuted file sits beside the real one.

Run:  python -m runner_up_trace.examples.end_to_end
"""

from __future__ import annotations

import json
import os
import tempfile

from ..base_pass import BaseRow, run_base_pass
from ..claims import report
from ..permute import permute
from ..records import read_jsonl, write_jsonl
from ..selection import selection_sets, union_positions
from ..separation import score, write_separations
from ..trace import TraceRow, trace_positions
from .synthetic_model import SyntheticModel

CASE_ID = "synthetic-case-01"
PROMPT = "an operator coupled to a machine senses its condition"
SEED = 11


def run(outdir: str, seed: int = SEED, max_tokens: int = 96, d_max: int = 128) -> dict:
    model = SyntheticModel(seed=seed)
    prompt = model.tokenize(PROMPT)

    # A
    base_rows = run_base_pass(model, prompt, max_tokens=max_tokens)
    write_jsonl(os.path.join(outdir, "base.jsonl"), (r.to_record() for r in base_rows))

    # B
    sel = selection_sets(base_rows, random_seed=seed)
    write_jsonl(os.path.join(outdir, "selection.jsonl"), sel)
    positions = union_positions(sel)

    # C
    traces = trace_positions(model, prompt, base_rows, positions, d_max=d_max)
    write_jsonl(os.path.join(outdir, "traces.jsonl"), (t.to_record() for t in traces))

    # D (re-read from disk: the offline stage must not need the model objects)
    base_rows2 = [BaseRow.from_record(r) for r in read_jsonl(os.path.join(outdir, "base.jsonl"))]
    traces2 = [TraceRow.from_record(r) for r in read_jsonl(os.path.join(outdir, "traces.jsonl"))]
    seps = score(base_rows2, traces2, CASE_ID, model.model_id)
    write_separations(os.path.join(outdir, "separations.jsonl"), seps)

    # Section 6: permutation null, filed beside
    perm = permute(seps, seed=seed, mode="row")
    write_separations(os.path.join(outdir, "separations.permuted.jsonl"), perm)

    rep = report(seps, perm, sel, CASE_ID, model.model_id)
    rep["record"] = {"case_id": CASE_ID, "model_id": model.model_id, "prompt": PROMPT,
                     "seed": seed, "permutation_mode": "row", "permutation_seed": seed,
                     "entropy_kind": base_rows[0].entropy_kind, "k": base_rows[0].k,
                     "positions_traced": len(positions), "traces": len(traces),
                     "separation_rows": len(seps)}
    with open(os.path.join(outdir, "report.json"), "w") as fh:
        json.dump(rep, fh, indent=2, sort_keys=True)
    return rep


def main() -> None:
    with tempfile.TemporaryDirectory() as d:
        rep = run(d)
        files = sorted(os.listdir(d))
    print("files:", files)
    print("record:", json.dumps(rep["record"], sort_keys=True))
    print("params:", json.dumps(rep["params"], sort_keys=True))
    s = rep["summary_real"]
    print(f"real:     rows={s['rows']} mean_resync={s['mean_resync']:.3f} "
          f"mean_div={s['mean_div']:.3f} sustained={len(s['sustained_positions'])} "
          f"stable_from_D={s['stability']['stable_from_D']}")
    s = rep["summary_permuted"]
    print(f"permuted: rows={s['rows']} mean_resync={s['mean_resync']:.3f} "
          f"mean_div={s['mean_div']:.3f} sustained={len(s['sustained_positions'])} "
          f"stable_from_D={s['stability']['stable_from_D']}")
    for c in rep["claims"]:
        print(f"  {c['claim']}: {c['status']}" + (f"  ({c['reason']})" if c.get("reason") else ""))
    for n in rep["nulls"]:
        print(f"  {n['null']}: fires={n['fires']}  {n['what']}")
    print("(synthetic model: these statuses describe the plumbing, not any language model)")


if __name__ == "__main__":
    main()
