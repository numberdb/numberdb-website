"""Values of the derivative of the Riemann zeta function -- numberdb.org/T228

For each rational s = a/b in lowest terms with b <= 4 and -20 <= s <= 20,
this stores zeta'(s) where s != 1, and zeta'(s)/zeta(s) where s is neither
the pole at 1 nor a zero of zeta. In this real range the excluded zeros are
the negative even integers.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Values are computed as complex balls using arb's zeta derivative. The
logarithmic derivative is stored with its own sign, not negated.
"""

import os
import sys
from math import gcd

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.rational_field import QQ


MAX_DENOMINATOR = 4
MIN_ARGUMENT = QQ(-20)
MAX_ARGUMENT = QQ(20)
WORKING_GUARD = 96

QUANTITY_DERIVATIVE = "derivative"
QUANTITY_LOG_DERIVATIVE = "logderivative"


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _argument_order_key(s):
    return (s.denominator(), abs(s), s < 0)


def _arguments(max_denominator=MAX_DENOMINATOR):
    found = []
    for denominator in range(1, max_denominator + 1):
        for numerator in range(
            int(MIN_ARGUMENT * denominator),
            int(MAX_ARGUMENT * denominator) + 1,
        ):
            if gcd(numerator, denominator) != 1:
                continue
            s = QQ(numerator) / QQ(denominator)
            if s.denominator() != denominator:
                continue
            if MIN_ARGUMENT <= s <= MAX_ARGUMENT:
                found.append(s)
    for s in sorted(found, key=_argument_order_key):
        yield s


def _field(digits):
    return ComplexBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def _is_negative_even_integer(s):
    return s.denominator() == 1 and s < 0 and int(s) % 2 == 0


def _finite_real(value, label):
    if not value.real().is_finite() or not value.imag().is_finite():
        raise ArithmeticError("computed a non-finite ball for %s" % (label,))
    if not value.imag().contains_zero():
        raise ArithmeticError("expected a real value for %s" % (label,))
    return value.real()


def zeta_derivative(s, digits):
    field = _field(digits)
    value = field(s).zetaderiv(1)
    return _finite_real(value, "zeta'(%s)" % (s,))


def zeta_log_derivative(s, digits):
    field = _field(digits)
    point = field(s)
    value = point.zetaderiv(1) / point.zeta()
    return _finite_real(value, "zeta'(%s)/zeta(%s)" % (s, s))


def _comment(s, quantity):
    text = str(s)
    if quantity == QUANTITY_DERIVATIVE:
        if text == "0":
            return "$-\\frac12\\log(2\\pi)$."
        if text == "-2":
            return "$-\\zeta(3)/(4\\pi^2)$."
        if text == "-4":
            return "$3\\zeta(5)/(4\\pi^4)$."
    if quantity == QUANTITY_LOG_DERIVATIVE:
        if text == "2":
            return "The negative of this value is $\\sum_{n\\geq1}\\Lambda(n)/n^2$."
        if text == "0":
            return "$\\log(2\\pi)$."
    return ""


class RiemannZetaDerivativeRationalValues(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T228")
    parameters = ("s", "quantity")
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self, max_denominator=MAX_DENOMINATOR):
        for s in _arguments(max_denominator):
            if s == 1:
                continue
            yield {"s": str(s), "quantity": QUANTITY_DERIVATIVE}
            if not _is_negative_even_integer(s):
                yield {"s": str(s), "quantity": QUANTITY_LOG_DERIVATIVE}

    def value(self, params, digits):
        s = QQ(params["s"])
        quantity = str(params["quantity"])
        if quantity == QUANTITY_DERIVATIVE:
            number = zeta_derivative(s, digits)
        elif quantity == QUANTITY_LOG_DERIVATIVE:
            number = zeta_log_derivative(s, digits)
        else:
            raise ValueError("unknown quantity %r" % (quantity,))

        comment = _comment(s, quantity)
        if comment:
            return {"number": number, "comment": comment}
        return number


if __name__ == "__main__":
    _key_from_stdin()
    generator = RiemannZetaDerivativeRationalValues()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="zeta derivative values at rational arguments",
            assisted_by=os.environ.get("NUMBERDB_ASSISTED_BY", "codex-cli"),
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
