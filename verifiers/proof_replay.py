"""Replay verifier for ``erd169.bnb.v1`` branch-and-bound proofs.

The proof is a preorder list.  A branch node names an undecided integer and
points to its include and exclude children.  Prune nodes list disjoint active
progressions used in the exact weight upper bound.  The replay is independent of
the solver: it reconstructs every search state from the root and checks all
bounds and digests itself.
"""

from __future__ import annotations

import hashlib
from fractions import Fraction
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set, Tuple

from .common import (
    CertificateError,
    canonical_fraction_object as certificate_fraction,
    canonical_integer,
    canonical_sha256,
    find_k_ap,
    lcm,
    require_exact_keys,
    require_object,
)

PROOF_SCHEMA = "erd169.bnb.v1"


def _canonical_bytes(value: Any) -> bytes:
    import json

    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _all_progressions(n: int, k: int) -> List[Tuple[int, int, Tuple[int, ...]]]:
    progressions: List[Tuple[int, int, Tuple[int, ...]]] = []
    for start in range(1, n + 1):
        for difference in range(1, (n - start) // (k - 1) + 1):
            terms = tuple(start + index * difference for index in range(k))
            progressions.append((start, difference, terms))
    return progressions


def _weight(member: int, common_multiple: int) -> int:
    return common_multiple // member


def _active_bound(
    selected: Set[int],
    excluded: Set[int],
    undecided: Set[int],
    progressions: Iterable[Tuple[int, int, Tuple[int, ...]]],
    common_multiple: int,
    used_progressions: Iterable[Tuple[int, int]],
) -> int:
    """Compute the ratified integer-weight upper bound.

    Each selected progression must be active and the *undecided portions* of the
    selected progressions must be pairwise disjoint.  The minimum weight in each
    active progression is the least cost of excluding one of its undecided
    members.
    """

    by_key = {(start, difference): terms for start, difference, terms in progressions}
    selected_weight = sum(_weight(member, common_multiple) for member in selected)
    undecided_weight = sum(_weight(member, common_multiple) for member in undecided)
    occupied: Set[int] = set()
    deduction = 0
    for start, difference in used_progressions:
        terms = by_key.get((start, difference))
        if terms is None:
            raise CertificateError(f"unknown progression ({start},{difference})")
        if any(term in excluded for term in terms):
            raise CertificateError("prune progression is not active")
        active_undecided = set(terms) & undecided
        if not active_undecided:
            raise CertificateError("prune progression has no undecided member")
        if occupied & active_undecided:
            raise CertificateError("prune progressions overlap on undecided members")
        occupied.update(active_undecided)
        deduction += min(_weight(member, common_multiple) for member in active_undecided)
    return selected_weight + undecided_weight - deduction


def _parse_tree(proof: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    tree = proof.get("tree")
    if not isinstance(tree, list) or not tree or len(tree) > 2000000:
        raise CertificateError("proof tree must be a non-empty array")
    return [require_object(node, f"tree[{index}]") for index, node in enumerate(tree)]


def _children(node: Mapping[str, Any], label: str) -> Tuple[int, int]:
    if "include" not in node or "exclude" not in node:
        raise CertificateError(f"{label} branch lacks include/exclude children")
    include = canonical_integer(node["include"], f"{label}.include", 0)
    exclude = canonical_integer(node["exclude"], f"{label}.exclude", 0)
    return include, exclude


def _parse_progression_pairs(node: Mapping[str, Any]) -> List[Tuple[int, int]]:
    raw = node.get("aps")
    if not isinstance(raw, list):
        raise CertificateError("prune node requires an aps array")
    pairs: List[Tuple[int, int]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, list) or len(item) != 2:
            raise CertificateError(f"prune aps[{index}] must be [start,difference]")
        start = canonical_integer(item[0], f"prune aps[{index}][0]", 1)
        difference = canonical_integer(item[1], f"prune aps[{index}][1]", 1)
        pairs.append((start, difference))
    return pairs


def replay_proof(
    proof: Mapping[str, Any],
    witness: Optional[Mapping[str, Any]] = None,
    witness_bytes: Optional[bytes] = None,
    proof_bytes: Optional[bytes] = None,
) -> Dict[str, Any]:
    """Replay a proof and return a structured verification result."""

    try:
        proof = require_object(proof, "proof")
        require_exact_keys(
            proof,
            (
                "schema",
                "k",
                "N",
                "witness",
                "witness_score",
                "incumbent_weight",
                "tree",
            ),
            "proof",
        )
        if proof["schema"] != PROOF_SCHEMA:
            raise CertificateError(f"expected schema {PROOF_SCHEMA!r}")
        k = canonical_integer(proof["k"], "k", 3)
        n = canonical_integer(proof["N"], "N", 1)
        if n > 256 or k > 256:
            raise CertificateError("proof dimension cap")
        raw_witness = proof["witness"]
        if not isinstance(raw_witness, list):
            raise CertificateError("proof witness must be an array")
        witness_members = [
            canonical_integer(item, f"witness[{index}]", 1)
            for index, item in enumerate(raw_witness)
        ]
        if witness_members != sorted(set(witness_members)):
            raise CertificateError("proof witness must be strictly increasing")
        if any(member > n for member in witness_members):
            raise CertificateError("proof witness exceeds N")
        if find_k_ap(witness_members, k) is not None:
            raise CertificateError("proof witness contains a k-term AP")
        witness_score = sum(
            (Fraction(1, member) for member in witness_members), Fraction(0, 1)
        )
        claimed_score = certificate_fraction(proof["witness_score"], "witness_score")
        if claimed_score != witness_score:
            raise CertificateError("proof witness_score does not equal the exact reciprocal sum")
        claimed_weight = proof["incumbent_weight"]
        if not isinstance(claimed_weight, str):
            raise CertificateError("incumbent_weight must be a canonical decimal string")
        canonical_integer(claimed_weight, "incumbent_weight", 0)
        if witness is not None:
            from .v169 import validate_finite

            checked = validate_finite(witness)
            if checked["k"] != k or checked["N"] != n:
                raise CertificateError("witness k/N differs from proof")
            if checked["members"] != witness_members:
                raise CertificateError("embedded witness differs from proof witness")

        if witness_bytes is not None:
            embedded = _canonical_bytes(witness) if witness is not None else witness_bytes
            if hashlib.sha256(embedded).hexdigest() != hashlib.sha256(witness_bytes).hexdigest():
                raise CertificateError("witness digest mismatch")
        if proof_bytes is not None:
            embedded = _canonical_bytes(proof)
            if hashlib.sha256(embedded).hexdigest() != hashlib.sha256(proof_bytes).hexdigest():
                raise CertificateError("proof digest mismatch")

        common_multiple = 1
        for member in range(1, n + 1):
            common_multiple = lcm(common_multiple, member)
        witness_weight = sum(_weight(member, common_multiple) for member in witness_members)
        incumbent = canonical_integer(proof["incumbent_weight"], "incumbent_weight", 0)
        if incumbent != witness_weight:
            raise CertificateError("incumbent_weight differs from witness weight")

        nodes = _parse_tree(proof)
        progressions = _all_progressions(n, k)
        by_key = {(start, difference): terms for start, difference, terms in progressions}
        visited: Set[int] = set()
        best_leaf_weight = -1
        leaves = 0
        prunes = 0

        def visit(index: int, selected: Set[int], excluded: Set[int]) -> None:
            nonlocal best_leaf_weight, leaves, prunes
            if index in visited:
                raise CertificateError("proof tree node is visited more than once")
            visited.add(index)
            if index >= len(nodes):
                raise CertificateError("proof child index is out of range")
            node = nodes[index]
            operation = node.get("op")
            if operation == "branch":
                require_exact_keys(node, ("op", "j", "include", "exclude"), "branch node")
                member = canonical_integer(node["j"], "branch j", 1)
                if member > n:
                    raise CertificateError("branch member exceeds N")
                if member in selected or member in excluded:
                    raise CertificateError("branch member is not undecided")
                include, exclude = _children(node, "branch node")
                visit(include, selected | {member}, excluded)
                visit(exclude, selected, excluded | {member})
                return
            if operation == "prune":
                require_exact_keys(node, ("op", "aps"), "prune node")
                if find_k_ap(selected, k) is not None:
                    raise CertificateError("pruned state already contains a k-term AP")
                undecided = set(range(1, n + 1)) - selected - excluded
                pairs = _parse_progression_pairs(node)
                bound = _active_bound(
                    selected,
                    excluded,
                    undecided,
                    progressions,
                    common_multiple,
                    pairs,
                )
                if bound > incumbent:
                    raise CertificateError("prune upper bound exceeds incumbent weight")
                prunes += 1
                return
            if operation == "leaf":
                require_exact_keys(node, ("op", "status"), "leaf node")
                if node["status"] not in ("feasible", "infeasible"):
                    raise CertificateError("unknown leaf status")
                leaves += 1
                undecided = set(range(1, n + 1)) - selected - excluded
                if node["status"] == "feasible":
                    if undecided:
                        raise CertificateError("feasible leaf leaves integers undecided")
                    if find_k_ap(selected, k) is not None:
                        raise CertificateError("feasible leaf contains a k-term AP")
                    best_leaf_weight = max(
                        best_leaf_weight,
                        sum(_weight(member, common_multiple) for member in selected),
                    )
                else:
                    if find_k_ap(selected, k) is None:
                        raise CertificateError("infeasible leaf has no k-term AP")
                return
            raise CertificateError(f"unknown proof operation: {operation!r}")

        visit(0, set(), set())
        if visited != set(range(len(nodes))):
            raise CertificateError("proof contains unreachable nodes")
        if best_leaf_weight < 0:
            raise CertificateError("proof has no feasible leaf")
        if best_leaf_weight > incumbent:
            raise CertificateError("proof contains a leaf better than the incumbent")
        return {
            "valid": True,
            "optimal": True,
            "k": k,
            "N": n,
            "witness_weight": witness_weight,
            "incumbent_weight": incumbent,
            "best_leaf_weight": best_leaf_weight,
            "leaves": leaves,
            "prunes": prunes,
            "nodes": len(nodes),
            "proof_sha256": hashlib.sha256(_canonical_bytes(proof)).hexdigest(),
        }
    except (CertificateError, TypeError, ValueError) as exc:
        return {"valid": False, "errors": [str(exc)]}
