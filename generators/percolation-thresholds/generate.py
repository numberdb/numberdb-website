"""Site and bond percolation thresholds of lattices -- numberdb.org/T152

For an infinite lattice graph, site percolation with parameter p keeps each
vertex independently with probability p and bond percolation keeps each edge;
the percolation threshold p_c is the value of p above which an infinite
connected component of kept vertices (or kept edges) exists almost surely and
below which it does not. The table holds p_c for site and bond percolation on
the eleven Archimedean lattices, their eight Laves duals, the simple cubic,
body-centred cubic, face-centred cubic and diamond lattices, and the
hypercubic lattices Z^d for 4 <= d <= 13: 66 entries, with three parameters,
`lattice`, `d` (the dimension) and `percolation` (site or bond).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**Two kinds of entry.** Eleven thresholds are known exactly and are
computed here in ball arithmetic at 100 digits from their closed forms:
1/2 (five rows, returned as the exact rational), 2 sin(pi/18),
1 - 2 sin(pi/18) (two rows) and sqrt(1 - 2 sin(pi/18)). The other 55 are
the most precise published estimates as of 6 September 2026, transcribed
with the paper's stated uncertainty and written as `centre +/- radius`, the
form the table of the fine-structure constant uses; each such entry
declares the number of digits its radius supports. The eight Laves bond
thresholds are 1 - p_c^bond of the dual Archimedean lattice, computed here
in exact decimal arithmetic from the Archimedean value with the same
radius. `MEASURED` below holds every transcribed value with its source, so
that updating a threshold is one line and one citation.

**Where the values come from.** Wikipedia's table of percolation thresholds,
which carries a reference for every value, was read on the date above and
the most precise value of each row was compared with the paper it cites:
Scullard and Jacobsen 2020 (Table I) for the nine unsolved Archimedean bond
thresholds, Jacobsen 2014 (Tables 51-57) and Suding and Ziff 1999 for the
planar site thresholds, Parviainen's dissertation (Table 4.3) for three
Laves site thresholds, Xu, Wang, Lv and Deng 2014 (Table V) for the four
cubic lattices, and Mertens and Moore 2018 (Table II) for the hypercubic
lattices. The square-lattice site threshold is the one row where the
published determinations disagree beyond their stated errors, in the
twelfth decimal; its entry is an interval containing all four of them.

**What was checked outside this file** before any entry was sent: the three
closed forms against OEIS A130880, A178959 and A174849 to every digit those
entries list, and against their minimal polynomials x^3 - 3x + 1,
x^3 - 3x^2 + 1 and x^6 - 3x^4 + 1 by a sign change across each written
enclosure; every transcribed value against the text of the paper cited;
the duality relation between each Laves bond row and its Archimedean dual;
the inequalities 1/(z-1) <= p_c^bond <= p_c^site <= 1 - (1 - p_c^bond)^z
on every lattice, with z the coordination number; and the 1/(2d-1) series
of Mertens and Moore against the hypercubic rows.
"""

import sys
from decimal import Decimal

import numberdb.sage as numberdb
from numberdb._compare import digits_of
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField

#: Bits of working precision beyond what the written digits need. Measured
#: over the four closed forms at 100 digits: the widest ball relative to its
#: value, 2 sin(pi/18), has relative radius 1.1e-119.
WORKING_GUARD = 64

#: The date on which the sources were read; the estimates are records and
#: move.
AS_OF = '6 September 2026'

#: The lattices, in the order the table lists them, with the dimension.
#: Archimedean lattices are named by their vertex configuration, the Laves
#: lattices as D(...) of the Archimedean lattice they are dual to.
LATTICES = [
    ('square', 2), ('triangular', 2), ('honeycomb', 2), ('kagome', 2),
    ('3-12-12', 2), ('4-6-12', 2), ('4-8-8', 2), ('3-4-6-4', 2),
    ('3-3-3-3-6', 2), ('3-3-4-3-4', 2), ('3-3-3-4-4', 2),
    ('D-3-3-4-3-4', 2), ('D-3-3-3-4-4', 2), ('D-3-3-3-3-6', 2), ('D-3-6-3-6', 2),
    ('D-3-4-6-4', 2), ('D-4-8-8', 2), ('D-4-6-12', 2), ('D-3-12-12', 2),
    ('sc', 3), ('bcc', 3), ('fcc', 3), ('diamond', 3),
] + [('hypercubic', d) for d in range(4, 14)]

