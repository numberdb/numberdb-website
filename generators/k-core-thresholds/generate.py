"""k-core thresholds of the Erdős–Rényi random graph -- numberdb.org/T156

For k >= 3, the k-core threshold c_k is the average degree at which the
random graph G(n, p = c/n) acquires a k-core, a nonempty subgraph of minimum
degree at least k: with probability tending to 1, the k-core is empty for
c < c_k and has order n for c > c_k (Pittel, Spencer and Wormald, 1996), and

    c_k = min over lambda > 0 of  lambda / P(Poisson(lambda) >= k - 1).

The table holds c_k for 3 <= k <= 12, one parameter `k`, at 100 digits in
ball arithmetic.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**How the minimum is enclosed.** Write T(x) = P(Poisson(x) >= k-1) and
f(x) = x / T(x). Then f'(x) = g(x) / T(x)^2 with

    g(x) = T(x) - x T'(x) = T(x) - e^(-x) x^(k-1) / (k-2)!,

and g(0) = 0, g(x) -> 1 as x -> infinity, and g'(x) = -x T''(x) =
e^(-x) x^(k-2) (x - (k-2)) / (k-2)!, so g decreases on (0, k-2) and increases
on (k-2, infinity): it has exactly one positive zero x_k, which lies beyond
k-2, is negative before it and positive after it. Hence f decreases on
(0, x_k] and increases on [x_k, infinity), and c_k = f(x_k) is the unique
minimum. That is the whole proof; the computation only has to enclose x_k.
It does so by bisection on the sign of g between k-2 and 4k+10, checked in
balls at every step, down to a bracket of half-width 10^-(digits+6), and
then confirms the sign change of g across the ends of the bracket. The
value f(X) on that bracket X, evaluated in ball arithmetic, encloses f(x_k).
The Poisson tail is the finite sum 1 - e^(-x) sum_{j<k-1} x^j/j!, which
needs nothing beyond exp and rational arithmetic.

**What was checked outside this file** before any entry was sent: every
value against mpmath at 120 digits, where the tail is the regularised
incomplete gamma function gamma(k-1, x)/Gamma(k-1) and the minimiser the
root of the derivative found by the secant method, a route that shares
nothing with the finite sum here; c_3 = 3.35 and the size 0.27 n of the
newborn 3-core against the abstract of Pittel, Spencer and Wormald; the
minimiser against x_k > k-2 for every k; and the growth of c_k against
k + sqrt(k ln k), which the table follows with a difference that stays
below one multiple of ln k.
"""

import sys

import numberdb.sage as numberdb
from numberdb._write import to_text
from sage.rings.integer_ring import ZZ
from sage.rings.real_arb import RealBallField
from sage.rings.real_mpfr import RealField

#: Bits of working precision beyond what the written digits need. Measured at
#: 100 digits: every ball has radius about 6e-106, and the widest relative
#: to its value is c_3, at 1.8e-106; the guard is more than the run needs
#: and costs nothing here.
WORKING_GUARD = 64

#: Decimal places of the bracket around the minimiser beyond the digits
#: written: the radius of f(X) is about (1/T + x T'/T^2) times the bracket's
#: half-width, a factor below 10 for every k here.
BRACKET_GUARD = 6

#: The rows: the table holds every k with 3 <= k <= K_MAX.
K_MAX = 12

#: Digits of the minimiser and the newborn core's size quoted in the entry
#: comments.
COMMENT_DIGITS = 12

PSW = 'PSW'


def poisson_tail(x, m):
    """P(Poisson(x) >= m) = 1 - e^(-x) sum_{j<m} x^j / j!, for a ball x."""
    total = x.parent()(0)
    term = x.parent()(1)
    for j in range(m):
        if j:
            term = term * x / j
        total += term
    return 1 - (-x).exp() * total


def g(x, k):
    """T(x) - x T'(x), the numerator of f'(x); its zero is the minimiser."""
    return poisson_tail(x, k - 1) - (-x).exp() * x ** (k - 1) / ZZ(k - 2).factorial()


def f(x, k):
    """x / P(Poisson(x) >= k-1), whose minimum over x > 0 is c_k."""
    return x / poisson_tail(x, k - 1)


def minimiser(k, digits):
    """A ball enclosing x_k, the unique positive zero of g, of radius
    10^-(digits + BRACKET_GUARD): bisection on the sign of g, each sign
    decided in ball arithmetic, then a sign change across the ends."""
    if k < 3:
        raise ValueError('the minimiser exists for k >= 3, not k = %s' % k)
    bits = numberdb.bits(digits, losing=WORKING_GUARD)
    RBF, RR = RealBallField(bits), RealField(bits)
    delta = RR(10) ** (-(digits + BRACKET_GUARD))
    lo, hi = RR(k - 2), RR(4 * k + 10)
    if not (g(RBF(lo), k) < 0 and g(RBF(hi), k) > 0):
        raise ArithmeticError('g does not change sign on [%s, %s] for k = %s' % (lo, hi, k))
    while hi - lo > delta / 4:
        mid = (lo + hi) / 2
        v = g(RBF(mid), k)
        if v.contains_zero():
            raise ArithmeticError('the sign of g could not be decided at x = %s for k = %s' % (mid, k))
        if v < 0:
            lo = mid
        else:
            hi = mid
    x0 = (lo + hi) / 2
    left, right = g(RBF(x0 - delta), k), g(RBF(x0 + delta), k)
    if not (left < 0 and right > 0):
        raise ArithmeticError('no sign change of g across x0 +/- delta for k = %s' % k)
    return RBF(x0).add_error(delta)


def threshold(k, digits):
    """(c_k, x_k, P(Poisson(x_k) >= k)) as balls."""
    x = minimiser(k, digits)
    c = f(x, k)
    if not (k - 2 < x and k < c < 4 * k + 10):
        raise ArithmeticError('the threshold came out as %s at x = %s for k = %s' % (c, x, k))
    return c, x, poisson_tail(x, k)


class KCoreThresholds(numberdb.Generator):

    table = 'T156'
    parameters = ('k',)
    type = 'R'
    digits = 100
    rigour = 'proven'

    def enumerate(self):
        for k in range(3, K_MAX + 1):
            yield {'k': str(k)}

    def value(self, params, digits):
        k = int(params['k'])
        c, x, size = threshold(k, digits)
        comment = (r'The minimum is attained at $\lambda_{%d}=%s$, and the $%d$-core, when it first '
                   r'appears, has about $%s\,n$ vertices, the fraction being '
                   r'$\mathbb{P}(\mathrm{Po}(\lambda_{%d})\geq %d)$ CITE{%s}.'
                   % (k, to_text(x, COMMENT_DIGITS), k, to_text(size, COMMENT_DIGITS), k, k, PSW))
        return {'number': c, 'comment': comment}


if __name__ == '__main__':
    generator = KCoreThresholds()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='k-core thresholds c_k of the random graph G(n, c/n) for 3 <= k <= 12, the '
                    'minimum of x / P(Poisson(x) >= k-1) enclosed in ball arithmetic at 100 '
                    'digits from a bisection bracket around its unique minimiser'))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
