"""Weil polynomials of abelian varieties over prime fields -- numberdb.org/T214.

    P_A(t) = det(t - F | T_l A)

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The table stores the characteristic polynomial of Frobenius, not the
L-polynomial. For prime q, the genus 1 and genus 2 coefficient inequalities
below enumerate the isogeny classes exactly.

Rows measured before the draft was created: g = 1 for prime q <= 13 and
g = 2 for prime q <= 7 gives 494 entries, longest 33 characters and a
105.6 KB entries block. Adding the next genus 2 prime, q = 11, gives
895 entries and a 195.0 KB block, so the table stops at q = 7 in genus 2.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import is_prime
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing

G1_PRIMES = (2, 3, 5, 7, 11, 13)
G2_PRIMES = (2, 3, 5, 7)
OEIS_A362198 = {2: 35, 3: 63, 5: 129, 7: 207}

ZT = PolynomialRing(ZZ, "t")
t = ZT.gen()

_RECORDS = None
_RECORDS_BY_KEY = None


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


def _lmfdb_url(label):
    g, q, iso = label.split(".", 2)
    return "https://www.lmfdb.org/Variety/Abelian/Fq/%s/%s/%s" % (g, q, iso)


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
    """Whether a monic quartic over ZZ factors over QQ."""
    if polynomial.degree() != 4:
        raise ValueError("expected a quartic")
    if _has_integer_root(polynomial):
        return True

    a = polynomial[3]
    b = polynomial[2]
    c = polynomial[1]
    d = polynomial[0]
    for v in _signed_divisors(abs(d)):
        if d % v != 0:
            continue
        z = d // v
        # Any factorisation is (t^2 + u t + v)(t^2 + w t + z).
        # The bounds here are deliberately loose; the table's q is small and
        # this avoids Sage's factorisation path, which imports Singular.
        bound = 2 * (abs(a) + abs(b) + abs(c) + abs(d) + 1)
        for u in range(-int(bound), int(bound) + 1):
            u = ZZ(u)
            w = a - u
            if u * z + w * v == c and u * w + v + z == b:
                return True
    return False


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
    simple = _is_simple_class(g, polynomial)
    return {
        "g": ZZ(g),
        "q": ZZ(q),
        "label": label,
        "url": _lmfdb_url(label),
        "coefficients": tuple(ZZ(c) for c in coefficients),
        "polynomial": ZT(polynomial),
        "p_rank": rank,
        "ordinary": bool(rank == g),
        "simple": simple,
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


def _coerce_params(params):
    return ZZ(params["g"]), ZZ(params["q"]), str(params["label"])


def _comment(record):
    simple = "simple" if record["simple"] else "not simple"
    ordinary = "ordinary" if record["ordinary"] else "not ordinary"
    return (
        "HREF{%s}[LMFDB %s]. The class is %s, has p-rank %s, and is %s."
        % (record["url"], record["label"], simple, record["p_rank"], ordinary)
    )


class WeilPolynomialsOfAbelianVarieties(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T214")
    parameters = ("g", "q", "label")
    type = "Z[]"
    rigour = "exact"

    def enumerate(self):
        for record in records():
            yield {
                "g": record["g"],
                "q": record["q"],
                "label": record["label"],
            }

    def value(self, params, digits):
        record = records_by_key()[_coerce_params(params)]
        _check_record(record)
        return {
            "number": record["polynomial"],
            "comment": _comment(record),
        }


if __name__ == "__main__":
    _key_from_stdin()
    generator = WeilPolynomialsOfAbelianVarieties()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="Weil polynomials over prime fields, g <= 2"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
