"""Normalised Hecke eigenvalues of level one cusp forms -- numberdb.org/T325.

For the ith normalised Hecke eigenform in S_k(SL_2(Z)), ordered by increasing
real T_2-eigenvalue a_2, this stores a_p / p^((k-1)/2) for primes p <= 61.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The computation uses exact Hecke matrices. It expresses T_p as a polynomial in
T_2, evaluates that polynomial at the exact algebraic roots of the T_2
characteristic polynomial, and converts only the final normalised value to a
real ball.
"""

from decimal import Decimal
from itertools import permutations
import os
import sys

import numberdb.sage as numberdb
import sage.symbolic.expression
from sage.libs.pari import pari
from sage.misc.verbose import set_verbose
from sage.modular.modform.constructor import CuspForms
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.qqbar import AA
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField
from sage.rings.real_mpfr import RealField


set_verbose(-2)

MAX_WEIGHT = 40
PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41,
          43, 47, 53, 59, 61)
WORKING_GUARD = 160
COMMENT_DIGITS = 80
HECKE_SLUG = "Hecke_polynomials_of_level_one_cusp_forms"

ZX = PolynomialRing(ZZ, "x")
QX = PolynomialRing(QQ, "x")
xq = QX.gen()

_HECKE_MATRICES = {}
_T2_POWERS = {}
_T2_ROOTS = {}
_POLYNOMIALS_IN_T2 = {}
_A_P = {}
_COMMENTS = {}
_DELTA = None
_CHECKED = False


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def cusp_dimension(k):
    if k < 12 or k % 2:
        return 0
    if k % 12 == 2:
        return k // 12 - 1
    return k // 12


def _rows():
    for k in range(12, MAX_WEIGHT + 1, 2):
        dimension = cusp_dimension(k)
        if dimension == 0:
            continue
        for i in range(1, dimension + 1):
            for p in PRIMES:
                yield ZZ(k), ZZ(i), ZZ(p)


def _matrix_rows(matrix):
    return tuple(tuple(QQ(matrix[row, col]) for col in range(matrix.ncols()))
                 for row in range(matrix.nrows()))


def _identity(size):
    return tuple(tuple(QQ(1) if row == col else QQ(0)
                       for col in range(size))
                 for row in range(size))


def _matmul(left, right):
    size = len(left)
    product = []
    for row in range(size):
        out = []
        for col in range(size):
            total = QQ(0)
            for mid in range(size):
                total += left[row][mid] * right[mid][col]
            out.append(total)
        product.append(tuple(out))
    return tuple(product)


def _flatten(matrix):
    return tuple(entry for row in matrix for entry in row)


def _permutation_sign(perm):
    inversions = 0
    for i in range(len(perm)):
        for j in range(i + 1, len(perm)):
            if perm[i] > perm[j]:
                inversions += 1
    return -1 if inversions % 2 else 1


def _charpoly_from_rows(matrix):
    dimension = len(matrix)
    if dimension == 0:
        return ZX(1)
    total = QX(0)
    for perm in permutations(range(dimension)):
        term = QX(1)
        for row, col in enumerate(perm):
            entry = xq if row == col else QX(0)
            entry -= matrix[row][col]
            term *= entry
        if _permutation_sign(perm) == 1:
            total += term
        else:
            total -= term

    coefficients = []
    for coefficient in total.list():
        if coefficient.denominator() != 1:
            raise ArithmeticError("nonintegral characteristic coefficient %s"
                                  % coefficient)
        coefficients.append(ZZ(coefficient))
    return ZX(coefficients)


def _pari_charpoly(k, p):
    raw = pari("charpoly(mfheckemat(mfinit([1,%d], 0), %d))"
               % (int(k), int(p)))
    return ZX([ZZ(c) for c in raw.Vecrev()])


def _hecke_matrix(k, p):
    key = (ZZ(k), ZZ(p))
    if key not in _HECKE_MATRICES:
        space = CuspForms(1, int(k))
        matrix = _matrix_rows(space.hecke_matrix(int(p)))
        dimension = cusp_dimension(int(k))
        if len(matrix) != dimension:
            raise ArithmeticError("weight %s has matrix size %s, expected %s"
                                  % (k, len(matrix), dimension))
        found = _charpoly_from_rows(matrix)
        expected = _pari_charpoly(k, p)
        if found != expected:
            raise ArithmeticError(
                "Sage and PARI disagree for k=%s, p=%s: %s against %s"
                % (k, p, found, expected))
        _HECKE_MATRICES[key] = matrix
    return _HECKE_MATRICES[key]


