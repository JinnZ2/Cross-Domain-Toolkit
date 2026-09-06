"""STAGE C -- forced continuation.

For each traced position i and each runner-up rank r in RANKS (2 and 3):
    rebuild prefix = prompt + base[:i], force top_k[r] at i,
    continue greedily so the continuation (forced token included) is D_MAX long.
The full D_MAX continuation is recorded once; the D sweep truncates at scoring.
Output: traces.jsonl
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Sequence

from .base_pass import BaseRow
from .model import ModelAdapter

RANKS = (2, 3)
D_MAX = 128


@dataclass(frozen=True)
class TraceRow:
    i: int
    branch_rank: int
    forced_token: int
    logprob_forced: float
    continuation: List[int]  # continuation[0] == forced_token

    def to_record(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_record(cls, d: Dict) -> "TraceRow":
        return cls(int(d["i"]), int(d["branch_rank"]), int(d["forced_token"]),
                   float(d["logprob_forced"]), [int(t) for t in d["continuation"]])


def trace_position(
    model: ModelAdapter,
    prompt_tokens: Sequence[int],
    base_rows: Sequence[BaseRow],
    i: int,
    ranks: Sequence[int] = RANKS,
    d_max: int = D_MAX,
) -> List[TraceRow]:
    row = base_rows[i]
    prefix = list(prompt_tokens) + [r.token_taken for r in base_rows[:i]]
    out: List[TraceRow] = []
    for r in ranks:
        if r > row.k:
            continue  # fewer than r alternatives recorded; no row, no guess
        tok, lp = row.runner_up(r)
        cont = [tok] + model.continue_greedy(prefix + [tok], d_max - 1)
        out.append(TraceRow(i=i, branch_rank=r, forced_token=tok,
                            logprob_forced=lp, continuation=cont))
    return out


def trace_positions(
    model: ModelAdapter,
    prompt_tokens: Sequence[int],
    base_rows: Sequence[BaseRow],
    positions: Sequence[int],
    ranks: Sequence[int] = RANKS,
    d_max: int = D_MAX,
) -> List[TraceRow]:
    out: List[TraceRow] = []
    for i in positions:
        out.extend(trace_position(model, prompt_tokens, base_rows, i, ranks, d_max))
    return out
