"""Classical-lattice Gram matrices shared with numberdb.org/T147.

The catalogue Gram blocks and the `gram()` convention are copied from the
committed T147 generator at b6f02bc. This table needs the same integral Gram
matrices because the Epstein zeta function is scale-dependent.
"""

import numberdb.sage as _numberdb  # Initialises Sage before named ring imports.
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.matrix.constructor import matrix
from sage.libs.pari.all import pari

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
