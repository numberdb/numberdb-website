"""Displacement thickness of the Falkner-Skan wedge flows -- numberdb.org/T415

For each two-decimal wedge parameter beta on the upper branch, this stores the
dimensionless displacement thickness delta_1 in the wedge and Hartree
normalisations.

Run it with SageMath:

    $ sage -pip install numberdb scipy numpy
    $ sage -python generate.py
    $ sage -python generate.py --publish

The stored values are finite-interval boundary-value solves, checked against a
fixed-step RK4 shooting computation and against the rounded Hartree-profile
values tabulated by Schlichting and Gersten.
"""

import os
import sys
from math import exp, isfinite, sqrt

import numberdb.sage as numberdb
from sage.rings.rational_field import QQ

import numpy as np
from scipy.integrate import solve_bvp


TABLE = os.environ.get("NUMBERDB_TABLE", "T415")
DIGITS = 12
ETA_MAX = 40.0
POINTS = 500
SOLVE_TOL = 1e-10
MAX_NODES = 20000

NORMALISATIONS = ("wedge", "hartree")
BRANCH = "upper"
BETAS = tuple(QQ(n) / QQ(100) for n in range(-19, 200))
DISPLAY_BETAS = tuple(sorted(BETAS, key=lambda beta: (abs(beta), beta < 0)))

SCHLICHTING_HARTREE_DELTA1 = {
    QQ(-1) / QQ(10): 2.801 * 0.515,
    QQ(0): 2.591 * 0.470,
    QQ(1) / QQ(2): 2.297 * 0.350,
    QQ(1): 2.216 * 0.292,
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


def _display(value, digits=DIGITS):
    text = ("%%.%dg" % digits) % float(value)
    if "e" not in text and "." not in text:
        text += ".0"
    return text


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
        raise ArithmeticError("solve_bvp failed at beta=%s: %s"
                              % (beta, answer.message))
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
    for n in range(1, 200):
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
        wall_shear = float(solution.sol(np.array([0.0]))[2, 0])
        factor_to_wedge = sqrt(2.0 - _float(beta))
        out[str(beta)] = {
            "hartree": delta1_hartree,
            "wedge": delta1_hartree * factor_to_wedge,
            "delta2_hartree": delta2_hartree,
            "wall_shear_hartree": wall_shear,
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
    if beta == QQ(1):
        return "The Hiemenz plane stagnation-point flow."
    return ""


def _rk4(beta, wall_shear, eta_max=ETA_MAX, step=0.0001):
    b = _float(beta)
    n = int(round(eta_max / step))
    h = eta_max / n
    state = [0.0, 0.0, float(wall_shear), 0.0, 0.0]

    def deriv(values):
        f, fp, fpp, d1, d2 = values
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

    worst_rk4 = 0.0
    for beta in (QQ(-19) / QQ(100), QQ(-1) / QQ(10), QQ(0),
                 QQ(1) / QQ(2), QQ(1), QQ(3) / QQ(2), QQ(199) / QQ(100)):
        row = values[str(beta)]
        rk4 = _rk4(beta, row["wall_shear_hartree"])
        worst_rk4 = max(worst_rk4, abs(rk4[3] - row["hartree"]))
        print("beta=%s hartree=%s wedge=%s rk4-diff=%.3g" % (
            beta, _display(row["hartree"]), _display(row["wedge"]),
            abs(rk4[3] - row["hartree"])))

    worst_table = 0.0
    for beta, rounded in SCHLICHTING_HARTREE_DELTA1.items():
        diff = abs(values[str(beta)]["hartree"] - rounded)
        worst_table = max(worst_table, diff)
        print("Schlichting beta=%s diff=%.3g" % (beta, diff))

    worst_identity = 0.0
    for beta in BETAS:
        row = values[str(beta)]
        b = _float(beta)
        left = row["wall_shear_hartree"]
        right = b * row["hartree"] + (1 + b) * row["delta2_hartree"]
        worst_identity = max(worst_identity, abs(left - right))
    print("worst RK4 delta1 check: %.3g" % worst_rk4)
    print("worst second solve check: %.3g" % worst_second_solve)
    print("worst printed-table check: %.3g" % worst_table)
    print("worst momentum identity check: %.3g" % worst_identity)


class FalknerSkanDisplacementThickness(numberdb.Generator):
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
        beta = QQ(params["beta"])
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


if __name__ == "__main__":
    _key_from_stdin()
    generator = FalknerSkanDisplacementThickness()
    if "--check" in sys.argv or os.environ.get("NUMBERDB_CHECK") == "1":
        run_checks()
    elif os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="Falkner-Skan displacement thickness on the upper branch"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
