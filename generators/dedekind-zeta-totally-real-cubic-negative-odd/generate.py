"""Values of Dedekind zeta functions of totally real cubic fields.

This is proposal 4 of agents/table-ideas/BATCH-2026-09-06T1042.md:

    zeta_K(s),  s = -1, -3, -5,

for every totally real cubic field K with discriminant D <= 5000. Fields with
the same discriminant are indexed by the lexicographic order of PARI's
polredabs reduced defining polynomial, the same convention used by T158 and
T159 for the cubic regulator and residue tables.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The values are exact rationals. They are computed from Siegel's finite formula
for totally real fields,

    zeta_K(1 - 2n) = 2^3 sum_l b_l(6n) S_l^K(2n),

where S_l^K(2n) sums N(I)^(2n-1) over integral ideals I dividing
(nu)D_{K/Q}, for totally positive nu in the codifferent with trace l. The
coefficients needed here are

    b_1(6)  = -1/504,
    b_1(12) =  1/8190,   b_2(12) =  1/196560,
    b_1(18) = -22/3591,  b_2(18) = -1/86184.

Before any table is filled, the constants are checked against exact
Dirichlet-character computations for Q(zeta_7)^+ and Q(zeta_9)^+. Every value
is also compared with PARI's lfun, recognized with denominator bound 10^20;
the exact formula coefficients imply much smaller denominators, so this is a
wide bound used only for the independent check.
"""

import os
import sys
from math import floor, sqrt

import numberdb.sage as numberdb
import sage.rings.polynomial.laurent_polynomial_ring  # noqa: F401
import sage.rings.real_mpfr  # noqa: F401
from sage.arith.misc import bernoulli, binomial
from sage.libs.pari import pari
from sage.matrix.constructor import matrix
from sage.modules.free_module_element import vector
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ
from sage.rings.real_mpfr import RealField


BOUND = 5000
EXPECTED_FIELDS = 173
ARGUMENTS = (-1, -3, -5)
LFUN_DIGITS = 120
LFUN_DENOMINATOR_BOUND = ZZ(10) ** 20
CHECK_LFUN = os.environ.get('NUMBERDB_SKIP_LFUN_CHECK') != '1'

SIEGEL_COEFFICIENTS = {
    1: (QQ(-1) / QQ(504),),
    2: (QQ(1) / QQ(8190), QQ(1) / QQ(196560)),
    3: (QQ(-22) / QQ(3591), QQ(-1) / QQ(86184)),
}

R = PolynomialRing(QQ, 'x')
x = R.gen()

_FIELDS = {}
_FIELD_INFO = {}
_NF = {}
_POSITIVE_FACTORS = {}
_ZETA_VALUES = {}
_CONSTANTS_CHECKED = False


def as_ZZ(value):
    return ZZ(str(value))


def as_QQ(value):
    return QQ(str(value))


def pari_col(entries):
    return pari('[%s]~' % ','.join(str(QQ(entry)) for entry in entries))


def hunter_box(bound):
    """Every monic cubic in the Hunter box for discriminants up to bound."""
    t2 = 1.0 / 3 + (2 / sqrt(3)) * sqrt(bound / 3.0)
    a1_max = int(floor((1 + t2) / 2)) + 1
    a0_max = int(floor((t2 / 3) ** 1.5)) + 1
    for a2 in (0, -1):
        for a1 in range(-a1_max, a1_max + 1):
            for a0 in range(-a0_max, a0_max + 1):
                if a0 != 0:
                    yield x ** 3 + a2 * x ** 2 + a1 * x + a0


def cubic_fields(bound=BOUND):
    """The reduced polynomials of totally real cubic fields, grouped by D."""
    if bound in _FIELDS:
        return _FIELDS[bound]
    found = {}
    for f in hunter_box(bound):
        g = pari(f)
        if not g.polisirreducible():
            continue
        D = ZZ(g.nfdisc())
        if not 0 < D <= bound:
            continue
        reduced = tuple(QQ(c) for c in g.polredabs().Vecrev())
        if len(reduced) != 4 or reduced[3] != 1 or any(c.denominator() != 1 for c in reduced):
            raise ArithmeticError('polredabs of %s is not a monic integral cubic: %s' % (f, reduced))
        found.setdefault(D, set()).add(tuple(ZZ(c) for c in reduced[:3]))
    table = {
        D: [
            R([a0, a1, a2, 1])
            for (a0, a1, a2) in sorted(polys, key=lambda c: (c[2], c[1], c[0]))
        ]
        for D, polys in found.items()
    }
    count = sum(len(v) for v in table.values())
    if bound == BOUND and count != EXPECTED_FIELDS:
        raise ArithmeticError('found %d totally real cubic fields; expected %d' % (count, EXPECTED_FIELDS))
    _FIELDS[bound] = table
    return table


def nf_of(poly):
    key = str(poly)
    if key not in _NF:
        _NF[key] = pari(poly).nfinit()
    return _NF[key]


