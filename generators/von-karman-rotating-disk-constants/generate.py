"""Constants of the von Karman rotating-disk flow -- numberdb.org/T421

This fills the three classical characteristic constants of the von Karman
similarity solution for flow above an infinite rotating disk: F'(0), G'(0) and
-H(infinity).

Run it with SageMath:

    $ sage -pip install numberdb mpmath          # once
    $ sage -python generate.py                   # check the table
    $ sage -python generate.py --publish         # fill the draft

For this repository's build environment, use:

    $ agents/sage.sh generate.py
    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
        agents/sage.sh generate.py

The computation shoots on F'(0), G'(0) and c=-H(infinity). At the finite
endpoint it imposes the linear far-field conditions F' + cF = 0 and
G' + cG = 0, together with H + c - 2F/c = 0 from H'=-2F. The 30 stored digits
must agree between two working precisions and with printed benchmark constants.
"""

import os
import sys
import gc

import numberdb.sage as numberdb

from mpmath import mp


TABLE = "T421"
DIGITS = 30
ETA_MAX_TEXT = "45"
LOW_EXTRA_DIGITS = 20
HIGH_EXTRA_DIGITS = 30

CONSTANTS = ("radial-shear", "azimuthal-shear", "axial-inflow")
BENCHMARKS = {
    "radial-shear": ("0.510232618867", "5e-13", "1"),
    "azimuthal-shear": ("-0.615922014399", "5e-13", "1"),
    # Miklavcic and Wang print k/2=0.442237055104 for the no-slip case.
    "axial-inflow": ("0.442237055104", "2e-12", "0.5"),
}

_CACHE = {}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _format_decimal(value, digits):
    return mp.nstr(
        value,
        n=digits,
        strip_zeros=False,
        min_fixed=-100,
        max_fixed=100,
    )


def _integrate(radial_shear, azimuthal_shear, dps):
    mp.dps = dps
    eta_max = mp.mpf(ETA_MAX_TEXT)
    radial_shear = mp.mpf(radial_shear)
    azimuthal_shear = mp.mpf(azimuthal_shear)

    def rhs(_eta, state):
        f, fp, g, gp, h = state
        return [
            fp,
            f * f - g * g + h * fp,
            gp,
            2 * f * g + h * gp,
            -2 * f,
        ]

    solution = mp.odefun(
        rhs,
        mp.mpf("0"),
        (mp.mpf("0"), radial_shear, mp.mpf("1"), azimuthal_shear, mp.mpf("0")),
        tol=mp.mpf(10) ** (-(dps - 10)),
        degree=30,
    )
    value = solution(eta_max)
    del solution
    gc.collect()
    return value


def _residuals(radial_shear, azimuthal_shear, axial_inflow, dps):
    f, fp, g, gp, h = _integrate(radial_shear, azimuthal_shear, dps)
    c = mp.mpf(axial_inflow)
    return (
        fp + c * f,
        gp + c * g,
        h + c - 2 * f / c,
    )


def _solve(dps, seed=None):
    mp.dps = dps
    if seed is None:
        seed = (mp.mpf("0.51023262"), mp.mpf("-0.61592201"), mp.mpf("0.88447410"))
    else:
        seed = tuple(mp.mpf(value) for value in seed)

    cached_at = None
    cached_value = None

    def residuals(a, b, c):
        nonlocal cached_at, cached_value
        point = (a, b, c)
        if cached_at != point:
            cached_at = point
            cached_value = _residuals(a, b, c, dps)
        return cached_value

    def r1(a, b, c):
        return residuals(a, b, c)[0]

    def r2(a, b, c):
        return residuals(a, b, c)[1]

    def r3(a, b, c):
        return residuals(a, b, c)[2]

    radial_shear, azimuthal_shear, axial_inflow = mp.findroot(
        (r1, r2, r3),
        seed,
        tol=mp.mpf(10) ** (-(dps - 16)),
        maxsteps=20,
    )
    residual = max(abs(part) for part in _residuals(
        radial_shear, azimuthal_shear, axial_inflow, dps))
    if residual > mp.mpf(10) ** (-(dps - 18)):
        raise ArithmeticError(
            "shooting residual too large at dps %d: %s"
            % (dps, mp.nstr(residual, 8))
        )
    return {
        "radial-shear": radial_shear,
        "azimuthal-shear": azimuthal_shear,
        "axial-inflow": axial_inflow,
    }


def _values_for_digits(digits):
    low_dps = digits + LOW_EXTRA_DIGITS
    high_dps = digits + HIGH_EXTRA_DIGITS
    low = _solve(low_dps)
    high = _solve(high_dps, seed=(
        low["radial-shear"],
        low["azimuthal-shear"],
        low["axial-inflow"],
    ))

    values = {}
    for name in CONSTANTS:
        low_text = _format_decimal(low[name], digits)
        high_text = _format_decimal(high[name], digits)
        if low_text != high_text:
            raise ArithmeticError(
                "%s disagrees between working precisions: %s vs %s"
                % (name, low_text, high_text)
            )
        benchmark, tolerance, scale = BENCHMARKS[name]
        observed = high[name] * mp.mpf(scale)
        if abs(observed - mp.mpf(benchmark)) > mp.mpf(tolerance):
            raise ArithmeticError(
                "%s does not match printed benchmark %s within %s: %s"
                % (name, benchmark, tolerance, _format_decimal(observed, digits))
            )
        values[name] = high_text
    return values


def _ensure_cache(digits):
    if digits not in _CACHE:
        _CACHE[digits] = _values_for_digits(digits)
    return _CACHE[digits]


class VonKarmanRotatingDiskConstants(numberdb.Generator):
    table = os.environ.get("NUMBERDB_TABLE", TABLE)
    parameters = ("constant",)
    type = "R"
    digits = DIGITS
    rigour = "heuristic (agreement-checked)"

    def enumerate(self):
        for constant in CONSTANTS:
            yield {"constant": constant}

    def value(self, params, digits):
        constant = params["constant"]
        if constant not in CONSTANTS:
            raise ValueError("unknown constant %r" % (constant,))
        return _ensure_cache(digits)[constant]


def self_check(digits=DIGITS):
    values = _ensure_cache(digits)
    print("self-check passed for %d constants" % (len(values),))
    for name in CONSTANTS:
        print("%s: %s" % (name, values[name]))


if __name__ == "__main__":
    _key_from_stdin()
    generator = VonKarmanRotatingDiskConstants()
    mode = os.environ.get("NUMBERDB_PUBLISH")
    if mode == "1" or "--publish" in sys.argv:
        print(generator.publish(message="computed von Karman rotating-disk constants"))
    elif mode == "preview" or "--preview" in sys.argv:
        print(generator.preview())
    else:
        self_check(generator.digits)
        if os.environ.get("NUMBERDB_API_KEY"):
            report = generator.verify(sample=None)
            print(report)
            sys.exit(0 if report.ok else 1)
        print("NUMBERDB_API_KEY is not set, so verify() was skipped")
