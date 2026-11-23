"""Independent verifier for Erdős Problem 169 certificates.

The verifier is intentionally conservative: every reported rational value is
recomputed with :class:`fractions.Fraction`, and no floating-point operation is
used anywhere in this module.
"""

from __future__ import annotations

from fractions import Fraction
from math import isqrt
from .standalone_verify import resolve_digest
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from .common import (
    CertificateError,
    canonical_fraction_object,
    canonical_integer,
    canonical_sha256,
    find_k_ap,
    fraction_object,
    require_array,
    require_exact_keys,
    require_object,
    result,
)

FINITE_SCHEMA = "erd169.finite.v1"
PREFIX_SCHEMA = "erd169.prefix_opt.v1"
DIGITSET_SCHEMA = "erd169.digitset.v1"


def _finite_keys(certificate: Mapping[str, Any]) -> None:
    require_exact_keys(
        certificate,
        ("schema", "k", "N", "members", "score"),
        "finite certificate",
    )
    if certificate["schema"] != FINITE_SCHEMA:
        raise CertificateError(f"expected schema {FINITE_SCHEMA!r}")


def validate_finite(certificate: Mapping[str, Any]) -> Dict[str, Any]:
    certificate = require_object(certificate, "finite certificate")
    _finite_keys(certificate)
    k = canonical_integer(certificate["k"], "k", 3)
    if certificate["N"] is None:
        upper = None
    elif isinstance(certificate["N"], str):
        upper = canonical_integer(certificate["N"], "N", 1)
    else:
        raise CertificateError("N must be a canonical decimal string or null")
    raw_members = require_array(certificate["members"], "members")
    members: List[int] = []
    previous = 0
    for index, raw_member in enumerate(raw_members):
        member = canonical_integer(raw_member, f"members[{index}]", 1)
        if member <= previous:
            raise CertificateError("members must be strictly increasing")
        if upper is not None and member > upper:
            raise CertificateError("member exceeds N")
        members.append(member)
        previous = member

    progression = find_k_ap(members, k)
    if progression is not None:
        start, difference = progression
        raise CertificateError(
            f"members contain the {k}-term AP beginning at {start} with difference {difference}"
        )

    exact_score = sum((Fraction(1, member) for member in members), Fraction(0, 1))
    claimed_score = canonical_fraction_object(certificate["score"], "score")
    if claimed_score != exact_score:
        raise CertificateError(
            f"score mismatch: claimed {claimed_score}, recomputed {exact_score}"
        )
    return {
        "members": members,
        "score": exact_score,
        "k": k,
        "N": upper,
    }


def verify_finite(certificate: Mapping[str, Any]) -> Dict[str, Any]:
    """Raise :class:`CertificateError` for an invalid finite certificate.

    This low-level verifier intentionally propagates validation failures so
    solvers and tests cannot accidentally treat a false certificate as valid.
    The high-level dispatcher ``verify_certificate`` below returns a structured
    result for callers that prefer it.
    """

    details = validate_finite(certificate)
    return {
        "valid": True,
        "score": fraction_object(details["score"]),
        "members": [str(member) for member in details["members"]],
    }


def validate_prefix(certificate: Mapping[str, Any]) -> Dict[str, Any]:
    certificate = require_object(certificate, "prefix certificate")
    require_exact_keys(
        certificate,
        (
            "schema",
            "k",
            "N",
            "witness_sha256",
            "proof_sha256",
            "proof_format",
            "tie_policy",
        ),
        "prefix certificate",
    )
    if certificate["schema"] != PREFIX_SCHEMA:
        raise CertificateError(f"expected schema {PREFIX_SCHEMA!r}")
    k = canonical_integer(certificate["k"], "k", 3)
    upper = canonical_integer(certificate["N"], "N", 1)
    witness_digest = canonical_sha256(certificate["witness_sha256"], "witness_sha256")
    proof_digest = canonical_sha256(certificate["proof_sha256"], "proof_sha256")
    if certificate["proof_format"] != "erd169.bnb.v1":
        raise CertificateError("proof_format must be erd169.bnb.v1")
    if not isinstance(certificate["tie_policy"], str) or not certificate["tie_policy"]:
        raise CertificateError("tie_policy must be a non-empty string")
    return {
        "k": k,
        "N": upper,
        "witness_sha256": witness_digest,
        "proof_sha256": proof_digest,
        "tie_policy": certificate["tie_policy"],
    }


