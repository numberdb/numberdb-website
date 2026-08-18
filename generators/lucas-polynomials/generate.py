"""Lucas polynomials L_n(x) -- numberdb.org (table wanted: numberdb-data#101)

    L_0 = 2,  L_1 = x,  L_n(x) = x L_(n-1)(x) + L_(n-2)(x)

so L_2 = x^2 + 2, L_3 = x^3 + 3x, L_4 = x^4 + 4x^2 + 2, and L_n(1) is the nth
Lucas number.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**The convention has to be stated, because there is more than one.** The
recurrence is the same one the Fibonacci polynomials obey and only the two
starting values differ, which is exactly why the pair has to say which is
which: L_0 = 2 and L_1 = x here. Elsewhere these are called the Fibonacci
polynomials of the second kind, and some authors index them from L_1.

They are also the Lucas sequence V_n(x, -1), the companion of the U_n(x, -1)
that gives the Fibonacci polynomials -- the same distinction as between Lucas
and Fibonacci numbers, which is what these become at x = 1.

Sage has no `lucas_polynomial`, so the recurrence is written out. That is not a
hardship: it is the definition, and a reader can check the code against the
line at the top of this file rather than against a library's documentation.

The values are exact, and `rigour = 'exact'` says so: there is no precision to
choose, and writing fewer coefficients of a polynomial does not approximate it,
it makes it a different polynomial.
"""

import sys

import numberdb.sage as numberdb
from sage.all import PolynomialRing, ZZ


#: How far the table goes. Kept equal to the Fibonacci polynomials' range: the
#: two tables are read together, and a reader comparing L_n with F_n should not
#: find one of them missing. Measured at 0..150: 125 KB, against a soft limit
#: of 320 KB for the whole entries block, with a largest entry of 2255
#: characters.
UP_TO = 150


class LucasPolynomials(numberdb.Generator):

    table = None            # set when the table exists
    parameters = ('n',)
    type = 'Z[]'
    rigour = 'exact'

    def enumerate(self, up_to=UP_TO):
        for n in range(0, up_to + 1):
            yield {'n': n}

    def value(self, params, digits):
        # L_0 = 2, L_1 = x, L_n = x L_(n-1) + L_(n-2). Iteratively, since
        # L_150 recursed naively is 2^150 calls.
        ring = PolynomialRing(ZZ, 'x')
        x = ring.gen()
        previous, current = ring(2), ring.gen()
        for _ in range(int(ZZ(params['n']))):
            previous, current = current, x * current + previous
        return previous


if __name__ == '__main__':
    generator = LucasPolynomials()

    if '--publish' in sys.argv:
        outcome = generator.publish(
            message='Lucas polynomials from the recurrence, n = 0..%d' % (UP_TO,))
        print(outcome)
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
