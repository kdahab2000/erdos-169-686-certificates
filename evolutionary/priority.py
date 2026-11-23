#!/usr/bin/env python3
"""Safe grammar-bounded priority-function evolution.

Programs are tiny immutable AST tuples.  They are interpreted by a bounded
recursive evaluator; ``exec``, ``eval``, compilation, imports, and network
calls are deliberately absent.
"""

from __future__ import annotations

import argparse
import json
import random
from fractions import Fraction
from typing import Any, Dict, List, Sequence, Tuple

Program = Tuple[Any, ...]
MAX_AST_NODES = 40
MAX_DEPTH = 8


def constant(value: int) -> Program:
    return ("const", value)


def variable(index: int) -> Program:
    return ("var", index)


def add(left: Program, right: Program) -> Program:
    return ("add", left, right)


def multiply(left: Program, right: Program) -> Program:
    return ("mul", left, right)


def maximum(left: Program, right: Program) -> Program:
    return ("max", left, right)


def node_count(program: Program) -> int:
    if program[0] in ("const", "var"):
        return 1
    return 1 + node_count(program[1]) + node_count(program[2])


def depth(program: Program) -> int:
    if program[0] in ("const", "var"):
        return 1
    return 1 + max(depth(program[1]), depth(program[2]))


def evaluate(program: Program, variables: Sequence[int]) -> int:
    if node_count(program) > MAX_AST_NODES or depth(program) > MAX_DEPTH:
        raise ValueError("program exceeds AST limits")
    operation = program[0]
    if operation == "const":
        return int(program[1])
    if operation == "var":
        index = int(program[1])
        if index < 0 or index >= len(variables):
            raise ValueError("variable index out of range")
        return variables[index]
    if operation in ("add", "mul", "max"):
        left = evaluate(program[1], variables)
        right = evaluate(program[2], variables)
        if operation == "add":
            return left + right
        if operation == "mul":
            return left * right
        return max(left, right)
    raise ValueError("unknown AST operation")


def contains_ap(values: Sequence[int], k: int) -> bool:
    present = set(values)
    ordered = sorted(present)
    if len(present) < k:
        return False
    maximum = ordered[-1]
    for start in ordered:
        for difference in range(1, maximum - start + 1):
            if start + (k - 1) * difference > maximum:
                break
            if all(start + index * difference in present for index in range(k)):
                return True
    return False


def greedy_members(program: Program, n: int, k: int) -> List[int]:
    priorities = [evaluate(program, [index]) for index in range(n)]
    order = sorted(range(n), key=lambda index: (-priorities[index], index))
    members: List[int] = []
    for index in order:
        candidate = members + [index + 1]
        if not contains_ap(candidate, k):
            members = candidate
    return sorted(members)


def fitness(program: Program, n: int, k: int) -> Fraction:
    members = greedy_members(program, n, k)
    return sum((Fraction(1, member) for member in members), Fraction(0, 1))


def mutate(program: Program, rng: random.Random, n: int) -> Program:
    if node_count(program) >= MAX_AST_NODES:
        return program
    operation = rng.choice(("add", "mul", "max", "replace"))
    if operation == "replace":
        if rng.random() < 0.5:
            return constant(rng.randrange(0, 32))
        return variable(rng.randrange(0, n))
    left = mutate(program[1], rng, n)
    right = mutate(program[2], rng, n)
    if operation == "add":
        return add(left, right)
    if operation == "mul":
        return multiply(left, right)
    return maximum(left, right)


def evolve(
    seeds: Sequence[Program], n: int, k: int, population_size: int, generations: int, seed: int
) -> Dict[str, Any]:
    rng = random.Random(seed)
    population = list(seeds)
    history: List[Dict[str, Any]] = []
    best = min(population, key=lambda program: (-fitness(program, n, k), repr(program)))
    for generation in range(generations):
        ranked = sorted(population, key=lambda program: (-fitness(program, n, k), repr(program)))
        best = ranked[0]
        history.append({
            "generation": str(generation),
            "best_num": str(fitness(best, n, k).numerator),
            "best_den": str(fitness(best, n, k).denominator),
        })
        elite = ranked[: max(1, population_size // 4)]
        population = list(elite)
        while len(population) < population_size:
            parent = elite[rng.randrange(len(elite))]
            child = mutate(parent, rng, n)
            if node_count(child) <= MAX_AST_NODES and depth(child) <= MAX_DEPTH:
                population.append(child)
    return {
        "best_program": serialize(best),
        "best_members": [str(value) for value in greedy_members(best, n, k)],
        "best_fitness": {
            "num": str(fitness(best, n, k).numerator),
            "den": str(fitness(best, n, k).denominator),
        },
        "history": history,
    }


def serialize(program: Program) -> List[Any]:
    if program[0] in ("const", "var"):
        return [program[0], str(program[1])]
    return [program[0], serialize(program[1]), serialize(program[2])]


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args(argv)
    seeds = [constant(31), variable(0), add(variable(0), constant(1))]
    print(json.dumps(evolve(seeds, args.n, args.k, 12, 8, args.seed), sort_keys=True))


if __name__ == "__main__":
    main()
