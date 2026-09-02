"""Nodes and weights of Gauss-Legendre quadrature -- numberdb.org/T132

    int_{-1}^{1} f(x) dx  ~  sum_{k=1}^{n} w_k f(x_k),

exact for every polynomial f of degree at most 2n - 1. The nodes
x_1 < ... < x_n are the roots of the Legendre polynomial P_n, and for every
n from 1 to 30 both the nodes and the weights are listed, in the order of
the nodes, under the symbolic parameter `expression` (x or w).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**These digits are proven.** P_n is built exactly in Q[x] by Bonnet's
recurrence; its roots are isolated by Sage's real root isolation over the
interval field (MPFI), so each node arrives as an interval that provably
contains exactly one root, and is carried from there as an arb ball. The
weight is w_k = 2 / ((1 - x_k^2) P_n'(x_k)^2) in ball arithmetic. The digits
written are the ones the ball supports.

**What is exact is written exactly.** The node x = 0 of every odd rule is
taken off P_n before isolating (the isolator would return a ball of radius
1e-120 around it), and its weight 2 / P_n'(0)^2 is a rational, returned as
one. The weights of the rules with n <= 3 -- 2; 1, 1; 5/9, 8/9, 5/9 -- are
rational too and are returned exactly, after the ball formula has been seen
to agree.

**Every rule is checked before any of it is returned**, against computations
sharing no code with the weight formula: the weights must also equal
2 (1 - x_k^2) / (n^2 P_{n-1}(x_k)^2), the rule must integrate x^m to
(1 + (-1)^m)/(m + 1) for every m <= 2n - 1 and must *fail* to do so at
m = 2n, the weights must sum to 2 and be positive, and the nodes must be
symmetric and strictly increasing. A rule failing any of these is an error
rather than a table.

Outside the generator, when this was written, the same values were compared
with the closed forms for n <= 5, with twenty OEIS decimal expansions
(A372267-A372276, A382103-A382107, A382686-A382690) to 100 digits, with the
polynomials of OEIS A112734 whose roots are the weights (n <= 8), and with
the seven-point row on Wikipedia's Gauss-Kronrod page, with the controls that
must fail failing.

**Conventions.** The interval is [-1, 1]; nodes are in increasing order and
both signs are stored, because search by number keeps the sign; n = 1 is the
midpoint rule x = 0, w = 2.
"""

import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField
from sage.rings.real_mpfi import RealIntervalField

#: Bits of working precision beyond what the written digits need. Measured
#: over the whole table at 100 digits: the widest ball (a weight at n = 30)
#: has radius 1.7e-110 with this guard, so it supports 110 digits; the nodes
#: are far better (radius 4.6e-120).
WORKING_GUARD = 64

#: Every rule up to here: 465 nodes and 465 weights. Entry length does not
#: grow with n, so the bound is a choice about what somebody looks up, and it
#: covers every order printed in Abramowitz-Stegun Table 25.4 below 32 and
#: every embedded Gauss rule of QUADPACK (7, 10, 15, 20, 25, 30).
ORDERS = 30

R = PolynomialRing(QQ, 'x')
x = R.gen()


def legendre(N):
    """P_0, ..., P_N exactly in Q[x], by Bonnet's recurrence.

    (n + 1) P_{n+1} = (2n + 1) x P_n - n P_{n-1}: multiplications and one
    division written between Sage rationals, so nothing here is a float.
    """
    P = [R(1), x]
    for n in range(1, N):
        P.append(R(((2 * n + 1) * x * P[n] - n * P[n - 1]) * (QQ(1) / QQ(n + 1))))
    return P


_P = legendre(ORDERS + 1)


def _legendre(n):
    if n >= len(_P):
        _P.extend(legendre(n)[len(_P):])
    return _P[n]


def _moment(m):
    """int_{-1}^1 x^m dx, exactly."""
    return QQ(2) / QQ(m + 1) if m % 2 == 0 else QQ(0)


