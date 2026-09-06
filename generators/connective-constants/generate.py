"""Connective constants of lattices -- numberdb.org/T157

For an infinite lattice graph, c_n is the number of self-avoiding walks of n
steps from a fixed vertex, and the connective constant mu = lim c_n^(1/n) is
their growth rate. The table holds mu for the honeycomb, square, triangular,
kagome, (3,12^2) and (4,8^2) lattices, the Manhattan and L lattices, the
simple cubic, body-centred cubic and face-centred cubic lattices, and the
hypercubic lattices Z^d for 4 <= d <= 8: 16 entries, with two parameters,
`lattice` and `d` (the dimension).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**Two kinds of entry.** Two constants are known exactly and are computed
here in ball arithmetic at 100 digits. The honeycomb constant is
sqrt(2 + sqrt 2) = 2 cos(pi/8), conjectured by Nienhuis and proved by
Duminil-Copin and Smirnov. The (3,12^2) constant follows from it: a walk on
(3,12^2) is a honeycomb walk in which every visited vertex has become a
triangle, crossed by one edge or by two, so a honeycomb step of weight y
becomes x^2 + x^3 and the two constants satisfy 1/mu_hex = 1/mu^2 + 1/mu^3,
that is mu^3 - mu_hex mu - mu_hex = 0. That cubic has one real root, since
its discriminant mu_hex^2 (4 mu_hex - 27) is negative, and the root is
enclosed by bisection on the sign of the cubic, every sign decided in ball
arithmetic, with a sign change checked across the final enclosure. The
other 14 entries are the most precise published estimates read on 6
September 2026, transcribed with the paper's stated uncertainty and written
as `centre +/- radius`, the form the tables of the fine-structure constant
and of the percolation thresholds use; each such entry declares the number
of digits its radius supports. `MEASURED` below holds every transcribed
value with its source, so that updating one is one line and one citation.

**Where the values come from.** Jacobsen, Scullard and Guttmann 2016 for
the square lattice; Jensen 2004 for the triangular lattice; Jensen's 2004
paper on lower bounds for the kagome lattice and, quoted there and by Alm
2005, Jensen and Guttmann 1998 for (4,8^2); Bennett-Wood, Cardy, Enting,
Guttmann and Owczarek 1998 for the Manhattan lattice; Clisby 2013 for the
simple cubic lattice; Clisby 2022 for the body-centred and face-centred
cubic lattices; Owczarek and Prellberg 2001 for Z^4 to Z^8. The L-lattice
value is the one listed in Wikipedia's table of connective constants, which
names no source for that row; no paper stating it could be read for this
table, and the entry says so.

**What was checked outside this file** before any entry was sent: the two
closed forms against OEIS A179260 and A249776 to every digit those entries
list, and against x^4 - 4x^2 + 2 and the degree-12 polynomial of the
(3,12^2) constant by a sign change across each written enclosure; the
degree-12 polynomial against the cubic relation by exact polynomial
arithmetic; every transcribed value against the text of the paper cited;
c_n >= mu^n, which Fekete's lemma gives for every n, against the published
walk counts of eleven of the lattices; each estimate against the rigorous
bounds of Jensen 2004, Alm 2005 and Owczarek and Prellberg 2001; and the
1/(2d-1) expansion against the hypercubic rows.
"""

import sys
from decimal import Decimal

import numberdb.sage as numberdb
from numberdb._compare import digits_of
from sage.rings.real_arb import RealBallField
from sage.rings.real_mpfr import RealField

#: Bits of working precision beyond what the written digits need. Measured
#: over the two closed forms at 100 digits: the wider enclosure, the
#: (3,12^2) root, is written with radius 10^-110 and the honeycomb ball has
#: relative radius below 10^-119.
WORKING_GUARD = 64

#: Decimal digits beyond `digits` to which the (3,12^2) root is bracketed.
BRACKET_GUARD = 10

#: The date on which the sources were read; the estimates are records and
#: move.
AS_OF = '6 September 2026'

