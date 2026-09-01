"""Hilbert class polynomials H_Delta(x) -- numberdb.org/T129

    H_Delta(x) = prod_{[a]} (x - j(a)),

the product over the h(Delta) classes of proper ideals of the imaginary
quadratic order O_Delta of discriminant Delta < 0, Delta = 0, 1 mod 4 -- or,
in the form the table was checked in, over the reduced primitive positive
definite binary quadratic forms (a, b, c) of discriminant Delta, with j
evaluated at tau = (-b + sqrt Delta) / 2a. Monic in Z[x] of degree h(Delta),
irreducible over Q. H_{-15} = x^2 + 191025 x - 121287375; H_{-163} = x +
640320^3.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**Every discriminant, not only the fundamental ones.** Delta = f^2 Delta_0
with Delta_0 fundamental and f the conductor; for f > 1 the roots generate the
ring class field of O_Delta rather than the Hilbert class field of the field,
and the CM method uses such orders freely. The table of rational singular
moduli (T83) lists -12, -16, -27, -28 beside the fundamental discriminants,
and OEIS A305474 enumerates the family the same way, so this table does too.
Each entry's comment names the order.

**Every value is proven before it is returned**, without trusting either
library it was compared against. Sage's `hilbert_class_polynomial` (FLINT,
complex interval arithmetic with rounding to the nearest integer) is taken as
the candidate; it must agree with PARI's `polclass`, which is a different
algorithm (CRT over small primes); its degree must equal the number of
reduced primitive forms counted here by brute force; and the product
prod (x - j(tau)) over those forms, computed in `ComplexBallField`, must
enclose every integer coefficient in a ball of radius below 1/2. An integer
in a ball of radius < 1/2 is determined, so the last check alone establishes
the polynomial given the enumeration of the forms. The controls that must
fail do: adding the imprimitive form (2, 2, 2) at Delta = -12 changes the
degree and the constant, and a target shifted by one is excluded.

When this was written the values were also checked, outside the generator,
against all 250 rows of the OEIS b-file of A305474 (|Delta| <= 500), the
thirteen rational singular moduli of T83, the classical factorisation of the
diagonal Phi_l(x, x) of the modular polynomials in T96 for l = 2, 3, 5, 7, 11,
Weber's theorem that H_Delta(0) is a cube when 3 does not divide Delta, and
the splitting criterion "H_Delta has a root mod p and (Delta/p) = 1 iff
4p = X^2 - Delta Y^2" on 11,420 pairs (Delta, p). No exception anywhere.

**The range is decided by the length of an entry.** Coefficients grow like
exp(pi sqrt|Delta| sum 1/a) and the degree like sqrt|Delta|, so the written
polynomial grows fast: the longest entry is 820 characters at |Delta| <= 200,
1106 at 300 (Delta = -239, degree 15), 1855 at 400 and 3139 at 500. The table
stops at |Delta| <= 300, where the longest entry is the length of F_100 in the
Fibonacci polynomials table: 150 entries, 94 of them fundamental, 46 KB.
"""

import sys

import numberdb.sage as numberdb
from sage.arith.misc import gcd
from sage.libs.pari import pari
from sage.rings.complex_arb import ComplexBallField
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.schemes.elliptic_curves.cm import hilbert_class_polynomial

#: Every discriminant Delta < 0, Delta = 0, 1 mod 4, with |Delta| up to here.
BOUND = 300

#: Bits for the ball product. The coefficients have up to 80 digits (270 bits)
#: in range, and at 1500 bits the worst radius over the table is below
#: 10^-300; 400 bits already gives 10^-105 at Delta = -23. The requirement is
#: only that the radius be below 1/2, which is what makes an integer
#: coefficient determined by its ball.
BITS = 1500

ZX = PolynomialRing(ZZ, 'x')


def discriminants(bound):
    """Delta = -3, -4, -7, -8, -11, -12, ... down to -bound, by |Delta|."""
    return [ZZ(D) for D in range(-3, -bound - 1, -1) if D % 4 in (0, 1)]


def reduced_primitive_forms(D):
    """The reduced primitive positive definite forms of discriminant D.

    (a, b, c) with b^2 - 4ac = D, |b| <= a <= c, gcd(a, b, c) = 1, and b >= 0
    when |b| = a or a = c. Brute force over a <= sqrt(|D|/3), with no number
    theory library, so that the class number the degree is compared with owes
    nothing to the code that computed the polynomial.
    """
    D = ZZ(D)
    forms = []
    a = ZZ(1)
    while 3 * a * a <= -D:
        for b in range(-a, a + 1):
            if (b * b - D) % (4 * a):
                continue
            c = (b * b - D) // (4 * a)
            if c < a or gcd(gcd(a, b), c) != 1:
                continue
            if (abs(b) == a or a == c) and b < 0:
                continue
            forms.append((a, ZZ(b), ZZ(c)))
        a += 1
    return forms


