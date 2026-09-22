"""Cyclotomic p-adic regulators of elliptic curves over Q of rank 1 -- numberdb.org/T412.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The file reads rank-one elliptic curves from Sage's mini Cremona database with
conductor N <= 175. For each good ordinary prime p in {5, 7, 11, 13}, it stores
Sage's cyclotomic p-adic regulator in the Mazur-Tate-Teitelbaum
normalisation, to the least precision n with p^n >= 10^50.
"""

import math
import os
import re
import sys

import numberdb.sage as numberdb
import sage.symbolic.ring  # noqa: F401
import sage.symbolic.function  # noqa: F401
import sage.functions.trig  # noqa: F401
from sage.databases.cremona import CremonaDatabase, cremona_to_lmfdb
import sage.rings.polynomial.laurent_polynomial_ring  # noqa: F401
import sage.schemes.hyperelliptic_curves.monsky_washnitzer as monsky_washnitzer
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.schemes.elliptic_curves.constructor import EllipticCurve


TABLE = os.environ.get("NUMBERDB_TABLE", "T412")
CONDUCTOR_BOUND = 175
ORDINARY_PRIMES = tuple(ZZ(p) for p in (5, 7, 11, 13))
DECIMAL_DIGITS = 50
PRECISION_TARGET = ZZ(10) ** DECIMAL_DIGITS
COMPUTE_GUARD = 8
AGREEMENT_GUARD = 16

_RECORDS = None
_BY_KEY = None

# Sage's Monsky-Washnitzer p-adic height code uses a lazy symbolic log in a
# precision branch. Under named imports that path can raise a symbolic RuntimeError.
monsky_washnitzer.log = math.log
monsky_washnitzer.ceil = math.ceil


def key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def precision_for_prime(p, decimal_digits=DECIMAL_DIGITS):
    """Least n with p^n carrying at least decimal_digits decimal digits."""
    p = ZZ(p)
    n = ZZ(1)
    power = p
    target = ZZ(10) ** ZZ(decimal_digits)
    while power < target:
        n += 1
        power *= p
    return n


def label_key(label):
    found = re.fullmatch(r"([a-z]+)([0-9]+)", label)
    if not found:
        return (label, 0)
    curve_class, number = found.groups()
    return (len(curve_class), curve_class, int(number))


def curve_from_ainvs(ainvs):
    return EllipticCurve(QQ, [QQ(a) for a in ainvs])


def cremona_rows(bound):
    database = CremonaDatabase()
    for conductor in range(11, bound + 1):
        for short_label, data in sorted(
                database.allcurves(conductor).items(),
                key=lambda item: label_key(item[0])):
            ainvs, rank, _torsion_order = data
            label = "%s%s" % (conductor, short_label)
            yield ZZ(conductor), label, tuple(QQ(a) for a in ainvs), ZZ(rank)


def record_key(params):
    return tuple(str(params[name]) for name in ("N", "c4", "c6", "p"))


def entry_comment(cremona_label, lmfdb_label):
    if lmfdb_label and lmfdb_label.replace(".", "") != cremona_label:
        return "Cremona label %s; LMFDB label %s." % (
            cremona_label, lmfdb_label)
    return "Cremona label %s." % (cremona_label,)


def is_good_ordinary(curve, conductor, p):
    return conductor % p != 0 and curve.ap(p) % p != 0


def truncated(value, precision):
    return value.add_bigoh(precision)


def check_height_identity(curve, p, precision, regulator):
    height = curve.padic_height(p, precision + AGREEMENT_GUARD)
    generator = curve.gens()[0]
    height_of_generator = truncated(height(generator), precision)
    if regulator != height_of_generator:
        raise ArithmeticError(
            "%s p=%s: regulator %s but h_p(P) %s"
            % (curve.cremona_label(), p, regulator, height_of_generator))
    quadratic = truncated(height(ZZ(2) * generator) - ZZ(4) * height(generator),
                          precision)
    if quadratic != 0 and quadratic.valuation() < precision:
        raise ArithmeticError(
            "%s p=%s: h_p(2P)-4h_p(P) has valuation %s, expected at least %s"
            % (curve.cremona_label(), p, quadratic.valuation(), precision))


