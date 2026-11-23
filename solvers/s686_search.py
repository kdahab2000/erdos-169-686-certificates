#!/usr/bin/env python3
"""Bounded exact search for #686 representations using binomial equality."""

from __future__ import annotations

import argparse
import json
from math import comb, isqrt
from typing import Dict, Iterable, List, Optional, Sequence


def _m_for_n(n_value: int, k: int, n: int) -> Optional[int]:
    target = n_value * comb(n + k, k)
    minimum = n + k
    if comb(minimum + k, k) > target:
        return None
    low = minimum
    high = max(low + 1, 2)
    while comb(high + k, k) < target:
        low = high
        high *= 2
    while low <= high:
        middle = (low + high) // 2
        value = comb(middle + k, k)
        if value < target:
            low = middle + 1
        elif value > target:
            high = middle - 1
        else:
            return middle
    return None


def representation_certificate(n_value: int, k: int, n: int, m: int) -> Dict[str, str]:
    return {
        "schema": "erd686.rep.v1",
        "N": str(n_value),
        "k": str(k),
        "n": str(n),
        "m": str(m),
    }


def search(
    n_value: int,
    k_values: Iterable[int],
    n_max: int = 10_000,
) -> Dict[str, object]:
    if n_value < 2:
        raise ValueError("N must be at least 2")
    ordered_k = sorted(set(k_values))
    for k in ordered_k:
        if k < 2:
            raise ValueError("k must be at least 2")
        for n in range(1, n_max + 1):
            m = _m_for_n(n_value, k, n)
            if m is not None:
                return {
                    "status": "found",
                    "certificate": representation_certificate(n_value, k, n, m),
                }
    root = isqrt(n_value)
    square = root * root == n_value
    return {
        "status": "not_found_in_box",
        "certificate": {
            "schema": "erd686.null.v1",
            "s": str(root if square else n_value),
            "k_set": [str(k) for k in ordered_k],
            "method": "bounded_box",
            "box": {"k_max": str(max(ordered_k)), "n_max": str(n_max)},
            "domain": "n>=1",
        },
    }


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--N", type=int, required=True)
    parser.add_argument("--k-min", type=int, default=3)
    parser.add_argument("--k-max", type=int, default=40)
    parser.add_argument("--n-max", type=int, default=10_000)
    parser.add_argument("--skip", action="append", default=[])
    args = parser.parse_args(argv)
    skip = {2, 4}
    k_values = [k for k in range(args.k_min, args.k_max + 1) if k not in skip]
    result = search(args.N, k_values, args.n_max)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
