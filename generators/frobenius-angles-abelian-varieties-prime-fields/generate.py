"""Frobenius angles of abelian varieties over prime fields -- numberdb.org/T216.

The table stores the sorted LMFDB Frobenius-angle list: theta in [0, 1]
with q^(-1/2) exp(pi i theta) a root of the L-polynomial. Boundary angles
0 and 1 are included with their multiplicities, so a genus 2 class may have
more than g angle rows.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The class range is a measured complete rectangle inside the Weil-polynomial
table this one depends on: g = 1 for prime q <= 13 and g = 2 for prime
q <= 5. Before the draft was created, that range measured 520 angle entries,
with a longest value of 176 characters and a 103.9 KB entries block.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import GCD, euler_phi, is_prime
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField
from sage.rings.complex_arb import ComplexBallField
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing

G1_PRIMES = (2, 3, 5, 7, 11, 13)
G2_PRIMES = (2, 3, 5)
OEIS_A362198 = {2: 35, 3: 63, 5: 129}
WORKING_GUARD = 192
ROOT_OF_UNITY_DENOMINATORS = (1, 2, 3, 4, 5, 6, 8, 10, 12)

ZT = PolynomialRing(ZZ, "t")
t = ZT.gen()

_RECORDS = None
_RECORDS_BY_KEY = None
_ANGLE_COUNTS_BY_KEY = None


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _floor_sqrt_times(coefficient, q):
    return ZZ(coefficient * coefficient * q).isqrt()


def _ceil_sqrt_times(coefficient, q):
    square = ZZ(coefficient * coefficient * q)
    root = square.isqrt()
    return root if root * root == square else root + 1


def _encode_nonnegative(n):
    n = ZZ(n)
    if n < 0:
        raise ValueError("expected a nonnegative integer")
    if n == 0:
        return "a"

    letters = []
    while n:
        n, digit = n.quo_rem(26)
        letters.append(chr(ord("a") + int(digit)))
    return "".join(reversed(letters))


def _encode_lmfdb_integer(n):
    n = ZZ(n)
    if n < 0:
        return "a" + _encode_nonnegative(-n)
    return _encode_nonnegative(n)


def lmfdb_label(g, q, coefficients):
    return "%s.%s.%s" % (
        g, q, "_".join(_encode_lmfdb_integer(c) for c in coefficients))


def _p_rank(q, coefficients):
    rank = 0
    for index, coefficient in enumerate(coefficients, start=1):
        if ZZ(coefficient) % q != 0:
            rank = index
    return ZZ(rank)


def _signed_divisors(n):
    for divisor in ZZ(n).divisors():
        yield ZZ(divisor)
        yield ZZ(-divisor)


def _has_integer_root(polynomial):
    for root in _signed_divisors(abs(polynomial[0])):
        if polynomial(root) == 0:
            return True
    return False


def _is_reducible_quartic(polynomial):
    if polynomial.degree() != 4:
        raise ValueError("expected a quartic")
    return len(_quadratic_factors(polynomial)) > 1


def _is_simple_class(g, polynomial):
    if g == 1:
        return True
    return not _is_reducible_quartic(polynomial)


def _genus1_records(q):
    bound = _floor_sqrt_times(2, q)
    for a1 in range(-int(bound), int(bound) + 1):
        a1 = ZZ(a1)
        polynomial = t**2 + a1 * t + q
        yield _record(1, q, (a1,), polynomial)


def _genus2_records(q):
    bound = _floor_sqrt_times(4, q)
    for a1 in range(-int(bound), int(bound) + 1):
        a1 = ZZ(a1)
        lower = _ceil_sqrt_times(2 * abs(a1), q) - 2 * q
        upper = a1 * a1 // 4 + 2 * q
        for a2 in range(int(lower), int(upper) + 1):
            a2 = ZZ(a2)
            polynomial = t**4 + a1 * t**3 + a2 * t**2 + q * a1 * t + q**2
            yield _record(2, q, (a1, a2), polynomial)


def _record(g, q, coefficients, polynomial):
    label = lmfdb_label(g, q, coefficients)
    rank = _p_rank(q, coefficients)
    polynomial = ZT(polynomial)
    return {
        "g": ZZ(g),
        "q": ZZ(q),
        "label": label,
        "coefficients": tuple(ZZ(c) for c in coefficients),
        "polynomial": polynomial,
        "p_rank": rank,
        "ordinary": bool(rank == g),
        "simple": _is_simple_class(g, polynomial),
    }


def _build_records():
    built = []
    for q in G1_PRIMES:
        if not is_prime(q):
            raise ArithmeticError("%s is not prime" % (q,))
        built.extend(sorted(_genus1_records(ZZ(q)),
                            key=lambda record: record["label"]))
    for q in G2_PRIMES:
        if not is_prime(q):
            raise ArithmeticError("%s is not prime" % (q,))
        built.extend(sorted(_genus2_records(ZZ(q)),
                            key=lambda record: record["label"]))
    return built


def _check_q_reciprocal(record):
    polynomial = record["polynomial"]
    g = int(record["g"])
    q = record["q"]
    if not polynomial.is_monic() or polynomial.degree() != 2 * g:
        raise ArithmeticError("%s is not monic of degree %s"
                              % (record["label"], 2 * g))
    for i in range(g + 1):
        if polynomial[i] != q**(g - i) * polynomial[2 * g - i]:
            raise ArithmeticError("%s does not satisfy q-reciprocity"
                                  % (record["label"],))


def _check_weil_bounds(record):
    g = int(record["g"])
    q = record["q"]
    coefficients = record["coefficients"]
    if g == 1:
        a1, = coefficients
        if a1 * a1 > 4 * q:
            raise ArithmeticError("%s fails the Hasse bound"
                                  % (record["label"],))
        return

    a1, a2 = coefficients
    if a1 * a1 > 16 * q:
        raise ArithmeticError("%s fails the genus 2 trace bound"
                              % (record["label"],))
    lower = _ceil_sqrt_times(2 * abs(a1), q) - 2 * q
    upper = a1 * a1 // 4 + 2 * q
    if not (lower <= a2 <= upper):
        raise ArithmeticError("%s fails the genus 2 Weil bounds"
                              % (record["label"],))


def _check_record(record):
    if lmfdb_label(record["g"], record["q"],
                   record["coefficients"]) != record["label"]:
        raise ArithmeticError("label mismatch for %s" % (record["label"],))
    _check_q_reciprocal(record)
    _check_weil_bounds(record)
    if _p_rank(record["q"], record["coefficients"]) != record["p_rank"]:
        raise ArithmeticError("p-rank mismatch for %s" % (record["label"],))
    if bool(record["p_rank"] == record["g"]) != record["ordinary"]:
        raise ArithmeticError("ordinary mismatch for %s" % (record["label"],))
    if _is_simple_class(record["g"], record["polynomial"]) != record["simple"]:
        raise ArithmeticError("simplicity mismatch for %s" % (record["label"],))


def _check_global(records):
    by_pair = {}
    labels = set()
    polynomials = set()
    for record in records:
        _check_record(record)
        key = (record["g"], record["q"])
        by_pair[key] = by_pair.get(key, 0) + 1
        if record["label"] in labels:
            raise ArithmeticError("duplicate label %s" % (record["label"],))
        labels.add(record["label"])
        poly_key = (record["g"], record["q"], str(record["polynomial"]))
        if poly_key in polynomials:
            raise ArithmeticError("duplicate polynomial %s"
                                  % (record["polynomial"],))
        polynomials.add(poly_key)

    for q in G1_PRIMES:
        q = ZZ(q)
        expected = 2 * _floor_sqrt_times(2, q) + 1
        if by_pair.get((ZZ(1), q)) != expected:
            raise ArithmeticError("g=1, q=%s: got %s, expected %s"
                                  % (q, by_pair.get((ZZ(1), q)), expected))
    for q, expected in OEIS_A362198.items():
        key = (ZZ(2), ZZ(q))
        if by_pair.get(key) != expected:
            raise ArithmeticError("g=2, q=%s: got %s, expected %s"
                                  % (q, by_pair.get(key), expected))

    required = {
        "2.2.ab_a": t**4 - t**3 - 2 * t + 4,
        "2.2.ad_f": t**4 - 3 * t**3 + 5 * t**2 - 6 * t + 4,
    }
    by_label = {record["label"]: record for record in records}
    for label, polynomial in required.items():
        if by_label[label]["polynomial"] != polynomial:
            raise ArithmeticError("%s is %s, expected %s"
                                  % (label, by_label[label]["polynomial"],
                                     polynomial))


def records():
    global _RECORDS
    if _RECORDS is None:
        _RECORDS = _build_records()
        _check_global(_RECORDS)
    return _RECORDS


def records_by_key():
    global _RECORDS_BY_KEY
    if _RECORDS_BY_KEY is None:
        _RECORDS_BY_KEY = {
            (record["g"], record["q"], record["label"]): record
            for record in records()
        }
    return _RECORDS_BY_KEY


def _coerce_record_key(params):
    return ZZ(params["g"]), ZZ(params["q"]), str(params["label"])


def _coerce_angle_key(params):
    return (_coerce_record_key(params), ZZ(params["i"]))


def _quadratic_factors(polynomial):
    polynomial = ZT(polynomial)
    degree = polynomial.degree()
    if degree == 2:
        return [polynomial]
    if degree != 4:
        raise ValueError("expected a quadratic or quartic")
    if _has_integer_root(polynomial):
        raise ArithmeticError("unexpected rational root in %s" % polynomial)

    a = polynomial[3]
    b = polynomial[2]
    c = polynomial[1]
    d = polynomial[0]
    bound = 2 * (abs(a) + abs(b) + abs(c) + abs(d) + 1)
    for v in _signed_divisors(abs(d)):
        if d % v != 0:
            continue
        z = d // v
        for u in range(-int(bound), int(bound) + 1):
            u = ZZ(u)
            w = a - u
            if u * z + w * v == c and u * w + v + z == b:
                return [t**2 + u * t + v, t**2 + w * t + z]
    return [polynomial]


def _angle_count(record):
    count = 0
    q = record["q"]
    for factor in _quadratic_factors(record["polynomial"]):
        if factor.degree() == 2 and factor == t**2 - q:
            count += 2
        else:
            count += factor.degree() // 2
    return count


def angle_counts_by_key():
    global _ANGLE_COUNTS_BY_KEY
    if _ANGLE_COUNTS_BY_KEY is None:
        _ANGLE_COUNTS_BY_KEY = {
            (record["g"], record["q"], record["label"]): _angle_count(record)
            for record in records()
        }
    return _ANGLE_COUNTS_BY_KEY


def _root_unity_polynomial(q, denominator):
    denominator = ZZ(denominator)
    phi = ZZ(euler_phi(denominator))
    cyclotomic = ZT.cyclotomic_polynomial(denominator)
    out = ZT(0)
    for power, coefficient in enumerate(cyclotomic.list()):
        out += ZZ(coefficient) * q**(phi - power) * t**(2 * power)
    return out


def _root_unity_order(theta):
    theta = QQ(theta)
    if theta == 0 or theta == 1:
        return ZZ(1)
    return ZZ(theta.denominator())


def _has_exact_rational_angle(polynomial, q, theta):
    denominator = _root_unity_order(theta)
    if denominator not in ROOT_OF_UNITY_DENOMINATORS:
        return False
    common = ZT(polynomial).gcd(_root_unity_polynomial(q, denominator))
    return common.degree() > 0


def _candidate_angles():
    found = {QQ(0), QQ(1)}
    for denominator in ROOT_OF_UNITY_DENOMINATORS:
        if denominator == 1:
            continue
        for numerator in range(1, int(denominator)):
            if GCD(numerator, denominator) == 1:
                found.add(QQ(numerator) / QQ(denominator))
    return sorted(found)


EXACT_CANDIDATES = _candidate_angles()


def _maybe_exact(polynomial, q, angle):
    approximate = float(angle)
    for candidate in EXACT_CANDIDATES:
        if abs(approximate - float(candidate)) < 1e-20:
            if _has_exact_rational_angle(polynomial, q, candidate):
                return candidate
    return angle


def _quadratic_angle(factor, q, field):
    if factor == t**2 - q:
        return [QQ(0), QQ(1)]
    if factor == t**2 + q:
        return [QQ(1) / QQ(2)]
    if factor[0] != q:
        raise ArithmeticError("unhandled real-root factor %s" % factor)
    coefficient = ZZ(factor[1])
    angle = (-field(coefficient) / (2 * field(q).sqrt())).arccos() / field.pi()
    return [_maybe_exact(factor, q, angle)]


def _quartic_angles(factor, q, field):
    complex_field = ComplexBallField(field.precision())
    polynomial_ring = PolynomialRing(complex_field, "t")
    roots = polynomial_ring(factor).roots(ring=complex_field,
                                          multiplicities=False)
    selected = []
    for root in roots:
        if float(root.imag()) > 0:
            angle = root.arg() / field.pi()
            selected.append(_maybe_exact(factor, q, angle))
    if len(selected) != 2:
        raise ArithmeticError("%s produced %s upper-half roots"
                              % (factor, len(selected)))
    return selected


def _sort_key(angle):
    return float(angle)


def frobenius_angles(record, digits):
    field = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
    q = record["q"]
    angles = []
    for factor in _quadratic_factors(record["polynomial"]):
        if factor.degree() == 2:
            angles.extend(_quadratic_angle(factor, q, field))
        else:
            angles.extend(_quartic_angles(factor, q, field))
    angles = sorted(angles, key=_sort_key)
    if len(angles) != _angle_count(record):
        raise ArithmeticError("%s produced %s angles, expected %s"
                              % (record["label"], len(angles),
                                 _angle_count(record)))
    return angles


class FrobeniusAnglesOfAbelianVarieties(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T216")
    parameters = ("g", "q", "label", "i")
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self):
        counts = angle_counts_by_key()
        for record in records():
            key = (record["g"], record["q"], record["label"])
            for i in range(1, int(counts[key]) + 1):
                yield {
                    "g": record["g"],
                    "q": record["q"],
                    "label": record["label"],
                    "i": ZZ(i),
                }

    def value(self, params, digits):
        record_key, i = _coerce_angle_key(params)
        record = records_by_key()[record_key]
        _check_record(record)
        angles = frobenius_angles(record, digits)
        return angles[int(i) - 1]


if __name__ == "__main__":
    _key_from_stdin()
    generator = FrobeniusAnglesOfAbelianVarieties()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="Frobenius angles over prime fields, g <= 2"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
