"""Values of Kummer's confluent hypergeometric function M -- numberdb.org/TBD

The standard real values of M(a;b;z) = 1F1(a;b;z), for rational parameters.
This draft stores a half-integer grid in a and b, with z in
{1/2, -1/2, 1, -1, 2, -2, 4, -4}, excluding the elementary rows a = b.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Values are computed as complex balls with arb. In Sage's arb interface, the
hypergeometric method is called on the argument and takes the parameter lists:
`CBF(z).hypergeometric([a], [b])`.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.rational_field import QQ
from sage.rings.integer_ring import ZZ


A_VALUES = ("1/2", "-1/2", "1", "3/2", "-3/2", "2", "5/2", "-5/2", "3")
B_VALUES = ("1/2", "1", "3/2", "2", "5/2", "3")
Z_VALUES = ("1/2", "-1/2", "1", "-1", "2", "-2", "4", "-4")

# Bits of working precision beyond what the written digits need.
#
# Measured over all 384 entries: at this guard the widest result still has
# radius less than 3e-115 when the table asks for 100 digits.
WORKING_GUARD = 64


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _is_nonpositive_integer(value):
    return value in ZZ and value <= 0


def _is_elementary_row(a, b, z):
    return z == 0 or a == b or _is_nonpositive_integer(a)


def _value_ball(a_text, b_text, z_text, digits):
    a_q = QQ(a_text)
    b_q = QQ(b_text)
    z_q = QQ(z_text)
    if b_q in ZZ and b_q <= 0:
        raise ValueError("M(a;b;z) has a pole at b=%s" % (b_text,))
    if _is_elementary_row(a_q, b_q, z_q):
        raise ValueError("row omitted by the table convention")

    field = ComplexBallField(numberdb.bits(digits, losing=WORKING_GUARD))
    a = field(a_q)
    b = field(b_q)
    z = field(z_q)
    value = z.hypergeometric([a], [b])
    if not value.real().is_finite() or not value.imag().is_finite():
        raise ArithmeticError("computed a non-finite ball for M(%s;%s;%s)"
                              % (a_text, b_text, z_text))
    if not value.imag().contains_zero():
        raise ArithmeticError("expected a real value for M(%s;%s;%s)"
                              % (a_text, b_text, z_text))
    return value.real()


class KummerMValues(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE") or "TBD"
    parameters = ("a", "b", "z")
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self, a_values=A_VALUES, b_values=B_VALUES, z_values=Z_VALUES):
        for a_text in a_values:
            a = QQ(a_text)
            for b_text in b_values:
                b = QQ(b_text)
                if b in ZZ and b <= 0:
                    continue
                for z_text in z_values:
                    z = QQ(z_text)
                    if _is_elementary_row(a, b, z):
                        continue
                    yield {"a": a_text, "b": b_text, "z": z_text}

    def value(self, params, digits):
        return _value_ball(str(params["a"]), str(params["b"]),
                           str(params["z"]), digits)


if __name__ == "__main__":
    _key_from_stdin()
    generator = KummerMValues()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="Kummer confluent hypergeometric values"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
