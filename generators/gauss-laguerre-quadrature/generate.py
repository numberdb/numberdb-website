"""Nodes and weights of Gauss-Laguerre quadrature -- numberdb.org/T135

    int_0^inf f(x) e^{-x} dx  ~  sum_{k=1}^{n} w_k f(x_k),

exact for every polynomial f of degree at most 2n - 1. The nodes
x_1 < ... < x_n are the roots of the Laguerre polynomial L_n, and for every
n from 1 to 30 both the nodes and the weights are listed, in the order of
the nodes, under the symbolic parameter `expression` (x or w).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**These digits are proven.** L_n is built exactly in Q[x] by the recurrence
(n + 1) L_{n+1} = (2n + 1 - x) L_n - n L_{n-1}, the division written between
Sage rationals; its roots are isolated by Sage's real root isolation over the
interval field (MPFI), so each node arrives as an interval that provably
contains exactly one root, and is carried from there as an arb ball. The
weight is w_k = x_k / ((n+1)^2 L_{n+1}(x_k)^2) (Abramowitz-Stegun 25.4.45) in
ball arithmetic. The digits written are the ones the ball supports.

**What is exact is written exactly.** The one-point rule is x = 1, w = 1,
returned as integers after the ball formulas have been seen to agree. For
n >= 2 the generator asks Sage for the rational roots of L_n and refuses to
go on if there are any (there are none: n! L_n has integer coefficients,
constant term n! and leading coefficient +-1, and no integer is a root), so
every other entry is an algebraic number of degree at least 2 and is a ball.

**Every rule is checked before any of it is returned**, against computations
sharing no code with the weight formula: the weights must also equal the
Christoffel function 1 / sum_{j<n} L_j(x_k)^2, the rule must integrate x^m to
m! for every m <= 2n - 1 and must *fail* to do so at m = 2n, the weights must
sum to 1 and be positive, and the nodes must be strictly increasing and lie
in (0, 4n + 2). The polynomials named in the entry comments for n <= 4 are
checked exactly against L_n, each stated weight polynomial must vanish at the
weight, and the weights of those rules must decrease with k, which is what
the words "largest root", "second largest" in the comments assert (from
n = 7 on they do not: w_2 > w_1). A rule failing any of these is an error
rather than a table.

Outside the generator, when this was written, the same values were compared
with the closed forms for n <= 2, with the Laguerre polynomials stored in
table T102, with fourteen OEIS decimal expansions (A384277-A384281,
A384586-A384589, A384463-A384467) to 100 digits, with the weight polynomials
of OEIS A387347 for n <= 6, with DLMF Tables 3.5.6-3.5.9 (n = 5, 10, 15, 20)
and with MathWorld's rows for n <= 5, with the controls that must fail
failing.

**Conventions.** The weight function is e^{-x} on [0, inf), that is the
generalised rule with alpha = 0 only, and L_n is normalised by L_n(0) = 1 as
in Abramowitz-Stegun 22.3.9, DLMF 18.3 and table T102 (the roots do not
depend on the normalisation). Nodes are in increasing order; n = 1 is the
one-point rule x = 1, w = 1.
"""

import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField
from sage.rings.real_mpfi import RealIntervalField

#: Bits of working precision beyond what the written digits need. Measured
#: over the whole table at 100 digits: with a guard of 64 bits the widest
#: ball, relative to its value, was a weight at n = 30 (k = 21) with relative
#: radius 3e-104 -- 100 digits supported, with three to spare, because
#: L_{31} at a node near 40 loses about fifteen digits to cancellation. At
#: 128 the same ball has relative radius 1.6e-123, and the dry run prints
#: the measurement.
WORKING_GUARD = 128

#: Every rule up to here: 465 nodes and 465 weights. Entry length does not
#: grow with n; the bound matches the Gauss-Legendre table T132 and the
#: Gauss-Hermite table T134, and covers every order of Abramowitz-Stegun
#: Table 25.9 below 32.
ORDERS = 30

R = PolynomialRing(QQ, 'x')
x = R.gen()


def laguerre(N):
    """L_0, ..., L_N exactly in Q[x], by the three-term recurrence.

    (n + 1) L_{n+1} = (2n + 1 - x) L_n - n L_{n-1}, the one division written
    between Sage rationals, so nothing here is a float.
    """
    L = [R(1), 1 - x]
    for n in range(1, N):
        L.append(R(((2 * n + 1 - x) * L[n] - n * L[n - 1]) * (QQ(1) / QQ(n + 1))))
    return L