#: The Laves lattice dual to each Archimedean lattice that is not self-dual
#: or dual to another Archimedean lattice (the square lattice is self-dual;
#: the triangular and honeycomb lattices are dual to each other).
DUAL = {
    'D-3-3-4-3-4': '3-3-4-3-4', 'D-3-3-3-4-4': '3-3-3-4-4', 'D-3-3-3-3-6': '3-3-3-3-6',
    'D-3-6-3-6': 'kagome', 'D-3-4-6-4': '3-4-6-4', 'D-4-8-8': '4-8-8',
    'D-4-6-12': '4-6-12', 'D-3-12-12': '3-12-12',
}

#: The exact thresholds: which closed form each row is.
EXACT = {
    ('triangular', 'site'): 'half',
    ('square', 'bond'): 'half',
    ('D-4-8-8', 'site'): 'half',
    ('D-4-6-12', 'site'): 'half',
    ('D-3-12-12', 'site'): 'half',
    ('triangular', 'bond'): 'sin',
    ('honeycomb', 'bond'): 'one-minus-sin',
    ('kagome', 'site'): 'one-minus-sin',
    ('3-12-12', 'site'): 'sqrt',
}

#: The transcribed thresholds, (centre, radius) as the paper prints them,
#: with the reference key of the table document. The radius is the paper's
#: stated uncertainty in the last digits of the centre.
MEASURED = {
    #Archimedean lattices, site percolation
    ('square', 'site'): ('0.592746050788', '6e-12', None),    # see COMMENT: four determinations
    ('honeycomb', 'site'): ('0.697040230', '5e-9', 'Jacobsen14'),
    ('4-6-12', 'site'): ('0.7478008', '2e-7', 'Jacobsen14'),
    ('4-8-8', 'site'): ('0.7297232', '5e-7', 'Jacobsen14'),
    ('3-4-6-4', 'site'): ('0.62181207', '7e-8', 'Jacobsen14'),
    ('3-3-3-3-6', 'site'): ('0.579498', '3e-6', 'SudingZiff'),
    ('3-3-4-3-4', 'site'): ('0.550806', '3e-6', 'SudingZiff'),
    ('3-3-3-4-4', 'site'): ('0.550213', '3e-6', 'SudingZiff'),
    #Archimedean lattices, bond percolation
    ('kagome', 'bond'): ('0.52440499916744820', '1e-17', 'ScullardJacobsen'),
    ('3-12-12', 'bond'): ('0.740420798850811610', '2e-18', 'ScullardJacobsen'),
    ('4-6-12', 'bond'): ('0.693733124922', '2e-12', 'ScullardJacobsen'),
    ('4-8-8', 'bond'): ('0.6768031243900113', '3e-16', 'ScullardJacobsen'),
    ('3-4-6-4', 'bond'): ('0.524831461573', '1e-12', 'ScullardJacobsen'),
    ('3-3-3-3-6', 'bond'): ('0.4343283172240', '6e-13', 'ScullardJacobsen'),
    ('3-3-4-3-4', 'bond'): ('0.4141378565917', '1e-13', 'ScullardJacobsen'),
    ('3-3-3-4-4', 'bond'): ('0.41964035886369', '2e-14', 'ScullardJacobsen'),
    #Laves lattices, site percolation (the bond thresholds are derived)
    ('D-3-3-4-3-4', 'site'): ('0.6501834', '2e-7', 'Jacobsen14'),
    ('D-3-3-3-4-4', 'site'): ('0.6470471', '2e-7', 'Jacobsen14'),
    ('D-3-3-3-3-6', 'site'): ('0.639447', '5e-6', 'Parviainen'),
    ('D-3-6-3-6', 'site'): ('0.585040', '5e-6', 'Parviainen'),
    ('D-3-4-6-4', 'site'): ('0.582410', '5e-6', 'Parviainen'),
    #Cubic lattices
    ('sc', 'site'): ('0.31160768', '15e-8', 'XuWangLvDeng'),
    ('sc', 'bond'): ('0.24881185', '10e-8', 'XuWangLvDeng'),
    ('bcc', 'site'): ('0.2459615', '2e-7', 'XuWangLvDeng'),
    ('bcc', 'bond'): ('0.18028762', '20e-8', 'XuWangLvDeng'),
    ('fcc', 'site'): ('0.19923517', '20e-8', 'XuWangLvDeng'),
    ('fcc', 'bond'): ('0.12016377', '15e-8', 'XuWangLvDeng'),
    ('diamond', 'site'): ('0.4299870', '4e-7', 'XuWangLvDeng'),
    ('diamond', 'bond'): ('0.3895892', '5e-7', 'XuWangLvDeng'),
}

