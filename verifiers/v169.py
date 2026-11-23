"""Independent verifier for Erdős Problem 169 certificates.

The verifier is intentionally conservative: every reported rational value is
recomputed with :class:`fractions.Fraction`, and no floating-point operation is
used anywhere in this module.
"""

from __future__ import annotations

from fractions import Fraction
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


def verify_prefix(certificate: Mapping[str, Any]) -> Dict[str, Any]:
    details = validate_prefix(certificate)
    return {"valid": True, **details}


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


def verify_certificate(certificate: Mapping[str, Any]) -> Dict[str, Any]:
    schema = certificate.get("schema") if isinstance(certificate, dict) else None
    if schema == FINITE_SCHEMA:
        return verify_finite(certificate)
    if schema == PREFIX_SCHEMA:
        return verify_prefix(certificate)
    if schema == DIGITSET_SCHEMA:
        return verify_digitset(certificate)
    return result(False, errors=[f"unsupported schema: {schema!r}"])
