"""Faltings heights of elliptic curves over Q -- numberdb.org/T211.

    h(E) = -1/2 log(area(C/Lambda_E))

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The period lattice area is computed directly in Arb from the agm formulas
Sage uses for its period basis. Sage's own faltings_height() is used only as
an outside check, not as the value source.
"""

import os
import re
import sys

import numberdb.sage as numberdb
from sage.databases.cremona import CremonaDatabase, cremona_to_lmfdb, sort_key
from sage.rings.complex_arb import ComplexBallField
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField
from sage.schemes.elliptic_curves.constructor import EllipticCurve
import sage.rings.qqbar as qqbar

qqbar._init_qqbar()

MAX_CONDUCTOR = 100
WORKING_GUARD_BITS = 192

_CURVES = None
_CURVES_BY_KEY = None


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _lmfdb_url(label):
    found = re.fullmatch(r"([0-9]+)\.([a-z]+)([0-9]+)", label)
    if found is None:
        raise ValueError("not an LMFDB curve label: %s" % (label,))
    conductor, iso, curve_number = found.groups()
    return "https://www.lmfdb.org/EllipticCurve/Q/%s/%s/%s" % (
        conductor, iso, curve_number)


def curves(max_conductor=MAX_CONDUCTOR):
    global _CURVES
    if _CURVES is not None and max_conductor == MAX_CONDUCTOR:
        return _CURVES

    database = CremonaDatabase()
    found = []
    for conductor in range(1, max_conductor + 1):
        for label, data in sorted(database.allcurves(conductor).items(),
                                  key=lambda item: sort_key(item[0])):
            curve = EllipticCurve(QQ, data[0]).minimal_model()
            c4, c6 = curve.c_invariants()
            cremona_label = "%s%s" % (conductor, label)
            lmfdb_label = cremona_to_lmfdb(cremona_label, database)
            found.append({
                "N": ZZ(conductor),
                "c4": ZZ(c4),
                "c6": ZZ(c6),
                "cremona_label": cremona_label,
                "lmfdb_label": lmfdb_label,
                "lmfdb_url": _lmfdb_url(lmfdb_label),
                "curve": curve,
            })
    if max_conductor == MAX_CONDUCTOR:
        _CURVES = found
    return found


def curves_by_key():
    global _CURVES_BY_KEY
    if _CURVES_BY_KEY is None:
        by_key = {}
        for record in curves():
            key = (record["N"], record["c4"], record["c6"])
            if key in by_key:
                raise ArithmeticError("duplicate curve key %s" % (key,))
            by_key[key] = record
        _CURVES_BY_KEY = by_key
    return _CURVES_BY_KEY


def _coerce_params(params):
    return (ZZ(params["N"]), ZZ(params["c4"]), ZZ(params["c6"]))


def period_lattice_area(curve, bits):
    lattice = curve.period_lattice()
    real_field = RealBallField(bits)
    complex_field = ComplexBallField(bits)
    pi = real_field.pi()

    if lattice.real_flag == 1:
        a, b, c = [real_field(value) for value in lattice._abc]
        omega_1 = pi / a.agm(b)
        omega_2_imag = pi / a.agm(c)
        return omega_1 * omega_2_imag

    a = complex_field(lattice._abc[0])
    x = a.real().abs()
    y = a.imag().abs()
    r = a.abs()
    omega_1 = pi / r.agm(x)
    omega_2_imag = pi / r.agm(y)
    return omega_1 * omega_2_imag / real_field(2)


def faltings_height(curve, digits, stable=False):
    bits = numberdb.bits(digits, losing=WORKING_GUARD_BITS)
    real_field = RealBallField(bits)
    height = -period_lattice_area(curve, bits).log() / real_field(2)
    if not stable:
        return height

    j = curve.j_invariant()
    denominator = real_field(ZZ(j.denominator()))
    discriminant = real_field(abs(ZZ(curve.discriminant())))
    return height + (denominator.log() - discriminant.log()) / real_field(12)


class FaltingsHeights(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T211")
    parameters = ("N", "c4", "c6", "quantity")
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self, max_conductor=MAX_CONDUCTOR):
        for record in curves(max_conductor):
            base = {
                "N": record["N"],
                "c4": record["c4"],
                "c6": record["c6"],
            }
            yield dict(base, quantity="h")
            if not record["curve"].is_semistable():
                yield dict(base, quantity="stable")

    def value(self, params, digits):
        record = curves_by_key()[_coerce_params(params)]
        value = faltings_height(record["curve"], digits,
                                stable=(params["quantity"] == "stable"))
        return {
            "number": value,
            "comment": (
                "HREF{%s}[LMFDB %s], Cremona label %s."
                % (record["lmfdb_url"], record["lmfdb_label"],
                   record["cremona_label"])
            ),
        }


if __name__ == "__main__":
    _key_from_stdin()
    generator = FaltingsHeights()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="Faltings heights for Sage mini Cremona curves, N <= %d"
                    % (MAX_CONDUCTOR,)))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
