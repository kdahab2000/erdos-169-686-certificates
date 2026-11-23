#!/usr/bin/env python3
"""Exact branch-and-bound optimiser for prefix maxima g_k(N).

The search objective is the sum of reciprocals.  All bounds use the exact
integer weights L/i, where L=lcm(1,...,N), and the emitted proof can be
replayed independently by ``verifiers.proof_replay``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from fractions import Fraction
from typing import Dict, List, Optional, Sequence, Set, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from verifiers.common import canonical_json_bytes, lcm


class NodeLimit(Exception):
    pass


def contains_ap(values: Set[int], k: int) -> bool:
    if len(values) < k:
        return False
    ordered = sorted(values)
    maximum = ordered[-1]
    for start in ordered:
        for difference in range(1, (maximum - start) // (k - 1) + 1):
            if all(start + index * difference in values for index in range(k)):
                return True
    return False


def all_progressions(n: int, k: int) -> List[Tuple[int, int, Tuple[int, ...]]]:
    result: List[Tuple[int, int, Tuple[int, ...]]] = []
    for start in range(1, n + 1):
        for difference in range(1, (n - start) // (k - 1) + 1):
            result.append(
                (start, difference, tuple(start + index * difference for index in range(k)))
            )
    return result


def active_disjoint_ap_pairs(
    excluded: Set[int], undecided: Set[int], k: int, n: int
) -> List[Tuple[int, int]]:
    """Return a deterministic disjoint family of active progression deductions."""

    candidates: List[Tuple[int, int, Set[int]]] = []
    for start in range(1, n + 1):
        for difference in range(1, (n - start) // (k - 1) + 1):
            terms = set(start + index * difference for index in range(k))
            if terms & excluded:
                continue
            active = terms & undecided
            if active:
                candidates.append((start, difference, active))
    # Pack by the greatest exact minimum undecided reciprocal weight.
    candidates.sort(key=lambda item: (-Fraction(1, max(item[2])), item[0], item[1]))
    occupied: Set[int] = set()
    selected: List[Tuple[int, int]] = []
    for start, difference, active in candidates:
        if occupied & active:
            continue
        selected.append((start, difference))
        occupied.update(active)
    return selected


def exact_upper_bound(
    selected: Set[int],
    excluded: Set[int],
    undecided: Set[int],
    k: int,
    n: int,
    common: int,
) -> Tuple[int, List[Tuple[int, int]]]:
    pairs = active_disjoint_ap_pairs(excluded, undecided, k, n)
    terms_by_pair = {
        (start, difference): tuple(start + index * difference for index in range(k))
        for start in range(1, n + 1)
        for difference in range(1, (n - start) // (k - 1) + 1)
    }
    occupied: Set[int] = set()
    deduction = 0
    for pair in pairs:
        active = set(terms_by_pair[pair]) & undecided
        if occupied & active:
            raise AssertionError("internal AP overlap")
        occupied.update(active)
        deduction += min(common // member for member in active)
    upper = (
        sum(common // member for member in selected)
        + sum(common // member for member in undecided)
        - deduction
    )
    return upper, pairs


def solve(k, n, max_nodes=2000000, max_seconds=300, warm_start=None):
    if not 3 <= k <= 256 or not 1 <= n <= 256:
        raise ValueError("invalid bounded dimensions")
    common = 1
    for j in range(1, n+1):
        common = lcm(common, j)
    weights = [common//j for j in range(1, n+1)]
    aps = [(a,d,sum(1 << (j-1) for j in terms)) for a,d,terms in all_progressions(n,k)]
    incidence = [[] for _ in range(n)]
    for a,d,mask in aps:
        for j in range(n):
            if mask >> j & 1:
                incidence[j].append(mask)
    full = (1 << n)-1
    nodes = []
    incumbent = -1
    best = 0
    complete = True
    started = time.monotonic()
    warm = set(warm_start or [])
    if any(j < 1 or j > n for j in warm) or contains_ap(warm, k):
        raise ValueError("invalid warm witness")
    warm_mask = sum(1 << (j-1) for j in warm)
    def weight(mask):
        result = 0
        while mask:
            bit = mask & -mask
            result += weights[bit.bit_length()-1]
            mask ^= bit
        return result
    def visit(selected, excluded, current, infeasible=False):
        nonlocal incumbent, best
        if len(nodes) >= max_nodes or time.monotonic()-started > max_seconds:
            raise NodeLimit
        index = len(nodes)
        nodes.append({})
        if infeasible:
            nodes[index] = {"op":"leaf", "status":"infeasible"}
            return index
        undecided = full ^ (selected | excluded)
        if not undecided:
            nodes[index] = {"op":"leaf", "status":"feasible"}
            if current > incumbent:
                incumbent, best = current, selected
            return index
        active = []
        forced = 0
        for a,d,mask in aps:
            if mask & excluded:
                continue
            todo = mask & undecided
            if todo:
                cost = weights[todo.bit_length()-1]
                active.append((-cost, a,d,todo))
                if todo & (todo-1) == 0:
                    forced |= todo
        active.sort()
        occupied = 0
        deduction = 0
        pairs = []
        for negative,a,d,todo in active:
            if not todo & occupied:
                occupied |= todo
                deduction -= negative
                pairs.append([str(a),str(d)])
        if current+weight(undecided)-deduction <= incumbent:
            nodes[index] = {"op":"prune", "aps":pairs}
            return index
        bit = (forced or undecided) & -(forced or undecided)
        j = bit.bit_length()-1
        nodes[index] = {"op":"branch", "j":str(j+1), "include":"", "exclude":""}
        def include():
            new = selected | bit
            bad = any(mask & new == mask for mask in incidence[j])
            return visit(new,excluded,current+weights[j],bad)
        def exclude():
            return visit(selected,excluded|bit,current)
        # Dive through a feasible previous-prefix witness before pruning.
        if incumbent < 0 and warm_start is not None and not bit & warm_mask:
            exc = exclude(); inc = include()
        else:
            inc = include(); exc = exclude()
        nodes[index]["include"], nodes[index]["exclude"] = str(inc),str(exc)
        return index
    try:
        visit(0,0,0)
    except NodeLimit:
        complete = False
    witness = [j+1 for j in range(n) if best >> j & 1]
    score = sum((Fraction(1,j) for j in witness),Fraction())
    proof = {"schema":"erd169.bnb.v1", "k":str(k), "N":str(n),
             "witness":list(map(str,witness)),
             "witness_score":{"num":str(score.numerator),"den":str(score.denominator)},
             "incumbent_weight":str(max(incumbent,0)), "tree":nodes}
    return {"complete":complete,"proof":proof,"nodes":len(nodes),"witness":witness,
            "score":score,"seconds":time.monotonic()-started}


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, required=True)
    parser.add_argument("--N", type=int, required=True)
    parser.add_argument("--max-nodes", type=int, default=2_000_000)
    parser.add_argument("--max-seconds", type=float, default=300.0)
    parser.add_argument("--output", "--proof-out", dest="output", type=str)
    args = parser.parse_args(argv)
    result = solve(args.k, args.N, args.max_nodes, args.max_seconds)
    payload = canonical_json_bytes(result["proof"])
    if args.output and result["complete"]:
        with open(args.output, "wb") as handle:
            handle.write(payload)
            handle.write(b"\n")
    summary = {
        "proof": result["proof"] if result["complete"] else None,
        "k": args.k,
        "N": args.N,
        "complete": result["complete"],
        "nodes": result["nodes"],
        "score": {
            "num": str(result["score"].numerator),
            "den": str(result["score"].denominator),
        },
    }
    print(json.dumps(summary, sort_keys=True))
    # The summary is intentionally machine-readable JSON.


if __name__ == "__main__":
    main()
