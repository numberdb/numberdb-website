"""Values of Ai at rational arguments -- numberdb.org/T198

The standard real values of Ai at rational arguments.
This draft stores every x = a/b in lowest terms with b <= 4 and |x| <= 5,
including x = 0.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Values are computed as complex balls with arb and returned as real balls.
Sage's real ball field does not expose Airy functions, but its complex ball
field does.

One function per table, as T55 and T56 are the zeros of Ai and Bi and
T57 and T58 their extrema. These four were one table until it was
split: that they solve the same equation, and that two of them are the
derivatives of the other two, is said in each table's `Similar tables`,
which is where a relation can be written down.
"""

import os
import sys
from math import gcd

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.rational_field import QQ


#: Which of the four this table holds.
FUNCTION = "Ai"
MAX_DENOMINATOR = 4
MAX_ABS_ARGUMENT = 5

# Bits of working precision beyond what the written digits need.
#
# Measured over all 244 entries: at this guard the widest result still has
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


def _arguments(max_denominator=MAX_DENOMINATOR, maximum=MAX_ABS_ARGUMENT):
    values = {QQ(0)}
    for denominator in range(1, max_denominator + 1):
        for numerator in range(-maximum * denominator,
                               maximum * denominator + 1):
            if numerator == 0 or gcd(abs(numerator), denominator) != 1:
                continue
            values.add(QQ(numerator) / QQ(denominator))
    for value in sorted(values, key=lambda x: (abs(x), 0 if x >= 0 else 1)):
        yield str(value)


def _field(digits):
    return ComplexBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def _real_airy_value(function, x_text, digits):
    field = _field(digits)
    z = field(QQ(x_text))
    if function == "Ai":
        value = z.airy_ai()
    elif function == "Ai-prime":
        value = z.airy_ai_prime()
    elif function == "Bi":
        value = z.airy_bi()
    elif function == "Bi-prime":
        value = z.airy_bi_prime()
    else:
        raise ValueError("unknown Airy function %r" % (function,))
    if not (value.real().is_finite() and value.imag().is_finite()):
        raise ArithmeticError("computed a non-finite ball for %s(%s)"
                              % (function, x_text))
    if not value.imag().contains_zero():
        raise ArithmeticError("computed a non-real ball for %s(%s): %s"
                              % (function, x_text, value))
    return value.real()


class AiryAiValues(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE") or "T198"
    parameters = ("x",)
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self, denominator=MAX_DENOMINATOR,
                  maximum=MAX_ABS_ARGUMENT):
        for x in _arguments(denominator, maximum):
            yield {"x": x}

    def value(self, params, digits):
        x_text = str(params["x"])
        return _real_airy_value(FUNCTION, x_text, digits)


if __name__ == "__main__":
    _key_from_stdin()
    generator = AiryAiValues()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="values of Ai at rational arguments"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
