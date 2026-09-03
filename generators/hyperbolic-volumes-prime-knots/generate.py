"""Hyperbolic volumes of the prime knots with at most ten crossings -- numberdb.org/T141

    Vol(S^3 \\ K),   the volume of the complete hyperbolic metric on the complement,

for every hyperbolic prime knot K = n_k of the Rolfsen table with at most ten
crossings: 243 knots, every prime knot with 3 <= n <= 10 crossings except the
six torus knots 3_1, 5_1, 7_1, 9_1, 8_19 and 10_124. Vol(4_1) = 2.0298832128...
is the smallest, Vol(10_123) = 17.0857094829... the largest.

Run it with SageMath and SnapPy:

    $ sage -pip install numberdb snappy   # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**Which manifold.** The knot n_k is Sage's `Knots().from_table(n, k)`, the
closure of the braid word `small_knots_table[(n, k)]` (Knot Atlas's), the
same knot the tables of Alexander, Jones and Conway polynomials of these
knots are about. SnapPy triangulates its exterior from that braid closure,
`Link(braid_closure=word).exterior()`. SnapPy's own Rolfsen table,
`Manifold('n_k')`, is not used, for two reasons found when this was written:
it numbers the ten-crossing knots as Rolfsen did before Perko (166 of them,
`10_161` and `10_162` isometric, so the after-Perko 10_k for k >= 162 is its
10_{k+1}), and its `10_83` and `10_86` are each other's -- neither is
isometric to the exterior built from the braid word or from KnotInfo's
diagram of the knot of that name, while the exteriors of the braid word and
of KnotInfo's diagram are isometric for all 243 knots.

**These digits are proven.** SnapPy supplies only combinatorics and a
starting point: the gluing equations of the triangulation, which are
integers, and its floating-point shapes. Everything after that is arb ball
arithmetic, written out below rather than taken from SnapPy's verify
module, so that the certificate is visible:

  1. A Krawczyk test on a square system of rectangular gluing equations --
     n - 1 edge equations and the meridian, in the logarithmic form
     log(c prod z_i^a (1-z_i)^b) = 0 -- proves that a box of complex balls
     contains a solution. The dropped edge equation is implied by the others,
     because the n edge equations multiply to the identity (each tetrahedron
     contributes (z z' z'')^2 = 1); the generator checks that on the integer
     exponents before it drops one.
  2. Every shape ball has positive imaginary part, and every logarithmic
     gluing equation, evaluated on the balls with principal logarithms, is
     within 0.1 of its value, 2 pi i on an edge and 0 on the meridian and
     the longitude. At the certified point each sum is an exact multiple of
     pi i, so this pins it: the dihedral angles sum to 2 pi around every
     edge, which makes the triangulation a hyperbolic structure, and the
     meridian holonomy is a translation with rotation 0, which makes the
     cusp complete. This is HIKMOT's criterion, as SnapPy's `verify_hyperbolicity`
     also applies it.
  3. The volume is the sum of the Bloch-Wigner dilogarithms D(z_i) = Im Li_2(z_i)
     + arg(1 - z_i) log|z_i| of the shape balls, arb's polylog, and the
     written digits are those the resulting ball supports.

By Mostow-Prasad rigidity the complete structure is unique, so the number is
the knot's. What is not proven here is the identification of the manifold
with the complement of the knot called n_k: that rests on Knot Atlas's braid
words, checked as described above against KnotInfo's diagrams.

**Checked outside the generator, when this was written:** all 243 balls
overlap KnotInfo's ten decimals, and agree with SnapPy's quad-double
volumes to 62 digits (five of them differ in the 63rd, which is quad-double's
roundoff over a dozen tetrahedra), with the controls that must fail failing; Vol(4_1) overlaps 2 Cl_2(pi/3)
computed independently in arb and the 58 digits of OEIS A091518; the six
torus knots are refused by the same code (their triangulations have flat
tetrahedra). The pairs of knots that KnotInfo lists with the same ten
decimals were certified the same way from KnotInfo's diagrams, and where an
entry says two volumes agree to the hundred digits listed, the two balls
overlap at that precision.

**Working precision.** Measured over the whole table at 100 digits with a
guard of 64 bits: the widest ball (10_122, nineteen tetrahedra) has radius
4e-114, supporting 113 digits; the figure-eight's supports 117. The guard
costs nothing and the margin is what it buys.
"""