#: The hypercubic lattices Z^d, 4 <= d <= 13, from Table II of Mertens and
#: Moore 2018: d -> (centre, radius).
HYPERCUBIC_SITE = {
    4: ('0.19688561', '3e-8'), 5: ('0.14079633', '4e-8'), 6: ('0.109016661', '8e-9'),
    7: ('0.088951121', '1e-9'), 8: ('0.075210128', '1e-9'), 9: ('0.0652095348', '6e-10'),
    10: ('0.0575929488', '4e-10'), 11: ('0.0515896843', '2e-10'), 12: ('0.0467309755', '1e-10'),
    13: ('0.04271507960', '10e-11'),
}
HYPERCUBIC_BOND = {
    4: ('0.16013122', '6e-8'), 5: ('0.11817145', '3e-8'), 6: ('0.09420165', '2e-8'),
    7: ('0.078675230', '2e-9'), 8: ('0.0677084181', '3e-10'), 9: ('0.0594960034', '1e-10'),
    10: ('0.0530925842', '2e-10'), 11: ('0.04794968373', '8e-11'), 12: ('0.04372385825', '10e-11'),
    13: ('0.04018761703', '6e-11'),
}

#: The table of rational numbers holds 1/2 (address read off a search result).
RATIONALS = 'Rational_numbers'
#: The table of cos(pi x) holds cos(4 pi / 9) = sin(pi / 18) at x = 4/9.
COSINES = 'Cos_pi_times_x_at_rational_numbers'

#: What each Archimedean or Laves lattice is also called, for the comments.
ALSO = {
    '3-12-12': 'the three-twelve or truncated hexagonal lattice',
    '4-6-12': 'the cross or truncated trihexagonal lattice',
    '4-8-8': 'the four-eight, bathroom-tile or truncated square lattice',
    '3-4-6-4': 'the ruby or rhombitrihexagonal lattice',
    '3-3-3-3-6': 'the snub hexagonal or maple-leaf lattice',
    '3-3-4-3-4': 'the snub square, puzzle or Shastry–Sutherland lattice',
    '3-3-3-4-4': 'the frieze, trellis or elongated triangular lattice',
    'D-3-3-4-3-4': 'the Cairo pentagonal lattice',
    'D-3-3-3-4-4': 'the prismatic pentagonal lattice',
    'D-3-3-3-3-6': 'the floret pentagonal lattice',
    'D-3-6-3-6': 'the rhombille or dice lattice',
    'D-3-4-6-4': 'the deltoidal trihexagonal or ruby-dual lattice',
    'D-4-8-8': 'the tetrakis square or union-jack lattice',
    'D-4-6-12': 'the kisrhombille or bisected-hexagon lattice',
    'D-3-12-12': 'the triakis triangular or asanoha lattice',
}

#: The Archimedean lattice each Laves lattice is dual to, as a phrase.
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


def quoted(centre, radius):
    """The value as the paper prints it, `0.7478008(2)`: the uncertainty as
    an integer in the last digits of the centre."""
    c, r = Decimal(centre), Decimal(radius)
    places = -c.as_tuple().exponent
    err = r.scaleb(places)
    if err != err.to_integral_value():
        raise ValueError('radius %s is not a whole number of units in the last place of %s' % (radius, centre))
    return '$%s(%d)$' % (centre, int(err))


