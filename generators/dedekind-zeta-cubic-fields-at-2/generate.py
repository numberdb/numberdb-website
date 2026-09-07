"""Values of Dedekind zeta functions of cubic fields at s = 2 -- numberdb.org/T162

    zeta_K(2) = sum_a N(a)^-2

for every cubic field K with |D| <= 3000, D the discriminant of K. Fields
sharing a discriminant are told apart by an index k, the position of the
field's reduced polynomial (PARI's polredabs) in lexicographic order of its
coefficient vector -- the index of the tables of regulators (numberdb.org/T158)
and residues (numberdb.org/T159) of cubic fields, which hold the same 515
fields.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**These digits are proven**, by two different routes for the two signatures.

For a complex cubic field (D < 0) the value is a real ball from binary
quadratic forms. Write zeta_K(s) = zeta(s) L(s, rho) with rho the
two-dimensional representation of S_3 (or, for a cyclic field, which is never
complex, the sum of the two cubic characters). Every primitive positive
definite form Q of discriminant D represents primes, and the primes
represented by the forms of one class C all decompose in K the same way,
splitting completely or staying prime; put eps(C) = 1 in the first case and
-1/2 in the second. Then

    L(s, rho) = (1/2) sum_C eps(C) Z_{Q_C}(s),    Z_Q(s) = sum'_{(m,n)} Q(m,n)^-s,

where the sum runs over the h(D) classes of primitive forms and Z_Q is the
Epstein zeta function of the form. The identity is a statement about weight-1
modular forms: L(s, rho) is the L-series of a cusp form of weight 1, level |D|
and character (D/.) (Hecke, since rho is induced from a cubic character of the
quadratic resolvent field Q(sqrt(D))), each theta series sum q^{Q(m,n)} is a
modular form of the same weight, level and character, and two such forms
whose first B Fourier coefficients agree are equal, for B the Sturm bound
|D| prod_{p | D}(1 + 1/p)/12. The generator checks the first B + 5
coefficients exactly, on every field, from the representation numbers of the
forms on one side and the Dirichlet coefficients of zeta_K(s)/zeta(s) (PARI's
dirzetak and Moebius inversion) on the other, and refuses the field if any
coefficient differs. Each Z_Q(2) is then the Chowla-Selberg expansion

    Z_Q(2) = (4/|D|) [ 2 zeta(4) y^2 + pi zeta(3)/y
             + 8 pi^2 sqrt(y) sum_{n>=1} n^{3/2} sigma_{-3}(n) K_{3/2}(2 pi n y) cos(pi n b/a) ],

y = sqrt|D|/(2a) for Q = a m^2 + b m n + c n^2, in which K_{3/2}(z) =
sqrt(pi/(2z)) e^{-z} (1 + 1/z) is elementary; the sum is cut where an
explicit bound on its tail is below 2^-481, and the bound is added to the
ball's radius. The expansion was checked, before any field was computed,
against 4 zeta(2) G for m^2 + n^2 (G Catalan's constant) and against
6 zeta(2) L(2, chi_{-3}) for m^2 + m n + n^2, both to 137 digits, and against
a brute-force sum for two forms that are not norm forms of a maximal order.

For a totally real cubic field (D > 0) the value is the functional equation
zeta_K(2) = -8 pi^6 zeta_K(-1) / D^{3/2} applied to the exact rational
zeta_K(-1) = -S/63, S a positive integer, from Siegel's formula as the table
of zeta_K(1 - 2m) for these fields (numberdb.org/T161) computes it: S sums
sigma-like divisor sums over the totally positive elements of trace 1 in the
codifferent. That rational is compared with PARI's lfun at s = -1 recognised
with denominator at most 10^20, and the generator refuses the field if the
two differ.

**Every value is compared with PARI's lfun at s = 2 before it is returned**,
computed at 110 digits from the Dirichlet coefficients and the functional
equation of zeta_K, sharing no code with either route; the two must agree
to 100 digits, and a value for which they do not is an error rather than an
entry. For the seven cyclic fields the value is also compared with
zeta(2) |L(2, chi)|^2, chi a cubic Dirichlet character of conductor sqrt(D),
computed from the Hurwitz zeta function in ball arithmetic.

**The enumeration is a theorem, and it is checked against OEIS.** By Hunter's
theorem (Cohen, A Course in Computational Algebraic Number Theory, Thm 6.4.2)
every cubic field of discriminant D contains an algebraic integer, not in Z,
of trace 0 or 1 whose conjugates have sum of squared absolute values at most
1/3 + (2/sqrt 3)(|D|/3)^(1/2); its minimal polynomial x^3 + a2 x^2 + a1 x + a0
then has a2 in {0, -1}, |a1| <= 18 and |a0| <= 43 for |D| <= 3000, and it
generates the field. Every polynomial in that box is tried, and the fields
found are collected by their reduced polynomial. The generator refuses to run
unless it finds 419 complex and 96 totally real fields, the counts of OEIS
A023679 and A006832 up to 3000 read from their b-files with multiplicity.

**What the entry comments carry.** The reduced polynomial, the Galois group,
the class number (PARI's bnfinit, certified by bnfcertify) and the LMFDB
label, as the tables of regulators and residues do; for a totally real field
the exact zeta_K(-1) the value was computed from; for a cyclic field the
Conrey label of a cubic character chi with zeta_K(2) = zeta(2)|L(2, chi)|^2;
for a pure cubic field its name Q(m^(1/3)); and for D = -23 the volume of
the Weeks manifold, 3 * 23^{3/2} zeta_K(2) / (4 pi^4).
"""

