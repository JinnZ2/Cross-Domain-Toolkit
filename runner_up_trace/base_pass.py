"""STAGE A -- base pass.

Greedy decode of prompt P. For every generated position i record:
    i, token_taken, logprob_taken, top_k (ids + logprobs), entropy_i,
    entropy_kind ("full" | "topk"), k
Output: base.jsonl (one row per position).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from .model import Distribution, ModelAdapter, entropy_of


@dataclass(frozen=True)
class BaseRow:
    i: int
    token_taken: int
    logprob_taken: float
    top_k: List[Tuple[int, float]]
    entropy_i: float
    entropy_kind: str
    k: int
    token_text: Optional[str] = None

    def to_record(self) -> Dict:
        d = asdict(self)
        d["top_k"] = [[t, lp] for t, lp in self.top_k]
        return d

    @classmethod
    def from_record(cls, d: Dict) -> "BaseRow":
        return cls(
            i=int(d["i"]),
            token_taken=int(d["token_taken"]),
            logprob_taken=float(d["logprob_taken"]),
            top_k=[(int(t), float(lp)) for t, lp in d["top_k"]],
            entropy_i=float(d["entropy_i"]),
            entropy_kind=str(d["entropy_kind"]),
            k=int(d["k"]),
            token_text=d.get("token_text"),
        )

    def runner_up(self, rank: int) -> Tuple[int, float]:
        """(token, logprob) at 1-based rank; rank 1 is the taken token."""
        return self.top_k[rank - 1]


def row_from_distribution(i: int, dist: Distribution, taken: int) -> BaseRow:
    ent, kind = entropy_of(dist)
    lp_taken = next((lp for t, lp in dist.top_k if t == taken), float("nan"))
    text = None
    if dist.texts:
        for (t, _), s in zip(dist.top_k, dist.texts):
            if t == taken:
                text = s
                break
    return BaseRow(
        i=i,
        token_taken=taken,
        logprob_taken=lp_taken,
        top_k=list(dist.top_k),
        entropy_i=ent,
        entropy_kind=kind,
        k=dist.k,
        token_text=text,
    )


def run_base_pass(
    model: ModelAdapter,
    prompt_tokens: Sequence[int],
    max_tokens: int,
) -> List[BaseRow]:
    """Greedy pass. Position i is the i-th generated token (0-based), so the
    prefix at i is prompt + base[:i]. Stops at eos or max_tokens."""
    rows: List[BaseRow] = []
    cur = list(prompt_tokens)
    for i in range(max_tokens):
        dist = model.next_token_distribution(cur)
        if dist.k == 0:
            break
        taken, _ = dist.rank(1)
        rows.append(row_from_distribution(i, dist, taken))
        cur.append(taken)
        if model.eos_token is not None and taken == model.eos_token:
            break
    return rows


def base_tokens(rows: Sequence[BaseRow]) -> List[int]:
    return [r.token_taken for r in rows]
