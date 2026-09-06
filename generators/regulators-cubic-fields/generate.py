"""Regulators of cubic fields -- numberdb.org/T158

    R_K = | det( log|sigma_i(eps_j)| )_{i,j <= r} |

for every cubic field K with |D| <= 3000, D the discriminant of K. For a
complex cubic field (D < 0) the unit rank r is 1, sigma_1 is the one real
embedding and eps_1 is a fundamental unit; for a totally real one (D > 0)
r = 2, sigma_1, sigma_2 are any two of the three real embeddings and
eps_1, eps_2 a fundamental pair. Fields sharing a discriminant are told apart
by an index k, the position of the field's reduced polynomial (PARI's
polredabs) in lexicographic order of its coefficient vector.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**These digits are proven.** The units come from PARI's bnfinit and are
certified by bnfcertify, which removes the assumption of the generalised
Riemann hypothesis that bnfinit makes; a field on which bnfcertify does not
return 1 is an error rather than an entry. Each unit is then taken exactly, as
a polynomial in a root a of the reduced polynomial with rational coefficients,
checked to be an algebraic integer of norm +-1, and evaluated at the real
root(s) of the polynomial isolated in interval arithmetic; the logarithms and
the 2 x 2 determinant are arb's, so the digits written are those the ball
supports. PARI's floating regulator `bnf.reg` is not used for the value.

**The enumeration is a theorem, and it is checked against OEIS.** By Hunter's
theorem (Cohen, A Course in Computational Algebraic Number Theory, Thm 6.4.2)
every cubic field of discriminant D contains an algebraic integer, not in Z,
of trace 0 or 1 whose conjugates have sum of squared absolute values at most
1/3 + (2/sqrt 3)(|D|/3)^(1/2); its minimal polynomial x^3 + a2 x^2 + a1 x + a0
then has a2 in {0, -1}, |a1| <= 18 and |a0| <= 43 for |D| <= 3000, and it
generates the field, since a cubic field has no proper subfield but Q. Every
polynomial in that box is tried, and the fields found are collected by their
reduced polynomial. The generator refuses to run unless it finds 419 complex
and 96 totally real fields, the counts of OEIS A023679 and A006832 up to 3000
read from their b-files with multiplicity; the per-discriminant comparison
with the b-files, Sage's own enumerate_totallyreal_fields_prim, PARI's
lfunrootres through the class number formula on every field, 21
regulators on LMFDB pages, OEIS A202539 and Wikipedia's example were run
outside the generator when this was written (see the table's rigour details).

**Two conventions had to be settled**, and both are stated on the table. For
D < 0 the unit in the entry comment is the one of +-eps^(+-1) whose real
embedding exceeds 1, so that R_K = log sigma(eps) with no absolute value; for
D > 0 the comment carries PARI's fundamental pair, each unit's sign chosen to
make its leading coefficient positive, since no pair is canonical. The value
does not depend on either choice. And the index k is defined here by the
reduced polynomial, because the LMFDB's rule for numbering fields of the same
discriminant could not be read; the LMFDB label in a comment is one that was
read off the field's LMFDB page.
"""

import sys
from math import floor, sqrt

import numberdb.sage as numberdb
from sage.libs.pari import pari
from sage.rings.integer_ring import ZZ
from sage.rings.number_field.number_field import NumberField
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField
from sage.rings.real_mpfi import RealIntervalField

#: Bits of working precision beyond what the written digits need, 461 bits in
#: all. Measured over the whole table at 100 digits on 2026-09-06: the worst
#: ball, D = 1772, has relative radius 2.8e-134 and supports 133 digits; the
#: complex fields all support 137 or more. Evaluating a unit whose coordinates
#: are large at an embedding where its value is small loses digits to
#: cancellation -- about twenty at D = -2991 before the unit was normalised to
#: exceed 1 -- and the guard is what absorbs the loss that remains in the
#: totally real case, where one of the three embeddings of a unit is small.
WORKING_GUARD = 128

#: Every cubic field with |D| up to here is listed. Nothing grows with D, so
#: the bound is a choice about what somebody looks up; 3000 is where the
#: proposal put it, with 515 fields.
BOUND = 3000

#: The counts the enumeration must reproduce: the terms of OEIS A023679
#: (discriminants of complex cubic fields, negated) and A006832 (totally real)
#: up to BOUND, counted with multiplicity from the b-files. A different count
#: means the box or the reduction is wrong, and the run stops.
EXPECTED = {'complex': 419, 'totally real': 96}