import sys
from math import floor, gcd, sqrt

import numberdb.sage as numberdb
import sage.rings.polynomial.laurent_polynomial_ring  # noqa: F401
import sage.rings.real_mpfr  # noqa: F401
from sage.arith.misc import divisors, moebius
from sage.libs.pari import pari
from sage.matrix.constructor import matrix
from sage.modules.free_module_element import vector
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField
from sage.rings.real_mpfr import RealField

#: Bits of working precision beyond what the written digits need, 461 bits in
#: all. Measured on 2026-09-07 over every field: the widest ball, at
#: D = -2991 (h(D) = 48 forms), has radius 3.9e-137 and so supports 136
#: digits, and 100 are written.
WORKING_GUARD = 128

#: Every cubic field with |D| up to here is listed: the range of the tables of
#: regulators and residues, 515 fields.
BOUND = 3000

#: The counts the enumeration must reproduce: the terms of OEIS A023679
#: (discriminants of complex cubic fields, negated) and A006832 (totally real)
#: up to BOUND, counted with multiplicity from the b-files.
EXPECTED = {'complex': 419, 'totally real': 96}

#: Decimal digits to which each value and PARI's lfun must agree on every
#: entry. lfun is asked for LFUN_DIGITS digits.
AGREE_DIGITS = 100
LFUN_DIGITS = 110

#: Siegel's coefficient b_1(6) = -1/504: zeta_K(-1) = 8 b_1(6) S_1^K(2) for a
#: totally real cubic field (Louboutin 2004, and the table of zeta_K(1-2m)).
SIEGEL_B1 = QQ(-1) / QQ(504)

#: Denominator bound for recognising PARI's lfun at s = -1 as a rational, a
#: wide bound used only for the check; the exact route makes it 63.
LFUN_DENOMINATOR_BOUND = ZZ(10) ** 20

R = PolynomialRing(QQ, 'x')
x = R.gen()


# ----------------------------------------------------------------- the fields

def hunter_box(bound):
    """Every monic cubic that Hunter's theorem allows a generator of a cubic
    field with |D| <= bound to have; see the module docstring."""
    t2 = 1.0 / 3 + (2 / sqrt(3)) * sqrt(bound / 3.0)
    a1_max = int(floor((1 + t2) / 2)) + 1
    a0_max = int(floor((t2 / 3) ** 1.5)) + 1
    for a2 in (0, -1):
        for a1 in range(-a1_max, a1_max + 1):
            for a0 in range(-a0_max, a0_max + 1):
                if a0 != 0:
                    yield x ** 3 + a2 * x ** 2 + a1 * x + a0


