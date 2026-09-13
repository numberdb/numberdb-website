"""Glaisher-Kinkelin constant and Bendersky constants -- numberdb.org/T227

For each integer 0 <= k <= 20, this stores the generalized Glaisher or
Bendersky constant A_k and its logarithm.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The values are computed from

    log A_k = B_{k+1} H_k / (k + 1) - zeta'(-k),

where H_0 = 0. The computation uses arb's derivative of the Riemann zeta
function in complex ball arithmetic and returns a real ball only after checking
that the imaginary part contains zero.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import bernoulli
from sage.rings.complex_arb import ComplexBallField
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ


MAX_K = 20
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


def log_bendersky_constant(k, digits):
    k = ZZ(k)
    field = _field(digits)
    harmonic = _harmonic_number(k)
    rational_part = QQ(bernoulli(k + 1)) * harmonic / QQ(k + 1)
    value = field(rational_part) - field(-k).zetaderiv(1)
    return _real(value, "log A_%s" % (k,))


def bendersky_constant(k, digits):
    return log_bendersky_constant(k, digits).exp()


def _comment(k, quantity):
    if quantity == "A" and k == 0:
        return "$A_0=\\sqrt{2\\pi}$."
    if quantity == "logA" and k == 0:
        return "$\\log A_0=\\frac12\\log(2\\pi)$."
    if quantity == "A" and k == 1:
        return "The classical Glaisher-Kinkelin constant."
    if quantity == "logA" and k == 1:
        return "$\\log A_1=\\frac1{12}-\\zeta'(-1)$."
    return ""


class GlaisherBenderskyConstants(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T227")
    parameters = ("k", "quantity")
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self, maximum=MAX_K):
        for k in range(0, maximum + 1):
            for quantity in QUANTITIES:
                yield {"k": str(k), "quantity": quantity}

    def value(self, params, digits):
        k = ZZ(params["k"])
        quantity = str(params["quantity"])
        if quantity == "A":
            number = bendersky_constant(k, digits)
        elif quantity == "logA":
            number = log_bendersky_constant(k, digits)
        else:
            raise ValueError("unknown quantity %r" % (quantity,))

        comment = _comment(int(k), quantity)
        if comment:
            return {"number": number, "comment": comment}
        return number


if __name__ == "__main__":
    _key_from_stdin()
    generator = GlaisherBenderskyConstants()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="Glaisher-Bendersky constants"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
