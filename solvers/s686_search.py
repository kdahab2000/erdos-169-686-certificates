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


def prime_valuation_factorial(n, p):
    total = 0
    while n:
        n //= p
        total += n
    return total


def binomial_valuation(t, k, p):
    return (prime_valuation_factorial(t+k,p)-prime_valuation_factorial(t,p)
            -prime_valuation_factorial(k,p))


def sieve_data(n_value, k):
    # For p>k, binom(t+k,k) is a polynomial modulo p, of period p.
    primes = [p for p in range(k+1,k+40)
              if all(p % q for q in range(2,isqrt(p)+1))][:2]
    result = []
    for p in primes:
        image = {comb(t+k,k)%p for t in range(p)}
        residues = {r for r in range(p) if n_value*comb(r+k,k)%p in image}
        result.append((p,residues))
    return result


def sweep(n_value, k, n_max, sieves=True):
    m, fm = 1, comb(1+k,k)
    fn = comb(1+k,k)
    filters = sieve_data(n_value,k) if sieves else []
    for n in range(1,n_max+1):
        if all(n % p in residues for p,residues in filters):
            target = n_value*fn
            while m < n+k or fm < target:
                fm = fm*(m+k+1)//(m+1)
                m += 1
            # Legendre valuations are an exact independent necessary test.
            if fm == target and all(
                binomial_valuation(m,k,p) == binomial_valuation(n,k,p)
                + prime_valuation_factorial(n_value,p)-prime_valuation_factorial(n_value-1,p)
                for p in (2,3,5,7)):
                yield n,m
        fn = fn*(n+k+1)//(n+1)


def search(n_value, k_values, n_max=10000):
    if n_value < 2 or n_max < 1:
        raise ValueError("invalid search bounds")
    ks = sorted(set(k_values))
    if not ks or min(ks) < 2 or max(ks) > 100:
        raise ValueError("invalid k values")
    certificates = [representation_certificate(n_value,k,n,m)
                    for k in ks for n,m in sweep(n_value,k,n_max)]
    if certificates:
        return {"status":"found", "certificate":certificates[0],
                "certificates":certificates}
    root = isqrt(n_value)
    certificate = None
    if root*root == n_value and len(ks)*n_max <= 6000000:
        certificate = {"schema":"erd686.null.v1", "s":str(root),
                       "k_set":list(map(str,ks)),"method":"bounded_box",
                       "box":{"k_max":str(max(ks)),"n_max":str(n_max)},"domain":"n>=1"}
    return {"status":"not_found_in_box", "certificate":certificate,
            "certificates":[], "N":str(n_value)}


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--N", type=int, required=True)
    parser.add_argument("--k-min", type=int, default=3)
    parser.add_argument("--k-max", type=int, default=40)
    parser.add_argument("--n-max", type=int, default=10_000)
    parser.add_argument("--skip", action="append", default=[])
    args = parser.parse_args(argv)
    skip = {2, 4} | {int(k) for item in args.skip for k in item.split(",")}
    k_values = [k for k in range(args.k_min, args.k_max + 1) if k not in skip]
    result = search(args.N, k_values, args.n_max)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