_FIELDS = {}


def cubic_fields(bound=BOUND):
    """{D: [f_1, f_2, ...]}: the reduced polynomials of the cubic fields of
    discriminant D with |D| <= bound, in the order that defines k: lexicographic
    on the coefficient vector (a2, a1, a0) of PARI's polredabs."""
    if bound in _FIELDS:
        return _FIELDS[bound]
    found = {}
    for f in hunter_box(bound):
        g = pari(f)
        if not g.polisirreducible():
            continue
        D = ZZ(g.nfdisc())
        if abs(D) > bound:
            continue
        reduced = tuple(QQ(c) for c in g.polredabs().Vecrev())
        if len(reduced) != 4 or reduced[3] != 1 or any(c.denominator() != 1 for c in reduced):
            raise ArithmeticError('polredabs of %s is not a monic integral cubic: %s' % (f, reduced))
        found.setdefault(D, set()).add(tuple(ZZ(c) for c in reduced[:3]))
    table = {D: [R([a0, a1, a2, 1]) for (a0, a1, a2) in sorted(polys, key=lambda c: (c[2], c[1], c[0]))]
             for D, polys in found.items()}
    counts = {'complex': sum(len(v) for D, v in table.items() if D < 0),
              'totally real': sum(len(v) for D, v in table.items() if D > 0)}
    if bound == BOUND and counts != EXPECTED:
        raise ArithmeticError('the box found %s fields, and OEIS A023679/A006832 list %s' % (counts, EXPECTED))
    _FIELDS[bound] = table
    return table


_NF = {}
_FIELD_INFO = {}


def nf_of(f):
    key = str(f)
    if key not in _NF:
        _NF[key] = pari(f).nfinit()
    return _NF[key]


def field_info(f):
    """(D, h_K, galois_order) for the field of the reduced polynomial f, the
    class number certified: bnfinit(f, 1) computes it under GRH and bnfcertify
    proves it unconditionally, or fails."""
    key = str(f)
    if key not in _FIELD_INFO:
        g = pari(f)
        bnf = g.bnfinit(1)
        if bnf.bnfcertify() != 1:
            raise ArithmeticError('bnfcertify did not certify the field of %s' % f)
        D = ZZ(g.nfdisc())
        order = ZZ(g.polgalois()[0])
        if (order == 3) != D.is_square():
            raise ArithmeticError('D = %s and Galois group of order %s disagree for %s' % (D, order, f))
        _FIELD_INFO[key] = (D, ZZ(bnf.bnf_get_no()), order)
    return _FIELD_INFO[key]


def _finite(ball):
    if not ball.is_finite():
        raise ArithmeticError('a value came back as a ball that is not finite')
    return ball


# ------------------------------------------------- complex fields: forms

def reduced_forms(D):
    """The primitive reduced forms (a, b, c) of discriminant D < 0, one per
    class: |b| <= a <= c, gcd(a, b, c) = 1, and b >= 0 if |b| = a or a = c."""
    forms = []
    a = 1
    while 3 * a * a <= -D:
        for b in range(-a, a + 1):
            if (b - D) % 2:
                continue
            num = b * b - D
            if num % (4 * a):
                continue
            c = num // (4 * a)
            if c < a:
                continue
            if gcd(gcd(a, abs(b)), c) != 1:
                continue
            if (abs(b) == a or a == c) and b < 0:
                continue
            forms.append((a, b, c))
        a += 1
    h = int(pari.qfbclassno(D))
    if len(forms) != h:
        raise ArithmeticError('D = %s: %d reduced forms found, and qfbclassno says %d' % (D, len(forms), h))
    return forms


