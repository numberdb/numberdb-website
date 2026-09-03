"""Conway polynomials of the prime knots with at most ten crossings -- numberdb.org/T140

    nabla_K(z) in Z[z], with nabla(unknot) = 1 and nabla(L+) - nabla(L-) = z nabla(L0),

for every knot n_k of the Rolfsen table, numbered after Perko: the unknot 0_1
and the 249 prime knots with 3 <= n <= 10 crossings that Sage ships as
`Knots().from_table(n, k)` (from Knot Atlas's braid words). nabla(3_1) =
z^2 + 1, nabla(4_1) = -z^2 + 1, nabla(5_2) = 2z^2 + 1, nabla(9_1) = z^8 +
7z^6 + 15z^4 + 10z^2 + 1, the longest entry at 33 characters.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**Convention.** The Conway polynomial is unique: no unit, no normalisation
to choose. The skein relation is Conway's, nabla(L+) - nabla(L-) =
z nabla(L0), the one Wikipedia, MathWorld, KnotInfo and Sage use (the
positive Hopf link has nabla = z). For a knot nabla has only even powers of
z and constant term 1, so it does not depend on the orientation or on the
choice between the knot and its mirror image (nabla of the mirror image is
nabla(-z)), and it is well defined for the name n_k. The variable is
Conway's z; Sage's `conway_polynomial()` prints it in t and the
coefficients are moved into Z[z] here.

**Every value is computed twice, by methods sharing no code.** The candidate
is Sage's `conway_polynomial()`, which substitutes into det(V - t V^T) for a
Seifert matrix V of the braid closure. It must agree with the polynomial
built here from det(t^e I - P) (t - 1) / (t^r - 1), where P / t^e is the
reduced Burau matrix of the same braid word on r strands (the Burau
matrices, their product and the Bareiss determinant are written out rather
than taken from a library): that quotient is the Alexander polynomial
Delta(t) up to a unit, and nabla is recovered from it by writing the
symmetric Laurent polynomial epsilon t^{-g} Delta(t) as a polynomial in
t + 1/t and substituting t + 1/t = z^2 + 2. The two computations see the
same braid word and nothing else. The value must also have only even powers
and constant term 1; |nabla(2i)| must equal Sage's `determinant()`; the
coefficient a_2 of z^2 reduced modulo 2 must equal the Arf invariant both as
Robertello's sum of Alexander coefficients and by Murasugi's criterion
(Arf = 0 exactly when the determinant is +-1 modulo 8); the four torus knots
T(2, q) and 10_132 must equal the Fibonacci polynomial F_q(z), built by its
recurrence, and 3_1, 7_7 and 9_44 the cyclotomic polynomials Phi_4, Phi_12
and Phi_8; and the counts per crossing number must be 1, 1, 2, 3, 7, 21, 49,
165 (OEIS A002863), which is the check that the table is the whole Rolfsen
table.

When this was written the 250 values were also compared, outside the
generator, with the `conway_polynomial` column of KnotInfo (the
`database_knotinfo` package, version 2026.9.1), which computes from its own
diagrams, and the Arf invariants with its `arf_invariant` column: all
agree. The values were tied to the stored Alexander polynomials (T138) by
Delta(s^2) = epsilon s^{2g} nabla(s - 1/s) and to the stored Jones
polynomials (T139) by V''(1) = -6 a_2 and V(i) = (-1)^Arf, on every knot.

**The unknot.** `from_table(0, 1)` fails inside Sage's one-strand braid
group; nabla(0_1) = 1 is written by hand.

**What the comments say.** Each entry's comment names the knot, a common
name where one exists, the torus knot it is if it is one, the coefficient
a_2 of z^2 (the Casson invariant, the Vassiliev invariant of order two),
the Arf invariant a_2 mod 2, the determinant |nabla(2i)|, and every other
knot in the table with the same polynomial -- the 249 prime knots take 211
distinct values, 36 of them shared by two or three knots, the same
coincidences as the Alexander polynomial, which nabla determines.
Answers numberdb-data#91.
"""

import sys

import numberdb.sage as numberdb
#The braid group behind the knot table imports sage.functions, which cannot
#initialise the symbolic ring from inside its own import; brought up first,
#by name, it can. Without this line `from sage.knots.knot import Knots` raises
#"cannot access submodule 'function' of module 'sage.symbolic'".
import sage.symbolic.ring                                       # noqa: F401
from sage.knots.knot import Knots
from sage.knots.knot_table import small_knots_table
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing

#: The table's ring, and two rings for the independent computation.
ZZz = PolynomialRing(ZZ, 'z')
z = ZZz.gen()
ZT = PolynomialRing(ZZ, 't')
t = ZT.gen()
ZU = PolynomialRing(ZZ, 'u')
u = ZU.gen()

