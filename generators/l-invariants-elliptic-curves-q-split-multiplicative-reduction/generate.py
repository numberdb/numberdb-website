"""L-invariants of elliptic curves over Q with split multiplicative reduction -- numberdb.org/T410.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The file reads elliptic curves from Sage's mini Cremona database with conductor
N <= 100. For each prime p of split multiplicative reduction it stores the
Mazur-Tate-Teitelbaum L-invariant, using Sage's Tate curve implementation and
the Iwasawa branch of the p-adic logarithm, log_p(p) = 0. The p-adic precision
is the least n with p^n >= 10^50.
"""

import os
import re
import sys

import numberdb.sage as numberdb
from sage.databases.cremona import CremonaDatabase, cremona_to_lmfdb
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.schemes.elliptic_curves.constructor import EllipticCurve


TABLE = os.environ.get("NUMBERDB_TABLE", "T410")
CONDUCTOR_BOUND = 100
DECIMAL_DIGITS = 50
PRECISION_TARGET = ZZ(10) ** DECIMAL_DIGITS
LOG_GUARD = 10
COMPUTE_GUARD = 10
AGREEMENT_GUARD = 20

_RECORDS = None
_BY_KEY = None


def key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def precision_for_prime(p, decimal_digits=DECIMAL_DIGITS):
    """Least n with p^n carrying at least decimal_digits decimal digits."""
    p = ZZ(p)
    n = 1
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
    """Build an elliptic curve without Sage's Sequence constructor path."""
    return EllipticCurve(QQ, [QQ(a) for a in ainvs])


def cremona_rows(bound):
    database = CremonaDatabase()
    for conductor in range(11, bound + 1):
        for short_label, data in sorted(
                database.allcurves(conductor).items(),
                key=lambda item: label_key(item[0])):
            label = "%s%s" % (conductor, short_label)
            yield conductor, label, tuple(QQ(a) for a in data[0])


def record_key(params):
    return tuple(str(params[name]) for name in ("N", "c4", "c6", "p"))


def independent_l_invariant(tate_curve, p, precision):
    q = tate_curve.parameter(precision + LOG_GUARD)
    return (q.log(p_branch=0) / ZZ(q.valuation())).add_bigoh(precision)


def entry_comment(cremona_label, lmfdb_label):
    if lmfdb_label:
        return "Cremona label %s; LMFDB label %s." % (
            cremona_label, lmfdb_label)
    return "Cremona label %s." % (cremona_label,)


def records():
    global _RECORDS, _BY_KEY
    if _RECORDS is not None:
        return _RECORDS

    out = []
    seen = set()
    for conductor, cremona_label, ainvs in cremona_rows(CONDUCTOR_BOUND):
        curve = curve_from_ainvs(ainvs)
        c4 = ZZ(curve.c4())
        c6 = ZZ(curve.c6())
        try:
            lmfdb_label = cremona_to_lmfdb(cremona_label)
        except Exception:  # noqa: BLE001
            lmfdb_label = None
        for p in sorted(ZZ(conductor).prime_divisors()):
            p = ZZ(p)
            if not curve.has_split_multiplicative_reduction(p):
                continue
            precision = precision_for_prime(p)
            tate_curve = curve.tate_curve(p)
            value = tate_curve.L_invariant(
                precision + COMPUTE_GUARD).add_bigoh(precision)
            repeated = tate_curve.L_invariant(
                precision + AGREEMENT_GUARD).add_bigoh(precision)
            if value != repeated:
                raise ArithmeticError(
                    "%s at p=%s: computations at two precisions disagree: "
                    "%s and %s" % (cremona_label, p, value, repeated))
            expected = independent_l_invariant(tate_curve, p, precision)
            if value != expected:
                raise ArithmeticError(
                    "%s at p=%s: L_invariant %s, log(q)/ord(q) %s"
                    % (cremona_label, p, value, expected))
            if value.precision_absolute() < precision:
                raise ArithmeticError(
                    "%s at p=%s has precision %s, expected at least %s"
                    % (cremona_label, p, value.precision_absolute(), precision))
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


class EllipticCurveMTTLInvariants(numberdb.Generator):
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


if __name__ == "__main__":
    key_from_stdin()
    generator = EllipticCurveMTTLInvariants()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="MTT L-invariants for split multiplicative elliptic curves"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
