"""Weight enumerators of the maximum distance separable codes -- numberdb.org/T389

For each stored triple (q, n, k), this gives the dehomogenised weight
enumerator W_{q,n,k}(x) of a q-ary linear [n,k,n-k+1]_q MDS code.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The stored range is every prime power q <= 19 and every 1 <= k <= n <= q + 1.
Generalized Reed-Solomon codes certify existence throughout this range, and
the weight enumerator depends only on q, n and k.
"""

import os
import sys
from itertools import product
from math import comb

import numberdb.sage as numberdb
from sage.rings.finite_rings.finite_field_constructor import GF
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


TABLE = "T389"
MAX_Q = 19

_R = PolynomialRing(ZZ, "x")
_x = _R.gen()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _is_prime(n):
    if n < 2:
        return False
    d = 2
    while d * d <= n:
        if n % d == 0:
            return False
        d += 1
    return True


def prime_powers_up_to(bound):
    values = set()
    for p in range(2, bound + 1):
        if not _is_prime(p):
            continue
        q = p
        while q <= bound:
            values.add(q)
            q *= p
    return sorted(values)


def mds_weight_count(q, n, k, weight):
    if weight == 0:
        return ZZ.one()
    distance = n - k + 1
    if weight < distance:
        return ZZ.zero()

    total = ZZ.zero()
    for j in range(weight - distance + 1):
        total += (
            ZZ(-1) ** j
            * ZZ(comb(weight, j))
            * (ZZ(q) ** (weight - distance + 1 - j) - 1)
        )
    return ZZ(comb(n, weight)) * total


def mds_weight_enumerator(q, n, k):
    return sum(mds_weight_count(q, n, k, w) * _x ** w for w in range(n + 1))


def krawtchouk_hamming(q, n, r, w):
    return sum(
        ZZ(-1) ** j
        * ZZ(q - 1) ** (r - j)
        * ZZ(comb(w, j))
        * ZZ(comb(n - w, r - j))
        for j in range(r + 1)
        if j <= w and r - j <= n - w
    )


def macwilliams_dual_counts(q, n, k):
    source = [mds_weight_count(q, n, k, w) for w in range(n + 1)]
    scale = ZZ(q) ** k
    transformed = []
    for r in range(n + 1):
        total = sum(source[w] * krawtchouk_hamming(q, n, r, w)
                    for w in range(n + 1))
        if total % scale != 0:
            raise ArithmeticError("MacWilliams transform was not integral")
        transformed.append(total // scale)
    return transformed


def _field_elements(field):
    return list(field)


def _evaluate_at_infinity(coefficients):
    if not coefficients:
        return ZZ.zero()
    return coefficients[-1]


def grs_weight_enumerator_by_enumeration(q, n, k):
    field = GF(q)
    finite_points = _field_elements(field)
    use_infinity = n == q + 1
    if use_infinity:
        points = finite_points
    else:
        points = finite_points[:n]

    counts = [ZZ.zero()] * (n + 1)
    for raw_coefficients in product(finite_points, repeat=k):
        coefficients = list(raw_coefficients)
        word = []
        for point in points:
            value = field.zero()
            power = field.one()
            for coefficient in coefficients:
                value += coefficient * power
                power *= point
            word.append(value)
        if use_infinity:
            word.append(_evaluate_at_infinity(coefficients))
        weight = sum(1 for value in word if value != 0)
        counts[weight] += 1
    return sum(counts[w] * _x ** w for w in range(n + 1))


def entry_note(q, n, k):
    if (q, n, k) == (3, 4, 2):
        return "These are the parameters of the ternary tetracode."
    if (q, n, k) == (4, 6, 3):
        return "These are the parameters of the hexacode."
    return None


class MDSWeightEnumerators(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", TABLE)
    parameters = ("q", "n", "k")
    type = "Z[]"
    rigour = "exact"

    def enumerate(self, max_q=MAX_Q):
        for q in prime_powers_up_to(max_q):
            for n in range(1, q + 2):
                for k in range(1, n + 1):
                    yield {"q": str(q), "n": str(n), "k": str(k)}

    def value(self, params, digits):
        q = int(params["q"])
        n = int(params["n"])
        k = int(params["k"])
        number = mds_weight_enumerator(q, n, k)
        comment = entry_note(q, n, k)
        if comment is None:
            return number
        return {"number": number, "comment": comment}


def run_integrity_checks(max_q=MAX_Q):
    for params in MDSWeightEnumerators().enumerate(max_q=max_q):
        q = int(params["q"])
        n = int(params["n"])
        k = int(params["k"])
        polynomial = mds_weight_enumerator(q, n, k)
        distance = n - k + 1

        if polynomial(1) != ZZ(q) ** k:
            raise ArithmeticError("wrong total count at q=%d, n=%d, k=%d"
                                  % (q, n, k))
        for weight in range(1, distance):
            if polynomial.monomial_coefficient(_x ** weight) != 0:
                raise ArithmeticError("nonzero coefficient below distance")

        if k < n:
            dual = [mds_weight_count(q, n, n - k, w) for w in range(n + 1)]
            if macwilliams_dual_counts(q, n, k) != dual:
                raise ArithmeticError("MacWilliams check failed at q=%d, n=%d, k=%d"
                                      % (q, n, k))

    for q in (2, 3, 4, 5):
        for n in range(1, q + 2):
            for k in range(1, n + 1):
                expected = grs_weight_enumerator_by_enumeration(q, n, k)
                formula = mds_weight_enumerator(q, n, k)
                if formula != expected:
                    raise ArithmeticError(
                        "GRS enumeration disagrees at q=%d, n=%d, k=%d"
                        % (q, n, k))


def fill_draft_once(generator, message):
    """Fill a fresh draft without the client's empty upsert probe."""
    from numberdb._generate import (
        _check_precision,
        _check_rigour,
        _producer,
        _run_name,
        _source_files,
    )
    from numberdb._write import Entries, attach, submit_entries, to_text

    table = generator.table
    run = _run_name(generator)
    entries = Entries(*generator.parameters)

    for params in generator.enumerate():
        params = dict(params)
        wanted = generator.digits_for(params)
        entry = generator._entry(params, wanted)
        value = entry["number"]
        identity = ",".join(str(params[name]) for name in generator.parameters)
        _check_rigour(generator, table, identity, value)

        written = to_text(value, wanted, generator.format)
        _check_precision(table, identity, written, wanted, lowering=False)

        record = dict(entry)
        record.pop("digits", None)
        entries.add(**params, **record, digits=wanted)

    answer = submit_entries(
        table,
        entries,
        message=message,
        produced_by=_producer(generator, os.environ.get("NUMBERDB_ASSISTED_BY", "")),
        upsert=False,
        run=run,
        rigour=generator.rigour,
    )

    for name, body in sorted(_source_files(generator).items()):
        attach(table, name, body, run=run, message=message,
               rigour=generator.rigour)

    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = MDSWeightEnumerators()
    run_integrity_checks()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="exact MDS weight enumerators"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
