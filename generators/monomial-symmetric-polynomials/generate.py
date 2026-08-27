"""Monomial symmetric polynomials -- numberdb.org/Monomial_symmetric_polynomials

    m_lambda(x_1, ..., x_n) = sum of the distinct rearrangements of x^lambda

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Computed from the definition rather than through Sage's SymmetricFunctions,
whose `.expand()` needs more of Sage initialised than the named imports below
provide. Checked against it over the whole range of this table.

Answers numberdb-data#106.
"""

import sys
from itertools import permutations

import numberdb.sage as numberdb
from sage.misc.misc_c import prod
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing

#: How far the table runs: partitions of at most 4, in at most 5 variables,
#: where the longest entry is 387 characters.
MOST_VARIABLES = 5
LARGEST_PARTITION = 4


def _partitions(total, longest=None):
    """Partitions of `total`, largest part first."""
    if longest is None:
        longest = total
    if total == 0:
        yield []
        return
    for part in range(min(total, longest), 0, -1):
        for rest in _partitions(total - part, part):
            yield [part] + rest


class MonomialSymmetricPolynomials(numberdb.Generator):

    table = 'T121'
    parameters = ('n', 'lambda')
    type = 'Z[]'

    #Exact: every coefficient is one.
    rigour = 'exact'

    def enumerate(self, most_variables=MOST_VARIABLES,
                  largest=LARGEST_PARTITION):
        for n in range(1, most_variables + 1):
            for size in range(1, largest + 1):
                for partition in _partitions(size):
                    if len(partition) <= n:
                        yield {'n': str(n),
                               'lambda': ','.join(str(p) for p in partition)}

    def value(self, params, digits):
        n = int(params['n'])
        partition = [int(p) for p in params['lambda'].split(',')]
        ring = PolynomialRing(ZZ, ['x%d' % (i + 1) for i in range(n)])
        exponents = partition + [0] * (n - len(partition))
        return sum(prod(g ** a for g, a in zip(ring.gens(), arrangement))
                   for arrangement in sorted(set(permutations(exponents))))


if __name__ == '__main__':
    generator = MonomialSymmetricPolynomials()

    if '--publish' in sys.argv:
        print(generator.publish(
            message='the monomial symmetric polynomials'))
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
