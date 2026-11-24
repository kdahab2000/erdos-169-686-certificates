"""Incremental bitmask solver and measurement harness for Z/125Z cyclic 5-AP-free sets."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from verifiers.common import canonical_json_bytes
from verifiers.v169 import cyclic_progressions


class SearchBudgetExceeded(Exception):
    pass


def build_z125_tables():
    """Precompute 125-bit vertex masks and 7525-bit AP incidence tables."""
    edges = cyclic_progressions(125)
    ap_masks: List[int] = []
    ap_pairs: List[List[str]] = []
    v_ap_bits = [0] * 125
    for idx, (edge, pair) in enumerate(edges.items()):
        m = 0
        for v in edge:
            m |= 1 << v
            v_ap_bits[v] |= 1 << idx
        ap_masks.append(m)
        ap_pairs.append([str(pair[0]), str(pair[1])])
    fibres = [sum(1 << (a + 5 * j) for j in range(25)) for a in range(5)]
    cosets = [sum(1 << (a + 25 * j) for j in range(5)) for a in range(25)]
    all_aps = (1 << len(ap_masks)) - 1
    full_125 = (1 << 125) - 1
    return {
        "ap_masks": ap_masks,
        "ap_pairs": ap_pairs,
        "v_ap_bits": v_ap_bits,
        "fibres": fibres,
        "cosets": cosets,
        "all_aps": all_aps,
        "full": full_125,
    }


def _bit_indices(mask: int) -> List[int]:
    out: List[int] = []
    while mask:
        b = mask & -mask
        out.append(b.bit_length() - 1)
        mask ^= b
    return out


def solve_orbit(
    h0_mask: int,
    tables: dict,
    strategy: str = "ap_interleave",
    max_nodes: int = 200_000,
    max_seconds: float = 10.0,
) -> Dict[str, object]:
    """Run v2-compatible branch-and-bound on one H0 representative mask."""
    ap_masks = tables["ap_masks"]
    ap_pairs = tables["ap_pairs"]
    v_ap_bits = tables["v_ap_bits"]
    fibres = tables["fibres"]
    cosets = tables["cosets"]
    all_aps = tables["all_aps"]
    full = tables["full"]

    cap = h0_mask.bit_count()
    nodes: List[dict] = []
    started = time.monotonic_ns()
    budget_ns = int(max_seconds * 1_000_000_000)

    # Initial H0 state: H0 selected, rest of fibre 0 excluded.
    sel0 = sum(1 << (5 * j) for j in range(25) if (h0_mask >> j) & 1)
    exc0 = fibres[0] ^ sel0

    # Initialize incremental 7525-bit AP buckets from (sel0, exc0).
    alive0 = all_aps
    tmp = exc0
    while tmp:
        b = tmp & -tmp
        alive0 &= ~v_ap_bits[b.bit_length() - 1]
        tmp ^= b

    s0 = all_aps
    s1 = 0
    s2 = 0
    s3 = 0
    s4 = 0
    tmp = sel0
    while tmp:
        b = tmp & -tmp
        v = b.bit_length() - 1
        vb = v_ap_bits[v]
        if alive0 & s4 & vb:
            raise ValueError("H0 already contains a 5-AP")
        h4 = s3 & vb
        h3 = s2 & vb
        h2 = s1 & vb
        h1 = s0 & vb
        s4 |= h4
        s3 = (s3 ^ h4) | h3
        s2 = (s2 ^ h3) | h2
        s1 = (s1 ^ h2) | h1
        s0 ^= h1
        tmp ^= b

    def add_selected(v: int, alive: int, b0: int, b1: int, b2: int, b3: int, b4: int):
        vb = v_ap_bits[v]
        c_bits = alive & b4 & vb
        if c_bits:
            c_idx = (c_bits & -c_bits).bit_length() - 1
            return None, c_idx
        h4 = b3 & vb
        h3 = b2 & vb
        h2 = b1 & vb
        h1 = b0 & vb
        return (
            b0 ^ h1,
            (b1 ^ h2) | h1,
            (b2 ^ h3) | h2,
            (b3 ^ h4) | h3,
            b4 | h4,
        ), -1

    def check_bounds(sel: int, und: int) -> Optional[str]:
        sel_cnt = sel.bit_count()
        # Dominance (cap = |H0|) and fibre (cap = 16)
        f_counts = [(sel & p).bit_count() for p in fibres]
        if any(n > cap for n in f_counts):
            return "dominance"
        dom_up = sel_cnt + sum(min((und & p).bit_count(), cap - n) for p, n in zip(fibres, f_counts))
        if dom_up <= 64:
            return "dominance"
        # Coset (cap = 4)
        c_counts = [(sel & p).bit_count() for p in cosets]
        if any(n > 4 for n in c_counts):
            return "coset"
        cos_up = sel_cnt + sum(min((und & p).bit_count(), 4 - n) for p, n in zip(cosets, c_counts))
        if cos_up <= 64:
            return "coset"
        # Fibre (cap = 16)
        if any(n > 16 for n in f_counts):
            return "fibre"
        fib_up = sel_cnt + sum(min((und & p).bit_count(), 16 - n) for p, n in zip(fibres, f_counts))
        if fib_up <= 64:
            return "fibre"
        return None

    def try_packing(sel: int, und: int, alive: int, b0: int, b1: int, b2: int, b3: int) -> Optional[List[List[str]]]:
        sel_cnt = sel.bit_count()
        und_cnt = und.bit_count()
        need = sel_cnt + und_cnt - 64
        if need <= 0:
            return []
        c2 = alive & b3
        min_width = 2 if c2 else (3 if (alive & b2) else (4 if (alive & b1) else 5))
        if need > und_cnt // min_width:
            return None
        occupied = 0
        packing: List[List[str]] = []
        # Smallest undecided-count APs first: count=2 (b3), count=3 (b2), count=4 (b1), count=5 (b0)
        for bucket in (c2, alive & b2, alive & b1, alive & b0):
            cur = bucket
            while cur:
                bit = cur & -cur
                idx = bit.bit_length() - 1
                cur ^= bit
                todo = ap_masks[idx] & und
                if not (todo & occupied):
                    occupied |= todo
                    packing.append(ap_pairs[idx])
                    if len(packing) >= need:
                        return packing
        return None

    def pick_branch(sel: int, und: int, alive: int, b0: int, b1: int, b2: int, b3: int) -> int:
        if strategy == "h1_first":
            # Strictly finish H1 (j%5==1), then H2, H3, H4.
            for r in (1, 2, 3, 4):
                cand_mask = und & fibres[r]
                if not cand_mask:
                    continue
                cands = _bit_indices(cand_mask)
                c2 = alive & b3
                scores = {j: 0 for j in cands}
                bucket = c2 if c2 else (alive & b2)
                cur = bucket
                while cur:
                    bit = cur & -cur
                    idx = bit.bit_length() - 1
                    cur ^= bit
                    todo = ap_masks[idx] & cand_mask
                    while todo:
                        jb = todo & -todo
                        scores[jb.bit_length() - 1] += 1
                        todo ^= jb
                return max(cands, key=lambda j: (scores[j], -j))

        if strategy == "ap_interleave":
            # Branch inside the smallest non-empty open AP bucket (count=2, then 3, 4, 5).
            cands = _bit_indices(und)
            c2 = alive & b3
            if c2:
                scores = {j: 0 for j in cands}
                cur = c2
                while cur:
                    bit = cur & -cur
                    idx = bit.bit_length() - 1
                    cur ^= bit
                    todo = ap_masks[idx] & und
                    j1 = (todo & -todo).bit_length() - 1
                    j2 = (todo ^ (todo & -todo)).bit_length() - 1
                    w = 2 if (j1 % 5) != (j2 % 5) else 1
                    scores[j1] += w
                    scores[j2] += w
                return max(cands, key=lambda j: (scores[j], -(cap - (sel & fibres[j % 5]).bit_count()), -j))
            for bucket in (alive & b2, alive & b1, alive & b0):
                if bucket:
                    scores = {j: 0 for j in cands}
                    cur = bucket
                    while cur:
                        bit = cur & -cur
                        idx = bit.bit_length() - 1
                        cur ^= bit
                        todo = ap_masks[idx] & und
                        while todo:
                            jb = todo & -todo
                            scores[jb.bit_length() - 1] += 1
                            todo ^= jb
                    return max(cands, key=lambda j: (scores[j], -(cap - (sel & fibres[j % 5]).bit_count()), -j))
            return max(cands, key=lambda j: (-(cap - (sel & fibres[j % 5]).bit_count()), -j))

        # Default "current": exact replica of z125_solver.py scoring
        cands = _bit_indices(und)
        scores = {j: 0 for j in cands}
        cur = alive & b3
        while cur:
            bit = cur & -cur
            idx = bit.bit_length() - 1
            cur ^= bit
            todo = ap_masks[idx] & und
            j1 = (todo & -todo).bit_length() - 1
            j2 = (todo ^ (todo & -todo)).bit_length() - 1
            w = 2 if (j1 % 5) != (j2 % 5) else 1
            scores[j1] += w
            scores[j2] += w
        return max(cands, key=lambda j: (scores[j], -(cap - (sel & fibres[j % 5]).bit_count()), -j))

    def visit(sel: int, exc: int, alive: int, b0: int, b1: int, b2: int, b3: int, b4: int) -> None:
        if len(nodes) >= max_nodes or (time.monotonic_ns() - started) > budget_ns:
            raise SearchBudgetExceeded()

        if sel.bit_count() >= 65:
            raise ValueError("larger witness: " + str(_bit_indices(sel)))

        und = full ^ (sel | exc)
        bnd = check_bounds(sel, und)
        if bnd is not None:
            nodes.append({"op": "prune", "bound": bnd})
            return

        # Batch check all forced exclusions (alive & b4)
        forced_aps = alive & b4
        if forced_aps:
            # Emit one force per newly excluded vertex, skipping duplicates.
            bit = forced_aps & -forced_aps
            idx = bit.bit_length() - 1
            todo = ap_masks[idx] & und
            j = todo.bit_length() - 1
            nodes.append({"op": "force", "j": str(j), "ap": ap_pairs[idx]})
            visit(sel, exc | (1 << j), alive & ~v_ap_bits[j], b0, b1, b2, b3, b4)
            return

        packing = try_packing(sel, und, alive, b0, b1, b2, b3)
        if packing is not None:
            nodes.append({"op": "prune", "bound": "packing", "aps": packing})
            return

        if not und:
            # sel.bit_count() <= 64 already checked above
            nodes.append({"op": "prune", "bound": "dominance"})
            return

        j = pick_branch(sel, und, alive, b0, b1, b2, b3)
        nodes.append({"op": "branch", "j": str(j)})

        # Include branch
        nxt_buckets, conflict_idx = add_selected(j, alive, b0, b1, b2, b3, b4)
        if conflict_idx >= 0:
            nodes.append({"op": "conflict", "ap": ap_pairs[conflict_idx]})
        else:
            nb0, nb1, nb2, nb3, nb4 = nxt_buckets
            visit(sel | (1 << j), exc, alive, nb0, nb1, nb2, nb3, nb4)

        # Exclude branch
        visit(sel, exc | (1 << j), alive & ~v_ap_bits[j], b0, b1, b2, b3, b4)

    status = "complete"
    witness = None
    try:
        visit(sel0, exc0, alive0, s0, s1, s2, s3, s4)
    except SearchBudgetExceeded:
        status = "budget exceeded"
    except ValueError as exc:
        if str(exc).startswith("larger witness: "):
            status = "witness_ge_65"
            witness = str(exc)
        else:
            raise

    elapsed_ns = time.monotonic_ns() - started
    return {
        "mask": str(h0_mask),
        "fibre_size": h0_mask.bit_count(),
        "strategy": strategy,
        "status": status,
        "nodes": len(nodes),
        "bytes": len(canonical_json_bytes(nodes)) if status == "complete" else 0,
        "elapsed_ns": str(elapsed_ns),
        "tree": nodes if status == "complete" else None,
        "witness": witness,
    }


def measure_c6(max_seconds_per_run: float = 5.0, max_nodes: int = 200_000) -> dict:
    """Run C-measure on mask 507375 and first size-13 orbit under 3 strategies."""
    tables = build_z125_tables()
    reps = list(map(int, json.loads(Path("benchmarks/c4_h0_orbits.json").read_text())["h0_representative_masks"]))
    mask_16 = 507375
    mask_13 = next(m for m in reps if m.bit_count() == 13)
    assert mask_16 in reps

    results = []
    for mask in (mask_16, mask_13):
        for strategy in ("current", "h1_first", "ap_interleave"):
            res = solve_orbit(
                mask,
                tables,
                strategy=strategy,
                max_nodes=max_nodes,
                max_seconds=max_seconds_per_run,
            )
            results.append({
                "mask": res["mask"],
                "fibre_size": res["fibre_size"],
                "strategy": strategy,
                "status": res["status"],
                "nodes": res["nodes"],
                "bytes": res["bytes"],
                "elapsed_ns": res["elapsed_ns"],
            })

    # Compute projection per strategy:
    # Conservative projection if both closed: 8*n16 + 50*n16 + 205*n13 + 528*n13 (or lower bound)
    projections = {}
    for strategy in ("current", "h1_first", "ap_interleave"):
        r16 = next(r for r in results if r["strategy"] == strategy and r["fibre_size"] == 16)
        r13 = next(r for r in results if r["strategy"] == strategy and r["fibre_size"] == 13)
        if r16["status"] == "complete" and r13["status"] == "complete":
            proj = 8 * r16["nodes"] + 783 * r13["nodes"]
        else:
            proj = None
        projections[strategy] = proj

    payload = {
        "claim": "none",
        "gate_g1_limit_nodes": 1_000_000,
        "orbits_tested": [str(mask_16), str(mask_13)],
        "measurements": results,
        "projected_total_nodes": projections,
        "gate_g1_passed": any(p is not None and p <= 1_000_000 for p in projections.values()),
    }
    Path("benchmarks/c6_z125_measure.json").write_text(json.dumps(payload, indent=2) + "\n")
    return payload
