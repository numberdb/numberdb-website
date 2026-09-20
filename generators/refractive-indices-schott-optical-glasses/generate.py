"""Refractive indices of the Schott optical glasses -- numberdb.org/T367.

For each Schott optical glass and selected Fraunhofer spectral line, this
computes the refractive index relative to air from the Sellmeier coefficients
in the refractiveindex.info copy of the SCHOTT Zemax catalogue.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The source data used by this generator is the compact snapshot in
source_data.json, extracted from refractiveindex.info-database commit
c5c2f188e848453def5970e347399d653df2ffc2. Lower-case d-line entries use the
source file's printed nd value. The other line entries are rounded to five
decimal places, matching the line refractive indices printed in the Schott data
sheets.
"""

import json
import os
import sys
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP, getcontext
from pathlib import Path

try:
    import numberdb.sage as numberdb
except (ImportError, ModuleNotFoundError) as exc:
    if getattr(exc, "name", None) not in (None, "sage") \
            or "needs SageMath" not in str(exc):
        raise
    import numberdb

DIGITS = 6
DECIMAL_PLACES = Decimal("0.00001")
MAKER = "Schott"
DATA_FILE = Path(__file__).with_name("source_data.json")

LINE_WAVELENGTHS_NM = (
    ("g", Decimal("435.8343")),
    ("F", Decimal("486.1327")),
    ("e", Decimal("546.0740")),
    ("d", Decimal("587.5618")),
    ("C", Decimal("656.2725")),
    ("r", Decimal("706.5188")),
)

getcontext().prec = 50


def load_source():
    with DATA_FILE.open(encoding="utf8") as handle:
        return json.load(handle)


SOURCE = load_source()
RECORDS = {record["glass"]: record for record in SOURCE["glasses"]}


def coefficient_key(record):
    return tuple(record["coefficients"])


def named_list(names):
    names = list(names)
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return "%s and %s" % (names[0], names[1])
    return "%s and %s" % (", ".join(names[:-1]), names[-1])


def duplicate_comments():
    by_coefficients = defaultdict(list)
    for record in SOURCE["glasses"]:
        by_coefficients[coefficient_key(record)].append(record["glass"])

    comments = {}
    for names in by_coefficients.values():
        if len(names) == 1:
            continue
        text = (
            "The source gives the same dispersion coefficients for %s; "
            "the catalogue distinguishes these glass types by transmittance, "
            "not by dispersion."
        ) % named_list(names)
        for name in names:
            comments[name] = text
    return comments


DUPLICATE_COMMENTS = duplicate_comments()


def wavelength_um(line):
    for key, nm in LINE_WAVELENGTHS_NM:
        if key == line:
            return nm / Decimal(1000)
    raise KeyError(line)


def in_range(record, line):
    low, high = (Decimal(value) for value in record["wavelength_range_um"])
    wavelength = wavelength_um(line)
    return low <= wavelength <= high


def refractive_index(record, line):
    coeffs = [Decimal(value) for value in record["coefficients"]]
    x = wavelength_um(line)
    x2 = x * x
    n_squared = Decimal(1)
    for index in range(0, 6, 2):
        b = coeffs[index]
        c = coeffs[index + 1]
        n_squared += b * x2 / (x2 - c)
    return getcontext().sqrt(n_squared)


def rounded_index(record, line):
    value = refractive_index(record, line)
    return str(value.quantize(DECIMAL_PLACES, rounding=ROUND_HALF_UP))


def significant_digits(text):
    digits = [char for char in text if char.isdigit()]
    while digits and digits[0] == "0":
        digits.pop(0)
    return len(digits)


def source_nd_decimal_places(record):
    text = record.get("nd", "")
    mantissa = text.lower().split("e", 1)[0]
    if "." not in mantissa:
        return 0
    return len(mantissa.split(".", 1)[1])


def source_nd_text(record):
    places = source_nd_decimal_places(record)
    quantum = Decimal(1).scaleb(-places)
    value = Decimal(record["nd"])
    return str(value.quantize(quantum, rounding=ROUND_HALF_UP))


def computed_d_text_at_source_precision(record):
    places = source_nd_decimal_places(record)
    quantum = Decimal(1).scaleb(-places)
    value = refractive_index(record, "d")
    return str(value.quantize(quantum, rounding=ROUND_HALF_UP))


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("\"'")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


class SchottOpticalGlassRefractiveIndices(numberdb.Generator):
    table = "T367"
    parameters = ("maker", "glass", "line")
    type = "R"
    digits = DIGITS
    rigour = "measured"
    files = ("generate.py", "source_data.json")

    def enumerate(self):
        for record in SOURCE["glasses"]:
            for line, _nm in LINE_WAVELENGTHS_NM:
                if in_range(record, line):
                    yield {
                        "maker": MAKER,
                        "glass": record["glass"],
                        "line": line,
                    }

    def value(self, params, digits):
        record = RECORDS[str(params["glass"])]
        line = str(params["line"])
        text = source_nd_text(record) if line == "d" else rounded_index(record, line)
        entry = {"number": text, "digits": significant_digits(text)}
        comment = DUPLICATE_COMMENTS.get(record["glass"])
        if comment:
            entry["comment"] = comment
        return entry


def check_d_line_against_source_nd():
    disagreements = []
    for record in SOURCE["glasses"]:
        computed = computed_d_text_at_source_precision(record)
        printed = source_nd_text(record)
        if Decimal(computed) != Decimal(printed):
            disagreements.append((record["glass"], printed, computed))
    return disagreements


if __name__ == "__main__":
    _key_from_stdin()
    generator = SchottOpticalGlassRefractiveIndices()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="computed Schott optical glass refractive indices",
            removing=True))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
