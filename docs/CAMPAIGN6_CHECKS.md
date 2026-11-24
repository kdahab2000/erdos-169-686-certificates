# Campaign 6 local checks and continuation

Status: **CHANGES**. The `<10s` standalone manifest replay gate (`7.21s–7.53s`) and the `200`-row `g_k(N)` prefix extension (`k=3,4` through `N=40`; `k=5,6` through `N=60`) both passed. Z/125Z did not pass Gate G1 (`64 ≤ maximum ≤ 80` remains unresolved); no `c6_z125_max.json` certificate was emitted. No release, push, or external submission occurred.

## Artifacts and claims

- Authoritative inventory: `benchmarks/campaign6_results.json`.
- Legacy byte snapshot: `benchmarks/c6_legacy_bytes.json` records raw SHA-256 digests of all `733` pre-existing certificate files plus the ordered C5 prefixes of `MANIFEST.json` (`731`) and `MANIFEST_DEEP.json` (`2`). All `733` legacy files remain byte-for-byte identical.
- New certificates (`24` files): `c6_g{3,4}_{37..40}_{witness,proof,prefix}.json`, appended to `MANIFEST.json` (`755` entries total). `MANIFEST_DEEP.json` remains unchanged (`2` entries).
- Prefix tables: `benchmarks/oeis_tables.json` now contains `200` contiguous exact reduced rational rows (`40, 40, 60, 60` for `k=3,4,5,6`), reconciled against `submissions.build_oeis.certified_tables()`. Each new row was triple-replayed in both `verifiers/standalone_verify.py` (`replay` and `verify_prefix`) and `verifiers/proof_replay.py` / `verifiers/v169.py` before advancing.
- OEIS offline drafts: `submissions/oeis/` regenerated (`13` files). Under `row_count >= endpoint + 20`, `k=3` and `k=4` at `40` rows remain ineligible for `b-files`.
- #686 scope: preserved from Campaign 5 (`969`-row Pell batch over `[2, 1000]`, `198`-cell square atlas over `s=2..100` for `k in {2,4}`, bounded cubic and prime-power null boxes).

## Replay speed optimizations (`<10s` gate)

Profile (`benchmarks/c6_profile.txt`) identified redundant double verification of `erd169.bnb.v1` and `erd169.finite.v1` inside `verify_prefix`, `copy.deepcopy` inside `resolve_digest`, Python `set` operations in `replay()`, double JSON parsing between `digest_run` and `verify_entry`, and per-integer generator checking in `cubic_sieve_hits`.

Implemented without altering legacy certificate bytes or floating-point rules:
1. Run-scoped memoization (`_DIGEST_INDEX` ContextVar) keyed by `("standalone", schema, canonical_sha256)`, populated only after verification succeeds and returning `copy.deepcopy` on hit.
2. Internal read-only `_resolve_readonly` inside `verifiers/standalone_verify.py` while keeping `resolve_digest` returning `copy.deepcopy` for public callers.
3. Single-parse binding in `verify_entry`: reads raw file bytes from disk on every call and reuses the `digest_run` parsed dict only when `(resolved_path, raw_sha256)` matches.
4. Bitmask integer `replay()` with incremental `sel_weight`, `und_weight`, and `incidence[member]` AP detection, preserving check ordering and error strings.
5. Residue-stepped `cubic_sieve_hits` over modulus `17017`, mirrored identically in `verifiers/v686.py`.

## Z/125Z C-measure (`Gate G1`)

`solvers/z125_solver.py` remains unchanged. `solvers/z125_fibre.py` implements an incremental `7525`-bit AP bucket tracker with batch forcing and measured `mask 507375` (`|H_0|=16`) and `mask 48623` (first `|H_0|=13` orbit) under 5-second / 200,000-node budgets (`benchmarks/c6_z125_measure.json`):

| Mask | `|H_0|` | Strategy | Status | Nodes | Elapsed (ns) |
| --- | --- | --- | --- | --- | --- |
| `507375` | 16 | `current` | budget exceeded | 54,486 | 5,000,239,208 |
| `507375` | 16 | `h1_first` | budget exceeded | 111,785 | 5,000,754,459 |
| `507375` | 16 | `ap_interleave` | budget exceeded | 36,084 | 5,000,172,959 |
| `48623` | 13 | `current` | budget exceeded | 43,598 | 5,000,331,041 |
| `48623` | 13 | `h1_first` | budget exceeded | 33,254 | 5,000,176,750 |
| `48623` | 13 | `ap_interleave` | budget exceeded | 30,644 | 5,000,389,709 |

Neither orbit closed within budget (`projected_total_nodes`: `null`, `gate_g1_passed`: `false`). Per the ratified Gate G1 rule (`<= 1,000,000` projected nodes across all `791` orbits), the 98-orbit sample and full run were not executed. Counting `dense_z25_fibres(13)` gives `392,125` masks (`3,125` of size 16, `25,000` of size 15, `100,000` of size 14, `264,000` of size 13), confirming that `erd169.cyclic_max.v2` bounds (`dominance`, `coset`, `fibre`, `packing`) cannot close `791` orbits within the 1M-node limit without a stronger checkable bound. `64 ≤ maximum ≤ 80` stays unresolved.

## Commands actually run and timings

- `python3 -B benchmarks/campaign6.py baseline` — verified `733` legacy hashes.
- `python3 -B benchmarks/campaign6.py z125-full` — confirmed `gate_g1_passed=False`; no certificate emitted.
- `python3 -B benchmarks/campaign6.py prefixes` — generated and triple-replayed `c6_g{3,4}_{37..40}_{witness,proof,prefix}.json`.
- `python3 -B benchmarks/campaign6.py manifests` — appended `24` entries to `MANIFEST.json` (`755` total).
- `python3 -B submissions/build_oeis.py` — regenerated `13` OEIS draft files.
- `python3 -B benchmarks/campaign6.py timings` (`benchmarks/c6_timings.json`):
  - `MANIFEST.json` run 1: `7,464,351,084 ns` (`7.46s`, exit 0)
  - `MANIFEST.json` run 2: `7,207,521,708 ns` (`7.21s`, exit 0)
  - `MANIFEST.json` run 3: `7,533,085,583 ns` (`7.53s`, exit 0)
  - `MANIFEST_DEEP.json`: `29,965,274,000 ns` (`29.97s`, exit 0)
- `python3 -B benchmarks/campaign6.py reconcile` — reconciled `200` prefix rows and `755`/`2` manifest entries.
- Full `unittest` suite, Node bridge, `hash_manifest.mjs`, and `git diff --check` run after final edits (recorded below upon completion).
