"""Covering radii and covering densities of the classical lattices -- numberdb.org/TBD

For a lattice L in R^n with Gram matrix G, minimal norm mu = min v^T G v over
nonzero v in Z^n, packing radius rho = sqrt(mu)/2, covering radius
R = max_x min_{v in L} |x - v| and determinant det L = det G:

    R / rho                                            the normalised covering radius
    Theta(L) = V_n R^n / sqrt(det L),  V_n = pi^(n/2)/Gamma(n/2 + 1)    the covering density

for the lattices Z^n, A_n, D_n, E_6, E_7, E_8, their duals A_n^*, D_n^*,
E_6^*, E_7^* and the Leech lattice Lambda_24, every one of dimension n <= 24,
under the parameters `family`, `n` and `expression` (radius or density).
Both quantities are unchanged when L is scaled, so no scaling of a named
lattice has to be chosen.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**Where the lattices come from.** Z^n is the identity matrix; A_n, D_n and
E_n are their Cartan matrices (minimal norm 2, determinants n+1, 4, 3, 2, 1);
a dual is the adjugate of the Cartan matrix, which is det(G) times the
inverse and so integral, with norms det(G) times those of the dual proper;
the Leech lattice is the GRAM block of its page in the Nebe-Sloane
Catalogue of Lattices, minimal norm 4. The determinant, minimal norm and
number of minimal vectors of every Gram matrix are recomputed (PARI's
qfminim) and must equal the known values before the lattice is used.

**Where the covering radii come from.** R^2 is a theorem for each family,
stated in the scaling of the Gram matrix used here (see `covering_radius_sq`):

    Z^n      n/4                                  the deep hole (1/2, ..., 1/2)
    A_n      a(n+1-a)/(n+1), a = floor((n+1)/2)   Conway-Sloane, chapter 4, section 6.1
    D_n      n/4 for n >= 4                        chapter 4, section 7.1
    E_6, E_7, E_8   4/3, 3/2, 1                    chapter 4, section 8
    A_n^*    n(n+2)/(12(n+1)) at mu = n/(n+1)      chapter 4, section 6.6 (Gameckii, Bleicher)
    D_n^*    n/8 (n even), (2n-1)/16 (n odd) at mu = 1
    E_6^*    2/3 at mu = 4/3;  E_7^*  7/8 at mu = 3/2
    Lambda_24   2 at mu = 4                        Conway, Parker and Sloane

The value for D_n^* = Z^n + (Z^n + (1/2)^n) follows from d(x, L)^2 =
min(sum x_i^2, sum (1/2 - x_i)^2) for x in [0, 1/2]^n, a maximum of a convex
function over the polytope sum x_i <= n/4, attained at (1/2^(n/2), 0^(n/2))
for even n and ((1/2)^((n-1)/2), 1/4, 0^((n-1)/2)) for odd n. The values
for E_6^* and E_7^* were computed exactly from their Voronoi cells, as were
all the values with n <= 8, in the checks run when the table was made.

**What is certified inside this file.** For every lattice of dimension
n <= CERTIFY_TO the covering radius is recomputed before use, exactly, as
the largest vertex norm of the Voronoi cell {x : x.v <= v.v/2 for all v in L}
built as a rational polytope from all lattice vectors of norm at most B,
with B raised until 4 R^2 <= B; every Voronoi-relevant vector v has
|v| <= 2R, so this proves the cell is complete and R^2 exact. A
disagreement with the formula is an error rather than an entry. Beyond that
dimension the formulas are the theorems cited.

**Exact arithmetic up to the last step.** (R/rho)^2 = 4 R^2 / mu and
Theta^2 / pi^(2k) = (V_n/pi^k)^2 R^(2n) / det L, k = floor(n/2), are exact
rationals; a value that is rational is returned as one (R/rho = 2 for Z^4,
Theta = 1 for Z), the rest are balls: a square root, and for Theta the
product with pi^k. No division of Python integers occurs anywhere in this
file; every quotient is between Sage rationals.

**These digits are proven.** With the guard below, the widest ball in the
table, relative to its value, has radius 4.5e-119 (measured at 100 digits over every entry: Theta(A_24)), so
100 digits are supported with room.
"""