_L = laguerre(ORDERS + 2)


def _laguerre(n):
    if n >= len(_L):
        _L.extend(laguerre(n)[len(_L):])
    return _L[n]


def _factorial(n):
    f = ZZ(1)
    for i in range(2, n + 1):
        f *= i
    return f


def _moment(m):
    """int_0^inf x^m e^{-x} dx = m!, exactly."""
    return QQ(_factorial(m))


#: The polynomials a reader can recognise the small rules by, checked before
#: they are written into a comment. Nodes: (-1)^n n! L_n, monic with integer
#: coefficients. Weights: the minimal polynomial of the weights, OEIS A387347,
#: coefficients in decreasing order of the exponent.
NODE_POLYNOMIALS = {
    2: [1, -4, 2],
    3: [1, -9, 18, -6],
    4: [1, -16, 72, -96, 24],
}
WEIGHT_POLYNOMIALS = {
    2: [8, -8, 1],
    3: [1944, -1944, 405, -4],
    4: [1990656, -1990656, 504576, -16960, 9],
}


def _from_decreasing(coefficients):
    return R(list(reversed([QQ(c) for c in coefficients])))


def rule(n, bits):
    """(nodes, weights) of the n-point rule; balls, except the exact n = 1.

    Balls for the nodes and the weights of every rule with n >= 2, and the
    integer 1 for both entries of the one-point rule.
    """
    n = int(n)
    if n < 1:
        raise ValueError('n must be at least 1, not %s' % n)
    RIF = RealIntervalField(bits)
    RBF = RealBallField(bits)
    L = _laguerre(n)
    Lnext = _laguerre(n + 1)
    if n >= 2:
        rational = L.roots(ring=QQ, multiplicities=False)
        if rational:
            raise ArithmeticError('L_%d has rational roots %s, which the table would '
                                  'want written exactly' % (n, rational))
    roots = L.roots(ring=RIF, multiplicities=False)
    if len(roots) != n:
        raise ArithmeticError('isolated %d roots of L_%d' % (len(roots), n))
    nodes = [RBF(r) for r in roots]
    nodes.sort(key=lambda b: b.mid())
    for a, b in zip(nodes, nodes[1:]):
        if not bool(a < b):
            raise ArithmeticError('n=%d: two node enclosures are not separated' % n)
    if not (bool(nodes[0] > 0) and bool(nodes[-1] < 4 * n + 2)):
        raise ArithmeticError('n=%d: a node lies outside (0, 4n+2)' % n)

    weights = []
    for k, xb in enumerate(nodes, 1):
        w = xb / (RBF(n + 1) ** 2 * RBF(Lnext(xb)) ** 2)
        # the Christoffel function, sharing nothing with the formula above;
        # the L_j are orthonormal for e^{-x}, so no norms appear
        other = RBF(0)
        for j in range(n):
            other += RBF(_laguerre(j)(xb)) ** 2
        other = 1 / other
        if not (w.is_finite() and other.is_finite() and w.overlaps(other)):
            raise ArithmeticError(
                'n=%d k=%d: x/((n+1)^2 L_{n+1}(x)^2) and the Christoffel function '
                'disagree; neither is right until the disagreement has a cause' % (n, k))
        if not bool(w > 0):
            raise ArithmeticError('n=%d k=%d: weight is not positive' % (n, k))
        weights.append(w)
    # The weights do not decrease with k for every n -- at n = 7 the second
    # exceeds the first -- so the ordinal words in the comments for n <= 4
    # are checked where they are used, not assumed.
    if n in WEIGHT_POLYNOMIALS:
        for a, b in zip(weights, weights[1:]):
            if not bool(a > b):
                raise ArithmeticError('n=%d: the weights do not decrease with k, so the '
                                      'comments naming them by size are wrong' % n)

    # sum, and the degree of exactness with its control
    if not sum(weights).overlaps(RBF(1)):
        raise ArithmeticError('n=%d: the weights do not sum to 1' % n)
    for m in range(0, 2 * n):
        s = sum(w * xb ** m for w, xb in zip(weights, nodes))
        if not s.overlaps(RBF(_moment(m))):
            raise ArithmeticError('n=%d: the rule is not exact on x^%d' % (n, m))
    s = sum(w * xb ** (2 * n) for w, xb in zip(weights, nodes))
    if s.overlaps(RBF(_moment(2 * n))):
        raise ArithmeticError('n=%d: control failed, the rule appears exact on x^%d' % (n, 2 * n))

    # the polynomials the entry comments name
    if n in NODE_POLYNOMIALS:
        if _from_decreasing(NODE_POLYNOMIALS[n]) != (-1) ** n * _factorial(n) * L:
            raise ArithmeticError('n=%d: the node polynomial in the comment is not (-1)^n n! L_n' % n)
    if n in WEIGHT_POLYNOMIALS:
        q = _from_decreasing(WEIGHT_POLYNOMIALS[n])
        for k, w in enumerate(weights, 1):
            if not RBF(q(w)).contains_zero():
                raise ArithmeticError('n=%d k=%d: the weight polynomial in the comment does '
                                      'not vanish at the weight' % (n, k))

    if n == 1:
        if not (nodes[0].overlaps(RBF(1)) and weights[0].overlaps(RBF(1))):
            raise ArithmeticError('the one-point rule is not x = 1, w = 1')
        return [ZZ(1)], [ZZ(1)]
    return nodes, weights


