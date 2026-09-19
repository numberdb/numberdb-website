"""Regulators of elliptic curves over real quadratic fields -- numberdb.org/T293.

For an elliptic curve E over K = Q(sqrt(D)), this stores the regulator of the
Mordell-Weil lattice with the absolute Neron-Tate height pairing. The table
lists positive-rank curves; in the range used here, every source curve has
rank 1, so the regulator is the height of the recorded generator.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The curve list and regulator values are from John Cremona's ecnf-data
repository, pinned in curve_data.py. Each row is checked against the source
height column and against the Birch-Swinnerton-Dyer quotient using ecnf-data's
Lvalue, Omega, torsion, finite Tamagawa product and Sha.
"""

import os
import sys
from decimal import Decimal, ROUND_DOWN, localcontext

import numberdb.sage as numberdb

from curve_data import MAX_CONDUCTOR_NORM, RECORDS, SOURCE_COMMIT


TABLE = os.environ.get("NUMBERDB_TABLE", "T293")
DIGITS = 35
BSD_RELATIVE_TOLERANCE = Decimal("5e-30")

_RECORDS_BY_KEY = {
    (str(record["D"]), "%s-%s%s" % (
        record["conductor"],
        record["class"],
        record["curve"],
    )): record
    for record in RECORDS
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _decimal(text):
    return Decimal(str(text).strip())


def _relative_error(got, expected):
    got = _decimal(got)
    expected = _decimal(expected)
    scale = max(abs(expected), Decimal(1))
    return abs(got - expected) / scale


def _require_close(label, got, expected, tolerance):
    error = _relative_error(got, expected)
    if error > tolerance:
        raise ArithmeticError(
            "%s: relative error %s is larger than %s; got %s, expected %s"
            % (label, error, tolerance, got, expected)
        )


def _truncate_significant(text, digits):
    value = _decimal(text)
    if not value:
        return "0"
    exponent = value.adjusted()
    quantum = Decimal(1).scaleb(exponent - digits + 1)
    with localcontext() as context:
        context.prec = max(80, digits + abs(exponent) + 10)
        truncated = value.quantize(quantum, rounding=ROUND_DOWN)
    if -7 < exponent < digits:
        return format(truncated, "f")
    mantissa, _, power = format(truncated, "e").partition("e")
    return "%se%d" % (mantissa, int(power))


def _rank_one_height(record):
    heights = record["heights"]
    if not (heights.startswith("[") and heights.endswith("]")):
        raise ArithmeticError("%s: malformed height list %s"
                              % (record["label"], heights))
    pieces = [part for part in heights[1:-1].split(",") if part]
    if len(pieces) != 1:
        raise ArithmeticError("%s: expected one generator height, got %s"
                              % (record["label"], heights))
    return pieces[0]


def _check_rank_and_height(record):
    rank = int(record["rank"])
    if rank != 1:
        raise ArithmeticError("%s: rank %s is outside this generator's check"
                              % (record["label"], rank))
    if int(record["ngens"]) != 1:
        raise ArithmeticError("%s: rank-one row has ngens=%s"
                              % (record["label"], record["ngens"]))
    _require_close(
        "%s regulator against generator height" % record["label"],
        record["regulator"],
        _rank_one_height(record),
        Decimal("1e-37"),
    )


def _check_bsd_quotient(record):
    with localcontext() as context:
        context.prec = 90
        numerator = (
            _decimal(record["lvalue"])
            * Decimal(int(record["torsion_order"]) ** 2)
            * Decimal(int(record["D"])).sqrt()
        )
        denominator = (
            (Decimal(2) ** int(record["rank"]))
            * _decimal(record["omega"])
            * _decimal(record["regulator"])
            * Decimal(int(record["tamagawa_product"]))
        )
        quotient = numerator / denominator

    _require_close(
        "%s BSD quotient" % record["label"],
        quotient,
        Decimal(int(record["sha"])),
        BSD_RELATIVE_TOLERANCE,
    )


def _equation_with_w(record):
    equation = record["equation"].replace("\\phi", "w")
    if record["D"] != 5:
        equation = equation.replace("a", "w")
    return equation


def _entry_comment(record):
    conductor_ideal = record["conductor_ideal"].replace("*w", "w")
    return (
        "LMFDB curve %s has conductor ideal $%s$, rank $%d$, and equation $%s$."
        % (
            record["label"],
            conductor_ideal,
            int(record["rank"]),
            _equation_with_w(record),
        )
    )


class RealQuadraticEllipticRegulators(numberdb.Generator):
    """Generator for T293."""

    table = TABLE
    parameters = ("D", "label")
    type = "R"
    digits = DIGITS
    rigour = "heuristic"
    files = ("generate.py", "curve_data.py")

    def enumerate(self):
        for record in RECORDS:
            yield {
                "D": str(record["D"]),
                "label": "%s-%s%s" % (
                    record["conductor"],
                    record["class"],
                    record["curve"],
                ),
            }

    def value(self, params, digits):
        record = _RECORDS_BY_KEY[(str(params["D"]), params["label"])]
        _check_rank_and_height(record)
        _check_bsd_quotient(record)
        return {
            "number": _truncate_significant(record["regulator"], digits),
            "comment": _entry_comment(record),
        }


if __name__ == "__main__":
    _key_from_stdin()
    generator = RealQuadraticEllipticRegulators()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message=(
                "elliptic-curve regulators over real quadratic fields from "
                "ecnf-data commit %s for conductor norm <= %d"
                % (SOURCE_COMMIT[:12], MAX_CONDUCTOR_NORM)
            ),
            overwrite=False,
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
