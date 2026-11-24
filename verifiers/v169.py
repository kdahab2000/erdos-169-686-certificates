"""Independent verifier for Erdős Problem 169 certificates.

The verifier is intentionally conservative: every reported rational value is
recomputed with :class:`fractions.Fraction`, and no floating-point operation is
used anywhere in this module.
"""

from __future__ import annotations

from fractions import Fraction
from math import isqrt, gcd
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
    require_exact_keys(cert,("schema","k","p","D","s","L","candidates","dual_arcs","min_nonempty_loss","pure_ref_sha256"),"rigidity")
    if (cert["schema"] != "erd169.rigidity.v1" or cert["k"] != "5" or cert["p"] != "5"
            or cert["s"] != "1" or cert["D"] != ["0","1","2","3"]):
        raise CertificateError("rigidity parameter mismatch")
    level = canonical_integer(cert["L"],"L",1)
    if level>8:
        raise CertificateError("rigidity level cap")
    if not isinstance(cert["candidates"],list) or len(cert["candidates"])>260:
        raise CertificateError("candidate array cap")
    candidates = [canonical_integer(x,"candidate",1) for x in cert["candidates"]]
    if candidates != rigidity_candidates(level):
        raise CertificateError("incomplete or invalid candidate list")
    cutoff = 1+5**level
    reflection = 3*(5**level-1)//4+2
    candidate_set = set(candidates)
    for a in candidates:
        if reflection-a not in candidate_set or not tail_compatible(a,1,level,[0,1,2,3]):
            raise CertificateError("candidate tail/reflection mismatch")
    margin = canonical_fraction_object(cert["min_nonempty_loss"],"min_nonempty_loss")
    if base_dir is None:
        raise CertificateError("pure reference requires directory")
    ref = resolve_digest(cert["pure_ref_sha256"],base_dir)
    verify_block_digit(ref)
    if ref["p"]!="5" or ref["k"]!="5" or ref["block_len"]!="1" or ref["s"]!="1" or ref["D"]!=cert["D"]:
        raise CertificateError("pure reference mismatch")
    if not isinstance(cert["dual_arcs"],list) or len(cert["dual_arcs"])>100000:
        raise CertificateError("arc array cap")
    coverage = {a:Fraction() for a in candidates}
    load = {}
    seen = set()
    def bounded(value):
        if max(value.numerator.bit_length(),value.denominator.bit_length())>4096:
            raise CertificateError("rigidity rational sum exceeds cap")
        return value
    for arc in cert["dual_arcs"]:
        if not isinstance(arc,dict):
            raise CertificateError("arc must be object")
        require_exact_keys(arc,("a","start","diff","weight"),"arc")
        a = canonical_integer(arc["a"],"a",1)
        start = canonical_integer(arc["start"],"start",1)
        diff = canonical_integer(arc["diff"],"diff",1)
        # Any admissible arc has d < 5**L. This also bounds membership work.
        if a not in candidate_set or diff>=5**level or start>=cutoff:
            raise CertificateError("arc range")
        identity = (a,start,diff)
        if identity in seen:
            raise CertificateError("duplicate arc")
        seen.add(identity)
        terms = [start+j*diff for j in range(5)]
        if a not in terms or any(not padded_member(x-1,[0,1,2,3]) for x in terms if x!=a):
            raise CertificateError("forged progression")
        head = rigidity_head_terms(terms,a,cutoff)
        if not head:
            raise CertificateError("arc has no removable head point")
        weight = canonical_fraction_object(arc["weight"],"weight")
        if weight<=0:
            raise CertificateError("nonpositive weight")
        coverage[a] = bounded(coverage[a]+weight)
        for r in head:
            load[r] = bounded(load.get(r,Fraction())+weight)
            if load[r]>Fraction(1,r):
                raise CertificateError("overloaded head capacity")
    for a,total in coverage.items():
        if total<bounded(Fraction(1,a)+margin):
            raise CertificateError("insufficient candidate coverage")
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
    require_exact_keys(cert,('schema','k','B','D','s','depth','Q','ap_mode','ap_params','lb_num','ub_num'),'quantized block')
    if cert['schema'] != 'erd169.quantized_block.v1':
        raise CertificateError('wrong quantized schema')
    k = canonical_integer(cert['k'],'k',3)
    base = canonical_integer(cert['B'],'B',2)
    s = canonical_integer(cert['s'],'s',1)
    depth = canonical_integer(cert['depth'],'depth',1)
    q = canonical_integer(cert['Q'],'Q',1)
    lb = canonical_integer(cert['lb_num'],'lb_num',0)
    ub = canonical_integer(cert['ub_num'],'ub_num',0)
    if k>6 or base>128 or s>10000 or depth>20 or q!=10**60 or lb>ub:
        raise CertificateError('quantized parameter cap/order')
    if not isinstance(cert['D'],list) or not 2<=len(cert['D'])<base:
        raise CertificateError('quantized digit cap')
    digits = [canonical_integer(x,'D',0) for x in cert['D']]
    if digits != sorted(set(digits)) or digits[0]!=0 or digits[-1]>=base:
        raise CertificateError('invalid quantized digits')
    if len(digits)**depth>1100000:
        raise CertificateError('quantized enumeration cap')
    params = cert['ap_params']
    if not isinstance(params,dict):
        raise CertificateError('AP params must be object')
    if cert['ap_mode']=='prime_power_cyclic':
        require_exact_keys(params,('p','block_len'),'AP params')
        p = canonical_integer(params['p'],'p',2)
        length = canonical_integer(params['block_len'],'block_len',1)
        if p>base or length>7 or k<p or any(p%j==0 for j in range(2,isqrt(p)+1)) or p**length!=base:
            raise CertificateError('invalid prime power')
        present = set(digits)
        if any(all((a+j*w)%base in present for j in range(p)) for a in digits for w in range(1,base)):
            raise CertificateError('cyclic AP')
    elif cert['ap_mode']=='carry_automaton':
        require_exact_keys(params,(),'AP params')
        if not carry_ap_free(base,digits,k):
            raise CertificateError('carry automaton accepts an AP')
    else:
        raise CertificateError('unknown AP proof mode')
    if quantized_enclosure(base,digits,s,depth,q)!=(lb,ub):
        raise CertificateError('quantized endpoint mismatch')
    return {'valid':True,'lb_num':str(lb),'ub_num':str(ub)}