import sys

import numberdb.sage as numberdb
#The knot table imports sage.functions, which cannot initialise the symbolic
#ring from inside its own import; brought up first, by name, it can.
import sage.symbolic.ring                                       # noqa: F401
from sage.knots.knot_table import small_knots_table
from sage.rings.complex_arb import ComplexBallField
from sage.rings.real_arb import RealBallField

#: Bits of working precision beyond what the written digits need; measured,
#: see the docstring.
WORKING_GUARD = 64

#: Prime knots with n crossings, n = 3, ..., 10: OEIS A002863.
COUNTS = {3: 1, 4: 1, 5: 2, 6: 3, 7: 7, 8: 21, 9: 49, 10: 165}

#: The torus knots among them, with (p, q): not hyperbolic, not in the table.
TORUS = {(3, 1): (2, 3), (5, 1): (2, 5), (7, 1): (2, 7), (9, 1): (2, 9),
         (8, 19): (3, 4), (10, 124): (3, 5)}

#: Rolfsen lists the alternating knots of each crossing number first; these are
#: the indices at which the non-alternating ones begin (KnotInfo's
#: `alternating` column). Below eight crossings every prime knot is alternating.
FIRST_NONALTERNATING = {8: 19, 9: 42, 10: 124}

GEOMETRIC = 'all tetrahedra positively oriented'

#: Names a reader would recognise.
NAMED = {
    (4, 1): 'the figure-eight knot',
    (5, 2): 'the three-twist knot',
    (6, 1): 'the stevedore knot',
    (6, 2): 'the Miller Institute knot',
    (7, 4): 'the endless knot',
    (8, 18): 'the Carrick mat',
    (10, 161): 'the Perko pair, listed twice by Rolfsen as $10_{161}$ and $10_{162}$',
}

#: The complements that are in SnapPy's census of orientable cusped hyperbolic
#: 3-manifolds (up to nine tetrahedra), by their census name: SnapPy's
#: identify() on the exterior built here, when this was written.
CENSUS = {
    (4, 1): 'm004', (5, 2): 'm015', (6, 1): 'm032', (6, 2): 'm289',
    (6, 3): 's912', (7, 2): 'm053', (7, 3): 'm340', (7, 4): 's648',
    (7, 5): 'v3310', (7, 6): 't11291', (7, 7): 't12656', (8, 1): 'm074',
    (8, 2): 's526', (8, 3): 's726', (8, 4): 's862', (8, 5): 't10932',
    (8, 6): 't12395', (8, 7): 't11034', (8, 8): 'o9_37770', (8, 9): 't12587',
    (8, 10): 'o9_43874', (8, 11): 'o9_42258', (8, 13): 'o9_43592',
    (8, 20): 'm222', (8, 21): 'v3505', (9, 2): 'm094', (9, 3): 's558',
    (9, 4): 's870', (9, 5): 'v2284', (9, 6): 't11675', (9, 7): 'o9_40064',
    (9, 8): 'o9_41611', (9, 9): 'o9_40076', (9, 10): 'o9_44057',
    (9, 11): 'o9_42277', (9, 35): 'o9_39339', (9, 42): 'm199',
    (9, 43): 'v2623', (9, 44): 't12271', (9, 45): 'o9_43771', (9, 46): 'm372',
    (10, 1): 's016', (10, 2): 'v1217', (10, 3): 'v2362', (10, 4): 'v2488',
    (10, 5): 'o9_32208', (10, 6): 'o9_42963', (10, 8): 'v2858',
    (10, 9): 'o9_42320', (10, 20): 'o9_42467', (10, 46): 'o9_36697',
    (10, 125): 's385', (10, 126): 't10499', (10, 128): 'v2553',
    (10, 130): 't09901', (10, 132): 'm201', (10, 133): 'o9_37732',
    (10, 134): 'o9_42974', (10, 136): 'o9_37080', (10, 139): 'm389',
    (10, 140): 's704', (10, 141): 'o9_39277', (10, 142): 't09859',
    (10, 145): 's580', (10, 152): 'o9_43609', (10, 153): 't12200',
    (10, 161): 'v2166',
}

