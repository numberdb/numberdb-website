"""Values L_p(E,1) of the p-adic L-function of elliptic curves over Q of rank 0 -- numberdb.org/T413.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The file reads elliptic curves from Sage's mini Cremona database with conductor
N <= 30 and rank 0. For each ordinary prime 5 <= p <= 29 of good reduction it
stores the central value L_p(E,1) in Sage's Mazur-Tate-Teitelbaum
normalisation. The p-adic precision is the least n with p^n >= 10^50.
"""

import math
import os
import re
import sys
from decimal import Decimal, localcontext

import numberdb.sage as numberdb
from sage.databases.cremona import CremonaDatabase, cremona_to_lmfdb
from sage.libs.pari import pari
from sage.rings.fast_arith import prime_range
from sage.rings.integer_ring import ZZ
from sage.rings.padics.factory import Qp
from sage.rings.rational_field import QQ
from sage.schemes.elliptic_curves.constructor import EllipticCurve


TABLE = os.environ.get("NUMBERDB_TABLE", "T413")
CONDUCTOR_BOUND = 30
PRIME_BOUND = 29
DECIMAL_DIGITS = 50
PRECISION_TARGET = ZZ(10) ** DECIMAL_DIGITS
ROOT_GUARD = 8
PARI_WORKING_DIGITS = 80
PARI_GUARD_BITS = 96
PARI_RELATIVE_TOLERANCE = Decimal("1e-25")

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
            ainvs = tuple(QQ(a) for a in data[0])
            rank = ZZ(data[1])
            yield conductor, label, ainvs, rank


def record_key(params):
    return tuple(str(params[name]) for name in ("N", "c4", "c6", "p"))


def unit_root(curve, p, precision):
    """The unit root of x^2 - a_p x + p by Hensel lifting."""
    p = ZZ(p)
    ap = ZZ(curve.ap(p))
    working = precision + ROOT_GUARD
    field = Qp(p, working, print_mode="series")
    x = field(ap)
    ap_padic = field(ap)
    p_padic = field(p)
    steps = int(math.ceil(math.log(max(working, 2), 2))) + 2
    for _ in range(steps):
        x -= (x * x - ap_padic * x + p_padic) / (2 * x - ap_padic)
    alpha = x.add_bigoh(working)
    residual = alpha * alpha - ap_padic * alpha + p_padic
    if residual.precision_absolute() < precision:
        raise ArithmeticError(
            "unit root for %s at p=%s has only O(%s^%s)"
            % (curve, p, p, residual.precision_absolute()))
    return alpha


def l_ratio(curve):
    """The exact rational L(E,1) / Omega_E in Sage's normalisation."""
    symbol = curve.modular_symbol(sign=+1, implementation="eclib")(0)
    return QQ(symbol) / QQ(curve.real_components())


def padic_l_value(curve, p, precision):
    ratio = l_ratio(curve)
    alpha = unit_root(curve, p, precision)
    value = QQ(ratio) * (1 - 1 / alpha) ** 2
    value = value.add_bigoh(precision)
    if value.precision_absolute() < precision:
        raise ArithmeticError(
            "L-value at p=%s has precision %s, expected at least %s"
            % (p, value.precision_absolute(), precision))
    residual = alpha * alpha - ZZ(curve.ap(p)) * alpha + ZZ(p)
    if residual.precision_absolute() < precision:
        raise ArithmeticError("alpha check lost precision at p=%s" % p)
    return value


def pari_l_value_ratio(curve, ainvs):
    """PARI's complex L(E,1), divided by the real Neron period."""
    bits = numberdb.bits(PARI_WORKING_DIGITS, losing=PARI_GUARD_BITS)
    pari.default("realbitprecision", bits)
    pari.default("realprecision", PARI_WORKING_DIGITS + 20)
    ainvs_text = "[%s]" % ",".join(str(int(a)) for a in ainvs)
    curve_data = pari("ellinit(%s)" % ainvs_text)
    value = pari.lfun(pari.lfuncreate(curve_data), 1, 0, bits)
    omega = pari("ellinit(%s).omega[1]" % ainvs_text) * curve.real_components()
    return Decimal(str(value)) / Decimal(str(omega))


def check_l_ratio(curve, ainvs, label):
    ratio = l_ratio(curve)
    with localcontext() as context:
        context.prec = PARI_WORKING_DIGITS
        expected = Decimal(int(ratio.numerator())) / Decimal(int(ratio.denominator()))
    got = pari_l_value_ratio(curve, ainvs)
    with localcontext() as context:
        context.prec = PARI_WORKING_DIGITS
        scale = max(abs(expected), Decimal(1))
        error = abs(got - expected) / scale
    if error > PARI_RELATIVE_TOLERANCE:
        raise ArithmeticError(
            "%s: PARI L(E,1)/Omega_E gives %s, exact ratio is %s "
            "(relative error %s)" % (label, got, expected, error))


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
    checked_ratios = set()
    primes = [ZZ(p) for p in prime_range(5, PRIME_BOUND + 1)]
    for conductor, cremona_label, ainvs, rank in cremona_rows(CONDUCTOR_BOUND):
        if rank != 0:
            continue
        curve = curve_from_ainvs(ainvs)
        c4 = ZZ(curve.c4())
        c6 = ZZ(curve.c6())
        if cremona_label not in checked_ratios:
            check_l_ratio(curve, ainvs, cremona_label)
            checked_ratios.add(cremona_label)
        try:
            lmfdb_label = cremona_to_lmfdb(cremona_label)
        except Exception:  # noqa: BLE001
            lmfdb_label = None
        for p in primes:
            if ZZ(conductor) % p == 0:
                continue
            if not curve.is_ordinary(p):
                continue
            precision = precision_for_prime(p)
            value = padic_l_value(curve, p, precision)
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


class EllipticCurvePadicLValues(numberdb.Generator):
    table = TABLE
    parameters = ("N", "c4", "c6", "p")
    type = "Qp"
    digits = DECIMAL_DIGITS
    rigour = "proven"

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
    generator = EllipticCurvePadicLValues()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="p-adic L-values of rank-zero elliptic curves"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