def epstein_at_2(form, RB):
    """Z_Q(2) = sum' Q(m,n)^-2 as a ball, by the Chowla-Selberg expansion of
    the module docstring, the tail of the Bessel sum bounded explicitly.

    For n > N the n-th term is at most n^{3/2} zeta(3) K_{3/2}(2 pi n y) <=
    C n r^n with r = e^{-2 pi y} and C = zeta(3)(1 + 1/(2 pi y))/(2 sqrt y),
    and sum_{n>N} n r^n = r^{N+1}((N+1) - N r)/(1-r)^2 exactly.
    """
    a, b, c = form
    D = b * b - 4 * a * c
    absD = RB(-D)
    y = absD.sqrt() / (2 * a)
    pi = RB.pi()
    zeta3 = RB(3).zeta()
    zeta4 = pi ** 4 / 90
    total = 2 * zeta4 * y * y + pi * zeta3 / y
    r = (-2 * pi * y).exp()
    C = zeta3 / (2 * y.sqrt()) * (1 + 1 / (2 * pi * y))
    cutoff = RB(2) ** (-RB.precision() - 20)
    s = RB(0)
    n = 0
    while True:
        n += 1
        z = 2 * pi * n * y
        bessel = (pi / (2 * z)).sqrt() * (-z).exp() * (1 + 1 / z)
        sigma = sum((RB(1) / RB(d) ** 3 for d in divisors(n)), RB(0))
        s += RB(n).sqrt() ** 3 * sigma * bessel * (pi * n * b / RB(a)).cos()
        tail = C * r ** (n + 1) * ((n + 1) - n * r) / (1 - r) ** 2
        if tail < cutoff:
            break
    s = s + RB(0).add_error(tail)
    return _finite(4 / absD * (total + 8 * pi * pi * y.sqrt() * s))


def represented_primes(form, D, how_many=2):
    """The smallest primes not dividing D that the form represents."""
    a, b, c = form
    found = set()
    for m in range(-40, 41):
        for n in range(0, 41):
            v = a * m * m + b * m * n + c * n * n
            if v > 1 and D % v != 0 and ZZ(v).is_prime():
                found.add(v)
    if len(found) < how_many:
        raise ArithmeticError('the form %s of discriminant %s represents too few small primes' % (form, D))
    return sorted(found)[:how_many]


def epsilon(nf, form, D):
    """1 if the primes represented by the form split completely in K, -1/2 if
    they stay prime. Two represented primes are looked at and must agree; a
    prime with two factors in K would be inert in Q(sqrt D), which a prime
    represented by a primitive form of discriminant D never is."""
    eps = None
    for p in represented_primes(form, D):
        if pari.kronecker(D, p) != 1:
            raise ArithmeticError('p = %s is represented by %s but is not split in Q(sqrt %s)' % (p, form, D))
        k = len(pari.idealprimedec(nf, p))
        if k == 3:
            e = QQ(1)
        elif k == 1:
            e = QQ(-1) / 2
        else:
            raise ArithmeticError('p = %s has %d primes above it in the field of discriminant %s' % (p, k, D))
        if eps is None:
            eps = e
        elif eps != e:
            raise ArithmeticError('two primes represented by %s decompose differently, D = %s' % (form, D))
    return eps


def sturm_bound(D):
    """|D| prod_{p | D} (1 + 1/p) / 12, rounded up: the Sturm bound for
    weight 1 on Gamma_0(|D|)."""
    N = ZZ(-D)
    idx = QQ(N)
    for p in N.prime_divisors():
        idx *= (1 + QQ(1) / p)
    return int((idx / 12).ceil())


def representation_numbers(form, B):
    """r_Q(n) = #{(m, n') : Q(m, n') = n} for 0 <= n <= B."""
    a, b, c = form
    D = b * b - 4 * a * c
    counts = [0] * (B + 1)
    nmax = int(floor(sqrt(4.0 * a * B / (-D)))) + 1
    for n in range(-nmax, nmax + 1):
        disc = b * b * n * n - 4 * a * (c * n * n - B)
        if disc < 0:
            continue
        root = sqrt(disc)
        lo = int(floor((-b * n - root) / (2 * a))) - 1
        hi = int(floor((-b * n + root) / (2 * a))) + 1
        for m in range(lo, hi + 1):
            v = a * m * m + b * m * n + c * n * n
            if 0 <= v <= B:
                counts[v] += 1
    return counts


