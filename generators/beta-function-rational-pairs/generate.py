"""Values of the Beta function at pairs of rational numbers -- numberdb.org/T177

    B(a, b) = Gamma(a) Gamma(b) / Gamma(a + b),

for positive rational a <= b, with a and b at most 2 and written in lowest
terms with denominator at most 6.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Values are computed as real balls using arb's complete Beta function. Rows for
which one parameter is a positive integer are returned as exact rationals, by
the recurrence B(n, x) = (n - 1)! / (x (x + 1) ... (x + n - 1)).
"""

import os
import sys
from math import gcd

import numberdb.sage as numberdb
from sage.arith.misc import factorial
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


# A denominator bound is the right rule for this one, which is not true of
# most tables of values. B(a,b) = Γ(a)Γ(b)/Γ(a+b), and the rationals with
# small denominators are where it is a number anybody names: B(1/2,1/2) is
# π, B(1/3,1/3) and B(1/6,1/6) are the periods of the equianharmonic and
# lemniscatic curves, and the reflection and multiplication formulas reach
# exactly the sixths, quarters and thirds. Nobody arrives holding B(1.96,1),
# which is the opposite of the situation for erf.
#
# So the bound stays and the range grows: every $a/b$ in lowest terms with
# $b\leq6$ up to 3 rather than 2. Unordered pairs, because B is symmetric,
# which is 36 rationals and 666 of them.
MAX_DENOMINATOR = 6
MAX_PARAMETER = 3

# Bits of working precision beyond what the written digits need.
#
# `verify` recomputes every entry and compares, so a guard too small for
# some pair fails there rather than quietly rounding.
WORKING_GUARD = 96


def _key_from_stdin():
    if os.environ.get('NUMBERDB_KEY_FROM_STDIN') != '1':
        return
    token = sys.stdin.read().strip()
    if '=' in token and token.split('=', 1)[0].isupper():
        token = token.split('=', 1)[1].strip().strip("'\"")
    if token:
        os.environ['NUMBERDB_API_KEY'] = token


def _rationals(max_denominator=MAX_DENOMINATOR, max_parameter=MAX_PARAMETER):
    for denominator in range(1, max_denominator + 1):
        for numerator in range(1, max_parameter * denominator + 1):
            if gcd(numerator, denominator) != 1:
                continue
            yield QQ(numerator) / QQ(denominator)


def _is_positive_integer(value):
    return value > 0 and value.denominator() == 1


def _integer_parameter_beta(n, x):
    n = ZZ(n)
    denominator = QQ(1)
    for k in range(n):
        denominator *= QQ(x) + QQ(k)
    return QQ(factorial(n - 1)) / denominator


def _exact_if_rational(a, b):
    if _is_positive_integer(a):
        return _integer_parameter_beta(a, b)
    if _is_positive_integer(b):
        return _integer_parameter_beta(b, a)
    return None


def _comment(a_text, b_text):
    if a_text == '1/2' and b_text == '1/2':
        return "$\\pi$."
    if a_text == '1/2' and b_text == '3/2':
        return "$\\pi/2$."
    if a_text == '1/3' and b_text == '1/3':
        return "The real period of the Dixonian elliptic functions."
    if a_text == '1/3' and b_text == '2/3':
        return "$2\\pi/\\sqrt{3}$."
    if a_text == '1/4' and b_text == '1/2':
        return "The lemniscate constant in the normalisation $\\Gamma(1/4)^2/\\sqrt{2\\pi}$."
    if a_text == '1/4' and b_text == '1/4':
        return "$\\Gamma(1/4)^2/\\sqrt{\\pi}$."
    if a_text == '2/3' and b_text == '4/3':
        return "$2\\sqrt{3}\\,\\pi/9$."
    return ''


class BetaFunctionAtRationalPairs(numberdb.Generator):

    table = os.environ.get('NUMBERDB_TABLE', 'T177')
    parameters = ('a', 'b')
    type = 'R'
    digits = 100
    rigour = 'proven'

    def enumerate(self, max_denominator=MAX_DENOMINATOR,
                  max_parameter=MAX_PARAMETER):
        rationals = list(_rationals(max_denominator, max_parameter))
        for a in rationals:
            for b in rationals:
                if a <= b:
                    yield {'a': str(a), 'b': str(b)}

    def value(self, params, digits):
        a = QQ(params['a'])
        b = QQ(params['b'])
        exact = _exact_if_rational(a, b)
        value = exact
        if value is None:
            field = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
            value = field(a).beta(field(b))
            if not value.is_finite():
                raise ArithmeticError('arb returned a non-finite ball')
        comment = _comment(str(a), str(b))
        if comment:
            return {'number': value, 'comment': comment}
        return value


if __name__ == '__main__':
    _key_from_stdin()
    generator = BetaFunctionAtRationalPairs()
    if '--publish' in sys.argv or os.environ.get('NUMBERDB_PUBLISH') == '1':
        print(generator.publish(message='Beta-function values at rational pairs'))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
