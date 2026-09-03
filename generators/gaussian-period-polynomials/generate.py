"""Gaussian period polynomials -- numberdb.org/T146

    Psi_{p,k}(x) = prod_{j=0}^{k-1} (x - eta_j),    eta_j = sum_{i=0}^{f-1} zeta_p^(g^(j+ki)),

for a prime p and a divisor k of p - 1 with 1 < k < p - 1, where f = (p-1)/k,
g is a primitive root modulo p and zeta_p = exp(2 pi i / p). The eta_j are the
k Gaussian periods of length f, and Psi_{p,k} is monic in Z[x], irreducible of
degree k, and defines the unique subfield of degree k of Q(zeta_p). Neither g
nor the numbering of the periods matters: another primitive root permutes
them. Psi_{7,3} = x^3 + x^2 - 2x - 1; Psi_{17,8} is the equation of
2 cos(2 pi/17) that Gauss solved for the 17-gon.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**Which rows.** Every prime p < 200 and every divisor k of p - 1 with
2 <= k <= 12 and k < p - 1: 158 entries. k = p - 1 is the cyclotomic
polynomial Phi_p, which the table of cyclotomic polynomials holds, and k = 1
is x + 1; both are left out. The cap on k is a cap on the degree, where an
entry stops being something a person reads; the cap on p is a choice of what
is common. The longest entry is 130 characters (p = 193, k = 12) and the
block 13 KB; p < 500 would be 346 entries and 30 KB.

**Every value is proven before it is returned, without trusting either
library it is compared with.** The candidate is the product of x - eta_j in
Q(zeta_p)[x], computed exactly with Sage's cyclotomic field, with every
coefficient required to be a rational integer. It must equal PARI's
polsubcyclo(p, k), a different algorithm. And the same product computed in
ComplexBallField must enclose every coefficient in a ball of radius below
1/2 with an imaginary part containing zero, which determines an integer
coefficient on its own. The theorems the comments and formulas rely on are
checks run on every entry before it is returned: monic of degree k and
irreducible; the x^(k-1) coefficient is 1 (the periods sum to -1);
Psi = (x - f)^k modulo p (each period is f modulo 1 - zeta_p); the
quadratic and cubic closed forms of Gauss, with 4p = L^2 + 27 M^2, L = 1
(mod 3), which the cubic comments quote; the discriminant is
(-1)^(r_2) p^(k-1) times a perfect square, the discriminant of the subfield
times the square of an index; and no root is real when f is odd, proven by
balls excluding the real axis, while every root ball meets the real axis
when f is even. The controls that must fail do: Psi_{7,3} is not
polsubcyclo(7, 2), and Psi_{13,3} is not (x - 3)^3 modulo 13.

When this was written the values were also checked, outside the generator,
against OEIS A394567 (the product of the three cubic periods, formally
verified in Lean) on all 21 cubic rows; against Brillhart's theorem and OEIS
A203411 that the discriminant is exactly p^((p-3)/2) when f = 2, on all 7
such rows; against Sage's CyclotomicField(p).subfields(k), which must be
isomorphic to the field Psi defines, for p <= 61 (52 rows); against Sage's
exact Gauss sums through tau(chi) = sum_j chi(g)^j eta_j for every
character of order d | k, d > 1, p <= 61 (91 pairs), and against the stored
hundred-digit Gauss sums of numberdb.org's table of them for p <= 50 (71
pairs); against 2 cos(2 pi a / p) in balls for the f = 2 rows; and Psi_{7,6},
computed as a control and not stored, is Phi_7.
"""

import sys

import numberdb.sage as numberdb
from sage.arith.misc import is_prime, primitive_root
from sage.libs.pari import pari
from sage.rings.complex_arb import ComplexBallField
from sage.rings.integer_ring import ZZ
from sage.rings.number_field.number_field import CyclotomicField
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ

#: Every prime p below here.
BOUND = 200

#: Every divisor k of p - 1 with 2 <= k <= KMAX and k < p - 1.
KMAX = 12

#: Bits for the ball product. The coefficients have at most 17 digits in
#: range, and at 256 bits the worst radius over the table is 1.7e-66; the
#: requirement is only that it be below 1/2.
BITS = 256

ZX = PolynomialRing(ZZ, 'x')
x = ZX.gen()


def rows(bound=BOUND, kmax=KMAX):
    """(p, k) for every prime p < bound and divisor k of p - 1, 2 <= k <= kmax, k < p - 1."""
    for p in range(5, bound):
        if not is_prime(p):
            continue
        for k in range(2, kmax + 1):
            if (p - 1) % k == 0 and k < p - 1:
                yield ZZ(p), ZZ(k)


