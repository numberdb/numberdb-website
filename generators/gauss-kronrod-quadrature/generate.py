"""Nodes and weights of Gauss-Kronrod quadrature -- numberdb.org/T136

    int_{-1}^{1} f(x) dx  ~  sum_{k=1}^{2n+1} w_k f(x_k),

the (2n+1)-point Kronrod extension of the n-point Gauss-Legendre rule: the n
Gauss nodes (the roots of the Legendre polynomial P_n) together with the n+1
roots of the Stieltjes polynomial E_{n+1}, and the interpolatory weights on
those 2n+1 points, exact for every polynomial of degree at most 3n+1 (3n+2
for odd n). Nodes x_1 < ... < x_{2n+1} and weights are listed under the
symbolic parameter `expression` (x or w) for n <= 15 and for the three larger
rules of QUADPACK, n = 20, 25, 30.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**These digits are proven.** P_n is built exactly in Q[x] by Bonnet's
recurrence. E_{n+1} is the monic polynomial of degree n+1 with
int P_n E_{n+1} x^j dx = 0 for j <= n, found exactly by solving that linear
system over Q (Gaussian elimination written out, so that no part of Sage that
the named imports leave uninitialised is needed). The roots of P_n and of
E_{n+1} are isolated separately by Sage's real root isolation over the
interval field (MPFI), so each node arrives as an interval provably
containing exactly one root, and is carried from there as an arb ball. With
omega = P_n E_{n+1}, the weight is w_k = q_omega(x_k) / omega'(x_k), where
q_omega(x) = int (omega(t) - omega(x)) / (t - x) dt is the secondary
polynomial of omega, exact in Q[x]; the division is done in ball arithmetic
and the digits written are the ones the ball supports.

**What is exact is written exactly.** x = 0 is a node of every rule (of P_n
for odd n, of E_{n+1} for even n); it is taken off before isolating, returned
as the integer 0, and its weight q_omega(0) / omega'(0) is a rational,
returned as one. The rules with n <= 2 have rational weights throughout
(5/9, 8/9, 5/9; and 98/495, 27/55, 28/45, 27/55, 98/495), and at n = 3 the
weights at the Gauss nodes +-sqrt(3/5) are 12500/46557; those are returned
exactly after the ball formula has been seen to agree.

**Every rule is checked before any of it is returned.** The Stieltjes
polynomial must satisfy its defining orthogonality exactly; the identity
q_omega = c_n + E_{n+1} q_n with c_n = int P_n x^n dx and q_n the secondary
polynomial of P_n must hold exactly in Q[x] (it is what makes the weights
w = lambda + c_n / (P_n'(x) E_{n+1}(x)) at a Gauss node with Gauss weight
lambda, and w = c_n / (P_n(x) E_{n+1}'(x)) at a Stieltjes node), and those
formulas must agree with q_omega / omega' at every node; the Stieltjes roots
must interlace with the Gauss roots and all lie in (-1, 1); the weights must
be positive, symmetric, sum to 2, and at each Gauss node lie below the Gauss
weight; the rule must integrate x^m to (1 + (-1)^m)/(m + 1) for every
m <= 3n + 1 and must *fail* to do so at the first even m beyond (3n + 2 for
even n, 3n + 3 for odd n). A rule failing any of these is an error rather
than a table.

Outside the generator, when this was written, the same values were compared
with the 33-digit constants of QUADPACK's dqk15, dqk21, dqk31, dqk41, dqk51
and dqk61 (281 values, one of them -- the central weight of the 51-point
rule -- differing from the rational value by 1.4 units in its 33rd digit),
with the fifteen-point row on Wikipedia's Gauss-Kronrod page, with closed
forms for n <= 3 computed in Q and Q(sqrt 330), with the Stieltjes
polynomials from a second linear system in the Legendre basis solved by
Sage's own matrix solver, with the interpolatory weights computed as the
integrals of the Lagrange basis polynomials, and with the stored Gauss nodes
and weights of table T132, with the controls that must fail failing.

**Conventions.** The interval is [-1, 1]; nodes are in increasing order and
both signs are stored, because search by number keeps the sign; n counts the
points of the embedded Gauss rule, so the Kronrod rule has 2n + 1 points and
the Gauss nodes are x_2, x_4, ..., x_2n. n = 1 is the extension of the
midpoint rule, which is the three-point Gauss rule.
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
#: ball relative to its value was a weight of the 61-point rule (n = 30,
#: k = 2) with relative radius 1.7e-96 -- fewer than the 100 digits asked
#: for, because q_omega and omega' for a polynomial of degree 61 with
#: coefficients of forty digits cancel about twenty digits at a node near
#: the end of the interval. With this guard the dry run measures the same
#: ball at relative radius 2.2e-125; the nodes are far better (1.2e-148 at
#: n = 12, k = 12).
WORKING_GUARD = 160

#: The orders listed: every rule with n <= 15 (3 to 31 points), and the three
#: larger rules of QUADPACK's dqk41, dqk51 and dqk61 (n = 20, 25, 30). All
#: n <= 30 would be 1980 entries, over the soft limit of 1200; these are 816.
ORDERS = list(range(1, 16)) + [20, 25, 30]

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


_P = legendre(max(ORDERS) + 1)


def _legendre(n):
    if n >= len(_P):
        _P.extend(legendre(n)[len(_P):])
    return _P[n]


def _moment(m):
    """int_{-1}^1 x^m dx, exactly."""
    return QQ(2) / QQ(m + 1) if m % 2 == 0 else QQ(0)


def _integral(p):
    """int_{-1}^1 p(x) dx, exactly, for p in Q[x]."""
    return sum(QQ(c) * _moment(m) for m, c in enumerate(p.list()))


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


def _solve(A, b):
    """Solve A c = b over Q by Gaussian elimination, written out.

    `matrix(QQ, A).solve_right` reaches for parts of Sage the named imports
    do not initialise; the systems here are at most 31 by 31.
    """
    n = len(A)
    M = [[QQ(v) for v in row] + [QQ(b[i])] for i, row in enumerate(A)]
    for col in range(n):
        pivot = next((r for r in range(col, n) if M[r][col] != 0), None)
        if pivot is None:
            raise ArithmeticError('the Stieltjes system is singular')
        M[col], M[pivot] = M[pivot], M[col]
        inv = QQ(1) / M[col][col]
        M[col] = [v * inv for v in M[col]]
        for r in range(n):
            if r != col and M[r][col] != 0:
                f = M[r][col]
                M[r] = [a - f * c for a, c in zip(M[r], M[col])]
    return [M[i][n] for i in range(n)]


def stieltjes(n):
    """E_{n+1}: monic of degree n + 1 with int P_n E_{n+1} x^j dx = 0 for j <= n.

    The n + 1 conditions are linear in the n + 1 lower coefficients; the
    solution is checked against the definition before it is returned.
    """
    P = _legendre(n)
    A = [[_integral(P * x ** (i + j)) for i in range(n + 1)] for j in range(n + 1)]
    b = [-_integral(P * x ** (n + 1 + j)) for j in range(n + 1)]
    c = _solve(A, b)
    E = x ** (n + 1) + sum(c[i] * x ** i for i in range(n + 1))
    for j in range(n + 1):
        if _integral(P * E * x ** j) != 0:
            raise ArithmeticError('n=%d: P_n E_{n+1} is not orthogonal to x^%d' % (n, j))
    # the control must have even parity as a whole, or it vanishes by symmetry
    m = n + 1 if n % 2 == 0 else n + 2
    if _integral(P * E * x ** m) == 0:
        raise ArithmeticError('n=%d: control failed, P_n E_{n+1} orthogonal to x^%d too' % (n, m))
    return E


_E = {}


def _stieltjes(n):
    if n not in _E:
        _E[n] = stieltjes(n)
    return _E[n]


#: Weights that are rational, apart from the central one that every rule has,
#: keyed by (n, k). Found by solving the symmetric Vandermonde system exactly
#: (in Q for n <= 2, where every x_k^2 is rational, and in Q(sqrt 330) for
#: n = 3); each is compared with the ball before it replaces it.
RATIONAL_WEIGHTS = {
    (1, 1): QQ(5) / 9, (1, 3): QQ(5) / 9,
    (2, 1): QQ(98) / 495, (2, 2): QQ(27) / 55, (2, 4): QQ(27) / 55, (2, 5): QQ(98) / 495,
    (3, 2): QQ(12500) / 46557, (3, 6): QQ(12500) / 46557,
}


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


def rule(n, bits):
    """(nodes, weights) of the (2n+1)-point rule; balls, exact where exact.

    Balls for the nodes, the exact 0 for the central node, a rational for the
    central weight and for the other rational weights of n <= 3, balls for
    every other weight.
    """
    n = int(n)
    if n < 1:
        raise ValueError('n must be at least 1, not %s' % n)
    RIF = RealIntervalField(bits)
    RBF = RealBallField(bits)
    P = _legendre(n)
    E = _stieltjes(n)
    omega = P * E
    gauss = _roots(P, RIF, RBF)
    stiel = _roots(E, RIF, RBF)
    if len(gauss) != n or len(stiel) != n + 1:
        raise ArithmeticError('n=%d: %d Gauss and %d Stieltjes roots' % (n, len(gauss), len(stiel)))
    # interlacing: xi_1 < x_1 < xi_2 < ... < x_n < xi_{n+1}
    nodes = []
    for i in range(n):
        nodes.append(stiel[i])
        nodes.append(gauss[i])
    nodes.append(stiel[n])
    N = 2 * n + 1
    for a, b in zip(nodes, nodes[1:]):
        if not bool(a < b):
            raise ArithmeticError('n=%d: the Stieltjes and Gauss roots do not interlace, or two '
                                  'enclosures are not separated' % n)
    if not (bool(nodes[0] > -1) and bool(nodes[-1] < 1)):
        raise ArithmeticError('n=%d: a node lies outside (-1, 1)' % n)
    if not nodes[n].is_zero():
        raise ArithmeticError('n=%d: the central node is not exactly 0' % n)

    q_omega = _secondary(omega)
    q_n = _secondary(P)
    c_n = _integral(P * x ** n)
    if q_omega != c_n + E * q_n:
        raise ArithmeticError('n=%d: q_omega != c_n + E_{n+1} q_n' % n)
    d_omega, dP, dE = omega.derivative(), P.derivative(), E.derivative()

    weights = []
    for k, xb in enumerate(nodes, 1):
        if k == n + 1:
            w = q_omega(QQ(0)) / d_omega(QQ(0))                  # exact
            wb = RBF(w)
        else:
            w = RBF(q_omega(xb)) / RBF(d_omega(xb))
            wb = w
        if k % 2 == 0:                                            # a Gauss node
            lam = 2 / ((1 - xb ** 2) * RBF(dP(xb)) ** 2)
            other = lam + RBF(c_n) / (RBF(dP(xb)) * RBF(E(xb)))
            if n >= 2 and not bool(wb < lam):
                raise ArithmeticError('n=%d k=%d: the Kronrod weight at a Gauss node is not below '
                                      'the Gauss weight' % (n, k))
        else:                                                     # a Stieltjes node
            other = RBF(c_n) / (RBF(P(xb)) * RBF(dE(xb)))
        if not (wb.is_finite() and other.is_finite() and wb.overlaps(other)):
            raise ArithmeticError(
                'n=%d k=%d: q_omega/omega\' and the c_n/(P_n E_{n+1})\' formula disagree; '
                'neither is right until the disagreement has a cause' % (n, k))
        if not bool(wb > 0):
            raise ArithmeticError('n=%d k=%d: weight is not positive' % (n, k))
        if (n, k) in RATIONAL_WEIGHTS:
            exact = RATIONAL_WEIGHTS[(n, k)]
            if not wb.overlaps(RBF(exact)):
                raise ArithmeticError('n=%d k=%d: the ball weight does not contain %s' % (n, k, exact))
            w = exact
        weights.append(w)

    # symmetry, sum, and the degree of exactness with its control
    for k in range(N):
        if not (nodes[k] + nodes[N - 1 - k]).contains_zero():
            raise ArithmeticError('n=%d: nodes are not symmetric at k=%d' % (n, k + 1))
        if not RBF(weights[k]).overlaps(RBF(weights[N - 1 - k])):
            raise ArithmeticError('n=%d: weights are not symmetric at k=%d' % (n, k + 1))
    if not sum(RBF(w) for w in weights).overlaps(RBF(2)):
        raise ArithmeticError('n=%d: the weights do not sum to 2' % n)
    for m in range(0, 3 * n + 2):
        s = sum(RBF(w) * xb ** m for w, xb in zip(weights, nodes))
        if not s.overlaps(RBF(_moment(m))):
            raise ArithmeticError('n=%d: the rule is not exact on x^%d' % (n, m))
    m = 3 * n + 2 if n % 2 == 0 else 3 * n + 3
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
#: Signs follow the increasing order of the nodes.
NAMED = {
    (1, 1, 'x'): r'$x_1=-\sqrt{3/5}$',
    (1, 2, 'x'): r'$x_2=0$; the Kronrod extension of the midpoint rule is the three-point Gauss rule',
    (1, 3, 'x'): r'$x_3=\sqrt{3/5}$',
    (1, 1, 'w'): r'$w_1=5/9$',
    (1, 2, 'w'): r'$w_2=8/9$',
    (1, 3, 'w'): r'$w_3=5/9$',
    (2, 1, 'x'): r'$x_1=-\sqrt{6/7}$',
    (2, 2, 'x'): r'$x_2=-1/\sqrt{3}$',
    (2, 3, 'x'): r'$x_3=0$',
    (2, 4, 'x'): r'$x_4=1/\sqrt{3}$',
    (2, 5, 'x'): r'$x_5=\sqrt{6/7}$',
    (2, 1, 'w'): r'$w_1=98/495$',
    (2, 2, 'w'): r'$w_2=27/55$',
    (2, 3, 'w'): r'$w_3=28/45$',
    (2, 4, 'w'): r'$w_4=27/55$',
    (2, 5, 'w'): r'$w_5=98/495$',
    (3, 1, 'x'): r'$x_1=-\tfrac13\sqrt{5+2\sqrt{30/11}}$',
    (3, 2, 'x'): r'$x_2=-\sqrt{3/5}$',
    (3, 3, 'x'): r'$x_3=-\tfrac13\sqrt{5-2\sqrt{30/11}}$',
    (3, 4, 'x'): r'$x_4=0$',
    (3, 5, 'x'): r'$x_5=\tfrac13\sqrt{5-2\sqrt{30/11}}$',
    (3, 6, 'x'): r'$x_6=\sqrt{3/5}$',
    (3, 7, 'x'): r'$x_7=\tfrac13\sqrt{5+2\sqrt{30/11}}$',
    (3, 1, 'w'): r'$w_1=(4057614-130977\sqrt{330})/16036300$',
    (3, 2, 'w'): r'$w_2=12500/46557$',
    (3, 3, 'w'): r'$w_3=(4057614+130977\sqrt{330})/16036300$',
    (3, 4, 'w'): r'$w_4=22016/48825$',
    (3, 5, 'w'): r'$w_5=(4057614+130977\sqrt{330})/16036300$',
    (3, 6, 'w'): r'$w_6=12500/46557$',
    (3, 7, 'w'): r'$w_7=(4057614-130977\sqrt{330})/16036300$',
}

CENTRAL_NODE = r'$x_{%d}=0$, the central node of every rule'

#: The table of the Gauss-Legendre rules, whose entries the Gauss nodes are
#: (address read off a search result, not derived from the title).
GAUSS_TABLE = 'Nodes_and_weights_of_Gauss_Legendre_quadrature'


def annotate(n, k, expression, value):
    entry = {'number': value}
    comment = NAMED.get((n, k, expression))
    if comment is None and expression == 'x' and k == n + 1:
        comment = CENTRAL_NODE % k
    if comment:
        entry['comment'] = comment
    if n == 1:
        # the whole rule is the three-point Gauss rule, entry by entry
        entry['equals'] = 'HREF{%s#3,%d,%s}' % (GAUSS_TABLE, k, expression)
    elif expression == 'x' and k % 2 == 0:
        entry['equals'] = 'HREF{%s#%d,%d,x}' % (GAUSS_TABLE, n, k // 2)
    elif expression == 'x' and k == n + 1:
        entry['equals'] = 'HREF{Zero}'
    return entry


class GaussKronrod(numberdb.Generator):

    table = 'T136'
    parameters = ('n', 'k', 'expression')
    type = 'R'
    digits = 100
    rigour = 'proven'

    def enumerate(self, orders=ORDERS):
        for n in orders:
            for k in range(1, 2 * n + 2):
                for expression in ('x', 'w'):
                    yield {'n': n, 'k': k, 'expression': expression}

    def value(self, params, digits):
        n, k = int(params['n']), int(params['k'])
        expression = params['expression']
        if not 1 <= k <= 2 * n + 1:
            raise ValueError('k must satisfy 1 <= k <= 2n+1, not %s' % k)
        if expression not in ('x', 'w'):
            raise ValueError("expression is 'x' or 'w', not %r" % expression)
        bits = numberdb.bits(digits, losing=WORKING_GUARD)
        nodes, weights = cached_rule(n, bits)
        value = nodes[k - 1] if expression == 'x' else weights[k - 1]
        if expression == 'x' and k == n + 1:
            value = ZZ(0)
        return annotate(n, k, expression, value)


if __name__ == '__main__':
    generator = GaussKronrod()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='Gauss-Kronrod nodes and weights for n <= 15 and n = 20, 25, 30: '
                    'Stieltjes polynomials solved exactly over Q, roots isolated over Q[x], '
                    'weights in ball arithmetic, every rule checked for its degree of '
                    'exactness with a control before being sent'))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
