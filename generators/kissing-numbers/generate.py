"""Kissing numbers tau_n -- numberdb.org/T151

The kissing number tau_n of R^n is the largest number of non-overlapping unit
balls that can touch one unit ball; equivalently, the largest number of
points on the unit sphere S^(n-1) with every pairwise angle at least 60
degrees. It is known in six dimensions,

    tau_1 = 2, tau_2 = 6, tau_3 = 12, tau_4 = 24, tau_8 = 240, tau_24 = 196560,

and in no other. For every other n <= 24 the table holds the interval
[a, b], a the size of the largest arrangement known and b the smallest
upper bound proven, as of 6 September 2026 -- the shape the table of
diagonal Ramsey numbers uses for R(5,5) = [43, 48]. The table has one
parameter, `n`, the dimension.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**Where the values come from.** Every entry is a fact from the literature,
cited in its comment: a theorem for the six exact values, and for the
others a construction (the lower endpoint) and a proof (the upper
endpoint). The endpoints were taken from Henry Cohn's table of kissing
number bounds and from Wikipedia's, which agreed in every dimension listed
on the date above, and compared with the abstracts of the papers cited.
Nothing here is computed except a check: for n <= 8 the lower endpoint or
exact value is the kissing number of a lattice (Z, A_2, A_3, D_4, D_5, E_6,
E_7, E_8), and before a value is returned the generator counts the minimal
vectors of that lattice from its Gram matrix -- the identity or the Cartan
matrix -- with PARI's qfminim, and a disagreement is an error rather than an
entry. The lattices attaining the lower endpoints in dimensions 16, 22, 23
and 24 (Lambda_16, Lambda_22, Lambda_23 and the Leech lattice) have Gram
matrices too large to carry here; the outside checks recomputed those four
from the Gram matrices of the table of the classical lattices.

**What an interval claims.** [a, b] says a <= tau_n <= b, both endpoints
theorems. It stays true when either bound is improved; it is then wider
than what is known, and the table is out of date rather than wrong. The
dimensions are in `KNOWN` and `BOUNDS` below, with the sources in
`COMMENT`, so that updating a bound is one line and one citation.

**Exact type.** The table is of type Z with rigour `exact`: an integer or an
interval with integer endpoints. The client writes an interval with exact
integer endpoints in decimal form, which for [40, 44] would be wrong, so an
interval is returned as the plain string `[40, 44]`, the form the database
stores. Plain: the first fill returned it as a subclass of `str` carrying
its endpoints, and the client's YAML writer serialised that as a Python
object, so eighteen entries were stored as a mapping of `args` and `state`,
rendered as two sub-entries each and absent from the search index -- and
`verify()` matched all twenty-four, since it compares the same serialisation
on both sides. The stored table read back through the API is what caught it.
"""

import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.matrix.constructor import matrix
from sage.libs.pari.all import pari

#: The largest dimension listed. The Leech lattice is where the known values
#: end; Cohn's table continues to 48 and 72.
TOP = 24

#: tau_n where it is known exactly.
KNOWN = {1: 2, 2: 6, 3: 12, 4: 24, 8: 240, 24: 196560}

#: (largest arrangement known, smallest upper bound proven) where tau_n is
#: not known, as of 6 September 2026.
BOUNDS = {
    5: (40, 44),
    6: (72, 77),
    7: (126, 134),
    9: (306, 363),
    10: (510, 553),
    11: (604, 868),
    12: (841, 1355),
    13: (1154, 2064),
    14: (1932, 3174),
    15: (2564, 4853),
    16: (4320, 7320),
    17: (5730, 10978),
    18: (7654, 16406),
    19: (11948, 24417),
    20: (19448, 36195),
    21: (29768, 53524),
    22: (49896, 80810),
    23: (93150, 122351),
}

#: The lattice whose kissing number is the exact value or the lower endpoint,
#: for the dimensions where the generator can rebuild it: (family, n).
LATTICE = {1: ('Z', 1), 2: ('A', 2), 3: ('A', 3), 4: ('D', 4), 5: ('D', 5),
           6: ('E', 6), 7: ('E', 7), 8: ('E', 8)}

