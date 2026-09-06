"""Runner-up trace / divergence map: record the branches sampling discards and
ask where a discarded branch, if followed, does not come back.

Stages (Section 3 of README.md):
    A  base_pass.run_base_pass      -> base rows          (needs a model)
    B  selection.selection_sets     -> declared positions (offline)
    C  trace.trace_positions        -> forced continuations (needs a model)
    D  separation.score             -> separations rows   (offline)
Then:
       permute.permute              -> the permutation null (Section 6)
       claims.report                -> RU-1..RU-5 and N1..N5 (Sections 7-8)

The core never imports a model. `model.ModelAdapter` is the contract; adapters
live in examples/. separations rows carry exactly `SEPARATION_FIELDS` and no
label; `separation.check_contract` refuses anything else.
"""

from .base_pass import BaseRow, base_tokens, run_base_pass
from .claims import PARAMS, report, separation_set, summary, sustained_set, topk_sensitivity
from .model import Distribution, ModelAdapter, entropy_from_topk, entropy_of
from .permute import permute
from .records import read_jsonl, write_jsonl
from .selection import N_SWEEP, selection_sets, top_entropy_positions, union_positions
from .separation import (
    D_SWEEP,
    MIN_MATCH,
    SEPARATION_FIELDS,
    SLACK,
    check_contract,
    normalized_edit_distance,
    resync,
    score,
    write_separations,
)
from .trace import D_MAX, RANKS, TraceRow, trace_position, trace_positions

__all__ = [
    "BaseRow", "base_tokens", "run_base_pass",
    "PARAMS", "report", "separation_set", "summary", "sustained_set", "topk_sensitivity",
    "Distribution", "ModelAdapter", "entropy_from_topk", "entropy_of",
    "permute",
    "read_jsonl", "write_jsonl",
    "N_SWEEP", "selection_sets", "top_entropy_positions", "union_positions",
    "D_SWEEP", "MIN_MATCH", "SEPARATION_FIELDS", "SLACK",
    "check_contract", "normalized_edit_distance", "resync", "score", "write_separations",
    "D_MAX", "RANKS", "TraceRow", "trace_position", "trace_positions",
]
