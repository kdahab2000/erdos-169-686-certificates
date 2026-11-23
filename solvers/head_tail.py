#!/usr/bin/env python3
"""Head/tail audit for #169 digit sets.

Cross-level arithmetic progressions are the main danger.  This module performs
an exhaustive AP audit on a finite prefix.  It is a diagnostic gate only: a
finite-prefix audit does not prove that an infinite digit set is AP-free.
"""

from __future__ import annotations

import argparse
import json
from typing import Iterable, List, Optional, Sequence


def find_ap(values: Iterable[int], k: int) -> Optional[List[int]]:
    ordered = sorted(set(values))
    present = set(ordered)
    if not ordered:
        return None
    maximum = ordered[-1]
    for start in ordered:
        for difference in range(1, maximum - start + 1):
            if start + (k - 1) * difference > maximum:
                break
            progression = [start + index * difference for index in range(k)]
            if all(value in present for value in progression):
                return progression
    return None


def audit_prefix(
    base: int, digits: List[int], s: int, limit: int, k: int
) -> dict:
    if k < 3 or base < 2 or limit < 1:
        raise ValueError("invalid audit parameters")
    values: List[int] = []
    for value in range(1, limit + 1):
        remainder = value
        allowed = True
        while remainder:
            if remainder % base not in digits:
                allowed = False
                break
            remainder //= base
        if allowed:
            values.append(s + value)
    progression = find_ap(values, k)
    return {
        "base": str(base),
        "digits": [str(digit) for digit in digits],
        "s": str(s),
        "limit": str(limit),
        "k": str(k),
        "member_count": str(len(values)),
        "ap_free": progression is None,
        "offending_ap": progression,
    }


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=int, required=True)
    parser.add_argument("--digits", required=True)
    parser.add_argument("--s", type=int, default=1)
    parser.add_argument("--limit", type=int, required=True)
    parser.add_argument("--k", type=int, required=True)
    args = parser.parse_args(argv)
    digits = [int(item) for item in args.digits.split(",")]
    print(json.dumps(audit_prefix(args.base, digits, args.s, args.limit, args.k), sort_keys=True))


if __name__ == "__main__":
    main()
