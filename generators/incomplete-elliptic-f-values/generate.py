"""Values of the incomplete elliptic integral of the first kind F(phi, m) -- numberdb.org/T349

The table stores real principal values of

    F(phi, m) = int_0^phi dtheta / sqrt(1 - m sin(theta)^2),

with phi = t*pi and with m the elliptic parameter, not the modulus.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The range follows numberdb-data#166: twelve amplitudes from pi/24 to pi/2,
and every reduced m = a/b in [0, 1) with b <= 12. The endpoint phi = pi/2
checks against the complete integral K(m), and the row m = 0 checks against
rational multiples of pi.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.rational_field import QQ


TABLE = os.environ.get("NUMBERDB_TABLE") or "T349"
WORKING_GUARD = 64

AMPLITUDES = (
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


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _m_values(denominator=12):
    for b in range(1, denominator + 1):
        for a in range(0, denominator + 1):
            m = QQ(a) / QQ(b)
            if m >= 1 or m.denominator() != b:
                continue
            yield m


def _field(digits):
    return ComplexBallField(numberdb.bits(digits, losing=WORKING_GUARD))


class IncompleteEllipticF(numberdb.Generator):

    table = TABLE
    parameters = ("phi", "m")
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self, denominator=12):
        for phi in AMPLITUDES:
            for m in _m_values(denominator):
                yield {"phi": str(phi), "m": str(m)}

    def value(self, params, digits):
        field = _field(digits)
        phi = field.pi() * field(QQ(params["phi"]))
        m = field(QQ(params["m"]))
        value = phi.elliptic_f(m)

        if not (value.real().is_finite() and value.imag().is_finite()):
            raise ArithmeticError(
                "F(%s*pi, %s) produced a non-finite ball: %s"
                % (params["phi"], params["m"], value))
        if not value.imag().contains_zero():
            raise ArithmeticError(
                "F(%s*pi, %s) came back with a non-real imaginary part: %s"
                % (params["phi"], params["m"], value.imag()))
        return value.real()


if __name__ == "__main__":
    _key_from_stdin()
    generator = IncompleteEllipticF()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="values of incomplete elliptic F in ball arithmetic"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
