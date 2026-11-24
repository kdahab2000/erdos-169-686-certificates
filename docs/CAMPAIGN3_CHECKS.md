# Campaign 3 local verification and continuation

Status: CHANGES. Unpunctured A(6), A(7), A(8) rigidity is certified.
The complete puncture family and exact cyclic Z/125 cardinality are unresolved.
Nothing was committed, deployed, published or sent. No network, AI, payment,
credential or production action was performed. No agents were started.

## Checks actually run

- Baseline `python3 -B -m unittest discover -s tests -p 'test_*.py' -q`:
  37 passed. Baseline standalone replay: verified=468, failures=0.
- Targeted OEIS tests: 3 passed, including executing all nine standard-library
  programs in subprocesses (tail through L=6, reciprocal sequences through n=12).
- Targeted initial rigidity tests: 7 passed; the real-cutoff regression was
  subsequently added, bringing this class to 8 tests.
- Full `python3 -B -m unittest discover -s tests -p 'test_*.py' -v`:
  48 passed in 22.887 seconds. Log: benchmarks/c3_python_checks.log.
- `python3 -B verifiers/standalone_verify.py certificates/MANIFEST.json`:
  verified=471, failures=0. Log: benchmarks/c3_manifest_check.log.
- `node --test tests/python_bridge.test.mjs`: 3 passed, 0 failed
  (Python compilation, all 48 unit tests, and standalone manifest replay).
  Log: benchmarks/c3_node_checks.log. An additional explicit TAP replay
  also passed all 3 bridge checks. The final suite also regenerates and
  compares the sparse dual arcs against all three saved certificates.
- `node tests/hash_manifest.mjs`: exit 0, 471 digest lines in
  benchmarks/c3_hashes.log. An additional local script matched all 471
  canonical hashes against the manifest, compared its first 468 entries
  with HEAD, and compared all original 468 certificate files byte for byte
  with HEAD. All assertions passed. The Node hash script alone only prints
  hashes; it is not described here as doing that additional comparison.
- `python3 -B solvers/f5_decisive.py --report`: regenerated the bounded
  benchmark, including four exact A(6) subset results, 175 measured puncture
  attempts, and the node-capped cyclic search.
- L9 enumeration plus individual checks completed in under one second;
  the full automaton proof is docs/CAMPAIGN3_AUTOMATON.md.
- OEIS rebuild is byte-identical. All DATA fields are <=260 characters;
  all b-files match certified tables, paired truncation and reduced fractions
  are checked. Novelty and upstream editorial acceptance are unverified.
- `git diff --check`: exit 0. This checks tracked diffs; a separate
  final whitespace check includes new source and document files.

## Unresolved and continuation

1. Implement the complete P(L) puncture pool, with four pairwise-disjoint
   tail-AP exclusion witnesses, and exact 1..3-puncture optimization for L6..L8.
   The current puncture test is a restricted singleton heuristic, not an
   exact null or a positive certificate. Its 3380 case has no tail points
   in the enumerated blocking edges, so it produces zero puncture trials.
2. Complete the cyclic cardinality proof: current exact B&B stopped at 2000
   nodes, giving only 64<=maximum<=100. It does not solve the required maximum.
   Infinite block reciprocal values require separately reviewed enclosures.
3. The exact singleton-cost function is available at all levels, but recorded
   complete costs are for A(6), not all 28+260 larger-level singletons.
4. Upstream YAML schema, OEIS novelty, account limit and historical attribution
   need manual checks. The YAML snippet is explicitly a template, not a
   verified apply-ready patch. Publication requires user trial and explicit
   approval; Relay cannot deploy.

The three dual certificates and tail-count result can be reviewed independently
of the unresolved extensions. Do not restart those proofs. Read
benchmarks/campaign3_f5_decisive.json and docs/CAMPAIGN3_AUTOMATON.md first.

## Changed files

- `benchmarks/c3_A6_exact_subsets.json`
- `benchmarks/c3_hashes.log`
- `benchmarks/c3_manifest_check.log`
- `benchmarks/c3_node_checks.log`
- `benchmarks/c3_python_checks.log`
- `benchmarks/campaign3_f5_decisive.json`
- `benchmarks/head_candidates_L1.json`
- `benchmarks/head_candidates_L2.json`
- `benchmarks/head_candidates_L3.json`
- `benchmarks/head_candidates_L4.json`
- `benchmarks/head_candidates_L5.json`
- `benchmarks/head_candidates_L9.json`
- `certificates/MANIFEST.json`
- `certificates/c3_rigidity_L6.json`
- `certificates/c3_rigidity_L7.json`
- `certificates/c3_rigidity_L8.json`
- `docs/CAMPAIGN3_AUTOMATON.md`
- `docs/CAMPAIGN3_CHECKS.md`
- `docs/CAMPAIGN3_FINAL_REPORT_AR.md`
- `solvers/f5_decisive.py`
- `submissions/PUBLISHING_GUIDE_AR.md`
- `submissions/arxiv_note_draft.md`
- `submissions/build_oeis.py`
- `submissions/erdosproblems_PR_169.md`
- `submissions/oeis/b_g3_denominators.txt`
- `submissions/oeis/b_g3_numerators.txt`
- `submissions/oeis/b_g4_den.txt`
- `submissions/oeis/b_g4_num.txt`
- `submissions/oeis/b_g5_den.txt`
- `submissions/oeis/b_g5_num.txt`
- `submissions/oeis/b_g6_den.txt`
- `submissions/oeis/b_g6_num.txt`
- `submissions/oeis/b_tail_compat_base5.txt`
- `submissions/oeis/batch1_seq1_tail_compat_base5.txt`
- `submissions/oeis/batch1_seq2_g3_numerators.txt`
- `submissions/oeis/batch1_seq3_g3_denominators.txt`
- `submissions/oeis/batch2_g4_den.txt`
- `submissions/oeis/batch2_g4_num.txt`
- `submissions/oeis/batch2_g5_den.txt`
- `submissions/oeis/batch2_g5_num.txt`
- `submissions/oeis/batch2_g6_den.txt`
- `submissions/oeis/batch2_g6_num.txt`
- `tests/test_campaign3_oeis.py`
- `tests/test_rigidity.py`
- `verifiers/standalone_verify.py`
- `verifiers/v169.py`
