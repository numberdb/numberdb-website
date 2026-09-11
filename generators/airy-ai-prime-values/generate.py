"""Values of Ai' at rational arguments -- numberdb.org/T201

The standard real values of Ai' at rational arguments.
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

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.rational_field import QQ


# A thousand values, at the arguments somebody actually arrives holding.
#
# The grid was rationals of bounded height, every $a/b$ in lowest terms with
# $b\leq12$, which was chosen for how many entries it made rather than for
# which arguments those were: Ai(1.96) is a number people arrive with and
# Ai(7/12) is not.
#
# Two decimals out to |x| = 5, one decimal from there to |x| = 10. The
# functions are consulted finely where they turn over and coarsely in the
# tails, and the wider range is what keeps the zeros in the table: Ai has
# four in |x| <= 10 and Bi has four, and all but the first two lie beyond 5.
FINE_STEP = QQ(1) / QQ(100)
FINE_LIMIT = 5
COARSE_STEP = QQ(1) / QQ(10)
MAX_ABS_ARGUMENT = 10

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


def _arguments(fine_step=FINE_STEP, fine_limit=FINE_LIMIT,
               coarse_step=COARSE_STEP, maximum=MAX_ABS_ARGUMENT):
    values = {QQ(0)}
    for index in range(1, int(QQ(fine_limit) / fine_step) + 1):
        values.add(index * fine_step)
        values.add(-index * fine_step)
    first = int(QQ(fine_limit) / coarse_step) + 1
    for index in range(first, int(QQ(maximum) / coarse_step) + 1):
        values.add(index * coarse_step)
        values.add(-index * coarse_step)
    #Smaller absolute value first, and the positive one ahead of its negative:
    #the arguments nearest the origin are the ones most often wanted.
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


class AiryAiPrimeValues(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE") or "T201"
    parameters = ("x",)
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self, fine_step=FINE_STEP, fine_limit=FINE_LIMIT,
                  coarse_step=COARSE_STEP, maximum=MAX_ABS_ARGUMENT):
        for x in _arguments(fine_step, fine_limit, coarse_step, maximum):
            yield {"x": x}

    def value(self, params, digits):
        x_text = str(params["x"])
        return _real_airy_value(FUNCTION, x_text, digits)


if __name__ == "__main__":
    _key_from_stdin()
    generator = AiryAiPrimeValues()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="values of Ai' at rational arguments"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
