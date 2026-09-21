"""Zeros of the Dedekind zeta functions of cubic fields -- numberdb.org/T385.

For each cubic field K with |D_K| <= 500, this stores the first ten positive
ordinates t_n for zeros zeta_K(1/2 + i*t_n) = 0 on the critical line.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

Under this repository's build wrapper:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
        agents/sage.sh generators/dedekind-zeta-zeros-cubic-fields/generate.py
"""

from decimal import Decimal
import os
import sys

import numberdb.sage as numberdb
from sage.libs.pari import pari


BOUND = 500
EXPECTED_FIELDS = 70
EXPECTED_NEGATIVE = 58
EXPECTED_POSITIVE = 12
ZEROS_PER_FIELD = 10
SEARCH_HEIGHT = 60
ZERO_MESH = 16
DIGITS = 30
WORKING_DIGITS = (80, 120)
CHECK_DIGITS = 80
GROUPS = ("C3", "S3")

T4_MATCHES = {
    (49, 1): {
        1: "HREF{Zeros_of_Dirichlet_L_functions#7,2,1}[the T4 row $(7,2,1)$]",
        2: "HREF{Zeros_of_Dirichlet_L_functions#7,4,1}[the T4 row $(7,4,1)$]",
        3: "HREF{Zeros_of_Dirichlet_L_functions#7,4,2}[the T4 row $(7,4,2)$]",
        4: "HREF{Zeros_of_Dirichlet_L_functions#7,2,2}[the T4 row $(7,2,2)$]",
        5: "HREF{Zeros_of_Dirichlet_L_functions#7,2,3}[the T4 row $(7,2,3)$]",
        6: "HREF{Zeros_of_Dirichlet_L_functions#7,4,3}[the T4 row $(7,4,3)$]",
    },
}

_FIELDS = None
_BY_IDENTITY = None
_DATA = {}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def _pari_poly(poly):
    return str(poly)


def _pari_decimal(value):
    return Decimal(str(value).replace(" ", ""))


def _field_discriminant(poly):
    return int(pari("nfdisc(%s)" % _pari_poly(poly)))


def _coeff_key(poly):
    degree = int(pari("poldegree(%s)" % _pari_poly(poly)))
    return tuple(
        int(pari("polcoef(%s,%d)" % (_pari_poly(poly), exponent)))
        for exponent in range(degree - 1, -1, -1)
    )


def _field_label(field):
    r1 = 3 if field["D"] > 0 else 1
    return "3.%d.%d.%d" % (r1, abs(field["D"]), field["k"])


def _fields(bound=BOUND):
    global _FIELDS, _BY_IDENTITY
    if _FIELDS is not None:
        return _FIELDS

    found = {}
    for group in GROUPS:
        for raw in pari('nflist("%s", [1, %d])' % (group, bound)):
            reduced = pari("polredabs(%s)" % _pari_poly(raw))
            discriminant = _field_discriminant(reduced)
            if abs(discriminant) > bound:
                continue
            key = str(reduced)
            if key in found and found[key]["group"] != group:
                raise ArithmeticError("%s was returned for two Galois groups" % reduced)
            found[key] = {
                "poly": reduced,
                "D": discriminant,
                "group": group,
            }

    grouped = {}
    for field in found.values():
        grouped.setdefault(field["D"], []).append(field)

    rows = []
    for discriminant in sorted(grouped, key=lambda d: (abs(d), d < 0)):
        fields = sorted(grouped[discriminant], key=lambda field: _coeff_key(field["poly"]))
        for index, field in enumerate(fields, 1):
            row = dict(field)
            row["k"] = index
            row["lmfdb_label"] = _field_label(row)
            rows.append(row)

    negative = sum(1 for row in rows if row["D"] < 0)
    positive = sum(1 for row in rows if row["D"] > 0)
    if (len(rows), negative, positive) != (
        EXPECTED_FIELDS,
        EXPECTED_NEGATIVE,
        EXPECTED_POSITIVE,
    ):
        raise ArithmeticError(
            "expected %d fields, %d negative and %d positive; found %d, %d, %d"
            % (
                EXPECTED_FIELDS,
                EXPECTED_NEGATIVE,
                EXPECTED_POSITIVE,
                len(rows),
                negative,
                positive,
            )
        )

    _FIELDS = tuple(rows)
    _BY_IDENTITY = {(row["D"], row["k"]): row for row in rows}
    return _FIELDS