def field_info(poly):
    """Return (D, h_K, galois_order), with the class number certified."""
    key = str(poly)
    if key not in _FIELD_INFO:
        g = pari(poly)
        bnf = g.bnfinit(1)
        if bnf.bnfcertify() != 1:
            raise ArithmeticError('bnfcertify did not certify the field of %s' % poly)
        D = ZZ(g.nfdisc())
        order = ZZ(g.polgalois()[0])
        if (order == 3) != D.is_square():
            raise ArithmeticError('D = %s and Galois group order %s disagree for %s' % (D, order, poly))
        _FIELD_INFO[key] = (D, ZZ(bnf.bnf_get_no()), order)
    return _FIELD_INFO[key]


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
    """Bounds for codifferent-basis coefficients of trace ell positives."""
    RR = embeddings.base_ring()
    inverse = embeddings.inverse()
    bounds = [0, 0, 0]
    for vertex in ((RR(a), RR(b), RR(c)) for a in (0, ell) for b in (0, ell) for c in (0, ell)):
        coeffs = inverse * vector(RR, vertex)
        for j in range(3):
            bounds[j] = max(bounds[j], int(abs(coeffs[j]).ceil()) + 4)
    return bounds


def positive_trace_factors(nf, poly, ell):
    """Ideal factorisations for the positive codifferent elements of trace ell."""
    key = (str(poly), int(ell))
    if key in _POSITIVE_FACTORS:
        return _POSITIVE_FACTORS[key]

    codiff = codiff_matrix(nf)
    basis_cols = [codiff.column(j) for j in range(3)]
    basis_elts = [pari.nfbasistoalg(nf, pari_col(col)) for col in basis_cols]
    traces = [as_QQ(pari.nfelttrace(nf, elt)) for elt in basis_elts]
    embeddings = basis_embeddings(nf, basis_cols)
    bounds = coefficient_bounds(embeddings, ell)
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
                ideal = pari.idealmul(nf, elt, nf.nf_get_diff())
                factors.append(ideal_factor_data(nf, ideal))

    _POSITIVE_FACTORS[key] = factors
    return factors


def ideal_factor_data(nf, ideal):
    fac = pari.idealfactor(nf, ideal)
    rows = int(fac.matsize()[0])
    data = []
    for i in range(rows):
        P = fac[i, 0]
        e = int(fac[i, 1])
        if e < 0:
            raise ArithmeticError('an ideal divisor exponent is negative')
        q = as_ZZ(pari.idealnorm(nf, P))
        data.append((q, e))
    return data


def divisor_norm_sum(factors, exponent):
    total = ZZ(1)
    for q, e in factors:
        total *= sum(q ** (exponent * j) for j in range(e + 1))
    return total


def siegel_sum(nf, poly, ell, n):
    total = ZZ(0)
    for factor_data in positive_trace_factors(nf, poly, ell):
        total += divisor_norm_sum(factor_data, 2 * n - 1)
    return total


def zeta_siegel(poly, n):
    nf = nf_of(poly)
    terms = (
        SIEGEL_COEFFICIENTS[n][ell - 1] * siegel_sum(nf, poly, ell, n)
        for ell in range(1, len(SIEGEL_COEFFICIENTS[n]) + 1)
    )
    return QQ(8) * sum(terms, QQ(0))


def zeta_lfun(poly, n):
    pari.set_real_precision(LFUN_DIGITS)
    value = pari('bestappr(lfun(lfuncreate(%s), %d), %s)' % (
        poly, 1 - 2 * n, LFUN_DENOMINATOR_BOUND))
    return as_QQ(value)


def zeta_values(poly):
    key = str(poly)
    if key not in _ZETA_VALUES:
        values = {}
        for n in (1, 2, 3):
            value = zeta_siegel(poly, n)
            if (n % 2 == 1 and value >= 0) or (n % 2 == 0 and value <= 0):
                raise ArithmeticError('unexpected sign for %s at s = %d: %s' % (poly, 1 - 2 * n, value))
            if CHECK_LFUN:
                other = zeta_lfun(poly, n)
                if value != other:
                    raise ArithmeticError(
                        'for %s at s = %d, Siegel gives %s and PARI lfun gives %s'
                        % (poly, 1 - 2 * n, value, other))
            values[1 - 2 * n] = value
        _ZETA_VALUES[key] = values
    return _ZETA_VALUES[key]


def bernoulli_polynomial_at(k, value):
    value = QQ(value)
    return sum(binomial(k, j) * bernoulli(j) * value ** (k - j)
               for j in range(k + 1))


def pair_add(z, w):
    return z[0] + w[0], z[1] + w[1]


def pair_mul(z, w):
    a, b = z
    c, d = w
    return a * c - b * d, a * d + b * c - b * d


def pair_scalar(q, z):
    return q * z[0], q * z[1]


def pair_conj(z):
    a, b = z
    return a - b, -b


def norm_pair(z):
    return pair_mul(z, pair_conj(z))[0]


