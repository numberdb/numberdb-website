"""Heat (caloric) polynomials -- numberdb.org/T254

    P_m(x,t) = sum_{l=0}^{floor(m/2)} m!/(l!(m-2l)!) x^(m-2l)t^l

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The rings are named rather than taken from `sage.all`, so this runs on a
modular passagemath as well as on a full SageMath. `numberdb.sage` is imported
first because it is what initialises Sage.

Answers numberdb-data#109, in the family numberdb-data#139.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing

#: How far the table runs. Measured: P_50 is 1016 characters written out, and
#: the whole block is 21 KB. This also keeps the Hermite-polynomial
#: specialization check inside the current range of T104.
UP_TO = 50

_R = PolynomialRing(ZZ, ('x', 't'))
_x, _t = _R.gens()


def _polynomials(up_to):
    values = [_R.one()]
    for m in range(up_to):
        current = values[-1]
        values.append(_x * current + ZZ(2) * _t * current.derivative(_x))
    return values


_VALUES = _polynomials(UP_TO)


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


class HeatCaloricPolynomials(numberdb.Generator):

    table = 'T254'
    parameters = ('m',)
    type = 'Z[]'

    # Exact: integer coefficients, no precision to choose.
    rigour = 'exact'

    def enumerate(self, up_to=UP_TO):
        for m in range(up_to + 1):
            yield {'m': str(m)}

    def value(self, params, digits):
        return _VALUES[int(params['m'])]


if __name__ == '__main__':
    _key_from_stdin()
    generator = HeatCaloricPolynomials()

    if '--publish' in sys.argv or bool(int(os.environ.get('NUMBERDB_PUBLISH', '0'))):
        print(generator.publish(message='heat-polynomial values from exact recurrence'))
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
