"""Shared strict JSON and exact-arithmetic helpers.

Certificate integers are decimal strings so that JSON parsers cannot silently coerce
large values through binary floating point.  This module intentionally has no
third-party dependencies.
"""

from __future__ import annotations

import hashlib
import json
import re
from fractions import Fraction
from typing import Any, Dict, Iterable, Mapping, Optional

MAX_INTEGER_BITS = 4096
MAX_CERTIFICATE_ELEMENTS = 2_000_000
_DECIMAL = re.compile(r"0|[1-9][0-9]*\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class CertificateError(ValueError):
    """Raised when a certificate violates its schema or mathematical claim."""


class StrictJSONError(ValueError):
    """Raised for JSON that is not safe for exact certificate processing."""


def _reject_float(token: str) -> None:
    raise StrictJSONError("floating-point JSON numbers are forbidden")


def _reject_int(token: str) -> None:
    raise StrictJSONError(
        "certificate integers must be encoded as canonical decimal strings"
    )


def _unique_object(pairs: Iterable[tuple[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJSONError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def strict_json_loads(text: str) -> Any:
    """Parse certificate JSON with duplicate-key, float, and raw-integer checks."""

    return json.loads(
        text,
        object_pairs_hook=_unique_object,
        parse_float=_reject_float,
        parse_constant=_reject_float,
        parse_int=_reject_int,
    )


def plain_json_loads(text: str) -> Any:
    """Parse operational JSON while still rejecting duplicate keys and floats."""

    return json.loads(
        text,
        object_pairs_hook=_unique_object,
        parse_float=_reject_float,
        parse_constant=_reject_float,
    )


def require_exact_keys(value: Mapping[str, Any], expected: Iterable[str], label: str) -> None:
    expected_set = set(expected)
    actual_set = set(value)
    missing = sorted(expected_set - actual_set)
    unknown = sorted(actual_set - expected_set)
    if missing or unknown:
        raise CertificateError(
            f"{label}: missing keys {missing}; unknown keys {unknown}"
        )


def require_object(value: Any, label: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise CertificateError(f"{label} must be a JSON object")
    return value


def require_array(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise CertificateError(f"{label} must be a JSON array")
    if len(value) > MAX_CERTIFICATE_ELEMENTS:
        raise CertificateError(f"{label} exceeds the element-count cap")
    return value


def canonical_integer(value: Any, label: str, minimum: Optional[int] = None) -> int:
    """Decode a canonical, non-negative decimal string into an exact integer."""

    if isinstance(value, bool) or not isinstance(value, str) or not _DECIMAL.fullmatch(value):
        raise CertificateError(
            f"{label} must be a canonical non-negative decimal string"
        )
    number = int(value, 10)
    if number.bit_length() > MAX_INTEGER_BITS:
        raise CertificateError(f"{label} exceeds the {MAX_INTEGER_BITS}-bit cap")
    if minimum is not None and number < minimum:
        raise CertificateError(f"{label} must be at least {minimum}")
    return number


def canonical_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise CertificateError(f"{label} must be a lowercase SHA-256 digest")
    return value


def canonical_fraction_object(value: Any, label: str) -> Fraction:
    """Decode a reduced {num, den} object using exact integer arithmetic."""

    obj = require_object(value, label)
    require_exact_keys(obj, ("num", "den"), label)
    numerator = canonical_integer(obj["num"], f"{label}.num", 0)
    denominator = canonical_integer(obj["den"], f"{label}.den", 1)
    fraction = Fraction(numerator, denominator)
    if fraction.numerator != numerator or fraction.denominator != denominator:
        raise CertificateError(f"{label} must be a reduced fraction")
    return fraction


def fraction_object(fraction: Fraction) -> Dict[str, str]:
    return {
        "num": str(fraction.numerator),
        "den": str(fraction.denominator),
    }


def canonical_json_bytes(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON bytes used for certificate digests."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def write_json(path: str, value: Any) -> bytes:
    payload = canonical_json_bytes(value)
    with open(path, "wb") as handle:
        handle.write(payload)
        handle.write(b"\n")
    return payload


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def read_strict_json(path: str) -> Any:
    with open(path, "rb") as handle:
        return strict_json_loads(handle.read().decode("utf-8"))


def lcm(a: int, b: int) -> int:
    from math import gcd

    return a // gcd(a, b) * b


def integer_weight_sum(members: Iterable[int], common_multiple: int) -> int:
    return sum(common_multiple // member for member in members)


def find_k_ap(members: Iterable[int], k: int) -> Optional[tuple[int, int]]:
    """Return the lexicographically first (start, difference) k-term AP."""

    if k < 2:
        return None
    values = sorted(set(members))
    present = set(values)
    for start in values:
        for difference in range(1, max(values, default=0) - start + 1):
            end = start + (k - 1) * difference
            if end > max(values, default=0):
                break
            if all(start + index * difference in present for index in range(k)):
                return start, difference
    return None


def result(valid: bool, **fields: Any) -> Dict[str, Any]:
    answer: Dict[str, Any] = {"valid": bool(valid)}
    answer.update(fields)
    return answer


def error_result(exc: Exception) -> Dict[str, Any]:
    return {"valid": False, "errors": [str(exc)]}