#: The rules whose weights are all rational, given exactly. Verified against
#: the ball formula every time they are used.
RATIONAL_WEIGHTS = {
    1: [QQ(2)],
    2: [QQ(1), QQ(1)],
    3: [QQ(5) / 9, QQ(8) / 9, QQ(5) / 9],
}


def rule(n, bits):
    """(nodes, weights) of the n-point rule; nodes as balls, exact where exact.

    Balls for the nodes, a rational for x = 0 and its weight, and rationals
    for the weights of n <= 3. Everything else is a ball.
    """
    n = int(n)
    if n < 1:
        raise ValueError('n must be at least 1, not %s' % n)
    RIF = RealIntervalField(bits)
    RBF = RealBallField(bits)
    P = _legendre(n)
    dP = P.derivative()
    p = P
    if n % 2 == 1:
        p = R(P // x)                                 # exact: P_n(0) = 0
        if p * x != P:
            raise ArithmeticError('P_%d is not divisible by x' % n)
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
    if not (bool(nodes[0] > -1) and bool(nodes[-1] < 1)):
        raise ArithmeticError('n=%d: a node lies outside (-1, 1)' % n)

    weights = []
    for k, xb in enumerate(nodes, 1):
        if k == centre:
            d0 = dP(QQ(0))
            w = QQ(2) / (d0 * d0)                     # exact
            wb = RBF(w)
        else:
            w = 2 / ((1 - xb ** 2) * RBF(dP(xb)) ** 2)
            wb = w
        other = 2 * (1 - xb ** 2) / (RBF(n) ** 2 * RBF(_legendre(n - 1)(xb)) ** 2)
        if not (wb.is_finite() and other.is_finite() and wb.overlaps(other)):
            raise ArithmeticError(
                'n=%d k=%d: 2/((1-x^2) P_n\'(x)^2) and 2(1-x^2)/(n^2 P_{n-1}(x)^2) '
                'disagree; neither is right until the disagreement has a cause' % (n, k))
        if not bool(wb > 0):
            raise ArithmeticError('n=%d k=%d: weight is not positive' % (n, k))
        weights.append(w)

    if n in RATIONAL_WEIGHTS:
        for k, (w, exact) in enumerate(zip(weights, RATIONAL_WEIGHTS[n]), 1):
            if not RBF(w).overlaps(RBF(exact)):
                raise ArithmeticError('n=%d k=%d: the ball weight does not contain %s'
                                      % (n, k, exact))
        weights = list(RATIONAL_WEIGHTS[n])

    # symmetry, sum, and the degree of exactness with its control
    for k in range(n):
        if not (nodes[k] + nodes[n - 1 - k]).contains_zero():
            raise ArithmeticError('n=%d: nodes are not symmetric at k=%d' % (n, k + 1))
        if not RBF(weights[k]).overlaps(RBF(weights[n - 1 - k])):
            raise ArithmeticError('n=%d: weights are not symmetric at k=%d' % (n, k + 1))
    if not sum(RBF(w) for w in weights).overlaps(RBF(2)):
        raise ArithmeticError('n=%d: the weights do not sum to 2' % n)
    for m in range(0, 2 * n):
        s = sum(RBF(w) * xb ** m for w, xb in zip(weights, nodes))
        if not s.overlaps(RBF(_moment(m))):
            raise ArithmeticError('n=%d: the rule is not exact on x^%d' % (n, m))
    s = sum(RBF(w) * xb ** (2 * n) for w, xb in zip(weights, nodes))
    if s.overlaps(RBF(_moment(2 * n))):
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
    (1, 1, 'x'): r'the midpoint rule',
    (1, 1, 'w'): r'$w_1=2$, the length of the interval',
    (2, 1, 'x'): r'$x_1=-1/\sqrt{3}$',
    (2, 2, 'x'): r'$x_2=1/\sqrt{3}$',
    (2, 1, 'w'): r'$w_1=1$',
    (2, 2, 'w'): r'$w_2=1$',
    (3, 1, 'x'): r'$x_1=-\sqrt{3/5}$',
    (3, 3, 'x'): r'$x_3=\sqrt{3/5}$',
    (3, 1, 'w'): r'$w_1=5/9$',
    (3, 2, 'w'): r'$w_2=8/9$',
    (3, 3, 'w'): r'$w_3=5/9$',
    (4, 1, 'x'): r'$x_1=-\sqrt{\bigl(3+2\sqrt{6/5}\bigr)/7}$',
    (4, 2, 'x'): r'$x_2=-\sqrt{\bigl(3-2\sqrt{6/5}\bigr)/7}$',
    (4, 3, 'x'): r'$x_3=\sqrt{\bigl(3-2\sqrt{6/5}\bigr)/7}$',
    (4, 4, 'x'): r'$x_4=\sqrt{\bigl(3+2\sqrt{6/5}\bigr)/7}$',
    (4, 1, 'w'): r'$w_1=(18-\sqrt{30})/36$',
    (4, 2, 'w'): r'$w_2=(18+\sqrt{30})/36$',
    (4, 3, 'w'): r'$w_3=(18+\sqrt{30})/36$',
    (4, 4, 'w'): r'$w_4=(18-\sqrt{30})/36$',
    (5, 1, 'x'): r'$x_1=-\tfrac13\sqrt{5+2\sqrt{10/7}}$',
    (5, 2, 'x'): r'$x_2=-\tfrac13\sqrt{5-2\sqrt{10/7}}$',
    (5, 4, 'x'): r'$x_4=\tfrac13\sqrt{5-2\sqrt{10/7}}$',
    (5, 5, 'x'): r'$x_5=\tfrac13\sqrt{5+2\sqrt{10/7}}$',
    (5, 1, 'w'): r'$w_1=(322-13\sqrt{70})/900$',
    (5, 2, 'w'): r'$w_2=(322+13\sqrt{70})/900$',
    (5, 3, 'w'): r'$w_3=128/225$',
    (5, 4, 'w'): r'$w_4=(322+13\sqrt{70})/900$',
    (5, 5, 'w'): r'$w_5=(322-13\sqrt{70})/900$',
}

