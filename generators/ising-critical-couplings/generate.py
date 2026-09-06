"""Critical couplings of the Ising model on lattices -- numberdb.org/T154

For the nearest-neighbour ferromagnetic Ising model on an infinite lattice,
with energy E = -J sum s_i s_j over the edges and spins s_i = +/-1, the
critical coupling is K_c = J/(k_B T_c), T_c the Curie temperature. The table
holds K_c and its reciprocal k_B T_c/J on the eleven Archimedean lattices,
their eight Laves duals, and the simple cubic, body-centred cubic,
face-centred cubic and diamond lattices: 23 rows, 46 entries, with two
parameters, `lattice` and `expression`.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**Two kinds of entry.** The 38 entries of the planar lattices are exact and
are computed here in ball arithmetic at 100 digits. For an Archimedean
lattice, v_c = tanh K_c is the unique root in (0, 1) of the polynomial
P(v) that Codello (J. Phys. A 43, 2010, Table 2) obtains from the
Feynman-Vdovichenko random-walk matrix; the root is enclosed by requiring
P to change sign across an interval of half-width 10^-(digits+5) around
the closed form's value, so that the enclosure is proved by the polynomial
and the closed form only says where to look. K_c = artanh v_c and
k_B T_c/J = 1/K_c follow in balls. Each Laves lattice is the planar dual of
an Archimedean lattice and takes its coupling from Kramers-Wannier duality,
K_c^* = -(1/2) ln tanh K_c. The 8 entries of the cubic lattices are not
computed: K_c is a published estimate, written as `centre +/- radius` with
the paper's stated uncertainty as the radius, and k_B T_c/J is its
reciprocal in exact decimal arithmetic with the uncertainty propagated;
each such entry declares the number of digits its radius supports.

**What was checked outside this file** before any entry was sent: every
planar value against Codello's printed k_B T_c/J and k_B T_c^*/J; every
Archimedean value against the Ising critical polynomials of Jacobsen
(J. Phys. A 47, 2014), a transfer-matrix computation sharing no method
with Codello's, which vanish at e^{2 K_c} - 1 and give the cube-root closed
forms of the (3^4,6) and (3^2,4,3,4) values; the square and honeycomb
couplings against OEIS A245592 and A329247 and against half the regulators
of Q(sqrt 2) and Q(sqrt 3) in the corpus; the values Codello found first,
for (4,6,12), (3,4,6,4) and (3^4,6), against the Monte Carlo estimates of
Malarz, Zborek and Wrobel and of Lima, Mostowicz and Malarz; and the cubic
estimates against the text of the paper cited, the body-centred cubic one
against Lundow and Campbell, who quote 0.1573725(5) from Butera and Comi's
series (whose own Table II prints (10)) and two Monte Carlo studies.
"""

import sys
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_EVEN, getcontext

import numberdb.sage as numberdb
from numberdb._compare import digits_of
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField
from sage.rings.real_mpfr import RealField

#: Bits of working precision beyond what the written digits need. Measured
#: over the 38 exact entries at 100 digits: the widest ball relative to its
#: value, k_B T_c/J of the triangular lattice, has relative radius 3.9e-105,
#: which is the half-width 10^-105 of the root enclosure carried through.
WORKING_GUARD = 64

#: The date on which the sources of the cubic estimates were read; the
#: estimates are records and move.
AS_OF = '6 September 2026'

#: The lattices, in the order the table lists them: the Archimedean lattices
#: by vertex configuration, the Laves lattices as D(...) of the Archimedean
#: lattice each is dual to, then the cubic lattices.
ARCHIMEDEAN = [
    'square', 'triangular', 'honeycomb', 'kagome', '3-12-12', '4-6-12', '4-8-8',
    '3-4-6-4', '3-3-3-3-6', '3-3-4-3-4', '3-3-3-4-4',
]
LAVES = [
    'D-3-3-4-3-4', 'D-3-3-3-4-4', 'D-3-3-3-3-6', 'D-3-6-3-6', 'D-3-4-6-4',
    'D-4-8-8', 'D-4-6-12', 'D-3-12-12',
]
CUBIC = ['sc', 'bcc', 'fcc', 'diamond']
LATTICES = ARCHIMEDEAN + LAVES + CUBIC

