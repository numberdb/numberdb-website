"""Values of Dirichlet L-functions at positive integers -- numberdb.org/T145

    L(s, chi) = sum_{n >= 1} chi(n) n^(-s),

for every primitive Dirichlet character chi of conductor q <= 30, indexed by
its Conrey label (q, n) as the tables of Gauss sums, of zeros of L(s, chi) and
of generalized Bernoulli numbers on this site index their characters, at
s = 1, 2, 3. The trivial character has L(s, 1) = zeta(s) and no row at s = 1,
where zeta has its pole.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**These digits are proven.** Every value is a complex ball: at s = 2, 3 it is
q^(-s) sum_a chi(a) zeta(s, a/q) with arb's Hurwitz zeta function, and at
s = 1 it is -(1/q) sum_a chi(a) psi(a/q) with arb's digamma, chi(a) being
exp(2 pi i r) of an exact rational r in arb. A hundred digits are written and
the widest ball, at (29, 27, 1), supports 117.

**The character is built from Conrey's definition, not looked up.** The value
chi_q(n, m) is computed from discrete logarithms modulo the prime powers
dividing q, exactly as the LMFDB knowl defines the label; Sage's character
with the same `conrey_number()` must agree with it on every value, and
primitivity decided by hand from the local exponents must agree with Sage's
`is_primitive()`, for every character of every modulus in range, before
anything is computed. A table indexed by the wrong labels is wrong in a way
no recomputation of the values can find.

**Two computations that share no code must agree on every entry.** The value
returned is the arb sum over the hand-built character. It must overlap a
second enclosure computed from Sage's character values by a hand-written
Euler-Maclaurin summation of each zeta(s, a/q) and psi(a/q), with the
Bernoulli numbers from their recurrence and the remainder bounded by the
first omitted term, which is a bound because t -> (t + x)^(-s) is completely
monotone. Where a closed form exists it must hold too: for chi(-1) = (-1)^s,

    L(s, chi) = (-1)^(s-1) (tau(chi) / 2) (2 pi i / q)^s B_{s, chibar} / s!,

with Sage's exact Gauss sum and exact generalized Bernoulli number enclosed
in balls; for odd chi, L(1, chi) = (pi / 2q) sum_a chi(a) cot(pi a / q); for
even chi, L(1, chi) = -(tau(chi) / q) sum_a chibar(a) log|1 - exp(2 pi i a/q)|.
For a real character the value is real, its imaginary part must contain zero
and is written as an exact 0, and with matching parity it is a rational
multiple of pi^s / sqrt(q) that the comment prints and the ball must contain.

**The comment on each entry** gives the order and the parity of chi; for a
real character the Kronecker symbol it is and, with matching parity, the
closed form; for the other characters with matching parity, when Q(zeta_d)
has degree at most 6, the exact B_{s, chibar} in Q(zeta_d), which with
tau(chi) from the table of Gauss sums is the closed form above. The real
characters at s = 1 are the residues in the table of Dedekind zeta functions
of quadratic fields, and are linked.
"""

import sys

import numberdb.sage as numberdb
from sage.arith.functions import lcm
from sage.arith.misc import euler_phi, factor, gcd, kronecker_symbol
from sage.modular.dirichlet import DirichletGroup
from sage.rings.complex_arb import ComplexBallField
from sage.rings.integer_ring import ZZ
from sage.rings.number_field.number_field import CyclotomicField
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField

#: Bits of working precision beyond what the written digits need. Measured
#: over the whole table at 100 digits: the sum of at most 30 terms loses
#: almost nothing, and the widest ball, at (29, 27, 1), has relative radius
#: 5.2e-118 at 397 bits, so the guard is the package's usual 64.
WORKING_GUARD = 64

#: Every primitive character of conductor up to here, at s = 1, 2, 3: 503
#: entries. The count of characters grows like the number of units (285 at
#: q <= 40, 471 at q <= 50), and at three values each the recommended
#: thousand entries is passed by q = 40.
BOUND = 30