import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField
from sage.matrix.constructor import matrix
from sage.libs.pari.all import pari
from sage.geometry.polyhedron.constructor import Polyhedron

#: Bits of working precision beyond what the written digits need. Measured
#: over the whole table at 100 digits: the widest ball, relative to its
#: value, is Theta(A_24) with relative radius 4.5e-119.
WORKING_GUARD = 64

#: The largest dimension listed. The Leech lattice is where the proven
#: results and the families of the companion table of packing densities end.
TOP = 24

#: Every lattice of dimension at most this is re-certified from its Voronoi
#: cell on every run (about a minute in all); the cells of dimension 7 and 8
#: were computed once, in the checks made when the table was built, and the
#: formulas are theorems in every dimension.
CERTIFY_TO = 6

#: The families and the dimensions each is listed in, as in the table of
#: packing densities: a dual similar to its own lattice (A_1^*, A_2^*, D_4^*)
#: and D_3 = A_3 are listed once, under the root-system name.
FAMILIES = (
    ('Z', range(1, TOP + 1)),
    ('A', range(1, TOP + 1)),
    ('D', range(4, TOP + 1)),
    ('E', (6, 7, 8)),
    ('A*', range(3, TOP + 1)),
    ('D*', range(5, TOP + 1)),
    ('E*', (6, 7)),
    ('Lambda', (24,)),
)

EXPRESSIONS = ('radius', 'density')


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


#: The Gram matrix of the Leech lattice from the Nebe-Sloane Catalogue of
#: Lattices (Leech.html), lower triangle, minimal norm 4: even, unimodular
#: and without vectors of norm 2, hence the Leech lattice by Conway's
#: uniqueness theorem.
LEECH_GRAM = [
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
]


def leech():
    n = 24
    G = [[0] * n for _ in range(n)]
    for i in range(n):
        if len(LEECH_GRAM[i]) != i + 1:
            raise ValueError('Leech: row %d of the lower triangle has %d entries' % (i, len(LEECH_GRAM[i])))
        for j in range(i + 1):
            G[i][j] = G[j][i] = LEECH_GRAM[i][j]
    return matrix(ZZ, G)


def gram(family, n):
    """An integral Gram matrix of the lattice, and the factor s by which its
    norms are scaled relative to the scaling the comments quote (s = 1
    except for the duals, whose adjugate Gram matrix is det(G) times the
    dual's own)."""
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
        if n != 24:
            raise ValueError('Lambda_n is listed for n = 24 only')
        return leech(), ZZ(1)
    raise ValueError('no family %r' % family)


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
        return 196560
    raise ValueError('no family %r' % family)


def known_determinant(family, n):
    """det L in the scaling the comments quote."""
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
        return QQ(1)
    raise ValueError('no family %r' % family)


def covering_radius_sq(family, n):
    """R^2 in the scaling the comments quote (the root lattices at minimal
    norm 2, Z^n and D_n^* at 1, A_n^* at n/(n+1), E_6^* at 4/3, E_7^* at
    3/2, the Leech lattice at 4), as an exact rational."""
    n = int(n)
    if family == 'Z':
        return QQ(n) / 4
    if family == 'A':
        a = (n + 1) // 2
        return QQ(a * (n + 1 - a)) / (n + 1)
    if family == 'D':
        return QQ(n) / 4
    if family == 'E':
        return {6: QQ(4) / 3, 7: QQ(3) / 2, 8: QQ(1)}[n]
    if family == 'A*':
        return QQ(n * (n + 2)) / (12 * (n + 1))
    if family == 'D*':
        return QQ(n) / 8 if n % 2 == 0 else QQ(2 * n - 1) / 16
    if family == 'E*':
        return {6: QQ(2) / 3, 7: QQ(7) / 8}[n]
    if family == 'Lambda':
        return QQ(2)
    raise ValueError('no family %r' % family)


