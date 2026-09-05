"""Hermite's constants gamma_n -- numberdb.org/T149

Hermite's constant gamma_n is the supremum, over all lattices L in R^n, of
the Hermite number

    gamma(L) = mu(L) / (det L)^(1/n)

with mu(L) the squared length of a shortest nonzero vector of L and det L the
determinant of a Gram matrix of L: sqrt(gamma_n) is the greatest length a
shortest vector of a lattice of covolume 1 in R^n can have. It is known for
n <= 8 and n = 24, and in no other dimension:

    gamma_n^n = 1, 4/3, 2, 4, 8, 64/3, 64, 256     for n = 1, ..., 8
    gamma_24^24 = 4^24

attained by Z, A_2, A_3, D_4, D_5, E_6, E_7, E_8 and the Leech lattice. The
table has one parameter, `n`, and one entry per dimension in which gamma_n is
known.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**Where the values come from.** The datum for each entry is the rational
number gamma_n^n, which is a theorem in each dimension listed (Lagrange for
n = 2, Gauss for n = 3, Korkine and Zolotareff for n = 4 and 5, Blichfeldt
for n = 6, 7 and 8, Cohn and Kumar for n = 24), together with the lattice
attaining it. Before a value is returned, gamma_n^n is recomputed as
mu^n / det from the Gram matrix of that lattice for n <= 8 -- the identity
for Z and the Cartan matrix for the root lattices, with mu from PARI's
qfminim -- and a disagreement is an error rather than an entry. For n = 24
the Leech lattice is even and unimodular with minimal norm 4, so
gamma_24^24 = 4^24 / 1; that Gram matrix is not carried here, and the
outside checks recomputed it from the catalogue's block.

**Exact arithmetic up to the last step.** gamma_n is written exactly when
gamma_n^n is an n-th power of a rational (n = 1, 8, 24: the values 1, 2, 4)
and otherwise as the ball for the n-th root in arb. No division of Python
integers occurs anywhere in this file.

**These digits are proven.** With the guard below, the widest ball in the
table, relative to its value, has radius 1.4e-119 (measured at 100 digits
over every entry: gamma_7), so 100 digits are supported with room.

**What was checked outside this file** when the table was made, before any
entry was sent: gamma_n^n against OEIS A007361/A007362; the digits of
gamma_2 to gamma_7 against OEIS A020832 (1/sqrt 75, ten times gamma_2),
A002580, A002193, A011093, A246184 and A246722; the closed forms of the
Wikipedia and MathWorld pages; the stored Hermite numbers of the table of
the classical lattices, of which gamma_n is the maximum in each dimension
listed, and the stored centre densities of the table of the densest lattice
packings, from which gamma_n = 4 delta_n^(2/n); the Leech lattice's
determinant and minimal norm from the catalogue's Gram block; and Hermite's,
Minkowski's, Blichfeldt's and Mordell's inequalities on every entry.
"""

import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField
from sage.matrix.constructor import matrix
from sage.libs.pari.all import pari

#: Bits of working precision beyond what the written digits need. Measured
#: over the whole table at 100 digits: the widest ball, relative to its
#: value, is gamma_7 with relative radius 1.4e-119.
WORKING_GUARD = 64

#: gamma_n^n in every dimension where Hermite's constant is known, with the
#: lattice attaining it (family and dimension, as the table of the classical
#: lattices names them) and the reference key of the table document for the
#: theorem.
KNOWN = {
    1: (QQ(1), 'Z', 1, None),
    2: (QQ(4) / 3, 'A', 2, 'Lagrange'),
    3: (QQ(2), 'A', 3, 'Gauss'),
    4: (QQ(4), 'D', 4, 'KZ'),
    5: (QQ(8), 'D', 5, 'KZ'),
    6: (QQ(64) / 3, 'E', 6, 'Blichfeldt'),
    7: (QQ(64), 'E', 7, 'Blichfeldt'),
    8: (QQ(256), 'E', 8, 'Blichfeldt'),
    24: (QQ(4) ** 24, 'Lambda', 24, 'CohnKumar'),
}

#: gamma_n in closed form, for the entry comment.
CLOSED_FORM = {
    1: '1',
    2: r'\frac{2}{\sqrt{3}}',
    3: r'2^{1/3}',
    4: r'\sqrt{2}',
    5: r'2^{3/5}',
    6: r'\frac{2}{3^{1/6}}',
    7: r'2^{6/7}',
    8: '2',
    24: '4',
}

#: The attaining lattice, as a phrase for the entry comment.
LATTICE = {
    1: r'$\mathbb{Z}$',
    2: r'the hexagonal lattice $A_2$',
    3: r'$A_3=D_3$, the face-centred cubic lattice',
    4: r'$D_4$',
    5: r'$D_5$',
    6: r'$E_6$',
    7: r'$E_7$',
    8: r'$E_8$',
    24: r'the Leech lattice $\Lambda_{24}$',
}

#: The row of the table of the classical lattices holding gamma(L) for the
#: attaining lattice L (address read off the stored document).
CLASSICAL = 'Packing_densities_and_Hermite_numbers_of_the_classical_lattices'

