"""Hardy-Littlewood singular series of prime tuples -- numberdb.org/T163

For an admissible tuple H = (0, h_2, ..., h_k), this computes

    S(H) = product_p (1 - w_H(p)/p) / (1 - 1/p)^k,

where w_H(p) is the number of residue classes occupied by H modulo p.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The values are the full singular series, including the small-prime factors.
Thus S((0,2)) is twice the twin prime constant C_2 stored in T39. Several
OEIS entries store only the generic tail of the product; this generator keeps
the finite factors explicit so the convention is visible in every named case.

The digits are not claimed proven. PARI's prodeulerrat evaluates the rational
Euler product tail quickly by zeta expansion, but it does not return a ball or
an interval. The table is therefore heuristic (agreement-checked), with the
agreement checks run outside this generator before the draft was filled.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import prime_divisors, prime_range
from sage.libs.pari import pari
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ

#: Pair offsets H = (0, D), for every even D up to this bound.
PAIR_BOUND = 100

#: Decimal digits written to the table. PARI is run with extra guard digits.
DIGITS = 100
PARI_PRECISION = DIGITS + 40

#: Prime constellations through k = 12. The k <= 9 rows are the ones listed on
#: Wikipedia's Prime k-tuple page; the k = 10, 11, 12 rows are the OEIS/Luhn
#: rows named in the proposal and cited from the table document.
CONSTELLATIONS = (
    (0, 2, 6),
    (0, 4, 6),
    (0, 2, 6, 8),
    (0, 2, 6, 8, 12),
    (0, 4, 6, 10, 12),
    (0, 4, 6, 10, 12, 16),
    (0, 2, 6, 8, 12, 18, 20),
    (0, 2, 8, 12, 14, 18, 20),
    (0, 2, 6, 8, 12, 18, 20, 26),
    (0, 2, 6, 12, 14, 20, 24, 26),
    (0, 6, 8, 14, 18, 20, 24, 26),
    (0, 2, 6, 8, 12, 18, 20, 26, 30),
    (0, 4, 6, 10, 16, 18, 24, 28, 30),
    (0, 2, 6, 12, 14, 20, 24, 26, 30),
    (0, 4, 10, 12, 18, 22, 24, 28, 30),
    (0, 2, 6, 8, 12, 18, 20, 26, 30, 32),
    (0, 2, 6, 12, 14, 20, 24, 26, 30, 32),
    (0, 4, 6, 10, 16, 18, 24, 28, 30, 34, 36),
    (0, 2, 6, 8, 12, 18, 20, 26, 30, 32, 36),
    (0, 2, 6, 8, 12, 18, 20, 26, 30, 32, 36, 42),
    (0, 6, 10, 12, 16, 22, 24, 30, 34, 36, 40, 42),
)

NAMES = {
    (0, 2, 6): 'prime triplet',
    (0, 4, 6): 'prime triplet',
    (0, 2, 6, 8): 'prime quadruplet',
    (0, 2, 6, 8, 12): 'prime quintuplet',
    (0, 4, 6, 10, 12): 'prime quintuplet',
    (0, 4, 6, 10, 12, 16): 'prime sextuplet',
}

OEIS_NOTES = {
    (0, 2, 6): 'OEIS A271886 stores this full normalization; A065418 omits the factor $9/2$',
    (0, 4, 6): 'OEIS A271886 stores this full normalization; A065418 omits the factor $9/2$',
    (0, 2, 6, 8): 'OEIS A061642 stores this full normalization; A065419 omits the factor $27/2$',
    (0, 2, 6, 8, 12): 'OEIS A269843 stores only the generic tail, so the full singular series multiplies it by $50625/2048$',
    (0, 4, 6, 10, 12): 'OEIS A269843 stores only the generic tail, so the full singular series multiplies it by $50625/2048$',
}

OEIS_REFERENCES = {
    (0, 2, 6, 8, 12, 18, 20, 26, 30, 32): 'OEISDecaplet1',
    (0, 2, 6, 12, 14, 20, 24, 26, 30, 32): 'OEISDecaplet2',
    (0, 4, 6, 10, 16, 18, 24, 28, 30, 34, 36): 'OEISEleven1',
    (0, 2, 6, 8, 12, 18, 20, 26, 30, 32, 36): 'OEISEleven2',
    (0, 2, 6, 8, 12, 18, 20, 26, 30, 32, 36, 42): 'OEISTwelve2',
    (0, 6, 10, 12, 16, 22, 24, 30, 34, 36, 40, 42): 'OEISTwelve1',
}

_TAILS = {}


def tuple_text(H):
    """The parameter spelling: offsets separated by commas, with no spaces."""
    return ','.join(str(ZZ(h)) for h in H)


def parse_tuple(text):
    """Inverse of tuple_text, for values read back from NumberDB."""
    return tuple(ZZ(part) for part in str(text).split(','))


def local_factor(H, p):
    """The exact p-factor in the singular series."""
    H = tuple(ZZ(h) for h in H)
    p = ZZ(p)
    k = ZZ(len(H))
    w = ZZ(len({h % p for h in H}))
    return (QQ(1) - QQ(w) / QQ(p)) / (QQ(1) - QQ(1) / QQ(p)) ** k


def admissible(H):
    """Whether H passes the local admissibility condition."""
    H = tuple(ZZ(h) for h in H)
    for p in prime_range(2, len(H) + 1):
        if len({h % p for h in H}) == p:
            return False
    return True


def generic_factor(k):
    """PARI expression for the p-factor once all offsets are distinct mod p."""
    return 'p^%d*(p-%d)/(p-1)^%d' % (k - 1, k, k)


def tail_start(H):
    """An integer from which every prime sees all offsets distinctly."""
    H = tuple(ZZ(h) for h in H)
    return int(max(H) + 1)


def finite_factor(H, start):
    """The exact product of local factors before the generic tail starts."""
    product = QQ(1)
    for p in prime_range(2, start):
        product *= local_factor(H, p)
    return product


def pari_tail(k, start):
    """The generic tail over primes p >= start, cached by k and start."""
    key = (int(k), int(start))
    if key not in _TAILS:
        pari('default(realprecision, %d)' % PARI_PRECISION)
        _TAILS[key] = pari('prodeulerrat(%s, 1, %d)' % (
            generic_factor(k), start))
    return _TAILS[key]


def singular_series(H):
    """The Hardy-Littlewood singular series for H."""
    H = tuple(ZZ(h) for h in H)
    if not admissible(H):
        return pari('0')
    start = tail_start(H)
    return pari(str(finite_factor(H, start))) * pari_tail(len(H), start)


def decimal(value, digits):
    """A PARI real as NumberDB's plain decimal text."""
    text = str(pari('Strprintf("%%.%dg", %s)' % (int(digits), value)))
    return text.replace('E', 'e')