def records():
    global _RECORDS, _BY_KEY
    if _RECORDS is not None:
        return _RECORDS

    out = []
    seen = set()
    for conductor, cremona_label, ainvs, rank in cremona_rows(CONDUCTOR_BOUND):
        if rank != 1:
            continue
        curve = curve_from_ainvs(ainvs)
        c4 = ZZ(curve.c4())
        c6 = ZZ(curve.c6())
        try:
            lmfdb_label = cremona_to_lmfdb(cremona_label)
        except Exception:  # noqa: BLE001
            lmfdb_label = None
        for p in ORDINARY_PRIMES:
            p = ZZ(p)
            if not is_good_ordinary(curve, conductor, p):
                continue
            precision = precision_for_prime(p)
            value = truncated(
                curve.padic_regulator(p, precision + COMPUTE_GUARD),
                precision)
            repeated = truncated(
                curve.padic_regulator(p, precision + AGREEMENT_GUARD),
                precision)
            if value != repeated:
                raise ArithmeticError(
                    "%s at p=%s: computations at two precisions disagree: "
                    "%s and %s" % (cremona_label, p, value, repeated))
            if value.precision_absolute() < precision:
                raise ArithmeticError(
                    "%s at p=%s has precision %s, expected at least %s"
                    % (cremona_label, p, value.precision_absolute(), precision))
            check_height_identity(curve, p, precision, value)
            params = {
                "N": str(conductor),
                "c4": str(c4),
                "c6": str(c6),
                "p": str(p),
            }
            key = record_key(params)
            if key in seen:
                raise ArithmeticError(
                    "the parameters do not identify one row: %s"
                    % (",".join(key),))
            seen.add(key)
            out.append({
                "params": params,
                "value": value,
                "cremona_label": cremona_label,
                "lmfdb_label": lmfdb_label,
            })

    _RECORDS = out
    _BY_KEY = {record_key(row["params"]): row for row in out}
    return _RECORDS


def row_for(params):
    if _BY_KEY is None:
        records()
    return _BY_KEY[tuple(str(params[name]) for name in ("N", "c4", "c6", "p"))]


def run_integrity_checks():
    rows = records()
    if len(rows) != 285:
        raise ArithmeticError("expected 285 p-adic regulators, found %d" % len(rows))
    longest = ("", 0)
    by_prime = {}
    for row in rows:
        text = str(row["value"])
        label = "%s, p=%s" % (row["cremona_label"], row["params"]["p"])
        if len(text) > longest[1]:
            longest = (label, len(text))
        p = int(row["params"]["p"])
        by_prime[p] = by_prime.get(p, 0) + 1
    print("integrity checks passed for %d p-adic regulators" % len(rows))
    print("checked agreement at two precisions, Reg_p(E)=h_p(P), and h_p(2P)=4h_p(P)")
    print("longest value has %d characters at %s" % (longest[1], longest[0]))
    print("entries by prime: %s" % sorted(by_prime.items()))


class CyclotomicPadicRegulatorsRankOne(numberdb.Generator):
    table = TABLE
    parameters = ("N", "c4", "c6", "p")
    type = "Qp"
    digits = DECIMAL_DIGITS
    rigour = "heuristic (agreement-checked)"

    def enumerate(self):
        for row in records():
            yield dict(row["params"])

    def value(self, params, digits):
        row = row_for(params)
        return {
            "number": row["value"],
            "comment": entry_comment(row["cremona_label"], row["lmfdb_label"]),
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
        bounded = True if generator.type == "Qp" else None
        _check_rigour(generator, table, identity, value, bounded=bounded)

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
    key_from_stdin()
    generator = CyclotomicPadicRegulatorsRankOne()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="fill cyclotomic p-adic regulator draft from Sage",
        ))
    elif os.environ.get("NUMBERDB_CHECK_ONLY") == "1":
        sys.exit(0)
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