#: Entry comments for the rows with something particular to say; the rest
#: are built from the source in `MEASURED`.
COMMENT = {
    ('square', 'site'): (
        r'The published determinations disagree beyond their stated errors in the twelfth '
        r'decimal: $0.59274605079210(2)$ CITE{Jacobsen15} from the eigenvalue formulation of '
        r'critical polynomials, $0.592746050786(3)$ CITE{Mertens22} from the exact spanning '
        r'probabilities of $n\times n$ squares with $n\leq 24$, and $0.5927460507896(1)$ '
        r'CITE{YangZhou24} and $0.59274605079016(1)$ CITE{Jacobsen24}, the last two as quoted '
        r'in CITE{Wiki}. The entry is the interval $0.592746050788\pm 6\cdot 10^{-12}$, which '
        r'contains all four with their error bars; the first ten decimals, $0.5927460507$, are '
        r'OEIS A377420 CITE{OEISsquare}.'),
    ('triangular', 'site'): (
        r'$p_c=\frac12$, exact CITE{SykesEssam}: the triangular lattice is self-matching, so '
        r'its site threshold is $\frac12$ by the argument of Kesten CITE{Kesten}.'),
    ('honeycomb', 'site'): (
        r'%s CITE{Jacobsen14}, from critical polynomials on bases of up to $8$ unit cells; '
        r'the honeycomb lattice is also called the hexagonal lattice.' % quoted('0.697040230', '5e-9')),
    ('kagome', 'site'): (
        r'$p_c=1-2\sin\frac{\pi}{18}=1-2\cos\frac{4\pi}{9}$, exact CITE{SykesEssam}, the root '
        r'in $(0,1)$ of $x^3-3x^2+1$, OEIS A178959 CITE{OEISkagome}; it equals the bond '
        r'threshold of the honeycomb lattice, since the kagome lattice is the line graph of '
        r'the honeycomb lattice; $\cos\frac{4\pi}{9}$ is in the '
        r'HREF{%s#4/9}[table of $\cos(\pi x)$].' % COSINES),
    ('3-12-12', 'site'): (
        r'$p_c=\sqrt{1-2\sin\frac{\pi}{18}}$, exact CITE{SudingZiff}, the root in $(0,1)$ of '
        r'$x^6-3x^4+1$, OEIS A174849 CITE{OEIStt}: contracting the edges of $(3,12^2)$ that lie '
        r'in no triangle gives the kagome lattice, and a contracted edge is open when both of '
        r'its ends are, with probability $p^2$.'),
    ('square', 'bond'): (
        r'$p_c=\frac12$, exact: conjectured from series and self-duality by Sykes and Essam '
        r'CITE{SykesEssam} and proved by Kesten CITE{Kesten}.'),
    ('triangular', 'bond'): (
        r'$p_c=2\sin\frac{\pi}{18}=2\cos\frac{4\pi}{9}$, exact, the root in $(0,1)$ of '
        r'$x^3-3x+1$, OEIS A130880 CITE{OEIStri}; found by Sykes and Essam CITE{SykesEssam} '
        r'from the star–triangle transformation and proved by Wierman CITE{Wierman}; '
        r'$\cos\frac{4\pi}{9}$ is in the HREF{%s#4/9}[table of $\cos(\pi x)$].' % COSINES),
    ('honeycomb', 'bond'): (
        r'$p_c=1-2\sin\frac{\pi}{18}$, exact, the root in $(0,1)$ of $x^3-3x^2+1$, OEIS '
        r'A178959 CITE{OEISkagome}; found by Sykes and Essam CITE{SykesEssam} and proved by '
        r'Wierman CITE{Wierman}; $1$ minus the bond threshold of the triangular lattice, its '
        r'planar dual.'),
    ('kagome', 'bond'): (
        r'%s CITE{ScullardJacobsen}, from the eigenvalue formulation of critical polynomials; '
        r'not known exactly: the conjectured polynomial $3p^2+6p^3-12p^4+6p^5-p^6=1$ has its '
        r'root at $0.52442971\ldots$, which differs from the estimate in the fifth decimal.'
        % quoted('0.52440499916744820', '1e-17')),
    ('D-4-8-8', 'site'): (
        r'$p_c=\frac12$, exact CITE{SykesEssam}: every face of the tetrakis square lattice is '
        r'a triangle, so the lattice is self-matching.'),
    ('D-4-6-12', 'site'): (
        r'$p_c=\frac12$, exact CITE{SykesEssam}: every face of the kisrhombille lattice is a '
        r'triangle, so the lattice is self-matching.'),
    ('D-3-12-12', 'site'): (
        r'$p_c=\frac12$, exact CITE{SykesEssam}: every face of the triakis triangular lattice '
        r'is a triangle, so the lattice is self-matching.'),
    ('sc', 'bond'): (
        r'%s CITE{XuWangLvDeng}, from wrapping probabilities in Monte Carlo simulations; the '
        r'earlier $0.24881182(10)$ of Wang, Zhou, Zhang, Garoni and Deng CITE{WangEtAl} '
        r'agrees within the errors.' % quoted('0.24881185', '10e-8')),
}

METHOD = {
    'Jacobsen14': 'from critical polynomials computed by transfer matrices',
    'SudingZiff': 'from hull-walk gradient percolation',
    'ScullardJacobsen': 'from the eigenvalue formulation of critical polynomials',
    'Parviainen': 'by simulation, the standard error of the estimate being about $5\\cdot 10^{-6}$',
    'XuWangLvDeng': 'from wrapping probabilities in Monte Carlo simulations',
    'MertensMoore': 'from invasion percolation',
}