#: Knots whose volume agrees with this entry's to the hundred digits listed:
#: KnotInfo's ten decimals name them, and the balls certified from KnotInfo's
#: diagrams of the knots to thirteen crossings overlap the entry's ball.
SAME_VOLUME = {
    (5, 2): '$12n_{242}$, the $(-2,3,7)$ pretzel knot',
    (6, 2): '$12n_{121}$',
    (6, 3): '$13n_{469}$',
    (7, 5): '$13n_{1153}$',
    (8, 18): '$12n_{276}$',
    (8, 20): '$11n_{38}$',
    (9, 42): '$10_{132}$',
    (9, 43): '$12n_{243}$',
    (10, 126): '$13n_{912}$',
    (10, 128): '$11n_{57}$',
    (10, 130): '$13n_{1021}$',
    (10, 132): '$9_{42}$',
    (10, 134): '$13n_{1164}$',
}


def names():
    """(n, k) for every hyperbolic knot of the table, in table order."""
    keys = sorted(key for key in small_knots_table if key[0])
    counts = {}
    for n, k in keys:
        counts[n] = counts.get(n, 0) + 1
    if counts != COUNTS:
        raise ArithmeticError('the knot table holds %s knots per crossing '
                              'number, not the Rolfsen table %s' % (counts, COUNTS))
    return [key for key in keys if key not in TORUS]


def triangulation(n, k):
    """SnapPy's triangulation of the exterior of the braid closure.

    Returned as plain data: the rectangular gluing equations (rows (A, B, c),
    meaning c prod z_i^A_i (1 - z_i)^B_i = 1; the n edge equations, then the
    meridian and the longitude), the logarithmic ones (rows of 3n integers,
    coefficients of log z_i, log z'_i, log z''_i), and the shapes as pairs of
    decimal strings. Everything else in this file is SnapPy-free.
    """
    try:
        from snappy import Link
    except ImportError:
        raise ImportError('SnapPy is needed for the triangulations: sage -pip install snappy')
    strands, word = small_knots_table[(n, k)]
    M = Link(braid_closure=[int(x) for x in word]).exterior()
    if M.num_cusps() != 1:
        raise ArithmeticError('%d_%d: the exterior has %d cusps' % (n, k, M.num_cusps()))
    for attempt in range(50):
        if M.solution_type() == GEOMETRIC:
            break
        M.randomize()
    else:
        raise ArithmeticError('%d_%d: no geometric triangulation found' % (n, k))
    rect = [([int(a) for a in A], [int(b) for b in B], int(c))
            for A, B, c in M.gluing_equations(form='rect')]
    rows = M.gluing_equations()
    rows = rows.data if hasattr(rows, 'data') else rows.rows()
    log = [[int(x) for x in row] for row in rows]
    H = M.high_precision()
    shapes = [[str(s.real()), str(s.imag())] for s in H.tetrahedra_shapes('rect')]
    return {'rect': rect, 'log': log, 'shapes': shapes}


#-- the certificate ---------------------------------------------------------

class NotCertified(ArithmeticError):
    pass


def log_residuals(equations, z, CB):
    """log(c prod z^a (1-z)^b) for each equation; zero at a solution."""
    one = CB(1)
    out = []
    for A, B, c in equations:
        prod = CB(c)
        for a, b, zi in zip(A, B, z):
            if a:
                prod *= zi ** int(a)
            if b:
                prod *= (one - zi) ** int(b)
        out.append(prod.log())
    return out


def jacobian(equations, z, CB):
    """d/dz_i of log_residuals: a_i / z_i - b_i / (1 - z_i)."""
    one = CB(1)
    inv = [one / zi for zi in z]
    inv1 = [one / (one - zi) for zi in z]
    rows = []
    for A, B, c in equations:
        rows.append([CB(int(a)) * inv[i] - CB(int(b)) * inv1[i]
                     for i, (a, b) in enumerate(zip(A, B))])
    return rows


def midpoint(ball, CB):
    return CB(ball.mid())