#: The values of s that are filled. The family is L(s, chi) at positive
#: integers; these three are what somebody meets.
VALUES_OF_S = (1, 2, 3)


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


_TABLES = {}


def local_table(p, e):
    """Discrete logarithms modulo p^e in Conrey's coordinates.

    Odd p: {u: a} with u = g^a, a modulo phi(p^e). p = 2: {u: (a, b)} with
    u = (-1)^a 5^b, b modulo 2^(e-2); for e = 1 the only unit is 1.
    """
    pe = p ** e
    if pe in _TABLES:
        return _TABLES[pe]
    table = {}
    if p == 2:
        if e == 1:
            table[1] = (0, 0)
        else:
            for a in (0, 1):
                for b in range(2 ** (e - 2)):
                    table[((-1) ** a * pow(5, b, pe)) % pe] = (a, b)
    else:
        g = conrey_root(p)
        for a in range(euler_phi(pe)):
            table[pow(g, a, pe)] = a
    _TABLES[pe] = table
    return table


def conrey_exponent(q, n, m):
    """The rational r in [0, 1) with chi_q(n, m) = exp(2 pi i r), or None.

    None when gcd(m, q) > 1, where the character is 0. The label (q, n) is
    the LMFDB's: chi_q(n, m) = prod over p^e || q of chi_{p^e}(n, m), with
    chi_{p^e}(g^a, g^b) = e(ab / phi(p^e)) for odd p and, for p = 2 with
    e >= 2 and units (-1)^a 5^b, e(a a'/2 + b b'/2^(e-2)).
    """
    q = ZZ(q)
    if gcd(m, q) != 1:
        return None
    r = QQ(0)
    for p, e in factor(q):
        pe = p ** e
        table = local_table(p, e)
        if p == 2:
            if e >= 2:
                a, b = table[n % pe]
                a2, b2 = table[m % pe]
                r += QQ(a * a2) / 2 + QQ(b * b2) / 2 ** (e - 2)
        else:
            r += QQ(table[n % pe] * table[m % pe]) / euler_phi(pe)
    return r - r.floor()


def is_primitive_by_hand(q, n):
    """Whether chi_q(n, .) is primitive, from its local exponents.

    A character modulo p^e factors through p^(e-1) exactly when it is trivial
    on the kernel of reduction: for odd p and e >= 2 that is p | a, for e = 1
    it is a = 0; for 2^e it is e = 1, or e = 2 with a = 0, or e >= 3 with b
    even. Primitive means no local factor does.
    """
    q = ZZ(q)
    for p, e in factor(q):
        table = local_table(p, e)
        if p == 2:
            if e == 1:
                return False
            a, b = table[n % (p ** e)]
            if e == 2 and a == 0:
                return False
            if e >= 3 and b % 2 == 0:
                return False
        else:
            a = table[n % (p ** e)]
            if (e == 1 and a == 0) or (e >= 2 and a % p == 0):
                return False
    return True


def unit_ball(C, r):
    """exp(2 pi i r) as a ball, r an exact rational."""
    return (2 * C.pi() * C(0, 1) * C(r)).exp()


def l_value_by_hand(q, n, s, bits):
    """L(s, chi_q(n, .)) as a ball from Conrey's definition of the character.

    q^(-s) sum_a chi(a) zeta(s, a/q) with arb's Hurwitz zeta for s >= 2;
    -(1/q) sum_a chi(a) psi(a/q) with arb's digamma at s = 1, where the
    poles of zeta(s, a/q) cancel because sum_a chi(a) = 0.
    """
    C = ComplexBallField(bits)
    R = RealBallField(bits)
    total = C(0)
    for a in range(1, q + 1):
        r = conrey_exponent(q, n, a)
        if r is None:
            continue
        x = QQ(a) / q
        if s == 1:
            total += unit_ball(C, r) * C(R(x).psi())
        else:
            total += unit_ball(C, r) * C(s).zeta(C(x))
    if s == 1:
        return -total / q
    return total / C(q) ** s


# ---------------------------------------------------------------- Sage's characters, as the check

