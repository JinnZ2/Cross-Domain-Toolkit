"""STAGE D -- separation scoring. Offline. No model.

For each (i, branch, D):
    resync_D = 1 if the continuation is back on the base track at distance D:
               its last run of >= MIN_MATCH tokens appears contiguously in
               base[i : i+D+slack]. Else 0.
    div_D    = Levenshtein distance between continuation[:D] and base[i:i+D]
               over token ids, divided by the longer length.
    ent_i    = entropy at i (carried through)
    gap_i    = logprob_taken - logprob_runner_up at i

The output row carries EXACTLY the fields in SEPARATION_FIELDS. There is no
label field and the writer refuses one.

Declared parameters (free, so named, never tuned per case):
    D_SWEEP   = (8, 16, 32, 64, 128)
    MIN_MATCH = 4        minimum rejoin run length
    SLACK     = 4        extra base tokens searched past i+D, to tolerate a
                         one-or-few-token insertion in the branch
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Sequence

from .base_pass import BaseRow
from .trace import TraceRow

D_SWEEP = (8, 16, 32, 64, 128)
MIN_MATCH = 4
SLACK = 4

SEPARATION_FIELDS = ("case_id", "model_id", "i", "branch_rank", "D",
                     "ent_i", "gap_i", "resync_D", "div_D")


def levenshtein(a: Sequence[int], b: Sequence[int]) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for ia, ca in enumerate(a, 1):
        cur = [ia]
        for ib, cb in enumerate(b, 1):
            cur.append(min(prev[ib] + 1, cur[ib - 1] + 1,
                           prev[ib - 1] + (0 if ca == cb else 1)))
        prev = cur
    return prev[-1]


def normalized_edit_distance(a: Sequence[int], b: Sequence[int]) -> float:
    n = max(len(a), len(b))
    return 0.0 if n == 0 else levenshtein(a, b) / n


def _contains(hay: Sequence[int], needle: Sequence[int]) -> bool:
    n = len(needle)
    if n == 0 or n > len(hay):
        return False
    return any(list(hay[j:j + n]) == list(needle) for j in range(len(hay) - n + 1))


def resync(cont: Sequence[int], base_window: Sequence[int],
           min_match: int = MIN_MATCH) -> int:
    """1 iff the tail of `cont` (length >= min_match) is a contiguous run in
    `base_window`. The longest matching tail is tried first; any tail of
    length >= min_match that matches counts."""
    if len(cont) < min_match:
        return 0
    for length in range(len(cont), min_match - 1, -1):
        if _contains(base_window, cont[-length:]):
            return 1
    return 0


def score(
    base_rows: Sequence[BaseRow],
    traces: Iterable[TraceRow],
    case_id: str,
    model_id: str,
    d_sweep: Sequence[int] = D_SWEEP,
    min_match: int = MIN_MATCH,
    slack: int = SLACK,
) -> List[Dict]:
    base = [r.token_taken for r in base_rows]
    by_i = {r.i: r for r in base_rows}
    out: List[Dict] = []
    for t in traces:
        row = by_i[t.i]
        gap = row.logprob_taken - t.logprob_forced
        for d in d_sweep:
            cont = t.continuation[:d]
            base_d = base[t.i:t.i + d]
            base_win = base[t.i:t.i + d + slack]
            out.append({
                "case_id": case_id,
                "model_id": model_id,
                "i": t.i,
                "branch_rank": t.branch_rank,
                "D": d,
                "ent_i": row.entropy_i,
                "gap_i": gap,
                "resync_D": resync(cont, base_win, min_match),
                "div_D": normalized_edit_distance(cont, base_d),
            })
    return out


def check_contract(rows: Iterable[Dict]) -> None:
    """Raise if any row carries a field outside SEPARATION_FIELDS or lacks one.
    A label, category, type, or frame name is a contract violation."""
    want = set(SEPARATION_FIELDS)
    for n, row in enumerate(rows):
        got = set(row)
        if got != want:
            extra = sorted(got - want)
            missing = sorted(want - got)
            raise ValueError(
                f"separations row {n}: extra={extra} missing={missing}; "
                f"rows carry exactly {SEPARATION_FIELDS}")


def write_separations(path: str, rows: Sequence[Dict]) -> int:
    from .records import write_jsonl
    check_contract(rows)
    return write_jsonl(path, rows)


def _main(argv=None) -> int:
    import argparse
    from .records import read_jsonl
    p = argparse.ArgumentParser(description="STAGE D: score separations offline.")
    p.add_argument("base_jsonl")
    p.add_argument("traces_jsonl")
    p.add_argument("out_jsonl")
    p.add_argument("--case-id", required=True)
    p.add_argument("--model-id", required=True)
    p.add_argument("--min-match", type=int, default=MIN_MATCH)
    p.add_argument("--slack", type=int, default=SLACK)
    a = p.parse_args(argv)
    base_rows = [BaseRow.from_record(r) for r in read_jsonl(a.base_jsonl)]
    traces = [TraceRow.from_record(r) for r in read_jsonl(a.traces_jsonl)]
    rows = score(base_rows, traces, a.case_id, a.model_id,
                 min_match=a.min_match, slack=a.slack)
    n = write_separations(a.out_jsonl, rows)
    print(f"wrote {n} rows -> {a.out_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