def _field_by_identity(D, k):
    if _BY_IDENTITY is None:
        _fields()
    field = _BY_IDENTITY.get((int(D), int(k)))
    if field is None:
        raise KeyError("no cubic field at D=%s, k=%s" % (D, k))
    return field


def _zeros_for_field(field, working_digits):
    pari("default(realprecision,%d)" % int(working_digits))
    ldata = pari("lfuncreate(bnfinit(%s,1))" % _pari_poly(field["poly"]))
    zeros = pari("lfunzeros")(ldata, SEARCH_HEIGHT, ZERO_MESH)
    positive = [zero for zero in zeros if _pari_decimal(zero) > 0]
    if len(positive) < ZEROS_PER_FIELD:
        raise ArithmeticError(
            "D=%s k=%s has only %d positive zeros below height %d"
            % (field["D"], field["k"], len(positive), SEARCH_HEIGHT)
        )
    return tuple(str(zero) for zero in positive[:ZEROS_PER_FIELD])


def _data_for_precision(working_digits):
    working_digits = int(working_digits)
    if working_digits in _DATA:
        return _DATA[working_digits]
    rows = {}
    for field in _fields():
        rows[(field["D"], field["k"])] = _zeros_for_field(field, working_digits)
    _DATA[working_digits] = rows
    return rows


def _zero_text(D, k, n, working_digits):
    return _data_for_precision(working_digits)[(int(D), int(k))][int(n) - 1]


def _field_comment(field, n):
    signature = "$(3,0)$" if field["D"] > 0 else "$(1,1)$"
    text = (
        "$K=\\mathbb{Q}(a)$ with $%s=0$; signature %s; Galois closure %s; "
        "LMFDB %s."
        % (str(field["poly"]).replace("*", ""), signature, field["group"], field["lmfdb_label"])
    )
    match = T4_MATCHES.get((field["D"], field["k"]), {}).get(int(n))
    if match:
        text += " This ordinate is also %s." % match
    return text


def _assert_cyclic_controls():
    """The conductor-7 cyclic cubic field factors through T4's two characters."""
    expected = {
        1: "4.35640162473628422727957479051",
        2: "6.20123004275588129466099054628",
        3: "7.92743089809203774838798659746",
        4: "8.78555471449907536558015746317",
        5: "10.73611998749339311587424153504",
        6: "11.01044486207249042239362741094",
    }
    for n, text in expected.items():
        got = _zero_text(49, 1, n, CHECK_DIGITS)
        if not got.startswith(text):
            raise ArithmeticError("D=49 n=%d gave %s, expected prefix %s" % (n, got, text))
    print("matched the first six D=49 cyclic zeros with T4 prefixes")


class CubicDedekindZetaZeros(numberdb.Generator):
    table = os.environ.get("NUMBERDB_TABLE", "T385")
    parameters = ("D", "k", "n")
    type = "R"
    digits = DIGITS
    rigour = "heuristic (agreement-checked)"
    files = ("generate.py",)

    def enumerate(self, bound=BOUND):
        if bound != BOUND:
            raise ValueError("this generator is written for bound %d" % BOUND)
        for field in _fields():
            for n in range(1, ZEROS_PER_FIELD + 1):
                yield {"D": field["D"], "k": field["k"], "n": n}

    def value(self, params, digits):
        D = int(params["D"])
        k = int(params["k"])
        n = int(params["n"])
        field = _field_by_identity(D, k)
        return {
            "number": numberdb.agreeing(
                lambda working: _zero_text(D, k, n, working),
                at=WORKING_DIGITS,
            ),
            "comment": _field_comment(field, n),
        }


def fill_draft_once(generator, message):
    """Fill a fresh prose draft without the client's empty upsert probe."""
    from numberdb._generate import (
        _check_precision,
        _check_rigour,
        _producer,
        _run_name,
        _source_files,
    )
    from numberdb._write import Entries, attach, submit_entries, to_text

    table = generator.table
    run = _run_name(generator)
    entries = Entries(*generator.parameters)

    for params in generator.enumerate():
        params = dict(params)
        wanted = generator.digits_for(params)
        entry = generator._entry(params, wanted)
        value = entry["number"]
        identity = ",".join(str(params[name]) for name in generator.parameters)
        _check_rigour(generator, table, identity, value)

        written = to_text(value, wanted, generator.format)
        _check_precision(table, identity, written, wanted, lowering=False)

        record = dict(entry)
        record.pop("digits", None)
        entries.add(**params, **record, digits=wanted)

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
    generator = CubicDedekindZetaZeros()
    _assert_cyclic_controls()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="computed cubic Dedekind zeta zero ordinates",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
