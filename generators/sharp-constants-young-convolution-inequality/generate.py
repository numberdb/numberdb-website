"""Sharp constants in Young's convolution inequality -- numberdb.org/T357

This fills T357 with the constants Y^(n)_{p,q} in the sharp Young
convolution inequality

    ||f*g||_r <= Y^(n)_{p,q} ||f||_p ||g||_q,
    1/p + 1/q = 1 + 1/r.

Only rows with p <= q are listed, since the constants are symmetric in the
two input exponents.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The computation uses the Beckner factor

    A_t = (t^(1/t) / (t')^(1/t'))^(1/2),  t' = t/(t-1),

and returns (A_p A_q / A_r)^n as a real ball.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


MAX_N = 20
MAX_DENOMINATOR = 4
WORKING_GUARD = 160


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _field(digits):
    return RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def _exponents(max_denominator=MAX_DENOMINATOR):
    values = set()
    # With denominators at most 4, the smallest exponent above 1 is 5/4.
    # The condition 1/p + 1/q > 1 then forces every listed exponent below 5.
    for denominator in range(1, max_denominator + 1):
        for numerator in range(denominator + 1, 5 * denominator):
            value = QQ(numerator) / QQ(denominator)
            if value.denominator() == denominator and value > 1:
                values.add(value)
    return sorted(values)


def young_output_exponent(p, q):
    return QQ(1) / (QQ(1) / p + QQ(1) / q - QQ(1))


def beckner_factor(field, exponent):
    exponent = QQ(exponent)
    conjugate = exponent / (exponent - 1)
    return (field(exponent) ** (field(QQ(1)) / exponent)
            / field(conjugate) ** (field(QQ(1)) / conjugate)).sqrt()


def young_constant(n, p, q, digits):
    n = ZZ(n)
    p = QQ(p)
    q = QQ(q)
    r = young_output_exponent(p, q)
    field = _field(digits)
    value = (beckner_factor(field, p)
             * beckner_factor(field, q)
             / beckner_factor(field, r)) ** n
    if not value.is_finite():
        raise ArithmeticError("computed a non-finite ball")
    return value


class SharpYoungConvolutionConstants(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T357")
    parameters = ("n", "p", "q")
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self, max_n=MAX_N, max_denominator=MAX_DENOMINATOR):
        exponents = _exponents(max_denominator)
        for n in range(1, max_n + 1):
            for p in exponents:
                for q in exponents:
                    if p > q:
                        continue
                    if QQ(1) / p + QQ(1) / q <= 1:
                        continue
                    yield {"n": str(n), "p": str(p), "q": str(q)}

    def value(self, params, digits):
        return young_constant(params["n"], params["p"], params["q"], digits)


if __name__ == "__main__":
    _key_from_stdin()
    generator = SharpYoungConvolutionConstants()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="sharp Young constants in ball arithmetic"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