#: The lattices, in the order the table lists them, with the dimension.
#: Archimedean lattices are named by their vertex configuration.
LATTICES = [
    ('honeycomb', 2), ('square', 2), ('triangular', 2), ('kagome', 2),
    ('3-12-12', 2), ('4-8-8', 2), ('manhattan', 2), ('L', 2),
    ('sc', 3), ('bcc', 3), ('fcc', 3),
] + [('hypercubic', d) for d in range(4, 9)]

#: The exact constants: which closed form each row is.
EXACT = {'honeycomb': 'honeycomb', '3-12-12': 'three-twelve'}

#: The transcribed constants, (centre, radius) as the paper prints them,
#: with the reference key of the table document. The radius is the paper's
#: stated uncertainty in the last digits of the centre.
MEASURED = {
    'square': ('2.63815853032790', '3e-14', 'JSG16'),
    'triangular': ('4.150797226', '26e-9', 'Jensen04'),
    'kagome': ('2.560576765', '10e-9', 'Jensen04bounds'),
    '4-8-8': ('1.80883001', '6e-8', 'JensenGuttmann98'),
    'manhattan': ('1.733535', '2e-6', 'BennettWood98'),
    'L': ('1.5657', '15e-4', 'Wiki'),
    'sc': ('4.684039931', '27e-9', 'Clisby13'),
    'bcc': ('6.530511501', '84e-9', 'Clisby22'),
    'fcc': ('10.03705785', '14e-8', 'Clisby22'),
}

#: The hypercubic lattices Z^d, 4 <= d <= 8, from Table 1 of Owczarek and
#: Prellberg 2001: d -> (centre, radius).
HYPERCUBIC = {
    4: ('6.774043', '5e-6'), 5: ('8.838544', '3e-6'), 6: ('10.878094', '4e-6'),
    7: ('12.902817', '3e-6'), 8: ('14.919257', '2e-6'),
}

#: The table of cos(pi x) holds cos(pi/8) at x = 1/8 (address read off a
#: search result).
COSINES = 'Cos_pi_times_x_at_rational_numbers'


def quoted(centre, radius):
    """The value as the paper prints it, `4.150797226(26)`: the uncertainty
    as an integer in the last digits of the centre."""
    c, r = Decimal(centre), Decimal(radius)
    places = -c.as_tuple().exponent
    err = r.scaleb(places)
    if err != err.to_integral_value():
        raise ValueError('radius %s is not a whole number of units in the last place of %s' % (radius, centre))
    return '$%s(%d)$' % (centre, int(err))


def honeycomb(bits):
    """sqrt(2 + sqrt 2) as a ball."""
    RBF = RealBallField(bits)
    value = (2 + RBF(2).sqrt()).sqrt()
    #Compared with integers: a ball does not compare with a Python float.
    if not value.is_finite() or not (184 < 100 * value < 185):
        raise ArithmeticError('the honeycomb closed form did not give a ball near 1.8478')
    return value


def three_twelve(bits, digits):
    """The (3,12^2) constant: the one real root of x^3 - m x - m with
    m = sqrt(2 + sqrt 2), bracketed to 10^-(digits + BRACKET_GUARD) by
    bisection, each sign decided in ball arithmetic."""
    RBF, RR = RealBallField(bits), RealField(bits)
    m = honeycomb(bits)

    def f(x):
        return x * x * x - m * x - m

    delta = RR(10) ** (-(digits + BRACKET_GUARD))
    lo, hi = RR(17) / 10, RR(18) / 10
    if not (f(RBF(lo)) < 0 and f(RBF(hi)) > 0):
        raise ArithmeticError('x^3 - m x - m does not change sign on [1.7, 1.8]')
    while hi - lo > delta / 4:
        mid = (lo + hi) / 2
        v = f(RBF(mid))
        if v.contains_zero():
            raise ArithmeticError('the sign of x^3 - m x - m could not be decided at x = %s' % mid)
        if v < 0:
            lo = mid
        else:
            hi = mid
    x0 = (lo + hi) / 2
    if not (f(RBF(x0 - delta)) < 0 and f(RBF(x0 + delta)) > 0):
        raise ArithmeticError('no sign change of x^3 - m x - m across x0 +/- delta')
    value = RBF(x0).add_error(delta)
    #The degree-12 polynomial of Jensen and Guttmann must vanish on the
    #enclosure: it is (x^3/(x+1))^4 - 4 (x^3/(x+1))^2 + 2 times (x+1)^4.
    p = (value ** 12 - 4 * value ** 8 - 8 * value ** 7 - 4 * value ** 6
         + 2 * value ** 4 + 8 * value ** 3 + 12 * value ** 2 + 8 * value + 2)
    if not p.contains_zero():
        raise ArithmeticError('the degree-12 polynomial does not vanish on the enclosure')
    return value


