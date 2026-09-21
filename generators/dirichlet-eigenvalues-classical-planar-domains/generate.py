"""Dirichlet eigenvalues of the classical planar domains -- numberdb.org/T390.

This draft stores the first Dirichlet eigenvalue lambda_1(Omega) for each
domain listed in the table document. The sign convention is

    -Delta u = lambda u,      u|boundary = 0.

Run it with SageMath:

    $ sage -pip install numberdb
    $ sage -python generate.py
    $ sage -python generate.py --publish

For this repository's build environment, use:

    $ agents/sage.sh generate.py
    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 agents/sage.sh generate.py
"""

import os
import sys

import numberdb.sage as numberdb
import mpmath as mp


TABLE = os.environ.get("NUMBERDB_TABLE", "T390")
DIGITS = 30
WORKING_GUARD = 50

DOMAINS = (
    "unit-square",
    "rectangle-1x2",
    "unit-disk",
    "half-disk",
    "quarter-disk",
    "annulus-1-2",
    "sector-60",
    "equilateral-triangle",
    "right-isosceles-triangle",
    "hemiequilateral-triangle",
    "l-shape",
    "gww-drum-1",
    "gww-drum-2",
    "regular-pentagon",
    "regular-hexagon",
    "regular-heptagon",
    "regular-octagon",
)

L_SHAPE = (
    "9.6397238440219410527114592623648231562672895258219"
    "06456109579700564035647863370390722873165008796788"
)

GWW_FIRST = "2.53794399980"

REGULAR_POLYGON_AREA_PI = {
    5: (
        "6.0221379320426338782980087100542429670053053404485"
        "57982078846736673784801348686223580416426117672672"
    ),
    6: (
        "5.9174178316136612156885745768389615450082860040929"
        "34119040805009620004490361363223874041103755146850"
    ),
    7: (
        "5.8664493126559858577124749417588410842427349136980"
        "53784456012986066686011273838762976936742836505116"
    ),
    8: (
        "5.8384914335924428505166403795638157848367571520259"
        "62094176052525113941269462603724227921796589151583"
    ),
}

