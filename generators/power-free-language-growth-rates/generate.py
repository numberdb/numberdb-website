"""Growth rates of the power-free languages -- numberdb.org/T447.

This generator transcribes the rounded two-sided entries with beta >= 2 from
Tables 1 and 2 of Shur's arXiv appendix, widening each printed endpoint by
half of the last printed decimal place.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import os
import sys

import numberdb.sage as numberdb
from numberdb import _compare
from numberdb._write import to_text
from sage.rings.rational_field import QQ
from sage.rings.real_mpfi import RealIntervalField


TABLE = os.environ.get("NUMBERDB_TABLE", "T447")
DIGITS = 12
DECIMAL_PLACES = 7


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _q_decimal(text):
    whole, dot, frac = text.partition(".")
    sign = -1 if whole.startswith("-") else 1
    if whole.startswith("-"):
        whole = whole[1:]
    if not dot:
        return QQ(sign * int(whole))
    return sign * QQ(int(whole + frac)) / QQ(10) ** len(frac)


ROUNDING_HALF_WIDTH = QQ(1) / (2 * QQ(10) ** DECIMAL_PLACES)


def _expanded_interval(low, high=None):
    low_q = _q_decimal(low)
    high_q = _q_decimal(high or low)
    if high is not None and low == high:
        return low_q, high_q
    return low_q - ROUNDING_HALF_WIDTH, high_q + ROUNDING_HALF_WIDTH


def _row(alphabet, exponent, low, high=None, comment=None):
    return {
        "alphabet": str(alphabet),
        "exponent": exponent,
        "size": "length",
        "labelling": "unlabelled",
        "low": low,
        "high": high,
        "bounds": _expanded_interval(low, high),
        "comment": comment,
    }


DATA = [
    _row(2, "7/3", "1.0000000", "1.0000000", r"This language has polynomial growth, so $\gamma=1$ CITE{ShurTables}."),
    _row(2, "7/3+", "1.2206318", "1.2206448"),
    _row(2, "17/7", "1.2222235", "1.2222380"),
    _row(2, "17/7+", "1.2287081", "1.2287205"),
    _row(2, "5/2", "1.2294871", "1.2295017"),
    _row(2, "5/2+", "1.3662971", "1.3663011"),
    _row(2, "18/7", "1.3669547", "1.3669601"),
    _row(2, "18/7+", "1.3692782", "1.3692832"),
    _row(2, "13/5", "1.3693912", "1.3693962"),
    _row(2, "13/5+", "1.3760821", "1.3760876"),
    _row(2, "8/3", "1.3762649", "1.3762704"),
    _row(2, "8/3+", "1.4508577", "1.4508611"),
    _row(2, "14/5", "1.4522648", "1.4522680"),
    _row(2, "14/5+", "1.4552314", "1.4552358"),
    _row(2, "17/6", "1.4552552", "1.4552596"),
    _row(2, "17/6+", "1.4567773", "1.4567815"),
    _row(2, "3", "1.4575732", "1.4575773"),
    _row(2, "3+", "1.7951246", "1.7951264"),
    _row(2, "13/4", "1.7957598", "1.7957616"),
    _row(2, "13/4+", "1.7972871", "1.7972888"),
    _row(2, "10/3", "1.7973088", "1.7973105"),
    _row(2, "10/3+", "1.8029861", "1.8029877"),
    _row(2, "7/2", "1.8032409"),
    _row(2, "7/2+", "1.8172665"),
    _row(2, "11/3", "1.8174176"),
    _row(2, "11/3+", "1.8204960"),
    _row(2, "4", "1.8211000"),
    _row(2, "4+", "1.9208015"),
    _row(2, "9/2", "1.9214442"),
    _row(2, "9/2+", "1.9241348"),
    _row(2, "5", "1.9244437"),
    _row(2, "5+", "1.9646285"),
    _row(2, "6", "1.9653118"),
    _row(2, "6+", "1.9832942"),
    _row(2, "7", "1.9834409"),
    _row(2, "7+", "1.9918972"),
    _row(2, "8", "1.9919310"),
    _row(2, "8+", "1.9960151"),
    _row(2, "9", "1.9960232"),
    _row(2, "9+", "1.9980255"),
    _row(3, "2", "1.3017597", "1.3017619"),
    _row(3, "2+", "2.6058789", "2.6058791"),
    _row(3, "3", "2.7015614", "2.7015616"),
    _row(3, "3+", "2.9119240", "2.9119242"),
    _row(3, "4", "2.9172846"),
    _row(3, "4+", "2.9737546"),
]

TABLE2_SINGLE_ROWS = {
    4: ("2.6215080", "3.7284944", "3.7789513", "3.9487867", "3.9507588", "3.9879972"),
    5: ("3.7325386", "4.7898507", "4.8220672", "4.9662411", "4.9671478", "4.9935251"),
    6: ("4.7914069", "5.8277328", "5.8503616", "5.9760100", "5.9764861", "5.9961170"),
    7: ("5.8284661", "6.8537250", "6.8705878", "6.9820558", "6.9823298", "6.9974912"),
    8: ("6.8541173", "7.8727609", "7.8858522", "7.9860649", "7.9862337", "7.9982866"),
    9: ("7.8729902", "8.8873424", "8.8978188", "8.9888625", "8.9889721", "8.9987785"),
    10: ("8.8874856", "9.8988872", "9.9074705", "9.9908932", "9.9909674", "9.9990989"),
    11: ("9.8989813", "10.9082635", "10.9154294", "10.9924142", "10.9924662", "10.9993163"),
    12: ("10.9083279", "11.9160348", "11.9221106", "11.9935831", "11.9936207", "11.9994691"),
    13: ("11.9160804", "12.9225835", "12.9278022", "12.9945010", "12.9945288", "12.9995796"),
    14: ("12.9226167", "13.9281788", "13.9327109", "13.9952350", "13.9952560", "13.9996615"),
    15: ("13.9282035", "14.9330157", "14.9369892", "14.9958311", "14.9958473", "14.9997234"),
}

for alphabet, row in TABLE2_SINGLE_ROWS.items():
    for exponent, value in zip(("2", "2+", "3", "3+", "4", "4+"), row):
        DATA.append(_row(alphabet, exponent, value))


def _field():
    return RealIntervalField(numberdb.bits(DIGITS, losing=64))


def _identity(row):
    return (row["alphabet"], row["exponent"], row["size"], row["labelling"])


def value_interval(row):
    field = _field()
    lo, hi = row["bounds"]
    return field(lo, hi)


def supported_digits(value):
    text = to_text(value, DIGITS, "ball")
    return max(1, _compare.digits_of(text))


def exponent_sort_key(exponent):
    plus = exponent.endswith("+")
    base = exponent[:-1] if plus else exponent
    if "/" in base:
        numerator, denominator = base.split("/")
        value = QQ(int(numerator)) / QQ(int(denominator))
    else:
        value = QQ(int(base))
    return value, 1 if plus else 0


def run_integrity_checks():
    identities = [_identity(row) for row in DATA]
    if len(DATA) != 118:
        raise ArithmeticError("expected 118 entries, found %d" % len(DATA))
    if len(set(identities)) != len(identities):
        raise ArithmeticError("duplicate parameter identity in source data")

    rows_by_alphabet = {}
    rows_by_exponent = {}
    for row in DATA:
        rows_by_alphabet.setdefault(row["alphabet"], []).append(row)
        rows_by_exponent.setdefault(row["exponent"], []).append(row)

    for alphabet, rows in rows_by_alphabet.items():
        ordered = sorted(rows, key=lambda row: exponent_sort_key(row["exponent"]))
        for previous, current in zip(ordered, ordered[1:]):
            if previous["bounds"][1] > current["bounds"][0]:
                raise ArithmeticError(
                    "growth should not decrease for k=%s between %s and %s"
                    % (alphabet, previous["exponent"], current["exponent"])
                )

    for exponent, rows in rows_by_exponent.items():
        ordered = sorted(rows, key=lambda row: int(row["alphabet"]))
        for previous, current in zip(ordered, ordered[1:]):
            if previous["bounds"][1] > current["bounds"][0]:
                raise ArithmeticError(
                    "growth should not decrease between k=%s and k=%s for exponent %s"
                    % (previous["alphabet"], current["alphabet"], exponent)
                )

    controls = [
        ("2", "7/3", QQ(1)),
        ("2", "3", _q_decimal("1.4575772869240")),
        ("3", "2", _q_decimal("1.301761876")),
    ]
    by_key = {(row["alphabet"], row["exponent"]): row for row in DATA}
    for alphabet, exponent, expected in controls:
        low, high = by_key[(alphabet, exponent)]["bounds"]
        if not (low <= expected <= high):
            raise ArithmeticError(
                "control value %s is not inside k=%s exponent=%s"
                % (expected, alphabet, exponent)
            )


class PowerFreeLanguageGrowthRates(numberdb.Generator):
    table = TABLE
    parameters = ("alphabet", "exponent", "size", "labelling")
    type = "R"
    digits = DIGITS
    rigour = "proven"
    format = "ball"

    def enumerate(self):
        for row in DATA:
            yield {
                "alphabet": row["alphabet"],
                "exponent": row["exponent"],
                "size": row["size"],
                "labelling": row["labelling"],
            }

    def _row_for(self, params):
        identity = (
            params["alphabet"],
            params["exponent"],
            params["size"],
            params["labelling"],
        )
        for row in DATA:
            if _identity(row) == identity:
                return row
        raise KeyError(identity)

    def value(self, params, digits):
        row = self._row_for(params)
        value = value_interval(row)
        entry = {"number": value, "digits": supported_digits(value)}
        if row["comment"]:
            entry["comment"] = row["comment"]
        return entry


def fill_draft_once(generator, message):
    """Fill a fresh draft without the client's empty upsert probe."""
    from numberdb._generate import (
        _check_precision,
        _check_rigour,
        _producer,
        _run_name,
        _source_files,
        _written,
    )
    from numberdb._write import Entries, attach, submit_entries

    table = generator.table
    run = _run_name(generator)
    entries = Entries(*generator.parameters)

    for params in generator.enumerate():
        params = dict(params)
        asked = generator.digits_for(params)
        entry = generator._entry(params, asked)
        wanted = int(entry.pop("digits", asked) or asked)
        value = entry["number"]
        identity = ",".join(str(params[name]) for name in generator.parameters)
        _check_rigour(generator, table, identity, value)
        written = _written(value, wanted, generator.format)
        text = written[0] if isinstance(written, list) else written
        _check_precision(table, identity, text, wanted, lowering=False)
        entry["number"] = written
        entries.add(**params, **entry, digits=wanted)

    answer = submit_entries(
        table,
        entries,
        message=message,
        produced_by=_producer(generator, os.environ.get("NUMBERDB_ASSISTED_BY", "")),
        upsert=False,
        run=run,
        rigour=generator.rigour,
    )

    for name, body in sorted(_source_files(generator).items()):
        attach(table, name, body, run=run, message=message, rigour=generator.rigour)

    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = PowerFreeLanguageGrowthRates()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="growth rates of power-free languages from Shur's rounded tables",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