#: Entry comments for the rows with something particular to say; the rest
#: are built from the source in `MEASURED`.
COMMENT = {
    'honeycomb': (
        r'$\mu=\sqrt{2+\sqrt2}=2\cos\frac{\pi}{8}$, exact: conjectured by Nienhuis CITE{Nienhuis} '
        r'and proved by Duminil-Copin and Smirnov CITE{DuminilCopinSmirnov}; the largest root of '
        r'$x^4-4x^2+2$, OEIS A179260 CITE{OEIShoneycomb}; $\cos\frac{\pi}{8}$ is in the '
        r'HREF{%s#1/8}[table of $\cos(\pi x)$]; the honeycomb lattice is also called the '
        r'hexagonal lattice.' % COSINES),
    'square': (
        r'%s CITE{JSG16}, from the topological transfer matrix; the conjecture of Guttmann '
        r'that $\mu$ is the positive root of $13x^4-7x^2-581$, which is $2.63815853034\ldots$ '
        r'CITE{OEISconjecture}, fails in the twelfth digit; the first thirteen digits are OEIS '
        r'A387897 CITE{OEISsquare}.' % quoted('2.63815853032790', '3e-14')),
    'triangular': (
        r'%s CITE{Jensen04}, from series for self-avoiding polygons of up to 60 steps; the '
        r'triangular lattice is also called the hexagonal lattice by some authors, a name '
        r'this table keeps for the honeycomb lattice.' % quoted('4.150797226', '26e-9')),
    'kagome': (
        r'%s CITE{Jensen04bounds}, from unpublished enumerations of self-avoiding polygons; '
        r'the earlier $2.56062$ of Jensen and Guttmann CITE{JensenGuttmann98} is the value '
        r'listed in CITE{Wiki}.' % quoted('2.560576765', '10e-9')),
    '3-12-12': (
        r'$\mu$ is the one real root of $x^3-\mu_{6^3}x-\mu_{6^3}$ with '
        r'$\mu_{6^3}=\sqrt{2+\sqrt2}$ the honeycomb constant, and the largest real root of '
        r'$x^{12}-4x^8-8x^7-4x^6+2x^4+8x^3+12x^2+8x+2$, OEIS A249776 CITE{OEIStt}: a walk on '
        r'$(3,12^2)$ is a walk on the honeycomb lattice with every visited vertex replaced by '
        r'a triangle, crossed by one edge or by two CITE{JensenGuttmann98} '
        r'CITE{GuttmannParviainenRechnitzer}; the lattice is also called the three-twelve or '
        r'truncated hexagonal lattice.'),
    '4-8-8': (
        r'%s CITE{JensenGuttmann98}, from series analysis, as quoted in CITE{Jensen04bounds} '
        r'and CITE{Alm}; the lattice is also called the four-eight, bathroom-tile or truncated '
        r'square lattice.' % quoted('1.80883001', '6e-8')),
    'manhattan': (
        r'%s CITE{BennettWood98}, from series for self-avoiding polygons of up to 84 steps; the '
        r'table in CITE{Wiki} lists the uncertainty as $3$ in the last digit.'
        % quoted('1.733535', '2e-6')),
    'L': (
        r'%s as listed in CITE{Wiki}, which names no source for this value; no paper stating '
        r'it could be read for this table, and the walk counts of OEIS A322419 CITE{OEISL} are '
        r'consistent with it.' % quoted('1.5657', '15e-4')),
    'sc': (
        r'%s CITE{Clisby13}, from the pivot algorithm; the enumeration of Schram, Barkema and '
        r'Bisseling CITE{SchramBarkemaBisseling} gives $4.684043(12)$.'
        % quoted('4.684039931', '27e-9')),
    'bcc': (
        r'%s CITE{Clisby22}, from the pivot algorithm; the enumeration of Schram, Barkema, '
        r'Bisseling and Clisby CITE{SchramEtAl17} gives $6.530520(20)$.'
        % quoted('6.530511501', '84e-9')),
    'fcc': (
        r'%s CITE{Clisby22}, from the pivot algorithm; the enumeration of Schram, Barkema, '
        r'Bisseling and Clisby CITE{SchramEtAl17} gives $10.037075(20)$.'
        % quoted('10.03705785', '14e-8')),
}


