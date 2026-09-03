"""Jones polynomials of the prime knots with at most ten crossings, and of their mirror images -- numberdb.org/T139

    t^(-m) V_K(t) in Z[t], with m the lowest exponent of V_K,

for the unknot 0_1, for every prime knot K = n_k of the Rolfsen table with
3 <= n <= 10 crossings, numbered after Perko, and for the mirror image of
each chiral one. The right-handed trefoil has V = t + t^3 - t^4 and the entry
-t^3 + t^2 + 1 with m = 1; its mirror image has V = -t^-4 + t^-3 + t^-1 and
the entry t^3 + t - 1 with m = -4.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**Which mirror image is which.** The name n_k names a knot only up to mirror
image, and the Jones polynomial sees the difference: V of the mirror image
is V(1/t). The two standard tables disagree: for 139 of the 229 chiral knots
the diagram in the Knot Atlas (which is where Sage's `Knots().from_table`
takes its braid words) is the mirror image of the diagram in KnotInfo -- 137
of them by the Jones polynomial, 9_42 and 10_125 by the signature, while for
10_48, 10_71, 10_91 and 10_104 the two tables give the same braid word. Here the
knot K is the one KnotInfo draws, built from the `braid_notation` column of
the `database_knotinfo` package, version 2026.9.1, copied into
KNOTINFO_BRAIDS below so that this file needs nothing but Sage; the entry
`mirror` is its mirror image. For the six torus knots K is the right-handed
one, which the closed form below verifies.

**Every value is computed twice, by methods sharing no code, and a third
time from a different diagram.** The candidate is Sage's `jones_polynomial()`
of the closure of KnotInfo's braid, which evaluates a representation of the
braid group. It must agree exactly with the Kauffman bracket state sum
(`algorithm='statesum'`) on the planar diagram of the same closure, and up to
t -> 1/t with the Jones polynomial of `Knots().from_table(n, k)`, whose braid
word comes from the Knot Atlas and closes to the knot or its mirror image.
The polynomial of the mirror image is computed from `mirror_image()` of the
link and must equal V(1/t). The value must also satisfy V(1) = 1, V(w) = 1
for w a primitive cube root of unity, |V(-1)| equal to the determinant; the
span of V must be n exactly for the alternating knots, whose coefficients a_e
must satisfy (-1)^e a_e >= 0 for all e or <= 0 for all e, with extreme
coefficients +-1; V(t) = V(1/t) must hold exactly for the 20 amphichiral
knots and the six chiral knots listed in SYMMETRIC_CHIRAL; the six torus
knots must equal the closed form
t^((p-1)(q-1)/2) (1 - t^(p+1) - t^(q+1) + t^(p+q)) / (1 - t^2); and the
counts per crossing number must be 1, 1, 2, 3, 7, 21, 49, 165 (OEIS
A002863), which is the check that the table is the whole Rolfsen table.

When this was written the values were also compared, outside the generator,
with the `jones_polynomial` column of KnotInfo: all 249 agree exactly for K,
and hence as mirror images for the mirror entries. KnotInfo's `signature`,
`determinant`, `symmetry_type` and `alternating` columns were the check on
what the entry comments claim.

**The unknot.** `from_table(0, 1)` fails inside Sage's one-strand braid
group; V(0_1) = 1 is written by hand.

**What the comments say.** Each entry's comment names the knot or says that
it is the mirror image, gives m, the determinant |V(-1)|, the signature (in
KnotInfo's sign convention, where the right-handed trefoil has signature
-2, negated for the mirror image), whether the knot is alternating, and
every other entry with the same polynomial. Answers numberdb-data#91.
"""

import sys

import numberdb.sage as numberdb
#The braid group behind the knot table imports sage.functions, which cannot
#initialise the symbolic ring from inside its own import; brought up first,
#by name, it can. Without this line `from sage.knots.knot import Knots` raises
#"cannot access submodule 'function' of module 'sage.symbolic'".
import sage.symbolic.ring                                       # noqa: F401
from sage.groups.braid import BraidGroup
from sage.knots.knot import Knots
from sage.knots.knot_table import small_knots_table
from sage.knots.link import Link
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

#: The amphichiral knots, isotopic to their mirror images: KnotInfo's
#: `symmetry_type` (fully or negative amphicheiral), 1, 1, 5, 13 of them for
#: n = 4, 6, 8, 10 (OEIS A052401). They have one entry each.
AMPHICHIRAL = frozenset([
    (4, 1), (6, 3), (8, 3), (8, 9), (8, 12), (8, 17), (8, 18),
    (10, 17), (10, 33), (10, 37), (10, 43), (10, 45), (10, 79), (10, 81),
    (10, 88), (10, 99), (10, 109), (10, 115), (10, 118), (10, 123)])

#: Chiral knots whose Jones polynomial is nevertheless symmetric under
#: t -> 1/t (Wikipedia, Chiral knot; KnotInfo's `symmetry_type` is chiral or
#: reversible for each). Their two entries are equal.
SYMMETRIC_CHIRAL = frozenset([(9, 42), (10, 48), (10, 71), (10, 91), (10, 104), (10, 125)])

