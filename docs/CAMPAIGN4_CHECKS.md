# Campaign 4 proof and verification notes

This is a local, offline implementation checkpoint. There were no external services, live AI calls, dependency installations, commits or publication operations.

## Exact #686 prime-power exclusion lemma

Write Pₖ(t)=∏ᵢ₌₁ᵏ(t+i), and suppose Pₖ(m)=s²Pₖ(n), n≥1 and m≥n+k. Choose a prime p>k with p∤s. If q=pᵉ is the full p-power dividing n+j, only one factor of Pₖ(n) is divisible by p. The same holds on the m side. Equality of valuations therefore gives an i for which q divides m+i.

Both m+i and n+j are divisible by q, and m+i>n+j because m≥n+k. Thus m+i≥n+j+q, and m+1≥n+j+q−k+1. For k≥2,

```text
Pₖ(m) > (m+1)^k ≥ (n+j+q−k+1)^k,
s²Pₖ(n) < s²(n+k)^k.
```

Consequently `(n+j+q−k+1)^k ≥ s²(n+k)^k` contradicts equality. Each n is checked individually. The sliding maximum only selects the strongest eligible factor in that n's window; it never skips an interval. A smallest-prime-factor table reconstructs full prime powers exactly. Survivors use integer kth roots and exact product bisection over m∈[r−k+1,r−1], restricted to m≥n+k. m is never capped by the n box.

The recorded full-box survivor counts are 671 for s=2 and 882 for s=5, at k=101…200 and n=1…50,000. These counts are operational diagnostics, not certificate inputs. Both verifiers reconstruct them.

## Quantized Kempner enclosure

Q=10⁶⁰ is fixed. Each head summand is rounded outward with integer floor/ceiling. For a top-shell prefix x and t≥1 appended digits, there are dᵗ descendants. Their denominator lies between Bᵗx and Bᵗ⁻¹(Bx+M+s), since s≥1≥M/(B−1). Summing the geometric bounds gives the certified shell terms

```text
LB: B d / ((B-d)(B x+M+s)),
UB: d / ((B-d) x).
```

Each shell term is rounded outward separately. No unquantized common denominator accumulates. The depth-10 width is checked as `ub_num-lb_num < 2*10**53`. The mathematical oracle checks depths 1…5 against rational sums and legacy intervals. Endpoint tampering in either direction is rejected.

The carry automaton tracks all k−1 carries and whether a nonzero difference digit has occurred. A finite positive-difference AP exists exactly when the initial zero-carry state can reach zero carries with that flag true. Leading zero padding is permitted because 0∈D. The rejecting trap is B=4,D={0,1,2},k=4. The tests also compare existing cyclic certificates and small finite oracles.

A correction to the offensive's initial tail-loss assumption: cutting the **entire** tail at 5¹² does not lose less than 10⁻⁵. Summing the length-ell shell bound gives tail mass at least `3*(4/5)^12 > 1/5`. The puncture probe's small exact bound applies only to its specified MSD-prefix cylinder. It does not authorize a full block cutoff or a glued construction.

## Rigidity and cyclic search

Legacy v1 is retained. v2 raises only the approved level/candidate caps. The first unquantized L=9 dual was rejected for excessive rational bit length. The successful producer uses capacities floor(Q/r)/Q and demands ceil(Q/a)/Q: capacity rounding is downward and coverage rounding is upward. Its certificate replays 1,994 independently regenerated candidates. Zero margin proves Δ≤0, without uniqueness.

The Z/25 certificate has 46,861 nodes, replays in 0.08 s and exhaustively branches and uses pairwise-disjoint full cyclic AP deductions; its maximum is 16. Five disjoint Z/25 fibres of Z/125 give an upper bound 80. The Z/125 cardinality witness has size 64. Dense-fibre enumeration found 791 affine orbit representatives, and the bounded residual search saved 810 branches. These are search outputs with `claim: none`, not an optimality certificate. The verifier supports the H0 schema, exact orbit coverage and residual proof trees, but no complete positive Z/125 proof is available to exercise that path end to end. Adversarial missing-orbit coverage is tested in both verifiers.

The window probe processed all 11,529 nonmembers at L=6, using all baseline blockers, including tail points. The greedy allocation left 11,449 deficits; this does not prove linear-program infeasibility. It is research output only. No edited-tail candidate crossed the gate, so `glued_tail.v1` was not implemented.

## Timings and legacy integrity

The pre-change standalone replay passed 471 entries in 9.8923 s. A per-run canonical digest index reduced that to 3.8071 s. No index survives a replay scope; a same-size rewrite test checks freshness between runs, and returned objects cannot mutate the index.

The first integrated replay passed 561 default entries in 8.2265 s and two deep entries in 27.8390 s. Current measured runs are recorded in [c4_timings.json](../benchmarks/c4_timings.json). The default gate is below 10 s; slower prime-power boxes belong only to the deep tier. Timing is machine dependent. The original baseline failed the requested pre-optimization five-second target; the optimized legacy replay met it.

All original 471 certificate files are checked byte-for-byte using [c4_legacy_bytes.json](../benchmarks/c4_legacy_bytes.json). The original manifest entries retain their order and values. The manifest file itself changes only to append new entries. Prefix tables extend contiguously to 36,36,48,48, and offline b-files derive their rows from manifest-backed certificates.

## Local reproduction and checks

Producers are serial, use the standard library and write only inside this worktree. Run from the repository root:

```sh
python3 -B benchmarks/campaign4.py quantized
python3 -B benchmarks/campaign4.py rigidity
python3 -B benchmarks/campaign4.py prefixes
python3 -B benchmarks/campaign4.py sieves
python3 -B benchmarks/campaign4.py searches
python3 -B benchmarks/campaign4.py manifests
python3 -B submissions/build_oeis.py
python3 -B benchmarks/campaign4.py measure
```

`prefixes` resumes after each certified endpoint; search probes preserve unresolved branches. Producer timing logs are in `benchmarks/c4_*.log`. Certificate verification decisions use exact integers and rational arithmetic; elapsed-time measurements are operational floats encoded as strings in JSON.

Actual acceptance commands and their outputs are recorded in `c4_python_checks.log`, `c4_node_checks.log`, `c4_hashes.log`, and `c4_diff_check.log` under `benchmarks/`:

```sh
python3 -B -m unittest discover -s tests
python3 -B -m unittest tests.test_no_float tests.test_parity
python3 -B verifiers/standalone_verify.py certificates/MANIFEST.json
python3 -B verifiers/standalone_verify.py certificates/MANIFEST_DEEP.json
node --test tests/python_bridge.test.mjs
node tests/hash_manifest.mjs
/Library/Developer/CommandLineTools/usr/bin/git diff --check
```

No release readiness is claimed. User trial and explicit approval remain required before release; Relay cannot deploy.

## Final local acceptance checkpoint

The full Python suite passed 69 tests. The targeted Campaign 4 suite passed 13 tests; the no-float/parity suite passed four tests. Node passed all three bridge checks. Independent Node/Python canonical SHA-256 values agree for all 563 manifest entries. `git diff --check` passed. No Python bytecode caches were created. The [changed-file inventory](../benchmarks/c4_changed_files.json) lists the complete local uncommitted scope.

Unresolved research: finish the saved Z/125 residual trees, seek a complete H0 certificate, and improve the greedy window/puncture search. `residual_probe(fibres, checkpoint=previous_result)` resumes the saved masks; a zero-budget round-trip is tested. These open research outcomes do not establish an improvement over S₅. The user trial and release approval have not occurred.
