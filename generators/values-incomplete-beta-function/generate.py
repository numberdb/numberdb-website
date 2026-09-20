"""Values of the incomplete beta function B(x;a,b) -- numberdb.org/T353

This generator fills T353 with real values of the unregularised incomplete
beta function on the rational grid stated in the table. Rows known to be
rational by `_is_rational_row` are omitted: both parameters integral, or one
strict half-integer parameter paired with an integral parameter at a square
argument, with the mirrored case at a square value of `1 - x`.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send changes, with NUMBERDB_API_KEY set
"""

import os
import sys
from math import isqrt

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


TABLE = os.environ.get("NUMBERDB_TABLE", "T353")
DIGITS = 100
WORKING_GUARD = 64

PARAMETER_VALUES = (QQ(1) / 2, QQ(1), QQ(3) / 2, QQ(2), QQ(5) / 2)
MAX_X_DENOMINATOR = 10


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _field(digits, guard=WORKING_GUARD):
    return ComplexBallField(numberdb.bits(digits, losing=guard))


def _real_field(digits, guard=WORKING_GUARD):
    return RealBallField(numberdb.bits(digits, losing=guard))


def x_values(max_denominator=MAX_X_DENOMINATOR):
    values = set()
    for denominator in range(2, max_denominator + 1):
        for numerator in range(1, denominator):
            value = QQ(numerator) / QQ(denominator)
            if value.denominator() == denominator:
                values.add(value)
    return tuple(sorted(values))


def _is_integer(value):
    return QQ(value).denominator() == 1


def _is_square_rational(value):
    numerator = int(QQ(value).numerator())
    denominator = int(QQ(value).denominator())
    return isqrt(numerator) ** 2 == numerator \
        and isqrt(denominator) ** 2 == denominator


def _is_strict_half_integer(value):
    return QQ(value).denominator() == 2


def _is_rational_row(x, a, b):
    if _is_integer(a) and _is_integer(b):
        return True
    if _is_strict_half_integer(a) and _is_integer(b) and _is_square_rational(x):
        return True
    if _is_integer(a) and _is_strict_half_integer(b) and _is_square_rational(1 - x):
        return True
    return False


def _real(value, label):
    if not value.real().is_finite() or not value.imag().is_finite():
        raise ArithmeticError("computed a non-finite ball for %s: %s" % (label, value))
    if not value.imag().contains_zero():
        raise ArithmeticError("expected a real value for %s: %s" % (label, value))
    return value.real()


def complete_beta(a, b, digits):
    field = _real_field(digits)
    ab = field(a)
    bb = field(b)
    return ab.gamma() * bb.gamma() / field(a + b).gamma()


def _incomplete_beta_direct(x, a, b, digits):
    field = _field(digits)
    xb = field(x)
    ab = field(a)
    bb = field(b)
    value = xb ** ab / ab
    value *= xb.hypergeometric([ab, field(1) - bb], [ab + field(1)])
    return _real(value, "B(%s;%s,%s)" % (x, a, b))


def incomplete_beta(x, a, b, digits):
    if QQ(x) > QQ(1) / 2:
        return complete_beta(a, b, digits) - _incomplete_beta_direct(1 - x, b, a, digits)
    return _incomplete_beta_direct(x, a, b, digits)


class IncompleteBetaValues(numberdb.Generator):

    table = TABLE
    parameters = ("x", "a", "b")
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self):
        for x in x_values():
            for a in PARAMETER_VALUES:
                for b in PARAMETER_VALUES:
                    if _is_rational_row(x, a, b):
                        continue
                    yield {"x": str(x), "a": str(a), "b": str(b)}

    def value(self, params, digits):
        x = QQ(params["x"])
        a = QQ(params["a"])
        b = QQ(params["b"])
        return incomplete_beta(x, a, b, digits)


if __name__ == "__main__":
    _key_from_stdin()
    generator = IncompleteBetaValues()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="recompute incomplete beta values in ball arithmetic"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
