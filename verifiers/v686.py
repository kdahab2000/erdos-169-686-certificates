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


def validate_null(certificate: Mapping[str, Any]) -> Dict[str, Any]:
    certificate = require_object(certificate, "null certificate")
    require_exact_keys(
        certificate,
        ("schema", "s", "k_set", "method", "box", "domain"),
        "null certificate",
    )
    if certificate["schema"] != NULL_SCHEMA:
        raise CertificateError(f"expected schema {NULL_SCHEMA!r}")
    s = canonical_integer(certificate["s"], "s", 2)
    raw_k_set = require_array(certificate["k_set"], "k_set")
    k_set = [canonical_integer(item, f"k_set[{index}]", 2) for index, item in enumerate(raw_k_set)]
    if k_set != sorted(set(k_set)):
        raise CertificateError("k_set must be strictly increasing")
    method = certificate["method"]
    if method not in ("divisor_complete", "bounded_box"):
        raise CertificateError("unknown null-certificate method")
    box = certificate["box"]
    if method == "divisor_complete":
        if box is not None:
            raise CertificateError("divisor_complete null certificates must have box=null")
    else:
        box = require_object(box, "box")
        require_exact_keys(box, ("k_max", "n_max"), "box")
        canonical_integer(box["k_max"], "box.k_max", 2)
        canonical_integer(box["n_max"], "box.n_max", 1)
    if certificate["domain"] != "n>=1":
        raise CertificateError("null certificate domain must be n>=1")
    return {"s": s, "k_set": k_set, "method": method, "domain": "n>=1"}


def verify_null(certificate: Mapping[str, Any]) -> Dict[str, Any]:
    """Raise :class:`CertificateError` when a null certificate is invalid."""

    details = validate_null(certificate)
    return {"valid": True, **details}


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
