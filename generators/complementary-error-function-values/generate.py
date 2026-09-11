"""Values of %s at rational arguments -- numberdb.org/TID_%s

Every x = a/b in lowest terms with b <= 6 and 0 <= x <= 10.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Values are computed as balls with arb.

One function per table, as T192 and T193 are the sine and cosine
integrals and T198 and T202 the two Airy functions. These six were one
table until it was split: how each is written in terms of the others
is in `Formulas`, and that they belong together is in `Similar
tables`, which is where a relation can be written down.

The grid is wider than it was, 0 <= x <= 10 rather than 0 < x <= 5.
Zero is the one argument where every one of the six is exact, and the
table that left it out left out the only entry a reader can check by
hand.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


#: Which of the six this table holds.
FUNCTION = "erfc"

# A thousand values, at the arguments somebody actually arrives holding.
#
# The grid was rationals of bounded height, every $a/b$ in lowest terms with
# $b\leq18$, which was chosen for how many entries it made. That is counting
# rather than choosing: erf(1.96) is a number people arrive with and erf(17/18)
# is not, and a denominator bound admits the second to reach the first.
#
# So: every argument of two decimal places between 0 and 10. It is a rule that
# can be stated in a line, it holds every two-decimal number a computation
# hands back in that range, and it is a thousand and one of them.
STEP = QQ(1) / QQ(100)
MAX_ARGUMENT = 10

# Bits of working precision beyond what the written digits need.
#
# `verify` recomputes every entry and compares, so a guard too small
# for some argument fails there rather than quietly rounding; it is
# stated as a knob and checked as a result.
WORKING_GUARD = 64


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _arguments(step=STEP, maximum=MAX_ARGUMENT):
    #Zero included: see the note at the top.
    count = int(QQ(maximum) / step)
    for index in range(count + 1):
        yield str(index * step)


def _real_field(digits):
    return RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def _complex_field(digits):
    return ComplexBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def _fresnel(function, x_text, digits):
    field = _complex_field(digits)
    i = field.gen(0)
    one = field(1)
    z = field(QQ(x_text))
    argument = field.pi().sqrt() * (one - i) * z / field(2)
    value = (one + i) * argument.erf() / field(2)
    component = value.imag() if function == "fresnel-S" else value.real()
    if not component.is_finite():
        raise ArithmeticError("computed a non-finite ball for %s(%s)"
                              % (function, x_text))
    return component


def _value_ball(function, x_text, digits):
    if function in ("fresnel-S", "fresnel-C"):
        return _fresnel(function, x_text, digits)

    field = _real_field(digits)
    x = field(QQ(x_text))
    if function == "erf":
        value = x.erf()
    elif function == "erfc":
        #Directly where arb offers it, because 1 - erf(x) is catastrophic
        #cancellation for large x: erfc(13/2) is 1.5e-19 and erfc(10) is
        #2.1e-45, so subtracting from 1 throws away that many leading digits
        #and the ball comes back with 99 of the 100 asked for, then 55.
        #Where it is not offered, the subtraction is done in a field wide
        #enough to survive it: 400 bits is 120 decimal digits of headroom
        #against the 45 that x = 10 costs.
        if hasattr(x, "erfc"):
            value = x.erfc()
        else:
            wide = RealBallField(numberdb.bits(digits, losing=400))
            value = wide(1) - wide(QQ(x_text)).erf()
    elif function == "erfi":
        value = x.erfi()
    elif function == "dawson":
        value = field.pi().sqrt() * (-x * x).exp() * x.erfi() / field(2)
    else:
        raise ValueError("unknown error-function-family member %r"
                         % (function,))
    if not value.is_finite():
        raise ArithmeticError("computed a non-finite ball for %s(%s)"
                              % (function, x_text))
    return value


class ComplementaryErrorFunctionValues(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE") or "T204"
    parameters = ("x",)
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self, step=STEP, maximum=MAX_ARGUMENT):
        for x in _arguments(step, maximum):
            yield {"x": x}

    def value(self, params, digits):
        x_text = str(params["x"])
        if QQ(x_text) == 0:
            #A theorem, not a measurement: every one of the six is 0 at the
            #origin except erfc, which is 1. Checked against the computed
            #ball all the same, so the exact value is verified rather than
            #asserted.
            ball = _value_ball(FUNCTION, x_text, digits)
            if not ball.contains_exact(QQ(AT_ZERO)):
                raise ValueError("%s(0) is written as %s and the computation "
                                 "does not agree" % (FUNCTION, AT_ZERO))
            return ZZ(AT_ZERO)
        return _value_ball(FUNCTION, x_text, digits)


if __name__ == "__main__":
    _key_from_stdin()
    generator = ComplementaryErrorFunctionValues()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="values of erfc(x) at rational arguments"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