REGULAR_POLYGON_SIDES = {
    "regular-pentagon": 5,
    "regular-hexagon": 6,
    "regular-heptagon": 7,
    "regular-octagon": 8,
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def _set_precision(digits):
    mp.mp.dps = int(digits) + WORKING_GUARD


def _decimal(value, digits=DIGITS):
    text = mp.nstr(value, int(digits), strip_zeros=False)
    if "e" not in text.lower() and "." not in text:
        text += ".0"
    return text


def _annulus_root():
    def determinant(x):
        return (
            mp.besselj(0, x) * mp.bessely(0, 2 * x)
            - mp.besselj(0, 2 * x) * mp.bessely(0, x)
        )

    left = mp.mpf("3.0")
    right = mp.mpf("3.2")
    f_left = determinant(left)
    f_right = determinant(right)
    if f_left * f_right >= 0:
        raise ArithmeticError("annulus root bracket does not change sign")
    for _ in range(4 * mp.mp.dps):
        middle = (left + right) / 2
        f_middle = determinant(middle)
        if f_left * f_middle <= 0:
            right = middle
            f_right = f_middle
        else:
            left = middle
            f_left = f_middle
    root = (left + right) / 2
    if abs(determinant(root)) > mp.mpf(10) ** (-(mp.mp.dps // 2)):
        raise ArithmeticError("annulus root residual is too large")
    return root


def _regular_area(sides):
    s = mp.mpf(sides)
    return (s / 2) * mp.sin(2 * mp.pi / s)


def _first_value(domain):
    pi2 = mp.pi ** 2
    if domain == "unit-square":
        return 2 * pi2
    if domain == "rectangle-1x2":
        return mp.mpf(5) * pi2 / 4
    if domain == "unit-disk":
        return mp.besseljzero(0, 1) ** 2
    if domain == "half-disk":
        return mp.besseljzero(1, 1) ** 2
    if domain == "quarter-disk":
        return mp.besseljzero(2, 1) ** 2
    if domain == "annulus-1-2":
        return _annulus_root() ** 2
    if domain == "sector-60":
        return mp.besseljzero(3, 1) ** 2
    if domain == "equilateral-triangle":
        return 16 * pi2 / 3
    if domain == "right-isosceles-triangle":
        return 5 * pi2
    if domain == "hemiequilateral-triangle":
        return 112 * pi2 / 9
    if domain == "l-shape":
        return mp.mpf(L_SHAPE)
    if domain.startswith("gww-drum-"):
        return mp.mpf(GWW_FIRST)
    if domain in REGULAR_POLYGON_SIDES:
        sides = REGULAR_POLYGON_SIDES[domain]
        return mp.mpf(REGULAR_POLYGON_AREA_PI[sides]) * mp.pi / _regular_area(sides)
    raise KeyError(domain)


def _entry(domain, digits):
    value = _first_value(domain)
    if domain == "gww-drum-1":
        return {
            "number": GWW_FIRST,
            "digits": 12,
            "comment": "The first Gordon-Webb-Wolpert drum is isospectral to the second.",
        }
    if domain == "gww-drum-2":
        return {
            "number": GWW_FIRST,
            "digits": 12,
            "comment": "This equals the corresponding entry for the first Gordon-Webb-Wolpert drum.",
            "equals": "HREF{#gww-drum-1,1}[the first GWW drum entry]",
        }
    return _decimal(value, digits)


class DirichletEigenvaluesClassicalPlanarDomains(numberdb.Generator):
    table = TABLE
    parameters = ("domain", "n")
    type = "R"
    digits = DIGITS
    rigour = "heuristic (agreement-checked)"

    def enumerate(self):
        for domain in DOMAINS:
            yield {"domain": domain, "n": "1"}

    def value(self, params, digits):
        if params["n"] != "1":
            raise ValueError("this draft only stores n=1")
        _set_precision(digits)
        return _entry(params["domain"], digits)


def self_check():
    _set_precision(DIGITS)
    low = {domain: _decimal(_first_value(domain), DIGITS) for domain in DOMAINS}
    _set_precision(DIGITS + 30)
    high = {domain: _decimal(_first_value(domain), DIGITS) for domain in DOMAINS}
    for domain in DOMAINS:
        if domain.startswith("gww-drum-"):
            continue
        if low[domain] != high[domain]:
            raise ArithmeticError("%s changed with working precision" % (domain,))

    if not low["l-shape"].startswith("9.639723844021941"):
        raise ArithmeticError("L-shape value no longer matches the source prefix")
    hexagon = _decimal(_first_value("regular-hexagon"), 40)
    if not hexagon.startswith("7.1553391339260551282"):
        raise ArithmeticError("regular hexagon rescaling check failed")
    if _entry("gww-drum-1", DIGITS)["number"] != _entry("gww-drum-2", DIGITS)["number"]:
        raise ArithmeticError("GWW isospectral rows disagree")
    print("self-check passed: precision, L-shape source prefix, regular hexagon rescaling, and GWW equality")


def fill_draft_once(generator, message):
    """Fill a fresh draft without the empty upsert probe."""
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
        produced_by=_producer(
            generator,
            assisted_by=os.environ.get("NUMBERDB_ASSISTED_BY", "codex-cli"),
        ),
        upsert=False,
        run=run,
        rigour=generator.rigour,
    )

    stored = []
    for name, body in sorted(_source_files(generator).items()):
        attach(table, name, body, run=run, message=message,
               rigour=generator.rigour)
        stored.append(name)

    return {
        "tid": answer.get("tid", table),
        "revision": answer.get("revision"),
        "entries": len(entries),
        "files": stored,
    }


def main():
    _key_from_stdin()
    generator = DirichletEigenvaluesClassicalPlanarDomains()
    self_check()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="fundamental Dirichlet eigenvalues of classical planar domains"))
    elif os.environ.get("NUMBERDB_PUBLISH") == "preview" or "--preview" in sys.argv:
        print(generator.preview())
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
