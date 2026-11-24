# Exact local rigidity for three finite edits of a base-5 reciprocal construction

Draft for local review, 24 November 2026. Author: Dr. Khaled Aboeldahab.
Novelty: SOURCE_REPORTED_REQUIRES_LIVE_CHECK. No literature priority asserted.

Let K_5 be the nonnegative integers with base-5 digits in {0,1,2,3}, and
B=1+K_5. For level L fix the tail B intersect [1+5^L,infinity).
Let A(L) contain the positive integers a<=5^L outside B that have no
five-term AP beginning at a with four other points in this fixed tail.
Allow additions U subset A(L) and removals R subset B intersect [1,5^L].
Only edits whose entire resulting infinite set is 5-AP-free are admissible.
Their gain is Delta=sum_U 1/a - sum_R 1/r.

**Theorem (finite edit families only).** For L=6,7,8, max Delta=0.
This is not a determination of the unrestricted f(5), and gives no new
positive lower-bound record. Uniqueness is not claimed.

Each certificate assigns nonnegative reduced rational weights to explicit
APs containing one candidate and four baseline points. Each has a nonempty
removable head intersection. Coverage for a is >=1/a; load at every removable
r is <=1/r. Every admissible repair hits every cited edge for every a in U.
Summing gives sum_U 1/a <= sum_R 1/r, even when extra multi-addition APs
exist. The empty edit attains equality. See docs/CAMPAIGN3_AUTOMATON.md for
the full carry-language completeness argument and exact dual proof.

The certificates have respectively 2, 36 and 430 arcs for 2, 28 and 260
candidates. Both local verifiers recompute A(L); no candidate file is trusted.
The margin is zero. Certificate identifiers and canonical JSON SHA-256:

- `c3_rigidity_L6.json` — SHA-256 `b473355df43960e7f18bd3a03b0f31b53cbc1176cd992f19a208e075301dc5dc`
- `c3_rigidity_L7.json` — SHA-256 `d7da8f7243d06c2f46b1787c5be150de0bb1025eac088a5cb3a345669fd55b31`
- `c3_rigidity_L8.json` — SHA-256 `2a4930196c33091eb3bf3ee27182a0e61f0a3efc7bd765d56da03f65a4a68317`

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
30,30,40,40 terms respectively for k=3,4,5,6. These are not values of the
infinite f(k). The nine OEIS drafts separate reduced numerators and denominators
and include full b-files. The g_3 greedy values differ from optimum at n=9
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

There are exactly 7525 distinct nonconstant cyclic 5-AP sets modulo 125:
125*120/2 ordinary sets and 25 order-five cosets. A node-capped cardinality
B&B visited 2000 nodes and did not finish. A cyclic-AP-free 64-digit witness
and the elementary upper bound 100 are recorded. The upper bound follows
from the 25 disjoint order-five cosets, each omitting at least one digit.
The exact maximum is unresolved. No reciprocal ranking or infinite-value
claim is made; depth-two enclosures still exceed the existing rational cap.

## Reproducibility and release state

Run the stdlib suite, standalone manifest replay, Node bridge, hash script,
and git diff --check listed in the Arabic publishing guide. No dependencies
are required. Existing 468 certificates are unchanged and three rigidity
certificates are appended. The package remains a local draft. Manual novelty,
account-limit, publication-schema and user trial checks remain before any
explicit publication approval. No material has been submitted.
