"""Partial Bell polynomials -- numberdb.org/Partial_Bell_polynomials

    B_(n,k)(x_1, ..., x_(n-k+1))

the polynomial whose coefficient of x_1^j1 x_2^j2 ... is the number of ways to
partition n labelled elements into k blocks, exactly j_i of them of size i.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The rings are named rather than taken from `sage.all`, so this runs on a
modular passagemath as well as on a full SageMath.

Answers numberdb-data#114. The Bell polynomials in one variable are a
different family -- the Touchard polynomials -- and have their own table.
"""

import sys

import numberdb.sage as numberdb
from sage.combinat.combinat import bell_polynomial
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing

#: How far the table runs, and why it is not further.
#:
#: Not size: at n <= 16 the block would be 20 KB against a soft limit of 320.
#: The binding constraint is the number of variables. Search matches `x^2+1`
#: against `y^2+1`, which needs a key invariant under renaming, and that key
#: is found by trying permutations -- so the site refuses a polynomial in more
#: than six variables rather than attempt a factorial search.
#:
#: B_(n,k) involves n-k+1 variables, so the refusal starts at B_(8,2), which
#: has seven. Stopping at n = 7 keeps every entry of every row: 28 of 28. Going
#: further would leave holes in the middle of each row that nothing in the
#: table could explain.
UP_TO = 7


def _partial_bell(n, k):
    """B_(n,k) with the variables named x1, x2, ... rather than x0, x1, ...

    Sage indexes them from zero. The notation indexes from one, and so does
    every reference a reader will have open; a table that renamed them would
    be less readable and no more true.
    """
    polynomial = bell_polynomial(n, k)
    names = ['x%d' % (i + 1) for i in range(n - k + 1)]
    ring = PolynomialRing(ZZ, names)
    old = polynomial.parent().gens()
    return ring(polynomial.subs(
        {generator: ring.gen(i) for i, generator in enumerate(old)}))


class PartialBellPolynomials(numberdb.Generator):

    table = 'T113'
    parameters = ('n', 'k')
    type = 'Z[]'

    #Exact: the coefficients count set partitions.
    rigour = 'exact'

    def enumerate(self, up_to=UP_TO):
        for n in range(1, up_to + 1):
            for k in range(1, n + 1):
                yield {'n': str(n), 'k': str(k)}

    def value(self, params, digits):
        return _partial_bell(int(params['n']), int(params['k']))


if __name__ == '__main__':
    generator = PartialBellPolynomials()

    if '--publish' in sys.argv:
        outcome = generator.publish(
            message='the partial Bell polynomials, variables indexed from one')
        print(outcome)
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