# ---------------------------------------------------------------- the three routes

def exact_polynomial(p, k):
    """prod (x - eta_j) in Q(zeta_p)[x], every coefficient required to be an integer."""
    K = CyclotomicField(p)
    z = K.gen()
    g = primitive_root(p)
    f = (p - 1) // k
    periods = [sum(z ** pow(g, j + k * i, p) for i in range(f)) for j in range(k)]
    KX = PolynomialRing(K, 'x')
    t = KX.gen()
    P = KX(1)
    for eta in periods:
        P *= (t - eta)
    coefficients = []
    for c in P.list():
        if not c.is_rational():
            raise ArithmeticError('(%s, %s): a coefficient %s is not rational' % (p, k, c))
        c = QQ(c)
        if c.denominator() != 1:
            raise ArithmeticError('(%s, %s): a coefficient %s is not an integer' % (p, k, c))
        coefficients.append(ZZ(c))
    return ZX(coefficients)


def pari_polynomial(p, k):
    """PARI's polsubcyclo(p, k), the polynomial it gives for the degree-k subfield."""
    g = pari.polsubcyclo(p, k)
    if g.type() == 't_VEC':
        if len(g) != 1:
            raise ArithmeticError('(%s, %s): polsubcyclo gave %d polynomials' % (p, k, len(g)))
        g = g[0]
    return ZX([ZZ(c) for c in g.Vecrev()])


def ball_periods(p, k, bits=BITS):
    """The k periods as complex balls: sums of arb's exponential of exact rationals."""
    C = ComplexBallField(bits)
    zeta = (2 * C.pi() * C(0, 1) / p).exp()
    powers = [zeta ** a for a in range(p)]
    g = primitive_root(p)
    f = (p - 1) // k
    return [sum(powers[pow(g, j + k * i, p)] for i in range(f)) for j in range(k)]


def ball_polynomial(periods):
    """Coefficients, lowest first, of prod (x - eta) over complex balls."""
    C = periods[0].parent()
    coefficients = [C(1)]
    for eta in periods:
        shifted = [-eta * c for c in coefficients] + [C(0)]
        for m in range(len(coefficients)):
            shifted[m + 1] += coefficients[m]
        coefficients = shifted
    return coefficients


def proven(p, k, P, periods):
    """Refuse P unless the ball product determines it coefficient by coefficient."""
    balls = ball_polynomial(periods)
    if len(balls) != P.degree() + 1:
        raise ArithmeticError('(%s, %s): the ball product has degree %d and the '
                              'candidate %d' % (p, k, len(balls) - 1, P.degree()))
    for m, ball in enumerate(balls):
        real, imag = ball.real(), ball.imag()
        if not (real.is_finite() and imag.is_finite()):
            raise ArithmeticError('(%s, %s): coefficient %d is not a finite ball, '
                                  'which would agree with anything' % (p, k, m))
        if not (real.rad() < 0.5 and imag.contains_zero() and real.contains_exact(P[m])):
            raise ArithmeticError(
                '(%s, %s): coefficient %d is %s in balls and %s exactly; neither is '
                'right until the disagreement has a cause' % (p, k, m, ball, P[m]))
    return P


# ---------------------------------------------------------------- the theorems the table states

def cubic_LM(p):
    """(L, M) with 4p = L^2 + 27 M^2, L = 1 (mod 3), M >= 0; unique for p = 1 (mod 3)."""
    found = []
    M = ZZ(0)
    while 27 * M * M <= 4 * p:
        r = 4 * p - 27 * M * M
        L = ZZ(r).isqrt()
        if L * L == r:
            for s in (L, -L):
                if s % 3 == 1:
                    found.append((s, M))
        M += 1
    if len(found) != 1:
        raise ArithmeticError('p = %s: 4p = L^2 + 27M^2 with L = 1 (mod 3) has %d '
                              'solutions' % (p, len(found)))
    return found[0]


