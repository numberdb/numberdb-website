"""Values of exponential, logarithmic and trigonometric integrals -- numberdb.org/T188

The real values of Ei(x), E_1(x), li(x), Si(x), Ci(x), Shi(x) and Chi(x) at
positive rational arguments. This draft stores every x = a/b in lowest terms
with b <= 6 and 0 < x <= 5, except that li(1) is omitted.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Values are computed as real balls with arb. Sage's real ball methods use the
same branch conventions as the table for positive real arguments.
"""

import os
import sys
from math import gcd

import numberdb.sage as numberdb
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


FUNCTIONS = ("Ei", "E1", "li", "Si", "Ci", "Shi", "Chi")
MAX_DENOMINATOR = 6
MAX_ARGUMENT = 5

# Bits of working precision beyond what the written digits need.
#
# Measured over all 419 entries: at this guard the widest result still has
# radius less than 1e-117 when the table asks for 100 digits.
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


def _value_ball(function, x_text, digits):
    field = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
    xq = QQ(x_text)
    x = field(xq)
    if function == "Ei":
        value = x.Ei()
    elif function == "E1":
        value = -field(-xq).Ei()
    elif function == "li":
        value = x.log_integral()
    elif function == "Si":
        value = x.Si()
    elif function == "Ci":
        value = x.Ci()
    elif function == "Shi":
        value = x.Shi()
    elif function == "Chi":
        value = x.Chi()
    else:
        raise ValueError("unknown integral function %r" % (function,))
    if not value.is_finite():
        raise ArithmeticError("computed a non-finite ball for %s(%s)"
                              % (function, x_text))
    return value


def _comment(function, x_text):
    if function == "li" and x_text == "2":
        return ("This is the constant subtracted in Riemann's offset "
                "logarithmic integral $\\operatorname{Li}(x)$.")
    return ""


class ExponentialLogarithmicTrigonometricIntegrals(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T188")
    parameters = ("function", "x")
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self, functions=FUNCTIONS, denominator=MAX_DENOMINATOR,
                  maximum=MAX_ARGUMENT):
        arguments = tuple(_arguments(denominator, maximum))
        for function in functions:
            for x in arguments:
                if function == "li" and x == "1":
                    continue
                yield {"function": function, "x": x}

    def value(self, params, digits):
        function = str(params["function"])
        x_text = str(params["x"])
        value = _value_ball(function, x_text, digits)
        comment = _comment(function, x_text)
        if comment:
            return {"number": value, "comment": comment}
        return value


if __name__ == "__main__":
    _key_from_stdin()
    generator = ExponentialLogarithmicTrigonometricIntegrals()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(generator.publish(
            message="exponential, logarithmic and trigonometric integral values"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
