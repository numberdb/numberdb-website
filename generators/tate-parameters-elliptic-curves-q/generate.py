"""Tate parameters q_E of elliptic curves over Q -- numberdb.org/T409.

This generator fills T409 with the p-adic Tate parameters q_E of elliptic
curves over Q with split multiplicative reduction. The curves are the reduced
global minimal models in Sage's mini Cremona database with conductor N <= 100,
and the table stores every split multiplicative prime of each such curve.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The values are computed by Sage's TateCurve.parameter with absolute p-adic
precision p^n >= 10^50. The integrity check verifies the split multiplicative
filter, the absolute precision, v_p(q_E) = v_p(Delta_E), and the q-expansion
of the j-invariant to the precision left after inverting q_E.
"""

import os
import re
import sys
from functools import lru_cache

import numberdb.sage as numberdb
from sage.databases.cremona import CremonaDatabase, cremona_to_lmfdb
from sage.rings.integer_ring import ZZ
from sage.schemes.elliptic_curves import ell_generic  # noqa: F401
from sage.schemes.elliptic_curves.constructor import EllipticCurve


TABLE = os.environ.get("NUMBERDB_TABLE", "T409")
CONDUCTOR_BOUND = 100
DIGITS = 100


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def _label_key(label):
    found = re.fullmatch(r"([a-z]+)(\d+)", label)
    if found is None:
        return label, 0
    return found.group(1), int(found.group(2))


def target_absolute_precision(p):
    """The least n with p^n >= 10^50."""
    p = ZZ(p)
    n = ZZ(1)
    power = p
    bound = ZZ(10) ** 50
    while power < bound:
        n += 1
        power *= p
    return n


def invariants(ainvs):
    a1, a2, a3, a4, a6 = [ZZ(a) for a in ainvs]
    b2 = a1 * a1 + 4 * a2
    b4 = a1 * a3 + 2 * a4
    b6 = a3 * a3 + 4 * a6
    c4 = b2 * b2 - 24 * b4
    c6 = -b2 * b2 * b2 + 36 * b2 * b4 - 216 * b6
    return c4, c6


def curve_from_ainvs(ainvs):
    return EllipticCurve([ZZ(a) for a in ainvs])


@lru_cache(maxsize=1)
def tate_rows():
    rows = []
    database = CremonaDatabase()
    for conductor in range(1, CONDUCTOR_BOUND + 1):
        curves = database.allcurves(conductor)
        for label, record in sorted(curves.items(), key=lambda item: _label_key(item[0])):
            ainvs, _rank, _torsion_order = record
            ainvs = tuple(ZZ(a) for a in ainvs)
            curve = curve_from_ainvs(ainvs)
            c4, c6 = invariants(ainvs)
            for p in sorted(ZZ(conductor).prime_divisors()):
                p = ZZ(p)
                if not curve.has_split_multiplicative_reduction(p):
                    continue
                rows.append({
                    "N": ZZ(conductor),
                    "label": label,
                    "lmfdb_label": cremona_to_lmfdb("%s%s" % (conductor, label)),
                    "ainvs": ainvs,
                    "c4": c4,
                    "c6": c6,
                    "p": p,
                    "valuation": ZZ(curve.local_data(p).discriminant_valuation()),
                    "target": target_absolute_precision(p),
                })
    return tuple(rows)


def row_for_params(params):
    wanted = (ZZ(params["N"]), ZZ(params["c4"]), ZZ(params["c6"]), ZZ(params["p"]))
    for row in tate_rows():
        found = (row["N"], row["c4"], row["c6"], row["p"])
        if found == wanted:
            return row
    raise KeyError("no Tate parameter row has parameters %s" % (wanted,))


def tate_parameter(row):
    curve = curve_from_ainvs(row["ainvs"])
    relative = max(ZZ(1), row["target"] - row["valuation"])
    return curve.tate_curve(row["p"]).parameter(relative)