def checked(p, k, P, periods):
    """Every identity the comments and formulas state, required on this row."""
    f = (p - 1) // k
    if not (P.is_monic() and P.degree() == k and P.is_irreducible()):
        raise ArithmeticError('(%s, %s): not monic irreducible of degree %s' % (p, k, k))
    if P[k - 1] != 1:
        raise ArithmeticError('(%s, %s): the periods do not sum to -1' % (p, k))
    shifted = (x - f) ** k
    if any((P[m] - shifted[m]) % p != 0 for m in range(k + 1)):
        raise ArithmeticError('(%s, %s): not (x - f)^k modulo p' % (p, k))
    pstar = p if p % 4 == 1 else -p
    if k == 2 and P != x ** 2 + x + (1 - pstar) / 4:
        raise ArithmeticError('(%s, 2): not x^2 + x + (1 - p*)/4' % p)
    if k == 3:
        L, M = cubic_LM(p)
        if P != x ** 3 + x ** 2 - QQ(p - 1) / 3 * x - QQ(p * (L + 3) - 1) / 27:
            raise ArithmeticError("(%s, 3): not Gauss's cubic, L = %s, M = %s" % (p, L, M))
    sign = (-1) ** (k // 2) if f % 2 == 1 else 1
    quotient, remainder = P.discriminant().quo_rem(sign * p ** (k - 1))
    if remainder != 0 or quotient <= 0 or ZZ(quotient).isqrt() ** 2 != quotient:
        raise ArithmeticError('(%s, %s): discriminant %s is not the field discriminant '
                              'times a square' % (p, k, P.discriminant()))
    if f % 2 == 1:
        if any(eta.imag().contains_zero() for eta in periods):
            raise ArithmeticError('(%s, %s): f odd, but a period ball meets the real axis' % (p, k))
    elif not all(eta.imag().contains_zero() for eta in periods):
        raise ArithmeticError('(%s, %s): f even, but a period ball misses the real axis' % (p, k))
    if f == 2:
        if P.discriminant() != p ** (k - 1):
            raise ArithmeticError('(%s, %s): f = 2 but the discriminant is not p^(k-1)' % (p, k))


# ---------------------------------------------------------------- what the comment says

#: The k = 2 rows whose roots (-1 +- sqrt(p*))/2 the table of algebraic
#: numbers of degree 2 holds, as the roots of x^2 + x + c: its coefficients
#: run to |c| <= 5, and the anchor of a root is (a2, a1, a0, n).
IN_DEGREE_TWO = {5: -1, 7: 2, 11: 3, 13: -3, 17: -4, 19: 5}


def comment(p, k):
    f = (p - 1) // k
    pieces = []
    if k == 2:
        pstar = p if p % 4 == 1 else -p
        text = r'$p^*=%d$; roots $\frac{-1\pm\sqrt{%d}}{2}$' % (pstar, pstar)
        if p in IN_DEGREE_TWO:
            c = IN_DEGREE_TWO[p]
            if c != (1 - pstar) / 4:
                raise ArithmeticError('p = %s: the degree-2 anchor is wrong' % p)
            text += (', in HREF{Algebraic_numbers_of_degree_2#1,1,%d,1}'
                     '[Algebraic numbers of degree 2]' % c)
        pieces.append(text)
    if k == 3:
        L, M = cubic_LM(p)
        pieces.append(r'$4p=L^2+27M^2$ with $L=%d$, $M=%d$' % (L, M))
    if f == 2:
        pieces.append(r'$f=2$: the roots are $2\cos(2\pi a/%d)$, $1\leq a\leq %d$' % (p, k))
    if p == 17:
        pieces.append("a period equation of Gauss's construction of the regular 17-gon")
    return '; '.join(pieces)


class GaussianPeriodPolynomials(numberdb.Generator):

    table = 'T146'
    parameters = ('p', 'k')
    type = 'Z[]'
    rigour = 'exact'

    def enumerate(self, bound=BOUND, kmax=KMAX):
        for p, k in rows(bound, kmax):
            yield {'p': int(p), 'k': int(k)}

    def value(self, params, digits):
        p, k = ZZ(params['p']), ZZ(params['k'])
        P = exact_polynomial(p, k)
        independent = pari_polynomial(p, k)
        if P != independent:
            raise ArithmeticError(
                '(%s, %s): the periods give %s and PARI polsubcyclo %s; neither is '
                'right until the disagreement has a cause' % (p, k, P, independent))
        periods = ball_periods(p, k)
        P = proven(p, k, P, periods)
        checked(p, k, P, periods)
        entry = {'number': P}
        text = comment(p, k)
        if text:
            entry['comment'] = text
        return entry


if __name__ == '__main__':
    generator = GaussianPeriodPolynomials()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='Gaussian period polynomials for every prime p < %d and every '
                    'divisor k of p - 1 with 2 <= k <= %d, k < p - 1: the exact product '
                    'over the periods, equal to PARI polsubcyclo and proven by a ball '
                    'product, with the quadratic and cubic closed forms, the congruence '
                    'modulo p and the discriminant checked on every row' % (BOUND, KMAX)))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
