"""Values zeta_K(s) of Dedekind zeta functions of real quadratic fields at s = -1, -3, -5 -- numberdb.org/T130

    zeta_K(1 - 2m) = zeta(1 - 2m) L(1 - 2m, chi_D) = B_{2m} B_{2m, chi_D} / (2m)^2,

for K = Q(sqrt D), D a fundamental discriminant with 1 < D <= 1000, and
m = 1, 2, 3. Rational, by the Siegel-Klingen theorem, and positive.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**Every value is exact.** B_{2m} is Sage's Bernoulli number, and the
generalized Bernoulli number B_{k,chi} = q^(k-1) sum_{a=1}^q chi(a) B_k(a/q) is
built from Bernoulli polynomials evaluated at rationals, every division
between elements of QQ.

**Every value is checked twice before it is returned**, by computations that
share nothing with the Bernoulli route but the discriminant. At s = -1 it must
equal Siegel's formula zeta_K(-1) = (1/60) sum sigma_1((D - b^2)/4), the sum
over b^2 < D with b = D mod 2, which uses no character and no Bernoulli number.
At every s, the functional equation

    zeta_K(2m) = 2^(4m) m^2 pi^(4m) / ((2m)!)^2 / D^(2m - 1/2) * zeta_K(1 - 2m)

must hold as balls, with zeta_K(2m) = zeta(2m) L(2m, chi_D) computed from arb's
Hurwitz zeta function at 256 bits. A value that fails either is an error rather
than an entry. When this was written the controls failed as they must: 1/61 in
place of Siegel's 1/60 agreed nowhere, and the rational scaled by 1 + 1e-30
overlapped nothing (the worst ball had radius 3e-74).

Outside the generator the values were also compared with PARI's lfun on
lfuncreate(x^2 - D) for 121 discriminants (worst relative difference 5e-60),
with the generalized Bernoulli numbers the corpus stores in T49 for D = 5 and
D = 8 through k = 40, and with OEIS A370411/A370412, which hold
zeta_K(2n) sqrt(D) / pi^(4n) for the first five real quadratic fields.

**The range is decided by what is looked up, not by size.** The entries are
short (18 characters at most); s = -1 is the value that appears in Hirzebruch's
Euler number of the Hilbert modular surface and in Siegel's formula, s = -3 and
s = -5 are the next constant terms of Hilbert Eisenstein series, and D <= 1000
is the enumeration of the residue table T128. Beyond that, few of these numbers
are anything a person meets.
"""

import sys

import numberdb.sage as numberdb
from sage.arith.misc import (bernoulli, binomial, factorial, is_squarefree,
                             kronecker_symbol, sigma)
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField

#: Every real fundamental discriminant up to here: 302 of them.
BOUND = 1000

#: s = 1 - 2m for m = 1, ..., M.
M = 3

#: Bits for the functional-equation check. The rationals have at most 18
#: digits in range, and the balls at 256 bits have radius below 1e-73, so a
#: value wrong in its last digit is excluded by a wide margin.
CHECK_BITS = 256


def is_fundamental_discriminant(D):
    """D = 1 mod 4 squarefree, or D = 4m with m = 2, 3 mod 4 squarefree; not 1."""
    D = ZZ(D)
    if D == 0 or D == 1:
        return False
    if D % 4 == 1:
        return is_squarefree(D)
    if D % 4 == 0:
        m = D // 4
        return m % 4 in (2, 3) and is_squarefree(m)
    return False


def real_fundamental_discriminants(bound):
    return [ZZ(D) for D in range(2, bound + 1) if is_fundamental_discriminant(D)]


def bernoulli_polynomial_at(k, x):
    """B_k(x) = sum_j binom(k, j) B_j x^(k - j), with B_1 = -1/2, x rational."""
    x = QQ(x)
    return sum(binomial(k, j) * bernoulli(j) * x ** (k - j) for j in range(k + 1))


def generalized_bernoulli(k, D):
    """B_{k, chi_D} = D^(k-1) sum_{a=1}^{D} chi_D(a) B_k(a/D), chi_D = (D/.)."""
    D = ZZ(D)
    total = QQ(0)
    for a in range(1, D + 1):
        chi = kronecker_symbol(D, a)
        if chi:
            total += chi * bernoulli_polynomial_at(k, QQ(a) / QQ(D))
    return QQ(D) ** (k - 1) * total


