"""JSONL in/out. Every stage writes one record per line; nothing else."""

from __future__ import annotations

import json
from typing import Dict, Iterable, Iterator, List


def write_jsonl(path: str, rows: Iterable[Dict]) -> int:
    n = 0
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
            n += 1
    return n


def read_jsonl(path: str) -> List[Dict]:
    return list(iter_jsonl(path))


def iter_jsonl(path: str) -> Iterator[Dict]:
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)
