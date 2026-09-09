"""Sums of powers S_p(n) -- numberdb.org/T179.

    S_p(n) = sum_{k=1}^n k^p

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The rings are named rather than taken from `sage.all`, so this runs on a
modular passagemath as well as on a full SageMath.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import bernoulli, binomial
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ

#: How far the table runs. Measured before the draft was created: 51 entries,
#: S_50 is 729 characters written out, and the whole entries block is 15.7 KB.
UP_TO = 50

_R = PolynomialRing(QQ, 'n')
_n = _R.gen()


def _key_from_stdin():
    if os.environ.get('NUMBERDB_KEY_FROM_STDIN') != '1':
        return
    token = sys.stdin.read().strip()
    if '=' in token and token.split('=', 1)[0].isupper():
        token = token.split('=', 1)[1].strip().strip("'\"")
    if token:
        os.environ['NUMBERDB_API_KEY'] = token


def sums_of_powers_polynomial(p):
    coefficient = QQ(1) / QQ(p + 1)
    value = _R.zero()
    for j in range(p + 1):
        value += (coefficient * QQ((-1) ** j) * QQ(binomial(p + 1, j))
                  * QQ(bernoulli(j)) * _n ** (p + 1 - j))
    return value


class SumsOfPowers(numberdb.Generator):

    table = os.environ.get('NUMBERDB_TABLE', 'T179')
    parameters = ('p',)
    type = 'Q[]'

    #Exact: rational coefficients, no precision to choose.
    rigour = 'exact'

    def enumerate(self, up_to=UP_TO):
        for p in range(up_to + 1):
            yield {'p': str(p)}

    def value(self, params, digits):
        return sums_of_powers_polynomial(int(params['p']))


if __name__ == '__main__':
    _key_from_stdin()
    generator = SumsOfPowers()

    if os.environ.get('NUMBERDB_PUBLISH') == '1' or '--publish' in sys.argv:
        print(generator.publish(
            message='sums of powers as polynomials in n, p = 0..%d'
                    % (UP_TO,)))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
