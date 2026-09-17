"""Special L-values of elliptic curves over real quadratic fields -- numberdb.org/T292.

For an elliptic curve E over K = Q(sqrt(D)), this stores the leading Taylor
coefficient L^(r)(E/K, 1) / r!, where r is the Mordell-Weil rank over K.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The curve list and the outside 38-digit values are the real-quadratic files
from John Cremona's ecnf-data repository, pinned in curve_data.py. The values
stored by the table are recomputed with PARI's L-function machinery at two
working precisions. Each row is checked against ecnf-data's Lvalue, against the
BSD quotient using ecnf-data's Omega, regulator, torsion, finite Tamagawa
product and Sha, and, for source rows marked as base changes, against the
product of the two rational-curve L-values computed from Sage's Cremona
database.
"""

import math
import os
import re
import sys
import time
from decimal import Decimal, localcontext

import numberdb.sage as numberdb
from numberdb._generate import _producer
from numberdb._write import Entries, attach, submit_entries
from sage.databases.cremona import CremonaDatabase, lmfdb_to_cremona
from sage.libs.pari import pari

from curve_data import MAX_CONDUCTOR_NORM, RECORDS, SOURCE_COMMIT


TABLE = os.environ.get("NUMBERDB_TABLE", "T292")

# Decimal working precisions for the agreement check. The larger precision is
# also used for the source, BSD and base-change checks.
WORKING_DIGITS = (110, 130)
PARI_GUARD_BITS = 96

# The source values carry 38 significant digits. The tolerance is deliberately
# a little wider than one unit in the last source place, because PARI and the
# source are independent numerical computations and this check is a guard, not
# the stored error bound.
SOURCE_RELATIVE_TOLERANCE = Decimal("2e-36")

BSD_RELATIVE_TOLERANCE = Decimal("5e-30")
BASE_CHANGE_RELATIVE_TOLERANCE = Decimal("5e-30")

_FIELDS = {}
_RECORDS_BY_KEY = {
    (str(record["D"]), record["conductor"], record["class"]): record
    for record in RECORDS
}
_CREMONA = None
_Q_CURVES = {}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _field(polynomial):
    field = _FIELDS.get(polynomial)
    if field is None:
        field = pari("nfinit(%s)" % polynomial)
        _FIELDS[polynomial] = field
    return field


def _nf_element(text, polynomial):
    terms = []
    for power, coefficient in enumerate(text.split(",")):
        if coefficient == "0":
            continue
        if power == 0:
            terms.append("(%s)" % coefficient)
        elif power == 1:
            terms.append("(%s)*y" % coefficient)
        else:
            terms.append("(%s)*y^%d" % (coefficient, power))
    body = "+".join(terms) if terms else "0"
    return pari("Mod(%s,%s)" % (body, polynomial))


def _curve(record):
    polynomial = record["polynomial"]
    coefficients = [
        _nf_element(part, polynomial)
        for part in record["ainvs"].split(";")
    ]
    return pari.ellinit(coefficients, _field(polynomial))


def _pari_lvalue_text(record, working_digits):
    bits = numberdb.bits(working_digits, losing=PARI_GUARD_BITS)
    pari.default("realbitprecision", bits)
    pari.default("realprecision", working_digits + 20)
    value = pari.lfun(pari.lfuncreate(_curve(record)), 1,
                      int(record["rank"]), bits)
    rank = int(record["rank"])
    if rank > 1:
        value = value / pari(math.factorial(rank))
    return str(value)


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


def _check_source_value(record, computed):
    _require_close(
        "%s against ecnf-data Lvalue" % record["class_label"],
        computed,
        record["lvalue"],
        SOURCE_RELATIVE_TOLERANCE,
    )


def _check_bsd_quotient(record, computed):
    sha = int(record["sha"])
    root = math.isqrt(sha)
    if root * root != sha:
        raise ArithmeticError(
            "%s: ecnf-data Sha value %d is not a square"
            % (record["class_label"], sha)
        )

    with localcontext() as context:
        context.prec = 90
        numerator = (
            _decimal(computed)
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
        "%s BSD quotient" % record["class_label"],
        quotient,
        Decimal(sha),
        BSD_RELATIVE_TOLERANCE,
    )


def _cremona_database():
    global _CREMONA
    if _CREMONA is None:
        _CREMONA = CremonaDatabase()
    return _CREMONA


