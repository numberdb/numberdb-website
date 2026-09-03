"""Kloosterman sums modulo a prime -- numberdb.org/T144

    K(a; p) = sum_{x=1}^{p-1} exp(2 pi i (a x + xbar) / p),    x xbar = 1 (mod p),

for every prime 5 <= p <= 71 and every a with 1 <= a <= p - 1: 616 entries.
K(a; p) is the classical two-parameter sum K(a, b; p) at b = 1, and
K(a, b; p) = K(ab; p) for p not dividing b, so these are all of them.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**These digits are proven.** Every value is a real ball: each of the p - 1
terms is exp(2 pi i r) of an exact rational r in arb, the sum carries its
error through, and the imaginary part, which the theorem says is zero, must
contain zero before the real part is taken. A hundred digits are written and
the widest ball, at (47, 4), supports 115.

**Two computations that share no code must agree on every entry.** The value
returned is the arb sum from the definition. It must overlap an enclosure of
Sage's exact `trivial_character(p).kloosterman_sum(a, 1)`, an element of
Q(zeta_2p) computed by Sage's own routine; that exact value must equal its
complex conjugate; and the ball must satisfy Weil's bound K^2 < 4p.

**The theorems the comments rely on are checks, run for each prime before
any of its entries is returned.** The Galois conjugates of K(a; p) are the
K(a c^2; p), so the p - 1 values fall into two classes, the squares and the
non-squares modulo p, and the product of x - K(a; p) over a class has integer
coefficients. The generator computes all p - 1 balls, requires them to be
pairwise disjoint (which proves the values distinct, so each has degree
exactly (p - 1)/2), rounds the two products to integer polynomials that must
be monic of degree (p - 1)/2, must vanish exactly at Sage's exact value of
every member of their class and at no member of the other, and must be
congruent to (x + 1)^((p-1)/2) modulo p, which is K(a; p) = -1 modulo
1 - zeta_p. The four moment identities the table states -- the sums of
K(a; p)^k over a for k = 1, 2, 3, 4 -- are required exactly, in Q(zeta_2p).
Distinct roots forming one Galois orbit make each polynomial irreducible, so
it is the minimal polynomial of every entry in its class.

**The comment on each entry** gives the Legendre symbol (a/p), which says
which class the entry is in, the degree (p - 1)/2 of K(a; p) over Q, and,
for p <= 23, where that degree is at most 11, the minimal polynomial. The
four entries at p = 5 are quadratic irrationals held by the table of
algebraic numbers of degree 2, and are linked to it.

**Modulo 2 and 3 the sums are the integers 1, -1, 2**, which the table's
comments give; the entries start at p = 5.
"""

import sys

import numberdb.sage as numberdb
from sage.arith.misc import binomial, legendre_symbol
from sage.modular.dirichlet import trivial_character
from sage.rings.complex_arb import ComplexBallField
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField

#: Bits of working precision beyond what the written digits need. Measured
#: over the whole table at 100 digits: a sum of at most 70 exponentials of
#: exact rationals loses almost nothing, and the widest ball, at p = 47,
#: a = 4, has relative radius 7.5e-116 at 397 bits, so the guard is the
#: package's usual 64 rather than anything the family required.
WORKING_GUARD = 64

#: Every prime up to here, from 5: 18 primes, 616 entries, about 105 KB as
#: written with the comments. The count grows like p^2 / (2 log p): p <= 97
#: would be 1032 entries, past the recommended thousand.
BOUND = 71

#: The minimal polynomial goes in the comment when its degree (p - 1)/2 is
#: at most this: p <= 23.
MINPOLY_DEGREE = 12


# ---------------------------------------------------------------- the sum, from the definition

def kloosterman_ball(p, a, bits):
    """K(a; p) as a complex ball: sum over x of e((a x + xbar)/p), each term
    arb's exponential of a ball containing the exact rational exponent."""
    C = ComplexBallField(bits)
    two_pi_i = 2 * C.pi() * C(0, 1)
    total = C(0)
    for x in range(1, p):
        r = QQ((a * x + pow(x, -1, p)) % p) / p
        total += (two_pi_i * C(r)).exp()
    return total


# ---------------------------------------------------------------- Sage's exact sum, as the check

