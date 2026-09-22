"""Twisted Kloosterman sums modulo a prime -- numberdb.org/T376

    K(a, chi; p) = sum_{x=1}^{p-1} chi(x) exp(2 pi i (a x + xbar) / p),
    x xbar = 1 (mod p),

for every prime 5 <= p <= 13, every nontrivial Dirichlet character
chi = chi_p(n, .) modulo p in Conrey's labelling, and every a with
1 <= a <= p - 1: 264 entries. The two-parameter sum is recovered from these
by K(a, b, chi; p) = chi(b) K(ab, chi; p) when p does not divide b.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**These digits are proven.** Every value is a complex ball: each of the p - 1
terms is exp(2 pi i r) of an exact rational r in arb, where r includes both
Conrey's character exponent and the additive character's exponent. The sum
carries its error through, and the written digits are the digits the ball
supports.

**The character is built from Conrey's definition, not looked up.** For a
prime p, with g the least positive integer that generates (Z/p^k)^* for every
k, Conrey's label puts chi_p(g^r, g^s) = e(rs / (p - 1)). Sage numbers its
characters the same way (`conrey_number()`), and the generator compares the
two constructions on every value of every character of every prime in range.

**Two computations that share no code must agree on every entry.** The ball
sum from the hand-built character must overlap an enclosure of Sage's exact
`kloosterman_sum(a, 1)` for the character Sage numbers (p, n). The quadratic
character entries must also overlap Salié's closed form, and the entries with
a nonsquare argument are written as the exact integer 0.

**The formulas in the table are checked over the whole range.** Before any
entry of a prime is returned, the generator checks the two-parameter reduction,
the two Gauss-sum boundary formulas, conjugation, Salié's formula for the
quadratic character, and Weil's bound. The comment on each entry gives the
order of chi, the degree over Q, and the minimal polynomial when that degree
is at most 12.
"""

import os
import sys
from fractions import Fraction

import numberdb.sage as numberdb
from sage.arith.misc import factor, legendre_symbol
from sage.modular.dirichlet import DirichletGroup
from sage.rings.complex_arb import ComplexBallField
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


#: Bits of working precision beyond what the written digits need. Measured
#: over the whole table at 100 digits: a sum of at most 18 exponentials loses
#: almost nothing, and the widest ball supports more than 117 digits at
#: 397 bits, so the package's usual 64-bit guard is enough.
WORKING_GUARD = 64

#: Every nontrivial character and every nonzero argument up to here: 264
#: entries. A private run to p <= 19 produced 810 entries and a 374 KB entries
#: block, over the soft limit; p <= 13 keeps the same complete rectangle while
#: leaving room for extension.
BOUND = 13

#: The minimal polynomial goes in the comment when its degree is at most this.
MINPOLY_DEGREE = 12


# ---------------------------------------------------------------- Conrey's characters, by hand

