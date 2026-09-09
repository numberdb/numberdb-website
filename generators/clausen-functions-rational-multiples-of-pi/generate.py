"""Values of the Clausen functions at rational multiples of pi -- numberdb.org/T175

    Cl_s(pi t) = Im Li_s(exp(i pi t)) for even s, and
    Cl_s(pi t) = Re Li_s(exp(i pi t)) for odd s.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Values are computed as complex balls using arb's polylogarithm, with the
argument exp(i*pi*t) also built as a ball from the exact rational t.
"""

import os
import sys
from math import gcd

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.rational_field import QQ


ORDERS = (2, 3, 4)
MAX_DENOMINATOR = 24

# Bits of working precision beyond what the written digits need.
#
# Measured over all 538 entries: at this guard the widest result still carries
# more than 112 decimal digits when the table asks for 100.
WORKING_GUARD = 96


def _key_from_stdin():
    if os.environ.get('NUMBERDB_KEY_FROM_STDIN') != '1':
        return
    token = sys.stdin.read().strip()
    if '=' in token and token.split('=', 1)[0].isupper():
        token = token.split('=', 1)[1].strip().strip("'\"")
    if token:
        os.environ['NUMBERDB_API_KEY'] = token


def _comment(s, t):
    if s == 2 and t == '1/2':
        return "Catalan's constant $G$."
    if s == 2 and t == '1/3':
        return "Gieseking's constant, the volume of the regular ideal tetrahedron."
    if s == 2 and t == '2/3':
        return "$2/3$ of Gieseking's constant."
    if s == 3 and t == '1/3':
        return "$\\zeta(3)/3$."
    if s == 3 and t == '1/2':
        return "$-3\\zeta(3)/32$."
    if s == 3 and t == '2/3':
        return "$-4\\zeta(3)/9$."
    if s == 3 and t == '1':
        return "$-3\\zeta(3)/4$."
    if s == 4 and t == '1/2':
        return "$L(4,\\chi_4(3,\\cdot))$, Dirichlet's $\\beta(4)$."
    if s == 4 and t == '2/3':
        return "$(\\sqrt3/2)L(4,\\chi_3(2,\\cdot))$."
    return ''


class ClausenFunctionsAtRationalMultiplesOfPi(numberdb.Generator):

    table = 'T175'
    parameters = ('s', 't')
    type = 'R'
    digits = 100
    rigour = 'proven'

    def enumerate(self, orders=ORDERS, denominator=MAX_DENOMINATOR):
        for s in orders:
            for b in range(1, denominator + 1):
                for a in range(1, b + 1):
                    if gcd(a, b) != 1:
                        continue
                    if s % 2 == 0 and a == b:
                        continue
                    yield {'s': str(s), 't': str(QQ(a) / QQ(b))}

    def value(self, params, digits):
        s = int(params['s'])
        t_text = str(params['t'])
        field = ComplexBallField(numberdb.bits(digits, losing=WORKING_GUARD))
        i = field.gen(0)
        z = (i * field.pi() * field(QQ(t_text))).exp()
        polylog = z.polylog(s)
        value = polylog.imag() if s % 2 == 0 else polylog.real()
        if not value.is_finite():
            raise ArithmeticError('arb returned a non-finite ball')
        comment = _comment(s, t_text)
        if comment:
            return {'number': value, 'comment': comment}
        return value


if __name__ == '__main__':
    _key_from_stdin()
    generator = ClausenFunctionsAtRationalMultiplesOfPi()
    if '--publish' in sys.argv or os.environ.get('NUMBERDB_PUBLISH') == '1':
        print(generator.publish(message='Clausen values at rational multiples of pi'))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
