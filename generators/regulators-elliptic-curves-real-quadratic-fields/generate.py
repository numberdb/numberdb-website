"""Regulators of elliptic curves over real quadratic fields -- numberdb.org/T293.

For an elliptic curve E over K = Q(sqrt(D)), this stores the regulator of the
Mordell-Weil lattice with the absolute Neron-Tate height pairing. In the range
used here, every source curve has rank 0 or 1, so a positive-rank regulator is
the height of the recorded generator and a rank-zero regulator is exactly 1.

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
import time
from decimal import Decimal, localcontext

import numberdb.sage as numberdb
from numberdb._generate import _producer
from numberdb._write import Entries, attach, submit_entries

from curve_data import MAX_CONDUCTOR_NORM, RECORDS, SOURCE_COMMIT


TABLE = os.environ.get("NUMBERDB_TABLE", "T293")
DIGITS = 38
BSD_RELATIVE_TOLERANCE = Decimal("5e-30")

_RECORDS_BY_KEY = {
    (
        str(record["D"]),
        record["conductor"],
        record["class"],
        str(record["curve"]),
    ): record
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
    if rank == 0:
        if int(record["ngens"]) != 0 or record["regulator"] != "1":
            raise ArithmeticError(
                "%s: rank-zero row has ngens=%s and regulator=%s"
                % (record["label"], record["ngens"], record["regulator"])
            )
        return
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
    return (
        "LMFDB curve %s has conductor ideal $%s$, rank $%d$, and equation $%s$."
        % (
            record["label"],
            record["conductor_ideal"],
            int(record["rank"]),
            _equation_with_w(record),
        )
    )


class RealQuadraticEllipticRegulators(numberdb.Generator):
    """Generator for T293."""

    table = TABLE
    parameters = ("D", "conductor", "class", "curve")
    type = "R"
    digits = DIGITS
    rigour = "heuristic"
    files = ("generate.py", "curve_data.py")

    def enumerate(self):
        for record in RECORDS:
            yield {
                "D": str(record["D"]),
                "conductor": record["conductor"],
                "class": record["class"],
                "curve": str(record["curve"]),
            }

    def value(self, params, digits):
        record = _RECORDS_BY_KEY[
            (
                str(params["D"]),
                params["conductor"],
                params["class"],
                str(params["curve"]),
            )
        ]
        _check_rank_and_height(record)
        _check_bsd_quotient(record)
        value = 1 if int(record["rank"]) == 0 else record["regulator"]
        return {"number": value, "comment": _entry_comment(record)}


def _source_path(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


def fill_draft_once(generator, message):
    """Fill a fresh prose draft without the client's empty upsert probe."""
    run = "real-quadratic-elliptic-regulators-%d" % int(time.time())
    entries = Entries(*generator.parameters)
    for params in generator.enumerate():
        entries.add(**params, **generator.value(params, generator.digits))

    answer = submit_entries(
        generator.table,
        entries,
        message=message,
        produced_by=_producer(generator),
        upsert=False,
        run=run,
        rigour=generator.rigour,
    )
    for filename in generator.files:
        with open(_source_path(filename), encoding="utf8") as handle:
            attach(
                generator.table,
                filename,
                handle.read(),
                run=run,
                message=message,
                rigour=generator.rigour,
            )
    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = RealQuadraticEllipticRegulators()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            "elliptic-curve regulators over real quadratic fields from "
            "ecnf-data commit %s for conductor norm <= %d"
            % (SOURCE_COMMIT[:12], MAX_CONDUCTOR_NORM),
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
