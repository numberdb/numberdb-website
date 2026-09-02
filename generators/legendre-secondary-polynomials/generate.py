"""Secondary polynomials of the Legendre polynomials -- numberdb.org/T133

    q_n(x) = int_{-1}^{1} (P_n(t) - P_n(x)) / (t - x) dt,        n >= 0,

with P_n the Legendre polynomial and the density 1 on [-1, 1]. A polynomial
of degree n - 1 with rational coefficients; q_0 = 0, q_1 = 2, q_2 = 3x,
q_3 = 5x^2 - 4/3. Listed for 0 <= n <= 50, the range of the table of P_n.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**Exact.** Every coefficient is a Sage rational. The polynomials come from
Bonnet's recurrence, (n + 1) q_{n+1} = (2n + 1) x q_n - n q_{n-1}, started at
q_0 = 0 and q_1 = 2 -- the recurrence of P_n itself with the other pair of
starting values -- and the one division is written between Sage rationals.
Nothing here can be a float: in `sage -python` a `/` between Python ints is
float division, exact to 2^53 and quietly wrong after it.

**Every entry is checked before it is returned**, against two computations
that share nothing with the recurrence: the definition, as the integral of
(P_n(t) - P_n(x))/(t - x) taken exactly from the moments int t^i dt =
(1 + (-1)^i)/(i + 1); and DLMF 14.7.3, q_n = 2 sum_{k=1}^{n} P_{k-1} P_{n-k} / k,
the polynomial part of the Legendre function of the second kind. It must
also have degree n - 1, parity (-1)^(n-1), and q_n(1) = 2 H_n, twice the
harmonic number. A polynomial failing any of these is an error, not a table.

**The convention that had to be chosen.** Wikipedia defines the secondary
polynomials for "a density" and fixes none. This table takes rho = 1 on
[-1, 1], the inner product the table of Legendre polynomials states; the
probability density 1/2 would halve every entry. It is the choice under
which q_n(x_k)/P_n'(x_k) at the roots x_k of P_n is the Gauss-Legendre
weight w_k, and under which q_n = 2 W_{n-1} with the W_{n-1} of DLMF 14.7.

Outside the generator, when this was written, the same polynomials were
compared with a plain-Python computation in fractions sharing no code, with
arb's Legendre function of the second kind at rational points, with every
node and weight of the Gauss-Legendre table for n <= 30, and with the Pade
property of W_{n-1}/P_n for artanh, with the controls that must fail failing.

Answers numberdb-data#93, for the Legendre sequence.
"""

import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ

#: How far the table runs: the range of the table of Legendre polynomials.
#: Measured: q_50 is 1365 characters written out and the block is about
#: 30 KB, against a soft limit of 320 KB; q_60 would be 2018 characters,
#: past where an entry is something a person reads.
UP_TO = 50

R = PolynomialRing(QQ, 'x')
x = R.gen()


def legendre(N):
    """P_0, ..., P_N exactly in Q[x], by Bonnet's recurrence."""
    P = [R(1), x]
    for n in range(1, N):
        P.append(R(((2 * n + 1) * x * P[n] - n * P[n - 1]) * (QQ(1) / QQ(n + 1))))
    return P


def secondary(N):
    """q_0, ..., q_N by the same recurrence from q_0 = 0, q_1 = 2."""
    q = [R(0), R(2)]
    for n in range(1, N):
        q.append(R(((2 * n + 1) * x * q[n] - n * q[n - 1]) * (QQ(1) / QQ(n + 1))))
    return q


def _moment(i):
    """int_{-1}^{1} t^i dt, exactly."""
    return QQ(2) / QQ(i + 1) if i % 2 == 0 else QQ(0)