def verify_rigidity_v2(cert, base_dir=None):
    require_exact_keys(cert,("schema","k","p","D","s","L","candidates","dual_arcs","min_nonempty_loss","pure_ref_sha256"),"rigidity")
    if (cert["schema"] != "erd169.rigidity.v2" or cert["k"] != "5" or cert["p"] != "5"
            or cert["s"] != "1" or cert["D"] != ["0","1","2","3"]):
        raise CertificateError("rigidity parameter mismatch")
    level = canonical_integer(cert["L"],"L",1)
    if level>9:
        raise CertificateError("rigidity level cap")
    if not isinstance(cert["candidates"],list) or len(cert["candidates"])>2000:
        raise CertificateError("candidate array cap")
    candidates = [canonical_integer(x,"candidate",1) for x in cert["candidates"]]
    if candidates != rigidity_candidates(level):
        raise CertificateError("incomplete or invalid candidate list")
    cutoff = 1+5**level
    reflection = 3*(5**level-1)//4+2
    candidate_set = set(candidates)
    for a in candidates:
        if reflection-a not in candidate_set or not tail_compatible(a,1,level,[0,1,2,3]):
            raise CertificateError("candidate tail/reflection mismatch")
    margin = canonical_fraction_object(cert["min_nonempty_loss"],"min_nonempty_loss")
    if base_dir is None:
        raise CertificateError("pure reference requires directory")
    ref = resolve_digest(cert["pure_ref_sha256"],base_dir)
    verify_block_digit(ref)
    if ref["p"]!="5" or ref["k"]!="5" or ref["block_len"]!="1" or ref["s"]!="1" or ref["D"]!=cert["D"]:
        raise CertificateError("pure reference mismatch")
    if not isinstance(cert["dual_arcs"],list) or len(cert["dual_arcs"])>100000:
        raise CertificateError("arc array cap")
    coverage = {a:Fraction() for a in candidates}
    load = {}
    seen = set()
    def bounded(value):
        if max(value.numerator.bit_length(),value.denominator.bit_length())>4096:
            raise CertificateError("rigidity rational sum exceeds cap")
        return value
    for arc in cert["dual_arcs"]:
        if not isinstance(arc,dict):
            raise CertificateError("arc must be object")
        require_exact_keys(arc,("a","start","diff","weight"),"arc")
        a = canonical_integer(arc["a"],"a",1)
        start = canonical_integer(arc["start"],"start",1)
        diff = canonical_integer(arc["diff"],"diff",1)
        # Any admissible arc has d < 5**L. This also bounds membership work.
        if a not in candidate_set or diff>=5**level or start>=cutoff:
            raise CertificateError("arc range")
        identity = (a,start,diff)
        if identity in seen:
            raise CertificateError("duplicate arc")
        seen.add(identity)
        terms = [start+j*diff for j in range(5)]
        if a not in terms or any(not padded_member(x-1,[0,1,2,3]) for x in terms if x!=a):
            raise CertificateError("forged progression")
        head = rigidity_head_terms(terms,a,cutoff)
        if not head:
            raise CertificateError("arc has no removable head point")
        weight = canonical_fraction_object(arc["weight"],"weight")
        if weight<=0:
            raise CertificateError("nonpositive weight")
        coverage[a] = bounded(coverage[a]+weight)
        for r in head:
            load[r] = bounded(load.get(r,Fraction())+weight)
            if load[r]>Fraction(1,r):
                raise CertificateError("overloaded head capacity")
    for a,total in coverage.items():
        if total<bounded(Fraction(1,a)+margin):
            raise CertificateError("insufficient candidate coverage")
    return {"valid":True,"max_delta":{"num":"0","den":"1"},"unique_optimum":margin>0}