#: Prime knots with n crossings, n = 3, ..., 10: OEIS A002863. The table must
#: hold exactly these many, or it is not the Rolfsen table.
COUNTS = {3: 1, 4: 1, 5: 2, 6: 3, 7: 7, 8: 21, 9: 49, 10: 165}

#: The torus knots among them, with (p, q). KnotInfo's `geometric_type`.
TORUS = {(3, 1): (2, 3), (5, 1): (2, 5), (7, 1): (2, 7), (9, 1): (2, 9),
         (8, 19): (3, 4), (10, 124): (3, 5)}

#: Names a reader would recognise.
NAMED = {
    (0, 1): 'the unknot',
    (3, 1): 'the trefoil',
    (4, 1): 'the figure-eight knot',
    (5, 1): 'the cinquefoil',
    (5, 2): 'the three-twist knot',
    (6, 1): 'the stevedore knot',
    (6, 2): 'the Miller Institute knot',
    (7, 4): 'the endless knot',
    (8, 18): 'the Carrick mat',
    (10, 161): 'the Perko pair, listed twice by Rolfsen as $10_{161}$ and $10_{162}$',
}

#: The entries equal to an entry of the table of Fibonacci polynomials: the
#: torus knot T(2, q) has nabla = F_q, and 10_132 has the polynomial of 5_1.
FIBONACCI = {(3, 1): 3, (5, 1): 5, (7, 1): 7, (9, 1): 9, (10, 132): 5}
FIBONACCI_TABLE = 'Fibonacci_polynomials'

#: The entries equal to an entry of the table of cyclotomic polynomials,
#: Phi_4 = z^2 + 1, Phi_8 = z^4 + 1 and Phi_12 = z^4 - z^2 + 1; the first is
#: also F_3 and is linked there.
CYCLOTOMIC = {(3, 1): 4, (7, 7): 12, (9, 44): 8}
CYCLOTOMIC_VALUE = {4: z ** 2 + 1, 8: z ** 4 + 1, 12: z ** 4 - z ** 2 + 1}
CYCLOTOMIC_TABLE = 'Cyclotomic_polynomials'


def names():
    """(n, k) for every knot of the table, the unknot first, in table order."""
    keys = sorted(small_knots_table)
    counts = {}
    for n, k in keys:
        if n:
            counts[n] = counts.get(n, 0) + 1
    if counts != COUNTS or (0, 1) not in keys:
        raise ArithmeticError('the knot table holds %s knots per crossing '
                              'number, not the Rolfsen table %s' % (counts, COUNTS))
    return keys


def in_z(polynomial):
    """Sage's Conway polynomial, printed in t, as an element of Z[z]."""
    return ZZz([ZZ(c) for c in polynomial.list()])


def normalised(laurent):
    """The polynomial +-t^m Delta with nonzero positive constant term."""
    d = dict(laurent.dict())
    low = min(d)
    pol = ZT(sum(ZZ(c) * t ** (e - low) for e, c in d.items()))
    if pol[0] < 0:
        pol = -pol
    return pol


#-- the independent computation: the reduced Burau representation -----------

def burau_scaled(strands, letter):
    """t^(e) times the reduced Burau matrix of sigma_i^(+-1), e = 1 for an inverse.

    The reduced Burau matrix of sigma_i on r strands is the (r-1) x (r-1)
    identity with row i-1 (from 0) replaced: t in column i-2, -t in column
    i-1, 1 in column i, where those columns exist. It is I + e_r w^T, so its
    inverse is I - e_r w^T / (1 + w_r) = I + e_r w^T / t, and t times it is
    t I + e_r w^T, which has entries in Z[t]. Returned as a list of rows.
    """
    r = strands
    i = abs(letter)
    row = i - 1
    if letter > 0:
        M = [[ZT(1) if a == b else ZT(0) for b in range(r - 1)] for a in range(r - 1)]
        M[row][row] = -t
        if row > 0:
            M[row][row - 1] = t
        if row < r - 2:
            M[row][row + 1] = ZT(1)
    else:
        M = [[t if a == b else ZT(0) for b in range(r - 1)] for a in range(r - 1)]
        M[row][row] = ZT(-1)
        if row > 0:
            M[row][row - 1] = t
        if row < r - 2:
            M[row][row + 1] = ZT(1)
    return M


def multiply(A, B):
    size = len(A)
    return [[sum(A[a][c] * B[c][b] for c in range(size)) for b in range(size)]
            for a in range(size)]


