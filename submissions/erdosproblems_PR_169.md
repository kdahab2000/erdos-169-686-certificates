# Offline publication drafts — not submitted

**schema unverified — no local `data/problems.yaml`.**
Novelty: SOURCE_REPORTED_REQUIRES_LIVE_CHECK. The problem-page contents,
repository layout and YAML fields were not inspected remotely. The following
is a proposed text replacement to map onto the verified upstream schema;
it is not an apply-ready patch and invents no actual upstream field names.

## Proposed data/problems.yaml patch text

```diff
--- a/data/problems.yaml
+++ b/data/problems.yaml
@@ <locate problem 169 and its verified computational-results field> @@
+<verified field>: |
+  Finite edit result for the translated base-5 digit construction:
+  with fixed tail from 1+5^L, additions restricted to all tail-compatible
+  head points A(L), and removals restricted to baseline head points,
+  the maximum reciprocal gain is zero for L=6,7,8.
+  Candidate counts are 2,28,260. This does not settle unrestricted f(5).
+  Exact rational shared-capacity dual certificates are available for review.
```

Replace both placeholders only after examining the actual upstream file.
No repository URL or public artifact URL is fabricated.

## Forum draft for #169

We have local, independently replayable exact rational certificates proving
max Delta=0 for three finite head-edit families of B=1+K_5. At L=6,7,8,
all 2,28,260 tail-compatible additions are covered, simultaneously over every
subset, with arbitrary baseline head removals. The proof uses AP hitting
constraints and shared reciprocal capacity. This is not a new positive
lower bound for f(5); punctured-tail and unrestricted variants remain open.
A complete carry-automaton argument gives the tail-count sequence
0,0,0,0,0,2,28,260,1994 through L=9. Finite prefix optima g_k(n) and their
integer numerator/denominator tables are prepared separately. No novelty
claim is made before a literature check.

Certificate names and canonical SHA-256:

- `c3_rigidity_L6.json` — SHA-256 `b473355df43960e7f18bd3a03b0f31b53cbc1176cd992f19a208e075301dc5dc`
- `c3_rigidity_L7.json` — SHA-256 `d7da8f7243d06c2f46b1787c5be150de0bb1025eac088a5cb3a345669fd55b31`
- `c3_rigidity_L8.json` — SHA-256 `2a4930196c33091eb3bf3ee27182a0e61f0a3efc7bd765d56da03f65a4a68317`

## Separate forum draft for #686

These are reproducible controls and finite searches, not a resolution of
an infinite nonexistence claim. The certified relation is comb(m+k,k) = N*comb(n+k,k),
with n>=1, k>=2 and m>=n+k. Controls: N=9,k=3,n=11,m=25; N=16,k=3,n=4,m=13.
For N=4900, witnesses include k=2,n=16,m=1223 and k=3,n=1,m=47.
All are feasibility witnesses, without a novelty assertion.
For N=4 and N=25, the bounded-box null certificates cover k=3,n<=500000,
and separately 5<=k<=100,n<=50000. They do not rule out larger n or
unexamined k. The root parameter is s=2 or 5 respectively, not N itself.

Control and bounded-null certificate identifiers:

- `initial_686_n9.json` — SHA-256 `0fdd124387d7fa16cad824c9637b57695b5e928ddbde9c76033de877808610dc`
- `initial_686_n16.json` — SHA-256 `2c917d3915dc372a402fc23ff50566ba12def86980b1ce46b5177333b5141303`
- `c2_square_s70_k2_n16.json` — SHA-256 `b15c06dc3dfb1a189710d43c1f44c6feba5bcda619bf726b1491cde11d5418e5`
- `c2_square_s70_k3_n1.json` — SHA-256 `dc52dd13776c412a311ee1023801f0f8f61e363447c5062b6cda4cb0764aa59e`
- `c2_null_s2_k3.json` — SHA-256 `4cac6aec3f4310bb5af368f0cbee99ee2a1291cfe5e67d4d910e2e6875bce8ab`
- `c2_null_s5_k3.json` — SHA-256 `8ed3dcf7e52f56993d0198f3f2ed612d9ba7505a369ab70916f3cd596347ae0c`
- `c2_null_s2_k5_100.json` — SHA-256 `8586d438fc41c8a58c5a05e9168f639574a7cb07df8bcddb7556d1aff6b23e27`
- `c2_null_s5_k5_100.json` — SHA-256 `5c536dc16e6242c196c16d6b3fda564921b09d2a88e317bfcb2592b36c8ea960`

Before posting, the user must check novelty, review the page and patch schema,
choose public artifact hosting, try the local package, and explicitly approve
publication. Relay cannot deploy. This file sends no messages.
