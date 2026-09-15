"""Bendersky constants -- numberdb.org/T227

For each listed integer k, this fills T227 with the Bendersky constant A_k
and its logarithm, in that order. The classical k = 1 member is held in
numberdb.org/T249 under the name Glaisher-Kinkelin constant A, so this
generator skips k = 1.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The values are computed from

    log A_k = B_{k+1} H_k / (k + 1) - zeta'(-k),

where H_0 = 0. The computation uses arb's derivative of the Riemann zeta
function in complex ball arithmetic and returns real balls only after checking
that the imaginary parts contain zero.
"""

import os
import sys

import numberdb.sage as numberdb
from numberdb._write import to_text
from sage.arith.misc import bernoulli
from sage.rings.complex_arb import ComplexBallField
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ


MAX_K = 20
WORKING_GUARD = 96


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


def _comment(k):
    if k == 0:
        return "$A_0=\\sqrt{2\\pi}$. $\\log A_0=\\frac12\\log(2\\pi)$."
    return ""


class BenderskyConstants(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T227")
    parameters = ("k",)
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self, maximum=MAX_K):
        for k in range(0, maximum + 1):
            if k == 1:
                continue
            yield {"k": str(k)}

    def value(self, params, digits):
        k = ZZ(params["k"])
        entry = {
            "number": [
                bendersky_constant(k, digits),
                log_bendersky_constant(k, digits),
            ]
        }
        comment = _comment(int(k))
        if comment:
            entry["comment"] = comment
        return entry


def verify_all_list_values(generator):
    """Check both stored values in each row, not only the first one."""
    document = numberdb.table(generator.table)
    stored = document["Numbers"]
    ok = True
    for params in generator.enumerate():
        entry = generator.value(params, generator.digits)
        expected = [to_text(value, generator.digits)
                    for value in entry["number"]]
        got = stored[str(params["k"])]["number"]
        if expected != got:
            print("disagreement at k=%s" % (params["k"],))
            print("stored:   %r" % (got,))
            print("computed: %r" % (expected,))
            ok = False
    return ok


if __name__ == "__main__":
    _key_from_stdin()
    generator = BenderskyConstants()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="Bendersky constants"))
    else:
        all_values_ok = verify_all_list_values(generator)
        print("all stored list values match:", all_values_ok)
        sys.exit(0 if all_values_ok else 1)
