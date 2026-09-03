"""Alexander polynomials of the prime knots with at most ten crossings -- numberdb.org/T138

    Delta_K(t) in Z[t], normalised so that Delta_K(0) > 0,

for every knot n_k of the Rolfsen table, numbered after Perko: the unknot 0_1
and the 249 prime knots with 3 <= n <= 10 crossings that Sage ships as
`Knots().from_table(n, k)` (from Knot Atlas's braid words). Delta(3_1) =
t^2 - t + 1, Delta(4_1) = t^2 - 3t + 1, Delta(10_165) = 2t^4 - 10t^3 + 15t^2
- 10t + 2.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**Normalisation.** The Alexander polynomial is defined up to a unit +-t^m of
Z[t, 1/t]. Sage's `alexander_polynomial()` returns the Conway-normalised
Laurent polynomial, symmetric under t -> 1/t with value 1 at t = 1
(`-t^-1 + 3 - t` for 4_1); Rolfsen's table, Knot Atlas and KnotInfo write the
polynomial with nonzero positive constant term (`1 - 3t + t^2`). This table
follows Rolfsen, because that form is a polynomial and the table's type is
Z[]. It is palindromic of even degree 2g, so the leading coefficient is
positive too, and the two forms differ by the unit epsilon t^{-g} with
epsilon = Delta(1) = +-1.

**Every value is computed twice, by methods sharing no code.** The candidate
is Sage's `alexander_polynomial()`, det(V - t V^T) for a Seifert matrix V of
the braid closure. It must agree, up to the unit, with det(t^e I - P) (t -
1) / (t^n - 1), where P / t^e is the reduced Burau matrix of the same braid
word on n strands (e counts the inverse letters, so that P has entries in
Z[t]); the Burau matrices, their product and the Bareiss determinant are
written out here rather than taken from a library. The two computations
see the same braid word and nothing else. The value must also satisfy
Delta(1) = +-1, Delta(t) = t^{deg} Delta(1/t), and |Delta(-1)| equal to
Sage's `determinant()`; the six torus knots must equal the closed form
(t^{pq} - 1)(t - 1) / ((t^p - 1)(t^q - 1)); and the counts per crossing
number must be 1, 1, 2, 3, 7, 21, 49, 165 (OEIS A002863), which is the check
that the table is the whole Rolfsen table.

When this was written the 250 values were also compared, outside the
generator, with the `alexander_polynomial` column of KnotInfo (the
`database_knotinfo` package, version 2026.9.1), which computes from its own
diagrams: all agree. KnotInfo's `three_genus`, `alternating`, `fibered` and
`geometric_type` columns were the check on what the entry comments claim:
for every knot here the degree of Delta is twice the genus, Delta is monic
exactly for the fibred knots, the non-alternating knots are exactly
8_19-8_21, 9_42-9_49 and 10_124-10_165, and the torus knots are the six
named below.

**The unknot.** `from_table(0, 1)` fails inside Sage's one-strand braid
group; Delta(0_1) = 1 is written by hand. It is here so that a reader whose
polynomial came out as 1 finds it, with the comment saying that the first
nontrivial knots with Delta = 1 have eleven crossings.

**What the comments say.** Each entry's comment names the knot, a common
name where one exists, the determinant |Delta(-1)|, the genus deg/2,
whether the knot is alternating, the torus knot it is if it is one, and
every other knot in the table with the same polynomial -- the 249 prime
knots take 211 distinct values, 36 of them shared by two or three knots.
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

ZT = PolynomialRing(ZZ, 't')
t = ZT.gen()

#: Prime knots with n crossings, n = 3, ..., 10: OEIS A002863. The table must
#: hold exactly these many, or it is not the Rolfsen table.
COUNTS = {3: 1, 4: 1, 5: 2, 6: 3, 7: 7, 8: 21, 9: 49, 10: 165}

#: The torus knots among them, with (p, q). KnotInfo's `geometric_type`.
TORUS = {(3, 1): (2, 3), (5, 1): (2, 5), (7, 1): (2, 7), (9, 1): (2, 9),
         (8, 19): (3, 4), (10, 124): (3, 5)}

#: Rolfsen lists the alternating knots of each crossing number first; these are
#: the indices at which the non-alternating ones begin (KnotInfo's
#: `alternating` column, checked on all 249). Below eight crossings every
#: prime knot is alternating.
FIRST_NONALTERNATING = {8: 19, 9: 42, 10: 124}

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

#: The entries equal to an entry of the table of cyclotomic polynomials: the
#: Alexander polynomial of T(2, q) is Phi_{2q} for q an odd prime, and that
#: of T(3, 5) is Phi_15.
CYCLOTOMIC = {(3, 1): 6, (5, 1): 10, (7, 1): 14, (10, 124): 15}
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


def normalised(laurent):
    """The polynomial +-t^m Delta with nonzero positive constant term."""
    d = dict(laurent.dict())
    low = min(d)
    pol = sum(ZZ(c) * t ** (e - low) for e, c in d.items())
    pol = ZT(pol)
    if pol[0] < 0:
        pol = -pol
    return pol


#-- the independent computation: the reduced Burau representation -----------

def burau_scaled(strands, letter):
    """t^(e) times the reduced Burau matrix of sigma_i^(+-1), e = 1 for an inverse.

    The reduced Burau matrix of sigma_i on n strands is the (n-1) x (n-1)
    identity with row i-1 (from 0) replaced: t in column i-2, -t in column
    i-1, 1 in column i, where those columns exist. It is I + e_r w^T, so its
    inverse is I - e_r w^T / (1 + w_r) = I + e_r w^T / t, and t times it is
    t I + e_r w^T, which has entries in Z[t]. Returned as a list of rows.
    """
    n = strands
    i = abs(letter)
    r = i - 1
    if letter > 0:
        M = [[ZT(1) if a == b else ZT(0) for b in range(n - 1)] for a in range(n - 1)]
        M[r][r] = -t
        if r > 0:
            M[r][r - 1] = t
        if r < n - 2:
            M[r][r + 1] = ZT(1)
    else:
        M = [[t if a == b else ZT(0) for b in range(n - 1)] for a in range(n - 1)]
        M[r][r] = ZT(-1)
        if r > 0:
            M[r][r - 1] = t
        if r < n - 2:
            M[r][r + 1] = ZT(1)
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

    Delta(t) = det(I - psi(beta)) (1 - t) / (1 - t^n) up to a unit, psi the
    reduced Burau representation of B_n. With psi(beta) = P / t^e that is
    det(t^e I - P) (t - 1) / (t^n - 1) up to a unit.
    """
    n = strands
    if n == 1:
        return ZT(1)
    P = [[ZT(1) if a == b else ZT(0) for b in range(n - 1)] for a in range(n - 1)]
    e = 0
    for letter in word:
        P = multiply(P, burau_scaled(n, letter))
        if letter < 0:
            e += 1
    scale = t ** e
    M = [[(scale if a == b else ZT(0)) - P[a][b] for b in range(n - 1)] for a in range(n - 1)]
    D = determinant(M) * (t - 1)
    quotient, remainder = D.quo_rem(t ** n - 1)
    if remainder != 0 or quotient == 0:
        raise ArithmeticError('the Burau determinant is not a multiple of 1 + t + ... + t^(n-1)')
    return normalised(quotient)


