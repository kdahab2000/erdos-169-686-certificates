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
    # Prefer progressions with more unresolved terms, then smaller starts.
    candidates.sort(key=lambda item: (-len(item[2]), item[0], item[1]))
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


def solve(
    k: int,
    n: int,
    max_nodes: int = 2_000_000,
    max_seconds: float = 300.0,
) -> Dict[str, object]:
    if k < 3:
        raise ValueError("k must be at least 3")
    if n < 1:
        raise ValueError("N must be positive")
    common = 1
    for member in range(1, n + 1):
        common = lcm(common, member)
    progressions = all_progressions(n, k)
    terms_by_pair = {
        (start, difference): terms for start, difference, terms in progressions
    }
    nodes: List[Dict[str, object]] = []
    incumbent_members: Set[int] = set()
    incumbent_weight = -1
    started = time.monotonic()
    complete = True
    node_count = 0

    def weight(values: Set[int]) -> int:
        return sum(common // member for member in values)

    def upper_bound(
        selected: Set[int], excluded: Set[int], undecided: Set[int]
    ) -> Tuple[int, List[Tuple[int, int]]]:
        candidates: List[Tuple[int, int, Set[int]]] = []
        for start, difference, terms in progressions:
            term_set = set(terms)
            if term_set & excluded:
                continue
            active = term_set & undecided
            if active:
                candidates.append((start, difference, active))
        candidates.sort(key=lambda item: (-len(item[2]), item[0], item[1]))
        occupied: Set[int] = set()
        pairs: List[Tuple[int, int]] = []
        deduction = 0
        for start, difference, active in candidates:
            if occupied & active:
                continue
            pairs.append((start, difference))
            occupied.update(active)
            deduction += min(common // member for member in active)
        bound = weight(selected) + weight(undecided) - deduction
        return bound, pairs

    def visit(selected: Set[int], excluded: Set[int]) -> None:
        nonlocal incumbent_members, incumbent_weight, complete, node_count
        node_count += 1
        if node_count > max_nodes:
            complete = False
            raise NodeLimit
        if time.monotonic() - started > max_seconds:
            complete = False
            raise NodeLimit
        index = len(nodes)
        nodes.append({})
        undecided = set(range(1, n + 1)) - selected - excluded
        if contains_ap(selected, k):
            nodes[index] = {"op": "leaf", "status": "infeasible"}
            return
        if not undecided:
            nodes[index] = {"op": "leaf", "status": "feasible"}
            candidate_weight = weight(selected)
            if candidate_weight > incumbent_weight:
                incumbent_members = set(selected)
                incumbent_weight = candidate_weight
            return
        bound, pairs = upper_bound(selected, excluded, undecided)
        if bound <= incumbent_weight:
            nodes[index] = {
                "op": "prune",
                "aps": [[str(start), str(difference)] for start, difference in pairs],
            }
            return
        member = min(undecided)
        nodes[index] = {
            "op": "branch",
            "j": str(member),
            "include": "",
            "exclude": "",
        }
        include_index = len(nodes)
        visit(selected | {member}, excluded)
        exclude_index = len(nodes)
        visit(selected, excluded | {member})
        nodes[index]["include"] = str(include_index)
        nodes[index]["exclude"] = str(exclude_index)

    try:
        visit(set(), set())
    except NodeLimit:
        complete = False

    if incumbent_weight < 0:
        incumbent_members = set()
        incumbent_weight = 0
    witness = sorted(incumbent_members)
    score = sum((Fraction(1, member) for member in witness), Fraction(0, 1))
    proof: Dict[str, object] = {
        "schema": "erd169.bnb.v1",
        "k": str(k),
        "N": str(n),
        "witness": [str(member) for member in witness],
        "witness_score": {"num": str(score.numerator), "den": str(score.denominator)},
        "incumbent_weight": str(incumbent_weight),
        "tree": nodes,
    }
    return {
        "complete": complete,
        "proof": proof,
        "nodes": node_count,
        "witness": witness,
        "score": score,
        "seconds": time.monotonic() - started,
    }


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, required=True)
    parser.add_argument("--N", type=int, required=True)
    parser.add_argument("--max-nodes", type=int, default=2_000_000)
    parser.add_argument("--max-seconds", type=float, default=300.0)
    parser.add_argument("--output", type=str)
    args = parser.parse_args(argv)
    result = solve(args.k, args.N, args.max_nodes, args.max_seconds)
    payload = canonical_json_bytes(result["proof"])
    if args.output:
        with open(args.output, "wb") as handle:
            handle.write(payload)
            handle.write(b"\n")
    summary = {
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
