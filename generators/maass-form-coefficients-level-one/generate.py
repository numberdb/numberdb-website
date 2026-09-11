"""Fourier coefficients of Maass forms of level 1 -- numberdb.org/T218.

The table stores the prime Fourier coefficients a_p for the first ten
rigorous LMFDB level-one, weight-zero Maass cusp forms with trivial character.
The forms are ordered and labelled by the first five characters of their
positive spectral parameter, matching T84.

Run it with SageMath:

    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The LMFDB source gives each coefficient as a decimal centre with a rigorous
source radius. Both strings are parsed as exact rational numbers, and the
generator returns the corresponding Sage real interval.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_mpfi import RealIntervalField

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from maass_data import FORMS, PRIMES, WRITTEN_DIGITS  # noqa: E402


WORKING_GUARD = 64

_FORMS_BY_R = {record["R_key"]: record for record in FORMS}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def decimal_to_rational(text):
    """Parse a finite decimal or scientific-notation decimal exactly."""
    text = str(text).strip()
    if not text:
        raise ValueError("empty decimal")

    sign = 1
    if text[0] in "+-":
        if text[0] == "-":
            sign = -1
        text = text[1:]

    mantissa, marker, exponent = text.lower().partition("e")
    shift = int(exponent) if marker else 0
    if "." in mantissa:
        whole, fraction = mantissa.split(".", 1)
    else:
        whole, fraction = mantissa, ""
    if not whole:
        whole = "0"
    digits = whole + fraction
    if not digits.isdigit():
        raise ValueError("not a finite decimal: %s" % (text,))

    numerator = int(digits or "0")
    denominator = 10 ** len(fraction)
    if shift >= 0:
        numerator *= 10 ** shift
    else:
        denominator *= 10 ** (-shift)
    return QQ(sign * numerator) / QQ(denominator)


def decimal_unit(text, digits):
    """The value of the last written significant decimal place."""
    text = str(text).strip()
    if text and text[0] in "+-":
        text = text[1:]
    mantissa, marker, exponent = text.lower().partition("e")
    shift = int(exponent) if marker else 0
    if "." in mantissa:
        whole, fraction = mantissa.split(".", 1)
    else:
        whole, fraction = mantissa, ""
    decimal_position = len(whole)
    digits_only = whole + fraction
    first = None
    for index, digit in enumerate(digits_only):
        if digit != "0":
            first = index
            break
    if first is None:
        adjusted = 0
    else:
        adjusted = decimal_position - first - 1 + shift
    power = adjusted - int(digits) + 1
    if power >= 0:
        return QQ(10) ** power
    return QQ(1) / (QQ(10) ** (-power))


def source_interval(center, radius, digits, display_rounding=False):
    center_text = center
    center = decimal_to_rational(center)
    radius = decimal_to_rational(radius)
    if radius <= 0:
        raise ValueError("source radius must be positive")
    if display_rounding:
        radius += decimal_unit(center_text, digits)
    field = RealIntervalField(numberdb.bits(digits, losing=WORKING_GUARD))
    return field(center - radius, center + radius)


def form_url(record):
    return "https://www.lmfdb.org/ModularForm/GL2/Q/Maass/%s" % record["short_label"]


def fricke_text(sign):
    sign = ZZ(sign)
    return "+1" if sign > 0 else "-1"


def entry_comment(record):
    return (
        "LMFDB form HREF{%s}[%s] has %s symmetry and Fricke sign $%s$."
        % (
            form_url(record),
            record["label"],
            record["symmetry"],
            fricke_text(record["fricke_eigenvalue"]),
        )
    )


def hecke_pairs():
    """The composite source rows checked against the prime rows."""
    for i, p in enumerate(PRIMES):
        if p * p <= 1000:
            yield p, p, p * p
        for q in PRIMES[i + 1:]:
            if p * q <= 1000:
                yield p, q, p * q


def intervals_intersect(left, right):
    return not (left.upper() < right.lower() or right.upper() < left.lower())


def source_hecke_failures(digits=WRITTEN_DIGITS):
    """Return source Hecke-relation disagreements, if any."""
    failures = []
    field = RealIntervalField(numberdb.bits(digits, losing=WORKING_GUARD))
    for record in FORMS:
        prime_coefficients = {
            ZZ(p): source_interval(center, radius, digits)
            for p, (center, radius) in record["prime_coefficients"].items()
        }
        check_coefficients = {
            ZZ(n): source_interval(center, radius, digits)
            for n, (center, radius) in record["hecke_check_coefficients"].items()
        }
        for p, q, n in hecke_pairs():
            p = ZZ(p)
            q = ZZ(q)
            n = ZZ(n)
            if n not in check_coefficients:
                continue
            observed = check_coefficients[n]
            if p == q:
                predicted = prime_coefficients[p] ** 2 - field(1)
            else:
                predicted = prime_coefficients[p] * prime_coefficients[q]
            if not intervals_intersect(observed, predicted):
                failures.append((record["R_key"], int(n), observed, predicted))
    return failures


class MaassFormCoefficients(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T218")
    parameters = ("R", "p")
    type = "R"
    digits = WRITTEN_DIGITS
    rigour = "proven"
    #The house convention, and what 211 of the corpus's 219 documents hold:
    #the digits written are known and the last is uncertain by one. This table
    #wrote balls, and every one of its 150 radii was exactly one ulp of its own
    #last digit -- a radius recorded to say what the notation already says.
    #
    #`source_interval` adds one unit in the last written place when
    #`display_rounding` is set, which is there precisely so the decimal form
    #covers its own rounding, so the enclosure is as honest as it was before.
    #
    #Balls stay where the radius carries something: T3's thousand zeta zeros,
    #the measured constants in T10 and T12, the estimates in T157 and T171.
    format = "decimal"
    files = ("generate.py", "maass_data.py")

    def enumerate(self):
        for record in FORMS:
            for p in PRIMES:
                yield {"R": record["R_key"], "p": ZZ(p)}

    def value(self, params, digits):
        R_key = str(params["R"])
        p = ZZ(params["p"])
        record = _FORMS_BY_R[R_key]
        center, radius = record["prime_coefficients"][int(p)]
        entry = {"number": source_interval(
            center, radius, digits, display_rounding=True)}
        if p == 2:
            entry["comment"] = entry_comment(record)
        return entry


if __name__ == "__main__":
    _key_from_stdin()
    generator = MaassFormCoefficients()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="Maass form prime coefficients from LMFDB source intervals"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
