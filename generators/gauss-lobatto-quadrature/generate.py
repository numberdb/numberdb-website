"""Nodes and weights of Gauss-Lobatto quadrature -- numberdb.org/T137

    int_{-1}^{1} f(x) dx  ~  sum_{k=1}^{n} w_k f(x_k),

exact for every polynomial f of degree at most 2n - 3, with both endpoints
among the nodes: x_1 = -1, x_n = 1, and the interior nodes x_2 < ... < x_{n-1}
the roots of P_{n-1}', the derivative of the Legendre polynomial of degree
n - 1. For every n from 2 to 30 both the nodes and the weights are listed, in
the order of the nodes, under the symbolic parameter `expression` (x or w).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**These digits are proven.** P_{n-1} is built exactly in Q[x] by Bonnet's
recurrence; the roots of P_{n-1}' are isolated by Sage's real root isolation
over the interval field (MPFI), so each interior node arrives as an interval
that provably contains exactly one root, and is carried from there as an arb
ball. The weight at an interior node is w_k = 2 / (n (n-1) P_{n-1}(x_k)^2)
(Abramowitz-Stegun 25.4.32) in ball arithmetic. The digits written are the
ones the ball supports.

**What is exact is written exactly.** The endpoints are returned as the
integers -1 and 1, and their weights 2 / (n (n-1)) as rationals. The node
x = 0 of every rule of odd order is taken off P_{n-1}' before isolating (the
isolator would return a ball of radius 1e-120 around it), and its weight
2 / (n (n-1) P_{n-1}(0)^2) is a rational, returned as one. The rules with
n <= 5 -- 1, 1; 1/3, 4/3, 1/3; 1/6, 5/6, 5/6, 1/6; 1/10, 49/90, 32/45, 49/90,
1/10 -- have rational weights throughout and are returned exactly, after the
ball formula has been seen to agree.

**Every rule is checked before any of it is returned**, against computations
sharing no code with the weight formula. With omega_n = (x^2 - 1) P_{n-1}',
the polynomial whose roots are the nodes, the weights must also equal
q(x_k) / omega_n'(x_k), where q(x) = int (omega_n(t) - omega_n(x)) / (t - x) dt
is the secondary polynomial of omega_n, exact in Q[x]; at the endpoints and
at x = 0 that quotient is computed exactly in Q and must equal the rational
weight exactly. omega_n must equal n (n-1) / (2n-1) (P_n - P_{n-2}) exactly.
The interior nodes must interlace with the roots of P_{n-1} and lie in
(-1, 1); the weights must be positive, symmetric and sum to 2; the rule must
integrate x^m to (1 + (-1)^m)/(m + 1) for every m <= 2n - 3 and must *fail*
to do so at m = 2n - 2; and the closed forms named in the entry comments for
n <= 7 must contain the computed values. A rule failing any of these is an
error rather than a table.

Outside the generator, when this was written, the same values were compared
with the rows for n = 3 to 6 on MathWorld and n = 3 to 7 on Wikipedia (the
closed forms verified exactly in Q(sqrt 7) and Q(sqrt 15)), with the weights
computed as the integrals of the Lagrange basis polynomials of the nodes,
with the Legendre polynomials stored in table T101 and the secondary
polynomials stored in T133 (omega_n and q in terms of them, exactly), with
the Gauss-Legendre nodes stored in T132 (the interlacing), and with an
mpmath computation on another machine to 50 digits, with the controls that
must fail failing.

**Conventions.** The interval is [-1, 1]; n counts all the points, the two
endpoints included, as in Abramowitz-Stegun Table 25.6, Wikipedia and
MathWorld; nodes are in increasing order and both signs are stored, because
search by number keeps the sign; n = 2 is the trapezoidal rule and n = 3 is
Simpson's rule.
"""

import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField
from sage.rings.real_mpfi import RealIntervalField