_GROUPS = {}


def sage_characters(q):
    """Sage's characters modulo q keyed by Conrey index, checked against the hand-built ones."""
    q = ZZ(q)
    if q not in _GROUPS:
        group = DirichletGroup(q)
        chars = {ZZ(chi.conrey_number()): chi for chi in group}
        zeta = group.base_ring().gen() if q > 2 else None
        order = ZZ(zeta.multiplicative_order()) if q > 2 else ZZ(1)
        for n, chi in chars.items():
            if is_primitive_by_hand(q, n) != chi.is_primitive():
                raise ArithmeticError('q = %s, n = %s: primitivity by hand and by Sage disagree'
                                      % (q, n))
            for a in range(1, q + 1):
                r = conrey_exponent(q, n, a)
                want = 0 if r is None else (zeta ** ZZ(r * order) if q > 2 else 1)
                if chi(a) != want:
                    raise ArithmeticError('q = %s, n = %s: the hand-built character and '
                                          "Sage's disagree at %s" % (q, n, a))
        _GROUPS[q] = chars
    return _GROUPS[q]


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


# ---------------------------------------------------------------- Euler-Maclaurin, by hand

_BERNOULLI = [QQ(1)]


def bernoulli_number(m):
    """B_m from B_0 = 1 and sum_{j<m} binomial(m+1, j) B_j = 0, so B_1 = -1/2."""
    while len(_BERNOULLI) <= m:
        k = len(_BERNOULLI)
        total = QQ(0)
        for j in range(k):
            total += ZZ(k + 1).binomial(j) * _BERNOULLI[j]
        _BERNOULLI.append(-total / (k + 1))
    return _BERNOULLI[m]


#: Terms summed directly before the Euler-Maclaurin tail, and the largest
#: index 2j of a Bernoulli term. With N = 64 the terms fall below 2^-420 by
#: 2j = 260 for every x in (0, 1], and every remainder is then below the
#: working precision.
EM_DIRECT = 64
EM_CAP = 260


def hurwitz_by_euler_maclaurin(s, x, bits):
    """zeta(s, x) for an integer s >= 2 and rational x > 0.

    sum_{k<N} (k+x)^(-s) + (N+x)^(1-s)/(s-1) + (N+x)^(-s)/2
      + sum_{j>=1} B_{2j}/(2j)! (s)_{2j-1} (N+x)^(-s-2j+1),

    (s)_m the rising factorial, stopped at the first term below the working
    precision, that term's absolute value added to the radius: for a
    completely monotone f, here f(t) = (t+x)^(-s), the Euler-Maclaurin
    remainder has the sign of the first omitted term and is smaller.
    """
    R = RealBallField(bits)
    x = R(x)
    total = R(0)
    for k in range(EM_DIRECT):
        total += (k + x) ** (-s)
    y = EM_DIRECT + x
    total += y ** (1 - s) / (s - 1) + y ** (-s) / 2
    rising = R(s)
    ypow = y ** (-s - 1)
    j = 1
    while True:
        term = R(bernoulli_number(2 * j)) / ZZ(2 * j).factorial() * rising * ypow
        if term.abs() < R(2) ** (-(bits + 20)) or 2 * j >= EM_CAP:
            return total.add_error(term.abs().upper())
        total += term
        rising *= (s + 2 * j - 1) * (s + 2 * j)
        ypow /= y * y
        j += 1


def digamma_by_euler_maclaurin(x, bits):
    """psi(x) = log(N+x) - 1/(2(N+x)) - sum_{k<N} 1/(k+x) - sum_{j>=1} B_{2j} / (2j (N+x)^{2j}),

    the same stopping rule and the same remainder bound, f(t) = 1/(t+x).
    """
    R = RealBallField(bits)
    x = R(x)
    total = R(0)
    for k in range(EM_DIRECT):
        total -= 1 / (k + x)
    y = EM_DIRECT + x
    total += y.log() - 1 / (2 * y)
    ypow = 1 / (y * y)
    j = 1
    while True:
        term = R(bernoulli_number(2 * j)) / (2 * j) * ypow
        if term.abs() < R(2) ** (-(bits + 20)) or 2 * j >= EM_CAP:
            return total.add_error(term.abs().upper())
        total -= term
        ypow /= y * y
        j += 1