def cubic_conrey_index(q):
    for n in range(2, q):
        if ZZ(n).gcd(q) == 1 and pow(n, 3, q) == 1:
            return n
    raise ArithmeticError('no cubic character of conductor %s' % q)


def char_pair(q, index, a):
    if ZZ(a).gcd(ZZ(q)) != 1:
        return QQ(0), QQ(0)
    value = as_QQ(pari('chareval(znstar(%d,1), znconreychar(znstar(%d,1), %d), Mod(%d,%d))'
                       % (q, q, index, a, q)))
    if value == 0:
        return QQ(1), QQ(0)
    if value == QQ(1) / QQ(3):
        return QQ(0), QQ(1)
    if value == QQ(2) / QQ(3):
        return QQ(-1), QQ(-1)
    raise ArithmeticError('unexpected character value %s for q = %s, index = %s, a = %s'
                          % (value, q, index, a))


def generalized_bernoulli_pair(k, q, index):
    total = (QQ(0), QQ(0))
    for a in range(1, q + 1):
        total = pair_add(
            total,
            pair_scalar(bernoulli_polynomial_at(k, QQ(a) / QQ(q)),
                        char_pair(q, index, a)))
    return pair_scalar(QQ(q) ** (k - 1), total)


def cyclic_zeta(q, n):
    k = 2 * n
    b_chi = generalized_bernoulli_pair(k, q, cubic_conrey_index(q))
    return -bernoulli(k) * norm_pair(b_chi) / QQ(k ** 3)


def check_siegel_coefficients():
    """Check the constants against exact cyclic cubic fields."""
    global _CONSTANTS_CHECKED
    if _CONSTANTS_CHECKED:
        return
    controls = {
        7: R([1, -2, -1, 1]),   # Q(zeta_7)^+, D = 49
        9: R([-1, -3, 0, 1]),   # Q(zeta_9)^+, D = 81
    }
    for q, poly in controls.items():
        for n in (1, 2, 3):
            from_siegel = zeta_siegel(poly, n)
            from_character = cyclic_zeta(q, n)
            if from_siegel != from_character:
                raise ArithmeticError(
                    'Siegel constants fail at q = %s, s = %d: %s != %s'
                    % (q, 1 - 2 * n, from_siegel, from_character))
    _CONSTANTS_CHECKED = True


def poly_latex(poly, var='x'):
    coefficients = [ZZ(c) for c in poly.list()]
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


def named_field(D, multiplicity):
    if not D.is_square():
        return None
    conductor = ZZ(D).sqrt()
    if conductor == 7:
        return r'$K=\mathbb{Q}(\zeta_7)^+$'
    if conductor == 9:
        return r'$K=\mathbb{Q}(\zeta_9)^+$'
    if multiplicity == 1:
        return r'the cubic subfield of $\mathbb{Q}(\zeta_{%d})$' % conductor
    return r'a cyclic cubic field of conductor $%d$' % conductor


def comment(D, poly, h, order, multiplicity):
    parts = ['$%s=0$' % poly_latex(poly)]
    if order == 3:
        parts.append('$C_3$, conductor $%d$' % ZZ(D).sqrt())
    else:
        parts.append('$S_3$')
    parts.append('$h_K=%d$' % h)
    name = named_field(D, multiplicity)
    if name:
        parts.append(name)
    return '; '.join(parts)


class TotallyRealCubicZetaNegativeOdd(numberdb.Generator):

    table = 'T161'
    parameters = ('D', 'k', 's')
    type = 'Q'
    rigour = 'exact'

    def __init__(self):
        check_siegel_coefficients()

    def enumerate(self, bound=BOUND):
        fields = cubic_fields(bound)
        for D in sorted(fields):
            for k in range(1, len(fields[D]) + 1):
                for s in ARGUMENTS:
                    yield {'D': int(D), 'k': k, 's': s}

    def value(self, params, digits):
        D, k, s = ZZ(params['D']), ZZ(params['k']), ZZ(params['s'])
        if s not in ARGUMENTS:
            raise ValueError('s must be one of %s, not %s' % (ARGUMENTS, s))
        fields = cubic_fields()
        if D not in fields or not 1 <= k <= len(fields[D]):
            raise ValueError('no totally real cubic field with D = %s, k = %s and D <= %d' % (D, k, BOUND))
        poly = fields[D][int(k) - 1]
        field_D, h, order = field_info(poly)
        if field_D != D:
            raise ArithmeticError('the field of %s has D = %s, not %s' % (poly, field_D, D))
        return {
            'number': zeta_values(poly)[int(s)],
            'comment': comment(D, poly, h, order, len(fields[D])),
        }


if __name__ == '__main__':
    generator = TotallyRealCubicZetaNegativeOdd()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='zeta_K(s) for totally real cubic fields with D <= %d and s = -1, -3, -5, '
                    'from exact Siegel sums checked against cyclic character values and PARI lfun'
                    % BOUND))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