#: Names a reader would recognise, for the knot as KnotInfo draws it and for
#: its mirror image.
NAMED = {
    (0, 1): 'the unknot',
    (3, 1): 'the right-handed trefoil',
    (4, 1): 'the figure-eight knot',
    (5, 1): 'the cinquefoil',
    (5, 2): 'the three-twist knot',
    (6, 1): 'the stevedore knot',
    (6, 2): 'the Miller Institute knot',
    (7, 4): 'the endless knot',
    (8, 18): 'the Carrick mat',
    (10, 161): 'the Perko pair, listed twice by Rolfsen as $10_{161}$ and $10_{162}$',
}
NAMED_MIRROR = {(3, 1): 'the left-handed trefoil'}

#: KnotInfo's braid word for each knot, (number of strands, word), from the
#: `braid_notation` and `braid_index` columns of database_knotinfo 2026.9.1;
#: a positive letter i is the generator sigma_i of Sage's BraidGroup. KnotInfo
#: lists two words for 10_136 and the first is taken. The closure of each is
#: the knot as KnotInfo draws it, which is what the entry `K` means.
KNOTINFO_BRAIDS = {
    (3, 1): (2, [1,1,1]),
    (4, 1): (3, [1,-2,1,-2]),
    (5, 1): (2, [1,1,1,1,1]),
    (5, 2): (3, [1,1,1,2,-1,2]),
    (6, 1): (4, [1,1,2,-1,-3,2,-3]),
    (6, 2): (3, [1,1,1,-2,1,-2]),
    (6, 3): (3, [1,1,-2,1,-2,-2]),
    (7, 1): (2, [1,1,1,1,1,1,1]),
    (7, 2): (4, [1,1,1,2,-1,2,3,-2,3]),
    (7, 3): (3, [1,1,1,1,1,2,-1,2]),
    (7, 4): (4, [1,1,2,-1,2,2,3,-2,3]),
    (7, 5): (3, [1,1,1,1,2,-1,2,2]),
    (7, 6): (4, [1,1,-2,1,3,-2,3]),
    (7, 7): (4, [-1,2,-1,2,-3,2,-3]),
    (8, 1): (5, [1,1,2,-1,2,3,-2,-4,3,-4]),
    (8, 2): (3, [1,1,1,1,1,-2,1,-2]),
    (8, 3): (5, [1,1,2,-1,-3,2,-3,-4,3,-4]),
    (8, 4): (4, [-1,-1,-1,2,-1,2,3,-2,3]),
    (8, 5): (3, [1,1,1,-2,1,1,1,-2]),
    (8, 6): (4, [1,1,1,1,2,-1,-3,2,-3]),
    (8, 7): (3, [-1,-1,-1,-1,2,-1,2,2]),
    (8, 8): (4, [-1,-1,-1,-2,1,3,-2,3,3]),
    (8, 9): (3, [1,1,1,-2,1,-2,-2,-2]),
    (8, 10): (3, [-1,-1,-1,2,-1,-1,2,2]),
    (8, 11): (4, [1,1,2,-1,2,2,-3,2,-3]),
    (8, 12): (5, [1,-2,1,3,-2,-4,3,-4]),
    (8, 13): (4, [1,1,-2,1,-2,-2,-3,2,-3]),
    (8, 14): (4, [1,1,1,2,-1,2,-3,2,-3]),
    (8, 15): (4, [1,1,-2,1,3,2,2,2,3]),
    (8, 16): (3, [-1,-1,2,-1,-1,2,-1,2]),
    (8, 17): (3, [1,1,-2,1,-2,1,-2,-2]),
    (8, 18): (3, [1,-2,1,-2,1,-2,1,-2]),
    (8, 19): (3, [1,1,1,2,1,1,1,2]),
    (8, 20): (3, [1,1,1,-2,-1,-1,-1,-2]),
    (8, 21): (3, [1,1,1,2,-1,-1,2,2]),
    (9, 1): (2, [1,1,1,1,1,1,1,1,1]),
    (9, 2): (5, [1,1,1,2,-1,2,3,-2,3,4,-3,4]),
    (9, 3): (3, [1,1,1,1,1,1,1,2,-1,2]),
    (9, 4): (4, [1,1,1,1,1,2,-1,2,3,-2,3]),
    (9, 5): (5, [1,1,2,-1,2,2,3,-2,3,4,-3,4]),
    (9, 6): (3, [1,1,1,1,1,1,2,-1,2,2]),
    (9, 7): (4, [1,1,1,1,2,-1,2,3,-2,3,3]),
    (9, 8): (5, [1,1,-2,1,-2,-3,2,4,-3,4]),
    (9, 9): (3, [1,1,1,1,1,2,-1,2,2,2]),
    (9, 10): (4, [1,1,2,-1,2,2,2,2,3,-2,3]),
    (9, 11): (4, [-1,-1,-1,-1,2,-1,-3,2,-3]),
    (9, 12): (5, [1,1,-2,1,3,-2,3,4,-3,4]),
    (9, 13): (4, [1,1,1,1,2,-1,2,2,3,-2,3]),
    (9, 14): (5, [-1,-1,-2,1,3,-2,3,-4,3,-4]),
    (9, 15): (5, [-1,-1,-1,-2,1,3,-2,-4,3,-4]),
    (9, 16): (3, [1,1,1,1,2,2,-1,2,2,2]),
    (9, 17): (4, [-1,2,-1,2,2,2,-3,2,-3]),
    (9, 18): (4, [1,1,1,2,-1,2,2,2,3,-2,3]),
    (9, 19): (5, [-1,2,-1,2,2,3,-2,-4,3,-4]),
    (9, 20): (4, [1,1,1,-2,1,3,-2,3,3]),
    (9, 21): (5, [-1,-1,-2,1,-2,3,-2,-4,3,-4]),
    (9, 22): (4, [-1,2,-1,2,-3,2,2,2,-3]),
    (9, 23): (4, [1,1,1,2,-1,2,2,3,-2,3,3]),
    (9, 24): (4, [1,1,-2,1,3,-2,-2,-2,3]),
    (9, 25): (5, [1,1,-2,1,3,2,2,-4,3,-4]),
    (9, 26): (4, [-1,-1,-1,2,-1,2,-3,2,-3]),
    (9, 27): (4, [1,1,-2,1,-2,-2,3,-2,3]),
    (9, 28): (4, [1,1,-2,1,3,-2,-2,3,3]),
    (9, 29): (4, [1,-2,-2,3,-2,1,-2,3,-2]),
    (9, 30): (4, [-1,-1,2,2,-1,2,-3,2,-3]),
    (9, 31): (4, [1,1,-2,1,-2,3,-2,3,3]),
    (9, 32): (4, [-1,-1,-3,2,-3,-1,2,-1,2]),
    (9, 33): (4, [-1,-3,2,-3,-1,2,2,-1,2]),
    (9, 34): (4, [-1,2,-1,2,-3,2,-1,2,-3]),
    (9, 35): (5, [1,1,2,-1,2,2,3,-2,-2,4,-3,2,4,3]),
    (9, 36): (4, [-1,-1,-1,2,-1,-1,-3,2,-3]),
    (9, 37): (5, [1,1,-2,1,3,-2,-1,-4,3,-2,3,-4]),
    (9, 38): (4, [1,1,2,2,-3,2,-1,2,3,3,2]),
    (9, 39): (5, [-1,-1,-2,1,3,2,-1,-4,-3,2,-3,-4]),
    (9, 40): (4, [1,-2,1,3,-2,1,3,-2,3]),
    (9, 41): (5, [-1,-1,-2,1,3,2,2,-4,-3,2,-3,-4]),
    (9, 42): (4, [-1,-1,-1,2,1,1,-3,2,-3]),
    (9, 43): (4, [1,1,1,2,1,1,-3,2,-3]),
    (9, 44): (4, [1,1,1,2,-1,-1,-3,2,-3]),
    (9, 45): (4, [-1,-1,-2,1,-2,-1,-3,2,-3]),
    (9, 46): (4, [-1,2,-1,2,-3,-2,1,-2,-3]),
    (9, 47): (4, [-1,2,-1,2,3,2,-1,2,3]),
    (9, 48): (4, [-1,-1,-2,1,-2,-1,3,-2,1,-2,3]),
    (9, 49): (4, [1,1,2,1,1,-3,2,-1,2,3,3]),
    (10, 1): (6, [1,1,2,-1,2,3,-2,3,4,-3,-5,4,-5]),
    (10, 2): (3, [1,1,1,1,1,1,1,-2,1,-2]),
    (10, 3): (6, [1,1,2,-1,2,3,-2,-4,3,-4,-5,4,-5]),
    (10, 4): (5, [-1,-1,-1,2,-1,2,3,-2,3,4,-3,4]),
    (10, 5): (3, [-1,-1,-1,-1,-1,-1,2,-1,2,2]),
    (10, 6): (4, [1,1,1,1,1,1,2,-1,-3,2,-3]),
    (10, 7): (5, [1,1,2,-1,2,3,-2,3,3,-4,3,-4]),
    (10, 8): (4, [1,1,1,1,1,-2,1,-2,-3,2,-3]),
    (10, 9): (3, [1,1,1,1,1,-2,1,-2,-2,-2]),
    (10, 10): (5, [1,1,-2,1,-2,-2,-3,2,-3,-4,3,-4]),
    (10, 11): (5, [1,1,1,1,2,-1,-3,2,-3,-4,3,-4]),
    (10, 12): (4, [-1,-1,-1,-1,-1,-2,1,3,-2,3,3]),
    (10, 13): (6, [1,1,2,-1,-3,2,4,-3,-5,4,-5]),
    (10, 14): (4, [1,1,1,1,1,2,-1,2,-3,2,-3]),
    (10, 15): (4, [-1,-1,-1,-1,2,-1,2,3,-2,3,3]),
    (10, 16): (5, [1,1,2,-1,2,2,-3,2,-3,-4,3,-4]),
    (10, 17): (3, [1,1,1,1,-2,1,-2,-2,-2,-2]),
    (10, 18): (5, [1,1,1,2,-1,2,-3,2,-3,-4,3,-4]),
    (10, 19): (4, [1,1,1,1,-2,1,-2,-2,-3,2,-3]),
    (10, 20): (5, [1,1,1,1,2,-1,2,3,-2,-4,3,-4]),
    (10, 21): (4, [1,1,2,-1,2,2,2,2,-3,2,-3]),
    (10, 22): (4, [1,1,1,1,2,-1,-3,2,-3,-3,-3]),
    (10, 23): (4, [1,1,-2,1,-2,-2,-2,-2,-3,2,-3]),
    (10, 24): (5, [1,1,2,-1,2,2,2,3,-2,-4,3,-4]),
    (10, 25): (4, [1,1,1,1,2,-1,2,2,-3,2,-3]),
    (10, 26): (4, [-1,-1,-1,2,-1,2,2,2,3,-2,3]),
    (10, 27): (4, [-1,-1,-1,-1,-2,1,-2,3,-2,3,3]),
    (10, 28): (5, [-1,-1,-2,1,-2,-2,-3,2,4,-3,4,4]),
    (10, 29): (5, [1,1,1,-2,1,3,-2,-4,3,-4]),
    (10, 30): (5, [1,1,2,-1,2,2,3,-2,3,-4,3,-4]),
    (10, 31): (5, [1,1,1,2,-1,-3,2,-3,-3,-4,3,-4]),
    (10, 32): (4, [-1,-1,-1,2,-1,2,2,3,-2,3,3]),
    (10, 33): (5, [1,1,2,-1,2,-3,2,-3,-3,-4,3,-4]),
    (10, 34): (5, [-1,-1,-1,-2,1,-2,-3,2,4,-3,4,4]),
    (10, 35): (6, [1,-2,1,-2,-3,2,4,-3,-5,4,-5]),
    (10, 36): (5, [1,1,1,2,-1,2,3,-2,3,-4,3,-4]),
    (10, 37): (5, [1,1,1,2,-1,-3,2,-3,-4,3,-4,-4]),
    (10, 38): (5, [1,1,1,2,-1,2,2,3,-2,-4,3,-4]),
    (10, 39): (4, [1,1,1,2,-1,2,2,2,-3,2,-3]),
    (10, 40): (4, [-1,-1,-1,-2,1,-2,-2,3,-2,3,3]),
    (10, 41): (5, [-1,2,-1,2,2,-3,2,4,-3,4]),
    (10, 42): (5, [1,1,-2,1,-2,3,-2,-4,3,-4]),
    (10, 43): (5, [1,1,-2,1,3,-2,-4,3,-4,-4]),
    (10, 44): (5, [1,1,-2,1,3,-2,3,-4,3,-4]),
    (10, 45): (5, [1,-2,1,-2,3,-2,3,-4,3,-4]),
    (10, 46): (3, [1,1,1,1,1,-2,1,1,1,-2]),
    (10, 47): (3, [-1,-1,-1,-1,-1,2,-1,-1,2,2]),
    (10, 48): (3, [-1,-1,-1,-1,2,2,-1,2,2,2]),
    (10, 49): (4, [1,1,1,1,-2,1,3,2,2,2,3]),
    (10, 50): (4, [1,1,2,-1,2,2,-3,2,2,2,-3]),
    (10, 51): (4, [-1,-1,-2,1,-2,-2,3,-2,-2,3,3]),
    (10, 52): (4, [1,1,1,-2,1,1,-2,-2,-3,2,-3]),
    (10, 53): (5, [1,1,2,-1,2,-3,2,4,3,3,3,4]),
    (10, 54): (4, [-1,-1,-1,2,-1,-1,2,3,-2,3,3]),
    (10, 55): (5, [1,1,1,2,-1,-3,2,4,3,3,3,4]),
    (10, 56): (4, [1,1,1,2,-1,2,-3,2,2,2,-3]),
    (10, 57): (4, [-1,-1,-1,-2,1,-2,3,-2,-2,3,3]),
    (10, 58): (6, [-1,2,-1,-3,2,4,3,3,-5,4,-5]),
    (10, 59): (5, [-1,2,-1,2,-3,2,2,4,-3,4]),
    (10, 60): (5, [-1,2,-1,2,2,-3,2,-3,-2,-4,3,-4]),
    (10, 61): (4, [1,1,1,-2,1,1,1,-2,-3,2,-3]),
    (10, 62): (3, [-1,-1,-1,-1,2,-1,-1,-1,2,2]),
    (10, 63): (5, [1,1,-2,1,3,2,2,2,3,4,-3,4]),
    (10, 64): (3, [1,1,1,-2,1,1,1,-2,-2,-2]),
    (10, 65): (4, [-1,-1,-2,1,-2,3,-2,-2,-2,3,3]),
    (10, 66): (4, [1,1,1,-2,1,3,2,2,2,3,3]),
    (10, 67): (5, [1,1,1,3,-4,2,3,-4,-2,-2,3,2,-1,2]),
    (10, 68): (5, [1,1,-2,1,-2,-2,-3,2,2,-4,3,-2,-4,-3]),
    (10, 69): (5, [-1,-1,-2,1,3,-2,-1,-4,3,-2,3,-4]),
    (10, 70): (5, [1,-2,1,3,-2,-2,-2,-4,3,-4]),
    (10, 71): (5, [-1,-1,2,-1,-3,2,2,4,-3,4]),
    (10, 72): (4, [1,1,1,1,2,2,-1,2,-3,2,-3]),
    (10, 73): (5, [-1,-1,-2,1,-2,-1,3,-2,3,-4,3,-4]),
    (10, 74): (5, [1,1,2,-1,2,2,3,-2,-2,-4,3,2,-4,3]),
    (10, 75): (5, [-1,2,-1,2,-3,2,2,-4,3,-2,-4,-3]),
    (10, 76): (4, [1,1,1,1,2,-1,-3,2,2,2,-3]),
    (10, 77): (4, [-1,-1,-1,-1,-2,1,3,-2,-2,3,3]),
    (10, 78): (5, [1,1,2,-1,2,1,-3,2,4,-3,4,4]),
    (10, 79): (3, [1,1,1,-2,-2,1,1,-2,-2,-2]),
    (10, 80): (4, [1,1,1,-2,1,1,3,2,2,2,3]),
    (10, 81): (5, [1,1,-2,1,3,2,2,-4,-3,-3,-3,-4]),
    (10, 82): (3, [1,1,1,1,-2,1,-2,1,-2,-2]),
    (10, 83): (4, [-1,-1,-2,1,-2,3,-2,-2,3,-2,3]),
    (10, 84): (4, [1,1,1,-3,2,-3,2,2,-3,-1,2]),
    (10, 85): (3, [-1,-1,-1,-1,2,-1,-1,2,-1,2]),
    (10, 86): (4, [-1,-1,2,-1,2,-1,2,2,3,-2,3]),
    (10, 87): (4, [1,1,1,2,-1,-3,2,-3,2,-3,-3]),
    (10, 88): (5, [1,-2,1,3,-2,3,-2,-4,3,-4]),
    (10, 89): (5, [-1,2,-1,2,3,-2,-1,-4,-3,2,-3,-4]),
    (10, 90): (4, [-1,-1,2,2,3,-1,-2,3,2,-1,2]),
    (10, 91): (3, [-1,-1,-1,2,-1,2,2,-1,2,2]),
    (10, 92): (4, [1,1,1,2,-3,2,-1,2,-3,2,2]),
    (10, 93): (4, [-1,-1,3,-2,3,2,-1,2,-1,-1,2]),
    (10, 94): (3, [1,1,1,-2,1,-2,-2,1,1,-2]),
    (10, 95): (4, [1,1,-2,-3,-3,-2,1,-2,3,-2,-2]),
    (10, 96): (5, [1,-2,-1,3,-2,-1,3,-4,3,-2,3,-4]),
    (10, 97): (5, [1,1,2,-1,2,1,-3,2,-1,2,3,-4,3,-4]),
    (10, 98): (4, [1,1,2,-3,2,2,-1,2,-3,2,2]),
    (10, 99): (3, [1,1,-2,1,1,-2,-2,1,-2,-2]),
    (10, 100): (3, [-1,-1,-1,2,-1,-1,2,-1,-1,2]),
    (10, 101): (5, [1,1,1,2,-1,3,-2,1,3,2,2,4,-3,4]),
    (10, 102): (4, [-1,-1,2,-1,-3,2,-1,2,2,3,3]),
    (10, 103): (4, [-1,-1,-2,1,3,-2,-2,3,-2,-2,3]),
    (10, 104): (3, [-1,-1,-1,2,2,-1,2,-1,2,2]),
    (10, 105): (5, [1,1,-2,1,3,2,2,-4,-3,2,-3,-4]),
    (10, 106): (3, [1,1,1,-2,1,-2,1,1,-2,-2]),
    (10, 107): (5, [1,1,4,-3,2,-3,4,-2,-2,-3,1,-2]),
    (10, 108): (4, [1,1,-2,1,1,3,-2,1,-2,-3,-3]),
    (10, 109): (3, [1,1,-2,1,-2,-2,1,1,-2,-2]),
    (10, 110): (5, [1,-4,-3,2,-3,-4,2,2,2,3,1,-2]),
    (10, 111): (4, [1,1,2,2,-3,2,2,-1,2,-3,2]),
    (10, 112): (3, [-1,-1,-1,2,-1,2,-1,2,-1,2]),
    (10, 113): (4, [1,1,1,2,-3,2,-1,2,-3,2,-3]),
    (10, 114): (4, [-1,-1,-2,1,3,-2,3,-2,3,-2,3]),
    (10, 115): (5, [1,-2,1,3,2,2,-4,-3,2,-3,-3,-4]),
    (10, 116): (3, [-1,-1,2,-1,-1,2,-1,2,-1,2]),
    (10, 117): (4, [-1,-1,-2,-2,3,-2,1,-2,3,-2,3]),
    (10, 118): (3, [1,1,-2,1,-2,-2,1,-2,1,-2]),
    (10, 119): (4, [1,1,-2,1,3,-2,1,-2,-3,-3,-2]),
    (10, 120): (5, [1,1,2,-1,-3,-2,1,4,3,2,2,3,3,4]),
    (10, 121): (4, [1,1,2,-3,2,-1,2,-3,2,-3,2]),
    (10, 122): (4, [-1,-1,-2,3,-2,1,3,-2,3,-2,3]),
    (10, 123): (3, [1,-2,1,-2,1,-2,1,-2,1,-2]),
    (10, 124): (3, [1,1,1,1,1,2,1,1,1,2]),
    (10, 125): (3, [-1,-1,-1,-1,-1,2,1,1,1,2]),
    (10, 126): (3, [-1,-1,-1,-1,-1,-2,1,1,1,-2]),
    (10, 127): (3, [1,1,1,1,1,2,-1,-1,2,2]),
    (10, 128): (4, [1,1,1,2,1,1,2,2,3,-2,3]),
    (10, 129): (4, [-1,-1,-1,2,1,1,-3,2,1,-3,2]),
    (10, 130): (4, [1,1,1,-2,-1,-1,-2,-2,-3,2,-3]),
    (10, 131): (4, [1,1,1,2,-1,-1,2,2,3,-2,3]),
    (10, 132): (4, [1,1,1,-2,-1,-1,-2,-3,2,-3,-3]),
    (10, 133): (4, [1,1,1,2,-1,-1,2,3,-2,3,3]),
    (10, 134): (4, [1,1,1,2,1,1,2,3,-2,3,3]),
    (10, 135): (4, [-1,-1,-1,-2,1,-2,3,2,2,2,3]),
    (10, 136): (4, [-1,-1,-2,3,-2,1,-2,-2,3,2,2]),
    (10, 137): (5, [1,-2,1,-2,3,2,2,-4,3,-4]),
    (10, 138): (5, [-1,2,-1,2,3,2,2,-4,3,-4]),
    (10, 139): (3, [1,1,1,1,2,1,1,1,2,2]),
    (10, 140): (4, [-1,-1,-1,2,1,1,1,2,3,-2,3]),
    (10, 141): (3, [-1,-1,-1,-1,2,1,1,1,2,2]),
    (10, 142): (4, [1,1,1,2,1,1,1,2,3,-2,3]),
    (10, 143): (3, [-1,-1,-1,-1,-2,1,1,1,-2,-2]),
    (10, 144): (4, [1,1,2,-1,2,1,-3,2,1,-3,-2]),
    (10, 145): (4, [-1,-1,-2,1,-2,-1,-3,-2,1,-2,-3]),
    (10, 146): (4, [-1,-1,2,-1,2,1,-3,2,-1,2,-3]),
    (10, 147): (4, [1,1,1,-3,2,-1,2,-3,-2,1,-2]),
    (10, 148): (3, [-1,-1,-1,-1,-2,1,-2,1,1,-2]),
    (10, 149): (3, [1,1,1,1,2,-1,2,-1,2,2]),
    (10, 150): (4, [1,1,1,-2,1,1,3,-2,-1,3,2]),
    (10, 151): (4, [-1,-1,-1,-2,1,1,-3,2,-1,-3,2]),
    (10, 152): (3, [1,1,1,2,2,1,1,2,2,2]),
    (10, 153): (4, [-1,-1,-1,-2,-1,-1,3,2,2,2,3]),
    (10, 154): (4, [1,1,2,-1,2,1,3,2,2,2,3]),
    (10, 155): (3, [-1,-1,-1,-2,1,1,-2,1,1,-2]),
    (10, 156): (4, [-1,-1,-1,2,1,1,-3,-2,1,-2,-3]),
    (10, 157): (3, [-1,-1,-1,-2,-2,1,-2,1,-2,-2]),
    (10, 158): (4, [-1,-1,-1,-2,1,1,3,2,-1,2,3]),
    (10, 159): (3, [1,1,1,2,-1,2,-1,-1,2,2]),
    (10, 160): (4, [1,1,1,2,1,1,-3,2,-1,2,-3]),
    (10, 161): (3, [1,1,1,2,-1,2,1,1,2,2]),
    (10, 162): (4, [-1,-1,-2,1,1,-2,-2,-1,3,-2,3]),
    (10, 163): (4, [1,1,-2,-1,-1,3,2,-1,2,2,3]),
    (10, 164): (4, [1,1,-2,1,-2,-2,-3,2,-1,2,-3]),
    (10, 165): (4, [-1,-1,-2,1,3,-2,1,-2,-3,-3,-2]),
}


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
    if set(KNOTINFO_BRAIDS) != set(keys) - {(0, 1)}:
        raise ArithmeticError('the KnotInfo braid words and the knot table name different knots')
    return keys