#: The Archimedean lattice each Laves lattice is dual to. The square lattice
#: is self-dual and the triangular and honeycomb lattices are dual to each
#: other, so those three have no Laves row.
DUAL = {
    'D-3-3-4-3-4': '3-3-4-3-4', 'D-3-3-3-4-4': '3-3-3-4-4', 'D-3-3-3-3-6': '3-3-3-3-6',
    'D-3-6-3-6': 'kagome', 'D-3-4-6-4': '3-4-6-4', 'D-4-8-8': '4-8-8',
    'D-4-6-12': '4-6-12', 'D-3-12-12': '3-12-12',
}

#: Codello's polynomials P(v), Table 2 of arXiv:1008.4720, reduced to the
#: one factor with a root in (0, 1); coefficients in ascending powers of
#: v = tanh K. The other factors of his P(v) have no root in (0, 1).
POLYNOMIAL = {
    'square': [1, -2, -1],
    'triangular': [1, -4, 1],
    'honeycomb': [1, 0, -3],
    'kagome': [1, 0, -4, 0, -6, 0, -4, 0, 1],
    '3-12-12': [1, -2, 3, -2, -2],
    '4-6-12': [1, 0, -2, 0, 2, 0, -10, 0, 1],
    '4-8-8': [1, 0, 0, -4, -1],
    '3-4-6-4': [1, 0, -4, 0, -6, 0, -4, 0, 1],
    '3-3-3-3-6': [1, -4, 7, -12, 3, 0, -3],
    '3-3-4-3-4': [1, -2, -1, -4, -9, 6, -7],
    '3-3-3-4-4': [1, -3],
}

#: The coordination number z of each lattice, for the mean-field bound
#: K_c > 1/z that every row must satisfy.
COORDINATION = {
    'square': 4, 'triangular': 6, 'honeycomb': 3, 'kagome': 4, '3-12-12': 3, '4-6-12': 3,
    '4-8-8': 3, '3-4-6-4': 4, '3-3-3-3-6': 5, '3-3-4-3-4': 5, '3-3-3-4-4': 5,
    'D-3-3-4-3-4': 4, 'D-3-3-3-4-4': 5, 'D-3-3-3-3-6': 6, 'D-3-6-3-6': 6, 'D-3-4-6-4': 6,
    'D-4-8-8': 8, 'D-4-6-12': 12, 'D-3-12-12': 12,
    'sc': 6, 'bcc': 8, 'fcc': 12, 'diamond': 4,
}

#: The transcribed couplings of the cubic lattices, (centre, radius, source):
#: the paper's value with its stated uncertainty in the last digits.
MEASURED = {
    'sc': ('0.221654626', '5e-9', 'FXL'),
    'bcc': ('0.1573725', '5e-7', 'LundowCampbell'),
    'fcc': ('0.102069', '1e-6', 'LundowCampbell'),
    'diamond': ('0.3697398', '1e-7', 'LundowCampbell'),
}

#: Addresses in the corpus, read off search results and the tables' pages.
REGULATORS = 'Regulators_of_real_quadratic_fields'
QUADRATIC = 'Algebraic_numbers_of_degree_2'

#: The Archimedean lattices as phrases, for the Laves comments.
DUAL_NAME = {
    '3-3-4-3-4': r'the snub square lattice $(3^2,4,3,4)$',
    '3-3-3-4-4': r'the elongated triangular lattice $(3^3,4^2)$',
    '3-3-3-3-6': r'the snub hexagonal lattice $(3^4,6)$',
    'kagome': r'the kagome lattice $(3,6,3,6)$',
    '3-4-6-4': r'the rhombitrihexagonal lattice $(3,4,6,4)$',
    '4-8-8': r'the truncated square lattice $(4,8^2)$',
    '4-6-12': r'the truncated trihexagonal lattice $(4,6,12)$',
    '3-12-12': r'the truncated hexagonal lattice $(3,12^2)$',
}

