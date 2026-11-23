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


def cyclic_edges(base, p=5):
    """Distinct nonconstant cyclic p-progressions, including repeated residues."""
    return sorted({tuple(sorted({(a+j*w)%base for j in range(p)}))
                   for a in range(base) for w in range(1,base)})


def cyclic_maximum_25():
    """Exact maximum-cardinality search with 0 required (translation invariant)."""
    masks = [sum(1<<j for j in edge) for edge in cyclic_edges(25)]
    incidence = [[mask for mask in masks if mask>>j&1] for j in range(25)]
    best = 0
    best_mask = 0
    nodes = 0
    def visit(selected, undecided):
        nonlocal best, best_mask, nodes
        nodes += 1
        if selected.bit_count()+undecided.bit_count() <= best:
            return
        if not undecided:
            best, best_mask = selected.bit_count(), selected
            return
        bit = undecided & -undecided
        remaining = undecided ^ bit
        j = bit.bit_length()-1
        candidate = selected | bit
        if not any(candidate & mask == mask for mask in incidence[j]):
            visit(candidate, remaining)
        visit(selected, remaining)
    visit(1, ((1<<25)-1)^1)
    return {"maximum":str(best), "digits":[str(j) for j in range(25) if best_mask>>j&1], "nodes":str(nodes)}


def head_edges(a, s, L, digits):
    from verifiers.v169 import padded_member
    edges = set()
    cutoff = s+5**L
    for i in range(5):
        for d in range(1,cutoff-1):
            start = a-i*d
            terms = tuple(start+j*d for j in range(5))
            if start > 0 and all(x == a or padded_member(x-s,digits) for x in terms):
                edges.add(terms)
    return sorted(edges)


def coupled_search(candidates, L=6, s=1, seed=1):
    """Measured finite candidate search; no global/local optimality claim."""
    from fractions import Fraction
    from verifiers.v169 import padded_member, tail_compatible
    from evolutionary.local_search import head_delta_move
    checked, compatible, trials = [], [], []
    for a in candidates:
        if padded_member(a-s,[0,1,2,3]):
            continue
        checked.append(a)
        if not tail_compatible(a,s,L,[0,1,2,3]):
            continue
        compatible.append(a)
        edges = head_edges(a,s,L,[0,1,2,3])
        # This bounded move adds one element and removes a hitting set.
        # It does not establish rigidity under coupled multiple additions.
        removed = head_delta_move({a},edges,seed,head_limit=s+5**L)
        if removed is None:
            continue
        delta = Fraction(1,a)-sum((Fraction(1,x) for x in removed),Fraction())
        trials.append({"added":[str(a)],"removed":list(map(str,sorted(removed))),
                       "delta_num":str(delta.numerator),"delta_den":str(delta.denominator),
                       "internal_or_cross_edges":str(len(edges))})
    return {"L":str(L), "checked":list(map(str,checked)),
            "tail_compatible":list(map(str,compatible)), "trials":trials,
            "scope":"explicit candidates only; no rigidity claim"}


def scan_tail_candidates(L, max_seconds=30):
    import time
    from verifiers.v169 import padded_member, tail_compatible
    if not 1 <= L <= 8:
        raise ValueError('candidate scan level cap')
    started = time.monotonic_ns()
    compatible = []
    last = 0
    for a in range(1,5**L+1):
        if time.monotonic_ns()-started > max_seconds*1000000000:
            break
        last = a
        if not padded_member(a-1,[0,1,2,3]) and tail_compatible(a,1,L,[0,1,2,3]):
            compatible.append(str(a))
    return {'L':str(L), 's':'1', 'scanned_through':str(last), 'complete':last == 5**L,
            'tail_compatible':compatible,'elapsed_ns':str(time.monotonic_ns()-started)}