def conrey_root(p):
    """The least positive integer generating (Z/p^k)^* for every k >= 1."""
    phi1, phi2 = p - 1, p * (p - 1)
    g = 2
    while True:
        if all(pow(g, phi1 // r, p) != 1 for r, _ in factor(phi1)) and \
                all(pow(g, phi2 // r, p * p) != 1 for r, _ in factor(phi2)):
            return g
        g += 1


_LOGS = {}


def discrete_logs(p):
    """{u: r} with u = g^r modulo p, r modulo p - 1, g Conrey's root."""
    p = ZZ(p)
    if p not in _LOGS:
        g = conrey_root(p)
        _LOGS[p] = {pow(g, r, p): r for r in range(p - 1)}
    return _LOGS[p]


def conrey_exponent(p, n, m):
    """The rational r in [0, 1) with chi_p(n, m) = exp(2 pi i r), or None when p | m."""
    if m % p == 0:
        return None
    logs = discrete_logs(p)
    r = QQ(logs[n % p] * logs[m % p]) / (p - 1)
    return r - r.floor()


def twisted_ball(p, n, a, bits):
    """K(a, chi_p(n, .); p) as a ball from Conrey's definition of chi."""
    C = ComplexBallField(bits)
    two_pi_i = 2 * C.pi() * C(0, 1)
    total = C(0)
    for x in range(1, p):
        character = conrey_exponent(p, n, x)
        additive = QQ((a * x + pow(x, -1, p)) % p) / p
        r = character + additive
        total += (two_pi_i * C(r - r.floor())).exp()
    return total


# ---------------------------------------------------------------- Sage's characters and exact sums, as the check

_GROUPS = {}


def sage_characters(p):
    """Sage's characters modulo p keyed by Conrey index, checked against the hand-built ones."""
    p = ZZ(p)
    if p not in _GROUPS:
        group = DirichletGroup(p)
        chars = {ZZ(chi.conrey_number()): chi for chi in group}
        zeta = group.base_ring().gen()
        order = ZZ(zeta.multiplicative_order())
        for n, chi in chars.items():
            for a in range(1, p):
                want = zeta ** ZZ(conrey_exponent(p, n, a) * order)
                if chi(a) != want:
                    raise ArithmeticError('p = %s, n = %s: the hand-built character and '
                                          "Sage's disagree at %s" % (p, n, a))
        _GROUPS[p] = chars
    return _GROUPS[p]


def enclose(x, bits):
    """A cyclotomic number as a ball with a genuine radius."""
    C = ComplexBallField(bits)
    K = x.parent()
    if K is QQ or K is ZZ:
        return C(x)
    m = K.gen().multiplicative_order()
    zeta = (2 * C.pi() * C(0, 1) / m).exp()
    return x.polynomial()(zeta)


def finite(ball):
    return ball.real().is_finite() and ball.imag().is_finite()


# ---------------------------------------------------------------- independent identities

def salie_ball(p, a, bits):
    """Salié's closed form for the quadratic character, b = 1."""
    C = ComplexBallField(bits)
    if legendre_symbol(a, p) == -1:
        return C(0)
    roots = [y for y in range(1, p) if (y * y - a) % p == 0]
    if len(roots) != 2:
        raise ArithmeticError('p = %s, a = %s: expected two square roots' % (p, a))
    epsilon = C(1) if p % 4 == 1 else C(0, 1)
    two_pi_i = 2 * C.pi() * C(0, 1)
    total = C(0)
    for y in roots:
        total += (two_pi_i * C(QQ(2 * y) / p)).exp()
    return epsilon * C(p).sqrt() * total


def check_two_parameter_formulas(p, values):
    """The formulas for K(a, b, chi; p), including the Gauss-sum boundary cases."""
    chars = sage_characters(p)
    for n, chi in chars.items():
        if n == 1:
            continue
        inverse_n = ZZ(pow(int(n), -1, int(p)))
        chibar = chars[inverse_n]
        tau = chi.gauss_sum()
        tau_bar = chibar.gauss_sum()
        for a in range(1, p):
            if chi.kloosterman_sum(a, 0) != chi(a).conjugate() * tau:
                raise ArithmeticError('(%s, %s, %s): K(a, 0, chi) is not chibar(a) tau(chi)'
                                      % (p, n, a))
            if chi.kloosterman_sum(0, a) != chi(a) * tau_bar:
                raise ArithmeticError('(%s, %s, %s): K(0, a, chi) is not chi(a) tau(chibar)'
                                      % (p, n, a))
            for b in range(1, p):
                lhs = chi.kloosterman_sum(a, b)
                rhs = chi(b) * values[(n, (a * b) % p)]['exact']
                if lhs != rhs:
                    raise ArithmeticError('(%s, %s, %s, %s): two-parameter reduction failed'
                                          % (p, n, a, b))


def check_conjugates(p, values):
    """Complex conjugation sends chi to chibar, with the factor chibar(-1)."""
    chars = sage_characters(p)
    for n, chi in chars.items():
        if n == 1:
            continue
        inverse_n = ZZ(pow(int(n), -1, int(p)))
        factor = chars[inverse_n](-1)
        for a in range(1, p):
            if values[(n, a)]['exact'].conjugate() != factor * values[(inverse_n, a)]['exact']:
                raise ArithmeticError('(%s, %s, %s): conjugation identity failed' % (p, n, a))


# ---------------------------------------------------------------- comments and written values

def latex_polynomial(poly):
    """An integer polynomial as a reader writes it."""
    coefficients = poly.list()
    pieces = []
    for k in range(len(coefficients) - 1, -1, -1):
        c = QQ(coefficients[k])
        if c == 0:
            continue
        if c.denominator() != 1:
            raise ArithmeticError('minimal polynomial has nonintegral coefficient %s' % c)
        c = ZZ(c)
        sign = '-' if c < 0 else '+'
        c = abs(c)
        if k == 0:
            body = str(c)
        else:
            power = 'x' if k == 1 else ('x^%d' % k if k < 10 else 'x^{%d}' % k)
            body = power if c == 1 else '%d%s' % (c, power)
        pieces.append((sign, body))
    if not pieces:
        return '0'
    text = ('-' if pieces[0][0] == '-' else '') + pieces[0][1]
    for sign, body in pieces[1:]:
        text += ' %s %s' % (sign, body)
    return text


def as_interval(ball):
    """A Sage real ball as this package's interval, with exact endpoints."""
    interval = ball.union(ball)
    lower, upper = interval.lower(), interval.upper()

    def exactly(endpoint):
        rational = endpoint.exact_rational()
        return Fraction(int(rational.numerator()),
                        int(rational.denominator()))

    return numberdb.RealInterval(exactly(lower), exactly(upper))


def written(exact, ball):
    """Write exact zero parts exactly, by theorem from the exact value."""
    if exact == 0:
        if not ball.real().contains_zero() or not ball.imag().contains_zero():
            raise ArithmeticError('exact zero is not contained in %s' % ball)
        return ZZ(0)
    if exact.conjugate() == exact:
        if not ball.imag().contains_zero():
            raise ArithmeticError('real exact value has imaginary ball %s' % ball.imag())
        return numberdb.ComplexInterval(as_interval(ball.real()), 0)
    if exact.conjugate() == -exact:
        if not ball.real().contains_zero():
            raise ArithmeticError('purely imaginary exact value has real ball %s' % ball.real())
        return numberdb.ComplexInterval(0, as_interval(ball.imag()))
    return ball


def comment(p, n, a, chi, degree, minpoly, exact):
    order = ZZ(chi.order())
    if exact == 0:
        return (r'$\chi$ of order $%d$, $[\mathbb{Q}(K(%d,\chi;%d)):\mathbb{Q}]=1$, exact value $0$'
                % (order, a, p))
    text = (r'$\chi$ of order $%d$, $[\mathbb{Q}(K(%d,\chi;%d)):\mathbb{Q}]=%d$'
            % (order, a, p, degree))
    if minpoly is not None:
        text += r', $K(%d,\chi;%d)$ a root of $%s$' % (a, p, latex_polynomial(minpoly))
    return text


# ---------------------------------------------------------------- all data at a prime

_PRIMES = {}


def prime_data(p, bits):
    p = ZZ(p)
    if (p, bits) in _PRIMES:
        return _PRIMES[(p, bits)]
    C = ComplexBallField(bits)
    chars = sage_characters(p)
    values = {}
    widest = C(0)
    for n in sorted(chars):
        if n == 1:
            continue
        chi = chars[n]
        for a in range(1, p):
            ball = twisted_ball(p, n, a, bits)
            exact = chi.kloosterman_sum(a, 1)
            check = enclose(exact, bits)
            if not (finite(ball) and finite(check) and ball.overlaps(check)):
                raise ArithmeticError(
                    '(%s, %s, %s): the hand-built sum gives %s and Sage exact gives %s'
                    % (p, n, a, ball, check))
            norm = (ball * ball.conjugate()).real()
            if not norm.upper() <= 4 * p:
                raise ArithmeticError('(%s, %s, %s): |K|^2 = %s is above 4p' % (p, n, a, norm))
            if n == p - 1:
                salie = salie_ball(p, a, bits)
                if not ball.overlaps(salie):
                    raise ArithmeticError('(%s, %s, %s): Salié formula gives %s, not %s'
                                          % (p, n, a, salie, ball))
                if legendre_symbol(a, p) == -1 and exact != 0:
                    raise ArithmeticError('(%s, %s, %s): nonsquare Salié sum is not zero'
                                          % (p, n, a))
            minpoly = exact.minpoly()
            degree = ZZ(minpoly.degree())
            small_minpoly = minpoly if degree <= MINPOLY_DEGREE and exact != 0 else None
            if small_minpoly is not None and small_minpoly(exact) != 0:
                raise ArithmeticError('(%s, %s, %s): minpoly does not vanish at exact value'
                                      % (p, n, a))
            values[(n, a)] = {'ball': ball, 'exact': exact, 'degree': degree,
                              'minpoly': small_minpoly}
            if ball.real().rad() + ball.imag().rad() > widest.real().rad() + widest.imag().rad():
                widest = ball
    check_conjugates(p, values)
    check_two_parameter_formulas(p, values)
    _PRIMES[(p, bits)] = {'values': values, 'widest': widest}
    return _PRIMES[(p, bits)]


class TwistedKloostermanSums(numberdb.Generator):

    table = 'T376'
    parameters = ('p', 'n', 'a')
    type = 'C'
    digits = 100
    rigour = 'proven'

    def enumerate(self, bound=BOUND):
        for p in range(5, bound + 1):
            if not ZZ(p).is_prime():
                continue
            sage_characters(p)
            for n in range(2, p):
                for a in range(1, p):
                    yield {'p': int(p), 'n': int(n), 'a': int(a)}

    def value(self, params, digits):
        p, n, a = ZZ(params['p']), ZZ(params['n']), ZZ(params['a'])
        bits = numberdb.bits(digits, losing=WORKING_GUARD)
        item = prime_data(p, bits)['values'][(n, a)]
        chi = sage_characters(p)[n]
        return {
            'number': written(item['exact'], item['ball']),
            'comment': comment(p, n, a, chi, item['degree'], item['minpoly'], item['exact']),
        }


if __name__ == '__main__':
    generator = TwistedKloostermanSums()
    if '--publish' in sys.argv or os.environ.get('NUMBERDB_PUBLISH') == '1':
        print(generator.publish(
            message='Twisted Kloosterman sums K(a, chi; p) for nontrivial characters '
                    'modulo primes up to 13, summed in ball arithmetic from Conrey '
                    "characters and checked against Sage's exact sums, Salié's formula "
                    'and the two-parameter identities'))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
