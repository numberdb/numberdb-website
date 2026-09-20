"""Values of the incomplete elliptic integral of the second kind -- numberdb.org/T350

For each listed pair (phi, m), this stores the principal real value
E(varphi, m), where varphi = phi*pi and m is the elliptic parameter.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Values are computed as complex balls using arb's incomplete elliptic integral
of the second kind, with the imaginary part checked to contain zero.
"""

import os
import sys
from math import gcd

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.rational_field import QQ


ANGLE_MULTIPLES = (
    QQ(1) / QQ(24),
    QQ(1) / QQ(12),
    QQ(1) / QQ(8),
    QQ(1) / QQ(6),
    QQ(5) / QQ(24),
    QQ(1) / QQ(4),
    QQ(7) / QQ(24),
    QQ(1) / QQ(3),
    QQ(3) / QQ(8),
    QQ(5) / QQ(12),
    QQ(11) / QQ(24),
    QQ(1) / QQ(2),
)
MAX_M_DENOMINATOR = 12
WORKING_GUARD = 64


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _complex_field(digits):
    return ComplexBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def _m_values(max_denominator=MAX_M_DENOMINATOR):
    for denominator in range(1, max_denominator + 1):
        for numerator in range(denominator):
            if gcd(numerator, denominator) != 1:
                continue
            m = QQ(numerator) / QQ(denominator)
            if m.denominator() == denominator:
                yield m


def _real(value, label):
    if not value.real().is_finite() or not value.imag().is_finite():
        raise ArithmeticError("computed a non-finite ball for %s" % (label,))
    if not value.imag().contains_zero():
        raise ArithmeticError("imaginary part does not contain zero for "
                              "%s: %s" % (label, value.imag()))
    return value.real()


def _incomplete_e(phi_multiple, m, digits):
    field = _complex_field(digits)
    phi = field.pi() * field(phi_multiple)
    return _real(phi.elliptic_e_inc(field(m)), "E(%s*pi,%s)" % (
        phi_multiple, m))


class IncompleteEllipticEValues(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T350")
    parameters = ("phi", "m")
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self, max_m_denominator=MAX_M_DENOMINATOR):
        for phi in ANGLE_MULTIPLES:
            for m in _m_values(max_m_denominator):
                yield {"phi": str(phi), "m": str(m)}

    def value(self, params, digits):
        return _incomplete_e(QQ(params["phi"]), QQ(params["m"]), digits)


if __name__ == "__main__":
    _key_from_stdin()
    generator = IncompleteEllipticEValues()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="computed incomplete elliptic E values in ball arithmetic"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
