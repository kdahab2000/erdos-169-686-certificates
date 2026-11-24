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

Every certificate below belongs to the [default manifest](certificates/MANIFEST.json) or [deep manifest](certificates/MANIFEST_DEEP.json). The [claim table](benchmarks/campaign4_results.json) reconciles the artifacts and search limitations.

| Claim | Domain | Value | Claim level | Certificate path(s) |
| --- | --- | --- | --- | --- |
| Finite reciprocal maxima | k=3,4; N=1…36; k=5,6; N=1…48 | 168 exact reduced rational rows | certified optimal | `c2_g*_prefix.json`, `c4_g*_prefix.json` in default manifest; [tables](benchmarks/oeis_tables.json) |
| Pure base-five S₅=Σ 1/(1+x), base-five digits of x in {0,1,2,3} | Infinite set, depth-10 quantized enclosure | Exact interval below; width < 2×10⁻⁷ | feasible construction with certified enclosure | [depth 6](certificates/c4_pure5_q_depth6.json), [depth 10](certificates/c4_pure5_q_depth10.json) |
| Unchanged-tail rigidity | Base-five tail above 5ᴸ untouched, L=6,7,8,9 | maximum edit gain Δ=0 | certified optimal within this edit class | [L6](certificates/c3_rigidity_L6.json), [L7](certificates/c3_rigidity_L7.json), [L8](certificates/c3_rigidity_L8.json), [L9](certificates/c4_rigidity_L9.json) |
| Carry-automaton candidate counts a(1…9) | Tail-compatible single additions | 0, 0, 0, 0, 0, 2, 28, 260, 1994 | L=6…9 certified enumeration by rigidity replay; L=1…5 computed, uncertified | [L9 candidates](certificates/c4_rigidity_L9.json); [sequence](submissions/oeis/b_tail_compat_base5.txt) |
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

## Verify with Python alone

No installation or third-party library is required. From the repository root:

```sh
python3 -B verifiers/standalone_verify.py certificates/MANIFEST.json
python3 -B verifiers/standalone_verify.py certificates/MANIFEST_DEEP.json
```

The standalone verifier is a single standard-library file. It recomputes mathematical claims, checks canonical certificate digests and follows content-addressed references. The default tier has 561 entries; the deep tier has two slower prime-power boxes. Measured replay times and the commands actually run are in [CAMPAIGN4_CHECKS](docs/CAMPAIGN4_CHECKS.md). Timing gates depend on the local machine.

## Search status and scope

The general-base carry automaton searched three deterministic greedy digit orders for every B=6…60, including B=55. No candidate passed the lower-bound comparison against the certified S₅ upper endpoint. This was a bounded heuristic search, not an exhaustive classification. Z/125Z and window rigidity remain unresolved. The gated edited-tail schema was not activated because no candidate exceeded the reference threshold.

The claim levels are **feasible**, **certified optimal**, **bounded null box**, and **computed, uncertified**. No infinite problem is resolved here. No literature priority, OEIS acceptance, or external publication is asserted. See the [trap ledger](docs/TRAPS.md) and [Arabic campaign report](docs/CAMPAIGN4_REPORT_AR.md). All artifacts remain local; release requires a user trial and explicit approval.

## Repository map

| Directory | Contents |
| --- | --- |
| `verifiers/` | Strict parsers, laboratory verifiers, standalone replay |
| `certificates/` | Immutable legacy evidence, Campaign 4 certificates, two manifest tiers |
| `solvers/` | Prefix branch-and-bound, digit/carry searches, dual producers, modular sieves |
| `benchmarks/` | Reproducible `campaign4.py` producer phases, timings, unresolved search frontiers |
| `submissions/oeis/` | Offline draft descriptions and b-files regenerated from certificate-backed prefix rows |
| `tests/` | Exact arithmetic, adversarial tampering, parity and independent small-box oracles |
| `docs/` | Proof notes, checks, claim limitations and Arabic summary |

## ملخص عربي

يبحث المختبر في المسألتين #169 و#686 باستخدام حسابات صحيحة وشهادات قابلة لإعادة التحقق محليًا. جداول g₃ وg₄ حتى N=36، وجداول g₅ وg₆ حتى N=48، تتضمن 168 **قيمة مثلى مُثبتة بشهادة**. إنشاء S₅ هو **إنشاء ممكن** بفاصل صحيح دقيق معروض أعلاه وعرض أقل من 2×10⁻⁷، وليس حدًا أعلى للدالة f(5).

تثبت شهادات الصلابة أن أقصى كسب Δ=0 عند إبقاء الذيل دون تعديل للمستويات L=6…9. المتتالية a(1…9) هي 0، 0، 0، 0، 0، 2، 28، 260، 1994؛ ويعيد تحقق شهادة L=9 حساب 1994 مرشحًا. الأعداد للمستويات L=1…5 محسوبة محليًا، غير مُصدَّقة بشهادة مستقلة. لا تعني ملاءمة المرشح للذيل جواز إضافته دون حذف نقاط أخرى.

القيمة المثلى في Z/25Z هي 16. أما Z/125Z فما زالت غير محسومة: يوجد إنشاء ممكن بحجم 64 وحد أعلى 80 مستنتج من شهادة Z/25Z. البحث المتبقي وفرضية صلابة النوافذ **محسوبة محليًا، غير مُصدَّقة**. لا توجد نتيجة مُصدَّقة تتجاوز S₅ في البحث الحالي.

للمسألة #686، عند N=4 وN=25، لا توجد حلول في **صندوق بحث محدود بلا حلول**: k=3 و1≤n≤5,000,000؛ وكذلك k=5…200 و1≤n≤50,000. لا يوجد حد أعلى مفروض على m. يعاد التحقق بالشيفرة أعلاه، مع ملف عميق منفصل للشهادات الأبطأ. هذه النتائج محدودة بمجالاتها، ولا تثبت حل أي مسألة لانهائية.

## Citation

Repository: https://github.com/kdahab2000/erdos-169-686-certificates (this campaign does not publish to it).

```bibtex
@misc{aboeldahab_erdos_certificates,
  author = {Khaled Aboeldahab},
  title = {Erdős Breakthrough Lab: Exact Certificates for Problems 169 and 686},
  year = {2026},
  howpublished = {Local research artifact},
  url = {https://github.com/kdahab2000/erdos-169-686-certificates},
  note = {Campaign 4; bounded computational claims, independently replayable}
}
```

Machine-readable citation metadata: [CITATION.cff](CITATION.cff).
