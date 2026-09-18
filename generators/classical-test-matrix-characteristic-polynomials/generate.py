"""Characteristic polynomials of the classical test matrices -- numberdb.org/T330.

For each listed default test matrix A_n this computes

    chi_{A_n}(x) = det(x I_n - A_n).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The matrices are built over QQ and the characteristic polynomials are returned
exactly in QQ[x].
"""

import os
import sys
from functools import lru_cache
from itertools import permutations
from math import comb

import numberdb.sage as numberdb
from sage.matrix.constructor import matrix
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ

TABLE = os.environ.get("NUMBERDB_TABLE", "T330")
MIN_N = 2
MAX_N = 12
ZERO = QQ(0)
ONE = QQ(1)
HALF = QQ(1) / QQ(2)
R = PolynomialRing(QQ, "x")
X = R.gen()

FAMILIES = (
    "hilbert",
    "lehmer",
    "pascal",
    "redheffer",
    "vandermonde",
    "cauchy",
    "fiedler",
    "kms",
    "minij",
    "grcar",
    "chow",
    "frank",
    "wilkinson",
    "clement",
    "moler",
    "parter",
    "ris",
    "lotkin",
    "riemann",
    "second-difference",
)


def hilbert(i, j, n):
    return ONE / QQ(i + j + 1)


def lehmer(i, j, n):
    a, b = i + 1, j + 1
    return QQ(min(a, b)) / QQ(max(a, b))


def pascal(i, j, n):
    return QQ(comb(i + j, i))


def redheffer(i, j, n):
    a, b = i + 1, j + 1
    return ONE if b == 1 or b % a == 0 else ZERO


def vandermonde(i, j, n):
    return QQ(i + 1) ** j


def cauchy(i, j, n):
    return ONE / QQ(i + j + 2)


def fiedler(i, j, n):
    return QQ(abs(i - j))


def kms(i, j, n):
    return ONE / (QQ(2) ** abs(i - j))


def minij(i, j, n):
    return QQ(min(i + 1, j + 1))


def grcar(i, j, n):
    if i == j + 1:
        return QQ(-1)
    if i <= j <= i + 3:
        return ONE
    return ZERO


def chow(i, j, n):
    return ONE if j <= i + 1 else ZERO


def frank(i, j, n):
    if j < i - 1:
        return ZERO
    return QQ(n - max(i, j))


def wilkinson(i, j, n):
    if i == j:
        return abs(QQ(n - 1) / QQ(2) - QQ(i))
    if abs(i - j) == 1:
        return ONE
    return ZERO


def clement(i, j, n):
    if i == j + 1:
        return QQ(n - j - 1)
    if j == i + 1:
        return QQ(j)
    return ZERO


def moler(i, j, n):
    if i == j:
        return QQ(i + 1)
    return QQ(min(i + 1, j + 1) - 2)


def parter(i, j, n):
    return ONE / (QQ(i - j) + HALF)


def ris(i, j, n):
    return HALF / (QQ(n - i - j) - HALF)


def lotkin(i, j, n):
    if i == 0:
        return ONE
    return hilbert(i, j, n)


def riemann(i, j, n):
    a, b = i + 2, j + 2
    return QQ(a - 1) if b % a == 0 else QQ(-1)


def second_difference(i, j, n):
    if i == j:
        return QQ(2)
    if abs(i - j) == 1:
        return QQ(-1)
    return ZERO