def voronoi_covering_radius_sq(G):
    """R^2 of the lattice with Gram matrix G, exactly, from its Voronoi
    cell; also the bound B used and the number of vertices.

    The cell is cut from all lattice vectors of norm <= B; the polytope so
    obtained contains the cell, so its largest vertex norm R_B^2 is at least
    R^2, and once B >= 4 R_B^2 every Voronoi-relevant vector (|v| <= 2R) has
    been used, so the polytope is the cell and R_B^2 = R^2.
    """
    n = G.nrows()
    mu = ZZ(pari(G).qfminim(None, None, 0)[1])
    bound = 2 * mu
    while True:
        found = pari(G).qfminim(bound, None, 0)
        count, vectors = int(found[0]), found[2]
        ieqs = []
        for j in range(count // 2):
            v = [ZZ(vectors[j][i]) for i in range(n)]
            Gv = [sum(G[i, k] * v[k] for k in range(n)) for i in range(n)]
            norm = sum(v[i] * Gv[i] for i in range(n))
            ieqs.append([QQ(norm) / 2] + [-c for c in Gv])
            ieqs.append([QQ(norm) / 2] + [c for c in Gv])
        cell = Polyhedron(ieqs=ieqs, base_ring=QQ)
        if not cell.is_compact():
            raise ArithmeticError('the vectors of norm <= %s do not bound the Voronoi cell' % bound)
        best = QQ(0)
        nverts = 0
        for vert in cell.vertices():
            x = [QQ(c) for c in vert]
            nverts += 1
            xn = sum(x[i] * sum(G[i, k] * x[k] for k in range(n)) for i in range(n))
            if xn > best:
                best = xn
        if 4 * best <= bound:
            return best, bound, nverts
        bound += mu


def invariants(family, n):
    """(det, mu, tau, r2): determinant, minimal norm, number of minimal
    vectors and squared covering radius, all in the scaling the comments
    quote (exact rationals), after the checks described at the top."""
    G, s = gram(family, n)
    n = G.nrows()
    det_scaled = ZZ(G.det())
    if det_scaled <= 0:
        raise ArithmeticError('%s_%d: Gram matrix is not positive definite' % (family, n))
    found = pari(G).qfminim(None, None, 0)
    tau, mu_scaled = int(found[0]), ZZ(found[1])
    del found
    det = QQ(det_scaled) / QQ(s) ** n
    mu = QQ(mu_scaled) / QQ(s)
    if tau != known_kissing_number(family, n):
        raise ArithmeticError('%s_%d: qfminim counts %d minimal vectors, the kissing number is %d'
                              % (family, n, tau, known_kissing_number(family, n)))
    if det != known_determinant(family, n):
        raise ArithmeticError('%s_%d: determinant %s, expected %s' % (family, n, det, known_determinant(family, n)))
    r2 = covering_radius_sq(family, n)
    if n <= CERTIFY_TO:
        certified, bound, nverts = voronoi_covering_radius_sq(G)
        if certified != r2 * s:
            raise ArithmeticError('%s_%d: the Voronoi cell gives R^2 = %s in the Gram scaling, the formula %s'
                                  % (family, n, certified, r2 * s))
    if 4 * r2 < mu:
        raise ArithmeticError('%s_%d: R < rho' % (family, n))
    return det, mu, tau, r2


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


def sqrt_exact_or_ball(q, RBF):
    q = QQ(q)
    if q.is_square():
        return q.sqrt()
    return RBF(q).sqrt()


def compute(family, n, bits):
    """(R/rho, Theta) as exact rationals where rational and as balls
    otherwise, with the invariants used."""
    n = int(n)
    det, mu, tau, r2 = invariants(family, n)
    RBF = RealBallField(bits)
    ratio_sq = 4 * r2 / mu                      # (R/rho)^2, exact
    theta_sq_over_pi = r2 ** n / det            # (Theta / V_n)^2, exact
    delta_sq = (mu / 4) ** n / det              # the centre density squared, as the packing table has it
    if theta_sq_over_pi != ratio_sq ** n * delta_sq:
        raise ArithmeticError('%s_%d: Theta^2 and (R/rho)^(2n) delta^2 disagree' % (family, n))
    radius = sqrt_exact_or_ball(ratio_sq, RBF)
    c = ball_volume_over_pi_power(n)
    k = n // 2
    root = sqrt_exact_or_ball(theta_sq_over_pi, RBF)
    if k == 0:
        density = c * root                       # n = 1: V_1 = 2, exact
    else:
        density = RBF(c) * RBF.pi() ** k * root
    for name, value in (('radius', radius), ('density', density)):
        if hasattr(value, 'is_finite') and not value.is_finite():
            raise ArithmeticError('%s_%d: %s is not a finite ball' % (family, n, name))
    return {'radius': radius, 'density': density,
            'det': det, 'mu': mu, 'tau': tau, 'r2': r2, 'ratio_sq': ratio_sq}


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


def latex_pi_form(n, square):
    """c pi^k sqrt(square) with c = V_n / pi^k, as a closed form."""
    n = int(n)
    k = n // 2
    c = ball_volume_over_pi_power(n)
    r = QQ(square)
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


#: Which lattices are proven to be the thinnest covering of their dimension,
#: and the reference key of the table document: 'all' among all coverings by
#: equal balls, 'lattice' among lattice coverings.
OPTIMAL = {
    ('Z', 1): ('all', None),
    ('A', 1): ('all', None),
    ('A*', 3): ('lattice', 'Bambah'),
    ('A*', 4): ('lattice', 'DeloneRyshkov'),
    ('A*', 5): ('lattice', 'RyshkovBaranovskii'),
}

#: The hexagonal lattice A_2 = A_2^* is the thinnest covering of the plane
#: by equal discs, lattice or not (Kershner).
HEXAGONAL = ('A', 2)

#: Dimensions in which a lattice covering thinner than A_n^* is known, with
#: the reference key of the table document: Schuermann and Vallentin for
#: 6, 7, 8, and Table 2 of Dutour Sikiric, Schuermann and Vallentin (the
#: least dense lattice coverings known up to dimension 24) for the rest --
#: their own lattices in 9 to 15, Coxeter lattices in 17, 19, 20, 21 and the
#: duals of the laminated lattices in 22 and 23. In dimensions 16 and 18 that
#: table lists A_n^* itself, and in 24 the Leech lattice.
BEATEN = {6: 'SV', 7: 'SV', 8: 'SV'}
BEATEN.update({n: 'DSV' for n in (9, 10, 11, 12, 13, 14, 15, 17, 19, 20, 21, 22, 23)})
LISTED_THINNEST = (16, 18)

#: Where the corpus already holds a value: pi/2 and 2pi/3 in the table of
#: rational multiples of pi, and the quadratic irrationals among the R/rho in
#: the table of algebraic numbers of degree 2, whose anchor a2,a1,a0,n is the
#: n-th root of a2 x^2 + a1 x + a0 in increasing order: R/rho = sqrt(p/q)
#: is the larger root of q x^2 - p. The addresses were read off the stored
#: tables, and only the rows that exist there are linked.
PI_TABLE = 'Rational_multiples_of_pi'
DEGREE_TWO = 'Algebraic_numbers_of_degree_2'
DEGREE_TWO_ROWS = {
    QQ(2): '1,0,-2,2', QQ(3): '1,0,-3,2', QQ(5): '1,0,-5,2',
    QQ(4) / 3: '3,0,-4,2', QQ(5) / 2: '2,0,-5,2', QQ(5) / 3: '3,0,-5,2',
}


def alias_note(family, n):
    n = int(n)
    notes = []
    if (family, n) == ('A', 1):
        notes.append(r'$A_1=\sqrt{2}\,\mathbb{Z}$')
    if (family, n) == ('A', 2):
        notes.append(r'$A_2$ is the hexagonal lattice, $A_2^{*}\cong A_2$')
    if (family, n) == ('A', 3):
        notes.append(r'$A_3=D_3$, the face-centred cubic lattice')
    if (family, n) == ('A*', 3):
        notes.append(r'$A_3^{*}$ is the body-centred cubic lattice')
    if (family, n) == ('D', 4):
        notes.append(r'$D_4^{*}\cong D_4$')
    if (family, n) == ('E', 8):
        notes.append(r'$E_8^{*}=E_8$')
    if (family, n) == ('Lambda', 24):
        notes.append(r'$\Lambda_{24}$ is the Leech lattice')
    return notes


def status_note(family, n):
    n = int(n)
    if (family, n) == HEXAGONAL:
        return 'the thinnest covering of the plane by equal discs CITE{Kershner}'
    if (family, n) in OPTIMAL:
        kind, who = OPTIMAL[(family, n)]
        if kind == 'all':
            return 'the thinnest covering of $\\mathbb{R}$ by equal intervals'
        return 'the thinnest lattice covering in dimension %d CITE{%s}' % (n, who)
    if family == 'A*' and n in BEATEN:
        return 'a thinner lattice covering in dimension %d is known CITE{%s}' % (n, BEATEN[n])
    if family == 'A*' and n in LISTED_THINNEST:
        return ('the thinnest lattice covering in dimension %d listed by Dutour Sikirić, '
                'Schürmann and Vallentin CITE{DSV}' % n)
    if family == 'A*' and n == TOP:
        return r'the Leech lattice $\Lambda_{24}$ is a thinner lattice covering CITE{DSV}'
    if (family, n) == ('E', 8):
        return 'not a locally thinnest lattice covering CITE{SVLeech}'
    if (family, n) == ('Lambda', 24):
        return 'a locally thinnest lattice covering CITE{SVLeech}'
    return None


def comment(family, n, expression, values):
    n = int(n)
    name = latex_name(family, n)
    parts = []
    if expression == 'radius':
        parts.append(r'$R/\rho=%s$' % latex_sqrt_of_rational(values['ratio_sq']))
        parts.append(r'$R^2=%s$ with $\mu=%s$' % (latex_rational(values['r2']), latex_rational(values['mu'])))
    else:
        parts.append(r'$\Theta(%s)=%s$' % (name, latex_pi_form(n, values['r2'] ** n / values['det'])))
        status = status_note(family, n)
        if status:
            parts.append(status)
    parts.extend(alias_note(family, n))
    return '; '.join(parts)


def equals_link(family, n, expression, values):
    number = values[expression]
    exact = not hasattr(number, 'rad')
    if exact and number == 1:
        return 'HREF{One}'
    if expression == 'radius' and not exact and values['ratio_sq'] in DEGREE_TWO_ROWS:
        return 'HREF{%s#%s}' % (DEGREE_TWO, DEGREE_TWO_ROWS[values['ratio_sq']])
    if expression == 'density' and int(n) in (2, 3):
        square = values['r2'] ** int(n) / values['det']
        if QQ(square).is_square():
            return 'HREF{%s#%s}' % (PI_TABLE, ball_volume_over_pi_power(n) * QQ(square).sqrt())
    return None


class LatticeCoveringDensities(numberdb.Generator):

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
        link = equals_link(family, n, expression, values)
        if link:
            entry['equals'] = link
        return entry


_cache = {}


def cached(family, n, bits):
    key = (family, int(n), int(bits))
    if key not in _cache:
        _cache[key] = compute(family, n, bits)
    return _cache[key]


if __name__ == '__main__':
    generator = LatticeCoveringDensities()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='normalised covering radius R/rho and covering density Theta of Z^n, '
                    'the root lattices, their duals and the Leech lattice for n <= %d: exact '
                    'rationals where rational, balls otherwise, from integral Gram matrices '
                    'with the kissing number and determinant of every lattice checked and the '
                    'covering radius recomputed from the Voronoi cell for n <= %d' % (TOP, CERTIFY_TO)))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
