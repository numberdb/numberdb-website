"""Values of the error function family -- numberdb.org/TBD

The standard real values of erf, erfc, erfi, Dawson's integral and the
Fresnel integrals at positive rational arguments. This draft stores every
x = a/b in lowest terms with b <= 6 and 0 < x <= 5.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Values are computed as real or complex balls with arb. Sage has direct real
ball methods for erf and erfi. The complementary error function is computed as
1 - erf(x), Dawson's integral from its relation with erfi, and the Fresnel
integrals from their standard relation with erf at a complex argument.
"""

import os
import sys
from math import gcd

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


FUNCTIONS = ("erf", "erfc", "erfi", "dawson", "fresnel-S", "fresnel-C")
MAX_DENOMINATOR = 6
MAX_ARGUMENT = 5

# Bits of working precision beyond what the written digits need.
#
# Measured over all 360 entries: at this guard the widest result still has
# radius less than 1e-108 when the table asks for 100 digits.
WORKING_GUARD = 64


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _arguments(max_denominator=MAX_DENOMINATOR, maximum=MAX_ARGUMENT):
    values = set()
    for denominator in range(1, max_denominator + 1):
        for numerator in range(1, maximum * denominator + 1):
            if gcd(numerator, denominator) == 1:
                values.add(QQ(numerator) / QQ(denominator))
    for value in sorted(values):
        yield str(value)


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
        value = field(1) - x.erf()
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


class ErrorFunctionFamilyValues(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE") or "TBD"
    parameters = ("function", "x")
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self, functions=FUNCTIONS, denominator=MAX_DENOMINATOR,
                  maximum=MAX_ARGUMENT):
        arguments = tuple(_arguments(denominator, maximum))
        for function in functions:
            for x in arguments:
                yield {"function": function, "x": x}

    def value(self, params, digits):
        function = str(params["function"])
        x_text = str(params["x"])
        return _value_ball(function, x_text, digits)


if __name__ == "__main__":
    _key_from_stdin()
    generator = ErrorFunctionFamilyValues()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="error function family values at rational arguments"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
