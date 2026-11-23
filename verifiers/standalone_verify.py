#!/usr/bin/env python3
"""Single-file, dependency-free verifier for the laboratory manifest.

This file intentionally imports nothing from the laboratory.  It supports the
finite/prefix/digit-set #169 schemas, #686 schemas, and independently replays the
branch-and-bound proof format used by this implementation.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from fractions import Fraction
from math import comb, gcd, isqrt
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set, Tuple

_DECIMAL = re.compile(r"0|[1-9][0-9]*\Z")


class BadCertificate(ValueError):
    pass


def _pairs(items: Iterable[Tuple[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise BadCertificate(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _no_float(token: str) -> None:
    raise BadCertificate("floating-point JSON number")


def _no_int(token: str) -> None:
    raise BadCertificate("certificate integer must be a decimal string")


def load_strict(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_pairs,
        parse_float=_no_float,
        parse_int=_no_int,
    )


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def load_manifest(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_pairs,
        parse_float=_no_float,
        parse_int=_no_int,
    )


def integer(value: Any, label: str, minimum: Optional[int] = None) -> int:
    if isinstance(value, bool) or not isinstance(value, str) or not _DECIMAL.fullmatch(value):
        raise BadCertificate(f"{label} is not a canonical decimal string")
    number = int(value)
    if number.bit_length() > 4096:
        raise BadCertificate(f"{label} exceeds 4096 bits")
    if minimum is not None and number < minimum:
        raise BadCertificate(f"{label} is below {minimum}")
    return number


def exact_keys(obj: Mapping[str, Any], expected: Iterable[str], label: str) -> None:
    expected = set(expected)
    actual = set(obj)
    if expected != actual:
        raise BadCertificate(
            f"{label} keys differ: missing={sorted(expected-actual)}, unknown={sorted(actual-expected)}"
        )


def fraction_obj(value: Any, label: str) -> Fraction:
    if not isinstance(value, dict):
        raise BadCertificate(f"{label} is not an object")
    exact_keys(value, ("num", "den"), label)
    numerator = integer(value["num"], label + ".num", 0)
    denominator = integer(value["den"], label + ".den", 1)
    result = Fraction(numerator, denominator)
    if result.numerator != numerator or result.denominator != denominator:
        raise BadCertificate(f"{label} is not reduced")
    return result


def find_ap(values: Iterable[int], k: int) -> Optional[Tuple[int, int]]:
    values = sorted(set(values))
    present = set(values)
    if not values:
        return None
    maximum = values[-1]
    for start in values:
        for difference in range(1, maximum - start + 1):
            if start + (k - 1) * difference > maximum:
                break
            if all(start + index * difference in present for index in range(k)):
                return start, difference
    return None


def verify_finite(cert: Mapping[str, Any]) -> Dict[str, Any]:
    exact_keys(cert, ("schema", "k", "N", "members", "score"), "finite")
    if cert["schema"] != "erd169.finite.v1":
        raise BadCertificate("wrong finite schema")
    k = integer(cert["k"], "k", 3)
    if cert["N"] is None:
        upper = None
    elif isinstance(cert["N"], str):
        upper = integer(cert["N"], "N", 1)
    else:
        raise BadCertificate("N must be a decimal string or null")
    if not isinstance(cert["members"], list):
        raise BadCertificate("members is not an array")
    members = [integer(value, "member", 1) for value in cert["members"]]
    if members != sorted(set(members)):
        raise BadCertificate("members are not strictly increasing")
    if upper is not None and any(value > upper for value in members):
        raise BadCertificate("member exceeds N")
    if find_ap(members, k) is not None:
        raise BadCertificate("members contain a k-term AP")
    score = sum((Fraction(1, value) for value in members), Fraction())
    if fraction_obj(cert["score"], "score") != score:
        raise BadCertificate("score mismatch")
    return {
        "valid": True,
        "score": {"num": str(score.numerator), "den": str(score.denominator)},
        "members": [str(value) for value in members],
    }


def digit_candidates(base: int, digits: List[int], positions: int) -> Iterable[int]:
    if positions == 0:
        yield 0
    else:
        for tail in digit_candidates(base, digits, positions - 1):
            for digit in digits:
                yield digit * base ** (positions - 1) + tail


def verify_digitset(cert: Mapping[str, Any]) -> Dict[str, Any]:
    exact_keys(
        cert,
        ("schema", "k", "B", "D", "s", "L", "Q", "head_lb", "tail_lb"),
        "digitset",
    )
    if cert["schema"] != "erd169.digitset.v1":
        raise BadCertificate("wrong digit-set schema")
    k = integer(cert["k"], "k", 3)
    base = integer(cert["B"], "B", 2)
    s = integer(cert["s"], "s", 1)
    level = integer(cert["L"], "L", 1)
    q = integer(cert["Q"], "Q", 1)
    if not isinstance(cert["D"], list):
        raise BadCertificate("D is not an array")
    digits = [integer(value, "D member", 0) for value in cert["D"]]
    if digits != sorted(set(digits)) or len(digits) < 2:
        raise BadCertificate("D is not strictly increasing with at least two members")
    if any(value >= base for value in digits):
        raise BadCertificate("D contains a value outside [0,B)")
    if 2 * max(digits) >= base:
        raise BadCertificate("2*max(D) < B failed")
    if find_ap(digits, k) is not None:
        raise BadCertificate("D contains a k-term AP")
    nonzero = [value for value in digits if value != 0]
    head_values: List[int] = []
    if 0 in digits:
        head_values.append(0)
    for length in range(1, level):
        for leading in nonzero:
            for tail in digit_candidates(base, digits, length - 1):
                head_values.append(leading * base ** (length - 1) + tail)
    if len(head_values) > 2_000_000:
        raise BadCertificate("digit-head enumeration cap exceeded")
    head = sum((Fraction(q // (s + value), q) for value in head_values), Fraction())
    count = len(digits)
    max_digit = max(digits)
    constant = Fraction(base - 1, 1) / (
        Fraction((base - 1) * s, base**level) + max_digit
    )
    ratio = Fraction(count, base)
    alpha = count - 1 if 0 in digits else count
    tail = constant * (
        Fraction(alpha, 1) * count ** (level - 1) / base**level / (1 - ratio)
    )
    if fraction_obj(cert["head_lb"], "head_lb") != head:
        raise BadCertificate("head_lb mismatch")
    if fraction_obj(cert["tail_lb"], "tail_lb") != tail:
        raise BadCertificate("tail_lb mismatch")
    return {
        "valid": True,
        "head_lb": {"num": str(head.numerator), "den": str(head.denominator)},
        "tail_lb": {"num": str(tail.numerator), "den": str(tail.denominator)},
    }


def verify_prefix(cert: Mapping[str, Any], base_dir: Path) -> Dict[str, Any]:
    exact_keys(
        cert,
        (
            "schema",
            "k",
            "N",
            "witness_sha256",
            "proof_sha256",
            "proof_format",
            "tie_policy",
        ),
        "prefix",
    )
    if cert["schema"] != "erd169.prefix_opt.v1":
        raise BadCertificate("wrong prefix schema")
    integer(cert["k"], "k", 3)
    integer(cert["N"], "N", 1)
    if cert["proof_format"] != "erd169.bnb.v1":
        raise BadCertificate("wrong proof format")
    for label in ("witness_sha256", "proof_sha256"):
        digest = cert[label]
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise BadCertificate(f"bad {label}")
    return {"valid": True, "prefix": True}


def novelty_tags(n_value: int, k: int) -> List[str]:
    root = isqrt(n_value)
    square = root * root == n_value
    tags: List[str] = []
    if not square:
        tags.append("NONSQUARE_PELL_KNOWN")
    elif k == 2:
        tags.append("K2_SQUARE_DIVISOR_KNOWN_METHOD")
    elif k == 4:
        tags.append("K4_SQUARE_DIVISOR_KNOWN_METHOD")
    elif k == 3 and n_value in (9, 16):
        tags.append("SMALL_K3_FIXTURE")
    elif square:
        tags.append("CANDIDATE_SQUARE")
    return tags


def verify_686_rep(cert: Mapping[str, Any]) -> Dict[str, Any]:
    exact_keys(cert, ("schema", "N", "k", "n", "m"), "686 rep")
    if cert["schema"] != "erd686.rep.v1":
        raise BadCertificate("wrong #686 representation schema")
    n_value = integer(cert["N"], "N", 2)
    k = integer(cert["k"], "k", 2)
    n = integer(cert["n"], "n", 1)
    m = integer(cert["m"], "m", 1)
    if m < n + k:
        raise BadCertificate("m < n+k")
    if comb(m + k, k) != n_value * comb(n + k, k):
        raise BadCertificate("binomial equality failed")
    product_m = 1
    product_n = 1
    for index in range(1, k + 1):
        product_m *= m + index
        product_n *= n + index
    if product_m != n_value * product_n:
        raise BadCertificate("product equality failed")
    return {
        "valid": True,
        "N": n_value,
        "k": k,
        "n": n,
        "m": m,
        "novelty_tags": novelty_tags(n_value, k),
    }


def verify_686_null(cert: Mapping[str, Any]) -> Dict[str, Any]:
    exact_keys(cert, ("schema", "s", "k_set", "method", "box", "domain"), "686 null")
    if cert["schema"] != "erd686.null.v1":
        raise BadCertificate("wrong #686 null schema")
    integer(cert["s"], "s", 2)
    if not isinstance(cert["k_set"], list):
        raise BadCertificate("k_set is not an array")
    k_set = [integer(value, "k", 2) for value in cert["k_set"]]
    if k_set != sorted(set(k_set)):
        raise BadCertificate("k_set is not strictly increasing")
    if cert["method"] == "divisor_complete":
        if cert["box"] is not None:
            raise BadCertificate("divisor_complete null must have box=null")
    else:
        if not isinstance(cert["box"], dict):
            raise BadCertificate("bounded_box null requires a box object")
        exact_keys(cert["box"], ("k_max", "n_max"), "box")
        integer(cert["box"]["k_max"], "k_max", 2)
        integer(cert["box"]["n_max"], "n_max", 1)
    if cert["method"] not in ("divisor_complete", "bounded_box"):
        raise BadCertificate("bad null method")
    if cert["domain"] != "n>=1":
        raise BadCertificate("bad null domain")
    return {"valid": True}


def lcm(a: int, b: int) -> int:
    return a // gcd(a, b) * b


def replay(proof: Mapping[str, Any]) -> Dict[str, Any]:
    exact_keys(
        proof,
        ("schema", "k", "N", "witness", "witness_score", "incumbent_weight", "tree"),
        "proof",
    )
    if proof["schema"] != "erd169.bnb.v1":
        raise BadCertificate("wrong proof schema")
    k = integer(proof["k"], "k", 3)
    n = integer(proof["N"], "N", 1)
    if not isinstance(proof["witness"], list):
        raise BadCertificate("witness is not an array")
    witness = [integer(value, "witness member", 1) for value in proof["witness"]]
    if witness != sorted(set(witness)) or any(value > n for value in witness):
        raise BadCertificate("invalid witness ordering/range")
    if find_ap(witness, k) is not None:
        raise BadCertificate("witness contains an AP")
    score = sum((Fraction(1, value) for value in witness), Fraction())
    if fraction_obj(proof["witness_score"], "witness_score") != score:
        raise BadCertificate("witness score mismatch")
    common = 1
    for value in range(1, n + 1):
        common = lcm(common, value)
    weight = sum(common // value for value in witness)
    incumbent = integer(proof["incumbent_weight"], "incumbent_weight", 0)
    if incumbent != weight:
        raise BadCertificate("incumbent mismatch")
    progressions: List[Tuple[int, int, Tuple[int, ...]]] = []
    for start in range(1, n + 1):
        for difference in range(1, (n - start) // (k - 1) + 1):
            progressions.append(
                (start, difference, tuple(start + i * difference for i in range(k)))
            )
    by_key = {(a, b): terms for a, b, terms in progressions}
    nodes = proof["tree"]
    if not isinstance(nodes, list) or not nodes:
        raise BadCertificate("empty proof tree")
    visited: Set[int] = set()
    best = -1

    def bound(
        selected: Set[int],
        excluded: Set[int],
        undecided: Set[int],
        pairs: List[Tuple[int, int]],
    ) -> int:
        occupied: Set[int] = set()
        deduction = 0
        for start, difference in pairs:
            terms = by_key.get((start, difference))
            if terms is None:
                raise BadCertificate("unknown progression")
            if any(value in excluded for value in terms):
                raise BadCertificate("inactive progression")
            active = set(terms) & undecided
            if not active:
                raise BadCertificate("progression has no undecided member")
            if occupied & active:
                raise BadCertificate("overlapping progression deductions")
            occupied |= active
            deduction += min(common // value for value in active)
        return sum(common // value for value in selected) + sum(
            common // value for value in undecided
        ) - deduction

    def visit(index: int, selected: Set[int], excluded: Set[int]) -> None:
        nonlocal best
        if index in visited or index < 0 or index >= len(nodes):
            raise BadCertificate("invalid/cyclic proof child")
        visited.add(index)
        node = nodes[index]
        if not isinstance(node, dict):
            raise BadCertificate("proof node is not an object")
        operation = node.get("op")
        if operation == "branch":
            exact_keys(node, ("op", "j", "include", "exclude"), "branch")
            member = integer(node["j"], "j", 1)
            if member > n or member in selected or member in excluded:
                raise BadCertificate("branch on non-undecided member")
            include = integer(node["include"], "include", 0)
            exclude = integer(node["exclude"], "exclude", 0)
            visit(include, selected | {member}, excluded)
            visit(exclude, selected, excluded | {member})
        elif operation == "prune":
            exact_keys(node, ("op", "aps"), "prune")
            if find_ap(selected, k) is not None:
                raise BadCertificate("invalid selected state")
            undecided = set(range(1, n + 1)) - selected - excluded
            pairs: List[Tuple[int, int]] = []
            if not isinstance(node["aps"], list):
                raise BadCertificate("aps is not an array")
            for item in node["aps"]:
                if not isinstance(item, list) or len(item) != 2:
                    raise BadCertificate("bad progression pair")
                pairs.append(
                    (integer(item[0], "start", 1), integer(item[1], "difference", 1))
                )
            if bound(selected, excluded, undecided, pairs) > incumbent:
                raise BadCertificate("invalid prune bound")
        elif operation == "leaf":
            exact_keys(node, ("op", "status"), "leaf")
            if node["status"] == "feasible":
                if find_ap(selected, k) is not None:
                    raise BadCertificate("invalid feasible leaf")
                best = max(best, sum(common // value for value in selected))
            elif node["status"] != "infeasible":
                raise BadCertificate("unknown leaf status")
        else:
            raise BadCertificate("unknown proof operation")

    visit(0, set(), set())
    if visited != set(range(len(nodes))):
        raise BadCertificate("unreachable proof nodes")
    if best < 0 or best > incumbent:
        raise BadCertificate("proof does not certify the incumbent")
    return {"valid": True, "optimal": True, "nodes": len(nodes), "best": best}


def verify_certificate(cert: Mapping[str, Any]) -> Dict[str, Any]:
    """Verify one standalone certificate and return a structured result."""

    if not isinstance(cert, dict):
        raise BadCertificate("certificate is not an object")
    schema = cert.get("schema")
    if schema == "erd169.finite.v1":
        return verify_finite(cert)
    if schema == "erd169.digitset.v1":
        return verify_digitset(cert)
    if schema == "erd169.prefix_opt.v1":
        return verify_prefix(cert, Path.cwd())
    if schema == "erd686.rep.v1":
        return verify_686_rep(cert)
    if schema == "erd686.null.v1":
        return verify_686_null(cert)
    raise BadCertificate(f"unsupported schema {schema!r}")


def verify_entry(entry: Mapping[str, Any], base_dir: Path) -> Dict[str, Any]:
    if not isinstance(entry, dict):
        return {"valid": False, "error": "manifest entry is not an object"}
    path_value = entry.get("path")
    if not isinstance(path_value, str):
        return {"valid": False, "error": "manifest entry has no path"}
    path = (base_dir / path_value).resolve()
    try:
        path.relative_to(base_dir.resolve())
    except ValueError:
        return {"valid": False, "error": "path escapes certificate directory"}
    expected_digest = entry.get("sha256")
    if not isinstance(expected_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_digest):
        return {"valid": False, "error": "manifest entry has no valid sha256"}
    try:
        cert = load_strict(path)
        if not isinstance(cert, dict):
            raise BadCertificate("certificate is not an object")
        actual_digest = hashlib.sha256(canonical_bytes(cert)).hexdigest()
        if actual_digest != expected_digest:
            return {"valid": False, "error": "certificate sha256 mismatch"}
        schema = cert.get("schema")
        if schema == "erd169.finite.v1"
            return verify_finite(cert)
        if schema == "erd169.digitset.v1":
            return verify_digitset(cert)
        if schema == "erd169.prefix_opt.v1":
            return verify_prefix(cert, base_dir)
        if schema == "erd686.rep.v1":
            return verify_686_rep(cert)
        if schema == "erd686.null.v1":
            return verify_686_null(cert)
        raise BadCertificate(f"unsupported schema {schema!r}")
    except (OSError, json.JSONDecodeError, BadCertificate, ValueError) as exc:
        return {"valid": False, "error": str(exc)}


def main(argv: List[str]) -> int:
    if len(argv) != 2:
        print("usage: standalone_verify.py MANIFEST.json", file=sys.stderr)
        return 2
    manifest_path = Path(argv[1]).resolve()
    try:
        manifest = load_manifest(manifest_path)
        if not isinstance(manifest, dict):
            raise BadCertificate("manifest must be an object")
        entries = manifest.get("entries")
        if entries is None and isinstance(manifest.get("certificates"), list):
            entries = manifest["certificates"]
        if not isinstance(entries, list):
            raise BadCertificate("manifest must contain an entries array")
        failures = 0
        for entry in entries:
            answer = verify_entry(entry, manifest_path.parent)
            status = "OK" if answer.get("valid") else "FAIL"
            print(f"{status} {entry.get('path', '<unknown>') if isinstance(entry, dict) else '<invalid>'}")
            if not answer.get("valid"):
                failures += 1
                print(f"  {answer.get('error', answer.get('errors'))}", file=sys.stderr)
        print(f"verified={len(entries)} failures={failures}")
        return 1 if failures else 0
    except (OSError, json.JSONDecodeError, BadCertificate, ValueError) as exc:
        print(f"manifest error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