def cyclic_progressions(modulus):
    # Store a canonical (start,difference) for each distinct cyclic AP set.
    edges = {}
    for a in range(modulus):
        for d in range(1,modulus):
            terms = frozenset((a+j*d)%modulus for j in range(5))
            edges.setdefault(terms,(a,d))
    return edges


def verify_cyclic_max(cert):
    require_exact_keys(cert,('schema','modulus','p','max_cardinality','witness','mode','proof'),'cyclic max')
    if cert['schema']!='erd169.cyclic_max.v1' or cert['p']!='5' or cert['modulus']!='25' or cert['mode']!='direct_bnb':
        raise CertificateError('unsupported cyclic proof mode; Z125 remains unresolved')
    maximum = canonical_integer(cert['max_cardinality'],'maximum',0)
    if maximum>25 or not isinstance(cert['witness'],list) or len(cert['witness'])!=maximum:
        raise CertificateError('cyclic witness cap')
    witness = [canonical_integer(x,'witness',0) for x in cert['witness']]
    if witness!=sorted(set(witness)) or any(x>=25 for x in witness):
        raise CertificateError('cyclic witness range/order')
    edges = cyclic_progressions(25)
    if any(edge<=set(witness) for edge in edges):
        raise CertificateError('cyclic witness has AP')
    nodes = cert['proof']
    if not isinstance(nodes,list) or not 1<=len(nodes)<=1000000:
        raise CertificateError('cyclic tree cap')
    index = 0
    full = set(range(25))
    def parse_ap(pair):
        if not isinstance(pair,list) or len(pair)!=2:
            raise CertificateError('cyclic AP pair')
        a,d = [canonical_integer(x,'AP',0) for x in pair]
        if a>=25 or not 1<=d<25:
            raise CertificateError('cyclic AP range')
        return {(a+j*d)%25 for j in range(5)}
    def visit(selected,excluded):
        nonlocal index
        if index>=len(nodes):
            raise CertificateError('truncated cyclic tree')
        node = nodes[index]; index+=1
        if not isinstance(node,dict):
            raise CertificateError('cyclic node must be object')
        op = node.get('op')
        undecided = full-selected-excluded
        if op=='branch':
            require_exact_keys(node,('op','j'),'cyclic branch')
            j = canonical_integer(node['j'],'j',0)
            if j not in undecided:
                raise CertificateError('cyclic repeated branch')
            visit(selected|{j},excluded)
            visit(selected,excluded|{j})
        elif op=='conflict':
            require_exact_keys(node,('op','ap'),'cyclic conflict')
            if not parse_ap(node['ap'])<=selected:
                raise CertificateError('forged cyclic conflict')
        elif op=='prune':
            require_exact_keys(node,('op','aps'),'cyclic prune')
            if not isinstance(node['aps'],list) or len(node['aps'])>25:
                raise CertificateError('cyclic packing cap')
            occupied = set()
            for pair in node['aps']:
                edge = parse_ap(pair)
                active = edge & undecided
                if edge&excluded or not active or edge&occupied:
                    raise CertificateError('invalid cyclic packing')
                occupied |= edge
            if len(selected)+len(undecided)-len(node['aps'])>maximum:
                raise CertificateError('invalid cyclic upper bound')
        else:
            raise CertificateError('unknown cyclic node')
    visit(set(),set())
    if index!=len(nodes):
        raise CertificateError('unused cyclic nodes')
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
    require_exact_keys(cert,('schema','modulus','p','max_cardinality','witness','mode','proof'),'H0 max')
    if cert['schema']!='erd169.cyclic_max.v1' or cert['modulus']!='125' or cert['p']!='5' or cert['mode']!='h0_orbit_bnb':
        raise CertificateError('wrong H0 parameters')
    maximum = canonical_integer(cert['max_cardinality'],'maximum',0)
    if not 64<=maximum<=80 or not isinstance(cert['witness'],list) or len(cert['witness'])!=maximum:
        raise CertificateError('H0 witness cap')
    witness = [canonical_integer(x,'witness',0) for x in cert['witness']]
    if witness!=sorted(set(witness)) or witness[-1]>=125:
        raise CertificateError('invalid H0 witness')
    proof = cert['proof']
    if not isinstance(proof,dict):
        raise CertificateError('H0 proof must be object')
    require_exact_keys(proof,('z25_ref_sha256','orbits'),'H0 proof')
    orbits = proof['orbits']
    if not isinstance(orbits,list) or not 1<=len(orbits)<=1000:
        raise CertificateError('H0 orbit cap')
    total = 0
    threshold = (maximum+5)//5
    for orbit in orbits:
        if not isinstance(orbit,dict):
            raise CertificateError('H0 orbit must be object')
        require_exact_keys(orbit,('fibre','tree'),'H0 orbit')
        if not isinstance(orbit['fibre'],list) or not threshold<=len(orbit['fibre'])<=16:
            raise CertificateError('H0 fibre cap')
        if not isinstance(orbit['tree'],list) or not orbit['tree']:
            raise CertificateError('H0 tree array')
        total += len(orbit['tree'])
        if total>1000000:
            raise CertificateError('H0 total node cap')
    if base_dir is None:
        raise CertificateError('H0 reference requires directory')
    ref = resolve_digest(proof['z25_ref_sha256'],base_dir)
    verify_cyclic_max(ref)
    if ref['modulus']!='25' or ref['max_cardinality']!='16':
        raise CertificateError('H0 requires Z25 maximum 16')
    edges = cyclic_progressions(125)
    present = set(witness)
    if any(edge<=present for edge in edges):
        raise CertificateError('H0 witness has AP')
    coverage = set()
    representatives = set()
    units = [a for a in range(25) if gcd(a,25)==1]
    parsed = []
    for orbit in orbits:
        fibre = [canonical_integer(x,'fibre',0) for x in orbit['fibre']]
        if fibre!=sorted(set(fibre)) or fibre[-1]>=25:
            raise CertificateError('H0 fibre range/order')
        if any(edge<=set(fibre) for edge in cyclic_progressions(25)):
            raise CertificateError('H0 fibre contains AP')
        mask = sum(1<<x for x in fibre)
        if mask in representatives:
            raise CertificateError('duplicate H0 representative')
        representatives.add(mask)
        for a in units:
            for c in range(25):
                coverage.add(sum(1<<((a*x+c)%25) for x in fibre))
        parsed.append((fibre,orbit['tree']))
    if any(mask not in coverage for mask in dense_z25_fibres(threshold)):
        raise CertificateError('incomplete H0 affine orbit coverage')
    full = set(range(125))
    cosets = [{a+25*j for j in range(5)} for a in range(25)]
    fibres = [{a+5*j for j in range(25)} for a in range(5)]
    for fibre,nodes in parsed:
        selected0 = {5*y for y in fibre}
        excluded0 = {5*y for y in range(25)}-selected0
        index = 0
        def ap(pair):
            if not isinstance(pair,list) or len(pair)!=2:
                raise CertificateError('H0 AP pair')
            a,d = [canonical_integer(x,'AP',0) for x in pair]
            if a>=125 or not 1<=d<125:
                raise CertificateError('H0 AP range')
            return {(a+j*d)%125 for j in range(5)}
        def visit(selected,excluded):
            nonlocal index
            if index>=len(nodes):
                raise CertificateError('truncated H0 tree')
            node = nodes[index]
            index+=1
            if not isinstance(node,dict):
                raise CertificateError('H0 node must be object')
            undecided = full-selected-excluded
            op = node.get('op')
            if op=='branch':
                require_exact_keys(node,('op','j'),'H0 branch')
                j = canonical_integer(node['j'],'j',0)
                if j not in undecided:
                    raise CertificateError('H0 branch violates fixed fibre')
                visit(selected|{j},excluded)
                visit(selected,excluded|{j})
            elif op=='conflict':
                require_exact_keys(node,('op','ap'),'H0 conflict')
                if not ap(node['ap'])<=selected:
                    raise CertificateError('forged H0 conflict')
            elif op=='prune':
                bound = node.get('bound')
                if bound in ('coset','fibre'):
                    require_exact_keys(node,('op','bound'),'H0 bound')
                    parts,cap = (cosets,4) if bound=='coset' else (fibres,16)
                    upper = len(selected)+sum(min(len(part&undecided),cap-len(part&selected)) for part in parts)
                elif bound=='packing':
                    require_exact_keys(node,('op','bound','aps'),'H0 packing')
                    if not isinstance(node['aps'],list) or len(node['aps'])>125:
                        raise CertificateError('H0 packing cap')
                    occupied = set()
                    for pair in node['aps']:
                        edge = ap(pair)
                        active = edge&undecided
                        if edge&excluded or not active or edge&occupied:
                            raise CertificateError('invalid H0 packing')
                        occupied |= edge
                    upper = len(selected)+len(undecided)-len(node['aps'])
                else:
                    raise CertificateError('unknown H0 bound')
                if upper>maximum:
                    raise CertificateError('invalid H0 prune bound')
            else:
                raise CertificateError('unknown H0 node')
        visit(selected0,excluded0)
        if index!=len(nodes):
            raise CertificateError('unused H0 nodes')
    return {'valid':True,'optimal':True,'max_cardinality':str(maximum)}


def verify_certificate(certificate: Mapping[str, Any], base_dir=None) -> Dict[str, Any]:
    schema = certificate.get("schema") if isinstance(certificate, dict) else None
    if schema == "erd169.quantized_block.v1":
        return verify_quantized_block(certificate)
    if schema == "erd169.rigidity.v2":
        return verify_rigidity_v2(certificate, base_dir)
    if schema == "erd169.cyclic_max.v1":
        if certificate.get("mode") == "h0_orbit_bnb":
            return verify_h0_cyclic_max(certificate,base_dir)
        return verify_cyclic_max(certificate)
    if schema == "erd169.block_digit.v1":
        return verify_block_digit(certificate)
    if schema == "erd169.head_tail.v1":
        return verify_head_tail(certificate, base_dir)
    if schema == "erd169.rigidity.v1":
        return verify_rigidity(certificate, base_dir)
    if schema == FINITE_SCHEMA:
        return verify_finite(certificate)
    if schema == PREFIX_SCHEMA:
        return verify_prefix(certificate, base_dir)
    if schema == DIGITSET_SCHEMA:
        return verify_digitset(certificate)
    return result(False, errors=[f"unsupported schema: {schema!r}"])
