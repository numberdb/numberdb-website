"""Condition numbers of the classical test matrices -- numberdb.org/T327.

For each listed default test matrix A_n this computes the finite 2-norm
condition number

    kappa_2(A_n) = sigma_max(A_n) / sigma_min(A_n).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The matrices are built over QQ. The singular values are obtained from the
eigenvalues of A^T A in Sage's algebraic real field, then converted to real
balls for storage. Singular default matrices are omitted, because their 2-norm
condition number is infinite rather than a finite real.
"""

import os
import sys
from functools import lru_cache
from math import comb, isfinite

import numberdb.sage as numberdb
from sage.matrix.constructor import matrix
from sage.rings.qqbar import AA, _init_qqbar
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField

_init_qqbar()

DIGITS = 100
WORKING_GUARD = 96
MIN_N = 2
MAX_N = 20
ZERO = QQ(0)
ONE = QQ(1)
HALF = QQ(1) / QQ(2)

FAMILIES = (
    'hilbert',
    'lehmer',
    'pascal',
    'redheffer',
    'vandermonde',
    'cauchy',
    'fiedler',
    'kms',
    'minij',
    'grcar',
    'frank',
    'wilkinson',
    'clement',
    'moler',
    'parter',
    'ris',
    'lotkin',
    'riemann',
    'second-difference',
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
    return QQ(1) / (QQ(2) ** abs(i - j))


def minij(i, j, n):
    return QQ(min(i + 1, j + 1))


def grcar(i, j, n):
    if i == j + 1:
        return QQ(-1)
    if i <= j <= i + 3:
        return ONE
    return ZERO


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


def triw(i, j, n, alpha=QQ(-1)):
    if i <= j:
        return ONE if i == j else alpha
    return ZERO


def moler(i, j, n):
    total = ZERO
    for k in range(n):
        total += triw(k, i, n) * triw(k, j, n)
    return total


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
    'hilbert': hilbert,
    'lehmer': lehmer,
    'pascal': pascal,
    'redheffer': redheffer,
    'vandermonde': vandermonde,
    'cauchy': cauchy,
    'fiedler': fiedler,
    'kms': kms,
    'minij': minij,
    'grcar': grcar,
    'frank': frank,
    'wilkinson': wilkinson,
    'clement': clement,
    'moler': moler,
    'parter': parter,
    'ris': ris,
    'lotkin': lotkin,
    'riemann': riemann,
    'second-difference': second_difference,
}


@lru_cache(maxsize=None)
def test_matrix(family, n):
    return matrix(QQ, n, n, lambda i, j: ENTRY[family](i, j, n))


@lru_cache(maxsize=None)
def singular(family, n):
    return test_matrix(family, n).det() == 0


@lru_cache(maxsize=None)
def condition_ball(family, n, digits):
    A = test_matrix(family, n)
    if A.det() == 0:
        raise ValueError('%s(%s) is singular' % (family, n))
    B = A.transpose() * A
    roots = []
    for root in B.eigenvalues():
        root = AA(root)
        if root > 0:
            roots.append(root)
        elif root != 0:
            raise ValueError('%s(%s) has a negative squared singular value %s'
                             % (family, n, root))
    if len(roots) != n:
        raise ValueError('%s(%s) has %d positive squared singular values, not %d'
                         % (family, n, len(roots), n))
    smallest = min(roots)
    largest = max(roots)
    field = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
    value = (field(largest) / field(smallest)).sqrt()
    approximate = float(value)
    nearest = round(approximate) if isfinite(approximate) else None
    if (nearest is not None and abs(nearest) <= 1000
            and abs(approximate - nearest) < 1e-12):
        exact_value = (largest / smallest).sqrt()
        try:
            rational = QQ(exact_value)
        except (TypeError, ValueError):
            pass
        else:
            return rational
    if not value.is_finite():
        raise ValueError(
            '%s(%s) produced a non-finite ball %s' % (family, n, value))
    return value


def _key_from_stdin():
    if os.environ.get('NUMBERDB_KEY_FROM_STDIN') != '1':
        return
    token = sys.stdin.read().strip()
    if '=' in token and token.split('=', 1)[0].isupper():
        token = token.split('=', 1)[1].strip().strip('"\'')
    if token:
        os.environ['NUMBERDB_API_KEY'] = token


class ClassicalTestMatrixConditionNumbers(numberdb.Generator):
    table = 'T327'
    parameters = ('family', 'n')
    type = 'R'
    digits = DIGITS
    rigour = 'proven'

    def enumerate(self, max_n=MAX_N):
        for family in FAMILIES:
            for n in range(MIN_N, max_n + 1):
                if singular(family, n):
                    continue
                yield {'family': family, 'n': str(n)}

    def value(self, params, digits):
        family = str(params['family'])
        n = int(params['n'])
        return condition_ball(family, n, digits)


if __name__ == '__main__':
    _key_from_stdin()
    generator = ClassicalTestMatrixConditionNumbers()
    if os.environ.get('NUMBERDB_PUBLISH') == '1' or '--publish' in sys.argv:
        print(generator.publish(
            message='computed finite condition numbers', removing=True))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
