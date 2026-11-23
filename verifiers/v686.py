"""Verifier for Erdős Problem 686 representation certificates."""

from __future__ import annotations

from math import comb, isqrt
from typing import Any, Dict, Mapping

from .common import (
    CertificateError,
    canonical_integer,
    require_array,
    require_exact_keys,
    require_object,
)

REP_SCHEMA = "erd686.rep.v1"
NULL_SCHEMA = "erd686.null.v1"


def novelty_tags(n_value: int, k: int) -> list[str]:
    root = isqrt(n_value)
    square = root * root == n_value
    tags: list[str] = []
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


def validate_representation(certificate: Mapping[str, Any]) -> Dict[str, Any]:
    certificate = require_object(certificate, "representation certificate")
    require_exact_keys(
        certificate,
        ("schema", "N", "k", "n", "m"),
        "representation certificate",
    )
    if certificate["schema"] != REP_SCHEMA:
        raise CertificateError(f"expected schema {REP_SCHEMA!r}")
    n_value = canonical_integer(certificate["N"], "N", 2)
    k = canonical_integer(certificate["k"], "k", 2)
    n = canonical_integer(certificate["n"], "n", 1)
    m = canonical_integer(certificate["m"], "m", 1)
    if k > 10000 or max(n, m).bit_length() > 256:
        raise CertificateError("representation resource cap")
    if m < n + k:
        raise CertificateError("m must satisfy m >= n + k")

    numerator = comb(m + k, k)
    denominator = comb(n + k, k)
    if numerator != n_value * denominator:
        raise CertificateError("binomial equality comb(m+k,k) = N*comb(n+k,k) failed")
    product_m = 1
    for index in range(1, k + 1):
        product_m *= m + index
    product_n = 1
    for index in range(1, k + 1):
        product_n *= n + index
    if product_m != n_value * product_n:
        raise CertificateError("equal-length consecutive-product equality failed")

    return {
        "N": n_value,
        "k": k,
        "n": n,
        "m": m,
        "novelty_tags": novelty_tags(n_value, k),
    }


def verify_representation(certificate: Mapping[str, Any]) -> Dict[str, Any]:
    """Raise :class:`CertificateError` when a representation is invalid."""

    details = validate_representation(certificate)
    return {"valid": True, **details}


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


def verify_null(cert):
    require_exact_keys(cert, ("schema", "s", "k_set", "method", "box", "domain"), "null")
    if cert["schema"] != "erd686.null.v1" or cert["domain"] != "n>=1":
        raise CertificateError("wrong null schema/domain")
    s = canonical_integer(cert["s"], "s", 2)
    if s > 10000:
        raise CertificateError("null root resource cap")
    if not isinstance(cert["k_set"], list):
        raise CertificateError("k_set must be an array")
    ks = [canonical_integer(x, "k", 2) for x in cert["k_set"]]
    if not ks or ks != sorted(set(ks)) or max(ks) > 100:
        raise CertificateError("empty, unordered or excessive k_set")
    if cert["method"] == "divisor_complete":
        if cert["box"] is not None or any(k not in (2, 4) for k in ks):
            raise CertificateError("invalid divisor domain")
        if any(divisor_has_hit(s, k) for k in ks):
            raise CertificateError("divisor null contains a representation")
    elif cert["method"] == "bounded_box":
        box = cert["box"]
        if not isinstance(box, dict):
            raise CertificateError("box must be an object")
        require_exact_keys(box, ("k_max", "n_max"), "box")
        top = canonical_integer(box["k_max"], "k_max", 2)
        limit = canonical_integer(box["n_max"], "n_max", 1)
        if top != max(ks) or limit * len(ks) > 6000000:
            raise CertificateError("box extent mismatch or resource cap")
        for k in ks:
            if next(box_hits(s*s, k, limit), None) is not None:
                raise CertificateError("bounded null contains a representation")
    else:
        raise CertificateError("unknown null method")
    return {"valid": True, "s": s, "k_set": ks, "method": cert["method"], "domain": "n>=1"}


def validate_null(certificate):
    """Preserve the historical low-level API, now with full replay."""
    details = verify_null(certificate)
    return {key: value for key, value in details.items() if key != "valid"}


def verify_certificate(certificate: Mapping[str, Any]) -> Dict[str, Any]:
    schema = certificate.get("schema") if isinstance(certificate, dict) else None
    try:
        if schema == REP_SCHEMA:
            return verify_representation(certificate)
        if schema == NULL_SCHEMA:
            return verify_null(certificate)
        raise CertificateError(f"unsupported schema: {schema!r}")
    except (CertificateError, TypeError, ValueError) as exc:
        return {"valid": False, "errors": [str(exc)]}
