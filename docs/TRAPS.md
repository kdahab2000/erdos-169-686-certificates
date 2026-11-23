# Trap and claim-control ledger

This file records failure modes that must be checked before any #169 or #686 claim is called novel.

1. **Periodic sets can contain progressions.** A modular construction needs a separate proof; testing one residue class is not enough.
2. **Pell methods for non-square #686 values are known methods.** A new witness is not automatically a new literature result.
3. **The domain matters for #686.** This lab enforces `n >= 1`; allowing `n = 0` changes the problem and invalidates null claims.
4. **The rejected prime-base rule is false.** For example, `B=5, D={0,1,2,3}` is not 3-AP-free, and neither is `B=5, D={0,1,2}`.
5. **Rejecting differences divisible by `k-1` is false.** It discards genuine optima; only a complete k-term progression is a violation.
6. **Carry trap.** `2,4,6,8` is a 4-term AP; its base-4 digits are `2,10,12,20`.
7. **No cross-N or cross-k comparisons.** `g_3(24)` cannot be compared with `g_3(16)`, and `g_3(N)` cannot be compared with `g_4(M)`.
8. **Decimal printing is floor-only.** If `D` printed digits follow a decimal, the enclosure is `printed + 10^-digits`; it is not a rounded interval.
9. **A bounded box is not a proof.** `erd686.null.v1` with `method=bounded_box` says only that the stated box was searched.
10. **F(8) literature conflicts.** The inherited figures 151182379 and 151640330 disagree; #148 remains deferred until the live source is checked.
11. **#64 bounds mix graph classes.** Cubic, bipartite-cubic, planar, and 3-connected results cannot be compared as one record.
12. **Finite-prefix digit audits do not prove infinite AP-freeness.** The accepted digit rule is: `D` is k-AP-free and `2*max(D) < B`; level-crossing audits remain a separate diagnostic.
13. **Feasible, optimal, and novel are different claim levels.** Certificate acceptance is feasibility; replay is optimality; only a reconciled literature baseline and explicit user approval can support a record claim.
14. **No float in verification.** Verifier decisions use `Fraction` and exact big integers; floating-point values are rejected by strict JSON parsing.