def _q_curve(label):
    """Return (a-invariants, rank) for a label like 175.b1."""
    cached = _Q_CURVES.get(label)
    if cached is not None:
        return cached

    cremona_label = lmfdb_to_cremona(label, _cremona_database())
    found = re.fullmatch(r"([0-9]+)([a-z]+[0-9]+)", cremona_label)
    if found is None:
        raise ValueError(
            "could not convert ecnf-data LMFDB label %s to a Cremona label"
            % label
        )
    conductor, key = found.groups()
    data = _cremona_database().allcurves(int(conductor))[key]
    cached = ([int(value) for value in data[0]], int(data[1]))
    _Q_CURVES[label] = cached
    return cached


def _q_lvalue_decimal(label, working_digits):
    ainvs, rank = _q_curve(label)
    bits = numberdb.bits(working_digits, losing=PARI_GUARD_BITS)
    pari.default("realbitprecision", bits)
    pari.default("realprecision", working_digits + 20)
    value = pari.lfun(pari.lfuncreate(pari.ellinit(ainvs)), 1, rank, bits)
    if rank > 1:
        value = value / pari(math.factorial(rank))
    return _decimal(str(value)), rank


def _check_base_change(record, computed):
    labels = record["base_change"]
    if not labels:
        return
    if len(labels) != 2:
        raise ArithmeticError(
            "%s: expected two base-change labels, got %r"
            % (record["class_label"], labels)
        )
    with localcontext() as context:
        context.prec = 90
        product = Decimal(1)
        rank = 0
        for label in labels:
            value, curve_rank = _q_lvalue_decimal(label, max(WORKING_DIGITS))
            product *= value
            rank += curve_rank
    if rank != int(record["rank"]):
        raise ArithmeticError(
            "%s: base-change ranks add to %d, not %d"
            % (record["class_label"], rank, int(record["rank"]))
        )
    _require_close(
        "%s base-change product" % record["class_label"],
        computed,
        product,
        BASE_CHANGE_RELATIVE_TOLERANCE,
    )


def _clean_equation(record):
    equation = record["equation"]
    equation = equation.replace(r"\phi", "w")
    if int(record["D"]) != 5:
        equation = re.sub(r"(?<![A-Za-z\\])a(?=\\{|[^A-Za-z]|$)", "w", equation)
    equation = equation.replace("{x}", "x").replace("{y}", "y")
    return equation


def _lmfdb_url(record):
    return "https://www.lmfdb.org/EllipticCurve/%s/%s/%s/%d" % (
        record["field_label"],
        record["conductor"],
        record["class"],
        int(record["curve"]),
    )


def _entry_comment(record):
    return (
        "Representative curve HREF{%s}[LMFDB %s], conductor ideal $%s$, "
        "rank $%d$: $%s$."
        % (
            _lmfdb_url(record),
            record["label"],
            record["conductor_ideal"],
            int(record["rank"]),
            _clean_equation(record),
        )
    )


class RealQuadraticEllipticLValues(numberdb.Generator):
    """Generator for T292."""

    table = TABLE
    parameters = ("D", "conductor", "class")
    type = "R"
    digits = 100
    rigour = "heuristic (agreement-checked)"
    files = ("generate.py", "curve_data.py")

    def enumerate(self):
        for record in RECORDS:
            yield {
                "D": str(record["D"]),
                "conductor": record["conductor"],
                "class": record["class"],
            }

    def value(self, params, digits):
        record = _RECORDS_BY_KEY[
            (str(params["D"]), params["conductor"], params["class"])
        ]
        texts = {
            working: _pari_lvalue_text(record, working)
            for working in WORKING_DIGITS
        }
        computed = texts[max(WORKING_DIGITS)]
        _check_source_value(record, computed)
        _check_bsd_quotient(record, computed)
        _check_base_change(record, computed)
        return {
            "number": numberdb.agreeing(lambda working: texts[working],
                                        at=WORKING_DIGITS),
            "comment": _entry_comment(record),
        }


def _source_path(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


def fill_draft_once(generator, message):
    """Fill a fresh prose draft without the client's empty upsert probe."""
    run = "real-quadratic-elliptic-lvalues-%d" % int(time.time())
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
    generator = RealQuadraticEllipticLValues()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            "special L-values over real quadratic fields from PARI, checked "
            "against ecnf-data commit %s for conductor norm <= %d"
            % (SOURCE_COMMIT[:12], MAX_CONDUCTOR_NORM),
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
