#!/usr/bin/env python3
"""Complete divisor decision procedure for #686 squares at k=2 and k=4."""

from __future__ import annotations

import argparse
import json
import os
import sys
from math import isqrt
from typing import Dict, List, Optional, Sequence, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from verifiers.common import canonical_json_bytes


def divisor_pairs(value: int) -> List[Tuple[int, int]]:
    result: List[Tuple[int, int]] = []
    for lower in range(1, isqrt(value) + 1):
        if value % lower == 0:
            result.append((lower, value // lower))
    return result


def from_linear(value: int) -> Optional[int]:
    """Invert value=2*n+3 with n>=1."""

    if value < 5 or value % 2 != 1:
        return None
    return (value - 3) // 2


def from_quadratic(value: int) -> Optional[int]:
    """Invert value=n^2+5n+5 with n>=1."""

    if value < 11:
        return None
    root = isqrt(4 * value + 5)
    if root * root != 4 * value + 5 or root < 7 or (root - 5) % 2:
        return None
    return (root - 5) // 2


def solve_square(s: int) -> Dict[str, object]:
    if s < 2:
        raise ValueError("s must be at least 2")
    value = s * s - 1
    witnesses: Dict[str, List[Dict[str, str]]] = {"2": [], "4": []}
    for lower, upper in divisor_pairs(value):
        if lower % 2 != upper % 2:
            continue
        midpoint = (lower + upper) // 2
        if midpoint % s:
            continue
        y = midpoint // s
        x = (upper - lower) // 2
        if x <= y:
            continue
        n2 = from_linear(y)
        m2 = from_linear(x)
        if n2 is not None and m2 is not None and m2 >= n2 + 2:
            witnesses["2"].append({"n": str(n2), "m": str(m2)})
        n4 = from_quadratic(y)
        m4 = from_quadratic(x)
        if n4 is not None and m4 is not None and m4 >= n4 + 4:
            witnesses["4"].append({"n": str(n4), "m": str(m4)})
    for key in witnesses:
        witnesses[key].sort(key=lambda item: (int(item["n"]), int(item["m"])))
    return {
        "s": str(s),
        "N": str(s * s),
        "domain": "n>=1",
        "method": "divisor_complete",
        "k_set": ["2", "4"],
        "witnesses": witnesses,
    }


def null_certificate(decision: Dict[str, object], k: int) -> Optional[Dict[str, object]]:
    witnesses = decision["witnesses"]
    assert isinstance(witnesses, dict)
    if witnesses[str(k)]:
        return None
    return {
        "schema": "erd686.null.v1",
        "s": str(decision["s"]),
        "k_set": [str(k)],
        "method": "divisor_complete",
        "box": None,
        "domain": "n>=1",
    }


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--s-max", type=int, default=100)
    parser.add_argument("--output", type=str)
    args = parser.parse_args(argv)
    decisions = [solve_square(s) for s in range(2, args.s_max + 1)]
    payload = canonical_json_bytes(decisions)
    if args.output:
        with open(args.output, "wb") as handle:
            handle.write(payload)
            handle.write(b"\n")
    unresolved = [
        decision["s"]
        for decision in decisions
        if not decision["witnesses"]["2"] and not decision["witnesses"]["4"]
    ]
    print(json.dumps({"s_max": args.s_max, "unresolved": unresolved}, sort_keys=True))


if __name__ == "__main__":
    main()
