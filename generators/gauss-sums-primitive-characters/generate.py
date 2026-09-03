"""Gauss sums of primitive Dirichlet characters -- numberdb.org/T142

    tau(chi) = sum_{a=1}^{q} chi(a) exp(2 pi i a / q),

for every primitive Dirichlet character chi of conductor q <= 50, indexed by
its Conrey label (q, n), as the tables of zeros of L(s, chi) and of generalized
Bernoulli numbers on this site index their characters.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**These digits are proven.** Every value is a complex ball: each of the q terms
is exp(2 pi i r) of an exact rational r in arb, and the sum carries its error
through. The written digits are the ones the ball supports.

**The character is built from Conrey's definition, not looked up.** The value
chi_q(n, m) is computed here from discrete logarithms modulo the prime powers
dividing q, exactly as the LMFDB knowl defines the label: for an odd prime
power p^e with g the least positive integer generating (Z/p^k)^* for every k,
chi(g^a, g^b) = e(ab / phi(p^e)); for 2^e with the units written (-1)^a 5^b,
chi = e(a a'/2 + b b'/2^(e-2)); and a product over the prime powers of q. This
is a second construction of the character that shares nothing with Sage's
`DirichletGroup`, and the two must agree, entry by entry, before a value is
returned:

* the ball sum from the hand-built character must overlap an enclosure of
  Sage's exact `gauss_sum()` of the character Sage numbers (q, n) -- so a
  disagreement about what chi_q(n, .) *is* fails here rather than being
  published under the wrong label;
* tau(chi) times its conjugate must contain q, which is the theorem
  |tau(chi)|^2 = q for primitive chi;
* which characters are primitive is decided by hand from the local exponents
  and compared with Sage's `is_primitive()` for every character of every
  modulus in range.

When this was written all 471 entries passed, and the controls that must fail
fail (the index 2 character mod 7 against Sage's index 3; a value shifted by
1e-60 against OEIS A396260).

**For a real character the known-zero part is written as an exact zero.**
Gauss's theorem gives tau = sqrt(q) for an even quadratic character and
i sqrt(q) for an odd one; the ball is required to contain zero in that part,
and the part is then replaced by 0, so that the entry reads `0 + i * 1.73...`
and not a hundred digits of rounding noise.

**The comment on each entry** gives the order and parity of chi, the degree
of tau(chi) over Q, and, when that degree is at most 12, the minimal
polynomial. Neither comes from Sage's `minpoly()`, which for a character of
order 46 modulo 47 works in a field of degree 1012 and did not finish in half
an hour. The degree is the number of distinct Galois conjugates of tau(chi):
sigma_c(tau(chi)) = sum_a chi(a)^c e(ac/q) for c in (Z/M)^*, M = lcm(q, d),
is a sum of M-th roots of unity, computed as balls for one c per coset of the
subgroup {c = 1 mod d, chi(c) = 1} that fixes tau; balls that are pairwise
disjoint are distinct numbers, and two that overlap are compared exactly. The
minimal polynomial, when the degree is small, is the product over the
conjugates rounded to integers and then required to vanish exactly at
tau(chi) in its cyclotomic field. For prime q the degree is d phi(d), d the
order of chi (the formula of OEIS A396254), which the table's formulas state
and the checks outside this file compared with every entry.

**Ninety-two of the non-real Gauss sums are sqrt(q) times a root of unity**
-- every character whose component at each prime p dividing q is either
quadratic or of conductor p^e with e >= 2 -- and their comments say which
root of unity: tau(chi_16(5, .)) = 4 zeta_16^15. tau^2/q lies in Q(zeta_M),
so it is a root of unity only if its z-th power is 1, z the number of roots
of unity in that field; a ball for that power excluding 1 proves it is not,
and when the ball allows it the exponent is read off the argument and
confirmed exactly in the field. The other 348 are proven not to be, entry by
entry, in that way.
"""

import sys

import numberdb.sage as numberdb
from sage.arith.functions import lcm
from sage.arith.misc import euler_phi, factor, gcd
from sage.modular.dirichlet import DirichletGroup
from sage.rings.complex_arb import ComplexBallField
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField

#: Bits of working precision beyond what the written digits need. Measured
#: over the whole table at 100 digits: a sum of at most 50 exponentials loses
#: almost nothing, and the widest ball (q = 47) supports about 116 digits at
#: 397 bits, so the guard is the package's usual 64 rather than anything the
#: family required.
WORKING_GUARD = 64