def _t2_powers(k):
    k = ZZ(k)
    if k not in _T2_POWERS:
        t2 = _hecke_matrix(k, ZZ(2))
        powers = [_identity(len(t2))]
        while len(powers) < len(t2):
            powers.append(_matmul(powers[-1], t2))
        _T2_POWERS[k] = tuple(powers)
    return _T2_POWERS[k]


def _solve_overdetermined(rows, variables):
    rows = [[QQ(entry) for entry in row] for row in rows]
    rank = 0
    pivots = []
    for col in range(variables):
        pivot = None
        for row in range(rank, len(rows)):
            if rows[row][col] != 0:
                pivot = row
                break
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        scale = rows[rank][col]
        rows[rank] = [entry / scale for entry in rows[rank]]
        for row in range(len(rows)):
            if row != rank and rows[row][col] != 0:
                factor = rows[row][col]
                rows[row] = [rows[row][i] - factor * rows[rank][i]
                             for i in range(variables + 1)]
        pivots.append(col)
        rank += 1

    for row in rows:
        if all(row[col] == 0 for col in range(variables)) and row[-1] != 0:
            raise ArithmeticError("T_p is not a polynomial in T_2")
    if len(pivots) != variables:
        raise ArithmeticError("powers of T_2 are not independent")

    solution = [QQ(0)] * variables
    for row, col in enumerate(pivots):
        solution[col] = rows[row][-1]
    return tuple(solution)


def _polynomial_in_t2(k, p):
    key = (ZZ(k), ZZ(p))
    if key not in _POLYNOMIALS_IN_T2:
        target = _flatten(_hecke_matrix(k, p))
        powers = _t2_powers(k)
        columns = [_flatten(power) for power in powers]
        equations = []
        for row in range(len(target)):
            equations.append([column[row] for column in columns] + [target[row]])
        _POLYNOMIALS_IN_T2[key] = _solve_overdetermined(
            equations, len(powers))
    return _POLYNOMIALS_IN_T2[key]


def _t2_roots(k):
    k = ZZ(k)
    if k not in _T2_ROOTS:
        polynomial = _charpoly_from_rows(_hecke_matrix(k, ZZ(2)))
        roots = sorted(polynomial.roots(ring=AA, multiplicities=False))
        dimension = cusp_dimension(int(k))
        if len(roots) != dimension:
            raise ArithmeticError(
                "weight %s has %s T_2 roots, expected %s"
                % (k, len(roots), dimension))
        for before, after in zip(roots, roots[1:]):
            if before == after:
                raise ArithmeticError("weight %s has repeated a_2 roots" % k)
        _T2_ROOTS[k] = tuple(roots)
    return _T2_ROOTS[k]


def _evaluate(coefficients, alpha):
    total = AA(0)
    power = AA(1)
    for coefficient in coefficients:
        total += AA(coefficient) * power
        power *= alpha
    return total


def _a_p(k, i, p):
    key = (ZZ(k), ZZ(i), ZZ(p))
    if key not in _A_P:
        alpha = _t2_roots(k)[int(i) - 1]
        _A_P[key] = _evaluate(_polynomial_in_t2(k, p), alpha)
    return _A_P[key]