#: Codello's k_B T_c/J for the Laves lattices (his T_c^*, Table 3), quoted
#: in their comments.
CODELLO_DUAL = {
    'D-3-12-12': '5.0071', 'D-4-6-12': '4.1363', 'D-4-8-8': '3.9310', 'D-3-4-6-4': '2.4055',
    'D-3-6-3-6': '2.4055', 'D-3-3-3-3-6': '1.8757', 'D-3-3-3-4-4': '1.8205', 'D-3-3-4-3-4': '1.7992',
}

_CACHE = {}


def closed_form(lattice, RBF):
    """v_c = tanh K_c as a ball from its closed form: Codello's Table 3 for
    nine lattices, and for the two he left as decimals the cube-root forms
    of Jacobsen (arXiv:1401.7847, equations 48 and 53), which give
    u = e^{2K_c} - 1 = (w^{1/3} - 2 w^{-1/3} - 2)/3 and so v = u/(u+2)."""
    s2, s3 = RBF(2).sqrt(), RBF(3).sqrt()
    if lattice == 'square':
        return s2 - 1
    if lattice == 'triangular':
        return 2 - s3
    if lattice == 'honeycomb':
        return 1 / s3
    if lattice in ('kagome', '3-4-6-4'):
        return RBF(1) / 2 - (s3 / 2).sqrt() + s3 / 2
    if lattice == '3-12-12':
        return -RBF(1) / 4 - s3 / 4 + (3 + 5 * s3 / 2).sqrt() / 2
    if lattice == '4-6-12':
        return ((5 + 3 * s3 - (44 + 26 * s3).sqrt()) / 2).sqrt()
    if lattice == '4-8-8':
        return -1 - 1 / s2 + ((5 + 4 * s2) / 2).sqrt()
    if lattice == '3-3-3-4-4':
        return RBF(QQ(1) / 3)
    if lattice == '3-3-4-3-4':
        w = 37 + 27 * s2 + 3 * (315 + 222 * s2).sqrt()
    elif lattice == '3-3-3-3-6':
        w = 37 + 27 * s3 + 3 * (6 * (66 + 37 * s3)).sqrt()
    else:
        raise ValueError('no closed form for %s' % lattice)
    c = w ** (QQ(1) / 3)
    u = (c - 2 / c - 2) / 3
    return u / (u + 2)


def polynomial_at(lattice, v):
    p = v.parent()(0)
    for coefficient in reversed(POLYNOMIAL[lattice]):
        p = p * v + coefficient
    return p


def sign_of(ball):
    """+1 or -1 for a ball that does not contain zero; None otherwise."""
    if ball.contains_zero():
        return None
    return 1 if ball > 0 else -1


def root_enclosure(lattice, bits, digits):
    """A ball of radius 10^-(digits+5) around the closed form's value, proved
    to contain the root of P by a sign change of P across its ends, and
    proved to be the root in (0, 1) by P having no other sign change there."""
    key = (lattice, bits, digits)
    if key in _CACHE:
        return _CACHE[key]
    RBF = RealBallField(bits)
    RR = RealField(bits)
    guess = closed_form(lattice, RBF)
    if not guess.is_finite() or not (0 < guess < 1):
        raise ArithmeticError('%s: the closed form is not a finite ball in (0, 1): %s' % (lattice, guess))
    m = RR(guess.mid())
    w = RR(10) ** (-(digits + 5))
    lo, hi = sign_of(polynomial_at(lattice, RBF(m - w))), sign_of(polynomial_at(lattice, RBF(m + w)))
    if lo is None or hi is None or lo == hi:
        raise ArithmeticError('%s: P(v) does not change sign across %s +/- %s' % (lattice, m, w))
    enclosure = RBF(m).add_error(w)
    if not enclosure.overlaps(guess):
        raise ArithmeticError('%s: the closed form %s is not inside the enclosure %s' % (lattice, guess, enclosure))
    #No other root in (0, 1). On a margin of half-width 2^-10 around m the
    #derivative P' keeps one sign, so P is monotone there and the sign
    #change is one root; outside the margin P is nonzero on every piece of
    #a covering of [0, 1], pieces being split where a ball contains zero,
    #down to a width below which the doubt is treated as a root.
    margin = RR(2) ** (-10)
    if derivative_at(lattice, RBF(m).add_error(margin)).contains_zero():
        raise ArithmeticError('%s: P\'(v) may vanish within %s of the root' % (lattice, margin))
    for a, b in ((RR(0), m - margin), (m + margin, RR(1))):
        nonzero_on(lattice, a, b, RR(2) ** (-40))
    _CACHE[key] = enclosure
    return enclosure


