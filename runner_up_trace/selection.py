"""STAGE B -- candidate selection. The rule is DECLARED, not tuned.

    trace position i if entropy_i is in the top N of the pass,
    for N in {10, 25, 50}, each logged separately.

Ties are broken by position (earlier wins). No hand-picking, no selection on
content. The optional `random_positions` control is the base-rate comparison
RU-2 needs: same N, seeded, logged under its own name.
"""

from __future__ import annotations

import random
from typing import Dict, List, Sequence

from .base_pass import BaseRow

N_SWEEP = (10, 25, 50)


def top_entropy_positions(rows: Sequence[BaseRow], n: int) -> List[int]:
    order = sorted(rows, key=lambda r: (-r.entropy_i, r.i))
    return sorted(r.i for r in order[:n])


def random_positions(rows: Sequence[BaseRow], n: int, seed: int) -> List[int]:
    rng = random.Random(seed)
    pool = [r.i for r in rows]
    return sorted(rng.sample(pool, min(n, len(pool))))


def selection_sets(
    rows: Sequence[BaseRow],
    n_sweep: Sequence[int] = N_SWEEP,
    random_seed: int = 0,
    with_random_control: bool = True,
) -> List[Dict]:
    """One record per (rule, N). Returned in a form ready for selection.jsonl."""
    out: List[Dict] = []
    for n in n_sweep:
        out.append({"rule": "top_entropy", "N": n,
                    "positions": top_entropy_positions(rows, n)})
        if with_random_control:
            out.append({"rule": "random", "N": n, "seed": random_seed,
                        "positions": random_positions(rows, n, random_seed + n)})
    return out


def union_positions(sets: Sequence[Dict]) -> List[int]:
    acc = set()
    for s in sets:
        acc.update(s["positions"])
    return sorted(acc)