#-- Laurent polynomials as {exponent: coefficient} ---------------------------

def laurent(expression):
    """Sage's symbolic Jones polynomial as {exponent: coefficient}, exact.

    `jones_polynomial()` returns a symbolic expression because a link can
    have half-integer exponents; a knot cannot, and a half-integer here is an
    error.
    """
    variables = expression.variables()
    if not variables:
        return {ZZ(0): ZZ(expression)}
    out = {}
    for coefficient, exponent in expression.coefficients(variables[0]):
        if ZZ(exponent) != exponent:
            raise ArithmeticError('exponent %s is not an integer' % exponent)
        out[ZZ(exponent)] = ZZ(coefficient)
    return out


def mirrored(V):
    """V(1/t)."""
    return {-e: c for e, c in V.items()}


def shifted(V):
    """(t^(-m) V as a polynomial in Z[t], m), m the lowest exponent."""
    m = min(V)
    return ZT({e - m: c for e, c in V.items()}), m


def evaluated(V, point):
    return sum(c * point ** e for e, c in V.items())


def at_cube_root_of_unity(V):
    """V(w) as an element of Z[t]/(t^2 + t + 1), exactly."""
    return ZT(sum(c * t ** (e % 3) for e, c in V.items()))


def torus_closed_form(p, q):
    """t^((p-1)(q-1)/2) (1 - t^(p+1) - t^(q+1) + t^(p+q)) / (1 - t^2) for the right-handed T(p, q)."""
    quotient, remainder = (1 - t ** (p + 1) - t ** (q + 1) + t ** (p + q)).quo_rem(1 - t ** 2)
    if remainder != 0 or ((p - 1) * (q - 1)) % 2:
        raise ArithmeticError('the torus closed form did not divide exactly')
    return {ZZ(e + (p - 1) * (q - 1) // 2): ZZ(c) for e, c in quotient.dict().items()}


def alternates(V):
    """Whether V is an alternating polynomial: (-1)^e a_e all >= 0 or all <= 0.

    Zero coefficients are allowed; the right-handed trefoil's t + t^3 - t^4
    has one, at t^2, and is alternating in this sense.
    """
    signed = [(-1) ** e * c for e, c in V.items()]
    return all(s >= 0 for s in signed) or all(s <= 0 for s in signed)


#-- the table ---------------------------------------------------------------

def subscript(n, k):
    return '$%d_%d$' % (n, k) if k < 10 else '$%d_{%d}$' % (n, k)


def entry_name(n, k, image):
    if image == 'K':
        text = subscript(n, k)
        if (n, k) in NAMED:
            text += ', ' + NAMED[(n, k)]
        return text
    text = 'the mirror image of ' + subscript(n, k)
    if (n, k) in NAMED_MIRROR:
        text += ', ' + NAMED_MIRROR[(n, k)]
    elif (n, k) in NAMED:
        text += ', ' + NAMED[(n, k)]
    return text


def comment(n, k, image, m, det, signature, partners):
    parts = [entry_name(n, k, image)]
    if (n, k) == (0, 1):
        parts.append('$V=1$, and whether any nontrivial knot has $V=1$ is an open question')
        return '; '.join(parts)
    if (n, k) in TORUS and image == 'K':
        parts[0] += ', the torus knot $T(%d,%d)$' % TORUS[(n, k)]
    parts.append('$m=%d$' % m)
    facts = []
    if image == 'K':
        facts.append('determinant $%d$' % det)
    facts.append('signature $%d$' % signature)
    if image == 'K':
        facts.append('non-alternating' if k >= FIRST_NONALTERNATING.get(n, 10 ** 6)
                     else 'alternating')
    parts.append(', '.join(facts))
    if (n, k) in AMPHICHIRAL:
        parts.append('amphichiral, so the mirror image is the same knot and $V(t)=V(1/t)$')
    elif (n, k) in SYMMETRIC_CHIRAL and image == 'K':
        parts.append('chiral, yet $V(t)=V(1/t)$, so the mirror image has the same polynomial')
    if partners:
        parts.append('the same polynomial as ' + ', '.join(
            entry_name(*p).split(',')[0] for p in partners))
    return '; '.join(parts)


class JonesPolynomials(numberdb.Generator):

    table = 'T139'
    parameters = ('n', 'k', 'knot')
    type = 'Z[]'
    rigour = 'exact'

    #: Every knot, computed once: the comments need the whole table to name
    #: the other entries with the same value.
    _knots = None

    def enumerate(self):
        for n, k in names():
            yield {'n': int(n), 'k': int(k), 'knot': 'K'}
            if (n, k) != (0, 1) and (n, k) not in AMPHICHIRAL:
                yield {'n': int(n), 'k': int(k), 'knot': 'mirror'}

    def knot(self, n, k):
        """The checked Jones polynomial of K and of its mirror image, with the
        determinant and signature of K: (V, V_mirror, det, signature)."""
        if (n, k) == (0, 1):
            return {ZZ(0): ZZ(1)}, {ZZ(0): ZZ(1)}, ZZ(1), ZZ(0)
        strands, word = KNOTINFO_BRAIDS[(n, k)]
        link = Link(BraidGroup(strands)(word))
        V = laurent(link.jones_polynomial())
        by_bracket = laurent(link.jones_polynomial(algorithm='statesum'))
        if V != by_bracket:
            raise ArithmeticError(
                '%d_%d: the braid representation gives %s and the state sum %s; '
                'neither is right until the disagreement has a cause' % (n, k, V, by_bracket))
        from_atlas = laurent(Knots().from_table(n, k).jones_polynomial())
        if from_atlas != V and from_atlas != mirrored(V):
            raise ArithmeticError('%d_%d: the Knot Atlas braid gives %s, neither %s nor its mirror'
                                  % (n, k, from_atlas, V))
        V_mirror = laurent(link.mirror_image().jones_polynomial())
        if V_mirror != mirrored(V):
            raise ArithmeticError('%d_%d: the mirror image gives %s, not V(1/t)' % (n, k, V_mirror))
        if evaluated(V, ZZ(1)) != 1:
            raise ArithmeticError('%d_%d: V(1) = %s' % (n, k, evaluated(V, ZZ(1))))
        if at_cube_root_of_unity(V) % (t ** 2 + t + 1) != 1:
            raise ArithmeticError('%d_%d: V at a cube root of unity is not 1' % (n, k))
        det = ZZ(abs(evaluated(V, ZZ(-1))))
        if det != link.determinant():
            raise ArithmeticError('%d_%d: |V(-1)| = %s but the determinant is %s'
                                  % (n, k, det, link.determinant()))
        span = max(V) - min(V)
        alternating = k < FIRST_NONALTERNATING.get(n, 10 ** 6)
        if (span == n) != alternating:
            raise ArithmeticError('%d_%d: span %d, alternating %s' % (n, k, span, alternating))
        if alternating and not (alternates(V) and abs(V[min(V)]) == 1 and abs(V[max(V)]) == 1):
            raise ArithmeticError('%d_%d: alternating, but V = %s' % (n, k, V))
        symmetric = (n, k) in AMPHICHIRAL or (n, k) in SYMMETRIC_CHIRAL
        if (V == mirrored(V)) != symmetric:
            raise ArithmeticError('%d_%d: V(t) = V(1/t) is %s' % (n, k, V == mirrored(V)))
        if (n, k) in TORUS and V != torus_closed_form(*TORUS[(n, k)]):
            raise ArithmeticError('%d_%d: not the right-handed torus knot closed form' % (n, k))
        return V, V_mirror, det, ZZ(link.signature())

    def all_knots(self):
        if self._knots is None:
            self._knots = {(n, k): self.knot(n, k) for n, k in names()}
        return self._knots

    def value(self, params, digits):
        n, k, image = int(params['n']), int(params['k']), params['knot']
        if image not in ('K', 'mirror'):
            raise ValueError("knot is 'K' or 'mirror', not %r" % image)
        if image == 'mirror' and ((n, k) == (0, 1) or (n, k) in AMPHICHIRAL):
            raise ValueError('%d_%d is its own mirror image and has one entry' % (n, k))
        knots = self.all_knots()
        V, V_mirror, det, signature = knots[(n, k)]
        pol, m = shifted(V if image == 'K' else V_mirror)
        if image == 'mirror':
            signature = -signature
        partners = []
        for key in names():
            other_V, other_mirror, _, _ = knots[key]
            for other_image, other in (('K', other_V), ('mirror', other_mirror)):
                if other_image == 'mirror' and (key == (0, 1) or key in AMPHICHIRAL):
                    continue
                if (key, other_image) == ((n, k), image):
                    continue
                if key == (n, k) and key in SYMMETRIC_CHIRAL and image == 'K':
                    continue                     # the comment already says so
                if shifted(other)[0] == pol:
                    partners.append((key[0], key[1], other_image))
        entry = {'number': pol, 'comment': comment(n, k, image, m, det, signature, partners)}
        if (n, k) == (0, 1):
            entry['equals'] = 'HREF{One}'
        return entry


if __name__ == '__main__':
    generator = JonesPolynomials()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='Jones polynomials of the unknot, the 249 prime knots with at most '
                    'ten crossings as KnotInfo draws them, and the mirror images of the '
                    '229 chiral ones; each checked by two algorithms, against the Knot '
                    'Atlas braid up to mirror and, outside the generator, against KnotInfo'))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
