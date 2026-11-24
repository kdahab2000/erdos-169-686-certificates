# Campaign 5 local checks and continuation

Status: **CHANGES**. Mathematical certificate replay passes; Z/125Z closure and
its positive full-certificate test remain unavailable, and default replay exceeds
12 seconds. No release or external activity occurred.

## Artifacts and claims

The authoritative inventory is `benchmarks/campaign5_results.json`; the full
changed-file list is `benchmarks/c5_changed_files.txt`. The default manifest has
731 entries and the deep manifest retains its original two. The 170 new files
are one 969-row Pell batch, 73 combined square nulls, 24 k=4-only nulls, and 72
prefix witness/proof/prefix files. Prefix endpoints are 36,36,60,60, or 192 rows.
All 563 legacy certificate byte hashes and both original manifest prefixes match
`benchmarks/c5_legacy_bytes.json`. Six duplicate digests predate this campaign;
no new duplicate digest was introduced. The v1 H0 function source text is
unchanged in both verifiers (`benchmarks/c5_v1_unchanged.json`).

Pell replay through both engines took about 0.005 seconds, below 0.5 seconds.
The largest m is 252 bits at N=661. The atlas checks all 198 cells and reconciles
24/0/75. Existing scan rows were checked against fresh divisor decisions,
coverage bounds and representation certificates; the higher-k scans were not
rerun. Their raw source digest is recorded in every atlas row. These scans
remain bounded benchmark evidence.

Prefix production used a 20-second per-row budget. All completed rows replayed
before advancing; witness and content-addressed prefix references also replayed.
g5/g6 reached 60. The producer log records solve times; table rows record solve
and replay nanoseconds. The first g6 run stopped at 55 because the timer included
digest-index setup; the resumed run used proof replay alone for the per-row
replay budget. Every proof replay was under one second; the initially index-inclusive g6(55)
timing was resolved by a direct proof replay in `benchmarks/c5_g6_55_replay.json`. No legacy file changed.

## Commands actually run

- `python3 -B benchmarks/campaign5.py pell`
- `python3 -B benchmarks/campaign5.py squares` (first attempt exposed extra scan
  records without divisor fields; corrected, then passed)
- `python3 -B benchmarks/campaign5.py prefixes` (initial and resumed runs)
- `python3 -B benchmarks/campaign5.py manifests`
- `python3 -B benchmarks/campaign5.py reconcile`
- Bounded direct calls to `prove_orbits`, first three seconds then twenty seconds
  per orbit; final probe used a 30-second overall budget.
- Targeted Pell, cyclic v2 and no-float tests. Initial test failures exposed
  different canonical-string error messages and an invalid synthetic packing;
  corrected before the full suite.
- `python3 -B -m unittest discover -s tests -p 'test_*.py' -v`;
  final result: 77 tests passed in 66.253 seconds (`benchmarks/c5_unittest.log`).
- `node --test tests/python_bridge.test.mjs`: all three checks passed;
  the bridge reran the suite and default replay (`benchmarks/c5_node_bridge.log`).
- `node tests/hash_manifest.mjs`: completed; 734 top-level hash rows recorded
  in `benchmarks/c5_hash_manifest.log`. This enumerates digests; the separate
  legacy integrity tests compare the original bytes and manifest prefixes.
- Both standalone manifests, with return code 0. Timing and context are in
  `benchmarks/c5_timings.json`; replay output is in the corresponding logs.
- `python3 -B submissions/build_oeis.py`, followed by scans for OEIS novelty
  placeholders and fake identifiers; no matches.
- Scanned README, docs, submissions and CITATION for local machine paths;
  no matches.
- Legacy byte rehash and append-only manifest checks in Campaign 5 tests.
- Source comparison of the two v1 H0 functions against HEAD; both identical.
- Git diff whitespace check using the installed Command Line Tools executable;
  no errors. No commit, reset, push or deployment was performed.

The first manifest measurements overlapped a test run (22.79 and 31.79 seconds).
A subsequent default replay, without another task command running, took
**22.13 seconds**, above the required 12-second ceiling. The later deep replay
passed in **30.40 seconds**; its end overlapped the next test-suite start.
These measurements establish replay correctness, not satisfaction of the speed
gate. No trusted hot-path optimization was attempted.

## Trusted verifier changes

v2 is a separate schema/path. Translate a densest residue class mod 5 into H0,
then lift the affine normalization y→ay+c on Z25 to x→a′x+5c on Z125, with
unit a′≡a mod 25. These maps permute the residue classes and leave H0 densest.
Consequently completions may be restricted to fibre sizes at most |F0|.
An overfull fibre has no allowed completion, giving dominance upper=0.
Otherwise the upper bound sums each fibre's remaining slack. Force nodes need
four selected AP points and exclude only the fifth undecided point. Packing
requires disjoint undecided AP parts and forbids excluded points.

New synthetic tests exercise the actual shared-shape node engine in both
independent verifier files, including positive branch/conflict/force/dominance
and selected-point-overlapping packing. Adversarial tests cover forged bounds,
force preconditions, packing overlap/exclusion, malformed trees, coverage,
reference/witness tampering, duplicates and caps. They do **not** constitute a
positive end-to-end replay of a complete 791-orbit certificate. Pell tests cover
coverage, square/duplicate rows, caps, norm, canonical integers and coordinates.

## Continuation checkpoint

The first 16-point fibre (mask 507375) did not close after 20 seconds and 76083
nodes; no completed orbit was persisted. The local progress file has claim
`none`, is not listed in a manifest, and contains no proof of a maximum.
No `c5_z125_max.json` was emitted. Keep 64≤maximum≤80.

Next work: improve branching/pruning before further measurement; complete the
specified sample, estimate total nodes and cold replay, and run all 791 orbits
only if both gates pass. The current producer implements the bounded measurement
and complete-orbit checkpoint stage; full gated certificate production remains
unfinished. Obtain full positive replay in both verifiers. Profile default replay
separately and restore the under-12-second gate without changing legacy bytes or
introducing unreviewed trusted-code rewrites. No optional g3/g4 extension was run.

OEIS allocations are user supplied and were not checked online. No open-problem
status or literature priority was verified externally. Any submission or release
requires user trial and explicit approval; Relay cannot deploy.