#: Where the corpus already holds an entry: the exact zero, the integer
#: weights, and the nodes of degree 2 in the table of quadratic algebraic
#: numbers (addresses read off that table, not derived).
EQUALS = {
    (1, 1, 'w'): 'HREF{Integers#2}',
    (2, 1, 'w'): 'HREF{One}',
    (2, 2, 'w'): 'HREF{One}',
    (2, 1, 'x'): 'HREF{Algebraic_numbers_of_degree_2#3,0,-1,1}',
    (2, 2, 'x'): 'HREF{Algebraic_numbers_of_degree_2#3,0,-1,2}',
    (3, 1, 'x'): 'HREF{Algebraic_numbers_of_degree_2#5,0,-3,1}',
    (3, 3, 'x'): 'HREF{Algebraic_numbers_of_degree_2#5,0,-3,2}',
}

CENTRAL_NODE = (r'$x_{%d}=0$, the central node of every rule of odd order; '
                r'it identifies nothing, the weight is what belongs to $n$')


def annotate(n, k, expression, value):
    entry = {'number': value}
    comment = NAMED.get((n, k, expression))
    if expression == 'x' and n % 2 == 1 and k == (n + 1) // 2:
        comment = CENTRAL_NODE % k if n > 1 else (
            r'$x_1=0$, the midpoint rule; $0$ is a node of every rule of odd order '
            r'and identifies nothing')
        entry['equals'] = 'HREF{Zero}'
    if comment:
        entry['comment'] = comment
    if (n, k, expression) in EQUALS:
        entry['equals'] = EQUALS[(n, k, expression)]
    return entry


class GaussLegendre(numberdb.Generator):

    table = 'T132'
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
    generator = GaussLegendre()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='Gauss-Legendre nodes and weights for n <= %d: roots of P_n '
                    'isolated over Q[x], weights in ball arithmetic, every rule '
                    'checked for its degree of exactness with a control before '
                    'being sent' % ORDERS))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
