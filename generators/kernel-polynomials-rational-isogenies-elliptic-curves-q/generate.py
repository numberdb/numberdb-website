"""Kernel polynomials of rational isogenies of elliptic curves over Q -- numberdb.org/T345

For each elliptic curve E/Q in Sage's mini Cremona database with conductor
N <= 300, and for each rational isogeny E -> E' of prime degree ell >= 5,
this stores the monic polynomial whose roots are the x-coordinates of the
nonzero points in the kernel.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The rings are named rather than taken from `sage.all`, so this runs on a
modular passagemath as well as on a full SageMath. `numberdb.sage` is imported
first because it is what initialises Sage.

Answers numberdb-data#10 in the family numberdb-data#165.
"""

import os
import re
import sys

import numberdb.sage as numberdb
import sage.rings.polynomial.laurent_polynomial_ring  # noqa: F401
import sage.rings.qqbar as qqbar
from sage.databases.cremona import CremonaDatabase
from sage.libs.pari import pari
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ
from sage.schemes.elliptic_curves.constructor import EllipticCurve


TABLE = os.environ.get("NUMBERDB_TABLE", "T345")
CONDUCTOR_BOUND = 300

QX = PolynomialRing(QQ, "x")
qqbar._init_qqbar()

_RECORDS = None
_BY_KEY = None


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _curve_from_ainvs(ainvs):
    """Build an elliptic curve without Sage's Sequence constructor path."""
    return EllipticCurve(QQ, [QQ(a) for a in ainvs])


def _label_key(label):
    """Sort labels like a1, a2, b1 by Cremona class and curve number."""
    found = re.fullmatch(r"([a-z]+)([0-9]+)", label)
    if not found:
        return (label, 0)
    curve_class, number = found.groups()
    return (len(curve_class), curve_class, int(number))


def _curve_rows(bound):
    database = CremonaDatabase()
    for conductor in range(1, bound + 1):
        for short_label, data in sorted(
                database.allcurves(conductor).items(),
                key=lambda item: _label_key(item[0])):
            ainvs = tuple(QQ(a) for a in data[0])
            yield conductor, "%s%s" % (conductor, short_label), ainvs


def _record_key(params):
    return tuple(str(params[name]) for name in
                 ("N", "c4", "c6", "ell", "target_c4", "target_c6"))


def _entry_comment(source_label, target_label):
    return "Cremona labels %s to %s." % (source_label, target_label)


def _records():
    global _RECORDS, _BY_KEY
    if _RECORDS is not None:
        return _RECORDS

    records = []
    seen = set()
    for conductor, source_label, ainvs in _curve_rows(CONDUCTOR_BOUND):
        source = _curve_from_ainvs(ainvs)
        source_c4 = ZZ(source.c4())
        source_c6 = ZZ(source.c6())
        isogenies = []
        for phi in source.isogenies_prime_degree():
            ell = ZZ(phi.degree())
            if ell < 5:
                continue
            target = phi.codomain().minimal_model()
            target_c4 = ZZ(target.c4())
            target_c6 = ZZ(target.c6())
            try:
                target_label = target.cremona_label()
            except Exception:  # noqa: BLE001
                target_label = "target with c4=%s, c6=%s" % (
                    target_c4, target_c6)
            polynomial = QX(phi.kernel_polynomial())
            params = {
                "N": str(conductor),
                "c4": str(source_c4),
                "c6": str(source_c6),
                "ell": str(ell),
                "target_c4": str(target_c4),
                "target_c6": str(target_c6),
            }
            key = _record_key(params)
            if key in seen:
                raise ArithmeticError(
                    "the parameters do not distinguish an isogeny: %s"
                    % (",".join(key),))
            seen.add(key)
            isogenies.append({
                "source": source,
                "source_ainvs": ainvs,
                "source_label": source_label,
                "target_label": target_label,
                "target_c4": target_c4,
                "target_c6": target_c6,
                "ell": ell,
                "params": params,
                "polynomial": polynomial,
            })

        records.extend(sorted(
            isogenies,
            key=lambda row: (
                int(row["params"]["ell"]),
                _label_key(row["target_label"][len(str(conductor)):])
                if row["target_label"].startswith(str(conductor))
                else row["target_label"],
                int(row["params"]["target_c4"]),
                int(row["params"]["target_c6"]),
            )))

    _RECORDS = records
    _BY_KEY = {_record_key(row["params"]): row for row in records}
    return _RECORDS


