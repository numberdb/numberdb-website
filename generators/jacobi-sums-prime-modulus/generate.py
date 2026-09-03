"""Jacobi sums of pairs of Dirichlet characters modulo a prime -- numberdb.org/T143

    J(chi, psi) = sum_{a=0}^{p-1} chi(a) psi(1 - a),

for a prime p and the characters chi = chi_p(m, .), psi = chi_p(n, .) modulo p
in Conrey's labelling, for every pair with chi, psi and chi psi nontrivial,
listed once per unordered pair (m <= n), for every prime p <= 19.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**These digits are proven.** Every value is a complex ball: each of the p - 2
terms is exp(2 pi i r) of an exact rational r in arb, and the sum carries its
error through. A hundred digits are written and the widest ball supports 117.

**The character is built from Conrey's definition, not looked up.** For a
prime p, with g the least positive integer that generates (Z/p^k)^* for every
k -- for p < 40487 the least primitive root modulo p -- Conrey's label puts
chi_p(g^a, g^b) = e(ab / (p - 1)), which is what the LMFDB knowl defines and
what the sum here uses, through a table of discrete logarithms. Sage numbers
its characters the same way (`conrey_number()`), and the generator compares
the two constructions on every value of every character of every prime in
range before it computes anything, so that a disagreement about what
chi_p(m, .) *is* fails here rather than being published under the wrong label.

**Two computations that share no code must agree on every entry.** The ball
sum from the hand-built characters must overlap an enclosure of Sage's exact
`jacobi_sum()` of the characters Sage numbers (p, m) and (p, n); that exact
value must satisfy J times its conjugate equals p, must lie in Z[zeta_d] for
d the least common multiple of the orders of chi and psi, must equal
tau(chi) tau(psi) / tau(chi psi) in Sage's exact Gauss sums, and must equal
the exact sum with chi and psi exchanged. Every value is checked, before it is
returned, to be neither real nor purely imaginary: J J-bar = p with p prime
makes J irrational, and a purely imaginary J would put sqrt(-p) in
Q(zeta_{p-1}), which is unramified at p.

**The comment on each entry** gives the orders of chi and psi and the exact
value as an element of Z[zeta_d], written with i for zeta_4 and with the
constant term first, a + b zeta_3 and a + b i, which is how the cubic and
quartic cases are written in Ireland-Rosen. For a cubic chi the entry
J(chi, chi) = a + b zeta_3 is required to satisfy a = -1, b = 0 (mod 3), and
for a quartic chi the entry -chi(-1) J(chi, chi) = a + b i is required to be
1 modulo 2 + 2i (b even, a = 1 - b (mod 4)); for the quadratic character chi
and every other nontrivial psi, J(chi, psi) = psi(4) J(psi, psi) is required
exactly. These are the theorems the table's formulas state, and a failure
stops the generator before a table exists.

**What the trivial character is worth at 0 does not reach the entries.** The
pairs listed have chi and psi nontrivial, so chi(0) = psi(0) = 0 and the
terms a = 0 and a = 1 vanish; the sum runs over 2 <= a <= p - 1. The point
count formula the table's Formulas section gives needs the trivial character
to take the value 1 at 0 (Ireland-Rosen's convention), and the table says so
there, because with Sage's convention (value 0 at 0) J(1, chi) is -1 and not
0 and the formula fails by one per trivial factor.
"""

import sys

import numberdb.sage as numberdb
from sage.arith.functions import lcm
from sage.arith.misc import factor
from sage.modular.dirichlet import DirichletGroup
from sage.rings.complex_arb import ComplexBallField
from sage.rings.integer_ring import ZZ
from sage.rings.number_field.number_field import CyclotomicField
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField

#: Bits of working precision beyond what the written digits need. Measured
#: over the whole table at 100 digits: a sum of at most 17 exponentials loses
#: almost nothing, and the widest ball (at p = 19, m = 4, n = 11) has
#: relative radius 1.7e-118 at 397 bits, so the guard is the package's usual 64.
WORKING_GUARD = 64

#: Every admissible pair for the primes up to here: 372 entries, 144 of them
#: at p = 19, 139 KB as written with the exact values in the comments. The
#: count per prime is (p - 1)(p - 3) / 2 and the comments grow with p, so
#: p <= 23 would be 592 entries and 237 KB, past the half of the block limit
#: a table is asked to stay under so that it can still be extended.
BOUND = 19


# ---------------------------------------------------------------- Conrey's characters, by hand