def torus_closed_form(p, q):
    """(t^{pq} - 1)(t - 1) / ((t^p - 1)(t^q - 1)), exactly in Z[t]."""
    quotient, remainder = ((t ** (p * q) - 1) * (t - 1)).quo_rem((t ** p - 1) * (t ** q - 1))
    if remainder != 0:
        raise ArithmeticError('the torus closed form did not divide exactly')
    return quotient


#-- the table ---------------------------------------------------------------

def subscript(n, k):
    return '$%d_%d$' % (n, k) if k < 10 else '$%d_{%d}$' % (n, k)


def comment(n, k, pol, partners):
    parts = [subscript(n, k)]
    if (n, k) in NAMED:
        parts[0] += ', ' + NAMED[(n, k)]
    if (n, k) in TORUS:
        parts.append('the torus knot $T(%d,%d)$' % TORUS[(n, k)])
    if n:
        facts = ['determinant $%d$' % abs(pol(-1)), 'genus $%d$' % (pol.degree() // 2)]
        facts.append('non-alternating' if k >= FIRST_NONALTERNATING.get(n, 10 ** 6)
                     else 'alternating')
        parts.append(', '.join(facts))
    else:
        parts.append('genus $0$; the first nontrivial knots with $\\Delta=1$ are '
                     '$11n_{34}$, the Conway knot, and $11n_{42}$, the '
                     'Kinoshita–Terasaka knot')
    if (n, k) == (8, 19):
        parts.append('$\\Delta=\\Phi_6\\Phi_{12}$')
    if (n, k) == (9, 1):
        parts.append('$\\Delta=\\Phi_6\\Phi_{18}$')
    if (n, k) in ((8, 20), (10, 140)):
        parts.append('$\\Delta=\\Phi_6^2$, also the Alexander polynomial of the '
                     'granny and square knots $3_1\\#3_1$ and $3_1\\#\\bar{3}_1$')
    if partners:
        parts.append('the same polynomial as ' + ', '.join(subscript(*p) for p in partners))
    return '; '.join(parts)


class AlexanderPolynomials(numberdb.Generator):

    table = 'T138'
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
        """Delta_{n_k}, checked, without the comment."""
        if (n, k) == (0, 1):
            return ZT(1)
        knot = Knots().from_table(n, k)
        pol = normalised(knot.alexander_polynomial())
        strands, word = small_knots_table[(n, k)]
        independent = alexander_by_burau(strands, word)
        if pol != independent:
            raise ArithmeticError(
                '%d_%d: the Seifert matrix gives %s and the Burau matrix %s; '
                'neither is right until the disagreement has a cause'
                % (n, k, pol, independent))
        if abs(pol(1)) != 1:
            raise ArithmeticError('%d_%d: Delta(1) = %s' % (n, k, pol(1)))
        if pol != pol.reverse() or pol.degree() % 2:
            raise ArithmeticError('%d_%d: %s is not palindromic of even degree' % (n, k, pol))
        if abs(pol(-1)) != knot.determinant():
            raise ArithmeticError('%d_%d: |Delta(-1)| = %s but the determinant is %s'
                                  % (n, k, abs(pol(-1)), knot.determinant()))
        if (n, k) in TORUS and pol != torus_closed_form(*TORUS[(n, k)]):
            raise ArithmeticError('%d_%d: not the torus knot closed form' % (n, k))
        return pol

    def all_values(self):
        if self._values is None:
            self._values = {(n, k): self.polynomial(n, k) for n, k in names()}
        return self._values

    def value(self, params, digits):
        n, k = int(params['n']), int(params['k'])
        values = self.all_values()
        pol = values[(n, k)]
        partners = [key for key in names() if key != (n, k) and values[key] == pol]
        entry = {'number': pol, 'comment': comment(n, k, pol, partners)}
        if (n, k) == (0, 1):
            entry['equals'] = 'HREF{One}'
        elif (n, k) in CYCLOTOMIC:
            entry['equals'] = 'HREF{%s#%d}[$\\Phi_{%d}$]' % (
                CYCLOTOMIC_TABLE, CYCLOTOMIC[(n, k)], CYCLOTOMIC[(n, k)])
        return entry


if __name__ == '__main__':
    generator = AlexanderPolynomials()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='Alexander polynomials of the unknot and the 249 prime knots '
                    'with at most ten crossings, each checked against a Burau '
                    'determinant and, outside the generator, against KnotInfo'))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