R = PolynomialRing(QQ, 'x')
x = R.gen()


def hunter_box(bound):
    """Every monic cubic that Hunter's theorem allows a generator of a cubic
    field with |D| <= bound to have.

    T2 <= 1/3 + (2/sqrt 3) (bound/3)^(1/2) bounds the sum of squared absolute
    values of the conjugates of a suitable generator of trace t in {0, 1};
    then |a1| = |e_2| <= (t^2 + T2)/2 and |a0| = |N| <= (T2/3)^(3/2). The
    bounds are computed in floating point and widened by one, which the box
    does not mind.
    """
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
    discriminant D with |D| <= bound, in the order that defines k.

    The order is lexicographic on the coefficient vector (a2, a1, a0) of the
    reduced polynomial x^3 + a2 x^2 + a1 x + a0, PARI's polredabs, so that
    for D = -1228 the fields are x^3 - x^2 + x - 7, x^3 - x^2 + 7x - 1,
    x^3 + 4x - 6 in that order.
    """
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


def field_data(f):
    """(K, h_K, units, galois_order) for the field of the reduced polynomial f,
    the units certified and checked.

    bnfinit(f, 1) computes the class group and a system of fundamental units
    under GRH; bnfcertify proves them right unconditionally, or fails. Each
    unit is rebuilt in Sage's number field from its polynomial and must be an
    algebraic integer of norm +-1 -- a check of the transcription, not of the
    certificate.
    """
    bnf = pari(f).bnfinit(1)
    if bnf.bnfcertify() != 1:
        raise ArithmeticError('bnfcertify did not certify the field of %s' % f)
    h = ZZ(bnf.bnf_get_no())
    K = NumberField(f, 'a')
    units = []
    for u in bnf.bnf_get_fu():
        coefficients = [QQ(c) for c in u.lift().Vecrev()]
        units.append(K(R(coefficients)))
    for u in units:
        if u.norm() not in (1, -1):
            raise ArithmeticError('%s has norm %s in the field of %s' % (u, u.norm(), f))
        if not u.is_integral():
            raise ArithmeticError('%s is not an algebraic integer in the field of %s' % (u, f))
    order = ZZ(pari(f).polgalois()[0])
    D = ZZ(pari(f).nfdisc())
    if (order == 3) != D.is_square():
        raise ArithmeticError('D = %s and Galois group of order %s disagree for %s' % (D, order, f))
    return K, h, units, order


def real_roots(f, bits):
    """The real roots of f as real balls, isolated in interval arithmetic."""
    RIF = RealIntervalField(bits)
    RB = RealBallField(bits)
    return [RB(r) for r in f.roots(RIF, multiplicities=False)]


def embed(u, root):
    """sigma(u) as a ball, u a polynomial in a with rational coefficients and
    root the ball of sigma(a): Horner's rule in balls."""
    RB = root.parent()
    value = RB(0)
    for c in reversed(u.polynomial().list()):
        value = value * root + RB(QQ(c))
    return value


def chosen_units(f, units, D):
    """The units the comment shows, and the regulator is computed from.

    D < 0: of eps, -eps, 1/eps, -1/eps exactly one has real embedding above
    1, and that one is taken -- as for the real quadratic fields -- so that
    R_K = log sigma(eps). D > 0: PARI's pair, each with the sign that makes
    its leading coefficient positive; no pair is canonical, and the value does
    not depend on the choice.
    """
    if D < 0:
        if len(units) != 1:
            raise ArithmeticError('expected one fundamental unit for D = %s, got %d' % (D, len(units)))
        roots = real_roots(f, 64)
        if len(roots) != 1:
            raise ArithmeticError('expected one real root of %s, found %d' % (f, len(roots)))
        u = units[0]
        chosen = [c for c in (u, -u, 1 / u, -1 / u) if embed(c, roots[0]) > 1]
        if len(chosen) != 1:
            raise ArithmeticError('%d of the conjugates of the unit exceed 1 for D = %s' % (len(chosen), D))
        return chosen
    if len(units) != 2:
        raise ArithmeticError('expected two fundamental units for D = %s, got %d' % (D, len(units)))
    return [u if u.polynomial().leading_coefficient() > 0 else -u for u in units]


