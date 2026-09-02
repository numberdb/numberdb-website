"""Nodes and weights of Gauss-Hermite quadrature -- numberdb.org/T134

    int_{-inf}^{inf} f(x) e^{-x^2} dx  ~  sum_{k=1}^{n} w_k f(x_k),

exact for every polynomial f of degree at most 2n - 1. The nodes
x_1 < ... < x_n are the roots of the physicists' Hermite polynomial H_n, and
for every n from 1 to 30 both the nodes and the weights are listed, in the
order of the nodes, under the symbolic parameter `expression` (x or w).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**These digits are proven.** H_n is built exactly in Z[x] by the recurrence
H_{n+1} = 2x H_n - 2n H_{n-1}; its roots are isolated by Sage's real root
isolation over the interval field (MPFI), so each node arrives as an interval
that provably contains exactly one root, and is carried from there as an arb
ball. The weight is w_k = 2^{n-1} n! sqrt(pi) / (n^2 H_{n-1}(x_k)^2)
(Abramowitz-Stegun 25.4.46) in ball arithmetic, sqrt(pi) included. The
digits written are the ones the ball supports.

**What is exact is written exactly.** The node x = 0 of every odd rule is
taken off H_n before isolating (the isolator would return a ball of radius
1e-120 around it) and is returned as the integer 0. No weight is rational:
every one is sqrt(pi) times an algebraic number, so every weight is a ball.

**Every rule is checked before any of it is returned**, against computations
sharing no code with the weight formula: the weights must also equal the
Christoffel function 1 / sum_{j<n} H_j(x_k)^2 / (2^j j! sqrt(pi)), the rule
must integrate x^m to Gamma((m+1)/2) = sqrt(pi) (m-1)!! / 2^(m/2) for every
even m <= 2n - 1 and to 0 for odd m, and must *fail* to do so at m = 2n; the
weights must sum to sqrt(pi) and be positive; the nodes must be symmetric and
strictly increasing; and for odd n the central weight must be
2^{n+1} n! sqrt(pi) / H_n'(0)^2. A rule failing any of these is an error
rather than a table.

Outside the generator, when this was written, the same values were compared
with the closed forms for n <= 5, with the polynomials H_n and He_n stored
in tables T103 and T104 (sqrt(2) x_k is a root of He_n), with twenty-five
OEIS decimal expansions (A393353-A393374 and A010503, A019704, A115754,
A019708) to 100 digits, with the minimal polynomials of w_k / sqrt(pi) in
OEIS A393904 for n <= 7, and with DLMF Tables 3.5.10-3.5.13 (n = 5, 10, 15,
20), with the controls that must fail failing.

**Conventions.** The weight function is e^{-x^2} and H_n is the physicists'
polynomial, as in Abramowitz-Stegun 25.4.46, DLMF 3.5.28, numpy's `hermgauss`
and the OEIS entries; the probabilists' rule for e^{-x^2/2} has nodes
sqrt(2) x_k and weights sqrt(2) w_k, and is not a second table. Nodes are in
increasing order and both signs are stored, because search by number keeps
the sign; n = 1 is the one-point rule x = 0, w = sqrt(pi).
"""

import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField
from sage.rings.real_mpfi import RealIntervalField

#: Bits of working precision beyond what the written digits need. Measured
#: over the whole table at 100 digits: the widest ball, relative to its
#: value, is a weight at n = 30 with relative radius 3e-113, so 100 digits
#: are supported with room; the nodes are better (1e-118).
WORKING_GUARD = 64

#: Every rule up to here: 465 nodes and 465 weights. Entry length does not
#: grow with n; the bound matches the Gauss-Legendre table T132 and covers
#: every order of Abramowitz-Stegun Table 25.10 below 32.
ORDERS = 30

R = PolynomialRing(ZZ, 'x')
x = R.gen()


