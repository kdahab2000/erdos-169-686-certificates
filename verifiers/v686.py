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


def iroot(value, k):
    if value < 0 or k < 1:
        raise CertificateError('root domain')
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
    m0, m1, m2 = moduli
    t0, t1, t2 = allowed
    good0 = [r for r in range(m0) if t0[r]]
    y_lo = lo + 2
    y_hi = hi + 2
    base = y_lo - (y_lo % m0)
    while base <= y_hi:
        for r in good0:
            y = base + r
            if y < y_lo:
                continue
            if y > y_hi:
                break
            if t1[y % m1] and t2[y % m2]:
                target = s*s*(y*y*y-y)
                x = icbrt(target)+1
                if x*x*x-x == target and x-2 >= y+1:
                    yield 3,y-2,x-2
        base += m0


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
                    raise CertificateError('prime power survivor cap')
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
    require_exact_keys(cert,('schema','s','k_lo','k_hi','n_lo','n_hi','method','domain'),'sieve null')
    if cert['schema']!='erd686.sieve_null.v1' or cert['domain']!='n>=1':
        raise CertificateError('sieve schema/domain')
    s = canonical_integer(cert['s'],'s',2)
    kl = canonical_integer(cert['k_lo'],'k_lo',3)
    kh = canonical_integer(cert['k_hi'],'k_hi',3)
    lo = canonical_integer(cert['n_lo'],'n_lo',1)
    hi = canonical_integer(cert['n_hi'],'n_hi',1)
    if s>10000 or kl>kh or lo>hi:
        raise CertificateError('sieve parameter cap/order')
    if cert['method']=='cubic_crt_icbrt':
        if kl!=3 or kh!=3 or hi>5000000:
            raise CertificateError('cubic cap')
        hits = cubic_sieve_hits(s,lo,hi)
    elif cert['method']=='prime_power_exclusion':
        if kl<5 or kh>200 or hi>100000 or (kh-kl+1)*(hi-lo+1)>10000000:
            raise CertificateError('prime power cap')
        hits = prime_power_sieve_hits(s,kl,kh,lo,hi)
    else:
        raise CertificateError('unknown sieve method')
    try:
        k,n,m = next(hits)
    except StopIteration as done:
        return {'valid':True,'survivors':str(done.value) if done.value is not None else 'not recorded'}
    raise CertificateError(f'sieve hit k={k} n={n} m={m}; emit erd686.rep.v1')


def _c5_integer(value: Any, label: str, minimum: Optional[int] = None) -> int:
    if isinstance(value, bool) or not isinstance(value, str) or not (value.isascii() and value.isdecimal() and (value=='0' or not value.startswith('0'))):
        raise CertificateError(f"{label} is not a canonical decimal string")
    number = int(value)
    if number.bit_length() > 4096:
        raise CertificateError(f"{label} exceeds 4096 bits")
    if minimum is not None and number < minimum:
        raise CertificateError(f"{label} is below {minimum}")
    return number


def _c5_keys(obj: Mapping[str, Any], expected: Iterable[str], label: str) -> None:
    expected = set(expected)
    actual = set(obj)
    if expected != actual:
        raise CertificateError(
            f"{label} keys differ: missing={sorted(expected-actual)}, unknown={sorted(actual-expected)}"
        )


def verify_pell_batch(cert):
    _c5_keys(cert,('schema','k','N_min','N_max','domain','rows'),'Pell batch')
    if cert['schema']!='erd686.pell_batch.v1' or cert['k']!='2' or cert['domain']!='n>=1':
        raise CertificateError('wrong Pell parameters')
    lo = _c5_integer(cert['N_min'],'N_min',2)
    hi = _c5_integer(cert['N_max'],'N_max',2)
    if not lo<=hi<=10000 or not isinstance(cert['rows'],list):
        raise CertificateError('Pell range/rows')
    expected = [n for n in range(lo,hi+1) if isqrt(n)**2!=n]
    if len(cert['rows'])!=len(expected):
        raise CertificateError('Pell coverage')
    for row,expected_n in zip(cert['rows'],expected):
        if not isinstance(row,dict):
            raise CertificateError('Pell row must be object')
        _c5_keys(row,('N','u','v','n','m'),'Pell row')
        N,u,v,n,m = [_c5_integer(row[key],key,1) for key in ('N','u','v','n','m')]
        if max(N,u,v,n,m).bit_length()>256:
            raise CertificateError('Pell 256-bit cap')
        if N!=expected_n:
            raise CertificateError('Pell coverage')
        if u<2 or u*u-N*v*v!=1:
            raise CertificateError('Pell norm')
        U,V = 2*u*u-1,2*u*v
        if 2*n!=U+V-3 or 2*m!=U+N*V-3 or m<n+2:
            raise CertificateError('Pell coordinates/domain')
        if (m+1)*(m+2)!=N*(n+1)*(n+2):
            raise CertificateError('Pell product equality')
    return {'valid':True,'k':2,'N_min':lo,'N_max':hi,'count':len(expected),
            'novelty_tags':['NONSQUARE_PELL_KNOWN']}


def verify_certificate(certificate: Mapping[str, Any]) -> Dict[str, Any]:
    schema = certificate.get("schema") if isinstance(certificate, dict) else None
    try:
        if schema == "erd686.pell_batch.v1":
            return verify_pell_batch(certificate)
        if schema == "erd686.sieve_null.v1":
            return verify_sieve_null(certificate)
        if schema == REP_SCHEMA:
            return verify_representation(certificate)
        if schema == NULL_SCHEMA:
            return verify_null(certificate)
        raise CertificateError(f"unsupported schema: {schema!r}")
    except (CertificateError, TypeError, ValueError) as exc:
        return {"valid": False, "errors": [str(exc)]}