def from_definition(p):
    """int (p(t) - p(x))/(t - x) dt from the moments: shares nothing with the recurrence.

    (t^j - x^j)/(t - x) = sum_{i<j} t^i x^{j-1-i}, so each monomial c_j x^j of
    p contributes c_j sum_{i<j} m_i x^{j-1-i}, with m_i the i-th moment.
    """
    q = R(0)
    for j, c in enumerate(p.list()):
        if c == 0:
            continue
        for i in range(0, j, 2):
            q += c * _moment(i) * x ** (j - 1 - i)
    return q


def from_dlmf(P, n):
    """2 W_{n-1} with W_{n-1} = sum_{k=1}^{n} P_{k-1} P_{n-k} / k (DLMF 14.7.3)."""
    w = R(0)
    for k in range(1, n + 1):
        w += P[k - 1] * P[n - k] * (QQ(1) / QQ(k))
    return 2 * w


_P = legendre(UP_TO + 1)
_Q = secondary(UP_TO + 1)
_H = [QQ(0)]
for _n in range(1, UP_TO + 2):
    _H.append(_H[-1] + QQ(1) / QQ(_n))


def checked(n):
    """q_n, after the three constructions and the shape have agreed."""
    n = int(n)
    if n < 0:
        raise ValueError('n must be nonnegative, not %s' % n)
    while n >= len(_Q):
        _P.extend(legendre(len(_P) + 10)[len(_P):])
        _Q.extend(secondary(len(_Q) + 10)[len(_Q):])
        _H.append(_H[-1] + QQ(1) / QQ(len(_H)))
    q = _Q[n]
    if q != from_definition(_P[n]):
        raise ArithmeticError('n=%d: the recurrence and the definition disagree' % n)
    if q != from_dlmf(_P, n):
        raise ArithmeticError('n=%d: the recurrence and DLMF 14.7.3 disagree' % n)
    if n == 0:
        if q != 0:
            raise ArithmeticError('q_0 is not 0')
        return q
    if q.degree() != n - 1:
        raise ArithmeticError('n=%d: degree %d, not %d' % (n, q.degree(), n - 1))
    if q(-x) != (-1) ** (n - 1) * q:
        raise ArithmeticError('n=%d: q_n does not have the parity of n - 1' % n)
    if q(QQ(1)) != 2 * _H[n]:
        raise ArithmeticError('n=%d: q_n(1) is not 2 H_n' % n)
    if q.leading_coefficient() != ZZ(2 * n).binomial(n) / ZZ(2) ** (n - 1):
        raise ArithmeticError('n=%d: leading coefficient is not binomial(2n, n)/2^(n-1)' % n)
    return q


#: The entries a reader could meet elsewhere, and where.
ANNOTATED = {
    0: {'comment': r'$q_0=0$: $P_0$ is constant, so the integrand vanishes. '
                   r'The value identifies nothing.',
        'equals': 'HREF{Zero}'},
    1: {'comment': r'$q_1=\int_{-1}^{1}dt=2$, the length of the interval; '
                   r'with the probability density $\frac12$ it would be $1$.',
        'equals': 'HREF{Integers#2}'},
    2: {'comment': r'$q_2=3x$ is also the Gegenbauer polynomial $C_1^{(3/2)}$; '
                   r'on its own it identifies nothing.',
        'equals': 'HREF{Gegenbauer_polynomials#3/2,1}'},
}


class LegendreSecondary(numberdb.Generator):

    table = 'T133'
    parameters = ('n',)
    type = 'Q[]'
    rigour = 'exact'

    def enumerate(self, up_to=UP_TO):
        for n in range(up_to + 1):
            yield {'n': str(n)}

    def value(self, params, digits):
        n = int(params['n'])
        entry = {'number': checked(n)}
        entry.update(ANNOTATED.get(n, {}))
        return entry


if __name__ == '__main__':
    generator = LegendreSecondary()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='secondary polynomials of the Legendre polynomials for n <= %d, '
                    'from Bonnet\'s recurrence at q_0 = 0, q_1 = 2, each checked against '
                    'the defining integral and against DLMF 14.7.3 before being sent' % UP_TO))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
