#!/usr/bin/env python3
"""Exact bounded search for certified digit-set lower bounds for #169."""

from __future__ import annotations

import argparse
import itertools
import json
from fractions import Fraction
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


def has_k_ap(values: Tuple[int, ...], k: int) -> bool:
    present = set(values)
    for start in values:
        for difference in range(1, max(values, default=0) - start + 1):
            if all(start + index * difference in present for index in range(k)):
                return True
    return False


def positive_head_values(base: int, digits: List[int], level: int) -> List[int]:
    values: List[int] = []
    if 0 in digits:
        values.append(0)
    nonzero = [digit for digit in digits if digit]
    for length in range(1, level):
        for leading in nonzero:
            for tail in itertools.product(digits, repeat=length - 1):
                suffix = 0
                for index, digit in enumerate(tail):
                    suffix += digit * base ** (length - 2 - index)
                values.append(leading * base ** (length - 1) + suffix)
    return values


def exact_bounds(
    base: int, digits: List[int], s: int, level: int, q: int
) -> Tuple[Fraction, Fraction]:
    head_values = positive_head_values(base, digits, level)
    if len(head_values) > 2_000_000:
        raise ValueError("digit head cap exceeded")
    head = sum((Fraction(q // (s + value), q) for value in head_values), Fraction(0, 1))
    count = len(digits)
    alpha = count - 1 if 0 in digits else count
    constant = Fraction(base - 1, 1) / (
        Fraction((base - 1) * s, base**level) + max(digits)
    )
    ratio = Fraction(count, base)
    tail = constant * (
        Fraction(alpha, 1) * count ** (level - 1) / base**level / (1 - ratio)
    )
    return head, tail


def certificate(
    k: int, base: int, digits: List[int], s: int, level: int, q: int
) -> Dict[str, object]:
    head, tail = exact_bounds(base, digits, s, level, q)
    return {
        "schema": "erd169.digitset.v1",
        "k": str(k),
        "B": str(base),
        "D": [str(digit) for digit in digits],
        "s": str(s),
        "L": str(level),
        "Q": str(q),
        "head_lb": {"num": str(head.numerator), "den": str(head.denominator)},
        "tail_lb": {"num": str(tail.numerator), "den": str(tail.denominator)},
    }


def search(
    k: int,
    base_min: int = 3,
    base_max: int = 12,
    max_digits: int = 5,
    level: int = 4,
    q: int = 1_000_000,
) -> Dict[str, object]:
    candidates: List[Tuple[Fraction, Dict[str, object]]] = []
    for base in range(max(k + 1, base_min), base_max + 1):
        max_digit = (base - 1) // 2
        if max_digit < 1:
            continue
        for size in range(2, min(max_digits, max_digit + 1) + 1):
            for digits in itertools.combinations(range(max_digit + 1), size):
                if has_k_ap(digits, k):
                    continue
                for s in range(1, max(1, base // 8) + 1):
                    cert = certificate(k, base, list(digits), s, level, q)
                    lower = Fraction(
                        int(cert["head_lb"]["num"]), int(cert["head_lb"]["den"])
                    ) + Fraction(
                        int(cert["tail_lb"]["num"]), int(cert["tail_lb"]["den"])
                    )
                    candidates.append((lower, cert))
    if not candidates:
        return {"status": "no_candidate", "certificate": None}
    lower, best = max(candidates, key=lambda item: item[0])
    return {
        "status": "candidate",
        "lower_bound": {"num": str(lower.numerator), "den": str(lower.denominator)},
        "certificate": best,
    }


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--base-max", type=int, default=12)
    parser.add_argument("--max-digits", type=int, default=5)
    parser.add_argument("--level", type=int, default=4)
    parser.add_argument("--q", type=int, default=1_000_000)
    args = parser.parse_args(argv)
    result = search(args.k, base_max=args.base_max, max_digits=args.max_digits, level=args.level, q=args.q)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