def enclose(x, bits):
    """A cyclotomic number as a ball with a genuine radius.

    `CBF(x.complex_embedding())` would be a point: the embedding rounds first
    and the ball around it has radius zero. Evaluating the polynomial of x
    at a ball enclosure of the generator of its field encloses x.
    """
    C = ComplexBallField(bits)
    K = x.parent()
    if K is QQ or K is ZZ:
        return C(x)
    m = K.gen().multiplicative_order()
    zeta = (2 * C.pi() * C(0, 1) / m).exp()
    return x.polynomial()(zeta)


def finite(ball):
    return ball.real().is_finite() and ball.imag().is_finite()


# ---------------------------------------------------------------- the two Galois orbits at a prime

def polynomial_from_roots(roots):
    """Coefficients, lowest first, of prod (x - r) over real balls."""
    R = roots[0].parent()
    coefficients = [R(1)]
    for root in roots:
        shifted = [-root * c for c in coefficients] + [R(0)]
        for k in range(len(coefficients)):
            shifted[k + 1] += coefficients[k]
        coefficients = shifted
    return coefficients


def integer_polynomial(coefficients):
    """The coefficient balls rounded to integers; refuses a ball that does
    not pin down a single integer."""
    R = coefficients[0].parent()
    out = []
    for c in coefficients:
        nearest = ZZ(c.mid().round())
        if not (c.contains_integer() and c.rad() < 0.25 and c.overlaps(R(nearest))):
            raise ArithmeticError('a coefficient ball %s holds no single integer' % c)
        out.append(nearest)
    return out


def evaluate(coefficients, x):
    return sum(c * x ** k for k, c in enumerate(coefficients))


_PRIMES = {}


def prime_data(p, bits):
    """Everything at one prime: the p - 1 real balls, and the two minimal
    polynomials, after every check this file describes."""
    p = ZZ(p)
    if (p, bits) in _PRIMES:
        return _PRIMES[(p, bits)]
    C = ComplexBallField(bits)
    chi0 = trivial_character(p)
    balls, exact = {}, {}
    for a in range(1, p):
        ball = kloosterman_ball(p, a, bits)
        value = chi0.kloosterman_sum(a, 1)
        check = enclose(value, bits)
        if not (finite(ball) and finite(check) and ball.overlaps(check)):
            raise ArithmeticError(
                '(%s, %s): the sum from the definition gives %s and Sage\'s exact '
                'Kloosterman sum %s; neither is right until the disagreement has '
                'a cause' % (p, a, ball, check))
        if not ball.imag().contains_zero():
            raise ArithmeticError('(%s, %s): imaginary part %s does not contain 0' % (p, a, ball.imag()))
        if value.conjugate() != value:
            raise ArithmeticError('(%s, %s): Sage\'s exact value is not real' % (p, a))
        real = ball.real()
        if not (real * real).upper() < 4 * p:
            raise ArithmeticError('(%s, %s): K^2 = %s is not below 4p (Weil)' % (p, a, real * real))
        balls[a], exact[a] = real, value
    # distinct: sorted real balls whose neighbours are disjoint are pairwise disjoint
    ordered = sorted(balls.values(), key=lambda b: b.mid())
    for left, right in zip(ordered, ordered[1:]):
        if left.overlaps(right):
            raise ArithmeticError('p = %s: two values overlap at %s bits, %s and %s'
                                  % (p, bits, left, right))
    # the moments, exactly in Q(zeta_2p)
    moments = [sum(v ** k for v in exact.values()) for k in (1, 2, 3, 4)]
    expected = [1, p * p - p - 1, legendre_symbol(-3, p) * p * p + 2 * p + 1,
                2 * p ** 3 - 3 * p ** 2 - 3 * p - 1]
    for k, (got, want) in enumerate(zip(moments, expected), 1):
        if got != want:
            raise ArithmeticError('p = %s: sum of K^%d is %s, not %s' % (p, k, got, want))
    # the two orbits
    squares = sorted({(c * c) % p for c in range(1, p)})
    classes = {1: squares, -1: [a for a in range(1, p) if a not in squares]}
    degree = (p - 1) // 2
    polynomials = {}
    for symbol, members in classes.items():
        coefficients = integer_polynomial(polynomial_from_roots([balls[a] for a in members]))
        if len(coefficients) != degree + 1 or coefficients[-1] != 1:
            raise ArithmeticError('p = %s: orbit polynomial is not monic of degree %s' % (p, degree))
        if any(evaluate(coefficients, exact[a]) != 0 for a in members):
            raise ArithmeticError('p = %s: orbit polynomial does not vanish exactly on its class' % p)
        if any(evaluate(coefficients, exact[a]) == 0 for a in classes[-symbol]):
            raise ArithmeticError('p = %s: orbit polynomial vanishes on the other class' % p)
        if any((coefficients[k] - binomial(degree, k)) % p != 0 for k in range(degree + 1)):
            raise ArithmeticError('p = %s: orbit polynomial is not (x+1)^%s modulo p' % (p, degree))
        polynomials[symbol] = coefficients
    _PRIMES[(p, bits)] = {'values': balls, 'polynomials': polynomials, 'degree': degree}
    return _PRIMES[(p, bits)]