def l_value_by_euler_maclaurin(q, chi, s, bits):
    """L(s, chi) from Sage's exact character values and the sums above."""
    C = ComplexBallField(bits)
    total = C(0)
    for a in range(1, q + 1):
        c = chi(a)
        if c == 0:
            continue
        x = QQ(a) / q
        if s == 1:
            total += enclose(c, bits) * C(digamma_by_euler_maclaurin(x, bits))
        else:
            total += enclose(c, bits) * C(hurwitz_by_euler_maclaurin(s, x, bits))
    if s == 1:
        return -total / q
    return total / C(q) ** s


# ---------------------------------------------------------------- the closed forms

def closed_form(q, chi, s, bits):
    """(-1)^(s-1) tau(chi)/2 (2 pi i / q)^s B_{s, chibar} / s! as a ball, for chi(-1) = (-1)^s."""
    C = ComplexBallField(bits)
    tau = enclose(chi.gauss_sum(), bits)
    B = enclose((chi ** (-1)).bernoulli(s), bits)
    return (-1) ** (s - 1) * tau / 2 * (2 * C.pi() * C(0, 1) / q) ** s * B / ZZ(s).factorial()


def cotangent_form(q, n, bits):
    """(pi / 2q) sum_{a=1}^{q-1} chi(a) cot(pi a / q) as a ball, for odd chi."""
    C = ComplexBallField(bits)
    total = C(0)
    for a in range(1, q):
        r = conrey_exponent(q, n, a)
        if r is not None:
            total += unit_ball(C, r) * (C.pi() * a / q).cot()
    return C.pi() / (2 * q) * total


def logarithm_form(q, n, chi, bits):
    """-(tau(chi) / q) sum_{a=1}^{q-1} chibar(a) log|1 - exp(2 pi i a / q)| as a ball, for even chi."""
    C = ComplexBallField(bits)
    R = RealBallField(bits)
    tau = enclose(chi.gauss_sum(), bits)
    total = C(0)
    for a in range(1, q):
        r = conrey_exponent(q, n, a)
        if r is not None:
            total += unit_ball(C, -r) * C((2 * (R.pi() * a / q).sin()).log())
    return -tau / q * total