def ball_product(D, forms, bits):
    """prod (x - j(tau)) over the forms, tau = (-b + sqrt D)/2a, in balls."""
    C = ComplexBallField(bits)
    P = PolynomialRing(C, 'x')
    t = P.gen()
    sqrt_D = C(D).sqrt()                          # i sqrt|D|
    pol = P(1)
    for a, b, c in forms:
        tau = (C(-b) + sqrt_D) / C(2 * a)
        pol *= (t - tau.modular_j())
    return pol


def proven(D, H, forms):
    """Refuse H unless the ball product determines it coefficient by coefficient."""
    pol = ball_product(D, forms, BITS)
    coefficients = pol.list()
    if len(coefficients) != H.degree() + 1:
        raise ArithmeticError('Delta = %s: the ball product has degree %d and '
                              'the candidate %d' % (D, len(coefficients) - 1, H.degree()))
    for k, ball in enumerate(coefficients):
        #A complex ball has no is_finite(); its two real balls do. A nan or
        #infinite ball contains every integer, so it must be refused first.
        real, imag = ball.real(), ball.imag()
        if not (real.is_finite() and imag.is_finite()):
            raise ArithmeticError('Delta = %s: coefficient %d is not a finite '
                                  'ball, which would agree with anything' % (D, k))
        if not (real.rad() < 0.5 and imag.contains_zero()
                and real.contains_exact(H[k])):
            raise ArithmeticError(
                'Delta = %s: coefficient %d is %s in balls and %s from FLINT; '
                'neither is right until the disagreement has a cause'
                % (D, k, ball, H[k]))
    return H


def fundamental_and_conductor(D):
    """(Delta_0, f) with Delta = f^2 Delta_0 and Delta_0 fundamental."""
    D = ZZ(D)
    f = ZZ(1)
    g = ZZ(2)
    while g * g <= -D:
        if D % (g * g) == 0 and (D // (g * g)) % 4 in (0, 1):
            f = g
        g += 1
    return D // (f * f), f


def comment(D, h):
    """The order, since Delta = -12 is not Q(sqrt -12), and its class number."""
    D0, f = fundamental_and_conductor(D)
    d = D0 if D0 % 4 == 1 else D0 // 4
    field = r'\mathbb{Q}(i)' if d == -1 else r'\mathbb{Q}(\sqrt{%d})' % d
    if f == 1:
        text = r'$h(\Delta)=%d$; maximal order of $%s$' % (h, field)
    else:
        text = r'$h(\Delta)=%d$; order of conductor $%d$ in $%s$' % (h, f, field)
    if D == -163:
        text += (r'; $640320^3=-H_\Delta(0)$ is the integer that '
                 r"HREF{Ramanujan_constant}[Ramanujan's constant "
                 r'$e^{\pi\sqrt{163}}$] falls $744$ short of')
    return text


class HilbertClassPolynomials(numberdb.Generator):

    table = 'T129'
    parameters = ('Delta',)
    type = 'Z[]'
    rigour = 'exact'

    def enumerate(self, bound=BOUND):
        for D in discriminants(bound):
            yield {'Delta': int(D)}

    def value(self, params, digits):
        D = ZZ(params['Delta'])
        H = ZX(hilbert_class_polynomial(D))
        independent = ZX(pari.polclass(D))
        if H != independent:
            raise ArithmeticError(
                'Delta = %s: FLINT gives %s and PARI polclass %s; neither is '
                'right until the disagreement has a cause' % (D, H, independent))
        forms = reduced_primitive_forms(D)
        if H.degree() != len(forms):
            raise ArithmeticError('Delta = %s: degree %d, but %d reduced primitive '
                                  'forms' % (D, H.degree(), len(forms)))
        if not H.is_monic():
            raise ArithmeticError('Delta = %s: not monic' % D)
        H = proven(D, H, forms)
        return {'number': H, 'comment': comment(D, H.degree())}


if __name__ == '__main__':
    generator = HilbertClassPolynomials()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='Hilbert class polynomials for every discriminant with '
                    '|Delta| <= %d, each checked against PARI polclass and '
                    'proven by a ball product over the reduced forms' % BOUND))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
