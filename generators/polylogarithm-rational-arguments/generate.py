"""Values of the polylogarithm at rational arguments -- numberdb.org/T176

    Li_s(x) = sum_{n >= 1} x^n / n^s,

for s = 2, 3, 4 and rational x in [-1, 1], x != 0, with x written in lowest
terms and denominator at most 20.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Values are computed as complex balls using arb's polylogarithm. Even at the
endpoints no analytic continuation is used, since the defining series
converges for s > 1 on |x| = 1.
"""

import os
import sys
from math import gcd

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.rational_field import QQ


ORDERS = (2, 3, 4)
MAX_DENOMINATOR = 20

# Bits of working precision beyond what the written digits need.
WORKING_GUARD = 96


def _key_from_stdin():
    if os.environ.get('NUMBERDB_KEY_FROM_STDIN') != '1':
        return
    token = sys.stdin.read().strip()
    if '=' in token and token.split('=', 1)[0].isupper():
        token = token.split('=', 1)[1].strip().strip("'\"")
    if token:
        os.environ['NUMBERDB_API_KEY'] = token


def _comment(s, x):
    if x == '1':
        return "$\\zeta(%d)$." % s
    if x == '-1':
        return "$-(1-2^{1-%d})\\zeta(%d)$." % (s, s)
    if s == 2 and x == '1/2':
        return "$\\pi^2/12-\\log^2(2)/2$."
    if s == 2 and x == '-1/2':
        return "OEIS A355234."
    if s == 3 and x == '1/2':
        return "$7\\zeta(3)/8-\\pi^2\\log(2)/12+\\log^3(2)/6$."
    if s == 4 and x == '1/2':
        return "The standard quadrilogarithm value $\\mathrm{Li}_4(1/2)$."
    return ''


class PolylogarithmAtRationalArguments(numberdb.Generator):

    table = os.environ.get('NUMBERDB_TABLE', 'T176')
    parameters = ('s', 'x')
    type = 'R'
    digits = 100
    rigour = 'proven'

    def enumerate(self, orders=ORDERS, denominator=MAX_DENOMINATOR):
        for s in orders:
            for b in range(1, denominator + 1):
                for a in range(1, b + 1):
                    if gcd(a, b) != 1:
                        continue
                    x = QQ(a) / QQ(b)
                    for signed in (x, -x):
                        yield {'s': str(s), 'x': str(signed)}

    def value(self, params, digits):
        s = int(params['s'])
        x_text = str(params['x'])
        field = ComplexBallField(numberdb.bits(digits, losing=WORKING_GUARD))
        polylog = field(QQ(x_text)).polylog(s)
        if not (polylog.real().is_finite() and polylog.imag().is_finite()):
            raise ArithmeticError('arb returned a non-finite ball')
        if not polylog.imag().contains_zero():
            raise ArithmeticError('polylogarithm value is not real')
        value = polylog.real()
        comment = _comment(s, x_text)
        if comment:
            return {'number': value, 'comment': comment}
        return value


if __name__ == '__main__':
    _key_from_stdin()
    generator = PolylogarithmAtRationalArguments()
    if '--publish' in sys.argv or os.environ.get('NUMBERDB_PUBLISH') == '1':
        print(generator.publish(message='polylogarithm values at rational arguments'))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
