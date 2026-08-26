"""Touchard polynomials -- numberdb.org/Touchard_polynomials

    T_n(x) = sum_{k=0}^{n} S(n,k) x^k

where S(n,k) is the Stirling number of the second kind: the number of ways to
partition n labelled elements into k non-empty blocks.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The rings are named rather than taken from `sage.all`, so this runs on a
modular passagemath as well as on a full SageMath. `numberdb.sage` is imported
first because it is what initialises Sage; a ring module imported before that
raises "cannot import name QQ".

Answers numberdb-data#115, and the univariate half of #114: the Bell
polynomials in one variable are these. The multivariate B_(n,k)(x_1, ...) are
a separate family and want a table of their own.
"""

import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.combinat.combinat import stirling_number2

#: How far the table runs.
#:
#: Measured rather than chosen: T_40 is 1267 characters written out and the
#: whole block is 18 KB, against a soft limit of 320 KB. T_50 would be 2009
#: characters, which is past the point where an entry is something anybody
#: reads -- the same judgement that put the Fibonacci polynomials at n = 100,
#: where F_100 is 1107 characters.
UP_TO = 40

_R = PolynomialRing(ZZ, 'x')
_x = _R.gen()


class TouchardPolynomials(numberdb.Generator):

    table = 'T110'
    parameters = ('n',)
    type = 'Z[]'

    #Exact: a polynomial with integer coefficients has no precision to choose,
    #and each coefficient is a count of set partitions.
    rigour = 'exact'

    def enumerate(self, up_to=UP_TO):
        for n in range(up_to + 1):
            yield {'n': str(n)}

    def value(self, params, digits):
        n = int(params['n'])
        return sum(stirling_number2(n, k) * _x ** k for k in range(n + 1))


if __name__ == '__main__':
    generator = TouchardPolynomials()

    if '--publish' in sys.argv:
        outcome = generator.publish(
            message='the Touchard polynomials, coefficients being the '
                    'Stirling numbers of the second kind')
        print(outcome)
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
