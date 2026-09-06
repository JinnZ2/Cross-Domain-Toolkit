"""The adapter contract the trace core consumes. The core never imports a model.

A model adapter exposes exactly what the instrument needs and nothing else:

    tokenize(text)                      -> token ids
    next_token_distribution(prefix)     -> Distribution (top-k over the vocab)
    continue_greedy(prefix, n)          -> n greedy token ids   [optional]

`continue_greedy` is an efficiency hook: an API that can return a greedy
continuation in one call should implement it. If it is absent the core loops
`next_token_distribution` one token at a time, which is correct and slow.

Entropy is natural-log. If the adapter can see the full distribution it fills
`Distribution.full_entropy`; otherwise the core computes a top-k truncated
entropy over the renormalised top-k and records which one it used
(`entropy_kind`). That choice is declared in every base row, never silent.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Distribution:
    """Top-k of the next-token distribution at one position.

    `top_k` is a list of (token_id, logprob) sorted by logprob descending.
    `full_entropy`, when present, is the entropy of the untruncated
    distribution (nats). `texts` optionally maps the same indices to strings
    for readability; it is never used for scoring.
    """

    top_k: Sequence[Tuple[int, float]]
    full_entropy: Optional[float] = None
    texts: Sequence[str] = field(default_factory=tuple)

    @property
    def k(self) -> int:
        return len(self.top_k)

    def rank(self, r: int) -> Tuple[int, float]:
        """1-based rank into top_k. rank(1) is the greedy token."""
        return self.top_k[r - 1]


class ModelAdapter:
    """Duck-typed base. Subclass or just match the surface."""

    model_id: str = "unnamed-model"
    eos_token: Optional[int] = None

    def tokenize(self, text: str) -> List[int]:  # pragma: no cover - contract
        raise NotImplementedError

    def next_token_distribution(self, prefix: Sequence[int]) -> Distribution:  # pragma: no cover
        raise NotImplementedError

    def continue_greedy(self, prefix: Sequence[int], n: int) -> List[int]:
        """Default: n single-token greedy steps. Override for batch APIs."""
        out: List[int] = []
        cur = list(prefix)
        for _ in range(n):
            dist = self.next_token_distribution(cur)
            if dist.k == 0:
                break
            tok, _ = dist.rank(1)
            out.append(tok)
            cur.append(tok)
            if self.eos_token is not None and tok == self.eos_token:
                break
        return out


def entropy_from_topk(top_k: Sequence[Tuple[int, float]]) -> float:
    """Entropy (nats) of the renormalised top-k. Truncated, and says so by name."""
    if not top_k:
        return 0.0
    lps = [lp for _, lp in top_k]
    m = max(lps)
    z = sum(math.exp(lp - m) for lp in lps)
    log_z = m + math.log(z)
    h = 0.0
    for lp in lps:
        p = math.exp(lp - log_z)
        if p > 0.0:
            h -= p * (lp - log_z)
    return h


def entropy_of(dist: Distribution) -> Tuple[float, str]:
    """(entropy, kind) with kind in {"full", "topk"}."""
    if dist.full_entropy is not None:
        return float(dist.full_entropy), "full"
    return entropy_from_topk(dist.top_k), "topk"