def hermite(N):
    """H_0, ..., H_N exactly in Z[x], by H_{n+1} = 2x H_n - 2n H_{n-1}.

    Multiplications and subtractions of integer polynomials only; nothing
    here can be a float.
    """
    H = [R(1), 2 * x]
    for n in range(1, N):
        H.append(2 * x * H[n] - 2 * n * H[n - 1])
    return H


_H = hermite(ORDERS + 1)


def _hermite(n):
    if n >= len(_H):
        _H.extend(hermite(n)[len(_H):])
    return _H[n]


def _factorial(n):
    f = ZZ(1)
    for i in range(2, n + 1):
        f *= i
    return f


def _double_factorial(m):
    """m!! as a Sage integer, with (-1)!! = 1."""
    f = ZZ(1)
    while m > 1:
        f *= m
        m -= 2
    return f


def _moment_over_sqrtpi(m):
    """int x^m e^{-x^2} dx divided by sqrt(pi), exactly: (m-1)!! / 2^{m/2}."""
    if m % 2 == 1:
        return QQ(0)
    return QQ(_double_factorial(m - 1)) / QQ(2) ** (m // 2)


def rule(n, bits):
    """(nodes, weights) of the n-point rule; nodes as balls, the zero exact.

    Balls for the nodes and the weights, the integer 0 for the central node
    of an odd rule.
    """
    n = int(n)
    if n < 1:
        raise ValueError('n must be at least 1, not %s' % n)
    RIF = RealIntervalField(bits)
    RBF = RealBallField(bits)
    sqrtpi = RBF.pi().sqrt()
    H = _hermite(n)
    p = H
    if n % 2 == 1:
        p = R(H // x)                                 # exact: H_n(0) = 0
        if p * x != H:
            raise ArithmeticError('H_%d is not divisible by x' % n)
    roots = p.roots(ring=RIF, multiplicities=False)
    if len(roots) != p.degree():
        raise ArithmeticError('isolated %d roots of a polynomial of degree %d'
                              % (len(roots), p.degree()))
    nodes = [RBF(r) for r in roots]
    centre = None
    if n % 2 == 1:
        centre = (n + 1) // 2
        nodes.append(RBF(0))
    nodes.sort(key=lambda b: b.mid())
    for a, b in zip(nodes, nodes[1:]):
        if not bool(a < b):
            raise ArithmeticError('n=%d: two node enclosures are not separated' % n)

    Hm1 = _hermite(n - 1)
    lead = RBF(2) ** (n - 1) * RBF(_factorial(n)) * sqrtpi / RBF(n) ** 2
    weights = []
    for k, xb in enumerate(nodes, 1):
        w = lead / RBF(Hm1(xb)) ** 2
        # the Christoffel function, sharing nothing with the formula above
        other = RBF(0)
        for j in range(n):
            other += RBF(_hermite(j)(xb)) ** 2 / (RBF(2) ** j * RBF(_factorial(j)) * sqrtpi)
        other = 1 / other
        if not (w.is_finite() and other.is_finite() and w.overlaps(other)):
            raise ArithmeticError(
                'n=%d k=%d: 2^(n-1) n! sqrt(pi)/(n^2 H_{n-1}(x)^2) and the Christoffel '
                'function disagree; neither is right until the disagreement has a cause' % (n, k))
        if not bool(w > 0):
            raise ArithmeticError('n=%d k=%d: weight is not positive' % (n, k))
        weights.append(w)

    if centre is not None:
        d0 = ZZ(H.derivative()(0))
        exact = QQ(2) ** (n + 1) * QQ(_factorial(n)) / QQ(d0 * d0)
        if not weights[centre - 1].overlaps(sqrtpi * RBF(exact)):
            raise ArithmeticError('n=%d: the central weight is not %s sqrt(pi)' % (n, exact))

    # symmetry, sum, and the degree of exactness with its control
    for k in range(n):
        if not (nodes[k] + nodes[n - 1 - k]).contains_zero():
            raise ArithmeticError('n=%d: nodes are not symmetric at k=%d' % (n, k + 1))
        if not weights[k].overlaps(weights[n - 1 - k]):
            raise ArithmeticError('n=%d: weights are not symmetric at k=%d' % (n, k + 1))
    if not sum(weights).overlaps(sqrtpi):
        raise ArithmeticError('n=%d: the weights do not sum to sqrt(pi)' % n)
    for m in range(0, 2 * n):
        s = sum(w * xb ** m for w, xb in zip(weights, nodes))
        if not s.overlaps(sqrtpi * RBF(_moment_over_sqrtpi(m))):
            raise ArithmeticError('n=%d: the rule is not exact on x^%d' % (n, m))
    s = sum(w * xb ** (2 * n) for w, xb in zip(weights, nodes))
    if s.overlaps(sqrtpi * RBF(_moment_over_sqrtpi(2 * n))):
        raise ArithmeticError('n=%d: control failed, the rule appears exact on x^%d' % (n, 2 * n))
    return nodes, weights


_cache = {}


def cached_rule(n, bits):
    key = (int(n), int(bits))
    if key not in _cache:
        _cache[key] = rule(n, bits)
    return _cache[key]


#: Closed forms a reader would recognise, for the entries that have one.
#: Keyed by (n, k, expression). Signs follow the increasing order of the nodes.
NAMED = {
    (1, 1, 'w'): r'$w_1=\sqrt{\pi}=\Gamma(1/2)$, the integral of $e^{-x^2}$',
    (2, 1, 'x'): r'$x_1=-1/\sqrt{2}$',
    (2, 2, 'x'): r'$x_2=1/\sqrt{2}$',
    (2, 1, 'w'): r'$w_1=\sqrt{\pi}/2=\Gamma(3/2)$',
    (2, 2, 'w'): r'$w_2=\sqrt{\pi}/2=\Gamma(3/2)$',
    (3, 1, 'x'): r'$x_1=-\sqrt{3/2}$',
    (3, 3, 'x'): r'$x_3=\sqrt{3/2}$',
    (3, 1, 'w'): r'$w_1=\sqrt{\pi}/6$',
    (3, 3, 'w'): r'$w_3=\sqrt{\pi}/6$',
    (4, 1, 'x'): r'$x_1=-\sqrt{\bigl(3+\sqrt{6}\bigr)/2}$',
    (4, 2, 'x'): r'$x_2=-\sqrt{\bigl(3-\sqrt{6}\bigr)/2}$',
    (4, 3, 'x'): r'$x_3=\sqrt{\bigl(3-\sqrt{6}\bigr)/2}$',
    (4, 4, 'x'): r'$x_4=\sqrt{\bigl(3+\sqrt{6}\bigr)/2}$',
    (4, 1, 'w'): r'$w_1=\sqrt{\pi}\,(3-\sqrt{6})/12$',
    (4, 2, 'w'): r'$w_2=\sqrt{\pi}\,(3+\sqrt{6})/12$',
    (4, 3, 'w'): r'$w_3=\sqrt{\pi}\,(3+\sqrt{6})/12$',
    (4, 4, 'w'): r'$w_4=\sqrt{\pi}\,(3-\sqrt{6})/12$',
    (5, 1, 'x'): r'$x_1=-\sqrt{\bigl(5+\sqrt{10}\bigr)/2}$',
    (5, 2, 'x'): r'$x_2=-\sqrt{\bigl(5-\sqrt{10}\bigr)/2}$',
    (5, 4, 'x'): r'$x_4=\sqrt{\bigl(5-\sqrt{10}\bigr)/2}$',
    (5, 5, 'x'): r'$x_5=\sqrt{\bigl(5+\sqrt{10}\bigr)/2}$',
    (5, 1, 'w'): r'$w_1=\sqrt{\pi}\,(7-2\sqrt{10})/60$',
    (5, 2, 'w'): r'$w_2=\sqrt{\pi}\,(7+2\sqrt{10})/60$',
    (5, 4, 'w'): r'$w_4=\sqrt{\pi}\,(7+2\sqrt{10})/60$',
    (5, 5, 'w'): r'$w_5=\sqrt{\pi}\,(7-2\sqrt{10})/60$',
}

#: Where the corpus already holds an entry: the exact zero, Gamma(1/2) and
#: Gamma(3/2) in the table of Gamma values, and the nodes of degree 2 in the
#: table of quadratic algebraic numbers (addresses read off search results,
#: not derived).
EQUALS = {
    (1, 1, 'w'): 'HREF{Values_of_the_Gamma_function_at_rational_numbers#1/2}',
    (2, 1, 'w'): 'HREF{Values_of_the_Gamma_function_at_rational_numbers#3/2}',
    (2, 2, 'w'): 'HREF{Values_of_the_Gamma_function_at_rational_numbers#3/2}',
    (2, 1, 'x'): 'HREF{Algebraic_numbers_of_degree_2#2,0,-1,1}',
    (2, 2, 'x'): 'HREF{Algebraic_numbers_of_degree_2#2,0,-1,2}',
    (3, 1, 'x'): 'HREF{Algebraic_numbers_of_degree_2#2,0,-3,1}',
    (3, 3, 'x'): 'HREF{Algebraic_numbers_of_degree_2#2,0,-3,2}',
}

#: The central weight of an odd rule is a rational times sqrt(pi); the
#: rational is short enough to print up to here.
CENTRAL_WEIGHT_NAMED_TO = 9


def central_factor(n):
    """The rational r with w_{(n+1)/2} = r sqrt(pi) for odd n."""
    d0 = ZZ(_hermite(n).derivative()(0))
    return QQ(2) ** (n + 1) * QQ(_factorial(n)) / QQ(d0 * d0)


def annotate(n, k, expression, value):
    entry = {'number': value}
    comment = NAMED.get((n, k, expression))
    if n % 2 == 1 and k == (n + 1) // 2:
        if expression == 'x':
            comment = (r'$x_1=0$, the one-point rule' if n == 1 else
                       r'$x_{%d}=0$, the central node of every rule of odd order' % k)
            entry['equals'] = 'HREF{Zero}'
        elif n <= CENTRAL_WEIGHT_NAMED_TO and n > 1:
            comment = r'$w_{%d}=%s\sqrt{\pi}$' % (k, _latex_rational(central_factor(n)))
    if comment:
        entry['comment'] = comment
    if (n, k, expression) in EQUALS:
        entry['equals'] = EQUALS[(n, k, expression)]
    return entry


def _latex_rational(r):
    r = QQ(r)
    if r.denominator() == 1:
        return str(r.numerator())
    return r'\tfrac{%d}{%d}' % (r.numerator(), r.denominator())


class GaussHermite(numberdb.Generator):

    table = 'T134'
    parameters = ('n', 'k', 'expression')
    type = 'R'
    digits = 100
    rigour = 'proven'

    def enumerate(self, orders=ORDERS):
        for n in range(1, orders + 1):
            for k in range(1, n + 1):
                for expression in ('x', 'w'):
                    yield {'n': n, 'k': k, 'expression': expression}

    def value(self, params, digits):
        n, k = int(params['n']), int(params['k'])
        expression = params['expression']
        if not 1 <= k <= n:
            raise ValueError('k must satisfy 1 <= k <= n, not %s' % k)
        if expression not in ('x', 'w'):
            raise ValueError("expression is 'x' or 'w', not %r" % expression)
        bits = numberdb.bits(digits, losing=WORKING_GUARD)
        nodes, weights = cached_rule(n, bits)
        value = nodes[k - 1] if expression == 'x' else weights[k - 1]
        if expression == 'x' and value.is_zero():
            value = ZZ(0)
        return annotate(n, k, expression, value)


if __name__ == '__main__':
    generator = GaussHermite()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='Gauss-Hermite nodes and weights for n <= %d: roots of H_n '
                    'isolated over Z[x], weights in ball arithmetic with sqrt(pi), '
                    'every rule checked for its degree of exactness with a control '
                    'before being sent' % ORDERS))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
