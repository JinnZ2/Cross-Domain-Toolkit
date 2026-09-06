"""Section 6 -- the permutation null.

Shuffle which position index carries which (ent_i, gap_i, resync_D, div_D)
tuple. Two declared modes:

    "row"      (default) within each (case_id, model_id, branch_rank, D)
               stratum, permute the tuples across positions independently.
               Destroys cross-D coherence and cross-model overlap; preserves
               every marginal.
    "position" one permutation of positions per (case_id, model_id), applied
               consistently across branch and D. Destroys position identity
               only; a summary that ignores position is unchanged by it.

The permuted file is a SECOND OUTPUT, filed beside the real one. It is not a
gate. Seed is recorded by the caller.
"""

from __future__ import annotations

import random
from collections import defaultdict
from typing import Dict, List, Sequence

TUPLE_FIELDS = ("ent_i", "gap_i", "resync_D", "div_D")


def permute(rows: Sequence[Dict], seed: int, mode: str = "row") -> List[Dict]:
    rng = random.Random(seed)
    if mode == "row":
        return _permute_rows(rows, rng)
    if mode == "position":
        return _permute_positions(rows, rng)
    raise ValueError(f"unknown mode {mode!r}; use 'row' or 'position'")


def _permute_rows(rows: Sequence[Dict], rng: random.Random) -> List[Dict]:
    strata: Dict[tuple, List[int]] = defaultdict(list)
    for idx, r in enumerate(rows):
        strata[(r["case_id"], r["model_id"], r["branch_rank"], r["D"])].append(idx)
    out = [dict(r) for r in rows]
    for idxs in strata.values():
        tuples = [tuple(rows[j][f] for f in TUPLE_FIELDS) for j in idxs]
        rng.shuffle(tuples)
        for j, tup in zip(idxs, tuples):
            for f, v in zip(TUPLE_FIELDS, tup):
                out[j][f] = v
    return out


def _permute_positions(rows: Sequence[Dict], rng: random.Random) -> List[Dict]:
    positions: Dict[tuple, set] = defaultdict(set)
    for r in rows:
        positions[(r["case_id"], r["model_id"])].add(r["i"])
    maps: Dict[tuple, Dict[int, int]] = {}
    for key, ps in positions.items():
        src = sorted(ps)
        dst = src[:]
        rng.shuffle(dst)
        maps[key] = dict(zip(src, dst))
    out = []
    for r in rows:
        r2 = dict(r)
        r2["i"] = maps[(r["case_id"], r["model_id"])][r["i"]]
        out.append(r2)
    return out


def _main(argv=None) -> int:
    import argparse
    from .records import read_jsonl
    from .separation import write_separations
    p = argparse.ArgumentParser(description="Permutation null over separations.jsonl.")
    p.add_argument("separations_jsonl")
    p.add_argument("out_jsonl")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--mode", choices=("row", "position"), default="row")
    a = p.parse_args(argv)
    rows = read_jsonl(a.separations_jsonl)
    n = write_separations(a.out_jsonl, permute(rows, a.seed, a.mode))
    print(f"wrote {n} permuted rows (mode={a.mode}, seed={a.seed}) -> {a.out_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