def derivative_at(lattice, v):
    p = v.parent()(0)
    coefficients = POLYNOMIAL[lattice]
    for k in range(len(coefficients) - 1, 0, -1):
        p = p * v + k * coefficients[k]
    return p


def nonzero_on(lattice, a, b, narrowest):
    """Raise unless P is proved nonzero on [a, b], by ball evaluation on
    pieces split wherever the ball contains zero."""
    stack = [(a, b)]
    while stack:
        lo, hi = stack.pop()
        RBF = RealBallField(lo.parent().precision())
        piece = RBF((lo + hi) / 2).add_error((hi - lo) / 2)
        if not polynomial_at(lattice, piece).contains_zero():
            continue
        if hi - lo < narrowest:
            raise ArithmeticError('%s: P(v) may vanish again on [%s, %s]' % (lattice, lo, hi))
        mid = (lo + hi) / 2
        stack.append((lo, mid))
        stack.append((mid, hi))


def reciprocal_text(centre, radius):
    """1/(centre +/- radius) as `centre +/- radius`, in decimal arithmetic:
    the reciprocal of the interval, its midpoint rounded so that the
    rounding is a tenth of the width, and the radius rounded up to two
    significant digits."""
    getcontext().prec = 60
    c, r = Decimal(centre), Decimal(radius)
    if r <= 0 or c <= r:
        raise ValueError('%s +/- %s is not a positive interval' % (centre, radius))
    lo, hi = 1 / (c + r), 1 / (c - r)
    half = (hi - lo) / 2
    places = -half.adjusted() + 1
    mid = ((lo + hi) / 2).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_EVEN)
    rad = max(hi - mid, mid - lo)
    rad = rad.quantize(Decimal(1).scaleb(rad.adjusted() - 1), rounding=ROUND_CEILING)
    if not (mid - rad <= lo and hi <= mid + rad):
        raise ArithmeticError('the rounded interval %s +/- %s does not contain [%s, %s]' % (mid, rad, lo, hi))
    return ('%s +/- %s' % (mid, rad.normalize())).lower()


def quoted(centre, radius):
    """The value as the paper prints it, `0.221654626(5)`."""
    c, r = Decimal(centre), Decimal(radius)
    places = -c.as_tuple().exponent
    err = r.scaleb(places)
    if err != err.to_integral_value():
        raise ValueError('radius %s is not a whole number of units in the last place of %s' % (radius, centre))
    return '$%s(%d)$' % (centre, int(err))


