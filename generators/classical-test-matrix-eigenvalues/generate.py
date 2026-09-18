"""Eigenvalues of the classical symmetric test matrices -- numberdb.org/T329.

For each listed symmetric default test matrix A_n this computes every real
eigenvalue, ordered increasingly:

    lambda_1(A_n) <= ... <= lambda_n(A_n).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The matrices are built over QQ. The characteristic polynomial is computed
exactly and its real roots are isolated in Sage's algebraic real field, then
converted to real balls for storage. Roots that are proved rational are
returned exactly.
"""

import os
import sys
from functools import lru_cache
from math import comb

import numberdb.sage as numberdb
from sage.matrix.constructor import matrix
from sage.rings.qqbar import AA, QQbar, _init_qqbar
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField

_init_qqbar()

TABLE = os.environ.get("NUMBERDB_TABLE", "T329")
DIGITS = 100
WORKING_GUARD = 96
MIN_N = 2
MAX_N = 12
ZERO = QQ(0)
ONE = QQ(1)
HALF = QQ(1) / QQ(2)

FAMILIES = (
    "hilbert",
    "lehmer",
    "pascal",
    "cauchy",
    "fiedler",
    "kms",
    "minij",
    "wilkinson",
    "moler",
    "ris",
    "second-difference",
)


def hilbert(i, j, n):
    return ONE / QQ(i + j + 1)


def lehmer(i, j, n):
    a, b = i + 1, j + 1
    return QQ(min(a, b)) / QQ(max(a, b))


def pascal(i, j, n):
    return QQ(comb(i + j, i))


def cauchy(i, j, n):
    return ONE / QQ(i + j + 2)


def fiedler(i, j, n):
    return QQ(abs(i - j))


def kms(i, j, n):
    return QQ(1) / (QQ(2) ** abs(i - j))


def minij(i, j, n):
    return QQ(min(i + 1, j + 1))


def wilkinson(i, j, n):
    if i == j:
        return abs(QQ(n - 1) / QQ(2) - QQ(i))
    if abs(i - j) == 1:
        return ONE
    return ZERO


def triw(i, j, n, alpha=QQ(-1)):
    if i <= j:
        return ONE if i == j else alpha
    return ZERO


def moler(i, j, n):
    total = ZERO
    for row in range(n):
        total += triw(row, i, n) * triw(row, j, n)
    return total


def ris(i, j, n):
    return HALF / (QQ(n - i - j) - HALF)


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
    "cauchy": cauchy,
    "fiedler": fiedler,
    "kms": kms,
    "minij": minij,
    "wilkinson": wilkinson,
    "moler": moler,
    "ris": ris,
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


def _cos_pi_rational(numerator, denominator):
    zeta = QQbar.zeta(2 * int(denominator)) ** int(numerator)
    return AA((zeta + zeta ** (-1)) / 2)


def _minij_eigenvalue(k, n):
    c = _cos_pi_rational(k, 2 * n + 1)
    return AA(ONE) / (AA(4) * c * c)


def _second_difference_eigenvalue(k, n):
    return AA(2) - AA(2) * _cos_pi_rational(k, n + 1)


def _assert_equal(family, n, what, left, right):
    if left != right:
        raise ArithmeticError(
            "%s(%s): %s mismatch: %s != %s" % (family, n, what, left, right)
        )


def _verify_charpoly(family, n, mat, polynomial):
    _assert_equal(
        family, n, "trace coefficient", polynomial[n - 1], -mat.trace()
    )
    _assert_equal(
        family, n, "determinant coefficient",
        polynomial[0], ((-1) ** n) * mat.det()
    )


def _verify_roots(family, n, roots):
    if len(roots) != n:
        raise ArithmeticError(
            "%s(%s) has %d real roots, not %d" % (family, n, len(roots), n)
        )

    if family == "minij":
        for k, root in enumerate(roots, 1):
            _assert_equal(family, n, "closed form k=%d" % k,
                          root, _minij_eigenvalue(k, n))

    if family == "second-difference":
        for k, root in enumerate(roots, 1):
            _assert_equal(family, n, "closed form k=%d" % k,
                          root, _second_difference_eigenvalue(k, n))

    if family == "pascal":
        for i in range(n // 2):
            _assert_equal(family, n, "reciprocal pair %d" % (i + 1),
                          roots[i] * roots[-i - 1], AA(1))
        if n % 2:
            _assert_equal(family, n, "middle eigenvalue", roots[n // 2], AA(1))


@lru_cache(maxsize=None)
def eigenvalues(family, n):
    mat = test_matrix(family, n)
    polynomial = mat.charpoly()
    _verify_charpoly(family, n, mat, polynomial)
    roots = []
    for root, multiplicity in polynomial.roots(ring=AA, multiplicities=True):
        roots.extend([AA(root)] * int(multiplicity))
    roots = tuple(sorted(roots))
    _verify_roots(family, n, roots)
    return roots


def _exact_rational(root):
    try:
        return QQ(root)
    except (TypeError, ValueError, ArithmeticError):
        return None


def eigenvalue(family, n, k, digits):
    root = eigenvalues(family, n)[k - 1]
    rational = _exact_rational(root)
    if rational is not None:
        return rational
    field = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
    value = field(root)
    if not value.is_finite():
        raise ValueError(
            "%s(%s,%s) produced a non-finite ball %s" % (family, n, k, value)
        )
    return value


class ClassicalTestMatrixEigenvalues(numberdb.Generator):
    table = TABLE
    parameters = ("family", "n", "k")
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self, max_n=MAX_N):
        for family in FAMILIES:
            for n in range(MIN_N, max_n + 1):
                for k in range(1, n + 1):
                    yield {"family": family, "n": str(n), "k": str(k)}

    def value(self, params, digits):
        family = str(params["family"])
        n = int(params["n"])
        k = int(params["k"])
        if family not in ENTRY:
            raise ValueError("unknown family %r" % (family,))
        if n < MIN_N or n > MAX_N:
            raise ValueError("n=%s is outside this table" % (n,))
        if k < 1 or k > n:
            raise ValueError("k=%s is outside 1..%s" % (k, n))
        return eigenvalue(family, n, k, digits)


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
    generator = ClassicalTestMatrixEigenvalues()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message=("eigenvalues of classical symmetric test matrices "
                     "for orders %d through %d") % (MIN_N, MAX_N)))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
