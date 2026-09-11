"""Values of the Lambert W function -- numberdb.org/T200

The real values of the Lambert W function at rational arguments. This draft
stores the principal branch W_0(x) for positive rational x = a/b in lowest
terms with b <= 6 and x <= 10, and both real branches for negative rational
x = a/b in lowest terms with b <= 10 and -1/e < x < 0.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Values are computed as complex balls with arb. Sage's real ball method gives
only the principal branch, so both branches are computed with
`ComplexBall.lambert_w(branch)` and checked to be real.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


# Seven hundred values, at the arguments somebody actually arrives holding.
#
# The grid was every $a/b$ in lowest terms with $b\leq6$, a bound chosen for
# the count it made rather than for the arguments it picked: W(1.96) is a
# number people arrive with and W(17/18) is not.
#
# Two decimals to 5 and one decimal from there to 20. W grows like a
# logarithm, so the far end is coarse without losing anything anybody reads
# off it, and 20 is past W(x) = 2.
STEP = QQ(1) / QQ(100)
FINE_LIMIT = 5
COARSE_STEP = QQ(1) / QQ(10)
POSITIVE_MAX_ARGUMENT = 20

# Below zero both branches are real, and only down to -1/e. Two decimals is
# the whole of that interval: -0.36 up to -0.01, and -0.37 is already outside
# the domain.
NEGATIVE_STEP = QQ(1) / QQ(100)

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


def _positive_arguments(step=STEP, fine_limit=FINE_LIMIT,
                        coarse_step=COARSE_STEP,
                        maximum=POSITIVE_MAX_ARGUMENT):
    for index in range(1, int(QQ(fine_limit) / step) + 1):
        yield str(index * step)
    first = int(QQ(fine_limit) / coarse_step) + 1
    for index in range(first, int(QQ(maximum) / coarse_step) + 1):
        yield str(index * coarse_step)


def _negative_arguments(step=NEGATIVE_STEP):
    #-1/e is where the two real branches meet, and it is irrational: the
    #comparison decides which two-decimal arguments are inside the domain
    #rather than a rounded bound standing in for it.
    field = RealBallField(256)
    one_over_e = field(1) / field(1).exp()
    index = 1
    while True:
        magnitude = index * step
        if not field(magnitude) < one_over_e:
            return
        yield str(-magnitude)
        index += 1


def _value_ball(branch_text, x_text, digits):
    branch = int(branch_text)
    field = ComplexBallField(numberdb.bits(digits, losing=WORKING_GUARD))
    value = field(QQ(x_text)).lambert_w(branch)
    if not value.real().is_finite() or not value.imag().is_finite():
        raise ArithmeticError("computed a non-finite ball for W_%s(%s)"
                              % (branch_text, x_text))
    if not value.imag().contains_zero():
        raise ArithmeticError("expected a real value for W_%s(%s)"
                              % (branch_text, x_text))
    return value.real()


def _comment(branch_text, x_text):
    if branch_text == "0" and x_text == "1":
        return "This is the omega constant."
    return ""


class LambertWValues(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE") or "T200"
    parameters = ("branch", "x")
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self, step=STEP, fine_limit=FINE_LIMIT,
                  coarse_step=COARSE_STEP,
                  positive_maximum=POSITIVE_MAX_ARGUMENT,
                  negative_step=NEGATIVE_STEP):
        for x in _positive_arguments(step, fine_limit, coarse_step,
                                     positive_maximum):
            yield {"branch": "0", "x": x}
        for x in _negative_arguments(negative_step):
            yield {"branch": "0", "x": x}
            yield {"branch": "-1", "x": x}

    def value(self, params, digits):
        branch_text = str(params["branch"])
        x_text = str(params["x"])
        value = _value_ball(branch_text, x_text, digits)
        comment = _comment(branch_text, x_text)
        if comment:
            return {"number": value, "comment": comment}
        return value


if __name__ == "__main__":
    _key_from_stdin()
    generator = LambertWValues()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="Lambert W function values at rational arguments"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