def real_closed_form(q, chi, D, s):
    """(a, b) with L(s, chi) = a pi^s / (b sqrt(q)) for the real character chi = (D/.), chi(-1) = (-1)^s.

    From the closed form with tau = i^a sqrt(q), a = 0 or 1 the parity, and
    B_{s, chi} rational: L = (-1)^(s-1) i^(a+s) 2^(s-1) B_{s,chi} / (q^s s!)
    times pi^s sqrt(q), and i^(a+s) = (-1)^((a+s)/2) since a + s is even.
    """
    parity = 0 if chi.is_even() else 1
    B = QQ(chi.bernoulli(s))
    sign = (-1) ** (s - 1) * (-1) ** ((parity + s) // 2)
    r = sign * QQ(2) ** (s - 1) * B / (QQ(q) ** s * ZZ(s).factorial())
    scaled = r * q                                       # L = scaled * pi^s / sqrt(q)
    return scaled.numerator(), scaled.denominator()


# ---------------------------------------------------------------- what the comment says

def latex_cyclotomic(x, d):
    """An element of Q(zeta_d) as a reader writes it: (-3 + i)/5, -1 - 3\\zeta_3, with the
    constant term first, i for zeta_4, and one denominator for the whole."""
    coefficients = [QQ(c) for c in x.polynomial().padded_list(euler_phi(d))]
    denominator = lcm([c.denominator() for c in coefficients] or [1])
    pieces = []
    for k, c in enumerate(coefficients):
        c = ZZ(c * denominator)
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
    if not pieces:
        return '0'
    text = ('-' if pieces[0][0] == '-' else '') + pieces[0][1]
    for sign, body in pieces[1:]:
        text += ' %s %s' % (sign, body)
    if denominator != 1:
        text = r'\frac{%s}{%d}' % (text, denominator)
    return text


def latex_real_closed_form(q, s, a, b):
    """a pi^s / (b sqrt(q)) as a reader writes it, with sqrt(q) an integer when it is one."""
    root = ZZ(q).isqrt()
    pi = r'\pi' if s == 1 else r'\pi^%d' % s
    if root ** 2 == q:
        a, b = QQ(a) / (b * root), 1
        a, b = a.numerator(), a.denominator()
        root_text = ''
    else:
        root_text = r'\sqrt{%d}' % q
    numerator = pi if a == 1 else ('-' + pi if a == -1 else '%d%s' % (a, pi))
    denominator = ('%d' % b if b != 1 else '') + root_text
    if denominator == '':
        return numerator
    return r'\frac{%s}{%s}' % (numerator, denominator)


#: Special names for values in the table, by (q, n, s).
NAMED = {
    (4, 3, 2): r"; $L(2,\chi)=G$, Catalan's constant",
}

#: The exact B_{s, chibar} goes in the comment while Q(chi) = Q(zeta_d) has
#: degree at most this, i.e. the number has at most six terms. Beyond that
#: the comment outweighs the value: with every B written the block at
#: q <= 30 is 170 KB, and the twelve-term numbers of the order-28 characters
#: are 250 characters each.
BERNOULLI_DEGREE = 6

#: The residues of the Dedekind zeta functions of quadratic fields, kappa_D
#: = L(1, chi_D), as the anchors of the entries of that table.
RESIDUES = 'Residues_of_Dedekind_zeta_functions_of_quadratic_fields'

#: zeta(s) for s = 2, 3, in the table of values of the Riemann zeta function.
ZETA = 'Values_of_the_Riemann_zeta_function_at_rational_numbers'


class DirichletLValues(numberdb.Generator):

    table = 'T145'
    parameters = ('q', 'n', 's')
    type = 'C'
    digits = 100
    rigour = 'proven'

    def enumerate(self, bound=BOUND):
        for q in range(1, bound + 1):
            chars = sage_characters(q)              # the hand-built characters against Sage's
            for n in sorted(chars):
                if not chars[n].is_primitive():
                    continue
                for s in VALUES_OF_S:
                    if q == 1 and s == 1:
                        continue                    # zeta has its pole there
                    yield {'q': int(q), 'n': int(n), 's': int(s)}

    def value(self, params, digits):
        q, n, s = ZZ(params['q']), ZZ(params['n']), ZZ(params['s'])
        bits = numberdb.bits(digits, losing=WORKING_GUARD)
        C = ComplexBallField(bits)
        R = RealBallField(bits)
        if q == 1:
            value = C(s).zeta()
            check = C(hurwitz_by_euler_maclaurin(s, QQ(1), bits))
            if not (finite(value) and value.overlaps(check)):
                raise ArithmeticError('(1, 1, %s): zeta(%s) by arb %s and by Euler-Maclaurin %s'
                                      % (s, s, value, check))
            if s == 2 and not value.real().overlaps(R.pi() ** 2 / 6):
                raise ArithmeticError('zeta(2) does not contain pi^2/6')
            value = C(value.real(), R(0))
            comment = r'$\chi=1$, the trivial character: $L(s,1)=\zeta(s)$'
            if s == 2:
                comment += r'; $\zeta(2)=\pi^2/6$'
            if s == 3:
                comment += r"; $\zeta(3)$ is Apéry's constant"
            return {'number': value, 'comment': comment,
                    'equals': r'HREF{%s#%d}[$\zeta(%d)$]' % (ZETA, s, s)}
        chi = sage_characters(q)[n]
        value = l_value_by_hand(q, n, s, bits)
        check = l_value_by_euler_maclaurin(q, chi, s, bits)
        if not (finite(value) and finite(check) and value.overlaps(check)):
            raise ArithmeticError(
                '(%s, %s, %s): the arb sum over the hand-built character gives %s and '
                "the Euler-Maclaurin sum over Sage's character %s; neither is right "
                'until the disagreement has a cause' % (q, n, s, value, check))
        d = ZZ(chi.order())
        parity = 'even' if chi.is_even() else 'odd'
        matching = (s % 2 == 1) == chi.is_odd()
        if matching and not value.overlaps(closed_form(q, chi, s, bits)):
            raise ArithmeticError('(%s, %s, %s): the closed form in tau(chi) and B_{s,chibar} '
                                  'does not overlap' % (q, n, s))
        if s == 1 and chi.is_odd() and not value.overlaps(cotangent_form(q, n, bits)):
            raise ArithmeticError('(%s, %s, 1): the cotangent form does not overlap' % (q, n))
        if s == 1 and chi.is_even() and not value.overlaps(logarithm_form(q, n, chi, bits)):
            raise ArithmeticError('(%s, %s, 1): the logarithm form does not overlap' % (q, n))
        entry = {}
        if d == 2:
            D = q if chi.is_even() else -q
            for a in range(1, q + 1):
                r = conrey_exponent(q, n, a)
                want = 0 if r is None else (1 if r == 0 else -1)
                if kronecker_symbol(D, a) != want:
                    raise ArithmeticError('(%s, %s): not the Kronecker symbol of %s at %s'
                                          % (q, n, D, a))
            if not value.imag().contains_zero():
                raise ArithmeticError('(%s, %s, %s): real character, imaginary part %s'
                                      % (q, n, s, value.imag()))
            value = C(value.real(), R(0))
            comment = r'$\chi=\left(\frac{%d}{\cdot}\right)$, %s' % (D, parity)
            if matching:
                a, b = real_closed_form(q, chi, D, s)
                exact = C(a) * C.pi() ** s / (b * C(q).sqrt())
                if not value.overlaps(exact):
                    raise ArithmeticError('(%s, %s, %s): the ball does not contain %s pi^%s / (%s sqrt %s)'
                                          % (q, n, s, a, s, b, q))
                comment += r'; $L(%d,\chi)=%s$' % (s, latex_real_closed_form(q, s, a, b))
            comment += NAMED.get((q, n, s), '')
            if s == 1:
                entry['equals'] = r'HREF{%s#%d}[$\kappa_{%d}$]' % (RESIDUES, D, D)
        else:
            if value.imag().contains_zero():
                raise ArithmeticError('(%s, %s, %s): a non-real character with a value whose '
                                      'imaginary part may vanish, %s' % (q, n, s, value.imag()))
            comment = r'$\chi$ of order $%d$, %s' % (d, parity)
            if matching and euler_phi(d) <= BERNOULLI_DEGREE:
                B = (chi ** (-1)).bernoulli(s)
                Kd = CyclotomicField(d)
                comment += r'; $B_{%d,\bar\chi}=%s$' % (s, latex_cyclotomic(Kd(B), d))
            if q == 5 and s == 1:
                sign = '+' if n == 2 else '-'
                cot = C.pi() / 5 * ((C.pi() / 5).cot() + (1 if n == 2 else -1) * C(0, 1) * (2 * C.pi() / 5).cot())
                if not value.overlaps(cot):
                    raise ArithmeticError('(5, %s, 1): not pi/5 (cot(pi/5) %s i cot(2pi/5))' % (n, sign))
                comment += r'; $L(1,\chi)=\frac{\pi}{5}\left(\cot\frac{\pi}{5}%si\cot\frac{2\pi}{5}\right)$' % sign
        entry['number'] = value
        entry['comment'] = comment
        return entry


if __name__ == '__main__':
    generator = DirichletLValues()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='L(s, chi) at s = 1, 2, 3 for every primitive Dirichlet character of '
                    'conductor at most 30, summed in ball arithmetic from Hurwitz zeta and '
                    "digamma values over Conrey's definition of the character, checked "
                    'against a hand-written Euler-Maclaurin sum and the closed forms'))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