def inverse_of_midpoints(J, CB):
    """An approximate inverse of the matrix of midpoints: Gauss-Jordan with
    partial pivoting, returned as exact (zero-radius) balls. Any matrix serves
    the Krawczyk test; a bad one only makes the test fail."""
    n = len(J)
    M = [[midpoint(J[i][j], CB) for j in range(n)] + [CB(1 if i == j else 0) for j in range(n)]
         for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(M[r][col].mid()))
        if abs(M[pivot][col].mid()) == 0:
            raise NotCertified('the Jacobian of the chosen equations is singular')
        M[col], M[pivot] = M[pivot], M[col]
        p = M[col][col]
        M[col] = [midpoint(x / p, CB) for x in M[col]]
        for r in range(n):
            if r != col and M[r][col] != 0:
                factor = M[r][col]
                M[r] = [midpoint(x - factor * y, CB) for x, y in zip(M[r], M[col])]
    return [row[n:] for row in M]


def matmul_vec(C, v):
    zero = C[0][0].parent()(0)
    return [sum((C[i][j] * v[j] for j in range(len(v))), zero) for i in range(len(C))]


def contained_in_interior(k, x, RB):
    """Whether the ball k lies inside the ball x, real and imaginary parts
    separately, by a rigorous comparison of midpoints and radii."""
    for kk, xx in ((k.real(), x.real()), (k.imag(), x.imag())):
        distance = (RB(kk.mid()) - RB(xx.mid())).abs() + RB(kk.rad())
        if not bool(distance < RB(xx.rad())):
            return False
    return True


def krawczyk(system, z0, first, C, X, CB):
    """K(X) = z0 - C f(z0) + (I - C J(X)) (X - z0); `first` is z0 - C f(z0).

    If K(X) lies inside X, then X contains exactly one solution of f = 0, and
    so does K(X)."""
    n = len(z0)
    JX = jacobian(system, X, CB)
    CJ = [[sum((C[i][l] * JX[l][j] for l in range(n)), CB(0)) for j in range(n)] for i in range(n)]
    delta = [X[j] - z0[j] for j in range(n)]
    return [first[i] + sum(((CB(1 if i == j else 0) - CJ[i][j]) * delta[j] for j in range(n)), CB(0))
            for i in range(n)]


def bloch_wigner(z, CB):
    """D(z) = Im Li_2(z) + arg(1 - z) log|z|, the volume of the ideal tetrahedron of shape z."""
    one = CB(1)
    return (one - z).arg() * z.abs().log() + z.polylog(2).imag()