#: Every primitive character of conductor up to here: 471 of them. The count
#: grows like the number of units, 1816 at q <= 100, so this is where the
#: recommended thousand entries would be passed; and q = 50 is where the
#: Gauss sums somebody meets by hand end.
BOUND = 50

#: The minimal polynomial goes in the comment when its degree is at most this.
MINPOLY_DEGREE = 12


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


def gauss_sum_by_hand(q, n, bits):
    """tau(chi_q(n, .)) as a ball, from Conrey's definition of the character."""
    C = ComplexBallField(bits)
    two_pi_i = 2 * C.pi() * C(0, 1)
    total = C(0)
    for m in range(1, q + 1):
        r = conrey_exponent(q, n, m)
        if r is None:
            continue
        total += (two_pi_i * C(r + QQ(m) / q)).exp()
    return total


# ---------------------------------------------------------------- Sage's characters, as the check

_GROUPS = {}


def sage_characters(q):
    """Sage's characters modulo q keyed by Conrey index."""
    q = ZZ(q)
    if q not in _GROUPS:
        _GROUPS[q] = {ZZ(chi.conrey_number()): chi for chi in DirichletGroup(q)}
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


# ---------------------------------------------------------------- the degree of tau(chi), from its conjugates

#: Bits for separating the Galois conjugates of tau(chi). Two conjugates
#: whose balls overlap at this precision are compared exactly, so the
#: precision decides only how often that happens, never what is concluded.
ORBIT_BITS = 128


def conjugates(q, n, chi, bits=ORBIT_BITS):
    """The Galois conjugates of tau(chi) as balls, one per coset of the group
    fixing it, each with the c that produced it.

    sigma_c, for c in (Z/M)^* with M = lcm(q, d), sends zeta_q to zeta_q^c and
    chi(a) to chi(a)^c, so sigma_c(tau(chi)) = sum_a chi(a)^c e(ac/q), a sum of
    M-th roots of unity. For c = 1 mod d it is chibar(c) tau(chi), so the
    subgroup {c = 1 mod d, chi(c) = 1} fixes tau and one c per coset of it
    is enough: the distinct values among these are all the conjugates.
    """
    d = ZZ(chi.order())
    M = lcm(q, d)
    C = ComplexBallField(bits)
    zeta = (2 * C.pi() * C(0, 1) / M).exp()
    powers = [C(1)]
    for _ in range(1, M):
        powers.append(powers[-1] * zeta)
    exponents = {}
    for a in range(1, q):
        r = conrey_exponent(q, n, a)
        if r is not None:
            exponents[a] = r
    seen = set()
    out = []
    for c in range(1, M):
        if gcd(c, M) != 1:
            continue
        key = (c % d, conrey_exponent(q, n, c % q))
        if key in seen:
            continue
        seen.add(key)
        total = C(0)
        for a, r in exponents.items():
            total += powers[ZZ((c * r + QQ(c * a) / q) * M) % M]
        out.append((c, total))
    return out


def exact_conjugate(chi, c, field):
    """sigma_c(tau(chi)) exactly: sum_a chi^c(a) zeta_q^(ac), Sage's gauss_sum(c) of chi^c."""
    return field((chi ** c).gauss_sum(c))


def distinct_conjugates(q, n, chi, exact):
    """The conjugates of tau(chi), one ball per distinct value.

    Balls that are pairwise disjoint are distinct numbers. Two that overlap
    are compared exactly, and are then either the same conjugate (one class)
    or a pair too close to separate here, which is refused rather than
    guessed. Overlaps are looked for among neighbours in real part only,
    which is where they can be.
    """
    field = exact.parent()
    items = sorted(conjugates(q, n, chi), key=lambda item: item[1].real().mid())
    R = RealBallField(ORBIT_BITS)
    classes = []                      # [(c, ball)] for the first of each class
    merged = [False] * len(items)
    for i, (c, ball) in enumerate(items):
        if merged[i]:
            continue
        classes.append((c, ball))
        j = i + 1
        while j < len(items):
            c2, other = items[j]
            gap = R(other.real().mid() - ball.real().mid())
            if gap > R(ball.real().rad()) + R(other.real().rad()):
                break
            if not merged[j] and ball.overlaps(other):
                if exact_conjugate(chi, c, field) == exact_conjugate(chi, c2, field):
                    merged[j] = True
                else:
                    raise ArithmeticError('(%s, %s): conjugates for c = %s and %s overlap '
                                          'at %s bits and are different numbers'
                                          % (q, n, c, c2, ORBIT_BITS))
            j += 1
    return [ball for _, ball in classes]