def _row_for(params):
    if _BY_KEY is None:
        _records()
    key = tuple(str(params[name]) for name in
                ("N", "c4", "c6", "ell", "target_c4", "target_c6"))
    return _BY_KEY[key]


def _pari_codomain_invariants(ainvs, kernel_polynomial):
    curve = pari([QQ(a) for a in ainvs]).ellinit()
    result = pari.ellisogeny(curve, pari(str(kernel_polynomial)))
    codomain_ainvs = [QQ(a) for a in result[0]]
    codomain = _curve_from_ainvs(codomain_ainvs).minimal_model()
    return ZZ(codomain.c4()), ZZ(codomain.c6())


def _stored_t341_polynomial(row):
    if row["ell"] != 5 or ZZ(row["params"]["N"]) > 60:
        return None
    document = numberdb.table("T341")
    by_conductor = document["Numbers"].get(row["params"]["N"])
    if not by_conductor:
        return None
    by_curve = by_conductor.get("%s,%s" % (
        row["params"]["c4"], row["params"]["c6"]))
    if not by_curve:
        return None
    entry = by_curve.get("5")
    if isinstance(entry, dict):
        entry = entry.get("number")
    return QX(entry) if entry else None


def run_integrity_checks():
    records = _records()
    by_degree = {}
    longest = (0, None)
    overlap_t341 = 0

    for row in records:
        ell = row["ell"]
        polynomial = row["polynomial"]
        by_degree[int(ell)] = by_degree.get(int(ell), 0) + 1

        if polynomial.leading_coefficient() != 1:
            raise ArithmeticError("kernel polynomial is not monic: %s"
                                  % row["params"])
        if polynomial.degree() != (ell - 1) // 2:
            raise ArithmeticError("wrong degree for %s" % row["params"])

        division = QX(row["source"].division_polynomial(ell))
        quotient, remainder = division.quo_rem(polynomial)
        if remainder:
            raise ArithmeticError("kernel polynomial does not divide psi_%s for %s"
                                  % (ell, row["params"]))

        t341 = _stored_t341_polynomial(row)
        if t341 is not None:
            _, t341_remainder = t341.quo_rem(polynomial)
            if t341_remainder:
                raise ArithmeticError("kernel polynomial does not divide T341 row %s"
                                      % row["params"])
            overlap_t341 += 1

        c4, c6 = _pari_codomain_invariants(
            row["source_ainvs"], polynomial)
        if (c4, c6) != (row["target_c4"], row["target_c6"]):
            raise ArithmeticError(
                "PARI isogeny target mismatch for %s: got c4=%s, c6=%s"
                % (row["params"], c4, c6))

        text_length = len(str(polynomial))
        if text_length > longest[0]:
            longest = (text_length, row["params"])

    counts = ", ".join("ell=%s: %s" % item for item in sorted(by_degree.items()))
    print("integrity checks passed for %d rational isogeny kernel polynomials"
          % len(records))
    print("degree counts: %s" % counts)
    print("checked divisibility against T341 on %d ell=5 overlap rows"
          % overlap_t341)
    print("PARI ellisogeny returned the target invariants for every row")
    print("longest polynomial has %d characters at %s" % longest)


class RationalIsogenyKernelPolynomials(numberdb.Generator):
    """Generator for T345, rational-isogeny kernel polynomials."""

    table = TABLE
    parameters = ("N", "c4", "c6", "ell", "target_c4", "target_c6")
    type = "Q[]"
    rigour = "exact"

    def enumerate(self):
        for row in _records():
            yield dict(row["params"])

    def value(self, params, digits):
        row = _row_for(params)
        return {
            "number": row["polynomial"],
            "comment": _entry_comment(row["source_label"], row["target_label"]),
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
        attach(table, name, body, run=run, message=message,
               rigour=generator.rigour)

    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = RationalIsogenyKernelPolynomials()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="rational-isogeny kernel polynomials from exact data"))
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