def determinant(M):
    """Bareiss fraction-free elimination over Z[t]; every division is exact."""
    M = [row[:] for row in M]
    size = len(M)
    sign = 1
    previous = ZT(1)
    for k in range(size - 1):
        if M[k][k] == 0:
            for i in range(k + 1, size):
                if M[i][k] != 0:
                    M[k], M[i] = M[i], M[k]
                    sign = -sign
                    break
            else:
                return ZT(0)
        for i in range(k + 1, size):
            for j in range(k + 1, size):
                quotient, remainder = (M[i][j] * M[k][k] - M[i][k] * M[k][j]).quo_rem(previous)
                if remainder != 0:
                    raise ArithmeticError('Bareiss division was not exact')
                M[i][j] = quotient
        previous = M[k][k]
    return sign * M[size - 1][size - 1]


def alexander_by_burau(strands, word):
    """Delta of the closure of the braid, normalised, from the Burau matrix.

    Delta(t) = det(I - psi(beta)) (1 - t) / (1 - t^r) up to a unit, psi the
    reduced Burau representation of B_r. With psi(beta) = P / t^e that is
    det(t^e I - P) (t - 1) / (t^r - 1) up to a unit.
    """
    r = strands
    if r == 1:
        return ZT(1)
    P = [[ZT(1) if a == b else ZT(0) for b in range(r - 1)] for a in range(r - 1)]
    e = 0
    for letter in word:
        P = multiply(P, burau_scaled(r, letter))
        if letter < 0:
            e += 1
    scale = t ** e
    M = [[(scale if a == b else ZT(0)) - P[a][b] for b in range(r - 1)] for a in range(r - 1)]
    D = determinant(M) * (t - 1)
    quotient, remainder = D.quo_rem(t ** r - 1)
    if remainder != 0 or quotient == 0:
        raise ArithmeticError('the Burau determinant is not a multiple of 1 + t + ... + t^(r-1)')
    return normalised(quotient)


def conway_from_alexander(delta):
    """nabla(z) from Delta(t) with positive constant term, by hand.

    epsilon t^{-g} Delta(t), epsilon = Delta(1), is symmetric under t -> 1/t,
    so it is c_g + sum_{j >= 1} c_{g+j} (t^j + t^{-j}); t^j + t^{-j} is the
    polynomial p_j(u) in u = t + 1/t with p_0 = 2, p_1 = u and p_j = u p_{j-1}
    - p_{j-2}; and u = z^2 + 2 for z = t^{1/2} - t^{-1/2}.
    """
    degree = delta.degree()
    if degree % 2:
        raise ArithmeticError('%s has odd degree' % delta)
    g = degree // 2
    epsilon = delta(1)
    if epsilon not in (1, -1):
        raise ArithmeticError('%s is not +-1 at t = 1' % delta)
    c = [epsilon * delta[i] for i in range(degree + 1)]          # of t^(i - g)
    p = [ZU(2), u]
    for j in range(2, g + 1):
        p.append(u * p[-1] - p[-2])
    in_u = ZU(c[g])
    for j in range(1, g + 1):
        if c[g + j] != c[g - j]:
            raise ArithmeticError('%s is not palindromic' % delta)
        in_u += c[g + j] * p[j]
    return ZZz(in_u(z ** 2 + 2))


def fibonacci(q):
    """The Fibonacci polynomial F_q(z): F_0 = 0, F_1 = 1, F_q = z F_{q-1} + F_{q-2}."""
    a, b = ZZz(0), ZZz(1)
    for _ in range(q):
        a, b = b, z * b + a
    return a


#-- the Arf invariant, two ways -----------------------------------------------

def arf_by_robertello(delta):
    """Arf from Delta = c_0 + c_1 t + ... + c_0 t^{2n}: c_{n-1} + c_{n-3} + ...
    + c_r modulo 2, r = 0 for n odd and r = 1 for n even (Wikipedia, Arf
    invariant of a knot, after Robertello)."""
    n = delta.degree() // 2
    total = sum(delta[i] for i in range(n - 1, -1, -2))
    return ZZ(total % 2)


def arf_by_murasugi(det):
    """Arf = 0 exactly when the determinant is congruent to +-1 modulo 8."""
    return ZZ(0) if det % 8 in (1, 7) else ZZ(1)