def integer_polynomial(roots):
    """prod (x - root) over balls whose product must be an integer polynomial.

    Returns the coefficients, lowest first, as Sage integers; refuses when a
    coefficient ball does not pin down one integer with zero imaginary part.
    """
    coefficients = [roots[0].parent()(1)]
    for root in roots:
        shifted = [-root * c for c in coefficients] + [coefficients[0].parent()(0)]
        for k in range(len(coefficients)):
            shifted[k + 1] += coefficients[k]
        coefficients = shifted
    out = []
    for c in coefficients:
        nearest = ZZ(c.real().mid().round())
        if not (c.imag().contains_zero() and c.real().contains_integer()
                and c.real().rad() < 0.25 and c.real().overlaps(RealBallField(ORBIT_BITS)(nearest))):
            raise ArithmeticError('a coefficient ball %s holds no single integer' % c)
        out.append(nearest)
    return out


def degree_and_polynomial(q, n, chi, exact):
    """[Q(tau(chi)) : Q], and the minimal polynomial when the degree is small.

    The degree is the number of distinct conjugates. When it is at most
    MINPOLY_DEGREE the product over them is rounded to an integer polynomial,
    which must vanish exactly at tau(chi) in its cyclotomic field; it is then
    the minimal polynomial, since it is monic, has the conjugates as its
    roots, and each of them once.
    """
    roots = distinct_conjugates(q, n, chi, exact)
    degree = ZZ(len(roots))
    if degree > MINPOLY_DEGREE:
        return degree, None
    coefficients = integer_polynomial(roots)
    value = sum(c * exact ** k for k, c in enumerate(coefficients))
    if value != 0:
        raise ArithmeticError('(%s, %s): the polynomial from the conjugates does not '
                              'vanish at tau exactly' % (q, n))
    return degree, coefficients


# ---------------------------------------------------------------- sqrt(q) times a root of unity?

def root_of_unity_form(q, chi, exact, tau):
    """r with tau(chi) = sqrt(q) exp(2 pi i r), or None when there is no such r.

    tau^2 / q is in Q(zeta_M), M = lcm(q, d), whose roots of unity are those
    of order dividing z = lcm(2, M); so tau is sqrt(q) times a root of unity
    exactly when (tau^2/q)^z = 1, and r is then a multiple of 1/(2z). The
    ball decides the negative case -- a ball for (tau^2/q)^z that excludes 1
    proves it -- and a positive case is confirmed exactly: r is read off the
    argument of the ball and exp(4 pi i r) must equal tau^2/q in the field.
    """
    K = exact.parent()
    z = ZZ(K.zeta_order())
    w = tau ** 2 / q
    if not (w ** z - 1).contains_zero():
        return None
    C = tau.parent()
    R = RealBallField(C.precision())
    argument = (tau.arg() / (2 * C.pi())).real()
    found = None
    for k in range(2 * z):
        candidate = R(QQ(k) / (2 * z))
        if argument.overlaps(candidate) or (argument + 1).overlaps(candidate):
            found = QQ(k) / (2 * z)
            break
    if found is None:
        raise ArithmeticError('(%s): tau^2/q is a root of unity but no argument k/%s '
                              'matches' % (q, 2 * z))
    exponent = 2 * found * z                      # exp(4 pi i r) = zeta_z^exponent
    if exponent.denominator() != 1 or K.zeta(z) ** ZZ(exponent) != exact ** 2 / q:
        raise ArithmeticError('(%s): tau^2/q is not exp(4 pi i %s) exactly' % (q, found))
    return found


# ---------------------------------------------------------------- what the comment says

def latex_polynomial(coefficients):
    """An integer polynomial, lowest coefficient first, as a reader writes it: x^6 - 7x^3 + 343."""
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


def root_of_unity_latex(q, r):
    """sqrt(q) exp(2 pi i r) as sqrt(q) zeta_m^k, with sqrt(q) an integer when it is one."""
    #`isqrt`, not `sqrt`: an Integer's sqrt of a non-square is a symbolic
    #expression, and comparing it reaches parts of Sage that named imports
    #do not initialise.
    root = ZZ(q).isqrt()
    if root ** 2 == q:
        scale = '' if root == 1 else str(root)
    else:
        scale = r'\sqrt{%d}\,' % q
    if r == 0:
        return scale or '1'
    m, k = r.denominator(), r.numerator()
    power = r'\zeta_{%d}' % m if k == 1 else r'\zeta_{%d}^{%d}' % (m, k)
    return scale + power


