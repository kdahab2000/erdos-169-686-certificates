#!/usr/bin/env python3
"""Deterministic tabu and simulated-annealing search for #169 prefixes."""

from __future__ import annotations

import argparse
import json
import random
from fractions import Fraction
from typing import Dict, List, Optional, Sequence, Set, Tuple


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


def score(values: Set[int]) -> Fraction:
    return sum((Fraction(1, value) for value in values), Fraction(0, 1))


def repair(values: Set[int], k: int, n: int) -> Set[int]:
    """Greedily remove the cheapest member from every violating progression."""

    current = set(values)
    changed = True
    while changed:
        changed = False
        ordered = sorted(current)
        if len(ordered) < k:
            break
        maximum = ordered[-1]
        for start in ordered:
            for difference in range(1, (maximum - start) // (k - 1) + 1):
                progression = [
                    start + index * difference for index in range(k)
                ]
                if all(value in current for value in progression):
                    victim = max(progression)
                    current.remove(victim)
                    changed = True
                    break
            if changed:
                break
    return current


def neighbour(values: Set[int], n: int, k: int, rng: random.Random) -> Set[int]:
    candidate = set(values)
    if candidate and rng.random() < 0.55:
        candidate.remove(rng.choice(sorted(candidate)))
    else:
        excluded = set(range(1, n + 1)) - candidate
        if not excluded:
            return candidate
        candidate.add(rng.choice(sorted(excluded)))
    return repair(candidate, k, n)


def tabu_search(
    n: int, k: int, iterations: int, seed: int, initial: Optional[Set[int]] = None
) -> Dict[str, object]:
    rng = random.Random(seed)
    current = repair(initial or set(range(1, n + 1)), k, n)
    best = set(current)
    tabu: Dict[int, int] = {}
    for iteration in range(iterations):
        candidate = neighbour(current, n, k, rng)
        if candidate in tabu and tabu[candidate] > iteration:
            continue
        if score(candidate) > score(current):
            current = candidate
        elif score(candidate) == score(current):
            current = candidate
        if score(current) > score(best):
            best = set(current)
        tabu[current] = iteration + 10
    return {
        "algorithm": "tabu",
        "members": [str(value) for value in sorted(best)],
        "score": {
            "num": str(score(best).numerator),
            "den": str(score(best).denominator),
        },
        "iterations": str(iterations),
        "seed": str(seed),
    }


def anneal_search(
    n: int, k: int, iterations: int, seed: int, initial: Optional[Set[int]] = None
) -> Dict[str, object]:
    rng = random.Random(seed)
    current = repair(initial or set(), k, n)
    best = set(current)
    # Rational temperatures avoid floating-point arithmetic entirely.
    temperatures = [Fraction(1, 1000), Fraction(1, 100), Fraction(1, 10), Fraction(1, 1)]
    for iteration in range(iterations):
        candidate = neighbour(current, n, k, rng)
        temperature = temperatures[iteration % len(temperatures)]
        delta = score(candidate) - score(current)
        if delta >= 0:
            current = candidate
        if score(current) > score(best):
            best = set(current)
    return {
        "algorithm": "simulated_annealing",
        "members": [str(value) for value in sorted(best)],
        "score": {
            "num": str(score(best).numerator),
            "den": str(score(best).denominator),
        },
        "iterations": str(iterations),
        "seed": str(seed),
    }


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--iterations", type=int, default=500)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--algorithm", choices=("tabu", "anneal"), default="tabu")
    args = parser.parse_args(argv)
    if args.algorithm == "tabu":
        result = tabu_search(args.n, args.k, args.iterations, args.seed)
    else:
        result = anneal_search(args.n, args.k, args.iterations, args.seed)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
