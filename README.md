# Erdős Breakthrough Lab

**Dr. Khaled Aboeldahab** · Computational mathematics and independently replayable certificates

A local research laboratory for finite optimization, infinite arithmetic-progression-free constructions, and exact searches related to Erdős problems [#169](https://www.erdosproblems.com/169) and [#686](https://www.erdosproblems.com/686). Links identify the problems; their current external status has not been checked in this offline campaign.

## Problems and notation

For #169, study the supremum **f(k)** of the reciprocal sum over positive-integer sets containing no nonconstant k-term arithmetic progression. The finite quantity **gₖ(N)** maximizes that sum inside {1,…,N}. A finite optimum does not settle f(k).

For #686, search the exact equation

```text
(m+1)⋯(m+k) = N (n+1)⋯(n+k),    n ≥ 1, m ≥ n+k.
```

Here N=s² in the square searches. The cubic identity uses x=m+2 and y=n+2: x³−x=s²(y³−y). Finite null boxes make no assertion outside their stated domains.

## Certified results

Every certificate below belongs to the [default manifest](certificates/MANIFEST.json) or [deep manifest](certificates/MANIFEST_DEEP.json). The [claim table](benchmarks/campaign6_results.json) reconciles the Campaign 6 artifacts and search limitations (see [Campaign 5 ledger](benchmarks/campaign5_results.json) for earlier #686 provenance).

| Claim | Domain | Value | Claim level | Certificate path(s) |
| --- | --- | --- | --- | --- |
| Finite reciprocal maxima | k=3,4; N=1…40; k=5,6; N=1…60 | 200 exact reduced rational rows | certified optimal | `c2_g*_prefix.json`, `c4_g*_prefix.json`, `c5_g*_prefix.json`, `c6_g*_prefix.json` in default manifest; [tables](benchmarks/oeis_tables.json) |
| Pure base-five S₅=Σ 1/(1+x), base-five digits of x in {0,1,2,3} | Infinite set, depth-10 quantized enclosure | Exact interval below; width < 2×10⁻⁷ | feasible construction with certified enclosure | [depth 6](certificates/c4_pure5_q_depth6.json), [depth 10](certificates/c4_pure5_q_depth10.json) |
| Unchanged-tail rigidity | Base-five tail above 5ᴸ untouched, L=6,7,8,9 | maximum edit gain Δ=0 | certified optimal within this edit class | [L6](certificates/c3_rigidity_L6.json), [L7](certificates/c3_rigidity_L7.json), [L8](certificates/c3_rigidity_L8.json), [L9](certificates/c4_rigidity_L9.json) |
| Carry-automaton candidate counts a(1…9) | Tail-compatible single additions | 0, 0, 0, 0, 0, 2, 28, 260, 1994 | L=6…9 certified enumeration by rigidity replay; L=1…5 computed, uncertified | [L9 candidates](certificates/c4_rigidity_L9.json); [sequence](submissions/oeis/batch1_seq1_tail_compat_base5.txt) |
| Cyclic five-term AP-free maximum | Z/25Z | 16 | certified optimal | [Z25 proof](certificates/c4_z25_max.json) |
| Cyclic five-term AP-free search | Z/125Z | 64 ≤ maximum ≤ 80; unresolved | 64 feasible; 80 certified upper bound from Z25; search closure uncertified | [64-digit witness](certificates/c2_block_search125.json), [Z25 proof](certificates/c4_z25_max.json), [frontier](benchmarks/c4_h0_residual.json) |
| Cubic #686 sweep | N=4,25; k=3; 1≤n≤5,000,000; m unbounded | no solutions | bounded null box | [N4](certificates/c4_null_s2_k3_5m.json), [N25](certificates/c4_null_s5_k3_5m.json) |
| Higher-k #686 sweep | N=4,25; k=5…200; 1≤n≤50,000; m unbounded | no solutions | bounded null box | default `c2_null_s{2,5}_k5_100.json`; deep [N4 extension](certificates/c4_null_s2_k101_200_50k.json), [N25 extension](certificates/c4_null_s5_k101_200_50k.json) |

The exact S₅ interval is

```text
[7872304791376599245143565191968392186045201865878690256808179,
 7872304977805305362976739131243867446117686946054980955786331] / 10^60
```

Floor-only decimal displays of its endpoints are `7.872304791376` and `7.872304977805`. Each displayed endpoint denotes its floor plus an error in [0,10⁻¹²); use the integer interval above for all comparisons. This is an enclosure of the pure construction, not an upper bound on f(5).

The L=9 rigidity proof has zero margin and does not establish uniqueness. Tail compatibility alone does not authorize adding a point. Puncturing the tail changes the theorem's hypotheses.

## Campaign 5: exact domains and remaining closure

Campaign 5 adds 170 certificates while preserving all 563 legacy files byte for byte.
The [Pell batch](certificates/c5_686_pell_batch_2_1000.json) verifies 969 nonsquare
values of N in [2,1000] at k=2; the largest m is 252 bits (N=661).
This is a certificate of the classical Pell construction, with no novelty claim.
The theorem applies to every nonsquare N≥2: powers of a nontrivial Pell unit
produce infinitely many distinct admissible pairs. The finite batch illustrates
that theorem; it is not exhaustive computational coverage through N=10000.

The [square atlas](benchmarks/c5_square_atlas.json) covers all 99 roots s=2…100
(N=s²≤10000), over the infinite domain n≥1, m≥n+k, for k∈{2,4}.
There are 24 k=2 positives, zero k=4 positives, and 75 roots with neither.
All 198 cells reference manifest-backed certificates. For s=4t+2, t≥2,
n=t−1 and m=4t²+4t−1 give an infinite family; s=99 has the separate pair
(n,m)=(1,241). Higher-k scans are benchmark evidence only. In particular,
k=3 for N=4 and N=25 remains open outside the certified finite boxes;
positive-rank curves do not imply an integral nonexistence result.

Both g₅ and g₆ now have certified contiguous prefixes through N=60.
OEIS drafts use the user-supplied A402682/A402683/A402684 allocations and
emit b-files only with at least 20 extra terms beyond DATA. No online
editorial status was checked or submission made.

Z/125Z remains at 64≤maximum≤80. The v2 verifier adds forced exclusions,
densest-fibre dominance and active-set packing while retaining v1 unchanged.
The first measured 16-point fibre exceeded 20 seconds at 76083 nodes without
closing. The measurement gate was not met; no maximum certificate was emitted.
See [measurements](benchmarks/c5_z125_measure.json) and the local continuation
checkpoint. Campaign 5 therefore remains **CHANGES**, pending theorem closure
and any unresolved verification gates recorded in the checks document.

## Campaign 6: `<10s` replay, 200-row table, and Z/125Z Gate G1

Campaign 6 appends 24 new prefix certificates (`c6_g{3,4}_{37..40}_{witness,proof,prefix}.json`) while preserving all 733 legacy certificate files byte for byte (`benchmarks/c6_legacy_bytes.json`). Contiguous certified prefixes now cover `N=1…40` for `g₃` and `g₄` and `N=1…60` for `g₅` and `g₆` (**200 exact reduced rational rows**), with all 13 offline OEIS draft files regenerated under the `≥ 20` extra-term `b-file` boundary. Finite `g_k(N)` optima remain distinct from the open infinite `f(k)` problem.

Standalone manifest replay (`verifiers/standalone_verify.py`) was optimized via run-scoped memoization, path-bound single JSON parsing, read-only internal digest lookup, bitmask `replay()`, and residue-stepped `cubic_sieve_hits` (mirrored in `verifiers/v686.py`). Across three fresh uncontended runs on the 755-entry default manifest, replay completed in **7.21–7.53 seconds** (all `< 10s`), and the 2-entry deep manifest passed in **29.97 seconds**.

For Z/125Z, `solvers/z125_fibre.py` (`solvers/z125_solver.py` unchanged) measured `mask 507375` (`|H₀|=16`) and `mask 48623` (first `|H₀|=13`) under `current`, `h1_first`, and `ap_interleave` (`benchmarks/c6_z125_measure.json`). All six runs exceeded the 5-second budget without closing (`25k–112k` nodes), leaving `projected_total_nodes: null` and **Gate G1 (`≤ 1,000,000` nodes across 791 orbits) not passed**. No `c6_z125_max.json` certificate was emitted; Z/125Z stays at `64 ≤ maximum ≤ 80`. The #686 969-row Pell batch and 198-cell square atlas (`s=2…100`, `k∈{2,4}`) remain intact and manifest-backed. See [CAMPAIGN6_CHECKS](docs/CAMPAIGN6_CHECKS.md) and [Arabic Campaign 6 report](docs/CAMPAIGN6_REPORT_AR.md).

## Verify with Python alone

No installation or third-party library is required. From the repository root:

```sh
python3 -B verifiers/standalone_verify.py certificates/MANIFEST.json
python3 -B verifiers/standalone_verify.py certificates/MANIFEST_DEEP.json
```

The standalone verifier is a single standard-library file. It recomputes mathematical claims, checks canonical certificate digests and follows content-addressed references. The default tier has 755 entries; the deep tier has two slower prime-power boxes. Measured replay times and the commands actually run are in [CAMPAIGN6_CHECKS](docs/CAMPAIGN6_CHECKS.md). Timing gates depend on the local machine.

## Search status and scope

The general-base carry automaton searched three deterministic greedy digit orders for every B=6…60, including B=55. No candidate passed the lower-bound comparison against the certified S₅ upper endpoint. This was a bounded heuristic search, not an exhaustive classification. Z/125Z and window rigidity remain unresolved. The gated edited-tail schema was not activated because no candidate exceeded the reference threshold.

The claim levels are **feasible**, **certified optimal**, **bounded null box**, and **computed, uncertified**. No infinite problem is resolved here. No literature priority, OEIS acceptance, or external publication is asserted. See the [trap ledger](docs/TRAPS.md) and [Arabic campaign report](docs/CAMPAIGN5_REPORT_AR.md). All artifacts remain local; release requires a user trial and explicit approval.

## Repository map

| Directory | Contents |
| --- | --- |
| `verifiers/` | Strict parsers, laboratory verifiers, standalone replay |
| `certificates/` | Immutable legacy evidence, Campaign 5 & 6 additions, two manifest tiers |
| `solvers/` | Prefix branch-and-bound, digit/carry searches, dual producers, modular sieves |
| `benchmarks/` | Reproducible `campaign5.py`/`campaign6.py` producer phases, timings, unresolved search frontiers |
| `submissions/oeis/` | Offline draft descriptions and b-files regenerated from certificate-backed prefix rows |
| `tests/` | Exact arithmetic, adversarial tampering, parity and independent small-box oracles |
| `docs/` | Proof notes, checks, claim limitations and Arabic summary |

## ملخص عربي

يبحث المختبر في المسألتين #169 و#686 باستخدام حسابات صحيحة وشهادات قابلة لإعادة التحقق محليًا. جداول g₃ وg₄ حتى N=40، وجداول g₅ وg₆ حتى N=60، تتضمن 200 **قيمة مثلى مُثبتة بشهادة**. إنشاء S₅ هو **إنشاء ممكن** بفاصل صحيح دقيق معروض أعلاه وعرض أقل من 2×10⁻⁷، وليس حدًا أعلى للدالة f(5).

تثبت شهادات الصلابة أن أقصى كسب Δ=0 عند إبقاء الذيل دون تعديل للمستويات L=6…9. المتتالية a(1…9) هي 0، 0، 0، 0، 0، 2، 28، 260، 1994؛ ويعيد تحقق شهادة L=9 حساب 1994 مرشحًا. الأعداد للمستويات L=1…5 محسوبة محليًا، غير مُصدَّقة بشهادة مستقلة. لا تعني ملاءمة المرشح للذيل جواز إضافته دون حذف نقاط أخرى.

القيمة المثلى في Z/25Z هي 16. أما Z/125Z فما زالت غير محسومة: يوجد إنشاء ممكن بحجم 64 وحد أعلى 80 مستنتج من شهادة Z/25Z. البحث المتبقي وفرضية صلابة النوافذ **محسوبة محليًا، غير مُصدَّقة**. لا توجد نتيجة مُصدَّقة تتجاوز S₅ في البحث الحالي.

للمسألة #686، عند N=4 وN=25، لا توجد حلول في **صندوق بحث محدود بلا حلول**: k=3 و1≤n≤5,000,000؛ وكذلك k=5…200 و1≤n≤50,000. لا يوجد حد أعلى مفروض على m. يعاد التحقق بالشيفرة أعلاه، مع ملف عميق منفصل للشهادات الأبطأ. هذه النتائج محدودة بمجالاتها، ولا تثبت حل أي مسألة لانهائية.

نتائج الحملة السادسة: أُضيفت 24 شهادة لتمديد g₃ وg₄ إلى N=40 (بإجمالي 200 صف في الجداول) مع الحفاظ على بايتات الشهادات السابقة وعددها 733، ليصل عدد مدخلات القائمة الافتراضية إلى 755 مدخلًا. انخفض زمن إعادة التحقق القياسي إلى 7.21–7.53 ثانية (أقل من بوابة 10 ثوانٍ). وفي Z/125Z، لم تجتز قياسات `solvers/z125_fibre.py` بوابة G1 (أقصى من 25 ألف–112 ألف عقدة دون إغلاق خلال 5 ثوانٍ)، فلم تُصدر شهادة قصوى ويبقى الحد بين 64 و80، مع الاحتفاظ بدفعة بيل (969 عددًا غير مربع) وأطلس المربعات (198 خلية) من الحملة الخامسة.

## Citation

Repository: https://github.com/kdahab2000/erdos-169-686-certificates (this campaign does not publish to it).

```bibtex
@misc{aboeldahab_erdos_certificates,
  author = {Khaled Aboeldahab},
  title = {Erdős Breakthrough Lab: Exact Certificates for Problems 169 and 686},
  year = {2026},
  howpublished = {Local research artifact},
  url = {https://github.com/kdahab2000/erdos-169-686-certificates},
  note = {Campaign 6; exact domain-limited computational claims, independently replayable}
}
```

Machine-readable citation metadata: [CITATION.cff](CITATION.cff).