ENTRY = {
    "hilbert": hilbert,
    "lehmer": lehmer,
    "pascal": pascal,
    "redheffer": redheffer,
    "vandermonde": vandermonde,
    "cauchy": cauchy,
    "fiedler": fiedler,
    "kms": kms,
    "minij": minij,
    "grcar": grcar,
    "chow": chow,
    "frank": frank,
    "wilkinson": wilkinson,
    "clement": clement,
    "moler": moler,
    "parter": parter,
    "ris": ris,
    "lotkin": lotkin,
    "riemann": riemann,
    "second-difference": second_difference,
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


@lru_cache(maxsize=None)
def test_matrix(family, n):
    return matrix(QQ, n, n, lambda i, j: ENTRY[family](i, j, n))


def _assert_equal(family, n, what, left, right):
    if left != right:
        raise ArithmeticError(
            "%s(%s): %s mismatch: %s != %s" % (family, n, what, left, right)
        )


def _mobius(k):
    factors = ZZ(k).factor()
    for _prime, exponent in factors:
        if exponent > 1:
            return ZZ(0)
    return ZZ(-1) ** len(factors)


def _mertens(n):
    return sum(_mobius(k) for k in range(1, n + 1))


def _hilbert_determinant(n):
    c_n = QQ(1)
    for k in range(1, n):
        c_n *= QQ(k) ** (n - k)
    c_2n = QQ(1)
    for k in range(1, 2 * n):
        c_2n *= QQ(k) ** (2 * n - k)
    return (c_n ** 4) / c_2n


def _vandermonde_determinant(n):
    product = QQ(1)
    for i in range(1, n + 1):
        for j in range(i + 1, n + 1):
            product *= QQ(j - i)
    return product


def _clement_polynomial(n):
    polynomial = R(1)
    for value in range(n - 1, -n, -2):
        polynomial *= X - QQ(value)
    return polynomial


def _second_difference_polynomial(n):
    previous = R(1)
    current = X - QQ(2)
    if n == 0:
        return previous
    if n == 1:
        return current
    for _ in range(2, n + 1):
        previous, current = current, (X - QQ(2)) * current - previous
    return current


def _permutation_sign(perm):
    inversions = 0
    for i in range(len(perm)):
        for j in range(i + 1, len(perm)):
            if perm[i] > perm[j]:
                inversions += 1
    return -1 if inversions % 2 else 1


def _leibniz_charpoly(mat):
    n = mat.nrows()
    total = R(0)
    for perm in permutations(range(n)):
        term = R(_permutation_sign(perm))
        for i, j in enumerate(perm):
            entry = X if i == j else R(0)
            term *= entry - R(mat[i, j])
        total += term
    return total


def _verify_polynomial(family, n, mat, polynomial):
    _assert_equal(family, n, "degree", polynomial.degree(), n)
    _assert_equal(family, n, "leading coefficient", polynomial[n], QQ(1))
    _assert_equal(family, n, "trace coefficient", polynomial[n - 1], -mat.trace())
    _assert_equal(
        family,
        n,
        "determinant coefficient",
        polynomial[0],
        ((-1) ** n) * mat.det(),
    )

    if n <= 5:
        _assert_equal(family, n, "Leibniz determinant", polynomial, _leibniz_charpoly(mat))

    if family == "redheffer":
        _assert_equal(family, n, "Mertens determinant", mat.det(), QQ(_mertens(n)))
    if family == "frank":
        _assert_equal(family, n, "Frank determinant", mat.det(), QQ(1))
    if family == "hilbert":
        _assert_equal(family, n, "Hilbert determinant", mat.det(), _hilbert_determinant(n))
    if family == "vandermonde":
        _assert_equal(family, n, "Vandermonde determinant", mat.det(), _vandermonde_determinant(n))
    if family == "clement":
        _assert_equal(family, n, "Clement spectrum", polynomial, _clement_polynomial(n))
    if family == "second-difference":
        _assert_equal(
            family,
            n,
            "second-difference recurrence",
            polynomial,
            _second_difference_polynomial(n),
        )


@lru_cache(maxsize=None)
def characteristic_polynomial(family, n):
    mat = test_matrix(family, n)
    polynomial = R(mat.charpoly())
    _verify_polynomial(family, n, mat, polynomial)
    return polynomial


class ClassicalTestMatrixCharacteristicPolynomials(numberdb.Generator):
    table = TABLE
    parameters = ("family", "n")
    type = "Q[]"
    rigour = "exact"

    def enumerate(self, max_n=MAX_N):
        for family in FAMILIES:
            for n in range(MIN_N, max_n + 1):
                yield {"family": family, "n": str(n)}

    def value(self, params, digits):
        family = str(params["family"])
        n = int(params["n"])
        if family not in ENTRY:
            raise ValueError("unknown family %r" % (family,))
        if n < MIN_N or n > MAX_N:
            raise ValueError("n=%s is outside this table" % (n,))
        return characteristic_polynomial(family, n)


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
        attach(table, name, body, run=run, message=message, rigour=generator.rigour)

    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = ClassicalTestMatrixCharacteristicPolynomials()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(
            fill_draft_once(
                generator,
                message=(
                    "characteristic polynomials of classical test matrices "
                    "for orders %d through %d"
                )
                % (MIN_N, MAX_N),
            )
        )
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