# ---------------------------------------------------------------- what the comment says

def latex_polynomial(coefficients):
    """An integer polynomial, lowest coefficient first, as a reader writes it: x^3 + 3x^2 - 4x - 13."""
    pieces = []
    for k in range(len(coefficients) - 1, -1, -1):
        c = ZZ(coefficients[k])
        if c == 0:
            continue
        sign = '-' if c < 0 else '+'
        c = abs(c)
        if k == 0:
            body = str(c)
        else:
            power = 'x' if k == 1 else ('x^%d' % k if k < 10 else 'x^{%d}' % k)
            body = power if c == 1 else '%d%s' % (c, power)
        pieces.append((sign, body))
    text = ('-' if pieces[0][0] == '-' else '') + pieces[0][1]
    for sign, body in pieces[1:]:
        text += ' %s %s' % (sign, body)
    return text


def comment(p, a, data):
    symbol = legendre_symbol(a, p)
    if data['degree'] <= MINPOLY_DEGREE:
        return (r'$\left(\frac{%d}{%d}\right)=%d$, $[\mathbb{Q}(K(%d;%d)):\mathbb{Q}]=%d$, a root of $%s$'
                % (a, p, symbol, a, p, data['degree'], latex_polynomial(data['polynomials'][symbol])))
    return (r'$\left(\frac{%d}{%d}\right)=%d$, degree $%d$ over $\mathbb{Q}$'
            % (a, p, symbol, data['degree']))


#: The four entries at p = 5, which the table of algebraic numbers of degree 2
#: holds under the anchors (a2, a1, a0, n) of x^2 - 3x + 1 and x^2 + 2x - 4,
#: with the closed form each ball must contain.
IN_DEGREE_TWO = {
    (5, 1): ('1,-3,1,1', r'\frac{3-\sqrt{5}}{2}', lambda s5: (3 - s5) / 2),
    (5, 4): ('1,-3,1,2', r'\frac{3+\sqrt{5}}{2}', lambda s5: (3 + s5) / 2),
    (5, 2): ('1,2,-4,1', r'-1-\sqrt{5}', lambda s5: -1 - s5),
    (5, 3): ('1,2,-4,2', r'-1+\sqrt{5}', lambda s5: -1 + s5),
}


class KloostermanSums(numberdb.Generator):

    table = 'T144'
    parameters = ('p', 'a')
    type = 'R'
    digits = 100
    rigour = 'proven'

    def enumerate(self, bound=BOUND):
        for p in range(5, bound + 1):
            if ZZ(p).is_prime():
                for a in range(1, p):
                    yield {'p': int(p), 'a': int(a)}

    def value(self, params, digits):
        p, a = ZZ(params['p']), ZZ(params['a'])
        bits = numberdb.bits(digits, losing=WORKING_GUARD)
        data = prime_data(p, bits)
        ball = data['values'][a]
        entry = {'number': ball, 'comment': comment(p, a, data)}
        if (p, a) in IN_DEGREE_TWO:
            anchor, caption, closed = IN_DEGREE_TWO[(p, a)]
            if not ball.overlaps(closed(RealBallField(bits)(5).sqrt())):
                raise ArithmeticError('(%s, %s): the ball does not contain %s' % (p, a, caption))
            entry['equals'] = 'HREF{Algebraic_numbers_of_degree_2#%s}[$%s$]' % (anchor, caption)
        return entry


if __name__ == '__main__':
    generator = KloostermanSums()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='Kloosterman sums K(a; p) for every prime 5 <= p <= 71 and every '
                    'a modulo p, summed in ball arithmetic from the definition and '
                    "checked against Sage's exact Kloosterman sum, the two Galois "
                    'orbits and four moment identities at every prime'))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
