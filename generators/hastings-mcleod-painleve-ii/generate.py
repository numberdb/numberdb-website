"""Values of the Hastings-McLeod solution q(s) of Painleve II -- numberdb.org/T443.

This generator fills T443 with values of the Hastings-McLeod solution
q''(s) = s q(s) + 2 q(s)^3, q(s) ~ Ai(s) as s -> +infinity, for every
two-decimal argument -8.00 <= s <= 2.00.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The values are measured, not proven. The primary computation is a SciPy
collocation boundary-value solve of Painleve II on [-20, 8], with the left
Hastings-McLeod asymptotic and the right Airy value as boundary conditions.
An independent check computes q(s) as [(I-K_Ai)^(-1) Ai](s), using a
Gauss-Legendre Nystrom discretisation of the Airy kernel on (s, infinity).
Each row keeps only the significant digits left after the two computations are
compared and two guard digits are discarded.
"""

import math
import os
import sys

import numberdb.sage as numberdb
import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.integrate import solve_bvp
from scipy.linalg import solve
from scipy.special import airy
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ


TABLE = os.environ.get("NUMBERDB_TABLE", "T443")

MIN_CENTS = -800
MAX_CENTS = 200
BVP_LEFT = -20.0
BVP_RIGHT = 8.0
BVP_MESH_POINTS = 700
BVP_TOLERANCE = 1e-10
BVP_MAX_NODES = 30000

FREDHOLM_ORDER = 120
FREDHOLM_SCALE = 10.0

MAX_DIGITS = 10
SAFETY_DIGITS = 2
MIN_DIGITS = 4

_TABLE_CACHE = None


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def _arguments():
    for cents in range(MIN_CENTS, MAX_CENTS + 1):
        yield cents, QQ(cents) / QQ(100)


def _left_asymptotic(x):
    x = np.asarray(x, dtype=float)
    series = (
        1.0
        + 1.0 / (8.0 * x ** 3)
        - 73.0 / (128.0 * x ** 6)
        + 10657.0 / (1024.0 * x ** 9)
    )
    return np.sqrt(-x / 2.0) * series


def _left_asymptotic_derivative(x):
    x = np.asarray(x, dtype=float)
    coeffs = (
        (1.0, 0),
        (1.0 / 8.0, -3),
        (-73.0 / 128.0, -6),
        (10657.0 / 1024.0, -9),
    )
    base = np.sqrt(-x / 2.0)
    base_derivative = -1.0 / (4.0 * base)
    series = sum(coefficient * x ** exponent for coefficient, exponent in coeffs)
    series_derivative = sum(
        coefficient * exponent * x ** (exponent - 1)
        for coefficient, exponent in coeffs
        if exponent
    )
    return base_derivative * series + base * series_derivative


def _painleve_ii(_x, y):
    return np.vstack((y[1], _x * y[0] + 2.0 * y[0] ** 3))


def _boundary_conditions(left, right):
    return np.array([
        left[0] - _left_asymptotic(BVP_LEFT),
        right[0] - airy(BVP_RIGHT)[0],
    ])


def _bvp_solution():
    mesh = np.linspace(BVP_LEFT, BVP_RIGHT, BVP_MESH_POINTS)
    airy_value, airy_derivative, _, _ = airy(mesh)

    q_guess = airy_value.copy()
    p_guess = airy_derivative.copy()
    left_mask = mesh < -2.0
    q_guess[left_mask] = _left_asymptotic(mesh[left_mask])
    p_guess[left_mask] = _left_asymptotic_derivative(mesh[left_mask])

    solution = solve_bvp(
        _painleve_ii,
        _boundary_conditions,
        mesh,
        np.vstack((q_guess, p_guess)),
        tol=BVP_TOLERANCE,
        max_nodes=BVP_MAX_NODES,
    )
    if not solution.success:
        raise ArithmeticError("Painleve II BVP failed: %s" % solution.message)
    return solution