class Row(object):
    """One lattice: its coupling and temperature, as balls or as strings,
    and the comment on each."""

    def __init__(self, lattice):
        if lattice not in LATTICES:
            raise ValueError('no row for the lattice %r' % lattice)
        self.lattice = lattice

    def coupling(self, bits, digits):
        RBF = RealBallField(bits)
        if self.lattice in ARCHIMEDEAN:
            v = root_enclosure(self.lattice, bits, digits)
            K = ((1 + v) / (1 - v)).log() / 2
        elif self.lattice in LAVES:
            v = root_enclosure(DUAL[self.lattice], bits, digits)
            K = -v.log() / 2
        else:
            centre, radius, _ = MEASURED[self.lattice]
            if Decimal(radius) <= 0 or not (0 < Decimal(centre) < 1):
                raise ValueError('%s: %s +/- %s is not a coupling with a positive uncertainty' % (self.lattice, centre, radius))
            return '%s +/- %s' % (centre, radius)
        if not K.is_finite() or not (0 < K < 2):
            raise ArithmeticError('%s: K_c came out as %s' % (self.lattice, K))
        return K

    def temperature(self, bits, digits):
        if self.lattice in CUBIC:
            centre, radius, _ = MEASURED[self.lattice]
            return reciprocal_text(centre, radius)
        return 1 / self.coupling(bits, digits)

    def entry(self, expression, bits, digits):
        if expression == 'coupling':
            number = self.coupling(bits, digits)
        elif expression == 'temperature':
            number = self.temperature(bits, digits)
        else:
            raise ValueError('expression must be coupling or temperature, not %r' % expression)
        if isinstance(number, str):
            value = Decimal(number.split(' +/- ')[0])
        else:
            value = Decimal(str(number.mid()))
        z = COORDINATION[self.lattice]
        if expression == 'coupling' and not value * z > 1:
            raise ArithmeticError('%s: K_c = %s violates the mean-field bound K_c > 1/%d' % (self.lattice, number, z))
        if expression == 'temperature' and not value < z:
            raise ArithmeticError('%s: k_B T_c/J = %s violates the mean-field bound T_c < %d J/k_B' % (self.lattice, number, z))
        entry = {'number': number, 'comment': COMMENT[self.lattice][0 if expression == 'coupling' else 1]}
        if isinstance(number, str):
            entry['digits'] = digits_of(number)
        return entry


def laves_comments(lattice):
    dual = DUAL[lattice]
    return (
        r'$K_c=-\frac12\ln\tanh K_c(L)$ with $L$ %s, its planar dual, by Kramers–Wannier duality '
        r'CITE{KW} CITE{formula-duality}.' % DUAL_NAME[dual],
        r'$k_BT_c/J=-2/\ln\tanh K_c(L)$ with $L$ %s; Codello gives $%s$ CITE{Codello}.'
        % (DUAL_NAME[dual], CODELLO_DUAL[lattice]))


