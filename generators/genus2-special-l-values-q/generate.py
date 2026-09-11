"""Special L-values of genus 2 curves over Q -- numberdb.org/T212.

For the Jacobian A of a genus 2 curve over Q, this stores the leading Taylor
coefficient L^{(r)}(A, 1)/r!, where r is the analytic rank.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The curve equations and analytic ranks are read from the LMFDB genus 2 curve
database.  The values are computed with PARI's lfungenus2 and lfun at two
working precisions; the LMFDB leading coefficients are kept in curve_data.py
only for independent checks.
"""

import ast
import math
import os
import sys

import numberdb.sage as numberdb
from sage.libs.pari import pari
from sage.rings.integer_ring import ZZ

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curve_data import CLASS_DATA  # noqa: E402

MAX_CONDUCTOR = 1000
WORKING_DIGITS = (60, 80)
PARI_GUARD_BITS = 64
CHECK_BITS = numberdb.bits(max(WORKING_DIGITS), losing=PARI_GUARD_BITS)

_BY_IDENTITY = {
    (record["label"], ZZ(record["rank"])): record for record in CLASS_DATA
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _poly(coefficients):
    x = pari("x")
    return sum(pari(coefficient) * x ** power
               for power, coefficient in enumerate(coefficients))


def _lfunction(record, bits):
    pari.default("realbitprecision", bits)
    f_coefficients, h_coefficients = ast.literal_eval(record["equation"])
    return pari.lfungenus2([_poly(f_coefficients), _poly(h_coefficients)])


def _pari_lvalue_text(record, working_digits):
    bits = numberdb.bits(working_digits, losing=PARI_GUARD_BITS)
    rank = int(record["rank"])
    value = pari.lfun(_lfunction(record, bits), 1, rank, bits)
    if rank > 1:
        value = pari("(%s) / %d" % (value, math.factorial(rank)))
    return str(value)


def computed_rank(record):
    return ZZ(pari.lfunorderzero(_lfunction(record, CHECK_BITS), 1))


def functional_equation_check(record):
    return ZZ(pari.lfuncheckfeq(_lfunction(record, CHECK_BITS),
                                None, CHECK_BITS))


def _lmfdb_curve_url(label):
    conductor, family, discriminant, curve = label.split(".")
    return ("https://www.lmfdb.org/Genus2Curve/Q/%s/%s/%s/%s"
            % (conductor, family, discriminant, curve))


def _term(coefficient, power):
    coefficient = int(coefficient)
    if power == 0:
        body = str(abs(coefficient))
    elif power == 1:
        body = "x" if abs(coefficient) == 1 else "%d x" % abs(coefficient)
    else:
        body = ("x^%d" % power if abs(coefficient) == 1
                else "%d x^%d" % (abs(coefficient), power))
    return "-" if coefficient < 0 else "+", body


def _polynomial_text(coefficients):
    terms = [
        _term(coefficient, power)
        for power, coefficient in reversed(list(enumerate(coefficients)))
        if coefficient
    ]
    if not terms:
        return "0"

    first_sign, first_body = terms[0]
    pieces = [("-" if first_sign == "-" else "") + first_body]
    for sign, body in terms[1:]:
        pieces.append(" %s %s" % (sign, body))
    return "".join(pieces)


def _nonzero_terms(coefficients):
    return [(int(coefficient), power)
            for power, coefficient in enumerate(coefficients)
            if coefficient]


def _times_y_text(coefficient, power):
    coefficient = abs(int(coefficient))
    if power == 0:
        return "y" if coefficient == 1 else "%d y" % coefficient
    if power == 1:
        return "xy" if coefficient == 1 else "%d xy" % coefficient
    body = "x^%d y" % power
    return body if coefficient == 1 else "%d %s" % (coefficient, body)


def equation_text(record):
    f_coefficients, h_coefficients = ast.literal_eval(record["equation"])
    left = "y^2"
    h_terms = _nonzero_terms(h_coefficients)
    if len(h_terms) == 1:
        coefficient, power = h_terms[0]
        sign = " - " if coefficient < 0 else " + "
        left += sign + _times_y_text(coefficient, power)
    elif h_terms:
        h_text = _polynomial_text(h_coefficients)
        left += " + (%s)y" % h_text
    return "%s = %s" % (left, _polynomial_text(f_coefficients))


def entry_comment(record):
    sentence = (
        "Representative curve HREF{%s}[LMFDB %s], $%s$."
        % (_lmfdb_curve_url(record["curve_label"]),
           record["curve_label"],
           equation_text(record))
    )
    return sentence


class Genus2SpecialLValues(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T212")
    parameters = ("label", "rank")
    type = "R"
    digits = 40
    rigour = "heuristic (agreement-checked)"
    files = ("generate.py", "curve_data.py")

    def enumerate(self, max_conductor=MAX_CONDUCTOR):
        for record in CLASS_DATA:
            if record["conductor"] <= max_conductor:
                yield {"label": record["label"], "rank": ZZ(record["rank"])}

    def value(self, params, digits):
        key = (params["label"], ZZ(params["rank"]))
        record = _BY_IDENTITY[key]
        return {
            "number": numberdb.agreeing(
                lambda working: _pari_lvalue_text(record, working),
                at=WORKING_DIGITS),
            "comment": entry_comment(record),
        }


if __name__ == "__main__":
    _key_from_stdin()
    generator = Genus2SpecialLValues()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message=("genus 2 special L-values for odd conductor <= %d, "
                     "computed with PARI at two precisions")
                    % (MAX_CONDUCTOR,)))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