class Threshold(object):
    """One row: how its value is made and what its comment says."""

    def __init__(self, lattice, d, kind):
        self.lattice, self.d, self.kind = lattice, int(d), kind
        if lattice == 'hypercubic':
            table = HYPERCUBIC_SITE if kind == 'site' else HYPERCUBIC_BOND
            if self.d not in table:
                raise ValueError('no hypercubic row for d = %d' % self.d)
            self.exact = None
            self.centre, self.radius = table[self.d]
            self.source = 'MertensMoore'
        elif (lattice, kind) in EXACT:
            self.exact = EXACT[(lattice, kind)]
            self.centre = self.radius = self.source = None
        elif (lattice, kind) in MEASURED:
            self.exact = None
            self.centre, self.radius, self.source = MEASURED[(lattice, kind)]
        elif lattice in DUAL and kind == 'bond':
            dual = Threshold(DUAL[lattice], 2, 'bond')
            if dual.exact is not None:
                raise ValueError('%s: the dual bond threshold is exact and should be listed as exact here' % lattice)
            self.exact = None
            self.centre = str(Decimal('1') - Decimal(dual.centre))
            self.radius = dual.radius
            self.source = dual.source
            self.dual = dual
        else:
            raise ValueError('no entry for %s, d = %d, %s' % (lattice, d, kind))

    def number(self, bits):
        if self.exact == 'half':
            return QQ(1) / 2
        if self.exact is not None:
            RBF = RealBallField(bits)
            s = 2 * (RBF.pi() / 18).sin()
            value = {'sin': s, 'one-minus-sin': 1 - s, 'sqrt': (1 - s).sqrt()}[self.exact]
            if not value.is_finite() or not (0 < value < 1):
                raise ArithmeticError('%s %s: the closed form did not give a finite ball in (0, 1)' % (self.lattice, self.kind))
            return value
        if Decimal(self.radius) <= 0 or not (0 < Decimal(self.centre) < 1):
            raise ValueError('%s %s: %s +/- %s is not a threshold with a positive uncertainty' % (self.lattice, self.kind, self.centre, self.radius))
        return '%s +/- %s' % (self.centre, self.radius)

    def comment(self):
        key = (self.lattice, self.kind)
        if key in COMMENT:
            return COMMENT[key]
        if self.lattice == 'hypercubic':
            return r'%s CITE{MertensMoore}, %s.' % (quoted(self.centre, self.radius), METHOD['MertensMoore'])
        if self.lattice in DUAL and self.kind == 'bond':
            return (r'$1-p_c^{\mathrm{bond}}$ of %s, its planar dual, whose bond threshold '
                    r'%s is CITE{%s}.' % (DUAL_NAME[self.dual.lattice],
                                          quoted(self.dual.centre, self.dual.radius), self.source))
        text = '%s CITE{%s}, %s' % (quoted(self.centre, self.radius), self.source, METHOD[self.source])
        if self.source == 'SudingZiff':
            #The paper's Table I prints (2); the Wikipedia table, maintained
            #by one of its authors, lists (3), and the values that paper gives
            #for the lattices since measured more precisely lie two to three
            #of its standard errors from the later values.
            text += r', with the uncertainty as listed in CITE{Wiki}; the paper prints $(2)$'
        if self.lattice in ALSO:
            text += '; the lattice is also called %s' % ALSO[self.lattice]
        return text + '.'

    def entry(self, bits):
        number = self.number(bits)
        entry = {'number': number, 'comment': self.comment()}
        if isinstance(number, str):
            entry['digits'] = digits_of(number)
        if self.exact == 'half':
            entry['equals'] = 'HREF{%s#1/2}' % RATIONALS
        return entry


class PercolationThresholds(numberdb.Generator):

    table = 'T152'
    parameters = ('lattice', 'd', 'percolation')
    type = 'R'
    digits = 100
    rigour = 'measured'

    def enumerate(self):
        for lattice, d in LATTICES:
            for kind in ('site', 'bond'):
                yield {'lattice': lattice, 'd': d, 'percolation': kind}

    def value(self, params, digits):
        bits = numberdb.bits(digits, losing=WORKING_GUARD)
        row = Threshold(params['lattice'], params['d'], params['percolation'])
        return row.entry(bits)


if __name__ == '__main__':
    generator = PercolationThresholds()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='site and bond percolation thresholds of the eleven Archimedean lattices, '
                    'their Laves duals, the four cubic lattices and Z^d for 4 <= d <= 13: the '
                    'exact values in ball arithmetic at 100 digits, the rest the most precise '
                    'published estimates as of %s with their stated uncertainties' % AS_OF))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