def zeta_K(D, m):
    """zeta_K(1 - 2m) = (-B_{2m} / 2m) (-B_{2m, chi_D} / 2m)."""
    return bernoulli(2 * m) * generalized_bernoulli(2 * m, D) / QQ(4 * m * m)


def siegel(D):
    """zeta_K(-1) by Siegel's formula: no character, no Bernoulli number."""
    D = ZZ(D)
    total = ZZ(0)
    for b in range(-D, D + 1):
        if b * b < D and (b - D) % 2 == 0:
            total += sigma((D - b * b) // 4, 1)
    return QQ(total) / QQ(60)


def zeta_K_at_2m(D, m, bits):
    """zeta_K(2m) = zeta(2m) L(2m, chi_D) as a ball, L from Hurwitz zeta."""
    R = RealBallField(bits)
    D = ZZ(D)
    s = R(2 * m)
    L = R(0)
    for a in range(1, D):
        chi = kronecker_symbol(D, a)
        if chi:
            L += chi * s.zeta(R(QQ(a) / QQ(D)))
    return s.zeta() * L / R(D) ** (2 * m)


def functional_equation(value, D, m, bits):
    """zeta_K(2m) predicted from zeta_K(1 - 2m).

    Lambda(s) = D^(s/2) (pi^(-s/2) Gamma(s/2))^2 zeta_K(s) equals Lambda(1 - s),
    and Gamma(1/2 - m) = (-1)^m 2^(2m) m! sqrt(pi) / (2m)!.
    """
    R = RealBallField(bits)
    D = ZZ(D)
    factor = R.pi() ** (4 * m) * R(D).sqrt() / R(D) ** (2 * m)
    factor *= R(ZZ(2) ** (4 * m) * m * m) / R(factorial(2 * m) ** 2)
    return R(value) * factor


def checked(D, m, value):
    """The value, or a refusal naming both sides of the disagreement."""
    if m == 1:
        other = siegel(D)
        if other != value:
            raise ArithmeticError(
                'D = %s: the Bernoulli route gives %s and Siegel\'s formula %s; '
                'neither is right until the disagreement has a cause'
                % (D, value, other))
    got = zeta_K_at_2m(D, m, CHECK_BITS)
    want = functional_equation(value, D, m, CHECK_BITS)
    if not (got.is_finite() and want.is_finite()):
        raise ArithmeticError('D = %s, m = %s: a ball in the functional-equation '
                              'check is not finite, and would agree with anything'
                              % (D, m))
    if not got.overlaps(want):
        raise ArithmeticError(
            'D = %s, s = %s: zeta_K(%s) is %s from Hurwitz zeta and %s from the '
            'functional equation applied to %s; neither is right until the '
            'disagreement has a cause' % (D, 1 - 2 * m, 2 * m, got, want, value))
    return value


def field_name(D):
    d = D if D % 4 == 1 else D // 4
    return r'\mathbb{Q}(\sqrt{%d})' % d


class DedekindZetaNegativeOdd(numberdb.Generator):

    table = 'T130'
    parameters = ('D', 's')
    type = 'Q'
    rigour = 'exact'

    def enumerate(self, bound=BOUND, m_max=M):
        for D in real_fundamental_discriminants(bound):
            for m in range(1, m_max + 1):
                yield {'D': int(D), 's': int(1 - 2 * m)}

    def value(self, params, digits):
        D = ZZ(params['D'])
        s = ZZ(params['s'])
        if s >= 0 or s % 2 == 0:
            raise ValueError('s must be a negative odd integer, not %s' % s)
        m = (1 - s) // 2
        value = checked(D, m, zeta_K(D, m))
        return {'number': value, 'comment': '$%s$' % field_name(D)}


if __name__ == '__main__':
    generator = DedekindZetaNegativeOdd()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='zeta_K(s) at s = -1, -3, -5 for every real quadratic field '
                    'with D <= %d, from Bernoulli numbers in QQ, each checked '
                    'against Siegel\'s formula and the functional equation' % BOUND))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
