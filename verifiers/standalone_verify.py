#!/usr/bin/env python3
"""Single-file, dependency-free verifier for the laboratory manifest.

This file intentionally imports nothing from the laboratory.  It supports the
finite/prefix/digit-set #169 schemas, #686 schemas, and independently replays the
branch-and-bound proof format used by this implementation.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import copy
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
        parse_constant=_no_float,
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
        parse_constant=_no_float,
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
    if level > 20 or len(digits)**(level-1) > 2000000:
        raise BadCertificate("digit enumeration cap")
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


_DIGEST_INDEX = ContextVar("digest_index", default=None)


@contextmanager
def digest_run(base_dir):
    """Snapshot canonical content for this replay only; never cache across runs."""
    root = Path(base_dir).resolve()
    index = {}
    for path in sorted(root.glob("*.json")):
        try:
            path.resolve().relative_to(root)
            obj = load_strict(path)
        except (OSError, ValueError):
            continue
        index[hashlib.sha256(canonical_bytes(obj)).hexdigest()] = obj
    token = _DIGEST_INDEX.set((root, index))
    try:
        yield
    finally:
        _DIGEST_INDEX.reset(token)


def resolve_digest(digest, base_dir):
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise BadCertificate("invalid reference digest")
    root = Path(base_dir).resolve()
    active = _DIGEST_INDEX.get()
    if active is None or active[0] != root:
        with digest_run(root):
            return resolve_digest(digest, root)
    if digest not in active[1]:
        raise BadCertificate("reference digest not found in certificate directory")
    return copy.deepcopy(active[1][digest])


def verify_prefix(cert, base_dir=None):
    exact_keys(cert, ("schema", "k", "N", "witness_sha256", "proof_sha256", "proof_format", "tie_policy"), "prefix")
    if cert["schema"] != "erd169.prefix_opt.v1" or cert["proof_format"] != "erd169.bnb.v1":
        raise BadCertificate("wrong prefix schema/format")
    integer(cert["k"], "k", 3)
    integer(cert["N"], "N", 1)
    if not isinstance(cert["tie_policy"], str) or not cert["tie_policy"]:
        raise BadCertificate("empty tie policy")
    if base_dir is None:
        raise BadCertificate("prefix verification requires certificate directory")
    witness = resolve_digest(cert["witness_sha256"], base_dir)
    proof = resolve_digest(cert["proof_sha256"], base_dir)
    if not isinstance(witness, dict) or not isinstance(proof, dict):
        raise BadCertificate("prefix evidence must be objects")
    verify_finite(witness)
    replay(proof)
    for key in ("k", "N"):
        if witness[key] != cert[key] or proof[key] != cert[key]:
            raise BadCertificate("prefix k/N mismatch")
    if witness["members"] != proof["witness"] or witness["score"] != proof["witness_score"]:
        raise BadCertificate("prefix witness/score mismatch")
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
    if k > 10000 or max(n, m).bit_length() > 256:
        raise BadCertificate("representation resource cap")
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


def box_hits(n_value, k, n_max):
    """Monotone exact merge; never bounds m by n_max."""
    m = 1
    fm = comb(m + k, k)
    fn = comb(1 + k, k)
    for n in range(1, n_max + 1):
        target = n_value * fn
        while m < n + k or fm < target:
            fm = fm * (m + k + 1) // (m + 1)
            m += 1
        if fm == target:
            yield n, m
        fn = fn * (n + k + 1) // (n + 1)


def divisor_has_hit(s, k):
    value = s * s - 1
    for lower in range(1, isqrt(value) + 1):
        if value % lower:
            continue
        upper = value // lower
        if (lower + upper) % 2 or ((lower + upper) // 2) % s:
            continue
        y = (lower + upper) // (2 * s)
        x = (upper - lower) // 2
        if k == 2:
            if y >= 5 and y % 2 and x % 2 and (x-y)//2 >= 2:
                return True
        else:
            ry, rx = isqrt(4*y+5), isqrt(4*x+5)
            if (ry*ry == 4*y+5 and rx*rx == 4*x+5 and ry >= 7
                    and (ry-5) % 2 == 0 and (rx-5) % 2 == 0
                    and (rx-ry)//2 >= 4):
                return True
    return False


def verify_686_null(cert):
    exact_keys(cert, ("schema", "s", "k_set", "method", "box", "domain"), "null")
    if cert["schema"] != "erd686.null.v1" or cert["domain"] != "n>=1":
        raise BadCertificate("wrong null schema/domain")
    s = integer(cert["s"], "s", 2)
    if s > 10000:
        raise BadCertificate("null root resource cap")
    if not isinstance(cert["k_set"], list):
        raise BadCertificate("k_set must be an array")
    ks = [integer(x, "k", 2) for x in cert["k_set"]]
    if not ks or ks != sorted(set(ks)) or max(ks) > 100:
        raise BadCertificate("empty, unordered or excessive k_set")
    if cert["method"] == "divisor_complete":
        if cert["box"] is not None or any(k not in (2, 4) for k in ks):
            raise BadCertificate("invalid divisor domain")
        if any(divisor_has_hit(s, k) for k in ks):
            raise BadCertificate("divisor null contains a representation")
    elif cert["method"] == "bounded_box":
        box = cert["box"]
        if not isinstance(box, dict):
            raise BadCertificate("box must be an object")
        exact_keys(box, ("k_max", "n_max"), "box")
        top = integer(box["k_max"], "k_max", 2)
        limit = integer(box["n_max"], "n_max", 1)
        if top != max(ks) or limit * len(ks) > 6000000:
            raise BadCertificate("box extent mismatch or resource cap")
        for k in ks:
            if next(box_hits(s*s, k, limit), None) is not None:
                raise BadCertificate("bounded null contains a representation")
    else:
        raise BadCertificate("unknown null method")
    return {"valid": True, "s": s, "k_set": ks, "method": cert["method"], "domain": "n>=1"}


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
    if n > 256 or k > 256:
        raise BadCertificate("proof dimension cap")
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
    if not isinstance(nodes, list) or not nodes or len(nodes) > 2000000:
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
                if set(range(1, n + 1)) - selected - excluded:
                    raise BadCertificate("feasible leaf leaves integers undecided")
                if find_ap(selected, k) is not None:
                    raise BadCertificate("invalid feasible leaf")
                best = max(best, sum(common // value for value in selected))
            elif node["status"] == "infeasible":
                if find_ap(selected, k) is None:
                    raise BadCertificate("infeasible leaf has no AP")
            else:
                raise BadCertificate("unknown leaf status")
        else:
            raise BadCertificate("unknown proof operation")

    visit(0, set(), set())
    if visited != set(range(len(nodes))):
        raise BadCertificate("unreachable proof nodes")
    if best < 0 or best > incumbent:
        raise BadCertificate("proof does not certify the incumbent")
    return {"valid": True, "optimal": True, "nodes": len(nodes), "best": best}


def rational_object(value):
    return {"num": str(value.numerator), "den": str(value.denominator)}


def padded_member(x, digits, base=5):
    if x < 0:
        return False
    while x:
        if x % base not in digits:
            return False
        x //= base
    return 0 in digits


def tail_compatible(a, s, level, digits, state_cap=200000):
    """Decide existence of four tail terms after a by signed base-5 carries.

    States retain the position only up to L. Beyond L the transition is
    stationary; revisiting a state cannot yield a new finite accepting path.
    An accepting path is a finite nonzero difference with four outputs >=5^L.
    """
    from collections import deque
    initial = ((a-s,)*4, 0, False, 0)
    queue = deque([initial])
    seen = {initial}
    while queue:
        carries, high, nonzero, pos = queue.popleft()
        if carries == (0, 0, 0, 0) and high == 15 and nonzero:
            return False
        for digit in range(5):
            values = [c + j*digit for j, c in enumerate(carries, 1)]
            outputs = [v % 5 for v in values]
            if any(v not in digits for v in outputs):
                continue
            mask = high
            if pos >= level:
                for j, v in enumerate(outputs):
                    if v:
                        mask |= 1 << j
            state = (tuple(v//5 for v in values), mask,
                     nonzero or digit != 0, min(level, pos+1))
            if state not in seen:
                if len(seen) >= state_cap:
                    raise BadCertificate("inconclusive: carry state cap")
                seen.add(state)
                queue.append(state)
    return True


def block_enclosure(base, digits, s, depth):
    if not 1 <= depth <= 20 or len(digits)**depth > 2000000:
        raise BadCertificate("block enumeration cap")
    values = [0]
    for _ in range(depth):
        values = [base*x+d for x in values for d in digits]
    head = Fraction()
    lower_tail = Fraction()
    upper_tail = Fraction()
    ratio_sum = Fraction(len(digits), base-len(digits))
    for x in values:
        head += Fraction(1, s+x)
        if x >= base**(depth-1):
            lower_tail += Fraction(1, x+1+s)*ratio_sum
            upper_tail += Fraction(1, x)*ratio_sum
        if max(head.denominator.bit_length(), lower_tail.denominator.bit_length(),
               upper_tail.denominator.bit_length()) > 4096:
            raise BadCertificate("exact enclosure exceeds 4096-bit rational cap")
    return head+lower_tail, head+upper_tail


def verify_block_digit(cert):
    exact_keys(cert, ("schema", "k", "p", "block_len", "D", "s", "depth", "lb", "ub"), "block digit")
    if cert["schema"] != "erd169.block_digit.v1":
        raise BadCertificate("wrong block digit schema")
    p = integer(cert["p"], "p", 2)
    k = integer(cert["k"], "k", 3)
    length = integer(cert["block_len"], "block_len", 1)
    depth = integer(cert["depth"], "depth", 1)
    s = integer(cert["s"], "s", 1)
    if p > 127 or k > 256 or length > 4:
        raise BadCertificate("block parameter cap")
    if any(p % q == 0 for q in range(2, isqrt(p)+1)) or k < p:
        raise BadCertificate("p must be prime and k >= p")
    base = p**length
    if not isinstance(cert["D"], list):
        raise BadCertificate("D must be an array")
    digits = [integer(x, "D", 0) for x in cert["D"]]
    if (not digits or digits != sorted(set(digits)) or digits[0] != 0
            or digits[-1] >= base or len(digits) >= base):
        raise BadCertificate("D must be proper, padded, sorted and contain zero")
    if base*len(digits)*p > 2000000:
        raise BadCertificate("cyclic AP audit cap")
    present = set(digits)
    for w in range(1, base):
        for a in digits:
            if all((a+j*w) % base in present for j in range(p)):
                raise BadCertificate("D contains a cyclic p-AP")
    lb, ub = block_enclosure(base, digits, s, depth)
    if fraction_obj(cert["lb"], "lb") != lb or fraction_obj(cert["ub"], "ub") != ub:
        raise BadCertificate("block enclosure mismatch")
    return {"valid": True, "lb": rational_object(lb), "ub": rational_object(ub)}


def signed_delta_fraction(obj):
    if not isinstance(obj, dict):
        raise BadCertificate("delta must be a rational object")
    exact_keys(obj, ("num", "den"), "delta")
    raw = obj["num"]
    if isinstance(raw, str) and raw.startswith("-"):
        numerator = -integer(raw[1:], "delta.num magnitude", 1)
    else:
        numerator = integer(raw, "delta.num", 0)
    denominator = integer(obj["den"], "delta.den", 1)
    value = Fraction(numerator, denominator)
    if value.numerator != numerator or value.denominator != denominator:
        raise BadCertificate("delta must be reduced")
    return value


def verify_head_tail(cert, base_dir=None):
    exact_keys(cert, ("schema", "k", "p", "D", "s", "L", "added", "removed", "delta", "pure_ref_sha256"), "head tail")
    if cert["schema"] != "erd169.head_tail.v1" or cert["k"] != "5" or cert["p"] != "5":
        raise BadCertificate("head tail requires p=k=5")
    s = integer(cert["s"], "s", 1)
    level = integer(cert["L"], "L", 1)
    if level > 9:
        raise BadCertificate("head level cap")
    if not isinstance(cert["D"], list):
        raise BadCertificate("D must be an array")
    digits = [integer(x, "D", 0) for x in cert["D"]]
    if not digits or digits != sorted(set(digits)) or digits[0] != 0 or digits[-1] > 4 or len(digits) == 5:
        raise BadCertificate("invalid padded digits")
    cutoff = s+5**level
    parsed = []
    for label in ("added", "removed"):
        if not isinstance(cert[label], list):
            raise BadCertificate("head delta must be arrays")
        values = [integer(x, label, 1) for x in cert[label]]
        if values != sorted(set(values)) or any(x >= cutoff for x in values):
            raise BadCertificate("head delta ordering/range")
        if any(padded_member(x-s, digits) != (label == "removed") for x in values):
            raise BadCertificate("head delta membership")
        parsed.append(set(values))
    added, removed = parsed
    if len(added)*5*cutoff > 20000000:
        raise BadCertificate("inconclusive: head audit cap")
    def member(x):
        return x > 0 and (x in added or (x not in removed and padded_member(x-s, digits)))
    for a in sorted(added):
        for i in range(5):
            for d in range(1, cutoff-1):
                start = a-i*d
                if start > 0 and all(member(start+j*d) for j in range(5)):
                    raise BadCertificate("head delta creates an AP")
        if not tail_compatible(a, s, level, digits):
            raise BadCertificate("head delta creates a cross-boundary AP")
    delta = sum((Fraction(1,x) for x in added), Fraction()) - sum((Fraction(1,x) for x in removed), Fraction())
    if signed_delta_fraction(cert["delta"]) != delta:
        raise BadCertificate("delta mismatch")
    if base_dir is None:
        raise BadCertificate("pure reference requires certificate directory")
    ref = resolve_digest(cert["pure_ref_sha256"], base_dir)
    verify_block_digit(ref)
    if ref["p"] != "5" or ref["block_len"] != "1" or ref["D"] != cert["D"] or ref["s"] != cert["s"]:
        raise BadCertificate("pure reference mismatch")
    return {"valid": True, "delta": rational_object(delta)}



def rigidity_candidates(level):
    """Independent aggregate carry-language decision; no stored scans trusted."""
    from functools import lru_cache
    @lru_cache(None)
    def transition(states, digit):
        targets = set()
        for carries in states:
            for d in range(5):
                values = tuple(c+digit+j*d for j,c in enumerate(carries,1))
                if all(v%5 != 4 for v in values):
                    targets.add(tuple(v//5 for v in values))
        return tuple(sorted(targets))
    @lru_cache(None)
    def accepts(states):
        queue = [(c,0) for c in states]
        seen = set(queue)
        for carries,mask in queue:
            if carries == (0,0,0,0) and mask == 15:
                return True
            for d in range(5):
                values = tuple(c+j*d for j,c in enumerate(carries,1))
                if any(v%5 == 4 for v in values):
                    continue
                high = mask
                for j,v in enumerate(values):
                    if v%5:
                        high |= 1<<j
                state = (tuple(v//5 for v in values),high)
                if state not in seen:
                    seen.add(state)
                    queue.append(state)
        return False
    result = []
    def walk(pos,states,x,place,outside):
        if pos == level:
            if outside and not accepts(states):
                result.append(x+1)
            return
        for digit in range(5):
            walk(pos+1,transition(states,digit),x+place*digit,place*5,outside or digit==4)
    walk(0,((0,0,0,0),),0,1,False)
    return sorted(result)


def rigidity_head_terms(terms, a, cutoff):
    return [x for x in terms if x != a and x < cutoff]


def verify_rigidity(cert, base_dir=None):
    exact_keys(cert,("schema","k","p","D","s","L","candidates","dual_arcs","min_nonempty_loss","pure_ref_sha256"),"rigidity")
    if (cert["schema"] != "erd169.rigidity.v1" or cert["k"] != "5" or cert["p"] != "5"
            or cert["s"] != "1" or cert["D"] != ["0","1","2","3"]):
        raise BadCertificate("rigidity parameter mismatch")
    level = integer(cert["L"],"L",1)
    if level>8:
        raise BadCertificate("rigidity level cap")
    if not isinstance(cert["candidates"],list) or len(cert["candidates"])>260:
        raise BadCertificate("candidate array cap")
    candidates = [integer(x,"candidate",1) for x in cert["candidates"]]
    if candidates != rigidity_candidates(level):
        raise BadCertificate("incomplete or invalid candidate list")
    cutoff = 1+5**level
    reflection = 3*(5**level-1)//4+2
    candidate_set = set(candidates)
    for a in candidates:
        if reflection-a not in candidate_set or not tail_compatible(a,1,level,[0,1,2,3]):
            raise BadCertificate("candidate tail/reflection mismatch")
    margin = fraction_obj(cert["min_nonempty_loss"],"min_nonempty_loss")
    if base_dir is None:
        raise BadCertificate("pure reference requires directory")
    ref = resolve_digest(cert["pure_ref_sha256"],base_dir)
    verify_block_digit(ref)
    if ref["p"]!="5" or ref["k"]!="5" or ref["block_len"]!="1" or ref["s"]!="1" or ref["D"]!=cert["D"]:
        raise BadCertificate("pure reference mismatch")
    if not isinstance(cert["dual_arcs"],list) or len(cert["dual_arcs"])>100000:
        raise BadCertificate("arc array cap")
    coverage = {a:Fraction() for a in candidates}
    load = {}
    seen = set()
    def bounded(value):
        if max(value.numerator.bit_length(),value.denominator.bit_length())>4096:
            raise BadCertificate("rigidity rational sum exceeds cap")
        return value
    for arc in cert["dual_arcs"]:
        if not isinstance(arc,dict):
            raise BadCertificate("arc must be object")
        exact_keys(arc,("a","start","diff","weight"),"arc")
        a = integer(arc["a"],"a",1)
        start = integer(arc["start"],"start",1)
        diff = integer(arc["diff"],"diff",1)
        # Any admissible arc has d < 5**L. This also bounds membership work.
        if a not in candidate_set or diff>=5**level or start>=cutoff:
            raise BadCertificate("arc range")
        identity = (a,start,diff)
        if identity in seen:
            raise BadCertificate("duplicate arc")
        seen.add(identity)
        terms = [start+j*diff for j in range(5)]
        if a not in terms or any(not padded_member(x-1,[0,1,2,3]) for x in terms if x!=a):
            raise BadCertificate("forged progression")
        head = rigidity_head_terms(terms,a,cutoff)
        if not head:
            raise BadCertificate("arc has no removable head point")
        weight = fraction_obj(arc["weight"],"weight")
        if weight<=0:
            raise BadCertificate("nonpositive weight")
        coverage[a] = bounded(coverage[a]+weight)
        for r in head:
            load[r] = bounded(load.get(r,Fraction())+weight)
            if load[r]>Fraction(1,r):
                raise BadCertificate("overloaded head capacity")
    for a,total in coverage.items():
        if total<bounded(Fraction(1,a)+margin):
            raise BadCertificate("insufficient candidate coverage")
    return {"valid":True,"max_delta":{"num":"0","den":"1"},"unique_optimum":margin>0}

def carry_ap_free(base, digits, k):
    """Finite positive-difference APs correspond exactly to accepting carry paths."""
    zero = (0,)*(k-1)
    queue = [(zero, False)]
    seen = set(queue)
    present = set(digits)
    for carries, nonzero in queue:
        for u in digits:
            for v in range(base):
                values = tuple(c+u+j*v for j,c in enumerate(carries,1))
                if any(x % base not in present for x in values):
                    continue
                nxt = (tuple(x//base for x in values), nonzero or v != 0)
                if nxt == (zero, True):
                    return False
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
    return True


def quantized_enclosure(base, digits, s, depth, q):
    # Streaming product avoids retaining the million-term depth-10 head.
    from itertools import product
    d, maximum = len(digits), max(digits)
    lb = ub = 0
    shell = base**(depth-1)
    for word in product(digits, repeat=depth):
        x = 0
        for digit in word:
            x = base*x+digit
        denominator = s+x
        lb += q//denominator
        ub += (q+denominator-1)//denominator
        if x >= shell:
            denominator = (base-d)*(base*x+maximum+s)
            numerator = q*base*d
            lb += numerator//denominator
            denominator = (base-d)*x
            ub += (q*d+denominator-1)//denominator
    return lb, ub


def verify_quantized_block(cert):
    exact_keys(cert,('schema','k','B','D','s','depth','Q','ap_mode','ap_params','lb_num','ub_num'),'quantized block')
    if cert['schema'] != 'erd169.quantized_block.v1':
        raise BadCertificate('wrong quantized schema')
    k = integer(cert['k'],'k',3)
    base = integer(cert['B'],'B',2)
    s = integer(cert['s'],'s',1)
    depth = integer(cert['depth'],'depth',1)
    q = integer(cert['Q'],'Q',1)
    lb = integer(cert['lb_num'],'lb_num',0)
    ub = integer(cert['ub_num'],'ub_num',0)
    if k>6 or base>128 or s>10000 or depth>20 or q!=10**60 or lb>ub:
        raise BadCertificate('quantized parameter cap/order')
    if not isinstance(cert['D'],list) or not 2<=len(cert['D'])<base:
        raise BadCertificate('quantized digit cap')
    digits = [integer(x,'D',0) for x in cert['D']]
    if digits != sorted(set(digits)) or digits[0]!=0 or digits[-1]>=base:
        raise BadCertificate('invalid quantized digits')
    if len(digits)**depth>1100000:
        raise BadCertificate('quantized enumeration cap')
    params = cert['ap_params']
    if not isinstance(params,dict):
        raise BadCertificate('AP params must be object')
    if cert['ap_mode']=='prime_power_cyclic':
        exact_keys(params,('p','block_len'),'AP params')
        p = integer(params['p'],'p',2)
        length = integer(params['block_len'],'block_len',1)
        if p>base or length>7 or k<p or any(p%j==0 for j in range(2,isqrt(p)+1)) or p**length!=base:
            raise BadCertificate('invalid prime power')
        present = set(digits)
        if any(all((a+j*w)%base in present for j in range(p)) for a in digits for w in range(1,base)):
            raise BadCertificate('cyclic AP')
    elif cert['ap_mode']=='carry_automaton':
        exact_keys(params,(),'AP params')
        if not carry_ap_free(base,digits,k):
            raise BadCertificate('carry automaton accepts an AP')
    else:
        raise BadCertificate('unknown AP proof mode')
    if quantized_enclosure(base,digits,s,depth,q)!=(lb,ub):
        raise BadCertificate('quantized endpoint mismatch')
    return {'valid':True,'lb_num':str(lb),'ub_num':str(ub)}


def verify_rigidity_v2(cert, base_dir=None):
    exact_keys(cert,("schema","k","p","D","s","L","candidates","dual_arcs","min_nonempty_loss","pure_ref_sha256"),"rigidity")
    if (cert["schema"] != "erd169.rigidity.v2" or cert["k"] != "5" or cert["p"] != "5"
            or cert["s"] != "1" or cert["D"] != ["0","1","2","3"]):
        raise BadCertificate("rigidity parameter mismatch")
    level = integer(cert["L"],"L",1)
    if level>9:
        raise BadCertificate("rigidity level cap")
    if not isinstance(cert["candidates"],list) or len(cert["candidates"])>2000:
        raise BadCertificate("candidate array cap")
    candidates = [integer(x,"candidate",1) for x in cert["candidates"]]
    if candidates != rigidity_candidates(level):
        raise BadCertificate("incomplete or invalid candidate list")
    cutoff = 1+5**level
    reflection = 3*(5**level-1)//4+2
    candidate_set = set(candidates)
    for a in candidates:
        if reflection-a not in candidate_set or not tail_compatible(a,1,level,[0,1,2,3]):
            raise BadCertificate("candidate tail/reflection mismatch")
    margin = fraction_obj(cert["min_nonempty_loss"],"min_nonempty_loss")
    if base_dir is None:
        raise BadCertificate("pure reference requires directory")
    ref = resolve_digest(cert["pure_ref_sha256"],base_dir)
    verify_block_digit(ref)
    if ref["p"]!="5" or ref["k"]!="5" or ref["block_len"]!="1" or ref["s"]!="1" or ref["D"]!=cert["D"]:
        raise BadCertificate("pure reference mismatch")
    if not isinstance(cert["dual_arcs"],list) or len(cert["dual_arcs"])>100000:
        raise BadCertificate("arc array cap")
    coverage = {a:Fraction() for a in candidates}
    load = {}
    seen = set()
    def bounded(value):
        if max(value.numerator.bit_length(),value.denominator.bit_length())>4096:
            raise BadCertificate("rigidity rational sum exceeds cap")
        return value
    for arc in cert["dual_arcs"]:
        if not isinstance(arc,dict):
            raise BadCertificate("arc must be object")
        exact_keys(arc,("a","start","diff","weight"),"arc")
        a = integer(arc["a"],"a",1)
        start = integer(arc["start"],"start",1)
        diff = integer(arc["diff"],"diff",1)
        # Any admissible arc has d < 5**L. This also bounds membership work.
        if a not in candidate_set or diff>=5**level or start>=cutoff:
            raise BadCertificate("arc range")
        identity = (a,start,diff)
        if identity in seen:
            raise BadCertificate("duplicate arc")
        seen.add(identity)
        terms = [start+j*diff for j in range(5)]
        if a not in terms or any(not padded_member(x-1,[0,1,2,3]) for x in terms if x!=a):
            raise BadCertificate("forged progression")
        head = rigidity_head_terms(terms,a,cutoff)
        if not head:
            raise BadCertificate("arc has no removable head point")
        weight = fraction_obj(arc["weight"],"weight")
        if weight<=0:
            raise BadCertificate("nonpositive weight")
        coverage[a] = bounded(coverage[a]+weight)
        for r in head:
            load[r] = bounded(load.get(r,Fraction())+weight)
            if load[r]>Fraction(1,r):
                raise BadCertificate("overloaded head capacity")
    for a,total in coverage.items():
        if total<bounded(Fraction(1,a)+margin):
            raise BadCertificate("insufficient candidate coverage")
    return {"valid":True,"max_delta":{"num":"0","den":"1"},"unique_optimum":margin>0}

def iroot(value, k):
    if value < 0 or k < 1:
        raise BadCertificate('root domain')
    if value < 2 or k == 1:
        return value
    x = 1 << ((value.bit_length()+k-1)//k)
    while True:
        y = ((k-1)*x+value//(x**(k-1)))//k
        if y >= x:
            return x
        x = y


def icbrt(value):
    return iroot(value,3)


def cubic_sieve_hits(s, lo, hi):
    """Hard-coded CRT necessary conditions, followed by exact inversion."""
    moduli = (17017,12673,47027)
    allowed = []
    for modulus in moduli:
        image = {(x*x*x-x)%modulus for x in range(modulus)}
        allowed.append(bytearray(s*s*(y*y*y-y)%modulus in image for y in range(modulus)))
    for n in range(lo,hi+1):
        y = n+2
        if not all(table[y%modulus] for modulus,table in zip(moduli,allowed)):
            continue
        target = s*s*(y*y*y-y)
        x = icbrt(target)+1
        if x*x*x-x == target and x-2 >= n+3:
            yield 3,n,x-2


def prime_power_sieve_hits(s, k_lo, k_hi, lo, hi, survivor_cap=200000):
    from collections import deque
    limit = hi+k_hi
    spf = list(range(limit+1))
    for p in range(2,isqrt(limit)+1):
        if spf[p] == p:
            for x in range(p*p,limit+1,p):
                if spf[x] == x:
                    spf[x] = p
    factors = [[] for _ in range(limit+1)]
    for t in range(2,limit+1):
        x = t
        while x>1:
            p = spf[x]
            q = 1
            while x%p==0:
                x//=p
                q*=p
            factors[t].append((p,q))
    survivors = 0
    for k in range(k_lo,k_hi+1):
        queue = deque()
        def add(t):
            score = max((t+q for p,q in factors[t] if p>k and s%p),default=0)
            while queue and queue[-1][1]<=score:
                queue.pop()
            queue.append((t,score))
        for t in range(lo+1,lo+k+1):
            add(t)
        product = 1
        for j in range(1,k+1):
            product *= lo+j
        for n in range(lo,hi+1):
            while queue and queue[0][0]<=n:
                queue.popleft()
            bound = queue[0][1]-k+1
            if bound<=0 or bound**k < s*s*(n+k)**k:
                survivors += 1
                if survivors>survivor_cap:
                    raise BadCertificate('prime power survivor cap')
                target = s*s*product
                r = iroot(target,k)
                left,right = max(n+k,r-k+1),r-1
                while left<=right:
                    m = (left+right)//2
                    value = 1
                    for j in range(1,k+1):
                        value *= m+j
                    if value == target:
                        yield k,n,m
                        break
                    if value<target:
                        left = m+1
                    else:
                        right = m-1
            if n<hi:
                product = product*(n+k+1)//(n+1)
                add(n+k+1)
    return survivors


def verify_sieve_null(cert):
    exact_keys(cert,('schema','s','k_lo','k_hi','n_lo','n_hi','method','domain'),'sieve null')
    if cert['schema']!='erd686.sieve_null.v1' or cert['domain']!='n>=1':
        raise BadCertificate('sieve schema/domain')
    s = integer(cert['s'],'s',2)
    kl = integer(cert['k_lo'],'k_lo',3)
    kh = integer(cert['k_hi'],'k_hi',3)
    lo = integer(cert['n_lo'],'n_lo',1)
    hi = integer(cert['n_hi'],'n_hi',1)
    if s>10000 or kl>kh or lo>hi:
        raise BadCertificate('sieve parameter cap/order')
    if cert['method']=='cubic_crt_icbrt':
        if kl!=3 or kh!=3 or hi>5000000:
            raise BadCertificate('cubic cap')
        hits = cubic_sieve_hits(s,lo,hi)
    elif cert['method']=='prime_power_exclusion':
        if kl<5 or kh>200 or hi>100000 or (kh-kl+1)*(hi-lo+1)>10000000:
            raise BadCertificate('prime power cap')
        hits = prime_power_sieve_hits(s,kl,kh,lo,hi)
    else:
        raise BadCertificate('unknown sieve method')
    try:
        k,n,m = next(hits)
    except StopIteration as done:
        return {'valid':True,'survivors':str(done.value) if done.value is not None else 'not recorded'}
    raise BadCertificate(f'sieve hit k={k} n={n} m={m}; emit erd686.rep.v1')


def cyclic_progressions(modulus):
    # Store a canonical (start,difference) for each distinct cyclic AP set.
    edges = {}
    for a in range(modulus):
        for d in range(1,modulus):
            terms = frozenset((a+j*d)%modulus for j in range(5))
            edges.setdefault(terms,(a,d))
    return edges


def verify_cyclic_max(cert):
    exact_keys(cert,('schema','modulus','p','max_cardinality','witness','mode','proof'),'cyclic max')
    if cert['schema']!='erd169.cyclic_max.v1' or cert['p']!='5' or cert['modulus']!='25' or cert['mode']!='direct_bnb':
        raise BadCertificate('unsupported cyclic proof mode; Z125 remains unresolved')
    maximum = integer(cert['max_cardinality'],'maximum',0)
    if maximum>25 or not isinstance(cert['witness'],list) or len(cert['witness'])!=maximum:
        raise BadCertificate('cyclic witness cap')
    witness = [integer(x,'witness',0) for x in cert['witness']]
    if witness!=sorted(set(witness)) or any(x>=25 for x in witness):
        raise BadCertificate('cyclic witness range/order')
    edges = cyclic_progressions(25)
    if any(edge<=set(witness) for edge in edges):
        raise BadCertificate('cyclic witness has AP')
    nodes = cert['proof']
    if not isinstance(nodes,list) or not 1<=len(nodes)<=1000000:
        raise BadCertificate('cyclic tree cap')
    index = 0
    full = set(range(25))
    def parse_ap(pair):
        if not isinstance(pair,list) or len(pair)!=2:
            raise BadCertificate('cyclic AP pair')
        a,d = [integer(x,'AP',0) for x in pair]
        if a>=25 or not 1<=d<25:
            raise BadCertificate('cyclic AP range')
        return {(a+j*d)%25 for j in range(5)}
    def visit(selected,excluded):
        nonlocal index
        if index>=len(nodes):
            raise BadCertificate('truncated cyclic tree')
        node = nodes[index]; index+=1
        if not isinstance(node,dict):
            raise BadCertificate('cyclic node must be object')
        op = node.get('op')
        undecided = full-selected-excluded
        if op=='branch':
            exact_keys(node,('op','j'),'cyclic branch')
            j = integer(node['j'],'j',0)
            if j not in undecided:
                raise BadCertificate('cyclic repeated branch')
            visit(selected|{j},excluded)
            visit(selected,excluded|{j})
        elif op=='conflict':
            exact_keys(node,('op','ap'),'cyclic conflict')
            if not parse_ap(node['ap'])<=selected:
                raise BadCertificate('forged cyclic conflict')
        elif op=='prune':
            exact_keys(node,('op','aps'),'cyclic prune')
            if not isinstance(node['aps'],list) or len(node['aps'])>25:
                raise BadCertificate('cyclic packing cap')
            occupied = set()
            for pair in node['aps']:
                edge = parse_ap(pair)
                active = edge & undecided
                if edge&excluded or not active or edge&occupied:
                    raise BadCertificate('invalid cyclic packing')
                occupied |= edge
            if len(selected)+len(undecided)-len(node['aps'])>maximum:
                raise BadCertificate('invalid cyclic upper bound')
        else:
            raise BadCertificate('unknown cyclic node')
    visit(set(),set())
    if index!=len(nodes):
        raise BadCertificate('unused cyclic nodes')
    return {'valid':True,'optimal':True,'max_cardinality':str(maximum)}


def dense_z25_fibres(threshold):
    masks = [sum(1<<x for x in edge) for edge in cyclic_progressions(25)]
    incidence = [[e for e in masks if e>>j&1] for j in range(25)]
    def visit(selected,todo):
        if selected.bit_count()+todo.bit_count()<threshold:
            return
        if not todo:
            yield selected
            return
        bit = todo&-todo
        j = bit.bit_length()-1
        rest = todo^bit
        chosen = selected|bit
        if not any(e&chosen==e for e in incidence[j]):
            forced = 0
            for e in incidence[j]:
                missing = e&~chosen
                if missing.bit_count()==1:
                    forced |= missing
            yield from visit(chosen,rest&~forced)
        yield from visit(selected,rest)
    yield from visit(0,(1<<25)-1)


def verify_h0_cyclic_max(cert,base_dir):
    exact_keys(cert,('schema','modulus','p','max_cardinality','witness','mode','proof'),'H0 max')
    if cert['schema']!='erd169.cyclic_max.v1' or cert['modulus']!='125' or cert['p']!='5' or cert['mode']!='h0_orbit_bnb':
        raise BadCertificate('wrong H0 parameters')
    maximum = integer(cert['max_cardinality'],'maximum',0)
    if not 64<=maximum<=80 or not isinstance(cert['witness'],list) or len(cert['witness'])!=maximum:
        raise BadCertificate('H0 witness cap')
    witness = [integer(x,'witness',0) for x in cert['witness']]
    if witness!=sorted(set(witness)) or witness[-1]>=125:
        raise BadCertificate('invalid H0 witness')
    proof = cert['proof']
    if not isinstance(proof,dict):
        raise BadCertificate('H0 proof must be object')
    exact_keys(proof,('z25_ref_sha256','orbits'),'H0 proof')
    orbits = proof['orbits']
    if not isinstance(orbits,list) or not 1<=len(orbits)<=1000:
        raise BadCertificate('H0 orbit cap')
    total = 0
    threshold = (maximum+5)//5
    for orbit in orbits:
        if not isinstance(orbit,dict):
            raise BadCertificate('H0 orbit must be object')
        exact_keys(orbit,('fibre','tree'),'H0 orbit')
        if not isinstance(orbit['fibre'],list) or not threshold<=len(orbit['fibre'])<=16:
            raise BadCertificate('H0 fibre cap')
        if not isinstance(orbit['tree'],list) or not orbit['tree']:
            raise BadCertificate('H0 tree array')
        total += len(orbit['tree'])
        if total>1000000:
            raise BadCertificate('H0 total node cap')
    if base_dir is None:
        raise BadCertificate('H0 reference requires directory')
    ref = resolve_digest(proof['z25_ref_sha256'],base_dir)
    verify_cyclic_max(ref)
    if ref['modulus']!='25' or ref['max_cardinality']!='16':
        raise BadCertificate('H0 requires Z25 maximum 16')
    edges = cyclic_progressions(125)
    present = set(witness)
    if any(edge<=present for edge in edges):
        raise BadCertificate('H0 witness has AP')
    coverage = set()
    representatives = set()
    units = [a for a in range(25) if gcd(a,25)==1]
    parsed = []
    for orbit in orbits:
        fibre = [integer(x,'fibre',0) for x in orbit['fibre']]
        if fibre!=sorted(set(fibre)) or fibre[-1]>=25:
            raise BadCertificate('H0 fibre range/order')
        if any(edge<=set(fibre) for edge in cyclic_progressions(25)):
            raise BadCertificate('H0 fibre contains AP')
        mask = sum(1<<x for x in fibre)
        if mask in representatives:
            raise BadCertificate('duplicate H0 representative')
        representatives.add(mask)
        for a in units:
            for c in range(25):
                coverage.add(sum(1<<((a*x+c)%25) for x in fibre))
        parsed.append((fibre,orbit['tree']))
    if any(mask not in coverage for mask in dense_z25_fibres(threshold)):
        raise BadCertificate('incomplete H0 affine orbit coverage')
    full = set(range(125))
    cosets = [{a+25*j for j in range(5)} for a in range(25)]
    fibres = [{a+5*j for j in range(25)} for a in range(5)]
    for fibre,nodes in parsed:
        selected0 = {5*y for y in fibre}
        excluded0 = {5*y for y in range(25)}-selected0
        index = 0
        def ap(pair):
            if not isinstance(pair,list) or len(pair)!=2:
                raise BadCertificate('H0 AP pair')
            a,d = [integer(x,'AP',0) for x in pair]
            if a>=125 or not 1<=d<125:
                raise BadCertificate('H0 AP range')
            return {(a+j*d)%125 for j in range(5)}
        def visit(selected,excluded):
            nonlocal index
            if index>=len(nodes):
                raise BadCertificate('truncated H0 tree')
            node = nodes[index]
            index+=1
            if not isinstance(node,dict):
                raise BadCertificate('H0 node must be object')
            undecided = full-selected-excluded
            op = node.get('op')
            if op=='branch':
                exact_keys(node,('op','j'),'H0 branch')
                j = integer(node['j'],'j',0)
                if j not in undecided:
                    raise BadCertificate('H0 branch violates fixed fibre')
                visit(selected|{j},excluded)
                visit(selected,excluded|{j})
            elif op=='conflict':
                exact_keys(node,('op','ap'),'H0 conflict')
                if not ap(node['ap'])<=selected:
                    raise BadCertificate('forged H0 conflict')
            elif op=='prune':
                bound = node.get('bound')
                if bound in ('coset','fibre'):
                    exact_keys(node,('op','bound'),'H0 bound')
                    parts,cap = (cosets,4) if bound=='coset' else (fibres,16)
                    upper = len(selected)+sum(min(len(part&undecided),cap-len(part&selected)) for part in parts)
                elif bound=='packing':
                    exact_keys(node,('op','bound','aps'),'H0 packing')
                    if not isinstance(node['aps'],list) or len(node['aps'])>125:
                        raise BadCertificate('H0 packing cap')
                    occupied = set()
                    for pair in node['aps']:
                        edge = ap(pair)
                        active = edge&undecided
                        if edge&excluded or not active or edge&occupied:
                            raise BadCertificate('invalid H0 packing')
                        occupied |= edge
                    upper = len(selected)+len(undecided)-len(node['aps'])
                else:
                    raise BadCertificate('unknown H0 bound')
                if upper>maximum:
                    raise BadCertificate('invalid H0 prune bound')
            else:
                raise BadCertificate('unknown H0 node')
        visit(selected0,excluded0)
        if index!=len(nodes):
            raise BadCertificate('unused H0 nodes')
    return {'valid':True,'optimal':True,'max_cardinality':str(maximum)}


def _replay_h0_v2(nodes, selected0, excluded0, maximum, full, cosets, fibres, dominance_cap):
    index = 0
    def ap(pair):
        if not isinstance(pair,list) or len(pair)!=2:
            raise BadCertificate('H0 AP pair')
        a,d = [integer(x,'AP',0) for x in pair]
        if a>=125 or not 1<=d<125:
            raise BadCertificate('H0 AP range')
        return {(a+j*d)%125 for j in range(5)}
    def visit(selected,excluded):
        nonlocal index
        if index>=len(nodes):
            raise BadCertificate('truncated H0 tree')
        node = nodes[index]
        index+=1
        if not isinstance(node,dict):
            raise BadCertificate('H0 node must be object')
        undecided = full-selected-excluded
        op = node.get('op')
        if op=='branch':
            exact_keys(node,('op','j'),'H0 branch')
            j = integer(node['j'],'j',0)
            if j not in undecided:
                raise BadCertificate('H0 branch violates fixed fibre')
            visit(selected|{j},excluded)
            visit(selected,excluded|{j})
        elif op=='force':
            exact_keys(node,('op','j','ap'),'H0 force')
            j = integer(node['j'],'j',0)
            edge = ap(node['ap'])
            if j not in undecided or j not in edge or not edge-{j}<=selected:
                raise BadCertificate('invalid H0 force')
            visit(selected,excluded|{j})
        elif op=='conflict':
            exact_keys(node,('op','ap'),'H0 conflict')
            if not ap(node['ap'])<=selected:
                raise BadCertificate('forged H0 conflict')
        elif op=='prune':
            bound = node.get('bound')
            if bound=='dominance':
                exact_keys(node,('op','bound'),'H0 dominance')
                cap = dominance_cap
                counts = [len(part&selected) for part in fibres]
                upper = 0 if any(n>cap for n in counts) else len(selected)+sum(
                    min(len(part&undecided),cap-n) for part,n in zip(fibres,counts))
            elif bound in ('coset','fibre'):
                exact_keys(node,('op','bound'),'H0 bound')
                parts,cap = (cosets,4) if bound=='coset' else (fibres,16)
                upper = len(selected)+sum(min(len(part&undecided),cap-len(part&selected)) for part in parts)
            elif bound=='packing':
                exact_keys(node,('op','bound','aps'),'H0 packing')
                if not isinstance(node['aps'],list) or len(node['aps'])>125:
                    raise BadCertificate('H0 packing cap')
                occupied = set()
                for pair in node['aps']:
                    edge = ap(pair)
                    active = edge&undecided
                    if edge&excluded or not active or active&occupied:
                        raise BadCertificate('invalid H0 packing')
                    occupied |= active
                upper = len(selected)+len(undecided)-len(node['aps'])
            else:
                raise BadCertificate('unknown H0 bound')
            if upper>maximum:
                raise BadCertificate('invalid H0 prune bound')
        else:
            raise BadCertificate('unknown H0 node')
    visit(selected0,excluded0)
    if index!=len(nodes):
        raise BadCertificate('unused H0 nodes')


def verify_h0_cyclic_max_v2(cert,base_dir):
    """Densest-fibre normalization is valid: translate a densest class to H0,
    then lift y -> ay+c on Z25 to x -> a'x+5c on Z125. These maps
    permute residue classes, preserving H0 as a densest fibre. Thus each
    searched completion may be restricted to fibre sizes <= len(F0).
    """
    exact_keys(cert,('schema','modulus','p','max_cardinality','witness','mode','proof'),'H0 max')
    if cert['schema']!='erd169.cyclic_max.v2' or cert['modulus']!='125' or cert['p']!='5' or cert['mode']!='h0_orbit_bnb':
        raise BadCertificate('wrong H0 parameters')
    maximum = integer(cert['max_cardinality'],'maximum',0)
    if not 64<=maximum<=80 or not isinstance(cert['witness'],list) or len(cert['witness'])!=maximum:
        raise BadCertificate('H0 witness cap')
    witness = [integer(x,'witness',0) for x in cert['witness']]
    if witness!=sorted(set(witness)) or witness[-1]>=125:
        raise BadCertificate('invalid H0 witness')
    proof = cert['proof']
    if not isinstance(proof,dict):
        raise BadCertificate('H0 proof must be object')
    exact_keys(proof,('z25_ref_sha256','orbits'),'H0 proof')
    orbits = proof['orbits']
    if not isinstance(orbits,list) or not (0 if (maximum+5)//5>=17 else 1)<=len(orbits)<=1000:
        raise BadCertificate('H0 orbit cap')
    total = 0
    threshold = (maximum+5)//5
    for orbit in orbits:
        if not isinstance(orbit,dict):
            raise BadCertificate('H0 orbit must be object')
        exact_keys(orbit,('fibre','tree'),'H0 orbit')
        if not isinstance(orbit['fibre'],list) or not threshold<=len(orbit['fibre'])<=16:
            raise BadCertificate('H0 fibre cap')
        if not isinstance(orbit['tree'],list) or not orbit['tree']:
            raise BadCertificate('H0 tree array')
        total += len(orbit['tree'])
        if total>1000000:
            raise BadCertificate('H0 total node cap')
    if base_dir is None:
        raise BadCertificate('H0 reference requires directory')
    ref = resolve_digest(proof['z25_ref_sha256'],base_dir)
    verify_cyclic_max(ref)
    if ref['modulus']!='25' or ref['max_cardinality']!='16':
        raise BadCertificate('H0 requires Z25 maximum 16')
    edges = cyclic_progressions(125)
    present = set(witness)
    if any(edge<=present for edge in edges):
        raise BadCertificate('H0 witness has AP')
    coverage = set()
    representatives = set()
    units = [a for a in range(25) if gcd(a,25)==1]
    parsed = []
    for orbit in orbits:
        fibre = [integer(x,'fibre',0) for x in orbit['fibre']]
        if fibre!=sorted(set(fibre)) or fibre[-1]>=25:
            raise BadCertificate('H0 fibre range/order')
        if any(edge<=set(fibre) for edge in cyclic_progressions(25)):
            raise BadCertificate('H0 fibre contains AP')
        mask = sum(1<<x for x in fibre)
        if mask in representatives:
            raise BadCertificate('duplicate H0 representative')
        representatives.add(mask)
        for a in units:
            for c in range(25):
                coverage.add(sum(1<<((a*x+c)%25) for x in fibre))
        parsed.append((fibre,orbit['tree']))
    if any(mask not in coverage for mask in dense_z25_fibres(threshold)):
        raise BadCertificate('incomplete H0 affine orbit coverage')
    full = set(range(125))
    cosets = [{a+25*j for j in range(5)} for a in range(25)]
    fibres = [{a+5*j for j in range(25)} for a in range(5)]
    for fibre,nodes in parsed:
        selected0 = {5*y for y in fibre}
        excluded0 = {5*y for y in range(25)}-selected0
        _replay_h0_v2(nodes,selected0,excluded0,maximum,full,cosets,fibres,len(fibre))
    return {'valid':True,'optimal':True,'max_cardinality':str(maximum)}


def verify_pell_batch(cert):
    exact_keys(cert,('schema','k','N_min','N_max','domain','rows'),'Pell batch')
    if cert['schema']!='erd686.pell_batch.v1' or cert['k']!='2' or cert['domain']!='n>=1':
        raise BadCertificate('wrong Pell parameters')
    lo = integer(cert['N_min'],'N_min',2)
    hi = integer(cert['N_max'],'N_max',2)
    if not lo<=hi<=10000 or not isinstance(cert['rows'],list):
        raise BadCertificate('Pell range/rows')
    expected = [n for n in range(lo,hi+1) if isqrt(n)**2!=n]
    if len(cert['rows'])!=len(expected):
        raise BadCertificate('Pell coverage')
    for row,expected_n in zip(cert['rows'],expected):
        if not isinstance(row,dict):
            raise BadCertificate('Pell row must be object')
        exact_keys(row,('N','u','v','n','m'),'Pell row')
        N,u,v,n,m = [integer(row[key],key,1) for key in ('N','u','v','n','m')]
        if max(N,u,v,n,m).bit_length()>256:
            raise BadCertificate('Pell 256-bit cap')
        if N!=expected_n:
            raise BadCertificate('Pell coverage')
        if u<2 or u*u-N*v*v!=1:
            raise BadCertificate('Pell norm')
        U,V = 2*u*u-1,2*u*v
        if 2*n!=U+V-3 or 2*m!=U+N*V-3 or m<n+2:
            raise BadCertificate('Pell coordinates/domain')
        if (m+1)*(m+2)!=N*(n+1)*(n+2):
            raise BadCertificate('Pell product equality')
    return {'valid':True,'k':2,'N_min':lo,'N_max':hi,'count':len(expected),
            'novelty_tags':['NONSQUARE_PELL_KNOWN']}


def verify_certificate(cert: Mapping[str, Any], base_dir=None) -> Dict[str, Any]:
    """Verify one standalone certificate and return a structured result."""

    if not isinstance(cert, dict):
        raise BadCertificate("certificate is not an object")
    schema = cert.get("schema")
    if schema == "erd686.pell_batch.v1":
        return verify_pell_batch(cert)
    if schema == "erd169.quantized_block.v1":
        return verify_quantized_block(cert)
    if schema == "erd169.rigidity.v2":
        return verify_rigidity_v2(cert, base_dir)
    if schema == "erd169.cyclic_max.v2":
        return verify_h0_cyclic_max_v2(cert,base_dir)
    if schema == "erd169.cyclic_max.v1":
        if cert.get("mode") == "h0_orbit_bnb":
            return verify_h0_cyclic_max(cert,base_dir)
        return verify_cyclic_max(cert)
    if schema == "erd169.block_digit.v1":
        return verify_block_digit(cert)
    if schema == "erd169.head_tail.v1":
        return verify_head_tail(cert, base_dir)
    if schema == "erd169.rigidity.v1":
        return verify_rigidity(cert, base_dir)
    if schema == "erd169.bnb.v1":
        return replay(cert)
    if schema == "erd169.finite.v1":
        return verify_finite(cert)
    if schema == "erd169.digitset.v1":
        return verify_digitset(cert)
    if schema == "erd169.prefix_opt.v1":
        return verify_prefix(cert, base_dir)
    if schema == "erd686.sieve_null.v1":
        return verify_sieve_null(cert)
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
        return verify_certificate(cert, base_dir)
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
        with digest_run(manifest_path.parent):
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