def regulator(f, units, D, bits):
    """|det(log|sigma_i(eps_j)|)| as a real ball, from the definition."""
    roots = real_roots(f, bits)
    if D < 0:
        if len(roots) != 1:
            raise ArithmeticError('expected one real root of %s' % f)
        return _finite(embed(units[0], roots[0]).abs().log().abs())
    if len(roots) != 3:
        raise ArithmeticError('expected three real roots of %s' % f)
    logs = [[embed(u, r).abs().log() for u in units] for r in roots[:2]]
    return _finite((logs[0][0] * logs[1][1] - logs[0][1] * logs[1][0]).abs())


def _finite(ball):
    if not ball.is_finite():
        raise ArithmeticError('the regulator came back as a ball that is not finite')
    return ball


def poly_latex(u, var='a'):
    """A polynomial with rational coefficients, written the way a person
    would: integer coefficients if it has them, otherwise \\tfrac{1}{d}(...)
    with d the common denominator."""
    coefficients = [QQ(c) for c in u.list()]
    if not coefficients:
        return '0'
    d = ZZ(1)
    for c in coefficients:
        d = d.lcm(c.denominator())
    numerators = [ZZ(c * d) for c in coefficients]
    terms = []
    for i in range(len(numerators) - 1, -1, -1):
        n = numerators[i]
        if n == 0:
            continue
        power = '' if i == 0 else (var if i == 1 else '%s^%d' % (var, i))
        magnitude = abs(n)
        body = ('' if magnitude == 1 and i > 0 else str(magnitude)) + power
        terms.append(('-' if n < 0 else ('+' if terms else '')) + body)
    text = ''.join(terms)
    return text if d == 1 else r'\tfrac{1}{%d}(%s)' % (d, text)


#: The LMFDB's index for the seventeen fields here that share a discriminant
#: with another, read from each field's LMFDB page on 2026-09-06 (the page
#: shows the same reduced polynomial, so the match is exact). For every other
#: discriminant with |D| <= 3000 the LMFDB holds one field, of index 1. The
#: LMFDB's numbering is not the lexicographic order that defines k -- at
#: D = -2891 its first field is k = 3 here -- and its knowl nf.label states
#: no rule beyond "counting from 1", so the index is data, not a formula.
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


def named(D, f):
    """What a reader would recognise: the field or the unit, for the entries
    that have a name."""
    D = int(D)
    if D == -23:
        return (r'$\varepsilon=\rho$ is the plastic number, $\rho^3=\rho+1$, so '
                r'$R_K=\log\rho$, OEIS A202539')
    if D == 49:
        return r'$K=\mathbb{Q}(\zeta_7)^+$, the maximal real subfield of the seventh cyclotomic field'
    if D == 81:
        return r'$K=\mathbb{Q}(\zeta_9)^+$'
    if ZZ(D).is_square():
        return r'the cubic subfield of $\mathbb{Q}(\zeta_{%d})$' % ZZ(D).sqrt()
    coefficients = f.list()
    if coefficients[1] == 0 and coefficients[2] == 0:
        return r'$K=\mathbb{Q}(\sqrt[3]{%d})$, a pure cubic field' % (-coefficients[0])
    return None


def comment(D, k, f, h, units, order, multiplicity):
    parts = ['$%s=0$' % poly_latex(f)]
    parts.append('$C_3$, conductor $%d$' % ZZ(D).sqrt() if order == 3 else '$S_3$')
    parts.append('$h_K=%d$' % h)
    if D < 0:
        parts.append(r'$\varepsilon=%s$' % poly_latex(units[0]))
    else:
        parts.append(r'$\varepsilon_1=%s$, $\varepsilon_2=%s$' % (poly_latex(units[0]), poly_latex(units[1])))
    parts.append('LMFDB %s' % lmfdb_label(D, k, multiplicity))
    extra = named(D, f)
    if extra:
        parts.append(extra)
    return '; '.join(parts)


class CubicRegulators(numberdb.Generator):

    table = 'T158'
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
        K, h, units, order = field_data(f)
        units = chosen_units(f, units, D)
        bits = numberdb.bits(digits, losing=WORKING_GUARD)
        return {'number': regulator(f, units, D, bits),
                'comment': comment(D, k, f, h, units, order, len(fields[D]))}


if __name__ == '__main__':
    generator = CubicRegulators()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='regulators of the cubic fields with |D| <= %d from units certified by '
                    'bnfcertify, evaluated at the real roots of the reduced polynomial in '
                    'ball arithmetic' % BOUND))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