class ConnectiveConstant(object):
    """One row: how its value is made and what its comment says."""

    def __init__(self, lattice, d):
        self.lattice, self.d = lattice, int(d)
        if lattice == 'hypercubic':
            if self.d not in HYPERCUBIC:
                raise ValueError('no hypercubic row for d = %d' % self.d)
            self.exact = None
            self.centre, self.radius = HYPERCUBIC[self.d]
            self.source = 'OwczarekPrellberg'
        elif lattice in EXACT:
            if (lattice, self.d) not in LATTICES:
                raise ValueError('%s is not a lattice of dimension %d here' % (lattice, self.d))
            self.exact = EXACT[lattice]
            self.centre = self.radius = self.source = None
        elif lattice in MEASURED:
            if (lattice, self.d) not in LATTICES:
                raise ValueError('%s is not a lattice of dimension %d here' % (lattice, self.d))
            self.exact = None
            self.centre, self.radius, self.source = MEASURED[lattice]
        else:
            raise ValueError('no entry for %s, d = %d' % (lattice, d))

    def number(self, bits, digits):
        if self.exact == 'honeycomb':
            return honeycomb(bits)
        if self.exact == 'three-twelve':
            return three_twelve(bits, digits)
        if Decimal(self.radius) <= 0 or Decimal(self.centre) <= 1:
            raise ValueError('%s: %s +/- %s is not a connective constant with a positive uncertainty'
                             % (self.lattice, self.centre, self.radius))
        return '%s +/- %s' % (self.centre, self.radius)

    def comment(self):
        if self.lattice in COMMENT:
            return COMMENT[self.lattice]
        if self.lattice == 'hypercubic':
            return (r'%s CITE{OwczarekPrellberg}, from the pivot algorithm.'
                    % quoted(self.centre, self.radius))
        raise ValueError('no comment for %s' % self.lattice)

    def entry(self, bits, digits):
        number = self.number(bits, digits)
        entry = {'number': number, 'comment': self.comment()}
        if isinstance(number, str):
            entry['digits'] = digits_of(number)
        return entry


class ConnectiveConstants(numberdb.Generator):

    table = 'T157'
    parameters = ('lattice', 'd')
    type = 'R'
    digits = 100
    rigour = 'measured'

    def enumerate(self):
        for lattice, d in LATTICES:
            yield {'lattice': lattice, 'd': d}

    def value(self, params, digits):
        bits = numberdb.bits(digits, losing=WORKING_GUARD)
        row = ConnectiveConstant(params['lattice'], params['d'])
        return row.entry(bits, digits)


if __name__ == '__main__':
    generator = ConnectiveConstants()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='connective constants of the honeycomb, square, triangular, kagome, (3,12^2), '
                    '(4,8^2), Manhattan and L lattices, the three cubic lattices and Z^d for '
                    '4 <= d <= 8: the two exact values in ball arithmetic at 100 digits, the rest '
                    'the most precise published estimates as of %s with their stated '
                    'uncertainties' % AS_OF))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
