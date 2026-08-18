"""Fibonacci polynomials F_n(x) -- numberdb.org (table wanted: numberdb-data#100)

    F_0 = 0,  F_1 = 1,  F_n(x) = x F_(n-1)(x) + F_(n-2)(x)

so F_2 = x, F_3 = x^2 + 1, F_4 = x^3 + 2x, and F_n(1) is the nth Fibonacci
number.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**The convention has to be stated, because there is more than one.** These are
the polynomials in the recurrence above, with F_0 = 0 and F_1 = 1. Two other
readings are in circulation and give different tables:

  * an indexing shifted by one, where the first polynomial is called F_1 = 1
    and everything moves down;
  * the Fibonacci polynomials of the *second* kind, which are the Lucas
    polynomials -- same recurrence, started at L_0 = 2, L_1 = x, and held in
    their own table.

Sage has no `fibonacci_polynomial`, so the recurrence is written out here. That
is not a hardship: it *is* the definition, and a reader can check the code
against the line at the top of this file rather than against a library's
documentation.

The values are exact. There is no precision to choose, nothing to round, and
`rigour = 'exact'` says so -- writing fewer coefficients of a polynomial does
not approximate it, it makes it a different polynomial.
"""

import sys

import numberdb.sage as numberdb
from sage.all import PolynomialRing, ZZ


#: How far the table goes.
#:
#: Not chosen for roundness. A polynomial of degree n has about n/2 terms with
#: coefficients of O(n) digits, so a table running to n costs O(n^3): measured
#: here, 0..100 is 42 KB, 0..150 is 123 KB and 0..200 is 269 KB, against a soft
#: limit of 320 KB for the whole entries block. 150 sits in the middle of the
#: 100-200 KB the database aims at and leaves room for somebody to extend it
#: without breaching anything, and the largest entry is 2248 characters, which
#: is still a thing you can look at.
UP_TO = 150


class FibonacciPolynomials(numberdb.Generator):

    table = None            # set when the table exists; see --publish below
    parameters = ('n',)
    type = 'Z[]'
    rigour = 'exact'

    def enumerate(self, up_to=UP_TO):
        for n in range(0, up_to + 1):
            yield {'n': n}

    def value(self, params, digits):
        # The recurrence, iteratively: F_0 = 0, F_1 = 1, F_n = x F_(n-1) +
        # F_(n-2). Iterative rather than recursive because F_150 recursed
        # naively is 2^150 calls, and rather than by the closed form in
        # binomial coefficients because the recurrence is what the table says
        # it is holding.
        ring = PolynomialRing(ZZ, 'x')
        x = ring.gen()
        previous, current = ring(0), ring(1)
        for _ in range(int(ZZ(params['n']))):
            previous, current = current, x * current + previous
        return previous


if __name__ == '__main__':
    generator = FibonacciPolynomials()

    if '--publish' in sys.argv:
        outcome = generator.publish(
            message='Fibonacci polynomials from the recurrence, n = 0..%d'
                    % (UP_TO,))
        print(outcome)
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
