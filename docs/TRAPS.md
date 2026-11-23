# Trap and claim-control ledger

This file records failure modes that must be checked before any #169 or #686 claim is called novel.

1. **Periodic sets can contain progressions.** A modular construction needs a separate proof; testing one residue class is not enough.
2. **Pell methods for non-square #686 values are known methods.** A new witness is not automatically a new literature result.
3. **The domain matters for #686.** This lab enforces `n >= 1`; allowing `n = 0` changes the problem and invalidates null claims.
4. **Prime-base rule has hypotheses.** It is valid only for prime p, k >= p, zero-padded digits, 0 in D, and a proper digit subset. Base 5 with D={0,1,2,3} is 5-AP-free, but remains invalid for k=3. Translation preserves AP-freeness.
5. **Rejecting differences divisible by `k-1` is false.** It discards genuine optima; only a complete k-term progression is a violation.
6. **Carry trap.** `2,4,6,8` is a 4-term AP; its base-4 digits are `2,10,12,20`.
7. **No cross-N or cross-k comparisons.** `g_3(24)` cannot be compared with `g_3(16)`, and `g_3(N)` cannot be compared with `g_4(M)`.
8. **Decimal printing is floor-only.** If `D` printed digits follow a decimal, the enclosure is `printed + 10^-digits`; it is not a rounded interval.
9. **A bounded null proves only its replayed box.** `erd686.null.v1` with `method=bounded_box` does not settle the infinite problem. Both verifiers recompute every stated n and k, with m unbounded by n_max.
10. **F(8) literature conflicts.** The inherited figures 151182379 and 151640330 disagree; #148 remains deferred until the live source is checked.
11. **#64 bounds mix graph classes.** Cubic, bipartite-cubic, planar, and 3-connected results cannot be compared as one record.
12. **Finite-prefix audits do not prove infinite AP-freeness.** The legacy no-carry digit rule remains conservative. The separate prime-base rule requires prime p, k >= p, padded digits, 0 in D and a proper subset. Block digits additionally require no nonconstant cyclic p-AP modulo p^L.
13. **Feasible, optimal, and novel are different claim levels.** Certificate acceptance is feasibility; replay is optimality; only a reconciled literature baseline and explicit user approval can support a record claim.
14. **No float in verification.** Verifier decisions use `Fraction` and exact big integers; floating-point values are rejected by strict JSON parsing.

15. **Unthinned h=5 tail trap.** Differences d_m=(5^m-1)/2 give arbitrarily large cross-boundary APs. A finite head scan cannot certify this addition.
16. **3380 is tail-compatible, not admissible.** At s=1,L=6, the 12 differences for APs starting at 3380 are 1,2,3,7,12,13,187,188,207,2062,2063,2082. Checking all positions of 3380 finds 80 APs. A coupled hitting set is required; none of these counts proves a positive gain.
17. **Root s is distinct from N.** N=s^2; N=4 and N=25 require s=2 and s=5. Historical s=4 and s=25 certificates refer to N=16 and N=625 and are preserved.
18. **Exact enclosure size is a resource constraint.** The required exact-sum block schema exceeds the existing 4096-bit rational cap at pure-base-5 depth 6. Do not replace its exact sums by rounded sums without a separately reviewed schema.
19. **OEIS and literature status are unverified here.** SOURCE_REPORTED_REQUIRES_LIVE_CHECK. No network lookup is authorized by this campaign.
