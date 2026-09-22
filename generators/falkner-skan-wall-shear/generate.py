"""Wall shear of the Falkner-Skan wedge flows -- numberdb.org/T418.

For each two-decimal Hartree pressure-gradient parameter beta on the upper
branch, this stores the wall shear f''(0) in the Hartree and wedge
normalisations.

Run it with SageMath:

    $ sage -pip install numberdb scipy numpy
    $ sage -python generate.py
    $ sage -python generate.py --publish

The stored values are finite-interval boundary-value solves, checked against a
fixed-step RK4 shooting computation, Toepfer's Blasius scaling, and rounded
values from Asaithambi's Falkner-Skan review.
"""

import os
import sys
from math import isfinite, sqrt

import numberdb.sage as numberdb
from sage.rings.rational_field import QQ

import numpy as np
from scipy.integrate import solve_bvp


TABLE = os.environ.get("NUMBERDB_TABLE", "T418")
DIGITS = 12
ETA_MAX = 40.0
POINTS = 500
SOLVE_TOL = 1e-10
MAX_NODES = 20000

NORMALISATIONS = ("hartree", "wedge")
BRANCH = "upper"
BETAS = tuple(QQ(n) / QQ(100) for n in range(-19, 134))
DISPLAY_BETAS = tuple(sorted(BETAS, key=lambda beta: (abs(beta), beta < 0)))

BLASIUS_HARTREE = 0.469599988361
ASAITHAMBI_HARTREE_SHEAR = {
    QQ(0): 0.469600,
    QQ(1) / QQ(2): 0.927680,
    QQ(1): 1.232588,
}

_CACHE = None


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _float(beta):
    return float(beta.numerator()) / float(beta.denominator())


def _rational_from_text(text):
    text = str(text)
    if "/" in text:
        numerator, denominator = text.split("/", 1)
        return QQ(int(numerator)) / QQ(int(denominator))
    return QQ(int(text))


def _display(value, digits=DIGITS):
    text = ("%%.%dg" % digits) % float(value)
    if "e" in text or "E" in text:
        mantissa, exponent = text.lower().split("e", 1)
        mantissa = _pad_significant_digits(mantissa, digits)
        return mantissa + "e" + exponent
    text = _pad_significant_digits(text, digits)
    if "." not in text:
        text += "."
    return text


def _pad_significant_digits(text, digits):
    sign = ""
    if text.startswith("-"):
        sign = "-"
        text = text[1:]
    if "." not in text:
        text += "."

    def count_significant(body):
        started = False
        count = 0
        for char in body:
            if char == ".":
                continue
            if char != "0":
                started = True
            if started:
                count += 1
        return count

    while count_significant(text) < digits:
        text += "0"
    return sign + text


def _initial_guess(x):
    tail = np.exp(-x)
    fp = 1 - tail
    f = x + tail - 1
    fpp = tail
    d1 = 1 - tail
    d2 = 0.5 - tail + 0.5 * tail * tail
    return np.vstack((f, fp, fpp, d1, d2))


def _solve(beta, previous=None, points=POINTS, tol=SOLVE_TOL):
    b = _float(beta)
    x = np.linspace(0.0, ETA_MAX, points)
    y = previous.sol(x) if previous is not None else _initial_guess(x)

    def ode(_x, y):
        f = y[0]
        fp = y[1]
        fpp = y[2]
        return np.vstack((
            fp,
            fpp,
            -f * fpp - b * (1 - fp * fp),
            1 - fp,
            fp * (1 - fp),
        ))

    def bc(left, right):
        return np.array((left[0], left[1], left[3], left[4], right[1] - 1))

    answer = solve_bvp(
        ode,
        bc,
        x,
        y,
        tol=tol,
        max_nodes=MAX_NODES,
        verbose=0,
    )
    if not answer.success:
        raise ArithmeticError(
            "solve_bvp failed at beta=%s: %s" % (beta, answer.message)
        )
    values = answer.sol(np.array([ETA_MAX]))[:, 0]
    if not all(isfinite(float(v)) for v in values):
        raise ArithmeticError("non-finite solution at beta=%s" % (beta,))
    return answer


def _compute_all(points=POINTS, tol=SOLVE_TOL):
    solutions = {}

    zero = QQ(0)
    zero_solution = _solve(zero, None, points=points, tol=tol)
    solutions[zero] = zero_solution

    previous = zero_solution
    for n in range(1, 134):
        beta = QQ(n) / QQ(100)
        previous = _solve(beta, previous, points=points, tol=tol)
        solutions[beta] = previous

    previous = zero_solution
    for n in range(-1, -20, -1):
        beta = QQ(n) / QQ(100)
        previous = _solve(beta, previous, points=points, tol=tol)
        solutions[beta] = previous

    out = {}
    for beta, solution in solutions.items():
        state = solution.sol(np.array([ETA_MAX]))[:, 0]
        delta1_hartree = float(state[3])
        delta2_hartree = float(state[4])
        wall_shear_hartree = float(solution.sol(np.array([0.0]))[2, 0])
        factor_to_wedge = sqrt(2.0 - _float(beta))
        out[str(beta)] = {
            "hartree": wall_shear_hartree,
            "wedge": wall_shear_hartree / factor_to_wedge,
            "delta1_hartree": delta1_hartree,
            "delta2_hartree": delta2_hartree,
        }
    return out