def certify(rect, log, shapes, bits, newton_steps=6, refinements=4):
    """Balls certified to contain the shapes of the complete structure, and the volume.

    Returns (volume, shape balls, exponent), the box tried having radius
    2^-exponent. Raises NotCertified when any step fails.
    """
    CB = ComplexBallField(bits)
    RB = RealBallField(bits)
    n = len(shapes)
    if len(rect) != n + 2 or len(log) != n + 2:
        raise NotCertified('expected %d edge rows and two cusp rows, got %d' % (n, len(rect)))
    edges, meridian = rect[:n], rect[n]
    for i in range(n):
        if sum(A[i] for A, B, c in edges) != 0 or sum(B[i] for A, B, c in edges) != 0:
            raise NotCertified('the edge equations do not multiply to 1 in variable %d' % i)
    sign = 1
    for A, B, c in edges:
        sign *= int(c)
    if sign != 1:
        raise NotCertified('the edge equations multiply to -1')
    system = edges[:-1] + [meridian]

    #Newton steps on midpoints, so that the box can be small.
    try:
        z0 = [CB(RB(str(re).replace(' ', '')), RB(str(im).replace(' ', ''))) for re, im in shapes]
    except (ValueError, TypeError) as trouble:
        raise NotCertified('a starting shape is not a number: %s' % trouble)
    for _ in range(newton_steps):
        f = log_residuals(system, z0, CB)
        C = inverse_of_midpoints(jacobian(system, z0, CB), CB)
        z0 = [midpoint(z0[i] - v, CB) for i, v in enumerate(matmul_vec(C, f))]
    f0 = log_residuals(system, z0, CB)
    C = inverse_of_midpoints(jacobian(system, z0, CB), CB)
    first = [z0[i] - v for i, v in enumerate(matmul_vec(C, f0))]

    X = None
    exponent = bits - 8
    while exponent > 8:
        radius = RB(2) ** (-exponent)
        box = [z.add_error(radius) for z in z0]
        K = krawczyk(system, z0, first, C, box, CB)
        if all(contained_in_interior(k, x, RB) for k, x in zip(K, box)):
            X = K
            break
        exponent -= 12
    if X is None:
        raise NotCertified('no box around the approximate solution passed the Krawczyk test')
    for _ in range(refinements):
        K = krawczyk(system, z0, first, C, X, CB)
        if all(contained_in_interior(k, x, RB) for k, x in zip(K, X)):
            X = K
        else:
            break

    for i, x in enumerate(X):
        if not bool(x.imag() > 0):
            raise NotCertified('shape %d is not certified to have positive imaginary part: %s' % (i, x))

    one = CB(1)
    logs = []
    for x in X:
        logs.extend([x.log(), (one / (one - x)).log(), ((x - one) / x).log()])
    two_pi_i = CB(0, 2) * CB.pi()
    for r, row in enumerate(log):
        total = sum((CB(int(e)) * l for e, l in zip(row, logs) if e), CB(0))
        target = two_pi_i if r < n else CB(0)
        if not (total - target).contains_zero():
            raise NotCertified('logarithmic equation %d misses its value %s: %s' % (r, target, total))
        if not (bool(total.real().rad() < 0.1) and bool(total.imag().rad() < 0.1)):
            raise NotCertified('logarithmic equation %d is not pinned: %s' % (r, total))

    volume = sum((bloch_wigner(x, CB) for x in X), RB(0))
    if not volume.is_finite():
        raise NotCertified('the volume ball is not finite')
    return volume, X, exponent


#-- the table ---------------------------------------------------------------

def subscript(n, k):
    return '$%d_%d$' % (n, k) if k < 10 else '$%d_{%d}$' % (n, k)


def comment(n, k):
    parts = [subscript(n, k)]
    if (n, k) in NAMED:
        parts[0] += ', ' + NAMED[(n, k)]
    if (n, k) in CENSUS:
        parts.append('the complement is %s in the SnapPy census' % CENSUS[(n, k)])
    parts.append('non-alternating' if k >= FIRST_NONALTERNATING.get(n, 10 ** 6) else 'alternating')
    if (n, k) == (4, 1):
        parts.append('$\\mathrm{Vol}=2\\,\\mathrm{Cl}_2(\\pi/3)$, the smallest volume of any '
                     'hyperbolic knot complement')
    if (n, k) == (10, 123):
        parts.append('the largest volume among the prime knots with at most ten crossings')
    if (n, k) in SAME_VOLUME:
        parts.append('the volume agrees to the hundred digits listed with that of %s'
                     % SAME_VOLUME[(n, k)])
    return '; '.join(parts)


class HyperbolicVolumes(numberdb.Generator):

    table = 'T141'
    parameters = ('n', 'k')
    type = 'R'
    digits = 100
    rigour = 'proven'

    def enumerate(self):
        for n, k in names():
            yield {'n': int(n), 'k': int(k)}

    def value(self, params, digits):
        n, k = int(params['n']), int(params['k'])
        if (n, k) not in names():
            raise ValueError('%d_%d is not a hyperbolic prime knot of the Rolfsen table' % (n, k))
        data = triangulation(n, k)
        bits = numberdb.bits(digits, losing=WORKING_GUARD)
        volume, shapes, exponent = certify(data['rect'], data['log'], data['shapes'], bits)
        return {'number': volume, 'comment': comment(n, k)}


if __name__ == '__main__':
    generator = HyperbolicVolumes()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='hyperbolic volumes of the 243 hyperbolic prime knots with at '
                    'most ten crossings, each certified in ball arithmetic by a '
                    'Krawczyk test on the gluing equations of a SnapPy '
                    'triangulation of the braid closure and a sum of Bloch-Wigner '
                    'dilogarithms'))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
