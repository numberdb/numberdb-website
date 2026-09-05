"""Packing densities and Hermite numbers of the classical lattices -- numberdb.org/TBD

For a lattice L in R^n with Gram matrix G, minimal norm mu = min v^T G v over
nonzero v in Z^n and determinant det L = det G:

    delta(L) = (sqrt(mu)/2)^n / sqrt(det L)          the centre density
    Delta(L) = V_n delta(L),  V_n = pi^(n/2)/Gamma(n/2 + 1)   the density
    gamma(L) = mu / (det L)^(1/n)                     the Hermite number

for the lattices Z^n, A_n, D_n, E_6, E_7, E_8, their duals A_n^*, D_n^*,
E_6^*, E_7^*, the laminated lattices Lambda_n and the Coxeter-Todd lattice
K_12, every one of dimension n <= 24, under the parameters `family`, `n` and
`expression` (density, centre or hermite).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**Where the lattices come from.** Every value is a function of the dimension,
the determinant and the minimal norm alone, and all three are scale-free, so
nothing here depends on how a lattice is scaled. Z^n is the identity matrix;
A_n, D_n and E_n are their Cartan matrices (minimal norm 2, determinants
n+1, 4, 3, 2, 1), built here directly rather than through Sage's root-system
machinery; a dual is the adjugate of the Cartan matrix, which is det(G) times
the inverse and so integral, and its determinant and minimal norm are
rescaled back to those of the dual proper (det 1/det G). Lambda_9 to
Lambda_23, K_12 and the Leech lattice Lambda_24 are the GRAM blocks of the
Nebe-Sloane Catalogue of Lattices, transcribed below with minimal norm 4;
the catalogue's own DET, MINIMAL_NORM and KISSING_NUMBER lines were
recomputed from each block before it was accepted, and the Leech and
Barnes-Wall blocks were compared with the lattices built from the Golay and
Reed-Muller codes. Lambda_n for n <= 8 is Z, A_2, A_3, D_4, D_5, E_6, E_7,
E_8 and is listed under those names, not under Lambda.

**Exact arithmetic up to the last step.** The determinant is an exact
integer, the minimal norm and the number of minimal vectors come from PARI's
`qfminim` on the integral Gram matrix, and delta^2 = (mu/4)^n / det and
gamma^n = mu^n / det are exact rationals. A value that is rational is
returned as one (delta of Z^n is 2^-n, gamma of E_8 is 2); the rest are
balls: a square root, an n-th root, and for Delta the power of pi times the
exact rational V_n / pi^floor(n/2). No division of Python integers occurs
anywhere in this file; every quotient is between Sage rationals.

**These digits are proven.** With the guard below, the widest ball in the
table, relative to its value, has radius 4.5e-119 (measured at 100 digits
over every entry: Delta(Lambda_22)), so 100 digits are supported with room.

**What is checked before anything is returned.** For every lattice, the
kissing number from `qfminim` must equal the known value (2n for Z^n,
n(n+1) for A_n, 2n(n-1) for D_n, 72, 126, 240 for E_6, E_7, E_8, 2(n+1) for
A_n^*, 2n for D_n^*, 54 and 56 for E_6^*, E_7^*, the catalogue's line for
Lambda_n and K_12), the determinant must be the known one, and
delta^2 = (gamma/4)^n must hold exactly. A lattice failing any of these
is an error rather than an entry.

Outside the generator, when this was written, the values were compared with
the OEIS decimal expansions A093766, A093825, A222066-A222072, A246184,
A246722 and A260646 to 100 digits, with the HERMITE_NUMBER and DENSITY lines
of the catalogue pages, with the centre densities of the catalogue's table
of densest packings, with the laminated determinants A028921, with the
kissing numbers A002336, with the closed forms for gamma(A_n^*) and
gamma(D_n^*) from Conway and Sloane, and with the stored digits of V_n in
T27 and of the quadratic irrationals in T35.
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
#: value, is Delta(Lambda_22) with relative radius 4.5e-119; every entry
#: supports more than 118 digits.
WORKING_GUARD = 64

#: The largest dimension listed. The Leech lattice is where the laminated
#: sequence and the proven results end, and every family stops there.
TOP = 24

#: The families and the dimensions each is listed in. A dual that is similar
#: to its own lattice (A_1^*, A_2^*, D_4^*) and D_3 = A_3 are listed once,
#: under the root-system name; Lambda_n for n <= 8 is a root lattice or Z.
FAMILIES = (
    ('Z', range(1, TOP + 1)),
    ('A', range(1, TOP + 1)),
    ('D', range(4, TOP + 1)),
    ('E', (6, 7, 8)),
    ('A*', range(3, TOP + 1)),
    ('D*', range(5, TOP + 1)),
    ('E*', (6, 7)),
    ('Lambda', range(9, TOP + 1)),
    ('K', (12,)),
)

EXPRESSIONS = ('density', 'centre', 'hermite')


def cartan(kind, n):
    """The Cartan matrix of A_n, D_n or E_n as an integer matrix.

    Built directly: 2 on the diagonal, -1 between neighbours in the Dynkin
    diagram. E_n uses Bourbaki's numbering, the chain 1-3-4-5-...-n with
    node 2 attached to node 4.
    """
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


#: Gram matrices from the Nebe-Sloane Catalogue of Lattices, lower triangles
#: of the GRAM block of each page (LAMBDA9.html ... LAMBDA23.html, K12.html,
#: Leech.html), minimal norm 4. Each reproduces the DET, MINIMAL_NORM and
#: KISSING_NUMBER lines of its page.
CATALOGUE_GRAM = {
    'LAMBDA9': [
        [4],
        [-2, 4],
        [0, -2, 4],
        [0, 2, 0, 4],
        [0, 0, 0, 2, 4],
        [0, 0, 2, 2, 2, 4],
        [0, 0, 0, 0, 0, 2, 4],
        [0, 0, 0, 0, 0, 2, 2, 4],
        [0, 0, 0, 0, 2, 1, 0, 0, 4],
    ],
    'LAMBDA10': [
        [4],
        [-2, 4],
        [0, -2, 4],
        [0, 2, 0, 4],
        [0, 0, 0, 2, 4],
        [0, 0, 2, 2, 2, 4],
        [0, 0, 0, 0, 0, 2, 4],
        [0, 0, 0, 0, 0, 2, 2, 4],
        [0, 0, 0, 0, 2, 1, 0, 0, 4],
        [0, 0, 0, 0, 1, 2, 2, 2, 2, 4],
    ],
    'LAMBDA11': [
        [4],
        [-2, 4],
        [0, -2, 4],
        [0, 2, 0, 4],
        [0, 0, 0, 2, 4],
        [0, 0, 2, 2, 2, 4],
        [0, 0, 0, 0, 0, 2, 4],
        [0, 0, 0, 0, 0, 2, 2, 4],
        [0, 0, 0, 0, 2, 1, 0, 0, 4],
        [0, 0, 0, 0, 1, 2, 2, 2, 2, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 4],
    ],
    'LAMBDA12': [
        [4],
        [-2, 4],
        [0, -2, 4],
        [0, 2, 0, 4],
        [0, 0, 0, 2, 4],
        [0, 0, 2, 2, 2, 4],
        [0, 0, 0, 0, 0, 2, 4],
        [0, 0, 0, 0, 0, 2, 2, 4],
        [0, 0, 0, 0, 2, 1, 0, 0, 4],
        [0, 0, 0, 0, 1, 2, 2, 2, 2, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2, 4],
    ],
    'LAMBDA13': [
        [4],
        [-2, 4],
        [0, -2, 4],
        [0, 2, 0, 4],
        [0, 0, 0, 2, 4],
        [0, 0, 2, 2, 2, 4],
        [0, 0, 0, 0, 0, 2, 4],
        [0, 0, 0, 0, 0, 2, 2, 4],
        [0, 0, 0, 0, 2, 1, 0, 0, 4],
        [0, 0, 0, 0, 1, 2, 2, 2, 2, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2, 4],
        [0, -1, 2, 0, 0, 1, 0, 1, 0, 1, 2, 1, 4],
    ],
    'LAMBDA14': [
        [4],
        [-2, 4],
        [0, -2, 4],
        [0, 2, 0, 4],
        [0, 0, 0, 2, 4],
        [0, 0, 2, 2, 2, 4],
        [0, 0, 0, 0, 0, 2, 4],
        [0, 0, 0, 0, 0, 2, 2, 4],
        [0, 0, 0, 0, 2, 1, 0, 0, 4],
        [0, 0, 0, 0, 1, 2, 2, 2, 2, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2, 4],
        [0, -1, 2, 0, 0, 1, 0, 1, 0, 1, 2, 1, 4],
        [1, 0, 1, 1, 0, 1, -1, 0, 0, 1, 1, 2, 0, 4],
    ],
    'LAMBDA15': [
        [4],
        [-2, 4],
        [0, -2, 4],
        [0, 2, 0, 4],
        [0, 0, 0, 2, 4],
        [0, 0, 2, 2, 2, 4],
        [0, 0, 0, 0, 0, 2, 4],
        [0, 0, 0, 0, 0, 2, 2, 4],
        [0, 0, 0, 0, 2, 1, 0, 0, 4],
        [0, 0, 0, 0, 1, 2, 2, 2, 2, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2, 4],
        [0, -1, 2, 0, 0, 1, 0, 1, 0, 1, 2, 1, 4],
        [1, 0, 1, 1, 0, 1, -1, 0, 0, 1, 1, 2, 0, 4],
        [1, 0, 1, 1, 0, 2, 1, 2, 0, 2, 1, 2, 2, 2, 4],
    ],
    'LAMBDA16': [
        [4],
        [-2, 4],
        [0, -2, 4],
        [0, 2, 0, 4],
        [0, 0, 0, 2, 4],
        [0, 0, 2, 2, 2, 4],
        [0, 0, 0, 0, 0, 2, 4],
        [0, 0, 0, 0, 0, 2, 2, 4],
        [0, 0, 0, 0, 2, 1, 0, 0, 4],
        [0, 0, 0, 0, 1, 2, 2, 2, 2, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 2, 4],
        [0, -1, 2, 0, 0, 1, 0, 1, 0, 1, 2, 1, 4],
        [1, 0, 1, 1, 0, 1, -1, 0, 0, 1, 1, 2, 0, 4],
        [1, 0, 1, 1, 0, 2, 1, 2, 0, 2, 1, 2, 2, 2, 4],
        [0, 1, 0, 2, 2, 2, 0, 1, 2, 2, 0, 1, 0, 2, 2, 4],
    ],
    'LAMBDA17': [
        [4],
        [2, 4],
        [0, -2, 4],
        [0, -2, 0, 4],
        [0, 0, -2, 0, 4],
        [-2, -2, 0, 0, 0, 4],
        [0, 0, 0, 0, 0, -2, 4],
        [0, 0, 0, 0, 0, 0, -2, 4],
        [0, 0, 0, 0, 1, -1, 0, 0, 4],
        [0, 0, 0, 0, -1, 0, 0, 0, 0, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, -2, 0, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -2, 4],
        [1, 0, -1, 1, 1, 0, 0, -1, 1, 1, 0, -1, 4],
        [-1, -1, 1, -1, 0, 0, 1, 0, 1, 1, -1, 1, 0, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 1, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, -1, 1, 0, 0, 1, 1, 0, 4],
        [0, 0, 1, 0, -2, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 4],
    ],
    'LAMBDA18': [
        [4],
        [2, 4],
        [0, -2, 4],
        [0, -2, 0, 4],
        [0, 0, -2, 0, 4],
        [-2, -2, 0, 0, 0, 4],
        [0, 0, 0, 0, 0, -2, 4],
        [0, 0, 0, 0, 0, 0, -2, 4],
        [0, 0, 0, 0, 1, -1, 0, 0, 4],
        [0, 0, 0, 0, -1, 0, 0, 0, 0, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, -2, 0, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -2, 4],
        [1, 0, -1, 1, 1, 0, 0, -1, 1, 1, 0, -1, 4],
        [-1, -1, 1, -1, 0, 0, 1, 0, 1, 1, -1, 1, 0, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 1, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, -1, 1, 0, 0, 1, 1, 0, 4],
        [0, 0, 1, 0, -2, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 4],
        [1, 0, 0, 1, 0, 0, -1, 0, 1, 0, -1, 1, 1, 0, 0, 0, 1, 4],
    ],
    'LAMBDA19': [
        [4],
        [2, 4],
        [0, -2, 4],
        [0, -2, 0, 4],
        [0, 0, -2, 0, 4],
        [-2, -2, 0, 0, 0, 4],
        [0, 0, 0, 0, 0, -2, 4],
        [0, 0, 0, 0, 0, 0, -2, 4],
        [0, 0, 0, 0, 1, -1, 0, 0, 4],
        [0, 0, 0, 0, -1, 0, 0, 0, 0, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, -2, 0, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -2, 4],
        [1, 0, -1, 1, 1, 0, 0, -1, 1, 1, 0, -1, 4],
        [-1, -1, 1, -1, 0, 0, 1, 0, 1, 1, -1, 1, 0, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 1, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, -1, 1, 0, 0, 1, 1, 0, 4],
        [0, 0, 1, 0, -2, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 4],
        [1, 0, 0, 1, 0, 0, -1, 0, 1, 0, -1, 1, 1, 0, 0, 0, 1, 4],
        [0, 0, 0, -1, 0, 1, 0, -1, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 4],
    ],
    'LAMBDA20': [
        [4],
        [2, 4],
        [0, -2, 4],
        [0, -2, 0, 4],
        [0, 0, -2, 0, 4],
        [-2, -2, 0, 0, 0, 4],
        [0, 0, 0, 0, 0, -2, 4],
        [0, 0, 0, 0, 0, 0, -2, 4],
        [0, 0, 0, 0, 1, -1, 0, 0, 4],
        [0, 0, 0, 0, -1, 0, 0, 0, 0, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, -2, 0, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -2, 4],
        [1, 0, -1, 1, 1, 0, 0, -1, 1, 1, 0, -1, 4],
        [-1, -1, 1, -1, 0, 0, 1, 0, 1, 1, -1, 1, 0, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 1, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, -1, 1, 0, 0, 1, 1, 0, 4],
        [0, 0, 1, 0, -2, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 4],
        [1, 0, 0, 1, 0, 0, -1, 0, 1, 0, -1, 1, 1, 0, 0, 0, 1, 4],
        [0, 0, 0, -1, 0, 1, 0, -1, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 4],
        [-1, -1, 1, 0, -1, 1, 0, -1, 0, 1, -1, 1, 0, 1, 0, 0, 1, 1, 0, 4],
    ],
    'LAMBDA21': [
        [4],
        [2, 4],
        [0, -2, 4],
        [0, -2, 0, 4],
        [0, 0, -2, 0, 4],
        [-2, -2, 0, 0, 0, 4],
        [0, 0, 0, 0, 0, -2, 4],
        [0, 0, 0, 0, 0, 0, -2, 4],
        [0, 0, 0, 0, 1, -1, 0, 0, 4],
        [0, 0, 0, 0, -1, 0, 0, 0, 0, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, -2, 0, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -2, 4],
        [1, 0, -1, 1, 1, 0, 0, -1, 1, 1, 0, -1, 4],
        [-1, -1, 1, -1, 0, 0, 1, 0, 1, 1, -1, 1, 0, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 1, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, -1, 1, 0, 0, 1, 1, 0, 4],
        [0, 0, 1, 0, -2, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 4],
        [1, 0, 0, 1, 0, 0, -1, 0, 1, 0, -1, 1, 1, 0, 0, 0, 1, 4],
        [0, 0, 0, -1, 0, 1, 0, -1, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 4],
        [-1, -1, 1, 0, -1, 1, 0, -1, 0, 1, -1, 1, 0, 1, 0, 0, 1, 1, 0, 4],
        [0, 0, -1, 1, 1, 0, 0, -1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 4],
    ],
    'LAMBDA22': [
        [4],
        [2, 4],
        [0, -2, 4],
        [0, -2, 0, 4],
        [0, 0, -2, 0, 4],
        [-2, -2, 0, 0, 0, 4],
        [0, 0, 0, 0, 0, -2, 4],
        [0, 0, 0, 0, 0, 0, -2, 4],
        [0, 0, 0, 0, 1, -1, 0, 0, 4],
        [0, 0, 0, 0, -1, 0, 0, 0, 0, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, -2, 0, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -2, 4],
        [1, 0, -1, 1, 1, 0, 0, -1, 1, 1, 0, -1, 4],
        [-1, -1, 1, -1, 0, 0, 1, 0, 1, 1, -1, 1, 0, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 1, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, -1, 1, 0, 0, 1, 1, 0, 4],
        [0, 0, 1, 0, -2, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 4],
        [1, 0, 0, 1, 0, 0, -1, 0, 1, 0, -1, 1, 1, 0, 0, 0, 1, 4],
        [0, 0, 0, -1, 0, 1, 0, -1, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 4],
        [-1, -1, 1, 0, -1, 1, 0, -1, 0, 1, -1, 1, 0, 1, 0, 0, 1, 1, 0, 4],
        [0, 0, -1, 1, 1, 0, 0, -1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 4],
        [0, 1, -1, -1, 1, -1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 4],
    ],
    'LAMBDA23': [
        [4],
        [2, 4],
        [0, -2, 4],
        [0, -2, 0, 4],
        [0, 0, -2, 0, 4],
        [-2, -2, 0, 0, 0, 4],
        [0, 0, 0, 0, 0, -2, 4],
        [0, 0, 0, 0, 0, 0, -2, 4],
        [0, 0, 0, 0, 1, -1, 0, 0, 4],
        [0, 0, 0, 0, -1, 0, 0, 0, 0, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, -2, 0, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -2, 4],
        [1, 0, -1, 1, 1, 0, 0, -1, 1, 1, 0, -1, 4],
        [-1, -1, 1, -1, 0, 0, 1, 0, 1, 1, -1, 1, 0, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 1, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, -1, 1, 0, 0, 1, 1, 0, 4],
        [0, 0, 1, 0, -2, 0, 0, 0, 0, 0, 0, -1, 0, 0, 0, 0, 4],
        [1, 0, 0, 1, 0, 0, -1, 0, 1, 0, -1, 1, 1, 0, 0, 0, 1, 4],
        [0, 0, 0, -1, 0, 1, 0, -1, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 4],
        [-1, -1, 1, 0, -1, 1, 0, -1, 0, 1, -1, 1, 0, 1, 0, 0, 1, 1, 0, 4],
        [0, 0, -1, 1, 1, 0, 0, -1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 4],
        [0, 1, -1, -1, 1, -1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 4],
        [0, -1, 0, 1, 0, 1, -1, 1, 0, 1, 0, -1, 1, 0, 0, 0, 1, 1, 0, 1, 0, 0, 4],
    ],
    'K12': [
        [4],
        [0, 4],
        [0, 0, 4],
        [-2, 0, 0, 4],
        [0, -2, 0, 0, 4],
        [0, 0, -2, 0, 0, 4],
        [2, 2, 2, -1, -1, -1, 4],
        [-1, -1, 2, -1, 2, -1, 0, 4],
        [-1, -1, 2, 2, -1, -1, 0, 0, 4],
        [-1, -1, -1, 2, 2, 2, -2, 0, 0, 4],
        [2, -1, -1, -1, -1, 2, 0, -2, 0, 0, 4],
        [-1, 2, -1, -1, -1, 2, 0, 0, -2, 0, 0, 4],
    ],
    'Leech': [
        [8],
        [4, 4],
        [4, 2, 4],
        [4, 2, 2, 4],
        [4, 2, 2, 2, 4],
        [4, 2, 2, 2, 2, 4],
        [4, 2, 2, 2, 2, 2, 4],
        [2, 2, 2, 2, 2, 2, 2, 4],
        [4, 2, 2, 2, 2, 2, 2, 1, 4],
        [4, 2, 2, 2, 2, 2, 2, 1, 2, 4],
        [4, 2, 2, 2, 2, 2, 2, 1, 2, 2, 4],
        [2, 2, 2, 2, 1, 1, 1, 2, 2, 2, 2, 4],
        [4, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 1, 4],
        [2, 2, 1, 1, 2, 2, 1, 2, 2, 2, 1, 2, 2, 4],
        [2, 1, 2, 1, 2, 1, 2, 2, 2, 1, 2, 2, 2, 2, 4],
        [2, 1, 1, 2, 2, 1, 1, 2, 2, 1, 1, 2, 2, 2, 2, 4],
        [4, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 1, 2, 1, 1, 1, 4],
        [2, 1, 2, 1, 2, 1, 1, 2, 2, 2, 1, 2, 1, 2, 2, 2, 2, 4],
        [2, 1, 1, 2, 2, 2, 1, 2, 2, 1, 2, 2, 1, 2, 2, 2, 2, 2, 4],
        [2, 2, 1, 1, 2, 1, 2, 2, 2, 1, 1, 2, 1, 2, 2, 2, 2, 2, 2, 4],
        [0, 1, 1, 1, 1, 0, 0, 2, 1, 0, 0, 2, 1, 2, 2, 2, 1, 2, 2, 2, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 2, 1, 1, 1, 2, 1, 1, 2, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 2, 1, 1, 1, 2, 1, 2, 2, 4],
        [-3, -1, -1, -1, -1, -1, -1, 1, -1, -1, -1, 1, -1, 1, 1, 1, -1, 1, 1, 1, 2, 2, 2, 4],
    ],
}


def catalogue(name):
    rows = CATALOGUE_GRAM[name]
    n = len(rows)
    G = [[0] * n for _ in range(n)]
    for i in range(n):
        if len(rows[i]) != i + 1:
            raise ValueError('%s: row %d of the lower triangle has %d entries' % (name, i, len(rows[i])))
        for j in range(i + 1):
            G[i][j] = G[j][i] = rows[i][j]
    return matrix(ZZ, G)


def gram(family, n):
    """An integral Gram matrix of the lattice, and the factor its scale was
    multiplied by relative to the scaling the comments quote.

    Returns (G, s): the lattice with Gram matrix G is the named lattice
    scaled so that norms are s times the quoted ones. s = 1 except for the
    duals, whose adjugate Gram matrix is det(G) times the dual's own.
    """
    n = int(n)
    if family == 'Z':
        return matrix(ZZ, n, n, lambda i, j: 1 if i == j else 0), ZZ(1)
    if family in ('A', 'D', 'E'):
        return cartan(family, n), ZZ(1)
    if family in ('A*', 'D*', 'E*'):
        G = cartan(family[0], n)
        d = ZZ(G.det())
        return matrix(ZZ, d * G.inverse()), d
    if family == 'Lambda':
        return catalogue('Leech' if n == 24 else 'LAMBDA%d' % n), ZZ(1)
    if family == 'K':
        if n != 12:
            raise ValueError('K_n is listed for n = 12 only')
        return catalogue('K12'), ZZ(1)
    raise ValueError('no family %r' % family)


def invariants(family, n):
    """(det, mu, tau): determinant, minimal norm and number of minimal
    vectors, in the scaling the comments quote (exact rationals)."""
    G, s = gram(family, n)
    n = G.nrows()
    det_scaled = ZZ(G.det())
    if det_scaled <= 0:
        raise ArithmeticError('%s_%d: Gram matrix is not positive definite' % (family, n))
    found = pari(G).qfminim(None, None, 0)
    tau, mu_scaled = int(found[0]), ZZ(found[1])
    det = QQ(det_scaled) / QQ(s) ** n
    mu = QQ(mu_scaled) / QQ(s)
    expected_tau = known_kissing_number(family, n)
    if tau != expected_tau:
        raise ArithmeticError('%s_%d: qfminim counts %d minimal vectors, the kissing number is %d'
                              % (family, n, tau, expected_tau))
    expected_det = known_determinant(family, n)
    if det != expected_det:
        raise ArithmeticError('%s_%d: determinant %s, expected %s' % (family, n, det, expected_det))
    return det, mu, tau


#: Kissing numbers of the laminated lattices Lambda_9 ... Lambda_24 and of
#: K_12: the catalogue's KISSING_NUMBER lines, which are OEIS A002336.
LAMINATED_KISSING = {9: 272, 10: 336, 11: 438, 12: 648, 13: 906, 14: 1422, 15: 2340,
                     16: 4320, 17: 5346, 18: 7398, 19: 10668, 20: 17400, 21: 27720,
                     22: 49896, 23: 93150, 24: 196560}

#: Determinants of the laminated lattices at minimal norm 4: the catalogue's
#: DET lines, which are OEIS A028921.
LAMINATED_DET = {9: 512, 10: 768, 11: 1024, 12: 1024, 13: 1024, 14: 768, 15: 512, 16: 256,
                 17: 256, 18: 192, 19: 128, 20: 64, 21: 32, 22: 12, 23: 4, 24: 1}


def known_kissing_number(family, n):
    n = int(n)
    if family == 'Z':
        return 2 * n
    if family == 'A':
        return n * (n + 1)
    if family == 'D':
        return 2 * n * (n - 1)
    if family == 'E':
        return {6: 72, 7: 126, 8: 240}[n]
    if family == 'A*':
        return 2 * (n + 1)
    if family == 'D*':
        return 2 * n
    if family == 'E*':
        return {6: 54, 7: 56}[n]
    if family == 'Lambda':
        return LAMINATED_KISSING[n]
    if family == 'K':
        return 756
    raise ValueError('no family %r' % family)


def known_determinant(family, n):
    n = int(n)
    if family == 'Z':
        return QQ(1)
    if family == 'A':
        return QQ(n + 1)
    if family == 'D':
        return QQ(4)
    if family == 'E':
        return QQ({6: 3, 7: 2, 8: 1}[n])
    if family == 'A*':
        return QQ(1) / (n + 1)
    if family == 'D*':
        return QQ(1) / 4
    if family == 'E*':
        return QQ(1) / {6: 3, 7: 2}[n]
    if family == 'Lambda':
        return QQ(LAMINATED_DET[n])
    if family == 'K':
        return QQ(729)
    raise ValueError('no family %r' % family)


def ball_volume_over_pi_power(n):
    """V_n / pi^floor(n/2) as an exact rational: 1/k! for n = 2k and
    2^(2k+1) k! / (2k+1)! for n = 2k+1."""
    n = int(n)
    k = n // 2
    kf = ZZ(1)
    for i in range(2, k + 1):
        kf *= i
    if n % 2 == 0:
        return QQ(1) / kf
    nf = ZZ(1)
    for i in range(2, n + 1):
        nf *= i
    return QQ(2) ** (2 * k + 1) * QQ(kf) / QQ(nf)


def compute(family, n, bits):
    """(density, centre density, Hermite number) as exact rationals where they
    are rational and as balls otherwise, with the invariants used."""
    n = int(n)
    det, mu, tau = invariants(family, n)
    RBF = RealBallField(bits)
    delta_sq = (mu / 4) ** n / det
    gamma_n = mu ** n / det
    if delta_sq != (gamma_n / 4 ** n):
        raise ArithmeticError('%s_%d: delta^2 and (gamma/4)^n disagree' % (family, n))
    if delta_sq.is_square():
        delta = delta_sq.sqrt()
    else:
        delta = RBF(delta_sq).sqrt()
    if gamma_n.is_nth_power(n):
        gamma = gamma_n.nth_root(n)
    else:
        gamma = RBF(gamma_n) ** (QQ(1) / n)
    c = ball_volume_over_pi_power(n)
    k = n // 2
    if k == 0:
        density = c * delta                         # n = 1: V_1 = 2, exact
    else:
        density = RBF(c) * RBF.pi() ** k * delta
    for name, value in (('density', density), ('centre', delta), ('hermite', gamma)):
        if hasattr(value, 'is_finite') and not value.is_finite():
            raise ArithmeticError('%s_%d: %s is not a finite ball' % (family, n, name))
    return {'density': density, 'centre': delta, 'hermite': gamma,
            'det': det, 'mu': mu, 'tau': tau}


# ---------------------------------------------------------------- comments

def latex_name(family, n):
    n = int(n)
    if family == 'Z':
        return r'\mathbb{Z}^{%d}' % n if n > 1 else r'\mathbb{Z}'
    if family == 'Lambda':
        return r'\Lambda_{%d}' % n
    base = family[0]
    star = '^{*}' if family.endswith('*') else ''
    return r'%s_{%d}%s' % (base, n, star)


def latex_rational(r):
    r = QQ(r)
    if r.denominator() == 1:
        return str(r.numerator())
    return r'\frac{%d}{%d}' % (r.numerator(), r.denominator())


def latex_sqrt_of_rational(r):
    """sqrt(r) for a positive rational r as (t/q) sqrt(s), s squarefree."""
    r = QQ(r)
    p, q = r.numerator(), r.denominator()
    m = ZZ(p * q)
    s = m.squarefree_part()
    t = ZZ((m // s).sqrt())
    coefficient = QQ(t) / q
    if s == 1:
        return latex_rational(coefficient)
    root = r'\sqrt{%d}' % s
    if coefficient == 1:
        return root
    if coefficient.denominator() == 1:
        return '%d%s' % (coefficient.numerator(), root)
    return r'\frac{%s%s}{%d}' % ('' if coefficient.numerator() == 1 else coefficient.numerator(),
                                  root, coefficient.denominator())


def latex_density(n, delta_sq):
    """Delta = c pi^k sqrt(delta_sq) with c = V_n / pi^k, as a closed form."""
    n = int(n)
    k = n // 2
    c = ball_volume_over_pi_power(n)
    r = QQ(delta_sq)
    p, q = r.numerator(), r.denominator()
    m = ZZ(p * q)
    s = m.squarefree_part()
    t = ZZ((m // s).sqrt())
    coefficient = c * QQ(t) / q
    pi_power = '' if k == 0 else (r'\pi' if k == 1 else r'\pi^{%d}' % k)
    root = '' if s == 1 else r'\sqrt{%d}' % s
    head = root + (r'\,' if root and pi_power else '') + pi_power
    if not head:
        return latex_rational(coefficient)
    if coefficient == 1:
        return head
    if coefficient.denominator() == 1:
        return '%d%s' % (coefficient.numerator(), head)
    num = '' if coefficient.numerator() == 1 else str(coefficient.numerator())
    return r'\frac{%s%s}{%d}' % (num, head, coefficient.denominator())


def latex_hermite(n, mu, det):
    """gamma = mu det^(-1/n) as a product of prime powers with rational
    exponents, numerator over denominator."""
    n = int(n)
    mu, det = QQ(mu), QQ(det)
    primes = set()
    for r in (mu, det):
        primes.update(p for p, _ in ZZ(r.numerator()).factor())
        primes.update(p for p, _ in ZZ(r.denominator()).factor())
    up, down = [], []
    for p in sorted(primes):
        e = QQ(mu.valuation(p)) - QQ(det.valuation(p)) / n
        if e == 0:
            continue
        target = up if e > 0 else down
        target.append((p, abs(e)))

    def render(factors):
        integer = ZZ(1)
        parts = []
        for p, e in factors:
            if e.denominator() == 1:
                integer *= ZZ(p) ** ZZ(e)
            elif e == QQ(1) / 2:
                parts.append(r'\sqrt{%d}' % p)
            else:
                parts.append(r'%d^{%d/%d}' % (p, e.numerator(), e.denominator()))
        if integer != 1 or not parts:
            parts.insert(0, str(integer))
        return r'\cdot '.join(parts) if len(parts) > 1 and parts[0] != '1' else ''.join(parts)

    top = render(up)
    if not down:
        return top
    return r'\frac{%s}{%s}' % (top, render(down))


#: Which lattices are proven optimal, and the theorem: 'lattice' for the
#: densest lattice packing of its dimension, 'all' for the densest packing
#: of any kind.
OPTIMAL = {
    ('Z', 1): ('all', None),
    ('A', 1): ('all', None),
    ('A', 2): ('all', 'ThueFejesToth'),
    ('A', 3): ('all', 'Hales'),
    ('D', 4): ('lattice', 'KZ'),
    ('D', 5): ('lattice', 'KZ'),
    ('E', 6): ('lattice', 'Blichfeldt'),
    ('E', 7): ('lattice', 'Blichfeldt'),
    ('E', 8): ('all', 'Viazovska'),
    ('Lambda', 24): ('all', 'CKMRV'),
}

#: Who proved that the lattice attaining Hermite's constant gamma_n is the
#: one listed, by dimension: the reference keys of the table document.
HERMITE_PROOF = {1: None, 2: 'Lagrange', 3: 'Gauss', 4: 'KZ', 5: 'KZ',
                 6: 'Blichfeldt', 7: 'Blichfeldt', 8: 'Blichfeldt', 24: 'CohnKumar'}

#: Lambda_n for n <= 8, by name.
LAMINATED_ALIAS = {('Z', 1): 1, ('A', 2): 2, ('A', 3): 3, ('D', 4): 4, ('D', 5): 5,
                   ('E', 6): 6, ('E', 7): 7, ('E', 8): 8}

#: Where the corpus already holds a value: the exact 1, pi/4 and pi/6 in the
#: table of rational multiples of pi, sqrt 2 and 2/sqrt 3 in the table of
#: quadratic algebraic numbers (addresses read off search results).
EQUALS = {
    ('Z', 2, 'density'): 'HREF{Rational_multiples_of_pi#1/4}',
    ('Z', 3, 'density'): 'HREF{Rational_multiples_of_pi#1/6}',
    ('D', 4, 'hermite'): 'HREF{Algebraic_numbers_of_degree_2#1,0,-2,2}',
    ('A', 2, 'hermite'): 'HREF{Algebraic_numbers_of_degree_2#3,0,-4,2}',
}


def alias_note(family, n):
    n = int(n)
    notes = []
    if (family, n) in LAMINATED_ALIAS:
        notes.append(r'$%s=\Lambda_{%d}$' % (latex_name(family, n), LAMINATED_ALIAS[(family, n)]))
    if (family, n) == ('A', 1):
        notes.append(r'$A_1=\sqrt{2}\,\mathbb{Z}$')
    if (family, n) == ('A', 3):
        notes.append(r'$A_3=D_3$, the face-centred cubic lattice')
    if (family, n) == ('A*', 3):
        notes.append(r'$A_3^{*}$ is the body-centred cubic lattice')
    if (family, n) == ('Lambda', 16):
        notes.append(r'$\Lambda_{16}=BW_{16}$, the Barnes–Wall lattice')
    if (family, n) == ('Lambda', 24):
        notes.append(r'$\Lambda_{24}$ is the Leech lattice')
    if (family, n) == ('K', 12):
        notes.append(r'$K_{12}$ is the Coxeter–Todd lattice')
    return notes


def status_note(family, n):
    n = int(n)
    if (family, n) in OPTIMAL:
        kind, who = OPTIMAL[(family, n)]
        if kind == 'all':
            return 'the densest packing of any kind in dimension %d' % n + (' CITE{%s}' % who if who else '')
        return 'the densest lattice packing in dimension %d CITE{%s}' % (n, who)
    if family == 'Lambda' and n in (11, 12, 13):
        return (r'not the densest lattice packing known in dimension %d: $K_{%d}$ has centre density $%s$'
                % (n, n, r'\frac{1}{27}' if n == 12 else r'\frac{\sqrt{3}}{54}'))
    if family == 'Lambda' or (family, n) == ('K', 12):
        return 'the densest lattice packing known in dimension %d CITE{Catalogue-density}' % n
    return None


def comment(family, n, expression, values):
    n = int(n)
    name = latex_name(family, n)
    det, mu, tau = values['det'], values['mu'], values['tau']
    delta_sq = (mu / 4) ** n / det
    parts = []
    if expression == 'density':
        parts.append(r'$\Delta(%s)=%s$' % (name, latex_density(n, delta_sq)))
        status = status_note(family, n)
        if status:
            parts.append(status)
    elif expression == 'centre':
        parts.append(r'$\delta(%s)=%s$' % (name, latex_sqrt_of_rational(delta_sq)))
        parts.append(r'$\det=%s$, $\mu=%s$, kissing number $%d$' % (latex_rational(det), latex_rational(mu), tau))
    else:
        parts.append(r'$\gamma(%s)=%s$' % (name, latex_hermite(n, mu, det)))
        if (family, n) in OPTIMAL and OPTIMAL[(family, n)][0] in ('all', 'lattice'):
            who = HERMITE_PROOF[n]
            parts.append(r"Hermite's constant $\gamma_{%d}$" % n + (' CITE{%s}' % who if who else ''))
    parts.extend(alias_note(family, n))
    return '; '.join(parts)


class LatticePackingDensities(numberdb.Generator):

    table = 'TBD'
    parameters = ('family', 'n', 'expression')
    type = 'R'
    digits = 100
    rigour = 'proven'

    def enumerate(self, top=TOP):
        for family, dimensions in FAMILIES:
            for n in dimensions:
                if n > top:
                    continue
                for expression in EXPRESSIONS:
                    yield {'family': family, 'n': n, 'expression': expression}

    def value(self, params, digits):
        family, n, expression = params['family'], int(params['n']), params['expression']
        if expression not in EXPRESSIONS:
            raise ValueError('expression is one of %s, not %r' % (', '.join(EXPRESSIONS), expression))
        bits = numberdb.bits(digits, losing=WORKING_GUARD)
        values = cached(family, n, bits)
        entry = {'number': values[expression],
                 'comment': comment(family, n, expression, values)}
        if (family, n, expression) in EQUALS:
            entry['equals'] = EQUALS[(family, n, expression)]
        elif values[expression] == 1 and not hasattr(values[expression], 'rad'):
            entry['equals'] = 'HREF{One}'
        return entry


_cache = {}


def cached(family, n, bits):
    key = (family, int(n), int(bits))
    if key not in _cache:
        _cache[key] = compute(family, n, bits)
    return _cache[key]


if __name__ == '__main__':
    generator = LatticePackingDensities()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='density, centre density and Hermite number of Z^n, the root '
                    'lattices, their duals, the laminated lattices and K_12 for '
                    'n <= %d: exact rationals where rational, balls otherwise, from '
                    'integral Gram matrices with the kissing number and determinant '
                    'of every lattice checked before it is written' % TOP))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
