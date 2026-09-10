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
from math import gcd

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


POSITIVE_MAX_DENOMINATOR = 6
POSITIVE_MAX_ARGUMENT = 10
NEGATIVE_MAX_DENOMINATOR = 10

# Bits of working precision beyond what the written digits need.
#
# Measured over all 142 entries: at this guard the widest result still has
# radius less than 1e-118 when the table asks for 100 digits.
WORKING_GUARD = 64


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _positive_arguments(max_denominator=POSITIVE_MAX_DENOMINATOR,
                        maximum=POSITIVE_MAX_ARGUMENT):
    values = set()
    for denominator in range(1, max_denominator + 1):
        for numerator in range(1, maximum * denominator + 1):
            if gcd(numerator, denominator) == 1:
                values.add(QQ(numerator) / QQ(denominator))
    for value in sorted(values):
        yield str(value)


def _negative_arguments(max_denominator=NEGATIVE_MAX_DENOMINATOR):
    values = set()
    field = RealBallField(256)
    one_over_e = field(1) / field(1).exp()
    for denominator in range(1, max_denominator + 1):
        for numerator in range(1, denominator):
            if gcd(numerator, denominator) != 1:
                continue
            magnitude = QQ(numerator) / QQ(denominator)
            if field(magnitude) < one_over_e:
                values.add(-magnitude)
    for value in sorted(values, key=lambda q: (abs(q), q)):
        yield str(value)


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

    def enumerate(self, positive_denominator=POSITIVE_MAX_DENOMINATOR,
                  positive_maximum=POSITIVE_MAX_ARGUMENT,
                  negative_denominator=NEGATIVE_MAX_DENOMINATOR):
        for x in _positive_arguments(positive_denominator, positive_maximum):
            yield {"branch": "0", "x": x}
        for x in _negative_arguments(negative_denominator):
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
