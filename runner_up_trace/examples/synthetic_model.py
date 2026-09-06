"""A deterministic toy language model, so the pipeline runs end to end with no
weights and no network.

It is a hashed second-order Markov process over a small vocabulary: the next
token distribution depends on the last two tokens and a seed. Some contexts
are peaked (one clear next token), some are flat (many live alternatives).
Because state is only two tokens, branches that reach the same bigram converge,
so continuations sometimes rejoin the base and sometimes wander. That is
enough to exercise every stage.

It is NOT a model of anything. Findings on it are findings about the
instrument's plumbing, never about language models. It exists so a reader can
run `python -m runner_up_trace.examples.end_to_end` before they have hardware.

Run:  python -m runner_up_trace.examples.synthetic_model
"""

from __future__ import annotations

import hashlib
import math
from typing import List, Sequence

from ..model import Distribution, ModelAdapter

VOCAB = 48
TOP_K = 20


def _hash_floats(*parts: int) -> List[float]:
    """VOCAB pseudo-random floats in [0,1) from a stable hash of parts."""
    out: List[float] = []
    ctr = 0
    while len(out) < VOCAB:
        h = hashlib.sha256(",".join(str(p) for p in parts + (ctr,)).encode()).digest()
        for j in range(0, len(h) - 3, 4):
            out.append(int.from_bytes(h[j:j + 4], "big") / 2 ** 32)
            if len(out) == VOCAB:
                break
        ctr += 1
    return out


class SyntheticModel(ModelAdapter):
    """`truncated=True` withholds the full entropy so the core has to compute the
    top-k kind, which is what a top-k-only API looks like."""

    def __init__(self, seed: int = 0, top_k: int = TOP_K, truncated: bool = False,
                 model_id: str = "synthetic-markov-2"):
        self.seed = seed
        self.top_k = top_k
        self.truncated = truncated
        self.model_id = model_id
        self.eos_token = None

    def tokenize(self, text: str) -> List[int]:
        return [ord(c) % VOCAB for c in text]

    def _logits(self, prefix: Sequence[int]) -> List[float]:
        a = prefix[-2] if len(prefix) >= 2 else -1
        b = prefix[-1] if prefix else -1
        u = _hash_floats(self.seed, a, b)
        # sharpness varies with context: some bigrams are near-deterministic,
        # others are flat. That is what makes an entropy ranking non-trivial.
        sharp = 0.5 + 8.0 * _hash_floats(self.seed + 1, a, b)[0]
        return [sharp * (x - 0.5) * 4.0 for x in u]

    def next_token_distribution(self, prefix: Sequence[int]) -> Distribution:
        logits = self._logits(prefix)
        m = max(logits)
        z = m + math.log(sum(math.exp(l - m) for l in logits))
        lps = [l - z for l in logits]
        order = sorted(range(VOCAB), key=lambda t: (-lps[t], t))[:self.top_k]
        top = [(t, lps[t]) for t in order]
        full = None if self.truncated else -sum(math.exp(lp) * lp for lp in lps)
        return Distribution(top_k=top, full_entropy=full,
                            texts=[f"<{t}>" for t in order])


def main() -> None:
    from ..base_pass import run_base_pass
    from ..selection import top_entropy_positions
    model = SyntheticModel(seed=7)
    prompt = model.tokenize("the projection step, not the output")
    rows = run_base_pass(model, prompt, max_tokens=64)
    print(f"model={model.model_id} positions={len(rows)} entropy_kind={rows[0].entropy_kind}")
    top = top_entropy_positions(rows, 10)
    print("top-10 entropy positions (declared rule, ties by position):", top)
    for i in top[:5]:
        r = rows[i]
        r2 = r.runner_up(2)
        print(f"  i={i:3d} taken={r.token_taken:3d} lp={r.logprob_taken:+.3f} "
              f"ent={r.entropy_i:.3f} runner_up={r2[0]:3d} gap={r.logprob_taken - r2[1]:.3f}")


if __name__ == "__main__":
    main()