#: Bits of working precision beyond what the written digits need. Measured
#: over the whole table at 100 digits by the dry run: the widest ball
#: relative to its value is the weight at n = 30, k = 2, with relative
#: radius 1.5e-108, so it supports 107 digits; the nodes are better
#: (9.2e-120 at n = 25, k = 11).
WORKING_GUARD = 64

#: Every rule up to here: 464 nodes and 464 weights. Entry length does not
#: grow with n; the bound matches the Gauss-Legendre table T132, and covers
#: every order of Abramowitz-Stegun Table 25.6 (n <= 10) and every order a
#: spectral-element code uses in practice.
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


def _secondary(p):
    """q_p(x) = int_{-1}^1 (p(t) - p(x)) / (t - x) dt, exactly in Q[x].

    (t^j - x^j) / (t - x) = sum_{i<j} t^{j-1-i} x^i, integrated term by term.
    """
    q = R(0)
    for j, cj in enumerate(p.list()):
        if cj == 0:
            continue
        for i in range(j):
            q += cj * _moment(j - 1 - i) * x ** i
    return q


def lobatto_polynomial(n):
    """omega_n = (x^2 - 1) P_{n-1}', the polynomial of degree n whose roots are the nodes.

    Checked exactly against the other form n (n-1) / (2n-1) (P_n - P_{n-2}),
    which follows from (x^2 - 1) P_m' = m (x P_m - P_{m-1}) and Bonnet.
    """
    n = int(n)
    omega = (x ** 2 - 1) * _legendre(n - 1).derivative()
    other = (QQ(n * (n - 1)) / QQ(2 * n - 1)) * (_legendre(n) - _legendre(n - 2))
    if omega != other:
        raise ArithmeticError('n=%d: (x^2-1) P_{n-1}\' != n(n-1)/(2n-1) (P_n - P_{n-2})' % n)
    return omega