def _normalised_value(k, i, p, digits):
    field = RealBallField(numberdb.bits(int(digits), losing=WORKING_GUARD))
    denominator = field(p) ** (int(k) // 2 - 1) * field(p).sqrt()
    value = field(_a_p(k, i, p)) / denominator
    if not value.is_finite():
        raise ArithmeticError("non-finite value at k=%s, i=%s, p=%s"
                              % (k, i, p))
    if value.lower() < -2 or value.upper() > 2:
        raise ArithmeticError(
            "Deligne bound failed at k=%s, i=%s, p=%s: %s"
            % (k, i, p, value))
    return value


def _sigma_power(n, power):
    total = ZZ(0)
    for divisor in ZZ(n).divisors():
        total += divisor ** power
    return total


def _series_sub(left, right):
    return [left[i] - right[i] for i in range(len(left))]


def _series_scale(series, scalar):
    scalar = QQ(scalar)
    return [scalar * coefficient for coefficient in series]


def _series_mul(left, right):
    bound = len(left) - 1
    product = [QQ(0)] * (bound + 1)
    for i, left_i in enumerate(left):
        if left_i == 0:
            continue
        for j in range(bound + 1 - i):
            if right[j] != 0:
                product[i + j] += left_i * right[j]
    return product


def _series_pow(series, exponent):
    result = [QQ(0)] * len(series)
    result[0] = QQ(1)
    base = series
    exponent = int(exponent)
    while exponent:
        if exponent % 2:
            result = _series_mul(result, base)
        exponent //= 2
        if exponent:
            base = _series_mul(base, base)
    return result


def _delta_coefficients():
    global _DELTA
    if _DELTA is not None:
        return _DELTA
    bound = max(PRIMES)
    e4 = [QQ(0)] * (bound + 1)
    e6 = [QQ(0)] * (bound + 1)
    e4[0] = QQ(1)
    e6[0] = QQ(1)
    for n in range(1, bound + 1):
        e4[n] = QQ(240) * _sigma_power(n, 3)
        e6[n] = QQ(-504) * _sigma_power(n, 5)
    _DELTA = _series_scale(
        _series_sub(_series_pow(e4, 3), _series_pow(e6, 2)),
        QQ(1) / QQ(1728))
    if _DELTA[0] != 0 or _DELTA[1] != 1:
        raise ArithmeticError("Delta q-expansion was not normalised")
    return _DELTA


def _decimal(value):
    return Decimal(str(value).replace(" ", ""))


def _short_decimal(value):
    return format(_decimal(value), ".16g")


def _entry_comment(k, i):
    key = (ZZ(k), ZZ(i))
    if key in _COMMENTS:
        return _COMMENTS[key]
    field = RealField(numberdb.bits(COMMENT_DIGITS, losing=64))
    a2 = _short_decimal(field(_t2_roots(k)[int(i) - 1]))
    href = "HREF{%s#%s,2}[$\\chi_{%s,2}$]" % (HECKE_SLUG, k, k)
    if cusp_dimension(int(k)) == 1:
        comment = "$a_2=%s$, the root of %s." % (a2, href)
    else:
        comment = (
            "$a_2$ is root %s of %s in increasing order; $a_2\\approx %s."
            % (i, href, a2))
    _COMMENTS[key] = comment
    return comment


def _check_weight_12_tau():
    delta = _delta_coefficients()
    for p in PRIMES:
        tau = delta[int(p)]
        if tau.denominator() != 1:
            raise ArithmeticError("tau(%s) is not integral: %s" % (p, tau))
        found = _a_p(ZZ(12), ZZ(1), ZZ(p))
        if found != AA(ZZ(tau)):
            raise ArithmeticError(
                "weight 12 p=%s gives %s, expected tau(p)=%s"
                % (p, found, tau))


def _check_global():
    global _CHECKED
    if _CHECKED:
        return
    rows = list(_rows())
    if len(rows) != 432:
        raise ArithmeticError("got %s rows, expected 432" % len(rows))
    for k in range(12, MAX_WEIGHT + 1, 2):
        if cusp_dimension(k) == 0:
            continue
        _t2_roots(ZZ(k))
        for p in PRIMES:
            _polynomial_in_t2(ZZ(k), ZZ(p))
    _check_weight_12_tau()
    _CHECKED = True


class NormalisedLevelOneHeckeEigenvalues(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T325")
    parameters = ("k", "i", "p")
    type = "R"
    digits = 100
    rigour = "proven"
    files = ("generate.py",)

    def enumerate(self, max_weight=MAX_WEIGHT):
        if int(max_weight) != MAX_WEIGHT:
            raise ValueError("this draft covers weights up to %s" % MAX_WEIGHT)
        _check_global()
        for k, i, p in _rows():
            yield {"k": k, "i": i, "p": p}

    def value(self, params, digits):
        k = ZZ(params["k"])
        i = ZZ(params["i"])
        p = ZZ(params["p"])
        if (k, i, p) not in set(_rows()):
            raise ValueError("row outside this table: k=%s, i=%s, p=%s"
                             % (k, i, p))
        return {
            "number": _normalised_value(k, i, p, digits),
            "comment": _entry_comment(k, i),
        }


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
    generator = NormalisedLevelOneHeckeEigenvalues()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message=("normalised Hecke eigenvalues for level one cusp forms "
                     "with weights up to %d and primes up to %d")
                    % (MAX_WEIGHT, PRIMES[-1])))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