#: The two constants that are quadratic irrationals are rows of the table of
#: algebraic numbers of degree 2, whose anchor is (a2, a1, a0, n) for the n-th
#: root of a2 x^2 + a1 x + a0 in increasing order: 2/sqrt(3) is the larger
#: root of 3x^2 - 4 and sqrt(2) the larger root of x^2 - 2. The `equals` of
#: those entries is spent on the classical-lattices row, so the comment
#: carries this link.
DEGREE_TWO = 'Algebraic_numbers_of_degree_2'
IN_DEGREE_TWO = {2: '3,0,-4,2', 4: '1,0,-2,2'}


def cartan(kind, n):
    """The Cartan matrix of A_n, D_n or E_n as an integer matrix: 2 on the
    diagonal, -1 between neighbours in the Dynkin diagram. E_n uses
    Bourbaki's numbering, the chain 1-3-4-5-...-n with node 2 attached to
    node 4."""
    M = [[0] * n for _ in range(n)]
    for i in range(n):
        M[i][i] = 2
    if kind == 'A':
        for i in range(n - 1):
            M[i][i + 1] = M[i + 1][i] = -1
    elif kind == 'D':
        if n < 4:
            raise ValueError('D_n needs n >= 4, not %s' % n)
        for i in range(n - 2):
            M[i][i + 1] = M[i + 1][i] = -1
        M[n - 3][n - 1] = M[n - 1][n - 3] = -1
    elif kind == 'E':
        if n not in (6, 7, 8):
            raise ValueError('E_n needs n in 6, 7, 8, not %s' % n)
        chain = [0, 2, 3, 4, 5, 6, 7][:n - 1]
        for a, b in zip(chain, chain[1:]):
            M[a][b] = M[b][a] = -1
        M[1][3] = M[3][1] = -1
    else:
        raise ValueError('no Cartan matrix of kind %r' % kind)
    return matrix(ZZ, M)


def gram(family, n):
    """An integral Gram matrix of the attaining lattice, for n <= 8."""
    n = int(n)
    if family == 'Z':
        return matrix(ZZ, n, n, lambda i, j: 1 if i == j else 0)
    if family in ('A', 'D', 'E'):
        return cartan(family, n)
    raise ValueError('no Gram matrix carried for %s_%d' % (family, n))


def hermite_power_from_lattice(family, n):
    """mu^n / det of the attaining lattice, an exact rational, from its
    Gram matrix and PARI's qfminim."""
    G = gram(family, n)
    det = ZZ(G.det())
    if det <= 0:
        raise ArithmeticError('%s_%d: Gram matrix is not positive definite' % (family, n))
    found = pari(G).qfminim(None, None, 0)
    mu = ZZ(found[1])
    return QQ(mu) ** ZZ(n) / QQ(det)


def compute(n, bits):
    n = int(n)
    if n not in KNOWN:
        raise ValueError("Hermite's constant is not known in dimension %d" % n)
    power, family, dim, _ = KNOWN[n]
    if dim != n:
        raise ValueError('n = %d is attained by a lattice of dimension %d' % (n, dim))
    if n <= 8:
        recomputed = hermite_power_from_lattice(family, n)
        if recomputed != power:
            raise ArithmeticError('n = %d: %s_%d gives gamma^n = %s, the table says %s'
                                  % (n, family, n, recomputed, power))
    if power.is_nth_power(n):
        gamma = power.nth_root(n)
    else:
        RBF = RealBallField(bits)
        gamma = RBF(power) ** (QQ(1) / n)
        if not gamma.is_finite():
            raise ArithmeticError('n = %d: the root is not a finite ball' % n)
    return {'hermite': gamma, 'power': power}


def latex_rational(r):
    r = QQ(r)
    if r.denominator() == 1:
        return str(r.numerator())
    return r'\frac{%d}{%d}' % (r.numerator(), r.denominator())


def latex_power(n, power):
    """gamma_n^n as the comment writes it: the reduced fraction, or 4^{24}."""
    if n == 24:
        return '4^{24}'
    return latex_rational(power)


def comment(n, values):
    n = int(n)
    power, _, _, who = KNOWN[n]
    text = r'$\gamma_{%d}=%s$, $\gamma_{%d}^{\,%d}=%s$; attained by %s' % (
        n, CLOSED_FORM[n], n, n, latex_power(n, power), LATTICE[n])
    if who:
        text += ' CITE{%s}' % who
    if n in IN_DEGREE_TWO:
        text += ('; the same number is in the HREF{%s#%s}[table of algebraic '
                 'numbers of degree 2]' % (DEGREE_TWO, IN_DEGREE_TWO[n]))
    return text


def equals_link(n):
    _, family, dim, _ = KNOWN[int(n)]
    return 'HREF{%s#%s,%d,hermite}' % (CLASSICAL, family, dim)


class HermiteConstants(numberdb.Generator):

    table = 'T149'
    parameters = ('n',)
    type = 'R'
    digits = 100
    rigour = 'proven'

    def enumerate(self):
        for n in sorted(KNOWN):
            yield {'n': n}

    def value(self, params, digits):
        n = int(params['n'])
        bits = numberdb.bits(digits, losing=WORKING_GUARD)
        values = compute(n, bits)
        return {'number': values['hermite'],
                'comment': comment(n, values),
                'equals': equals_link(n)}


if __name__ == '__main__':
    generator = HermiteConstants()
    if '--publish' in sys.argv:
        print(generator.publish(
            message="Hermite's constant gamma_n in every dimension where it is known, "
                    "n <= 8 and n = 24: the n-th root of the exact rational gamma_n^n, "
                    "written exactly where that is an integer and as a ball otherwise"))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