def _roots(p, RIF, RBF):
    """The real roots of p as balls, in increasing order, x = 0 taken off exactly."""
    p0 = p
    has_zero = p(QQ(0)) == 0
    if has_zero:
        p0 = R(p // x)
        if p0 * x != p:
            raise ArithmeticError('%s is not divisible by x' % p)
    roots = p0.roots(ring=RIF, multiplicities=False)
    if len(roots) != p0.degree():
        raise ArithmeticError('isolated %d roots of a polynomial of degree %d'
                              % (len(roots), p0.degree()))
    out = [RBF(r) for r in roots]
    if has_zero:
        out.append(RBF(0))
    out.sort(key=lambda b: b.mid())
    return out


#: The rules whose weights are all rational, given exactly. Verified against
#: the ball formula every time they are used.
RATIONAL_WEIGHTS = {
    2: [QQ(1), QQ(1)],
    3: [QQ(1) / 3, QQ(4) / 3, QQ(1) / 3],
    4: [QQ(1) / 6, QQ(5) / 6, QQ(5) / 6, QQ(1) / 6],
    5: [QQ(1) / 10, QQ(49) / 90, QQ(32) / 45, QQ(49) / 90, QQ(1) / 10],
}


def _closed_forms(n, RBF):
    """The closed forms of the entry comments for n = 6, 7, as balls, keyed by (k, expression).

    Written on Wikipedia's Gaussian quadrature page (Gauss-Lobatto rules)
    and verified exactly in Q(sqrt 7) and Q(sqrt 15) outside the generator;
    here each must contain the computed value.
    """
    out = {}
    if n == 6:
        s7 = RBF(7).sqrt()
        inner, outer = (RBF(1) / 3 - 2 * s7 / 21).sqrt(), (RBF(1) / 3 + 2 * s7 / 21).sqrt()
        out[(2, 'x')], out[(3, 'x')], out[(4, 'x')], out[(5, 'x')] = -outer, -inner, inner, outer
        w_in, w_out = (14 + s7) / 30, (14 - s7) / 30
        out[(2, 'w')], out[(3, 'w')], out[(4, 'w')], out[(5, 'w')] = w_out, w_in, w_in, w_out
    if n == 7:
        s53 = (RBF(5) / 3).sqrt()
        s15 = RBF(15).sqrt()
        inner = (RBF(5) / 11 - 2 * s53 / 11).sqrt()
        outer = (RBF(5) / 11 + 2 * s53 / 11).sqrt()
        out[(2, 'x')], out[(3, 'x')], out[(5, 'x')], out[(6, 'x')] = -outer, -inner, inner, outer
        w_in, w_out = (124 + 7 * s15) / 350, (124 - 7 * s15) / 350
        out[(2, 'w')], out[(3, 'w')], out[(5, 'w')], out[(6, 'w')] = w_out, w_in, w_in, w_out
        out[(4, 'w')] = RBF(256) / 525
    return out


def rule(n, bits):
    """(nodes, weights) of the n-point rule; nodes as balls, exact where exact.

    Balls for the interior nodes, the exact -1 and 1 for the endpoints, the
    exact 0 for the central node of odd n, rationals for the endpoint
    weights, the central weight and the weights of n <= 5, balls otherwise.
    """
    n = int(n)
    if n < 2:
        raise ValueError('n must be at least 2, not %s' % n)
    RIF = RealIntervalField(bits)
    RBF = RealBallField(bits)
    Pm = _legendre(n - 1)
    dP = Pm.derivative()
    omega = lobatto_polynomial(n)
    interior = _roots(dP, RIF, RBF)
    if len(interior) != n - 2:
        raise ArithmeticError('n=%d: %d interior nodes' % (n, len(interior)))
    centre = (n + 1) // 2 if n % 2 == 1 else None
    if centre is not None and not interior[centre - 2].is_zero():
        raise ArithmeticError('n=%d: the central node is not exactly 0' % n)
    nodes = [RBF(-1)] + interior + [RBF(1)]
    for a, b in zip(nodes, nodes[1:]):
        if not bool(a < b):
            raise ArithmeticError('n=%d: two node enclosures are not separated' % n)
    # the interior nodes are the extrema of P_{n-1}, so they interlace with its roots
    zeros = _roots(Pm, RIF, RBF)
    if len(zeros) != n - 1:
        raise ArithmeticError('n=%d: isolated %d roots of P_{n-1}' % (n, len(zeros)))
    for i, xb in enumerate(interior):
        if not (bool(zeros[i] < xb) and bool(xb < zeros[i + 1])):
            raise ArithmeticError('n=%d: interior node %d does not lie between two roots of P_{n-1}'
                                  % (n, i + 2))

    nn = QQ(n * (n - 1))
    q = _secondary(omega)
    d_omega = omega.derivative()
    w_end = QQ(2) / nn
    for e in (QQ(-1), QQ(1)):
        if q(e) / d_omega(e) != w_end:
            raise ArithmeticError('n=%d: q(%s)/omega\'(%s) != 2/(n(n-1))' % (n, e, e))
    weights = []
    for k, xb in enumerate(nodes, 1):
        if k in (1, n):
            w = w_end
            wb = RBF(w)
        elif k == centre:
            p0 = Pm(QQ(0))
            w = QQ(2) / (nn * p0 * p0)                      # exact
            if q(QQ(0)) / d_omega(QQ(0)) != w:
                raise ArithmeticError('n=%d: q(0)/omega\'(0) != 2/(n(n-1) P_{n-1}(0)^2)' % n)
            wb = RBF(w)
        else:
            w = 2 / (RBF(nn) * RBF(Pm(xb)) ** 2)
            wb = w
        other = RBF(q(xb)) / RBF(d_omega(xb))
        if not (wb.is_finite() and other.is_finite() and wb.overlaps(other)):
            raise ArithmeticError(
                'n=%d k=%d: 2/(n(n-1) P_{n-1}(x)^2) and q(x)/omega\'(x) disagree; '
                'neither is right until the disagreement has a cause' % (n, k))
        if not bool(wb > 0):
            raise ArithmeticError('n=%d k=%d: weight is not positive' % (n, k))
        weights.append(w)

    if n in RATIONAL_WEIGHTS:
        for k, (w, exact) in enumerate(zip(weights, RATIONAL_WEIGHTS[n]), 1):
            if not RBF(w).overlaps(RBF(exact)):
                raise ArithmeticError('n=%d k=%d: the ball weight does not contain %s'
                                      % (n, k, exact))
        weights = list(RATIONAL_WEIGHTS[n])
    for (k, expression), claimed in _closed_forms(n, RBF).items():
        computed = nodes[k - 1] if expression == 'x' else RBF(weights[k - 1])
        if not computed.overlaps(claimed):
            raise ArithmeticError('n=%d k=%d: the closed form of %s in the comment does not '
                                  'contain the computed value' % (n, k, expression))

    # symmetry, sum, and the degree of exactness with its control
    for k in range(n):
        if not (nodes[k] + nodes[n - 1 - k]).contains_zero():
            raise ArithmeticError('n=%d: nodes are not symmetric at k=%d' % (n, k + 1))
        if not RBF(weights[k]).overlaps(RBF(weights[n - 1 - k])):
            raise ArithmeticError('n=%d: weights are not symmetric at k=%d' % (n, k + 1))
    if not sum(RBF(w) for w in weights).overlaps(RBF(2)):
        raise ArithmeticError('n=%d: the weights do not sum to 2' % n)
    for m in range(0, 2 * n - 2):
        s = sum(RBF(w) * xb ** m for w, xb in zip(weights, nodes))
        if not s.overlaps(RBF(_moment(m))):
            raise ArithmeticError('n=%d: the rule is not exact on x^%d' % (n, m))
    m = 2 * n - 2
    s = sum(RBF(w) * xb ** m for w, xb in zip(weights, nodes))
    if s.overlaps(RBF(_moment(m))):
        raise ArithmeticError('n=%d: control failed, the rule appears exact on x^%d' % (n, m))
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
    (2, 1, 'x'): r'the trapezoidal rule',
    (2, 1, 'w'): r'$w_1=1$, the trapezoidal rule',
    (2, 2, 'w'): r'$w_2=1$',
    (3, 2, 'x'): r"$x_2=0$: Simpson's rule",
    (3, 1, 'w'): r"$w_1=1/3$, Simpson's rule",
    (3, 2, 'w'): r'$w_2=4/3$',
    (3, 3, 'w'): r'$w_3=1/3$',
    (4, 2, 'x'): r'$x_2=-1/\sqrt{5}$',
    (4, 3, 'x'): r'$x_3=1/\sqrt{5}$',
    (4, 1, 'w'): r'$w_1=1/6$',
    (4, 2, 'w'): r'$w_2=5/6$',
    (4, 3, 'w'): r'$w_3=5/6$',
    (4, 4, 'w'): r'$w_4=1/6$',
    (5, 2, 'x'): r'$x_2=-\sqrt{3/7}$',
    (5, 4, 'x'): r'$x_4=\sqrt{3/7}$',
    (5, 1, 'w'): r'$w_1=1/10$',
    (5, 2, 'w'): r'$w_2=49/90$',
    (5, 3, 'w'): r'$w_3=32/45$',
    (5, 4, 'w'): r'$w_4=49/90$',
    (5, 5, 'w'): r'$w_5=1/10$',
    (6, 2, 'x'): r'$x_2=-\sqrt{\tfrac13+\tfrac{2\sqrt{7}}{21}}$',
    (6, 3, 'x'): r'$x_3=-\sqrt{\tfrac13-\tfrac{2\sqrt{7}}{21}}$',
    (6, 4, 'x'): r'$x_4=\sqrt{\tfrac13-\tfrac{2\sqrt{7}}{21}}$',
    (6, 5, 'x'): r'$x_5=\sqrt{\tfrac13+\tfrac{2\sqrt{7}}{21}}$',
    (6, 1, 'w'): r'$w_1=1/15$',
    (6, 2, 'w'): r'$w_2=(14-\sqrt{7})/30$',
    (6, 3, 'w'): r'$w_3=(14+\sqrt{7})/30$',
    (6, 4, 'w'): r'$w_4=(14+\sqrt{7})/30$',
    (6, 5, 'w'): r'$w_5=(14-\sqrt{7})/30$',
    (6, 6, 'w'): r'$w_6=1/15$',
    (7, 2, 'x'): r'$x_2=-\sqrt{\tfrac{5}{11}+\tfrac{2}{11}\sqrt{5/3}}$',
    (7, 3, 'x'): r'$x_3=-\sqrt{\tfrac{5}{11}-\tfrac{2}{11}\sqrt{5/3}}$',
    (7, 5, 'x'): r'$x_5=\sqrt{\tfrac{5}{11}-\tfrac{2}{11}\sqrt{5/3}}$',
    (7, 6, 'x'): r'$x_6=\sqrt{\tfrac{5}{11}+\tfrac{2}{11}\sqrt{5/3}}$',
    (7, 1, 'w'): r'$w_1=1/21$',
    (7, 2, 'w'): r'$w_2=(124-7\sqrt{15})/350$',
    (7, 3, 'w'): r'$w_3=(124+7\sqrt{15})/350$',
    (7, 4, 'w'): r'$w_4=256/525$',
    (7, 5, 'w'): r'$w_5=(124+7\sqrt{15})/350$',
    (7, 6, 'w'): r'$w_6=(124-7\sqrt{15})/350$',
    (7, 7, 'w'): r'$w_7=1/21$',
}

