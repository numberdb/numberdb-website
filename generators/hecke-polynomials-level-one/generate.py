"""Hecke polynomials of level one cusp forms -- numberdb.org/T215.

    chi_{k,p}(x) = det(x I - T_p | S_k(SL_2(Z)))

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The values are computed exactly from q-expansions. Level-one cusp forms are
Delta times polynomials in E4 and E6; the generator builds that monomial basis,
applies the Hecke formula coefficient by coefficient, and takes the
characteristic polynomial of the resulting exact matrix. Each row is compared
with PARI's mfheckemat and charpoly before it is returned.

The range $k\leq94$, $p\in\{2,3,5,7\}$ measured 164 entries, with a longest
entry of 1151 characters at $(94,7)$ and a 60.8 KB entries block. Adding weight
$96$ raised the longest entry to 1503 characters.
"""

import os
import sys
from itertools import permutations

import numberdb.sage as numberdb
from sage.libs.pari import pari
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ

MIN_WEIGHT = 12
MAX_WEIGHT = 94
PRIMES = (2, 3, 5, 7)
SERIES_BOUND = max(PRIMES) * (MAX_WEIGHT // 12 + 1)

QX = PolynomialRing(QQ, "x")
xq = QX.gen()
ZX = PolynomialRing(ZZ, "x")
xz = ZX.gen()

_E4 = None
_E6 = None
_DELTA = None
_BASIS = {}
_PIVOTS = {}
_CHARPOLY = {}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _sigma_power(n, power):
    total = ZZ(0)
    for d in ZZ(n).divisors():
        total += d ** power
    return total


def _add(a, b):
    return [a[i] + b[i] for i in range(SERIES_BOUND + 1)]


def _sub(a, b):
    return [a[i] - b[i] for i in range(SERIES_BOUND + 1)]


def _scale(a, c):
    c = QQ(c)
    return [c * a[i] for i in range(SERIES_BOUND + 1)]


def _mul(a, b):
    product = [QQ(0)] * (SERIES_BOUND + 1)
    for i, ai in enumerate(a):
        if ai == 0:
            continue
        for j in range(SERIES_BOUND + 1 - i):
            if b[j] != 0:
                product[i + j] += ai * b[j]
    return product


def _pow(a, exponent):
    result = [QQ(0)] * (SERIES_BOUND + 1)
    result[0] = QQ(1)
    base = a
    exponent = int(exponent)
    while exponent:
        if exponent % 2:
            result = _mul(result, base)
        exponent //= 2
        if exponent:
            base = _mul(base, base)
    return result


def _series():
    global _E4, _E6, _DELTA
    if _E4 is not None:
        return _E4, _E6, _DELTA

    _E4 = [QQ(0)] * (SERIES_BOUND + 1)
    _E6 = [QQ(0)] * (SERIES_BOUND + 1)
    _E4[0] = QQ(1)
    _E6[0] = QQ(1)
    for n in range(1, SERIES_BOUND + 1):
        _E4[n] = QQ(240) * _sigma_power(n, 3)
        _E6[n] = QQ(-504) * _sigma_power(n, 5)

    e4_cubed = _pow(_E4, 3)
    e6_squared = _pow(_E6, 2)
    _DELTA = _scale(_sub(e4_cubed, e6_squared), QQ(1) / QQ(1728))
    if _DELTA[0] != 0 or _DELTA[1] != 1:
        raise ArithmeticError("Delta q-expansion was not normalised")
    return _E4, _E6, _DELTA


def _basis_exponents(k):
    for b in range(0, (k - 12) // 6 + 1):
        rest = k - 12 - 6 * b
        if rest >= 0 and rest % 4 == 0:
            yield rest // 4, b


def _basis(k):
    k = ZZ(k)
    if k not in _BASIS:
        e4, e6, delta = _series()
        forms = []
        for a, b in _basis_exponents(int(k)):
            forms.append(_mul(delta, _mul(_pow(e4, a), _pow(e6, b))))
        _BASIS[k] = forms
    return _BASIS[k]


def _rank(rows):
    rows = [[QQ(c) for c in row] for row in rows]
    if not rows:
        return 0
    width = len(rows[0])
    rank = 0
    for col in range(width):
        pivot = None
        for r in range(rank, len(rows)):
            if rows[r][col] != 0:
                pivot = r
                break
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        scale = rows[rank][col]
        rows[rank] = [c / scale for c in rows[rank]]
        for r in range(len(rows)):
            if r != rank and rows[r][col] != 0:
                factor = rows[r][col]
                rows[r] = [rows[r][i] - factor * rows[rank][i]
                           for i in range(width)]
        rank += 1
        if rank == len(rows):
            break
    return rank


def _pivots(k):
    k = ZZ(k)
    if k in _PIVOTS:
        return _PIVOTS[k]
    basis = _basis(k)
    dim = len(basis)
    rows = []
    pivots = []
    for n in range(1, SERIES_BOUND + 1):
        candidate = [form[n] for form in basis]
        if _rank(rows + [candidate]) > len(rows):
            rows.append(candidate)
            pivots.append(n)
            if len(pivots) == dim:
                _PIVOTS[k] = pivots
                return pivots
    raise ArithmeticError("could not find enough q-expansion pivots for k=%s" % k)


def _solve(rows, vector):
    rows = [[QQ(c) for c in row] + [QQ(vector[i])]
            for i, row in enumerate(rows)]
    n = len(vector)
    for col in range(n):
        pivot = None
        for r in range(col, n):
            if rows[r][col] != 0:
                pivot = r
                break
        if pivot is None:
            raise ArithmeticError("singular pivot matrix")
        rows[col], rows[pivot] = rows[pivot], rows[col]
        scale = rows[col][col]
        rows[col] = [c / scale for c in rows[col]]
        for r in range(n):
            if r != col and rows[r][col] != 0:
                factor = rows[r][col]
                rows[r] = [rows[r][i] - factor * rows[col][i]
                           for i in range(n + 1)]
    return [rows[i][-1] for i in range(n)]


def _basis_matrix_at(k, pivots):
    basis = _basis(k)
    return [[form[n] for form in basis] for n in pivots]


def _hecke_coefficients(form, k, p, pivots):
    coefficients = []
    multiplier = ZZ(p) ** (ZZ(k) - 1)
    for n in pivots:
        value = form[p * n]
        if n % p == 0:
            value += multiplier * form[n // p]
        coefficients.append(value)
    return coefficients


def _hecke_matrix(k, p):
    pivots = _pivots(k)
    interpolation = _basis_matrix_at(k, pivots)
    columns = []
    for form in _basis(k):
        columns.append(_solve(interpolation, _hecke_coefficients(form, k, p, pivots)))
    dim = len(columns)
    return [[columns[col][row] for col in range(dim)] for row in range(dim)]


def _permutation_sign(perm):
    inversions = 0
    for i in range(len(perm)):
        for j in range(i + 1, len(perm)):
            if perm[i] > perm[j]:
                inversions += 1
    return -1 if inversions % 2 else 1


def _charpoly_from_matrix(matrix):
    dim = len(matrix)
    if dim == 0:
        return ZX(1)
    total = QX(0)
    for perm in permutations(range(dim)):
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
    raw = pari("charpoly(mfheckemat(mfinit([1,%d], 0), %d))" % (k, p))
    return ZX([ZZ(c) for c in raw.Vecrev()])


def _charpoly(k, p):
    key = (ZZ(k), ZZ(p))
    if key not in _CHARPOLY:
        matrix = _hecke_matrix(k, p)
        polynomial = _charpoly_from_matrix(matrix)
        expected = _pari_charpoly(k, p)
        if polynomial != expected:
            raise ArithmeticError(
                "q-expansion Hecke polynomial for k=%s, p=%s is %s, "
                "but PARI gives %s" % (k, p, polynomial, expected))
        if polynomial.degree() != len(_basis(k)):
            raise ArithmeticError("degree mismatch for k=%s, p=%s" % (k, p))
        _CHARPOLY[key] = polynomial
    return _CHARPOLY[key]


def _rows():
    for k in range(MIN_WEIGHT, MAX_WEIGHT + 1, 2):
        if not _basis(k):
            continue
        for p in PRIMES:
            yield ZZ(k), ZZ(p)


def _check_global():
    rows = list(_rows())
    if len(rows) != 164:
        raise ArithmeticError("got %s rows, expected 164" % len(rows))
    required = {
        (12, 2): xz + 24,
        (24, 2): xz**2 - 1080 * xz - 20468736,
        (36, 2): xz**3 - 139656 * xz**2 - 59208339456 * xz
                 - 1467625047588864,
    }
    for key, expected in required.items():
        found = _charpoly(*key)
        if found != expected:
            raise ArithmeticError("%s: got %s, expected %s"
                                  % (key, found, expected))


def _comment(k, p):
    degree = _charpoly(k, p).degree()
    if k == 12:
        return (
            "This is $x-\\tau(%s)$, where $\\tau(n)$ is the coefficient of "
            "$q^n$ in HREF{Q-expansion_of_the_modular_discriminant}"
            "[the modular discriminant $\\Delta$]." % p
        )
    return "The degree is $%s=\\dim S_{%s}(\\mathrm{SL}_2(\\mathbb{Z}))$." % (
        degree, k)


class LevelOneHeckePolynomials(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T215")
    parameters = ("k", "p")
    type = "Z[]"
    rigour = "exact"

    def enumerate(self):
        _check_global()
        for k, p in _rows():
            yield {"k": k, "p": p}

    def value(self, params, digits):
        k, p = ZZ(params["k"]), ZZ(params["p"])
        if (k, p) not in set(_rows()):
            raise ValueError("row outside this table: k=%s, p=%s" % (k, p))
        return {
            "number": _charpoly(k, p),
            "comment": _comment(k, p),
        }


if __name__ == "__main__":
    _key_from_stdin()
    generator = LevelOneHeckePolynomials()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="Hecke polynomials on level-one cusp forms"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