def conrey_root(p):
    """The least positive integer generating (Z/p^k)^* for every k >= 1.

    A primitive root modulo p^2 is one modulo every higher power, so the test
    is modulo p and modulo p^2. For every prime below 40487 it is the least
    primitive root modulo p.
    """
    phi1, phi2 = p - 1, p * (p - 1)
    g = 2
    while True:
        if all(pow(g, phi1 // r, p) != 1 for r, _ in factor(phi1)) and \
                all(pow(g, phi2 // r, p * p) != 1 for r, _ in factor(phi2)):
            return g
        g += 1


_LOGS = {}


def discrete_logs(p):
    """{u: a} with u = g^a modulo p, a modulo p - 1, g Conrey's root."""
    p = ZZ(p)
    if p not in _LOGS:
        g = conrey_root(p)
        _LOGS[p] = {pow(g, a, p): a for a in range(p - 1)}
    return _LOGS[p]


def conrey_exponent(p, n, m):
    """The rational r in [0, 1) with chi_p(n, m) = exp(2 pi i r), or None when p | m."""
    if m % p == 0:
        return None
    logs = discrete_logs(p)
    r = QQ(logs[n % p] * logs[m % p]) / (p - 1)
    return r - r.floor()


def jacobi_sum_by_hand(p, m, n, bits):
    """J(chi_p(m, .), chi_p(n, .)) as a ball, from Conrey's definition of the characters."""
    C = ComplexBallField(bits)
    two_pi_i = 2 * C.pi() * C(0, 1)
    total = C(0)
    for a in range(2, p):                   # a = 0 and a = 1 contribute 0: chi, psi nontrivial
        r = conrey_exponent(p, m, a) + conrey_exponent(p, n, 1 - a)
        total += (two_pi_i * C(r - r.floor())).exp()
    return total


# ---------------------------------------------------------------- Sage's characters, as the check

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


_GAUSS = {}


def gauss_sum(p, n):
    """Sage's exact Gauss sum of chi_p(n, .), cached per character."""
    if (p, n) not in _GAUSS:
        _GAUSS[(p, n)] = sage_characters(p)[n].gauss_sum()
    return _GAUSS[(p, n)]


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


# ---------------------------------------------------------------- the theorems the comments rely on

def check_cubic(p, m, coefficients):
    """J(chi, chi) = a + b zeta_3 with a = -1 and b = 0 modulo 3, and a^2 - ab + b^2 = p."""
    a, b = coefficients
    if a % 3 != 2 or b % 3 != 0 or a * a - a * b + b * b != p:
        raise ArithmeticError('(%s, %s, %s): cubic J = %s + %s zeta_3 breaks the congruences'
                              % (p, m, m, a, b))


def check_quartic(p, m, chi, exact, K4):
    """-chi(-1) J(chi, chi) = a + b i with b even and a = 1 - b modulo 4, and a^2 + b^2 = p."""
    #chi(-1) is +-1 but lives in Sage's Q(zeta_{p-1}); multiplied there it
    #would carry the value out of Q(i) and the coefficients would be read
    #in the wrong basis. Take it as an integer first.
    a, b = (-ZZ(chi(-1)) * K4(exact)).polynomial().padded_list(2)
    if b % 2 != 0 or (a - (1 - b)) % 4 != 0 or a * a + b * b != p:
        raise ArithmeticError('(%s, %s, %s): quartic -chi(-1) J = %s + %s i is not 1 mod 2 + 2i'
                              % (p, m, m, a, b))


# ---------------------------------------------------------------- what the comment says

def latex_cyclotomic(coefficients, d):
    """sum c_k zeta_d^k, lowest power first, as a reader writes it: -1 - 3\\zeta_3, 3 + 2i."""
    pieces = []
    for k, c in enumerate(coefficients):
        c = ZZ(c)
        if c == 0:
            continue
        sign = '-' if c < 0 else '+'
        c = abs(c)
        if k == 0:
            body = str(c)
        else:
            if d == 4:
                power = 'i'
            else:
                power = r'\zeta_{%d}' % d if k == 1 else r'\zeta_{%d}^{%d}' % (d, k)
            body = power if c == 1 else '%d%s' % (c, power)
        pieces.append((sign, body))
    text = ('-' if pieces[0][0] == '-' else '') + pieces[0][1]
    for sign, body in pieces[1:]:
        text += ' %s %s' % (sign, body)
    return text


#: The two Jacobi sums the table of algebraic numbers of degree 2 holds, as
#: the anchors of its entries (a2, a1, a0, n): the roots -1 -+ 2i of x^2 + 2x + 5.
IN_DEGREE_TWO = {
    (5, 2, 2): r'HREF{Algebraic_numbers_of_degree_2#1,2,5,1}[$-1-2i$]',
    (5, 2, 4): r'HREF{Algebraic_numbers_of_degree_2#1,-2,5,2}[$1+2i$]',
    (5, 3, 3): r'HREF{Algebraic_numbers_of_degree_2#1,2,5,2}[$-1+2i$]',
    (5, 3, 4): r'HREF{Algebraic_numbers_of_degree_2#1,-2,5,1}[$1-2i$]',
}


class JacobiSums(numberdb.Generator):

    table = 'T143'
    parameters = ('p', 'm', 'n')
    type = 'C'
    digits = 100
    rigour = 'proven'

    def enumerate(self, bound=BOUND):
        for p in range(5, bound + 1):
            if not ZZ(p).is_prime():
                continue
            sage_characters(p)                      # the hand-built characters against Sage's
            for m in range(2, p):
                for n in range(m, p):
                    if (m * n) % p != 1:            # chi psi = chi_p(mn, .) nontrivial
                        yield {'p': int(p), 'm': int(m), 'n': int(n)}

    def value(self, params, digits):
        p, m, n = ZZ(params['p']), ZZ(params['m']), ZZ(params['n'])
        bits = numberdb.bits(digits, losing=WORKING_GUARD)
        ball = jacobi_sum_by_hand(p, m, n, bits)
        chars = sage_characters(p)
        chi, psi = chars[m], chars[n]
        exact = chi.jacobi_sum(psi)
        check = enclose(exact, bits)
        if not (finite(ball) and finite(check) and ball.overlaps(check)):
            raise ArithmeticError(
                '(%s, %s, %s): the sum over the hand-built characters gives %s and '
                "Sage's exact Jacobi sum %s; neither is right until the "
                'disagreement has a cause' % (p, m, n, ball, check))
        if exact * exact.conjugate() != p:
            raise ArithmeticError('(%s, %s, %s): J times its conjugate is not %s' % (p, m, n, p))
        if exact.conjugate() == exact or exact.conjugate() == -exact:
            raise ArithmeticError('(%s, %s, %s): J is real or purely imaginary' % (p, m, n))
        if psi.jacobi_sum(chi) != exact:
            raise ArithmeticError('(%s, %s, %s): J(chi, psi) and J(psi, chi) differ' % (p, m, n))
        product = chars[(m * n) % p]
        if exact != gauss_sum(p, m) * gauss_sum(p, n) / gauss_sum(p, (m * n) % p):
            raise ArithmeticError('(%s, %s, %s): J is not tau(chi) tau(psi) / tau(chi psi)'
                                  % (p, m, n))
        d1, d2 = ZZ(chi.order()), ZZ(psi.order())
        d = lcm(d1, d2)
        Kd = CyclotomicField(d)
        in_d = Kd(exact)                            # raises when J is not in Q(zeta_d)
        coefficients = in_d.polynomial().padded_list(Kd.degree())
        if any(c.denominator() != 1 for c in coefficients):
            raise ArithmeticError('(%s, %s, %s): J is not integral in zeta_%s' % (p, m, n, d))
        coefficients = [ZZ(c) for c in coefficients]
        if m == n and d1 == 3:
            check_cubic(p, m, coefficients)
        if m == n and d1 == 4:
            check_quartic(p, m, chi, exact, Kd)
        if d1 == 2:                                 # chi the quadratic character, m = p - 1
            if exact != psi(4) * psi.jacobi_sum(psi):
                raise ArithmeticError('(%s, %s, %s): J(chi, psi) is not psi(4) J(psi, psi)'
                                      % (p, m, n))
        del product
        comment = (r'$\chi$ of order $%d$, $\psi$ of order $%d$; $J(\chi,\psi)=%s$'
                   % (d1, d2, latex_cyclotomic(coefficients, d)))
        entry = {'number': ball, 'comment': comment}
        if (p, m, n) in IN_DEGREE_TWO:
            entry['equals'] = IN_DEGREE_TWO[(p, m, n)]
        return entry


if __name__ == '__main__':
    generator = JacobiSums()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='Jacobi sums of every pair of nontrivial characters modulo the primes '
                    'up to 19 with nontrivial product, summed in ball arithmetic from '
                    "Conrey's definition of the characters and checked against Sage's "
                    'exact Jacobi sum'))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