def determinant_of(nabla):
    """|nabla(2i)|, exactly: nabla is even, so nabla(2i) = sum a_{2j} (-4)^j."""
    return abs(sum(nabla[2 * j] * (-4) ** j for j in range(nabla.degree() // 2 + 1)))


#-- the table ---------------------------------------------------------------

def subscript(n, k):
    return '$%d_%d$' % (n, k) if k < 10 else '$%d_{%d}$' % (n, k)


def comment(n, k, nabla, partners):
    parts = [subscript(n, k)]
    if (n, k) in NAMED:
        parts[0] += ', ' + NAMED[(n, k)]
    if (n, k) == (0, 1):
        parts.append('$\\nabla=1$; the first nontrivial knots with $\\nabla=1$ are '
                     '$11n_{34}$, the Conway knot, and $11n_{42}$, the '
                     'Kinoshita–Terasaka knot')
        return '; '.join(parts)
    if (n, k) in TORUS:
        parts.append('the torus knot $T(%d,%d)$' % TORUS[(n, k)])
    if (n, k) in FIBONACCI:
        text = '\\nabla=F_{%d}' % FIBONACCI[(n, k)]
        if (n, k) in CYCLOTOMIC:
            text += '=\\Phi_{%d}' % CYCLOTOMIC[(n, k)]
        parts.append('$%s$' % text)
    elif (n, k) in CYCLOTOMIC:
        parts.append('$\\nabla=\\Phi_{%d}$' % CYCLOTOMIC[(n, k)])
    a2 = nabla[2]
    parts.append('$a_2=%d$, Arf invariant $%d$, determinant $%d$'
                 % (a2, a2 % 2, determinant_of(nabla)))
    if partners:
        parts.append('the same polynomial as ' + ', '.join(subscript(*p) for p in partners))
    return '; '.join(parts)


class ConwayPolynomials(numberdb.Generator):

    table = 'T140'
    parameters = ('n', 'k')
    type = 'Z[]'
    rigour = 'exact'

    #: Every polynomial, computed once: the comments need the whole table to
    #: name the other knots with the same value.
    _values = None

    def enumerate(self):
        for n, k in names():
            yield {'n': int(n), 'k': int(k)}

    def polynomial(self, n, k):
        """nabla_{n_k}, checked, without the comment."""
        if (n, k) == (0, 1):
            return ZZz(1)
        knot = Knots().from_table(n, k)
        nabla = in_z(knot.conway_polynomial())
        strands, word = small_knots_table[(n, k)]
        delta = alexander_by_burau(strands, word)
        independent = conway_from_alexander(delta)
        if nabla != independent:
            raise ArithmeticError(
                '%d_%d: the Seifert matrix gives %s and the Burau matrix %s; '
                'neither is right until the disagreement has a cause'
                % (n, k, nabla, independent))
        if nabla[0] != 1 or any(nabla[e] for e in range(1, nabla.degree() + 1, 2)):
            raise ArithmeticError('%d_%d: %s is not even with constant term 1' % (n, k, nabla))
        det = determinant_of(nabla)
        if det != knot.determinant():
            raise ArithmeticError('%d_%d: |nabla(2i)| = %s but the determinant is %s'
                                  % (n, k, det, knot.determinant()))
        arf = nabla[2] % 2
        if arf != arf_by_robertello(delta) or arf != arf_by_murasugi(det):
            raise ArithmeticError('%d_%d: a_2 = %s, Robertello %s, Murasugi %s'
                                  % (n, k, nabla[2], arf_by_robertello(delta), arf_by_murasugi(det)))
        if (n, k) in FIBONACCI and nabla != fibonacci(FIBONACCI[(n, k)]):
            raise ArithmeticError('%d_%d: not the Fibonacci polynomial F_%d' % (n, k, FIBONACCI[(n, k)]))
        if (n, k) in CYCLOTOMIC and nabla != CYCLOTOMIC_VALUE[CYCLOTOMIC[(n, k)]]:
            raise ArithmeticError('%d_%d: not the cyclotomic polynomial Phi_%d' % (n, k, CYCLOTOMIC[(n, k)]))
        return nabla

    def all_values(self):
        if self._values is None:
            self._values = {(n, k): self.polynomial(n, k) for n, k in names()}
        return self._values

    def value(self, params, digits):
        n, k = int(params['n']), int(params['k'])
        values = self.all_values()
        nabla = values[(n, k)]
        partners = [key for key in names() if key != (n, k) and values[key] == nabla]
        entry = {'number': nabla, 'comment': comment(n, k, nabla, partners)}
        if (n, k) == (0, 1):
            entry['equals'] = 'HREF{One}'
        elif (n, k) in FIBONACCI:
            q = FIBONACCI[(n, k)]
            entry['equals'] = 'HREF{%s#%d}[$F_{%d}$]' % (FIBONACCI_TABLE, q, q)
        elif (n, k) in CYCLOTOMIC:
            d = CYCLOTOMIC[(n, k)]
            entry['equals'] = 'HREF{%s#%d}[$\\Phi_{%d}$]' % (CYCLOTOMIC_TABLE, d, d)
        return entry


if __name__ == '__main__':
    generator = ConwayPolynomials()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='Conway polynomials of the unknot and the 249 prime knots with '
                    'at most ten crossings, each checked against a Burau determinant '
                    'and, outside the generator, against KnotInfo'))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
