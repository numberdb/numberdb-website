"""Values of the logarithmic integral -- numberdb.org/T191

The real values of li(x) at
positive rational arguments. This draft stores every x = a/b in lowest terms
with b <= 6 and 0 < x <= 5, except that li(1) is omitted.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Values are computed as real balls with arb. Sage's real ball methods use the
same branch conventions as the table for positive real arguments.

One function per table, as T20 and T21 are the zeros of the two kinds
of Bessel function and T22 and T23 their extrema. These seven values
were one table until it was split: that they are all integrals of an
elementary function is said in each table's `Similar tables`, which is
where a relation can be written down.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


#: Which integral this table holds.
FUNCTION = "li"
# Five hundred values or a thousand, at the arguments somebody actually
# arrives holding.
#
# The grid was every $a/b$ in lowest terms with $b\leq6$ and $x\leq5$, a bound
# picked for the count it made rather than for the arguments it chose: Si(1.96)
# is a number people arrive with and Si(17/18) is not.
#
# So: every argument of two decimal places up to 10. li is singular at 1, which `enumerate` already skips, and the
# grid starts at 1/100 because li(0) = 0 is the one value it
# would add and the integral is improper there.
STEP = QQ(1) / QQ(100)
MAX_ARGUMENT = 10

# Bits of working precision beyond what the written digits need.
#
# `verify` recomputes every entry and compares, so a guard too small
# for some argument fails there rather than quietly rounding.
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
    #From one step above zero: every function here is either
    #singular at the origin or exactly zero there.
    for index in range(1, int(QQ(maximum) / step) + 1):
        yield str(index * step)


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


class LogarithmicIntegralValues(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE") or "T191"
    parameters = ("x",)
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self, step=STEP, maximum=MAX_ARGUMENT):
        for x in _arguments(step, maximum):
            if x == "1":
                #li is singular there.
                continue
            yield {"x": x}

    def value(self, params, digits):
        function = FUNCTION
        x_text = str(params["x"])
        value = _value_ball(function, x_text, digits)
        comment = _comment(function, x_text)
        if comment:
            return {"number": value, "comment": comment}
        return value


if __name__ == "__main__":
    _key_from_stdin()
    generator = LogarithmicIntegralValues()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(generator.publish(
            message="values of the logarithmic integral"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