#: Where the corpus already holds an entry: the endpoints, the central zero,
#: the unit weights of the trapezoidal rule, and the nodes +-1/sqrt(5) in the
#: table of quadratic algebraic numbers (addresses read off search results,
#: not derived).
EQUALS = {
    (2, 1, 'w'): 'HREF{One}',
    (2, 2, 'w'): 'HREF{One}',
    (4, 2, 'x'): 'HREF{Algebraic_numbers_of_degree_2#5,0,-1,1}',
    (4, 3, 'x'): 'HREF{Algebraic_numbers_of_degree_2#5,0,-1,2}',
}


def annotate(n, k, expression, value):
    entry = {'number': value}
    comment = NAMED.get((n, k, expression))
    if comment:
        entry['comment'] = comment
    if expression == 'x' and k == 1:
        entry['equals'] = 'HREF{Integers#-1}'
    elif expression == 'x' and k == n:
        entry['equals'] = 'HREF{One}'
    elif expression == 'x' and n % 2 == 1 and k == (n + 1) // 2:
        entry['equals'] = 'HREF{Zero}'
    if (n, k, expression) in EQUALS:
        entry['equals'] = EQUALS[(n, k, expression)]
    return entry


class GaussLobatto(numberdb.Generator):

    table = 'T137'
    parameters = ('n', 'k', 'expression')
    type = 'R'
    digits = 100
    rigour = 'proven'

    def enumerate(self, orders=ORDERS):
        for n in range(2, orders + 1):
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
        if expression == 'x':
            if k == 1:
                value = ZZ(-1)
            elif k == n:
                value = ZZ(1)
            elif value.is_zero():
                value = ZZ(0)
        return annotate(n, k, expression, value)


if __name__ == '__main__':
    generator = GaussLobatto()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='Gauss-Lobatto nodes and weights for 2 <= n <= %d: roots of P_{n-1}\' '
                    'isolated over Q[x], endpoints and rational weights exact, weights in '
                    'ball arithmetic, every rule checked for its degree of exactness with a '
                    'control before being sent' % ORDERS))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