def verify_prefix(certificate, base_dir=None):
    from .standalone_verify import verify_prefix as independent_prefix, resolve_digest
    from .proof_replay import replay_proof
    validate_prefix(certificate)
    try:
        answer = independent_prefix(certificate, base_dir)
        checked = replay_proof(resolve_digest(certificate["proof_sha256"], base_dir),
                               resolve_digest(certificate["witness_sha256"], base_dir))
        if not checked.get("valid"):
            raise CertificateError(str(checked))
        return answer
    except ValueError as exc:
        raise CertificateError(str(exc)) from exc


def _is_k_ap_free(values: Iterable[int], k: int) -> bool:
    return find_k_ap(values, k) is None


def _digit_sum_candidates(
    base: int, digits: List[int], positions: int
) -> Iterable[int]:
    """Yield base-base integers whose *padded* positions all belong to digits."""

    if positions == 0:
        yield 0
        return
    for tail in _digit_sum_candidates(base, digits, positions - 1):
        for digit in digits:
            yield digit * (base ** (positions - 1)) + tail


def _head_lower_bound(
    base: int, digits: List[int], s: int, level: int, q: int
) -> Fraction:
    """Recompute the certified head for all positive integers below ``B**level``.

    ``level`` is the number of base-``base`` positions in a positive number,
    while the zero integer is handled separately.  Leading zeroes are not
    counted as additional digit lengths, so each integer occurs exactly once.
    """

    total = Fraction(0, 1)
    count = 0
    nonzero = [digit for digit in digits if digit != 0]
    if 0 in digits:
        # Zero is the level-0 number and is included exactly when its only
        # base-B digit belongs to D.
        count += 1
        total += Fraction(q // s, q)
    for length in range(1, level):
        combinations = len(nonzero) * len(digits) ** (length - 1)
        if count + combinations > 2_000_000:
            raise CertificateError("digit head exceeds the 2,000,000-element cap")
        for leading in nonzero:
            for tail in _digit_sum_candidates(base, digits, length - 1):
                value = leading * base ** (length - 1) + tail
                count += 1
                total += Fraction(q // (s + value), q)
    if count != (1 if 0 in digits else 0) + sum(
        len(nonzero) * len(digits) ** (length - 1)
        for length in range(1, level)
    ):
        raise CertificateError("internal digit enumeration count mismatch")
    return total


def _tail_lower_bound(
    base: int, digits: List[int], s: int, level: int
) -> Fraction:
    """Compute the exact geometric lower bound from the ratified digit lemma.

    At level ell there are d^ell admissible digit strings.  Every such x is at
    most max(D)*(B^ell-1)/(B-1).  Therefore the level contribution is at
    least d^ell(B-1)/(B^ell*((B-1)s/B^L+max(D))).  Summing ell >= L is a
    geometric series with exact rational arithmetic.
    """

    digit_count = len(digits)
    max_digit = max(digits)
    if digit_count >= base:
        raise CertificateError("digit tail does not converge")
    constant = Fraction(base - 1, 1) / (
        Fraction((base - 1) * s, base**level) + max_digit
    )
    ratio = Fraction(digit_count, base)
    # The number of positive base-B integers having exactly l digits and all
    # digits in D is alpha*d**(l-1), where alpha=d-1 if zero is in D and d
    # otherwise.  This distinction matters for the common set {0,1}.
    alpha = digit_count - 1 if 0 in digits else digit_count
    geometric = (
        Fraction(alpha, 1)
        * digit_count ** (level - 1)
        / base**level
        / (1 - ratio)
    )
    return constant * geometric


def validate_digitset(certificate: Mapping[str, Any]) -> Dict[str, Any]:
    certificate = require_object(certificate, "digit-set certificate")
    require_exact_keys(
        certificate,
        (
            "schema",
            "k",
            "B",
            "D",
            "s",
            "L",
            "Q",
            "head_lb",
            "tail_lb",
        ),
        "digit-set certificate",
    )
    if certificate["schema"] != DIGITSET_SCHEMA:
        raise CertificateError(f"expected schema {DIGITSET_SCHEMA!r}")
    k = canonical_integer(certificate["k"], "k", 3)
    base = canonical_integer(certificate["B"], "B", 2)
    s = canonical_integer(certificate["s"], "s", 1)
    level = canonical_integer(certificate["L"], "L", 1)
    q = canonical_integer(certificate["Q"], "Q", 1)

    raw_digits = require_array(certificate["D"], "D")
    digits: List[int] = []
    previous = -1
    for index, raw_digit in enumerate(raw_digits):
        digit = canonical_integer(raw_digit, f"D[{index}]", 0)
        if digit >= base:
            raise CertificateError("D must be contained in [0, B)")
        if digit <= previous:
            raise CertificateError("D must be strictly increasing")
        digits.append(digit)
        previous = digit
    if len(digits) < 2:
        raise CertificateError("D must contain at least two digits")
    if 2 * max(digits) >= base:
        raise CertificateError("digit-set condition 2*max(D) < B failed")
    progression = find_k_ap(digits, k)
    if progression is not None:
        start, difference = progression
        raise CertificateError(
            f"D contains a {k}-term AP beginning at {start} with difference {difference}"
        )

    if level < 1:
        raise CertificateError("L must be at least 1")
    if q < 1:
        raise CertificateError("Q must be at least 1")
    if level > 20 or len(digits)**(level-1) > 2000000:
        raise CertificateError("digit enumeration cap")
    exact_head = _head_lower_bound(base, digits, s, level, q)
    exact_tail = _tail_lower_bound(base, digits, s, level)
    claimed_head = canonical_fraction_object(certificate["head_lb"], "head_lb")
    claimed_tail = canonical_fraction_object(certificate["tail_lb"], "tail_lb")
    if claimed_head != exact_head:
        raise CertificateError(
            f"head_lb mismatch: claimed {claimed_head}, recomputed {exact_head}"
        )
    if claimed_tail != exact_tail:
        raise CertificateError(
            f"tail_lb mismatch: claimed {claimed_tail}, recomputed {exact_tail}"
        )
    return {
        "k": k,
        "B": base,
        "D": digits,
        "s": s,
        "L": level,
        "Q": q,
        "head_lb": exact_head,
        "tail_lb": exact_tail,
    }


def verify_digitset(certificate: Mapping[str, Any]) -> Dict[str, Any]:
    details = validate_digitset(certificate)
    return {
        "valid": True,
        "head_lb": fraction_object(details["head_lb"]),
        "tail_lb": fraction_object(details["tail_lb"]),
    }


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
                    raise CertificateError("inconclusive: carry state cap")
                seen.add(state)
                queue.append(state)
    return True


def block_enclosure(base, digits, s, depth):
    if not 1 <= depth <= 20 or len(digits)**depth > 2000000:
        raise CertificateError("block enumeration cap")
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
            raise CertificateError("exact enclosure exceeds 4096-bit rational cap")
    return head+lower_tail, head+upper_tail


def verify_block_digit(cert):
    require_exact_keys(cert, ("schema", "k", "p", "block_len", "D", "s", "depth", "lb", "ub"), "block digit")
    if cert["schema"] != "erd169.block_digit.v1":
        raise CertificateError("wrong block digit schema")
    p = canonical_integer(cert["p"], "p", 2)
    k = canonical_integer(cert["k"], "k", 3)
    length = canonical_integer(cert["block_len"], "block_len", 1)
    depth = canonical_integer(cert["depth"], "depth", 1)
    s = canonical_integer(cert["s"], "s", 1)
    if p > 127 or k > 256 or length > 4:
        raise CertificateError("block parameter cap")
    if any(p % q == 0 for q in range(2, isqrt(p)+1)) or k < p:
        raise CertificateError("p must be prime and k >= p")
    base = p**length
    if not isinstance(cert["D"], list):
        raise CertificateError("D must be an array")
    digits = [canonical_integer(x, "D", 0) for x in cert["D"]]
    if (not digits or digits != sorted(set(digits)) or digits[0] != 0
            or digits[-1] >= base or len(digits) >= base):
        raise CertificateError("D must be proper, padded, sorted and contain zero")
    if base*len(digits)*p > 2000000:
        raise CertificateError("cyclic AP audit cap")
    present = set(digits)
    for w in range(1, base):
        for a in digits:
            if all((a+j*w) % base in present for j in range(p)):
                raise CertificateError("D contains a cyclic p-AP")
    lb, ub = block_enclosure(base, digits, s, depth)
    if canonical_fraction_object(cert["lb"], "lb") != lb or canonical_fraction_object(cert["ub"], "ub") != ub:
        raise CertificateError("block enclosure mismatch")
    return {"valid": True, "lb": fraction_object(lb), "ub": fraction_object(ub)}


def signed_delta_fraction(obj):
    if not isinstance(obj, dict):
        raise CertificateError("delta must be a rational object")
    require_exact_keys(obj, ("num", "den"), "delta")
    raw = obj["num"]
    if isinstance(raw, str) and raw.startswith("-"):
        numerator = -canonical_integer(raw[1:], "delta.num magnitude", 1)
    else:
        numerator = canonical_integer(raw, "delta.num", 0)
    denominator = canonical_integer(obj["den"], "delta.den", 1)
    value = Fraction(numerator, denominator)
    if value.numerator != numerator or value.denominator != denominator:
        raise CertificateError("delta must be reduced")
    return value


def verify_head_tail(cert, base_dir=None):
    require_exact_keys(cert, ("schema", "k", "p", "D", "s", "L", "added", "removed", "delta", "pure_ref_sha256"), "head tail")
    if cert["schema"] != "erd169.head_tail.v1" or cert["k"] != "5" or cert["p"] != "5":
        raise CertificateError("head tail requires p=k=5")
    s = canonical_integer(cert["s"], "s", 1)
    level = canonical_integer(cert["L"], "L", 1)
    if level > 9:
        raise CertificateError("head level cap")
    if not isinstance(cert["D"], list):
        raise CertificateError("D must be an array")
    digits = [canonical_integer(x, "D", 0) for x in cert["D"]]
    if not digits or digits != sorted(set(digits)) or digits[0] != 0 or digits[-1] > 4 or len(digits) == 5:
        raise CertificateError("invalid padded digits")
    cutoff = s+5**level
    parsed = []
    for label in ("added", "removed"):
        if not isinstance(cert[label], list):
            raise CertificateError("head delta must be arrays")
        values = [canonical_integer(x, label, 1) for x in cert[label]]
        if values != sorted(set(values)) or any(x >= cutoff for x in values):
            raise CertificateError("head delta ordering/range")
        if any(padded_member(x-s, digits) != (label == "removed") for x in values):
            raise CertificateError("head delta membership")
        parsed.append(set(values))
    added, removed = parsed
    if len(added)*5*cutoff > 20000000:
        raise CertificateError("inconclusive: head audit cap")
    def member(x):
        return x > 0 and (x in added or (x not in removed and padded_member(x-s, digits)))
    for a in sorted(added):
        for i in range(5):
            for d in range(1, cutoff-1):
                start = a-i*d
                if start > 0 and all(member(start+j*d) for j in range(5)):
                    raise CertificateError("head delta creates an AP")
        if not tail_compatible(a, s, level, digits):
            raise CertificateError("head delta creates a cross-boundary AP")
    delta = sum((Fraction(1,x) for x in added), Fraction()) - sum((Fraction(1,x) for x in removed), Fraction())
    if signed_delta_fraction(cert["delta"]) != delta:
        raise CertificateError("delta mismatch")
    if base_dir is None:
        raise CertificateError("pure reference requires certificate directory")
    ref = resolve_digest(cert["pure_ref_sha256"], base_dir)
    verify_block_digit(ref)
    if ref["p"] != "5" or ref["block_len"] != "1" or ref["D"] != cert["D"] or ref["s"] != cert["s"]:
        raise CertificateError("pure reference mismatch")
    return {"valid": True, "delta": fraction_object(delta)}


def verify_certificate(certificate: Mapping[str, Any], base_dir=None) -> Dict[str, Any]:
    schema = certificate.get("schema") if isinstance(certificate, dict) else None
    if schema == "erd169.block_digit.v1":
        return verify_block_digit(certificate)
    if schema == "erd169.head_tail.v1":
        return verify_head_tail(certificate, base_dir)
    if schema == FINITE_SCHEMA:
        return verify_finite(certificate)
    if schema == PREFIX_SCHEMA:
        return verify_prefix(certificate, base_dir)
    if schema == DIGITSET_SCHEMA:
        return verify_digitset(certificate)
    return result(False, errors=[f"unsupported schema: {schema!r}"])