def tex_rational(value):
    """A rational in short TeX form."""
    value = QQ(value)
    if value.denominator() == 1:
        return str(value.numerator())
    return r'\frac{%s}{%s}' % (value.numerator(), value.denominator())


def pair_multiplier(D):
    """The exact multiplier in S((0,D)) = 2*C_2*pair_multiplier(D)."""
    multiplier = QQ(1)
    for p in prime_divisors(ZZ(D)):
        if p > 2:
            multiplier *= QQ(p - 1) / QQ(p - 2)
    return multiplier


def pair_comment(D):
    multiplier = pair_multiplier(D)
    if multiplier == 1:
        return (r'The pair offset is $D=%d$; this is $2C_2$, twice '
                r'HREF{Twin_prime_constant}[the twin prime constant $C_2$].'
                % D)
    return (r'The pair offset is $D=%d$; this is $%s\cdot2C_2$, where '
            r'$C_2$ is HREF{Twin_prime_constant}[the twin prime constant].'
            % (D, tex_rational(multiplier)))


def constellation_comment(H):
    H = tuple(ZZ(h) for h in H)
    name = NAMES.get(tuple(int(h) for h in H),
                     'prime %d-tuplet' % len(H))
    reference = OEIS_REFERENCES.get(tuple(int(h) for h in H))
    if reference:
        return (r'This is a %s CITE{%s}; the finite factor in '
                r'CITE{formula-tail} is included in the value.'
                % (name, reference))
    start = tail_start(H)
    factor = finite_factor(H, start)
    comment = (r'This is a %s; the finite factor before the generic tail '
               r'over primes $p>%d$ is $%s$'
               % (name, max(H), tex_rational(factor)))
    note = OEIS_NOTES.get(tuple(int(h) for h in H))
    if note:
        comment += '; %s' % note
    return comment + '.'


class HardyLittlewoodSingularSeries(numberdb.Generator):

    table = os.environ.get('NUMBERDB_TABLE', 'T163')
    parameters = ('H',)
    type = 'R'
    digits = DIGITS
    rigour = 'heuristic (agreement-checked)'

    def enumerate(self, pair_bound=PAIR_BOUND):
        for D in range(2, pair_bound + 1, 2):
            yield {'H': tuple_text((0, D))}
        for H in CONSTELLATIONS:
            if H != (0, 2):
                yield {'H': tuple_text(H)}

    def value(self, params, digits):
        H = parse_tuple(params['H'])
        number = decimal(singular_series(H), digits)
        if len(H) == 2:
            return {'number': number, 'comment': pair_comment(int(H[1]))}
        return {'number': number, 'comment': constellation_comment(H)}


if __name__ == '__main__':
    generator = HardyLittlewoodSingularSeries()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='Hardy-Littlewood singular series for small prime tuples'))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
