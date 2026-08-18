"""Special value of the L-function of rank 1 elliptic curves -- numberdb.org/T69

    L'(E, 1), for the optimal curves of rank 1 and conductor at most 1000.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**These digits are proven**, which the table did not previously claim, and the
reason is that Sage was already offering a bound nobody took.

The original script computed the value with `E.lseries().taylor_series(a=1)`,
which documents a precision in bits and no accuracy whatever, then widened the
result by four units in the last place -- a bound asserted by hand. It did
compute at two precisions and assert that the written forms agreed, which is a
real check and better than most of the corpus, but an assertion that two
approximations agree is not a bound on either.

`E.lseries().deriv_at1(k, prec)` returns a *pair*: the value and, in Sage's
words, "a bound on the error in the approximation". It follows Section 7.5.3 of
Cohen's *A Course in Computational Algebraic Number Theory*, and the bound is a
series truncation, so it shrinks with the number of terms rather than with the
working precision. Measured on 37a, the first entry here:

    k =  100    error 1.5e-45      45 proven digits
    k = 1000    error 7.2e-239    238 proven digits, in well under a second

So a hundred digits is cheap, and this generator returns a genuine ball --
value plus proven radius -- rather than a point somebody widened.

`deriv_at1` assumes L(E,1) = 0, which holds here because every curve in this
table has rank 1 and odd analytic rank. It has no counterpart for higher
derivatives, which is why the rank 2 and rank 3 tables cannot be done this way
and remain `assumed-bound`.

The curve list is the LMFDB snapshot the original script loaded, vendored as
`curves.py` and attached to the table alongside this file. It is not
regenerated from Sage's Cremona database, and that is deliberate: L'(E, 1) is
constant across an isogeny class, so the representative decides only which
(c4, c6) an entry is filed under -- and the LMFDB and Cremona disagree about
that for 397 of these 1124 classes. Enumerating from Cremona computes exactly
the same numbers and files a third of them under different identities, which
is the failure this database guards hardest against: citations that still
resolve, and resolve to something else.
"""

import sys

import curves
import numberdb.sage as numberdb
from sage.all import EllipticCurve, RealBallField


#: Terms of the series, and working precision in bits.
#:
#: The bound falls with the number of terms and is then floored by the working
#: precision. It also weakens with the conductor, which is what decides this
#: constant: a thousand terms proves 238 digits for conductor 37 and only 85
#: for conductor 999, and the run stopped on the latter -- correctly, since a
#: hundred were claimed. Measured over the largest conductors in the list:
#:
#:     k = 1000     85 proven digits
#:     k = 4000    237
#:     k = 16000   236   (no better: the working precision is the floor now)
#:
#: So 4000, sized for the worst entry rather than the typical one. The easy
#: entries are not the bottleneck: the whole table takes about a minute either
#: way. Stated here rather than derived, because the file attached to a table
#: is meant to be how those numbers were made.
TERMS = 4000
WORKING_BITS = 800

#: Conductors covered, as the table holds them.
MAX_CONDUCTOR = 1000


class RankOneLValues(numberdb.Generator):

    table = 'T69'
    parameters = ('N', 'c4', 'c6')
    type = 'R'
    digits = 100

    #: Because `deriv_at1` hands back an error bound, not because the
    #: arithmetic afterwards is exact. See the note above.
    rigour = 'proven'

    #: Both files, since the curve list decides the identities. Naming any file
    #: replaces the automatic one, so this file has to name itself too.
    files = ('generate.py', 'curves.py')

    def enumerate(self, max_conductor=MAX_CONDUCTOR):
        for E in self._curves(max_conductor):
            c4, c6 = E.c_invariants()
            yield {'N': E.conductor(), 'c4': c4, 'c6': c6}

    def value(self, params, digits):
        E = self._curve(params)
        derivative, error = E.lseries().deriv_at1(k=TERMS, prec=WORKING_BITS)

        # The pair becomes a ball: the value, and the radius Sage proved. Every
        # digit written from here is one the bound supports, and the package's
        # precision check measures the ball rather than taking a point's word
        # for it.
        return RealBallField(WORKING_BITS)(derivative).add_error(error)

    @staticmethod
    def _curves(max_conductor=MAX_CONDUCTOR):
        """Every curve in the list, as its minimal model, in the table's order.

        Sorted by conductor and then by Cremona label, which is what the
        original did and what the stored order reflects.
        """
        found = [EllipticCurve(a_invariants).minimal_model()
                 for a_invariants in curves.data]
        found = [E for E in found if E.conductor() <= max_conductor]
        found.sort(key=lambda E: E.cremona_label())
        found.sort(key=lambda E: E.conductor())
        return found

    def _curve(self, params):
        """The one curve with these invariants.

        Matched on (c4, c6) rather than rebuilt from them: a curve with the
        right c-invariants but a different model would give the right L-value
        under a subtly wrong identity.
        """
        wanted = (params['c4'], params['c6'])
        for E in self._curves():
            if tuple(E.c_invariants()) == wanted and E.conductor() == params['N']:
                return E
        raise LookupError('no curve of conductor %s with c4, c6 = %s'
                          % (params['N'], wanted))


if __name__ == '__main__':
    generator = RankOneLValues()
    if '--publish' in sys.argv:
        print(generator.publish(
            message="recomputed with deriv_at1, which returns a proven error "
                    "bound; the digits are no longer widened by a hand-chosen "
                    "four ulps"))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
