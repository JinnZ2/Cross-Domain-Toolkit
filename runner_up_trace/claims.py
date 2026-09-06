"""Sections 5-8 -- summaries, the five claims with refutation conditions, and
the nulls that must be reported.

Everything here runs on separations.jsonl rows (plus, optionally, the
selection sets from Stage B and a permuted copy from Section 6). No model.
No labels are read or written. Every threshold is a declared parameter and is
echoed into the report, because an unstated threshold is a free parameter and
free parameters manufacture results.

A claim's status is one of:
    "held"           its refutation condition did not fire
    "refuted"        its refutation condition fired (still a publishable result)
    "not_evaluable"  the inputs needed to test it were not supplied
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .separation import D_SWEEP

PARAMS = {
    "div_min": 0.5,        # a branch is 'separated' at D iff resync_D == 0 and div_D >= div_min
    "branch_rule": "any",  # a position is separated at D iff ANY traced branch is
    "d_sustained": 64,     # RU-1: sustained = separated at every D >= this in the sweep
    "resync_all": 0.95,    # RU-1 refuted iff mean resync over all rows >= this
    "jaccard_min": 0.8,    # RU-3: consecutive-D separation sets stable iff Jaccard >= this
    "z_crit": 1.96,        # RU-2: two-proportion z; |z| below this = 'not distinguishable'
    "p_crit": 0.05,        # RU-4: hypergeometric upper tail; p >= this = 'at chance'
}

Key = Tuple[str, str, int]  # (case_id, model_id, i)


# --------------------------------------------------------------------------
# summaries
# --------------------------------------------------------------------------

def d_values(rows: Iterable[Dict]) -> List[int]:
    return sorted({int(r["D"]) for r in rows}) or list(D_SWEEP)


def traced_positions(rows: Iterable[Dict]) -> Set[Key]:
    return {(r["case_id"], r["model_id"], int(r["i"])) for r in rows}


def separation_set(rows: Iterable[Dict], d: int, params: Dict = PARAMS) -> Set[Key]:
    """Positions separated at distance d under the declared branch rule."""
    per_pos: Dict[Key, List[bool]] = defaultdict(list)
    for r in rows:
        if int(r["D"]) != d:
            continue
        sep = int(r["resync_D"]) == 0 and float(r["div_D"]) >= params["div_min"]
        per_pos[(r["case_id"], r["model_id"], int(r["i"]))].append(sep)
    rule = all if params["branch_rule"] == "all" else any
    return {k for k, flags in per_pos.items() if rule(flags)}


def sustained_set(rows: Sequence[Dict], params: Dict = PARAMS) -> Set[Key]:
    ds = [d for d in d_values(rows) if d >= params["d_sustained"]]
    if not ds:
        return set()
    acc: Optional[Set[Key]] = None
    for d in ds:
        s = separation_set(rows, d, params)
        acc = s if acc is None else acc & s
    return acc or set()


def jaccard(a: Set, b: Set) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def stability_across_d(rows: Sequence[Dict], params: Dict = PARAMS) -> Dict:
    """Jaccard between separation sets at consecutive D, and the smallest D
    from which every later consecutive pair meets jaccard_min (None if none)."""
    ds = d_values(rows)
    sets = {d: separation_set(rows, d, params) for d in ds}
    pairs = [(ds[j], ds[j + 1], jaccard(sets[ds[j]], sets[ds[j + 1]]))
             for j in range(len(ds) - 1)]
    stable_from = None
    for j in range(len(pairs)):
        if all(jc >= params["jaccard_min"] for _, _, jc in pairs[j:]):
            stable_from = pairs[j][0]
            break
    if not pairs and ds:
        stable_from = ds[0]
    return {"consecutive_jaccard": [{"D_lo": a, "D_hi": b, "jaccard": round(jc, 4)}
                                    for a, b, jc in pairs],
            "stable_from_D": stable_from,
            "set_sizes": {str(d): len(sets[d]) for d in ds}}


def summary(rows: Sequence[Dict], params: Dict = PARAMS) -> Dict:
    n = len(rows)
    return {
        "rows": n,
        "positions_traced": len(traced_positions(rows)),
        "mean_resync": (sum(int(r["resync_D"]) for r in rows) / n) if n else None,
        "mean_div": (sum(float(r["div_D"]) for r in rows) / n) if n else None,
        "sustained_positions": sorted(sustained_set(rows, params)),
        "stability": stability_across_d(rows, params),
    }


# --------------------------------------------------------------------------
# helpers for RU-2 and RU-4
# --------------------------------------------------------------------------

def two_proportion_z(k1: int, n1: int, k2: int, n2: int) -> Optional[float]:
    if n1 == 0 or n2 == 0:
        return None
    p1, p2 = k1 / n1, k2 / n2
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    return None if se == 0 else (p1 - p2) / se


def hypergeom_upper_tail(obs: int, n: int, a: int, b: int) -> float:
    """P(X >= obs) when a marked and b drawn without replacement from n."""
    if n == 0:
        return 1.0
    total = math.comb(n, b)
    hi = min(a, b)
    return sum(math.comb(a, x) * math.comb(n - a, b - x) for x in range(obs, hi + 1)) / total


def _rate(keys: Set[Key], positions: Set[Key]) -> Tuple[int, int]:
    return len(keys & positions), len(positions)


# --------------------------------------------------------------------------
# claims
# --------------------------------------------------------------------------

def ru1(rows: Sequence[Dict], params: Dict = PARAMS) -> Dict:
    n = len(rows)
    if n == 0:
        return {"claim": "RU-1", "status": "not_evaluable", "reason": "no rows"}
    mean_resync = sum(int(r["resync_D"]) for r in rows) / n
    sus = sustained_set(rows, params)
    refuted = mean_resync >= params["resync_all"]
    return {"claim": "RU-1",
            "status": "refuted" if refuted else ("held" if sus else "not_evaluable"),
            "reason": (None if sus or refuted else
                       "no sustained-separation position, but resync did not approach 1 either"),
            "evidence": {"mean_resync": round(mean_resync, 4),
                         "sustained_count": len(sus)}}


def ru2(rows: Sequence[Dict], selection: Optional[Sequence[Dict]],
        case_id: str, model_id: str, params: Dict = PARAMS) -> Dict:
    if not selection:
        return {"claim": "RU-2", "status": "not_evaluable",
                "reason": "selection sets not supplied (need top_entropy and random control)"}
    sus = sustained_set(rows, params)
    top = {(case_id, model_id, i) for s in selection if s["rule"] == "top_entropy"
           for i in s["positions"]}
    rnd = {(case_id, model_id, i) for s in selection if s["rule"] == "random"
           for i in s["positions"]}
    traced = traced_positions(rows)
    top &= traced
    rnd &= traced
    if not top:
        return {"claim": "RU-2", "status": "not_evaluable", "reason": "no traced top-entropy positions"}
    k1, n1 = _rate(sus, top)
    ev = {"top_entropy": {"separated": k1, "n": n1, "rate": round(k1 / n1, 4)}}
    if not rnd:
        return {"claim": "RU-2", "status": "not_evaluable",
                "reason": "no random control positions traced; base rate unknown", "evidence": ev}
    k2, n2 = _rate(sus, rnd)
    z = two_proportion_z(k1, n1, k2, n2)
    ev["random_control"] = {"separated": k2, "n": n2, "rate": round(k2 / n2, 4)}
    ev["z"] = None if z is None else round(z, 3)
    minority = k1 / n1 < 0.5
    distinguishable = z is not None and abs(z) >= params["z_crit"]
    if not distinguishable:
        status = "refuted"
    elif minority:
        status = "held"
    else:
        status = "refuted"
        ev["note"] = "distinguishable from base rate but not a minority (see N2)"
    return {"claim": "RU-2", "status": status, "evidence": ev}


def ru3(rows: Sequence[Dict], params: Dict = PARAMS) -> Dict:
    st = stability_across_d(rows, params)
    if len(d_values(rows)) < 2:
        return {"claim": "RU-3", "status": "not_evaluable", "reason": "fewer than two D values"}
    return {"claim": "RU-3",
            "status": "held" if st["stable_from_D"] is not None else "refuted",
            "evidence": st}


def ru4(rows: Sequence[Dict], params: Dict = PARAMS) -> Dict:
    by_case: Dict[str, Dict[str, Set[int]]] = defaultdict(dict)
    sus = sustained_set(rows, params)
    traced = traced_positions(rows)
    models_by_case: Dict[str, Set[str]] = defaultdict(set)
    for c, m, _ in traced:
        models_by_case[c].add(m)
    pairs = []
    for c, models in models_by_case.items():
        ms = sorted(models)
        for a_idx in range(len(ms)):
            for b_idx in range(a_idx + 1, len(ms)):
                ma, mb = ms[a_idx], ms[b_idx]
                common = {i for (cc, mm, i) in traced if cc == c and mm == ma} & \
                         {i for (cc, mm, i) in traced if cc == c and mm == mb}
                A = {i for (cc, mm, i) in sus if cc == c and mm == ma} & common
                B = {i for (cc, mm, i) in sus if cc == c and mm == mb} & common
                obs = len(A & B)
                n = len(common)
                exp = (len(A) * len(B) / n) if n else 0.0
                p = hypergeom_upper_tail(obs, n, len(A), len(B)) if n else 1.0
                pairs.append({"case_id": c, "models": [ma, mb], "common": n,
                              "observed_overlap": obs, "expected_overlap": round(exp, 3),
                              "p_upper": round(p, 4)})
    if not pairs:
        return {"claim": "RU-4", "status": "not_evaluable",
                "reason": "no case traced on two or more models"}
    above = [pr for pr in pairs if pr["p_upper"] < params["p_crit"]]
    return {"claim": "RU-4", "status": "held" if above else "refuted",
            "evidence": {"pairs": pairs, "pairs_above_chance": len(above)}}


def ru5(rows: Sequence[Dict], permuted: Optional[Sequence[Dict]],
        params: Dict = PARAMS) -> Dict:
    if permuted is None:
        return {"claim": "RU-5", "status": "not_evaluable", "reason": "no permuted file supplied"}
    real, perm = summary(rows, params), summary(permuted, params)
    ev = {"real": {"sustained_count": len(real["sustained_positions"]),
                   "stable_from_D": real["stability"]["stable_from_D"]},
          "permuted": {"sustained_count": len(perm["sustained_positions"]),
                       "stable_from_D": perm["stability"]["stable_from_D"]}}
    reproduces = (len(perm["sustained_positions"]) >= len(real["sustained_positions"])
                  and (perm["stability"]["stable_from_D"] is not None
                       or real["stability"]["stable_from_D"] is None))
    return {"claim": "RU-5", "status": "refuted" if reproduces else "held", "evidence": ev}


# --------------------------------------------------------------------------
# nulls (Section 7) -- reported, never used to discard
# --------------------------------------------------------------------------

def nulls(rows: Sequence[Dict], claims: Sequence[Dict],
          selection: Optional[Sequence[Dict]] = None,
          case_id: str = "", model_id: str = "",
          params: Dict = PARAMS) -> List[Dict]:
    by = {c["claim"]: c for c in claims}
    out = []
    n = len(rows)
    mean_resync = (sum(int(r["resync_D"]) for r in rows) / n) if n else None
    out.append({"null": "N1", "fires": bool(n) and mean_resync >= params["resync_all"],
                "what": "separations land only on wording; nothing here",
                "evidence": {"mean_resync": mean_resync}})
    r2 = by.get("RU-2", {}).get("evidence", {}).get("top_entropy")
    out.append({"null": "N2", "fires": bool(r2) and r2["rate"] >= 1.0,
                "what": "every high-entropy position separates; entropy alone is the measure",
                "evidence": r2})
    # N3: D-dependence from RU-3; N-dependence from per-N separation rates
    n_rates = {}
    if selection:
        sus = sustained_set(rows, params)
        traced = traced_positions(rows)
        for s in selection:
            if s["rule"] != "top_entropy":
                continue
            ps = {(case_id, model_id, i) for i in s["positions"]} & traced
            if ps:
                n_rates[str(s["N"])] = round(len(sus & ps) / len(ps), 4)
    n_dep = len(set(n_rates.values())) > 1
    out.append({"null": "N3", "fires": by.get("RU-3", {}).get("status") == "refuted" or n_dep,
                "what": "results depend on D or on N; instrument-dependence finding",
                "evidence": {"stable_from_D": by.get("RU-3", {}).get("evidence", {}).get("stable_from_D"),
                             "separation_rate_by_N": n_rates}})
    out.append({"null": "N4", "fires": by.get("RU-5", {}).get("status") == "refuted",
                "what": "permuted run clusters as well as the real run; method artifact",
                "evidence": by.get("RU-5", {}).get("evidence")})
    out.append({"null": "N5", "fires": None,
                "what": "top-k truncation changes the entropy ordering; needs two base passes "
                        "at different k (see topk_sensitivity)",
                "evidence": None})
    return out


def topk_sensitivity(base_a: Sequence, base_b: Sequence, n_sweep: Sequence[int] = (10, 25, 50)) -> Dict:
    """N5: overlap of top-N entropy positions between two base passes of the
    same prompt at different k. 1.0 = identical ordering at that N."""
    from .selection import top_entropy_positions
    out = {}
    for n in n_sweep:
        a = set(top_entropy_positions(base_a, n))
        b = set(top_entropy_positions(base_b, n))
        out[str(n)] = round(jaccard(a, b), 4)
    return out


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------

def report(rows: Sequence[Dict], permuted: Optional[Sequence[Dict]] = None,
           selection: Optional[Sequence[Dict]] = None,
           case_id: str = "", model_id: str = "",
           params: Dict = PARAMS) -> Dict:
    claims = [ru1(rows, params),
              ru2(rows, selection, case_id, model_id, params),
              ru3(rows, params),
              ru4(rows, params),
              ru5(rows, permuted, params)]
    return {"params": dict(params),
            "summary_real": summary(rows, params),
            "summary_permuted": summary(permuted, params) if permuted is not None else None,
            "claims": claims,
            "nulls": nulls(rows, claims, selection, case_id, model_id, params)}


def _main(argv=None) -> int:
    import argparse
    import json
    from .records import read_jsonl
    p = argparse.ArgumentParser(description="Claims RU-1..RU-5 and nulls N1..N5 over separations.jsonl.")
    p.add_argument("separations_jsonl")
    p.add_argument("--permuted", help="permuted separations.jsonl (Section 6)")
    p.add_argument("--selection", help="selection.jsonl from Stage B")
    p.add_argument("--case-id", default="")
    p.add_argument("--model-id", default="")
    a = p.parse_args(argv)
    rows = read_jsonl(a.separations_jsonl)
    perm = read_jsonl(a.permuted) if a.permuted else None
    sel = read_jsonl(a.selection) if a.selection else None
    print(json.dumps(report(rows, perm, sel, a.case_id, a.model_id), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