def comment(q, n, chi, degree, minpoly, root_form):
    d = ZZ(chi.order())
    parity = 'even' if chi.is_even() else 'odd'
    if d == 2:
        D = q if chi.is_even() else -q
        closed = r'\sqrt{%d}' % q if chi.is_even() else r'i\sqrt{%d}' % q
        if q == 4:
            closed = '2i'
        return r'$\chi=\left(\frac{%d}{\cdot}\right)$, %s: $\tau(\chi)=%s$' % (D, parity, closed)
    text = r'$\chi$ of order $%d$, %s; $[\mathbb{Q}(\tau(\chi)):\mathbb{Q}]=%d$' % (d, parity, degree)
    if root_form is not None:
        text += r', $\tau(\chi)=%s$' % root_of_unity_latex(q, root_form)
    if minpoly is not None:
        text += r', $\tau(\chi)$ a root of $%s$' % latex_polynomial(minpoly)
    return text


#: The three quadratic Gauss sums the table of algebraic numbers of degree 2
#: holds, as the anchors of its entries (a2, a1, a0, n).
IN_DEGREE_TWO = {
    (3, 2): (r'HREF{Algebraic_numbers_of_degree_2#1,0,3,2}[$i\sqrt{3}$]'),
    (4, 3): (r'HREF{Algebraic_numbers_of_degree_2#1,0,4,2}[$2i$]'),
    (5, 4): (r'HREF{Algebraic_numbers_of_degree_2#1,0,-5,2}[$\sqrt{5}$]'),
}


class GaussSums(numberdb.Generator):

    table = 'T142'
    parameters = ('q', 'n')
    type = 'C'
    digits = 100
    rigour = 'proven'

    def enumerate(self, bound=BOUND):
        for q in range(1, bound + 1):
            chars = sage_characters(q)
            for n in sorted(chars):
                if is_primitive_by_hand(q, n) != chars[n].is_primitive():
                    raise ArithmeticError('q = %s, n = %s: primitivity by hand and '
                                          'by Sage disagree' % (q, n))
            for n in sorted(chars):
                if chars[n].is_primitive():
                    yield {'q': int(q), 'n': int(n)}

    def value(self, params, digits):
        q, n = ZZ(params['q']), ZZ(params['n'])
        if q == 1:
            return {'number': ZZ(1), 'equals': 'HREF{One}',
                    'comment': r'$\chi=1$, the trivial character: $\tau(1)=1$'}
        bits = numberdb.bits(digits, losing=WORKING_GUARD)
        tau = gauss_sum_by_hand(q, n, bits)
        chi = sage_characters(q)[n]
        exact = chi.gauss_sum()
        check = enclose(exact, bits)
        if not (finite(tau) and finite(check) and tau.overlaps(check)):
            raise ArithmeticError(
                '(%s, %s): the sum over the hand-built character gives %s and '
                "Sage's exact Gauss sum %s; neither is right until the "
                'disagreement has a cause' % (q, n, tau, check))
        if not (tau * tau.conjugate()).overlaps(ComplexBallField(bits)(q)):
            raise ArithmeticError('(%s, %s): |tau|^2 = %s does not contain %s'
                                  % (q, n, tau * tau.conjugate(), q))
        if chi.order() == 2:
            #Gauss: real for even chi, purely imaginary for odd. The part the
            #theorem makes zero must contain zero, and is then written as 0.
            R = RealBallField(bits)
            C = ComplexBallField(bits)
            if chi.is_even():
                if not tau.imag().contains_zero():
                    raise ArithmeticError('(%s, %s): even quadratic, imaginary part %s'
                                          % (q, n, tau.imag()))
                tau = C(tau.real(), R(0))
            else:
                if not tau.real().contains_zero():
                    raise ArithmeticError('(%s, %s): odd quadratic, real part %s'
                                          % (q, n, tau.real()))
                tau = C(R(0), tau.imag())
        degree, minpoly = degree_and_polynomial(q, n, chi, exact)
        root_form = root_of_unity_form(q, chi, exact, tau) if chi.order() > 2 else None
        entry = {'number': tau, 'comment': comment(q, n, chi, degree, minpoly, root_form)}
        if (q, n) in IN_DEGREE_TWO:
            entry['equals'] = IN_DEGREE_TWO[(q, n)]
        return entry


if __name__ == '__main__':
    generator = GaussSums()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='Gauss sums of every primitive Dirichlet character of '
                    'conductor at most 50, summed in ball arithmetic from '
                    "Conrey's definition of the character and checked against "
                    "Sage's exact Gauss sum"))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
