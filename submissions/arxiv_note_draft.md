# Exact local rigidity for four finite edit levels of a base-5 reciprocal construction

Draft for local review, 24 November 2026. Author: Dr. Khaled Aboeldahab.
No literature priority asserted; offline Campaign 5 draft.

Let K_5 be the nonnegative integers with base-5 digits in {0,1,2,3}, and
B=1+K_5. For level L fix the tail B intersect [1+5^L,infinity).
Let A(L) contain the positive integers a<=5^L outside B that have no
five-term AP beginning at a with four other points in this fixed tail.
Allow additions U subset A(L) and removals R subset B intersect [1,5^L].
Only edits whose entire resulting infinite set is 5-AP-free are admissible.
Their gain is Delta=sum_U 1/a - sum_R 1/r.

**Theorem (finite edit families only).** For L=6,7,8,9, max Delta=0.
This is not a determination of the unrestricted f(5), and gives no new
positive lower-bound record. Uniqueness is not claimed.

Each certificate assigns nonnegative reduced rational weights to explicit
APs containing one candidate and four baseline points. Each has a nonempty
removable head intersection. Coverage for a is >=1/a; load at every removable
r is <=1/r. Every admissible repair hits every cited edge for every a in U.
Summing gives sum_U 1/a <= sum_R 1/r, even when extra multi-addition APs
exist. The empty edit attains equality. See docs/CAMPAIGN3_AUTOMATON.md for
the full carry-language completeness argument and exact dual proof.

The L=6,7,8 certificates have 2, 36 and 430 arcs for 2, 28 and 260
candidates. The L=9 certificate has 3857 arcs for 1994 candidates. Both local verifiers recompute A(L); no candidate file is trusted.
The margin is zero. Certificate identifiers and canonical JSON SHA-256:

- `c3_rigidity_L6.json` — SHA-256 `b473355df43960e7f18bd3a03b0f31b53cbc1176cd992f19a208e075301dc5dc`
- `c3_rigidity_L7.json` — SHA-256 `d7da8f7243d06c2f46b1787c5be150de0bb1025eac088a5cb3a345669fd55b31`
- `c3_rigidity_L8.json` — SHA-256 `2a4930196c33091eb3bf3ee27182a0e61f0a3efc7bd765d56da03f65a4a68317`
- `c4_rigidity_L9.json` — SHA-256 `f8d10e33f117e252cc68933d132a4477375a0cf7d254b223344297904623b9d6`

All four A(6) subsets were also solved directly by exact weighted hitting-set
B&B, including the edges containing two additions. Exact costs and witnesses
are in benchmarks/campaign3_f5_decisive.json. This solver output is supporting
computation, not a separate replay-proof certificate. The dual certificates
above are the machine-checkable proof of the stated theorem.

The tail-count sequence through L=9 is 0,0,0,0,0,2,28,260,1994.
L=1..5 use complete per-element scans; L=6..8 match the previous complete
scans. At L=9, aggregate carry enumeration proves completeness; every listed
candidate separately passes tail_compatible, the count is even, and reflection
closure holds. The equivalence proof is in docs/CAMPAIGN3_AUTOMATON.md.
The list and methodology are in benchmarks/head_candidates_L9.json.

Finite reciprocal maxima g_k(n) are existing certified prefix results, with
36,36,60,60 terms respectively for k=3,4,5,6. These are not values of the
infinite f(k). The nine OEIS drafts separate reduced numerators and denominators
with b-files only when they add at least 20 terms beyond DATA. The g_3 greedy values differ from optimum at n=9
(143/72 versus 39/20) and n=24 (6059/2640 versus 45831/20020).
Attribution to Wroblewski remains withheld pending a source check.

## Punctures and cyclic blocks: unresolved

The ranked finite-pool puncture search at L=6 tested 175 singleton repairs
for a=8340 with 1,2,3 tail punctures and greedy head repairs, all with negative
gain. There are no tail points in the 80 single-addition edges for a=3380,
so this pool produces zero puncture trials for it. This is not a complete
puncture pool, an exact puncture optimum, or a global impossibility result.
No four-disjoint-tail witness system or punctured certificate schema is supplied.
L=7,8 punctures and additions outside A(L) remain unexamined here.

The Z/25Z cyclic maximum is exactly 16 (`c4_z25_max.json`). Five disjoint
Z25 fibres give a Z/125Z upper bound of 80, and an AP-free witness has size 64.
Thus 64≤maximum≤80 remains unresolved. The first Campaign 5 16-point-fibre
orbit exceeded 20 seconds at 76083 nodes. No maximum certificate was emitted.
The v2 verifier adds force, dominance and active-set packing; positive tests
exercise a synthetic node engine, not a complete Z125 certificate.

## Reproducibility and release state

Run the stdlib suite, standalone manifest replay, Node bridge, hash script,
and git diff --check listed in the Arabic publishing guide. No dependencies
are required. All 563 legacy certificate files are byte-identical; 170 Campaign 5
certificates are appended to the default manifest. The package remains a local draft. Manual novelty,
account-limit, publication-schema and user trial checks remain before any
explicit publication approval. No material has been submitted.

## Campaign 5 classical Pell theorem and square classification

For every nonsquare N≥2 choose integers u≥2,v≥1 with u²−Nv²=1.
Put U=2u²−1 and V=2uv. Then U is odd, V≥4 is even, and U²−NV²=1.
X=U+NV and Y=U+V are odd and X²−NY²=1−N. Hence
n=(Y−3)/2≥1, m=(X−3)/2 and m−n=(N−1)V/2≥2 give
(m+1)(m+2)=N(n+1)(n+2). Powers of the positive Pell unit tend to infinity,
so squaring those powers produces infinitely many distinct pairs.
This is a classical result, tagged NONSQUARE_PELL_KNOWN. The batch certificate
checks explicit units and product equalities for all 969 nonsquares in [2,1000],
within a 256-bit coordinate cap (largest m: 252 bits at N=661).
The theorem is general; the finite batch does not cover every N≤10000.

For a square N=s², k=2 reduces to (sY−X)(sY+X)=s²−1 with
X=2m+3,Y=2n+3. For k=4 use X=m²+5m+5,Y=n²+5n+5,
since (m+1)…(m+4)=X²−1. Enumerating positive factor pairs of s²−1,
with parity, divisibility, inverse-map and gap checks, is complete over
n≥1,m≥n+k. The atlas s=2…100 has 24 k=2 positives, no k=4 positives,
and 75 roots with neither. All 198 cells are manifest-backed.

For s=4t+2,t≥2, choose n=t−1,m=4t²+4t−1. Then
m+1=4t(t+1), m+2=(2t+1)² and m−n=4t²+3t,
proving the product identity and required gap. The 23 roots 10,14,…,98
are supplemented by s=99,n=1,m=241.
No infinite k=3 exclusion is claimed for s=2 or s=5. The supplied
positive-rank context is not a certified integral-point classification.
Existing higher-k scans are retained as digest-bound benchmark evidence.

Certified prefixes g₃,g₄ reach 36; g₅,g₆ reach 60 (192 values total).
OEIS identifiers A402682/A402683/A402684 are user supplied, not checked online.
The drafts are local, with b-files only when at least 20 extra terms exist.
All legacy certificate bytes remain unchanged. See CAMPAIGN5_CHECKS for
actual validation and unresolved gates. User trial and explicit approval
remain prerequisites to release; Relay cannot deploy.
