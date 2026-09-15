"""Values of the harmonic-number function at rational numbers -- numberdb.org/T247

For each rational x = a/b in lowest terms with b <= 12 and -4 < x <= 4, this
stores H_x = psi(x + 1) + gamma where it is finite.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Values are computed as real balls using arb's digamma function. The harmonic
rows H_n at nonnegative integers are returned as exact rationals, because their
definition is the finite sum 1 + 1/2 + ... + 1/n.
"""

import os
import sys
from math import gcd

import numberdb.sage as numberdb
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


MAX_DENOMINATOR = 12
MIN_ARGUMENT = QQ(-4)
MAX_ARGUMENT = QQ(4)
WORKING_GUARD = 96

POLES_H = frozenset([QQ(-1), QQ(-2), QQ(-3)])


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _argument_order_key(x):
    return (x.denominator(), abs(x), x < 0)


def _arguments(max_denominator=MAX_DENOMINATOR):
    found = []
    for denominator in range(1, max_denominator + 1):
        for numerator in range(
            int(MIN_ARGUMENT * denominator) + 1,
            int(MAX_ARGUMENT * denominator) + 1,
        ):
            if gcd(numerator, denominator) != 1:
                continue
            x = QQ(numerator) / QQ(denominator)
            if x.denominator() != denominator:
                continue
            if MIN_ARGUMENT < x <= MAX_ARGUMENT:
                found.append(x)
    for x in sorted(found, key=_argument_order_key):
        yield x


def _is_nonnegative_integer(x):
    return x >= 0 and x.denominator() == 1


def _harmonic_number(n):
    total = QQ(0)
    for k in range(1, int(n) + 1):
        total += QQ(1) / QQ(k)
    return total


def _field(digits):
    return RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def _finite(value, label):
    if not value.is_finite():
        raise ArithmeticError("computed a non-finite ball for %s" % (label,))
    return value


def _harmonic(x, digits):
    if _is_nonnegative_integer(x):
        return _harmonic_number(x)
    field = _field(digits)
    return _finite(
        field(x + 1).psi() + field.euler_constant(),
        "H_%s" % (x,),
    )


def _comment(x):
    text = str(x)
    if text == "0":
        return "The empty harmonic sum."
    if text == "1/2":
        return "$2-2\\log 2$."
    return ""


class HarmonicNumberRationalValues(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T247")
    parameters = ("x",)
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self, max_denominator=MAX_DENOMINATOR):
        for x in _arguments(max_denominator):
            if x not in POLES_H:
                yield {"x": str(x)}

    def value(self, params, digits):
        x = QQ(params["x"])
        value = _harmonic(x, digits)
        comment = _comment(x)
        if comment:
            return {"number": value, "comment": comment}
        return value


if __name__ == "__main__":
    _key_from_stdin()
    generator = HarmonicNumberRationalValues()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="harmonic-number values at rational arguments"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