def _airy_kernel(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    ai_x, aip_x, _, _ = airy(x)
    ai_y, aip_y, _, _ = airy(y)
    denominator = x - y
    with np.errstate(invalid="ignore", divide="ignore"):
        kernel = (ai_x * aip_y - aip_x * ai_y) / denominator
    same = np.isclose(denominator, 0.0)
    if np.any(same):
        x_broadcast = x + np.zeros_like(kernel)
        ai_broadcast = ai_x + np.zeros_like(kernel)
        aip_broadcast = aip_x + np.zeros_like(kernel)
        diagonal = aip_broadcast ** 2 - x_broadcast * ai_broadcast ** 2
        kernel = np.where(same, diagonal, kernel)
    return kernel


def _fredholm_q(s):
    nodes, weights = leggauss(FREDHOLM_ORDER)
    u = 0.5 * (nodes + 1.0)
    u_weights = 0.5 * weights
    x = s + FREDHOLM_SCALE * u / (1.0 - u)
    x_weights = u_weights * FREDHOLM_SCALE / (1.0 - u) ** 2

    ai, _, _, _ = airy(x)
    kernel = _airy_kernel(x[:, None], x[None, :])
    matrix = np.eye(FREDHOLM_ORDER) - kernel * x_weights[None, :]
    q_at_nodes = solve(matrix, ai, assume_a="gen")

    endpoint_kernel = _airy_kernel(np.full_like(x, s), x)
    return float(airy(s)[0] + np.dot(endpoint_kernel * x_weights, q_at_nodes))


def _kept_digits(primary, check):
    difference = abs(primary - check)
    if difference == 0:
        agreed = MAX_DIGITS + SAFETY_DIGITS
    else:
        scale = max(abs(primary), abs(check), 1e-300)
        agreed = math.floor(-math.log10(difference / scale))
    keep = min(MAX_DIGITS, agreed - SAFETY_DIGITS)
    if keep < MIN_DIGITS:
        raise ArithmeticError(
            "only %d digits agreed for q=%r against %r" % (agreed, primary, check)
        )
    return keep


def _format_significant(value, digits):
    text = format(value, ".%dg" % digits)
    if "e" in text or "E" in text:
        text = np.format_float_positional(
            value, precision=digits, unique=False, fractional=False, trim="-"
        )
    if "." not in text:
        text += ".0"
    while _significant_digits_in(text) < digits:
        text += "0"
    return text


def _significant_digits_in(text):
    mantissa = text.lower().split("e", 1)[0].lstrip("-")
    seen_nonzero = False
    count = 0
    for character in mantissa:
        if not character.isdigit():
            continue
        if character != "0":
            seen_nonzero = True
        if seen_nonzero:
            count += 1
    return count


def _compute_table():
    global _TABLE_CACHE
    if _TABLE_CACHE is not None:
        return _TABLE_CACHE

    solution = _bvp_solution()
    records = {}
    for _cents, argument in _arguments():
        s = float(argument)
        primary = float(solution.sol(s)[0])
        check = _fredholm_q(s)
        digits = _kept_digits(primary, check)
        records[str(argument)] = {
            "number": _format_significant(primary, digits),
            "digits": digits,
            "bvp": primary,
            "fredholm": check,
        }

    _TABLE_CACHE = records
    return records


class HastingsMcLeodPainleveIIValues(numberdb.Generator):
    """Generator for T443, values of the Hastings-McLeod solution q(s)."""

    table = TABLE
    parameters = ("s",)
    type = "R"
    rigour = "measured"
    digits = MAX_DIGITS

    def enumerate(self):
        for _cents, argument in _arguments():
            yield {"s": str(argument)}

    def value(self, params, digits=None):
        record = _compute_table()[params["s"]]
        return {"number": record["number"], "digits": record["digits"]}

    def digits_for(self, params):
        return _compute_table()[params["s"]]["digits"]


def run_integrity_checks():
    records = _compute_table()
    digits = [record["digits"] for record in records.values()]
    print("computed %d Hastings-McLeod values" % len(records))
    print("digits kept: min %d, max %d" % (min(digits), max(digits)))
    for key in ("-8", "-7", "-6", "-4", "0", "2"):
        record = records[key]
        print(
            "q(%s) = %s, %d digits, BVP-Fredholm %.3g"
            % (
                key,
                record["number"],
                record["digits"],
                record["bvp"] - record["fredholm"],
            )
        )


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
    generator = HastingsMcLeodPainleveIIValues()
    run_integrity_checks()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="fill Hastings-McLeod Painleve II values checked by Airy-kernel Nystrom quadrature",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