def entry_comment(row):
    cremona_label = "%s%s" % (row["N"], row["label"])
    lmfdb_label = row["lmfdb_label"]
    if lmfdb_label.replace(".", "") == cremona_label:
        return "Cremona label %s." % cremona_label
    return "Cremona label %s; LMFDB label %s." % (cremona_label, lmfdb_label)


def _ceil_div(a, b):
    return -(-ZZ(a) // ZZ(b))


def j_from_tate_parameter(q, required):
    """Compute j(q) from E4^3 / Delta, truncated past the required precision."""
    field = q.parent()
    one = field(1)
    q_power = one
    e4 = one
    delta_unit = one
    valuation = ZZ(q.valuation())
    terms = max(ZZ(1), _ceil_div(required, valuation) + 5)
    for n in range(1, int(terms) + 1):
        q_power *= q
        e4 += field(240 * n**3) * q_power / (one - q_power)
        delta_unit *= (one - q_power) ** 24
    return (e4 ** 3) / (q * delta_unit)


def check_j_invariant(row, q):
    curve = curve_from_ainvs(row["ainvs"])
    required = row["target"] - 2 * ZZ(q.valuation())
    if required <= 0:
        return
    found = j_from_tate_parameter(q, required)
    expected = q.parent()(curve.j_invariant())
    difference = found - expected
    if difference != 0 and difference.valuation() < required:
        raise ArithmeticError(
            "%s p=%s: j(q) agrees only to valuation %s, expected at least %s"
            % ("%s%s" % (row["N"], row["label"]), row["p"],
               difference.valuation(), required)
        )


def run_integrity_checks():
    rows = tate_rows()
    if len(rows) != 214:
        raise ArithmeticError("expected 214 Tate parameters, found %d" % len(rows))

    longest = ("", 0)
    by_prime = {}
    for row in rows:
        curve = curve_from_ainvs(row["ainvs"])
        if not curve.has_split_multiplicative_reduction(row["p"]):
            raise ArithmeticError(
                "%s p=%s is not split multiplicative"
                % ("%s%s" % (row["N"], row["label"]), row["p"])
            )
        q = tate_parameter(row)
        if q.precision_absolute() != row["target"]:
            raise ArithmeticError(
                "%s p=%s has absolute precision %s, expected %s"
                % ("%s%s" % (row["N"], row["label"]), row["p"],
                   q.precision_absolute(), row["target"])
            )
        if q.valuation() != row["valuation"]:
            raise ArithmeticError(
                "%s p=%s has valuation %s, expected %s"
                % ("%s%s" % (row["N"], row["label"]), row["p"],
                   q.valuation(), row["valuation"])
            )
        check_j_invariant(row, q)
        key = "%s%s, p=%s" % (row["N"], row["label"], row["p"])
        length = len(str(q))
        if length > longest[1]:
            longest = (key, length)
        by_prime[int(row["p"])] = by_prime.get(int(row["p"]), 0) + 1

    print("integrity checks passed for %d Tate parameters" % len(rows))
    print("checked split multiplicative reduction and absolute p-adic precision")
    print("checked v_p(q_E) = v_p(Delta_E) and the j(q) expansion on every row")
    print("longest value has %d characters at %s" % (longest[1], longest[0]))
    print("entries by prime: %s" % sorted(by_prime.items()))


class TateParametersEllipticCurvesQ(numberdb.Generator):
    table = TABLE
    parameters = ("N", "c4", "c6", "p")
    type = "Qp"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self):
        for row in tate_rows():
            yield {
                "N": str(row["N"]),
                "c4": str(row["c4"]),
                "c6": str(row["c6"]),
                "p": str(row["p"]),
            }

    def value(self, params, digits):
        row = row_for_params(params)
        return {
            "number": tate_parameter(row),
            "comment": entry_comment(row),
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
    generator = TateParametersEllipticCurvesQ()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="fill Tate-parameter draft from Sage Tate curves",
        ))
    elif os.environ.get("NUMBERDB_CHECK_ONLY") == "1":
        sys.exit(0)
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