#: The entry comments: what attains the lower endpoint, who proved the
#: upper one, and for an exact value who proved it. The kissing numbers of
#: the laminated lattices quoted here are OEIS A002336 and the entry
#: comments of the table of the classical lattices.
COMMENT = {
    1: r'$\tau_1=2$, attained by the integer lattice $\mathbb{Z}$.',
    2: r'$\tau_2=6$, attained by the hexagonal lattice $A_2$; a seventh circle '
       r'cannot touch, since two of seven rays from the centre would meet at '
       r'an angle smaller than $60^{\circ}$.',
    3: r'$\tau_3=12$, attained by the face-centred cubic lattice $A_3$ and by '
       r'many other arrangements, among them the vertices of a regular '
       r'icosahedron; whether a thirteenth sphere fits was disputed by Newton '
       r'and Gregory in 1694, and the first complete proof that it does not '
       r'is by Schütte and van der Waerden CITE{SvdW}.',
    4: r'$\tau_4=24$, attained by $D_4$, whose minimal vectors are the '
       r'vertices of the 24-cell; proved by Musin CITE{Musin}, and the '
       r'arrangement is unique up to isometry CITE{dLLdMK}.',
    5: r'$40$ is the kissing number of $D_5$ CITE{SPLAG}; the upper bound is '
       r'the semidefinite programming bound of Mittelmann and Vallentin '
       r'CITE{MV}.',
    6: r'$72$ is the kissing number of $E_6$ CITE{SPLAG}; the upper bound is by '
       r'de Laat, Leijenhorst and de Muinck Keizer CITE{dLLdMK}.',
    7: r'$126$ is the kissing number of $E_7$ CITE{SPLAG}; the upper bound is '
       r'by Mittelmann and Vallentin CITE{MV}.',
    8: r'$\tau_8=240$, attained by $E_8$; proved independently by Odlyzko and '
       r'Sloane CITE{OS} and by Levenshtein CITE{Levenshtein}, and the '
       r'arrangement is unique up to isometry CITE{BannaiSloane}. The theta '
       r'series of $E_8$ is the Eisenstein series $E_4$, whose coefficient of '
       r'$q$ is $240$.',
    9: r'$306$ is attained by a nonlattice arrangement of Leech and Sloane '
       r'CITE{LeechSloane}; the largest kissing number of a lattice in '
       r'dimension $9$ is $272$, that of $\Lambda_9$ CITE{Watson}; the upper '
       r'bound is by Machado and de Oliveira Filho CITE{MO}.',
    10: r'$510$ is attained by an arrangement of Ganzhinov CITE{Ganzhinov}; '
        r'the laminated lattice $\Lambda_{10}$ has $336$ minimal vectors; the '
        r'upper bound is by Machado and de Oliveira Filho CITE{MO}.',
    11: r'$604$ is attained by an arrangement found in 2026 by AI agents on '
        r'the EinsteinArena platform CITE{Bianchi}; $\Lambda_{11}$ has $438$ '
        r'minimal vectors; the upper bound is by de Laat and Leijenhorst '
        r'CITE{dLL}.',
    12: r'$841$ is attained by an arrangement of Takhanov, Assylbekov and Yun '
        r'CITE{TAY}, one sphere more than the arrangements of size $840$ known '
        r'before it; the Coxeter–Todd lattice $K_{12}$ has $756$ minimal '
        r'vectors; the upper bound is by de Laat and Leijenhorst CITE{dLL}.',
    13: r'$1154$ is attained by an arrangement of Zinoviev and Ericson '
        r'CITE{ZE}; $\Lambda_{13}$ has $906$ minimal vectors; the upper bound '
        r'is by de Laat and Leijenhorst CITE{dLL}.',
    14: r'$1932$ is attained by an arrangement of Ganzhinov CITE{Ganzhinov}; '
        r'$\Lambda_{14}$ has $1422$ minimal vectors; the upper bound is by de '
        r'Laat and Leijenhorst CITE{dLL}.',
    15: r'$2564$ is attained by a nonlattice arrangement of Leech and Sloane '
        r'CITE{LeechSloane}; $\Lambda_{15}$ has $2340$ minimal vectors; the '
        r'upper bound is by de Laat and Leijenhorst CITE{dLL}.',
    16: r'$4320$ is the kissing number of the Barnes–Wall lattice '
        r'$\Lambda_{16}$ CITE{BarnesWall}; the upper bound is by de Laat and '
        r'Leijenhorst CITE{dLL}.',
    17: r'$5730$ is attained by an arrangement of Cohn and Li CITE{CohnLi}, '
        r'obtained by changing signs in the minimal vectors of a lattice; '
        r'$\Lambda_{17}$ has $5346$ minimal vectors; the upper bound is by de '
        r'Laat and Leijenhorst CITE{dLL}.',
    18: r'$7654$ is attained by an arrangement of Cohn and Li CITE{CohnLi}; '
        r'$\Lambda_{18}$ has $7398$ minimal vectors; the upper bound is by de '
        r'Laat and Leijenhorst CITE{dLL}.',
    19: r'$11948$ is attained by an arrangement of Ho CITE{Ho}, improving the '
        r'$11692$ of Cohn and Li CITE{CohnLi}; $\Lambda_{19}$ has $10668$ '
        r'minimal vectors; the upper bound is by de Laat and Leijenhorst '
        r'CITE{dLL}.',
    20: r'$19448$ is attained by an arrangement of Cohn and Li CITE{CohnLi}; '
        r'$\Lambda_{20}$ has $17400$ minimal vectors; the upper bound is by de '
        r'Laat and Leijenhorst CITE{dLL}.',
    21: r'$29768$ is attained by an arrangement of Cohn and Li CITE{CohnLi}; '
        r'$\Lambda_{21}$ has $27720$ minimal vectors; the upper bound is by de '
        r'Laat and Leijenhorst CITE{dLL}.',
    22: r'$49896$ is the kissing number of the laminated lattice '
        r'$\Lambda_{22}$ CITE{Leech}; the upper bound is by de Laat and '
        r'Leijenhorst CITE{dLL}.',
    23: r'$93150$ is the kissing number of the laminated lattice '
        r'$\Lambda_{23}$ CITE{Leech}; the upper bound is by de Laat and '
        r'Leijenhorst CITE{dLL}.',
    24: r'$\tau_{24}=196560$, attained by the Leech lattice $\Lambda_{24}$ '
        r'CITE{Leech}; proved independently by Odlyzko and Sloane CITE{OS} and '
        r'by Levenshtein CITE{Levenshtein}, and the arrangement is unique up '
        r'to isometry CITE{BannaiSloane}.',
}