def artin_coefficients(nf, B):
    """The Dirichlet coefficients of zeta_K(s)/zeta(s) up to B: those of
    zeta_K from PARI, convolved with the Moebius function."""
    a = [ZZ(0)] + [ZZ(v) for v in pari.dirzetak(nf, B)]
    return [ZZ(0)] + [sum(moebius(d) * a[n // d] for d in divisors(n)) for n in range(1, B + 1)]


def check_forms_against_field(nf, forms, eps, D):
    """The Sturm check: (1/2) sum_C eps(C) r_{Q_C}(n) equals the n-th
    coefficient of zeta_K/zeta for every n up to the Sturm bound plus five."""
    B = sturm_bound(D) + 5
    expected = artin_coefficients(nf, B)
    coefficients = [QQ(0)] * (B + 1)
    for form in forms:
        counts = representation_numbers(form, B)
        for n in range(B + 1):
            coefficients[n] += eps[form] * counts[n] / 2
    if coefficients[0] != 0:
        raise ArithmeticError('D = %s: the constant term is %s, so the theta combination is not a cusp form'
                              % (D, coefficients[0]))
    for n in range(1, B + 1):
        if coefficients[n] != expected[n]:
            raise ArithmeticError('D = %s: coefficient %d is %s from the forms and %s from zeta_K/zeta'
                                  % (D, n, coefficients[n], expected[n]))
    return B


def zeta_2_complex(f, D, bits):
    """zeta(2) L(2, rho) as a ball, L(2, rho) = (1/2) sum_C eps(C) Z_{Q_C}(2)."""
    nf = nf_of(f)
    forms = reduced_forms(D)
    eps = {form: epsilon(nf, form, D) for form in forms}
    kernel = sum(1 for e in eps.values() if e == 1)
    if 3 * kernel != len(forms):
        raise ArithmeticError('D = %s: %d of %d classes split completely; a cubic character has a kernel of index 3'
                              % (D, kernel, len(forms)))
    check_forms_against_field(nf, forms, eps, D)
    RB = RealBallField(bits)
    L = RB(0)
    for form in forms:
        L += eps[form] * epstein_at_2(form, RB) / 2
    return _finite(RB.pi() ** 2 / 6 * L)


# ------------------------------------------- totally real fields: Siegel

def as_ZZ(value):
    return ZZ(str(value))


def as_QQ(value):
    return QQ(str(value))


def pari_col(entries):
    return pari('[%s]~' % ','.join(str(QQ(entry)) for entry in entries))


def codiff_matrix(nf):
    return matrix(QQ, pari.idealinv(nf, nf.nf_get_diff()).sage())


def basis_embeddings(nf, basis_cols):
    RR = RealField(160)
    rows = []
    for i in range(3):
        row = []
        for col in basis_cols:
            elt = pari.nfbasistoalg(nf, pari_col(col))
            embedding = pari.nfeltembed(nf, elt)
            text = str(embedding[i])
            row.append(RR(QQ(text)) if '/' in text else RR(text))
        rows.append(row)
    return matrix(RR, rows)


def coefficient_bounds(embeddings, ell):
    """Bounds for the codifferent-basis coefficients of a totally positive
    element of trace ell: the vertices of the cube [0, ell]^3 pulled back."""
    RR = embeddings.base_ring()
    inverse = embeddings.inverse()
    bounds = [0, 0, 0]
    for vertex in ((RR(a), RR(b), RR(c)) for a in (0, ell) for b in (0, ell) for c in (0, ell)):
        coeffs = inverse * vector(RR, vertex)
        for j in range(3):
            bounds[j] = max(bounds[j], int(abs(coeffs[j]).ceil()) + 4)
    return bounds


def ideal_factor_data(nf, ideal):
    fac = pari.idealfactor(nf, ideal)
    data = []
    for i in range(int(fac.matsize()[0])):
        e = int(fac[i, 1])
        if e < 0:
            raise ArithmeticError('an ideal divisor exponent is negative')
        data.append((as_ZZ(pari.idealnorm(nf, fac[i, 0])), e))
    return data


def positive_trace_factors(nf, ell):
    """The factorisations of (nu) D_{K/Q} for the totally positive nu in the
    codifferent with trace ell."""
    codiff = codiff_matrix(nf)
    basis_cols = [codiff.column(j) for j in range(3)]
    basis_elts = [pari.nfbasistoalg(nf, pari_col(col)) for col in basis_cols]
    traces = [as_QQ(pari.nfelttrace(nf, elt)) for elt in basis_elts]
    bounds = coefficient_bounds(basis_embeddings(nf, basis_cols), ell)
    pivot = max((j for j in range(3) if traces[j] != 0), key=lambda j: bounds[j])
    free = [j for j in range(3) if j != pivot]
    factors = []
    for c_first in range(-bounds[free[0]], bounds[free[0]] + 1):
        for c_second in range(-bounds[free[1]], bounds[free[1]] + 1):
            coeffs = [ZZ(0), ZZ(0), ZZ(0)]
            coeffs[free[0]] = ZZ(c_first)
            coeffs[free[1]] = ZZ(c_second)
            remaining = QQ(ell) - sum(QQ(coeffs[j]) * traces[j] for j in free)
            c_pivot = remaining / traces[pivot]
            if c_pivot.denominator() != 1 or abs(c_pivot) > bounds[pivot]:
                continue
            coeffs[pivot] = ZZ(c_pivot)
            col = vector(QQ, [0, 0, 0])
            for j in range(3):
                col += QQ(coeffs[j]) * basis_cols[j]
            elt = pari.nfbasistoalg(nf, pari_col([col[i] for i in range(3)]))
            if [int(sign) for sign in pari.nfeltsign(nf, elt)] == [1, 1, 1]:
                factors.append(ideal_factor_data(nf, pari.idealmul(nf, elt, nf.nf_get_diff())))
    return factors


def divisor_norm_sum(factors, exponent):
    total = ZZ(1)
    for q, e in factors:
        total *= sum(q ** (exponent * j) for j in range(e + 1))
    return total


_ZETA_MINUS_ONE = {}


def zeta_minus_one(f):
    """zeta_K(-1) = 8 b_1(6) S_1^K(2) exactly, S_1^K(2) the sum of
    sigma_1(N) over the ideals of the module docstring, checked against
    PARI's lfun at s = -1."""
    key = str(f)
    if key not in _ZETA_MINUS_ONE:
        nf = nf_of(f)
        S = sum((divisor_norm_sum(data, 1) for data in positive_trace_factors(nf, 1)), ZZ(0))
        value = QQ(8) * SIEGEL_B1 * S
        if value >= 0:
            raise ArithmeticError('zeta_K(-1) = %s is not negative for %s' % (value, f))
        if 63 % value.denominator() != 0:
            raise ArithmeticError('the denominator of zeta_K(-1) = %s does not divide 63 for %s' % (value, f))
        pari.set_real_precision(LFUN_DIGITS)
        other = as_QQ(pari('bestappr(lfun(lfuncreate(%s), -1), %s)' % (f, LFUN_DENOMINATOR_BOUND)))
        if other != value:
            raise ArithmeticError('for %s, Siegel gives zeta_K(-1) = %s and PARI lfun gives %s' % (f, value, other))
        _ZETA_MINUS_ONE[key] = value
    return _ZETA_MINUS_ONE[key]


def zeta_2_totally_real(f, D, bits):
    """-8 pi^6 zeta_K(-1) / D^{3/2} as a ball."""
    RB = RealBallField(bits)
    return _finite(-8 * RB.pi() ** 6 * RB(zeta_minus_one(f)) / RB(D).sqrt() ** 3)


# ----------------------------------------------------------- the checks

def zeta_2_lfun(f, digits=LFUN_DIGITS):
    """zeta_K(2) as PARI's lfun computes it from the Dirichlet coefficients
    and the functional equation. The string form of the call is used because
    cypari2's method form computes at PARI's default 38 digits whatever
    set_real_precision says."""
    pari.set_real_precision(digits)
    return RealBallField(numberdb.bits(digits))(str(pari('lfun(lfuncreate(%s), 2)' % f)))


def cubic_conrey_index(q):
    """The smaller Conrey index n of the two cubic Dirichlet characters of
    conductor q: n^3 = 1 mod q, n != 1."""
    q = ZZ(q)
    for n in range(2, q):
        if ZZ(n).gcd(q) == 1 and pow(n, 3, q) == 1:
            return n
    raise ArithmeticError('no cubic character of conductor %s' % q)


def cyclic_zeta_2(q, bits):
    """zeta(2) |L(2, chi)|^2 for the cubic character chi = chi_q(n, .),
    L(2, chi) = q^-2 sum_a chi(a) zeta(2, a/q) from the Hurwitz zeta
    function in balls; chi(a) is read from PARI as a fraction of a turn."""
    RB = RealBallField(bits)
    n = cubic_conrey_index(q)
    real, imag = RB(0), RB(0)
    for a in range(1, q):
        if ZZ(a).gcd(q) != 1:
            continue
        turn = as_QQ(pari('chareval(znstar(%d,1), znconreychar(znstar(%d,1), %d), Mod(%d,%d))' % (q, q, n, a, q)))
        angle = 2 * RB.pi() * RB(turn)
        hurwitz = RB(2).zeta(RB(a) / q)
        real += angle.cos() * hurwitz
        imag += angle.sin() * hurwitz
    return _finite(RB.pi() ** 2 / 6 * (real * real + imag * imag) / RB(q) ** 4)


# -------------------------------------------------------------- comments

#: The LMFDB's index for the seventeen fields here that share a discriminant
#: with another, read from each field's LMFDB page on 2026-09-06 for the
#: table of residues (the page shows the same reduced polynomial). For every
#: other discriminant with |D| <= 3000 the LMFDB holds one field, of index 1.
LMFDB_INDEX = {
    (-972, 1): 1, (-972, 2): 2,
    (-1228, 1): 1, (-1228, 2): 2, (-1228, 3): 3,
    (-1356, 1): 1, (-1356, 2): 3, (-1356, 3): 2,
    (-1836, 1): 1, (-1836, 2): 2,
    (-2075, 1): 3, (-2075, 2): 2, (-2075, 3): 1,
    (-2188, 1): 1, (-2188, 2): 3, (-2188, 3): 2,
    (-2891, 1): 2, (-2891, 2): 3, (-2891, 3): 1,
}


def lmfdb_label(D, k, multiplicity):
    signature = '3.1' if D < 0 else '3.3'
    if multiplicity == 1:
        index = 1
    elif (int(D), int(k)) in LMFDB_INDEX:
        index = LMFDB_INDEX[(int(D), int(k))]
    else:
        raise ArithmeticError('D = %s carries %d fields and the LMFDB index of k = %s was never read'
                              % (D, multiplicity, k))
    return '%s.%d.%d' % (signature, abs(int(D)), index)


def poly_latex(u, var='x'):
    coefficients = [ZZ(c) for c in u.list()]
    terms = []
    for i in range(len(coefficients) - 1, -1, -1):
        n = coefficients[i]
        if n == 0:
            continue
        power = '' if i == 0 else (var if i == 1 else '%s^%d' % (var, i))
        magnitude = abs(n)
        body = ('' if magnitude == 1 and i > 0 else str(magnitude)) + power
        terms.append(('-' if n < 0 else ('+' if terms else '')) + body)
    return ''.join(terms) or '0'


def pure_cubic_radicand(D, f):
    """The least m with K = Q(m^(1/3)), for a field of discriminant -3 f^2;
    recognised by nfisisom, since the reduced polynomial is not always x^3 - m."""
    for m in range(2, 1000):
        if any(m % p ** 3 == 0 for p in range(2, 10)):
            continue
        g = pari('x^3-%d' % m)
        if pari.nfdisc(g) == D and pari.nfisisom(g, pari(f)) != 0:
            return m
    raise ArithmeticError('D = %s is -3 times a square, but no x^3 - m with m < 1000 gives the field of %s'
                          % (D, f))


def cyclic_name(q):
    return {7: r'$K=\mathbb{Q}(\zeta_7)^+$', 9: r'$K=\mathbb{Q}(\zeta_9)^+$'}.get(
        int(q), r'the cubic subfield of $\mathbb{Q}(\zeta_{%d})$' % q)


def comment(D, k, f, h, order, multiplicity):
    parts = ['$%s=0$' % poly_latex(f)]
    parts.append('$C_3$, conductor $%d$' % ZZ(D).sqrt() if order == 3 else '$S_3$')
    parts.append('$h_K=%d$' % h)
    parts.append('LMFDB %s' % lmfdb_label(D, k, multiplicity))
    if D > 0:
        parts.append(r'$\zeta_K(-1)=%s$' % zeta_minus_one(f))
    if order == 3:
        q = ZZ(D).sqrt()
        parts.append(r'%s; $\zeta_K(2)=\zeta(2)|L(2,\chi)|^2$ for $\chi=\chi_{%d}(%d,\cdot)$'
                     % (cyclic_name(q), q, cubic_conrey_index(q)))
    if D < 0 and D % 3 == 0 and ZZ(-D // 3).is_square():
        parts.append(r'$K=\mathbb{Q}(\sqrt[3]{%d})$, a pure cubic field' % pure_cubic_radicand(D, f))
    if int(D) == -23:
        parts.append(r'the Weeks manifold has volume $3\cdot 23^{3/2}\zeta_K(2)/(4\pi^4)=0.9427\ldots$')
    return '; '.join(parts)


# ----------------------------------------------------------- the generator

class CubicZetaAtTwo(numberdb.Generator):

    table = 'T162'
    parameters = ('D', 'k')
    type = 'R'
    digits = 100
    rigour = 'proven'

    def enumerate(self, bound=BOUND):
        fields = cubic_fields(bound)
        for D in sorted(fields, key=lambda d: (abs(d), d)):
            for k in range(1, len(fields[D]) + 1):
                yield {'D': int(D), 'k': k}

    def value(self, params, digits):
        D, k = ZZ(params['D']), ZZ(params['k'])
        fields = cubic_fields()
        if D not in fields or not 1 <= k <= len(fields[D]):
            raise ValueError('no cubic field with D = %s, k = %s and |D| <= %d' % (D, k, BOUND))
        f = fields[D][k - 1]
        field_D, h, order = field_info(f)
        if field_D != D:
            raise ArithmeticError('the field of %s has D = %s, not %s' % (f, field_D, D))
        bits = numberdb.bits(digits, losing=WORKING_GUARD)
        if D < 0:
            value = zeta_2_complex(f, D, bits)
        else:
            value = zeta_2_totally_real(f, D, bits)
        tolerance = RealBallField(64)(10) ** (-AGREE_DIGITS)
        check = zeta_2_lfun(f)
        if not (value - check).abs() < tolerance:
            raise ArithmeticError(
                'D = %s, k = %s: this generator gives %s and PARI lfun %s; '
                'neither is right until the disagreement has a cause' % (D, k, value, check))
        if order == 3:
            other = cyclic_zeta_2(ZZ(D).sqrt(), bits)
            if not (value.overlaps(other) and (value - other).abs() < tolerance):
                raise ArithmeticError('D = %s: the functional equation gives %s and zeta(2)|L(2,chi)|^2 gives %s'
                                      % (D, value, other))
        return {'number': value,
                'comment': comment(D, k, f, h, order, len(fields[D]))}


if __name__ == '__main__':
    generator = CubicZetaAtTwo()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='zeta_K(2) for the 515 cubic fields with |D| <= %d: complex fields from Epstein zeta '
                    'functions of the forms of discriminant D with the identity checked to the Sturm '
                    'bound, totally real fields from the functional equation and the exact zeta_K(-1), '
                    'every value checked to 100 digits against PARI lfun' % BOUND))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
