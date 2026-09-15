"""Values of the polygamma functions psi^(n) at rational numbers -- numberdb.org/T250

For n = 1, 2 and each rational x = a/b in lowest terms with b <= 12 and
-4 < x <= 4, this stores psi^(n)(x) where it is finite.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

Values are computed as real parts of complex balls using arb's polygamma
function. The imaginary parts are checked to contain zero.
"""

import os
import sys
from math import gcd

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.rational_field import QQ


MAX_ORDER = 2
MAX_DENOMINATOR = 12
MIN_ARGUMENT = QQ(-4)
MAX_ARGUMENT = QQ(4)
WORKING_GUARD = 96


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
                if x.denominator() == 1 and x <= 0:
                    continue
                found.append(x)
    for x in sorted(found, key=_argument_order_key):
        yield x


def _field(digits):
    return ComplexBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def _real(value, label):
    if not value.real().is_finite() or not value.imag().is_finite():
        raise ArithmeticError("computed a non-finite ball for %s" % (label,))
    if not value.imag().contains_zero():
        raise ArithmeticError("expected a real value for %s: %s" % (label, value))
    return value.real()


def polygamma(n, x, digits):
    field = _field(digits)
    return _real(field(x).psi(int(n)), "psi^(%s)(%s)" % (n, x))


class PolygammaRationalValues(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T250")
    parameters = ("n", "x")
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self, max_order=MAX_ORDER, max_denominator=MAX_DENOMINATOR):
        for n in range(1, max_order + 1):
            for x in _arguments(max_denominator):
                yield {"n": n, "x": str(x)}

    def value(self, params, digits):
        n = int(params["n"])
        x = QQ(params["x"])
        return polygamma(n, x, digits)


if __name__ == "__main__":
    _key_from_stdin()
    generator = PolygammaRationalValues()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="polygamma values at rational arguments",
            assisted_by=os.environ.get("NUMBERDB_ASSISTED_BY", "codex-cli"),
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