_cache = {}


def cached_rule(n, bits):
    key = (int(n), int(bits))
    if key not in _cache:
        _cache[key] = rule(n, bits)
    return _cache[key]


def _ordinal(k, n):
    """Which root of a polynomial of degree n the k-th smallest is, in words."""
    if k == 1:
        return 'smallest'
    if k == n:
        return 'largest'
    if k == 2:
        return 'second smallest'
    if k == n - 1:
        return 'second largest'
    raise ValueError('no word for root %d of %d' % (k, n))


def _latex_poly(coefficients, var):
    terms = []
    degree = len(coefficients) - 1
    for i, c in enumerate(coefficients):
        e = degree - i
        if c == 0:
            continue
        sign = '-' if c < 0 else ('+' if terms else '')
        a = abs(c)
        body = ('' if a == 1 and e > 0 else str(a)) + (
            '' if e == 0 else var if e == 1 else '%s^%d' % (var, e))
        terms.append(sign + body)
    return ''.join(terms)


#: Closed forms a reader would recognise, for the entries that have one.
NAMED = {
    (1, 1, 'x'): r'$x_1=1$, the one-point rule',
    (1, 1, 'w'): r'$w_1=1=\int_0^\infty e^{-x}\,dx$',
    (2, 1, 'x'): r'$x_1=2-\sqrt{2}$',
    (2, 2, 'x'): r'$x_2=2+\sqrt{2}$',
    (2, 1, 'w'): r'$w_1=(2+\sqrt{2})/4$',
    (2, 2, 'w'): r'$w_2=(2-\sqrt{2})/4$',
}

#: Where the corpus already holds an entry: the integer 1, and the nodes of
#: degree 2 in the table of quadratic algebraic numbers (addresses read off
#: search results, not derived).
EQUALS = {
    (1, 1, 'x'): 'HREF{One}',
    (1, 1, 'w'): 'HREF{One}',
    (2, 1, 'x'): 'HREF{Algebraic_numbers_of_degree_2#1,-4,2,1}',
    (2, 2, 'x'): 'HREF{Algebraic_numbers_of_degree_2#1,-4,2,2}',
}


def annotate(n, k, expression, value):
    entry = {'number': value}
    comment = NAMED.get((n, k, expression))
    if comment is None and n in NODE_POLYNOMIALS and n >= 3:
        if expression == 'x':
            comment = r'$x_%d$ is the %s root of $%s=%s%d\,L_%d(x)$' % (
                k, _ordinal(k, n), _latex_poly(NODE_POLYNOMIALS[n], 'x'),
                '-' if n % 2 else '', _factorial(n), n)
        else:
            # the weights decrease with k, which rule() has checked
            comment = r'$w_%d$ is the %s root of $%s$ CITE{OEIS-weight-polynomials}' % (
                k, _ordinal(n + 1 - k, n), _latex_poly(WEIGHT_POLYNOMIALS[n], 'w'))
    if comment:
        entry['comment'] = comment
    if (n, k, expression) in EQUALS:
        entry['equals'] = EQUALS[(n, k, expression)]
    return entry


class GaussLaguerre(numberdb.Generator):

    table = 'T135'
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
        return annotate(n, k, expression, value)


if __name__ == '__main__':
    generator = GaussLaguerre()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='Gauss-Laguerre nodes and weights for n <= %d: roots of L_n '
                    'isolated over Q[x], weights in ball arithmetic, every rule '
                    'checked for its degree of exactness with a control before '
                    'being sent' % ORDERS))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
