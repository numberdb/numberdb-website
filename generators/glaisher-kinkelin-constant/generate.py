"""Glaisher-Kinkelin constant -- numberdb.org/T249

This fills T249 with the classical Glaisher-Kinkelin constant A and its
logarithmic convention log A. The same number is the k = 1 member A_1 of the
Bendersky family in numberdb.org/T227.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The values are computed from

    log A = 1/12 - zeta'(-1).

The computation uses arb's derivative of the Riemann zeta function in complex
ball arithmetic and returns a real ball only after checking that the imaginary
part contains zero.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import bernoulli
from sage.rings.complex_arb import ComplexBallField
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ


WORKING_GUARD = 96
QUANTITIES = ("A", "logA")


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _field(digits):
    return ComplexBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def _harmonic_number(k):
    total = QQ(0)
    for j in range(1, int(k) + 1):
        total += QQ(1) / QQ(j)
    return total


def _real(value, label):
    if not value.real().is_finite() or not value.imag().is_finite():
        raise ArithmeticError("computed a non-finite ball for %s" % (label,))
    if not value.imag().contains_zero():
        raise ArithmeticError("expected a real value for %s" % (label,))
    return value.real()


def log_glaisher_constant(digits):
    k = ZZ(1)
    field = _field(digits)
    harmonic = _harmonic_number(k)
    rational_part = QQ(bernoulli(k + 1)) * harmonic / QQ(k + 1)
    value = field(rational_part) - field(-k).zetaderiv(1)
    return _real(value, "log A")


def glaisher_constant(digits):
    return log_glaisher_constant(digits).exp()


class GlaisherKinkelinConstant(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T249")
    parameters = ("quantity",)
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self):
        for quantity in QUANTITIES:
            yield {"quantity": quantity}

    def value(self, params, digits):
        quantity = str(params["quantity"])
        if quantity == "A":
            return {
                "number": glaisher_constant(digits),
                "comment": "The classical Glaisher-Kinkelin constant.",
            }
        if quantity == "logA":
            return {
                "number": log_glaisher_constant(digits),
                "comment": "$\\log A_1=\\frac1{12}-\\zeta'(-1)$.",
            }
        raise ValueError("unknown quantity %r" % (quantity,))


if __name__ == "__main__":
    _key_from_stdin()
    generator = GlaisherKinkelinConstant()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="Glaisher-Kinkelin constant"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