#: tau_8 = 240 is the coefficient of q in the q-expansion of E_4, the theta
#: series of E_8 (address read off the stored document).
EISENSTEIN_E4 = 'Q-expansion_of_the_Eisenstein_series_E4'
EQUALS = {8: 'HREF{%s#1}' % EISENSTEIN_E4}


class IntegerInterval(object):
    """An integer known to lie between `lower` and `upper`, both integers.

    `str()` of it is the text the database stores, `[40, 44]`, and that
    plain string -- not this object, and not a subclass of `str` -- is what
    `value()` returns, because the client writes a string verbatim and
    serialises anything else as it sees fit.
    """

    def __init__(self, lower, upper):
        lower, upper = ZZ(lower), ZZ(upper)
        if not lower < upper:
            raise ValueError('[%s, %s] is not an interval of nonzero width' % (lower, upper))
        self.lower = lower
        self.upper = upper

    def __str__(self):
        return '[%s, %s]' % (self.lower, self.upper)

    __repr__ = __str__


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
    """An integral Gram matrix of the lattice, for the lattices carried here."""
    n = int(n)
    if family == 'Z':
        return matrix(ZZ, n, n, lambda i, j: 1 if i == j else 0)
    if family in ('A', 'D', 'E'):
        return cartan(family, n)
    raise ValueError('no Gram matrix carried for %s_%d' % (family, n))


def lattice_kissing_number(family, n):
    """The number of minimal vectors of the lattice, from PARI's qfminim on
    its Gram matrix: both signs counted, 240 for E_8."""
    G = gram(family, n)
    if ZZ(G.det()) <= 0:
        raise ArithmeticError('%s_%d: Gram matrix is not positive definite' % (family, n))
    found = pari(G).qfminim(None, None, 0)
    return ZZ(found[0])


def lower_endpoint(n):
    """The exact value or the lower endpoint, checked against the lattice
    that attains it where the generator carries that lattice."""
    n = int(n)
    value = KNOWN[n] if n in KNOWN else BOUNDS[n][0]
    if n in LATTICE:
        family, dim = LATTICE[n]
        counted = lattice_kissing_number(family, dim)
        if counted != value:
            raise ArithmeticError('n = %d: %s_%d has %s minimal vectors, the table says %s'
                                  % (n, family, dim, counted, value))
    return ZZ(value)


def compute(n):
    n = int(n)
    if n in KNOWN and n in BOUNDS:
        raise ValueError('n = %d is listed both as known and as bounded' % n)
    if n not in KNOWN and n not in BOUNDS:
        raise ValueError('no entry for n = %d' % n)
    lower = lower_endpoint(n)
    if n in KNOWN:
        return lower
    return IntegerInterval(lower, BOUNDS[n][1])


class KissingNumbers(numberdb.Generator):

    table = 'T151'
    parameters = ('n',)
    type = 'Z'
    rigour = 'exact'

    def enumerate(self):
        for n in range(1, TOP + 1):
            yield {'n': n}

    def value(self, params, digits):
        n = int(params['n'])
        number = compute(n)
        if isinstance(number, IntegerInterval):
            number = str(number)
        entry = {'number': number, 'comment': COMMENT[n]}
        if n in EQUALS:
            entry['equals'] = EQUALS[n]
        return entry


if __name__ == '__main__':
    generator = KissingNumbers()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='kissing numbers tau_n for n <= 24: the exact value in the six '
                    'dimensions where it is known, and otherwise the interval between the '
                    'largest arrangement known and the smallest upper bound proven, as of '
                    '6 September 2026'))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