#: (comment on K_c, comment on k_B T_c/J) for each row.
COMMENT = {
    'square': (
        r'$K_c=\frac12\ln(1+\sqrt2)=\frac12\operatorname{arsinh}1$, found by Kramers and Wannier from '
        r"self-duality CITE{KW} and confirmed by Onsager's solution CITE{Onsager}, OEIS A245592 "
        r'CITE{OEISsq}; $\tanh K_c=\sqrt2-1$ is in the HREF{%s#1,2,-1,2}[table of quadratic '
        r'irrationals], and $K_c$ is half the HREF{%s#8}[regulator of $\mathbb{Q}(\sqrt2)$].'
        % (QUADRATIC, REGULATORS),
        r'$k_BT_c/J=2/\ln(1+\sqrt2)$, OEIS A169800 CITE{OEISsqT}.'),
    'triangular': (
        r'$K_c=\frac14\ln3$ CITE{Wannier} CITE{Houtappel}; $\tanh K_c=2-\sqrt3$ is in the '
        r'HREF{%s#1,-4,1,1}[table of quadratic irrationals].' % QUADRATIC,
        r'$k_BT_c/J=4/\ln3$.'),
    'honeycomb': (
        r'$K_c=\frac12\ln(2+\sqrt3)=\frac12\operatorname{arcosh}2$ CITE{Houtappel}, OEIS A329247 CITE{OEIShc}; '
        r'$\tanh K_c=1/\sqrt3$ is in the HREF{%s#3,0,-1,2}[table of quadratic irrationals], and $K_c$ is '
        r'half the HREF{%s#12}[regulator of $\mathbb{Q}(\sqrt3)$].' % (QUADRATIC, REGULATORS),
        r'$k_BT_c/J=2/\ln(2+\sqrt3)$; the honeycomb lattice is also called the hexagonal lattice, a name that in '
        r'crystallography belongs to the triangular lattice.'),
    'kagome': (
        r'$K_c=\frac14\ln(3+2\sqrt3)$ CITE{KanoNaya}, so that $e^{4K_c}=3+2\sqrt3$ and '
        r'$\tanh K_c=\frac12-\sqrt{\frac{\sqrt3}{2}}+\frac{\sqrt3}{2}$; the same value as on $(3,4,6,4)$ CITE{Codello}.',
        r'$k_BT_c/J=4/\ln(3+2\sqrt3)$.'),
    '3-12-12': (
        r'$\tanh K_c=-\frac14-\frac{\sqrt3}{4}+\frac12\sqrt{3+\frac{5\sqrt3}{2}}$, the root in $(0,1)$ of '
        r'$1-2v+3v^2-2v^3-2v^4$ CITE{Syozi} CITE{Codello}; the lattice is also called the extended kagome '
        r'or three-twelve lattice.',
        r'$k_BT_c/J=1/K_c$; Codello gives $1.2315$ CITE{Codello}.'),
    '4-6-12': (
        r'$\tanh K_c=\sqrt{\frac{5+3\sqrt3-\sqrt{44+26\sqrt3}}{2}}$, the root in $(0,1)$ of '
        r'$1-2v^2+2v^4-10v^6+v^8$, found by Codello CITE{Codello}; the Monte Carlo estimate '
        r'$k_BT_c/J\approx1.40$ CITE{Malarz} preceded it.',
        r'$k_BT_c/J=1/K_c$; Codello gives $1.3898$ CITE{Codello}.'),
    '4-8-8': (
        r'$\tanh K_c=-1-\frac1{\sqrt2}+\sqrt{\frac{5+4\sqrt2}{2}}$, the root in $(0,1)$ of $1-4v^3-v^4$ '
        r'CITE{Utiyama} CITE{Codello}, so that $e^{2K_c}=1+\frac{1+\sqrt{5+4\sqrt2}}{\sqrt2}$ CITE{Jacobsen}; '
        r'the lattice is also called the bathroom-tile or four-eight lattice.',
        r'$k_BT_c/J=1/K_c$; Codello gives $1.4387$ CITE{Codello}.'),
    '3-4-6-4': (
        r'$K_c=\frac14\ln(3+2\sqrt3)$, the same value as on the kagome lattice, because the two '
        r'polynomials $P(v)$ share the factor $1-4v^2-6v^4-4v^6+v^8$ CITE{Codello}; found by Codello, '
        r"and confirmed by Jacobsen's critical polynomials CITE{Jacobsen} and by the Monte Carlo estimates "
        r'$k_BT_c/J\approx2.15$ CITE{Malarz} and $2.145(3)$ CITE{Lima}. The lattice is also called the ruby '
        r'lattice.',
        r'$k_BT_c/J=4/\ln(3+2\sqrt3)$.'),
    '3-3-3-3-6': (
        r'$\tanh K_c$ is the root in $(0,1)$ of $1-4v+7v^2-12v^3+3v^4-3v^6$, found by Codello CITE{Codello}, '
        r'and $e^{2K_c}=1+\frac13\left(\omega^{1/3}-2\omega^{-1/3}-2\right)$ with '
        r'$\omega=37+27\sqrt3+3\sqrt{6(66+37\sqrt3)}$ CITE{Jacobsen}; the Monte Carlo estimates are '
        r'$k_BT_c/J\approx2.80$ CITE{Malarz} and $2.784(3)$ CITE{Lima}. The lattice is also called the snub '
        r'hexagonal or maple-leaf lattice.',
        r'$k_BT_c/J=1/K_c$; Codello gives $2.7858$ CITE{Codello}.'),
    '3-3-4-3-4': (
        r'$\tanh K_c$ is the root in $(0,1)$ of $1-2v-v^2-4v^3-9v^4+6v^5-7v^6$ CITE{ThompsonWardrop} '
        r'CITE{Codello}, and $e^{2K_c}=1+\frac13\left(\omega^{1/3}-2\omega^{-1/3}-2\right)$ with '
        r'$\omega=37+27\sqrt2+3\sqrt{315+222\sqrt2}$ CITE{Jacobsen}; the lattice is also called the snub '
        r'square or Shastry–Sutherland lattice.',
        r'$k_BT_c/J=1/K_c$; Codello gives $2.9263$ CITE{Codello}.'),
    '3-3-3-4-4': (
        r'$K_c=\frac12\ln2$, since $\tanh K_c=\frac13$ CITE{ThompsonWardrop} CITE{Codello}; the lattice is '
        r'also called the elongated triangular or trellis lattice.',
        r'$k_BT_c/J=2/\ln2$.'),
    'sc': (
        r'%s CITE{FXL}, from Monte Carlo simulations with the Wolff cluster algorithm on lattices of up to '
        r'$1024^3$ sites; the high-temperature-series value $0.221655(2)$ CITE{ButeraComi} agrees.'
        % quoted('0.221654626', '5e-9'),
        r'$k_BT_c/J=1/K_c$, the reciprocal of the entry for $K_c$ with its uncertainty propagated.'),
    'bcc': (
        r'%s as quoted by Lundow and Campbell CITE{LundowCampbell} from the high-temperature series of '
        r'Butera and Comi CITE{ButeraComi} and the Monte Carlo simulations CITE{LMR} CITE{MuraseIto}; '
        r"Butera and Comi's own Table II prints $0.1573725(10)$." % quoted('0.1573725', '5e-7'),
        r'$k_BT_c/J=1/K_c$, the reciprocal of the entry for $K_c$ with its uncertainty propagated.'),
    'fcc': (
        r'%s from Monte Carlo simulations CITE{LMR} CITE{MuraseIto}, as quoted by Lundow and Campbell '
        r'CITE{LundowCampbell}.' % quoted('0.102069', '1e-6'),
        r'$k_BT_c/J=1/K_c$, the reciprocal of the entry for $K_c$ with its uncertainty propagated.'),
    'diamond': (
        r'%s from Monte Carlo simulations CITE{DengBlote} CITE{LMR}, as quoted by Lundow and Campbell '
        r'CITE{LundowCampbell}.' % quoted('0.3697398', '1e-7'),
        r'$k_BT_c/J=1/K_c$, the reciprocal of the entry for $K_c$ with its uncertainty propagated.'),
}
for _lattice in LAVES:
    COMMENT[_lattice] = laves_comments(_lattice)


class IsingCriticalCouplings(numberdb.Generator):

    table = 'T154'
    parameters = ('lattice', 'expression')
    type = 'R'
    digits = 100
    #: `heuristic` for the four transcribed cubic estimates, each one
    #: computation in its paper with an uncertainty chosen by its authors;
    #: `measured` is for values that come from experiment. The 38 planar
    #: entries are proven enclosures, and the rigour details say which is which.
    rigour = 'heuristic'

    def enumerate(self):
        for lattice in LATTICES:
            for expression in ('coupling', 'temperature'):
                yield {'lattice': lattice, 'expression': expression}

    def value(self, params, digits):
        bits = numberdb.bits(digits, losing=WORKING_GUARD)
        return Row(params['lattice']).entry(params['expression'], bits, digits)


if __name__ == '__main__':
    generator = IsingCriticalCouplings()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='critical couplings K_c = J/(k_B T_c) and k_B T_c/J of the Ising model on the eleven '
                    'Archimedean lattices, their Laves duals and the four cubic lattices: the planar values '
                    'exact, as roots of Codello\'s polynomials enclosed in ball arithmetic at 100 digits, the '
                    'cubic values the most precise published estimates as of %s with their stated '
                    'uncertainties' % AS_OF))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