def cyclic_weighted_25():
    """Exact maximum of sum(1/(1+d)); this is a finite surrogate, not f(5)."""
    from math import lcm
    from fractions import Fraction
    common = 1
    for n in range(1,26):
        common = lcm(common,n)
    weights = [common//(j+1) for j in range(25)]
    edges = cyclic_edges(25)
    masks = [sum(1<<j for j in edge) for edge in edges]
    incidence = [[mask for mask in masks if mask>>j&1] for j in range(25)]
    best = -1
    best_mask = 0
    nodes = 0
    def weight(mask):
        return sum(weights[j] for j in range(25) if mask>>j&1)
    def visit(selected,undecided,current):
        nonlocal best,best_mask,nodes
        nodes+=1
        if current+weight(undecided) <= best:
            return
        if not undecided:
            best,best_mask=current,selected
            return
        bit=undecided & -undecided
        rest=undecided^bit
        j=bit.bit_length()-1
        candidate=selected|bit
        if not any(candidate&mask==mask for mask in incidence[j]):
            visit(candidate,rest,current+weights[j])
        visit(selected,rest,current)
    visit(1,((1<<25)-1)^1,weights[0])
    value=Fraction(best,common)
    return {'digits':[str(j) for j in range(25) if best_mask>>j&1],
            'score':{'num':str(value.numerator),'den':str(value.denominator)},
            'nodes':str(nodes),'objective':'finite reciprocal sum; not infinite optimum'}


def coupled_subset_trials(candidates, L=6, seed=1, iterations=40):
    """Seeded multi-addition trials with all new APs and bounded head removals."""
    import random
    from fractions import Fraction
    from verifiers.v169 import padded_member
    from evolutionary.local_search import head_delta_move
    if len(candidates) > 8 or L > 7:
        raise ValueError('bounded coupled-trial cap')
    cutoff = 1+5**L
    precomputed = {a:head_edges(a,1,L,[0,1,2,3]) for a in candidates}
    rng=random.Random(seed)
    best=None
    for iteration in range(iterations):
        added={a for a in candidates if rng.randrange(2)}
        if not added:
            continue
        edges={e for a in added for e in precomputed[a]}
        def member(x):
            return x in added or padded_member(x-1,[0,1,2,3])
        # Every AP missed by the single-addition audits contains two additions.
        for a in added:
            for b in added:
                if a>=b:
                    continue
                for i in range(4):
                    for j in range(i+1,5):
                        if (b-a) % (j-i):
                            continue
                        d=(b-a)//(j-i)
                        start=a-i*d
                        terms=tuple(start+t*d for t in range(5))
                        if start>0 and all(member(x) for x in terms):
                            edges.add(terms)
        removed=head_delta_move(added,sorted(edges),seed+iteration,head_limit=cutoff)
        if removed is None:
            continue
        delta=sum((Fraction(1,a) for a in added),Fraction())-sum((Fraction(1,x) for x in removed),Fraction())
        if best is None or delta>best[0]:
            best=(delta,added,removed)
    if best is None:
        return {'status':'no feasible repair','L':str(L)}
    delta,added,removed=best
    return {'L':str(L),'seed':str(seed),'iterations':str(iterations),
            'candidates':list(map(str,candidates)), 'added':list(map(str,sorted(added))),
            'removed':list(map(str,sorted(removed))), 'delta_num':str(delta.numerator),
            'delta_den':str(delta.denominator), 'scope':'seeded finite trials; no optimality/rigidity claim'}


def cyclic_125_search(iterations=60, seed=1):
    """Seeded greedy cyclic-independent sets ranked by exact enclosure lower bound."""
    import random
    from fractions import Fraction
    from verifiers.v169 import block_enclosure
    edges=[set(edge) for edge in cyclic_edges(125)]
    incidence=[[edge for edge in edges if j in edge] for j in range(125)]
    rng=random.Random(seed)
    best=None
    for iteration in range(iterations):
        order=list(range(1,125))
        if iteration:
            rng.shuffle(order)
        chosen={0}
        for j in order:
            candidate=chosen|{j}
            if not any(edge <= candidate for edge in incidence[j]):
                chosen.add(j)
        digits=sorted(chosen)
        lb,ub=block_enclosure(125,digits,1,1)
        if best is None or lb>best[0]:
            best=(lb,ub,digits)
    lb,ub,digits=best
    return {'seed':str(seed),'iterations':str(iterations),'digits':list(map(str,digits)),
            'lb':{'num':str(lb.numerator),'den':str(lb.denominator)},
            'ub':{'num':str(ub.numerator),'den':str(ub.denominator)},
            'objective':'exact enclosure lower bound at depth 1; heuristic search'}