def _cache():
    global _CACHE
    if _CACHE is None:
        _CACHE = _compute_all()
    return _CACHE


def _comment(beta):
    if beta == QQ(0):
        return "The Blasius flat-plate boundary layer."
    if beta == QQ(1) / QQ(2):
        return "The right-angle wedge case."
    if beta == QQ(1):
        return "The Hiemenz plane stagnation-point flow."
    return ""


def _rk4(beta, wall_shear, eta_max=ETA_MAX, step=0.0002):
    b = _float(beta)
    n = int(round(eta_max / step))
    h = eta_max / n
    state = [0.0, 0.0, float(wall_shear), 0.0, 0.0]

    def deriv(values):
        f, fp, fpp, _d1, _d2 = values
        return [
            fp,
            fpp,
            -f * fpp - b * (1 - fp * fp),
            1 - fp,
            fp * (1 - fp),
        ]

    for _ in range(n):
        k1 = deriv(state)
        k2 = deriv([state[i] + h * k1[i] / 2 for i in range(5)])
        k3 = deriv([state[i] + h * k2[i] / 2 for i in range(5)])
        k4 = deriv([state[i] + h * k3[i] for i in range(5)])
        state = [
            state[i] + h * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]) / 6
            for i in range(5)
        ]
    return state


def run_checks():
    values = _cache()
    comparison = _compute_all(points=240, tol=1e-8)
    worst_second_solve = 0.0
    for beta in BETAS:
        first = values[str(beta)]
        second = comparison[str(beta)]
        for normalisation in NORMALISATIONS:
            worst_second_solve = max(
                worst_second_solve,
                abs(first[normalisation] - second[normalisation]),
            )

    worst_rk4_endpoint = 0.0
    worst_rk4_identity = 0.0
    for beta in (QQ(-19) / QQ(100), QQ(-1) / QQ(10), QQ(0),
                 QQ(1) / QQ(2), QQ(1), QQ(133) / QQ(100)):
        row = values[str(beta)]
        rk4 = _rk4(beta, row["hartree"])
        b = _float(beta)
        identity = b * rk4[3] + (1 + b) * rk4[4]
        worst_rk4_endpoint = max(worst_rk4_endpoint, abs(rk4[1] - 1.0))
        worst_rk4_identity = max(worst_rk4_identity,
                                 abs(identity - row["hartree"]))
        print("beta=%s hartree=%s wedge=%s rk4-fp-tail=%.3g" % (
            beta, _display(row["hartree"]), _display(row["wedge"]),
            abs(rk4[1] - 1.0)))

    blasius_diff = abs(values[str(QQ(0))]["hartree"] - BLASIUS_HARTREE)
    print("Blasius Hartree diff=%.3g" % blasius_diff)
    if blasius_diff > 5e-12:
        raise ArithmeticError("Blasius row failed the Toepfer-scaling value")

    worst_table = 0.0
    for beta, rounded in ASAITHAMBI_HARTREE_SHEAR.items():
        diff = abs(values[str(beta)]["hartree"] - rounded)
        worst_table = max(worst_table, diff)
        print("Asaithambi beta=%s diff=%.3g" % (beta, diff))
        if diff > 5e-7:
            raise ArithmeticError("Asaithambi check failed at beta=%s" % beta)

    worst_identity = 0.0
    for beta in BETAS:
        row = values[str(beta)]
        b = _float(beta)
        left = row["hartree"]
        right = b * row["delta1_hartree"] + (1 + b) * row["delta2_hartree"]
        worst_identity = max(worst_identity, abs(left - right))

    print("worst RK4 endpoint check: %.3g" % worst_rk4_endpoint)
    print("worst RK4 momentum identity check: %.3g" % worst_rk4_identity)
    print("worst second solve check: %.3g" % worst_second_solve)
    print("worst printed-table check: %.3g" % worst_table)
    print("worst collocation momentum identity check: %.3g" % worst_identity)
    if worst_second_solve > 5e-9:
        raise ArithmeticError("second solve disagreement is too large")
    if worst_rk4_endpoint > 5e-8:
        raise ArithmeticError("RK4 endpoint check is too large")
    if worst_identity > 5e-9:
        raise ArithmeticError("momentum identity check is too large")


class FalknerSkanWallShear(numberdb.Generator):
    table = TABLE
    parameters = ("beta", "branch", "normalisation")
    type = "R"
    digits = DIGITS
    rigour = "heuristic (agreement-checked)"

    def enumerate(self):
        for beta in DISPLAY_BETAS:
            for normalisation in NORMALISATIONS:
                yield {
                    "beta": str(beta),
                    "branch": BRANCH,
                    "normalisation": normalisation,
                }

    def value(self, params, digits):
        beta = _rational_from_text(params["beta"])
        if params["branch"] != BRANCH:
            raise ValueError("only the upper branch is filled")
        normalisation = params["normalisation"]
        if normalisation not in NORMALISATIONS:
            raise ValueError("unknown normalisation %r" % (normalisation,))
        row = _cache()[str(beta)]
        entry = {"number": _display(row[normalisation], digits)}
        comment = _comment(beta)
        if comment:
            entry["comment"] = comment
        return entry


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
    generator = FalknerSkanWallShear()
    if "--check" in sys.argv or os.environ.get("NUMBERDB_CHECK") == "1":
        run_checks()
    elif os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="Falkner-Skan wall shear on the upper branch",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
