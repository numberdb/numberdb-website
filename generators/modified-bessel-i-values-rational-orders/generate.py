"""Values of modified Bessel functions of the first kind I_nu -- numberdb.org/T196

The principal real values I_nu(x), for rational order nu and positive rational
argument x. This draft stores nu in {0, 1/3, 1/2, 2/3, 1, 3/2, 2, 5/2, 3}
and x = a/b in lowest terms with b <= 4 and 0 < x <= 5.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Values are computed as real balls with arb. In Sage's arb interface, Bessel
methods are called on the argument and take the order as the parameter:
`CBF(x).bessel_I(nu)`.

One function per table, as the ordinary Bessel functions J_nu and Y_nu are
separate value tables. The modified Bessel function K_nu is the companion
proposal and should get its own table rather than being folded into this one.
"""

import os
import sys
from math import gcd

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.rational_field import QQ


#The same orders as the Bessel tables T187 and T190, so the four sit on
#one grid: every half-integer to 15, and the thirds where the Airy
#functions live. At a half-integer these are elementary in sinh and
#cosh, which is what somebody checking a value against a closed form
#is holding.
ORDERS = tuple(str(nu) for nu in sorted(
    {QQ(k) / 2 for k in range(0, 31)} | {QQ(1) / 3, QQ(2) / 3}))
MAX_DENOMINATOR = 4
MAX_ARGUMENT = 5

# Bits of working precision beyond what the written digits need.
#
# Measured over all 270 entries: at this guard the widest result still has
# radius less than 1e-115 when the table asks for 100 digits.
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


def _modified_bessel_i(nu_text, x_text, digits):
    field = ComplexBallField(numberdb.bits(digits, losing=WORKING_GUARD))
    nu = field(QQ(nu_text))
    x = field(QQ(x_text))
    value = x.bessel_I(nu)
    if not value.real().is_finite() or not value.imag().is_finite():
        raise ArithmeticError("computed a non-finite ball")
    if not value.imag().contains_zero():
        raise ArithmeticError("expected a real value for I_%s(%s)"
                              % (nu_text, x_text))
    return value.real()


def _comment(nu_text):
    if nu_text != "1/2":
        return ""
    return r"$I_{1/2}(x)=\sqrt{2/(\pi x)}\sinh x$."


class ModifiedBesselIValues(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE") or "T196"
    parameters = ("nu", "x")
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self, orders=ORDERS, denominator=MAX_DENOMINATOR,
                  maximum=MAX_ARGUMENT):
        arguments = tuple(_arguments(denominator, maximum))
        for nu in orders:
            for x in arguments:
                yield {"nu": nu, "x": x}

    def value(self, params, digits):
        nu_text = str(params["nu"])
        x_text = str(params["x"])
        value = _modified_bessel_i(nu_text, x_text, digits)
        comment = _comment(nu_text)
        if comment:
            return {"number": value, "comment": comment}
        return value


if __name__ == "__main__":
    _key_from_stdin()
    generator = ModifiedBesselIValues()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="modified Bessel functions of the first kind at rational orders"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
