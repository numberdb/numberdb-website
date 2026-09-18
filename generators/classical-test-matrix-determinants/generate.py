"""Determinants of the classical test matrices -- numberdb.org/T331.

For each listed default test matrix A_n this computes the exact determinant

    det(A_n).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The matrices are built over QQ. Determinants are computed by an exact Bareiss
elimination written here, and checked against closed forms, recurrences and a
direct permutation determinant on small orders.
"""

import os
import sys
from functools import lru_cache
from itertools import permutations
from math import comb

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ

TABLE = os.environ.get("NUMBERDB_TABLE", "T331")
MIN_N = 2
MAX_N = 30
DIRECT_CHECK_N = 6
ZERO = QQ(0)
ONE = QQ(1)
HALF = QQ(1) / QQ(2)

FAMILIES = (
    "hilbert",
    "lehmer",
    "vandermonde",
    "cauchy",
    "fiedler",
    "kms",
    "grcar",
    "wilkinson",
    "clement",
    "parter",
    "ris",
    "lotkin",
    "riemann",
)

OMITTED_FAMILIES = (
    "pascal",
    "redheffer",
    "minij",
    "chow",
    "frank",
    "moler",
    "second-difference",
)

ALL_FAMILIES = (
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
def matrix_entries(family, n):
    return tuple(
        tuple(ENTRY[family](i, j, n) for j in range(n))
        for i in range(n)
    )


def _bareiss_determinant(entries):
    n = len(entries)
    if n == 0:
        return ONE
    a = [[QQ(value) for value in row] for row in entries]
    sign = ONE
    previous = ONE

    for k in range(n - 1):
        pivot_row = None
        for row in range(k, n):
            if a[row][k] != 0:
                pivot_row = row
                break
        if pivot_row is None:
            return ZERO
        if pivot_row != k:
            a[k], a[pivot_row] = a[pivot_row], a[k]
            sign = -sign

        pivot = a[k][k]
        for i in range(k + 1, n):
            for j in range(k + 1, n):
                a[i][j] = (a[i][j] * pivot - a[i][k] * a[k][j]) / previous
        previous = pivot
        for i in range(k + 1, n):
            a[i][k] = ZERO

    return sign * a[n - 1][n - 1]


def _permutation_sign(perm):
    inversions = 0
    for i in range(len(perm)):
        for j in range(i + 1, len(perm)):
            if perm[i] > perm[j]:
                inversions += 1
    return -ONE if inversions % 2 else ONE


def _leibniz_determinant(entries):
    total = ZERO
    for perm in permutations(range(len(entries))):
        term = _permutation_sign(perm)
        for i, j in enumerate(perm):
            term *= entries[i][j]
        total += term
    return total


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


def _lehmer_determinant(n):
    product = ONE
    for j in range(2, n + 1):
        product *= QQ(2 * j - 1) / QQ(j * j)
    return product


def _vandermonde_determinant(n):
    product = ONE
    for i in range(1, n + 1):
        for j in range(i + 1, n + 1):
            product *= QQ(j - i)
    return product


def _cauchy_determinant(x_values, y_values, scale=ONE):
    numerator = ONE
    denominator = ONE
    n = len(x_values)
    for i in range(n):
        for j in range(i + 1, n):
            numerator *= (x_values[j] - x_values[i]) * (y_values[j] - y_values[i])
    for x in x_values:
        for y in y_values:
            denominator *= x + y
    return (scale ** n) * numerator / denominator


def _cauchy_matrix_determinant(n):
    return _cauchy_determinant(
        tuple(QQ(i) for i in range(1, n + 1)),
        tuple(QQ(j) for j in range(1, n + 1)),
    )


def _parter_determinant(n):
    return _cauchy_determinant(
        tuple(QQ(i) for i in range(1, n + 1)),
        tuple(HALF - QQ(j) for j in range(1, n + 1)),
    )


def _ris_determinant(n):
    return _cauchy_determinant(
        tuple(-QQ(i) for i in range(1, n + 1)),
        tuple(QQ(n - j) + QQ(3) / QQ(2) for j in range(1, n + 1)),
        scale=HALF,
    )


def _fiedler_determinant(n):
    return QQ((-1) ** (n - 1)) * (QQ(2) ** (n - 2)) * QQ(n - 1)


def _kms_determinant(n):
    return (QQ(3) / QQ(4)) ** (n - 1)


def _grcar_determinant(n):
    values = [ONE, ONE, QQ(2), QQ(4), QQ(8)]
    if n < len(values):
        return values[n]
    for k in range(5, n + 1):
        values.append(values[k - 1] + values[k - 2] + values[k - 3] + values[k - 4])
    return values[n]


def _wilkinson_determinant(n):
    previous = ONE
    current = abs(QQ(n - 1) / QQ(2))
    if n == 0:
        return previous
    if n == 1:
        return current
    for j in range(2, n + 1):
        diagonal = abs(QQ(n - 1) / QQ(2) - QQ(j - 1))
        previous, current = current, diagonal * current - previous
    return current


def _clement_determinant(n):
    if n % 2:
        return ZERO
    product = ONE
    for j in range(1, n // 2 + 1):
        product *= QQ(2 * j - 1) ** 2
    return QQ((-1) ** (n // 2)) * product


def _lotkin_determinant(n):
    return QQ((-1) ** (n - 1)) * QQ(n) * _hilbert_determinant(n)


def _expected_determinant(family, n):
    if family == "hilbert":
        return _hilbert_determinant(n)
    if family == "lehmer":
        return _lehmer_determinant(n)
    if family == "vandermonde":
        return _vandermonde_determinant(n)
    if family == "cauchy":
        return _cauchy_matrix_determinant(n)
    if family == "fiedler":
        return _fiedler_determinant(n)
    if family == "kms":
        return _kms_determinant(n)
    if family == "grcar":
        return _grcar_determinant(n)
    if family == "wilkinson":
        return _wilkinson_determinant(n)
    if family == "clement":
        return _clement_determinant(n)
    if family == "parter":
        return _parter_determinant(n)
    if family == "ris":
        return _ris_determinant(n)
    if family == "lotkin":
        return _lotkin_determinant(n)
    return None


def _omitted_expected_determinant(family, n):
    if family in ("pascal", "minij", "frank", "moler"):
        return ONE
    if family == "chow":
        return ZERO
    if family == "redheffer":
        return QQ(_mertens(n))
    if family == "second-difference":
        return QQ(n + 1)
    raise ValueError("no omitted determinant formula for %s" % family)


@lru_cache(maxsize=None)
def determinant(family, n):
    entries = matrix_entries(family, n)
    value = _bareiss_determinant(entries)

    expected = _expected_determinant(family, n)
    if expected is not None:
        _assert_equal(family, n, "closed determinant", value, expected)

    if n <= DIRECT_CHECK_N:
        _assert_equal(family, n, "Leibniz determinant", value,
                      _leibniz_determinant(entries))

    return value


@lru_cache(maxsize=None)
def _verify_omitted_families(max_n):
    for family in OMITTED_FAMILIES:
        for n in range(MIN_N, max_n + 1):
            value = _bareiss_determinant(matrix_entries(family, n))
            expected = _omitted_expected_determinant(family, n)
            _assert_equal(family, n, "omitted-family formula", value, expected)


class ClassicalTestMatrixDeterminants(numberdb.Generator):
    table = TABLE
    parameters = ("family", "n")
    type = "Q"
    rigour = "exact"

    def enumerate(self, max_n=MAX_N):
        _verify_omitted_families(max_n)
        for family in FAMILIES:
            for n in range(MIN_N, max_n + 1):
                if family == "clement" and n % 2:
                    continue
                yield {"family": family, "n": str(n)}

    def value(self, params, digits):
        family = str(params["family"])
        n = int(params["n"])
        if family not in FAMILIES:
            raise ValueError("unknown family %r" % (family,))
        if n < MIN_N or n > MAX_N:
            raise ValueError("n=%s is outside this table" % (n,))
        if family == "clement" and n % 2:
            raise ValueError("the odd Clement matrices are singular and omitted")
        return determinant(family, n)


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
    generator = ClassicalTestMatrixDeterminants()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message=("determinants of classical test matrices for "
                     "orders %d through %d") % (MIN_N, MAX_N)))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
