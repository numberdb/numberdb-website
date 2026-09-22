"""Momentum thickness $\\delta_2$ of the Falkner-Skan wedge flows -- numberdb.org/T419.

For the upper-branch Falkner-Skan solution in Hartree's normalisation,

    f''' + f f'' + beta (1 - (f')^2) = 0,
    f(0) = f'(0) = 0, f'(infinity) = 1,

this generator stores the dimensionless momentum thickness

    delta_2 = integral_0^infinity f'(eta) (1 - f'(eta)) d eta

on the two-decimal beta grid. It stores both the Hartree coordinate and the
wedge coordinate. The conversion is

    delta_2,wedge = sqrt(2 - beta) delta_2,Hartree.

The endpoint beta = 2 is omitted because that conversion is singular there.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The values are heuristic agreement-checked numbers. Each stored value is the
union of two adaptive DOP853 shooting computations with different tolerances
and cutoffs. The generator also checks the momentum-integral identity and the
Blasius row from Toepfer's scaling before it sends entries.
"""

import math
import os
import sys

import numberdb.sage as numberdb
from sage.rings.rational_field import QQ

from scipy.integrate import solve_ivp
from scipy.optimize import brentq


TABLE = os.environ.get("NUMBERDB_TABLE", "T419")

DIGITS = 10

RUNS = {
    40: {"eta_max": 18.0, "rtol": 2e-11, "atol": 2e-13, "xtol": 2e-13},
    50: {"eta_max": 20.0, "rtol": 2e-12, "atol": 2e-14, "xtol": 5e-14},
}

IDENTITY_TOL = 5e-8
BLASIUS_TOL = 5e-9


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _q_to_float(value):
    rational = QQ(value)
    return float(rational.numerator()) / float(rational.denominator())


def _q_to_key(value):
    return str(QQ(value))


def _beta_grid():
    return [QQ(n) / QQ(100) for n in range(-19, 101)]


def _display_grid():
    def order(beta):
        return (abs(beta), 0 if beta >= 0 else 1, beta)

    return sorted(_beta_grid(), key=order)


def _decimal(value):
    text = format(value, ".17g")
    if "e" not in text and "." not in text:
        text += ".0"
    return text


def _integrate(beta, shear, eta_max, rtol, atol):
    def rhs(_eta, state):
        f, velocity, curvature, _delta1, _delta2 = state
        one_minus_velocity = 1.0 - velocity
        return [
            velocity,
            curvature,
            -f * curvature - beta * (1.0 - velocity * velocity),
            one_minus_velocity,
            velocity * one_minus_velocity,
        ]

    solution = solve_ivp(
        rhs,
        (0.0, eta_max),
        [0.0, 0.0, shear, 0.0, 0.0],
        method="DOP853",
        rtol=rtol,
        atol=atol,
    )
    if not solution.success:
        raise RuntimeError(solution.message)
    return solution.y[:, -1]


def _residual(beta, shear, config):
    row = _integrate(beta, shear, config["eta_max"], config["rtol"], config["atol"])
    residual = row[1] - 1.0
    if not math.isfinite(residual):
        raise RuntimeError("non-finite shooting residual")
    return residual


def _try_residual(beta, shear, config):
    try:
        return _residual(beta, shear, config)
    except Exception:
        return None


def _scan_bracket(beta, config):
    candidates = [
        0.0, 0.002, 0.005, 0.01, 0.02, 0.04, 0.07, 0.10, 0.15,
        0.22, 0.32, 0.46, 0.65, 0.90, 1.25, 1.75, 2.5, 3.5, 5.0,
    ]
    seen = []
    for shear in candidates:
        residual = _try_residual(beta, shear, config)
        if residual is not None and math.isfinite(residual):
            seen.append((shear, residual))
    brackets = []
    for (left, f_left), (right, f_right) in zip(seen, seen[1:]):
        if f_left == 0:
            return left, left
        if f_left < 0 < f_right:
            brackets.append((left, right))
    if not brackets:
        raise RuntimeError("could not bracket upper branch at beta=%s" % beta)
    return brackets[-1]


def _continuation_bracket(beta, previous, config):
    if previous is None:
        return _scan_bracket(beta, config)

    lo = max(0.0, previous)
    hi = previous * 1.12 + 0.08
    for _ in range(12):
        f_lo = _try_residual(beta, lo, config)
        f_hi = _try_residual(beta, hi, config)
        if f_lo is not None and f_hi is not None and f_lo < 0 < f_hi:
            return lo, hi
        if f_lo is not None and f_lo >= 0:
            hi = lo
            lo = max(0.0, lo * 0.95 - 0.02)
            continue
        hi = hi * 1.35 + 0.05
    return _scan_bracket(beta, config)


def _solve_shear(beta, previous, config):
    lo, hi = _continuation_bracket(beta, previous, config)
    if lo == hi:
        return lo
    f_lo = _residual(beta, lo, config)
    f_hi = _residual(beta, hi, config)
    if not (f_lo < 0 < f_hi):
        raise RuntimeError("bad bracket at beta=%s: %s, %s" % (beta, f_lo, f_hi))
    return brentq(
        lambda shear: _residual(beta, shear, config),
        lo,
        hi,
        xtol=config["xtol"],
        rtol=config["xtol"],
        maxiter=80,
    )


def _compute_grid(config):
    by_beta = {}
    previous = None
    for beta_q in _beta_grid():
        beta = _q_to_float(beta_q)
        previous = _solve_shear(beta, previous, config)
        row = _integrate(beta, previous, config["eta_max"], config["rtol"], config["atol"])
        shear = previous
        delta1_hartree = row[3]
        delta2_hartree = row[4]
        identity = beta * delta1_hartree + (1.0 + beta) * delta2_hartree
        if abs(identity - shear) > IDENTITY_TOL:
            raise RuntimeError(
                "momentum identity failed at beta=%s: %.3e"
                % (_q_to_key(beta_q), abs(identity - shear))
            )
        by_beta[_q_to_key(beta_q)] = {
            "shear": shear,
            "delta1_hartree": delta1_hartree,
            "delta2_hartree": delta2_hartree,
            "delta2_wedge": math.sqrt(2.0 - beta) * delta2_hartree,
        }
    return by_beta


def _topfer_blasius_hartree(config):
    # Hartree's beta=0 equation, normalised with F''(0)=1.
    row = _integrate(0.0, 1.0, config["eta_max"], config["rtol"], config["atol"])
    return row[1] ** -1.5


def _entry_comment(beta, normalisation):
    if beta == "0":
        if normalisation == "hartree":
            return (
                r"This is the Blasius boundary layer. In Hartree's "
                r"normalisation the momentum thickness equals $f''(0)$."
            )
        return (
            r"This is the Blasius boundary layer. In the wedge normalisation "
            r"$\delta_2=2f''(0)$."
        )
    if beta == "1":
        return r"This is the Hiemenz plane stagnation-point flow."
    if beta == "1/2":
        return r"This is the wedge with included angle $\pi/2$."
    return None


class FalknerSkanMomentumThickness(numberdb.Generator):

    table = TABLE
    parameters = ("beta", "branch", "normalisation")
    type = "R"
    digits = DIGITS
    rigour = "heuristic (agreement-checked)"

    def __init__(self):
        self._cache = {}
        self._checked_blasius = False

    def enumerate(self):
        for beta in _display_grid():
            for normalisation in ("wedge", "hartree"):
                yield {
                    "beta": _q_to_key(beta),
                    "branch": "upper",
                    "normalisation": normalisation,
                }

    def _grid(self, working):
        if working not in self._cache:
            self._cache[working] = _compute_grid(RUNS[working])
        return self._cache[working]

    def _value_text(self, params, working):
        row = self._grid(working)[_q_to_key(params["beta"])]
        normalisation = params["normalisation"]
        if normalisation == "hartree":
            value = row["delta2_hartree"]
        elif normalisation == "wedge":
            value = row["delta2_wedge"]
        else:
            raise ValueError("unknown normalisation %r" % normalisation)
        return _decimal(value)

    def _check_blasius(self):
        if self._checked_blasius:
            return
        fine = max(RUNS)
        topfer = _topfer_blasius_hartree(RUNS[fine])
        row = self._grid(fine)["0"]["delta2_hartree"]
        if abs(topfer - row) > BLASIUS_TOL:
            raise RuntimeError(
                "Blasius Toepfer check failed: %.3e" % abs(topfer - row)
            )
        self._checked_blasius = True

    def value(self, params, digits):
        params = dict(params)
        self._check_blasius()
        value = numberdb.agreeing(
            lambda working: self._value_text(params, working),
            at=tuple(sorted(RUNS)),
        )
        comment = _entry_comment(_q_to_key(params["beta"]), params["normalisation"])
        if comment:
            return {"number": value, "comment": comment}
        return value


def fill_draft_once(generator, message):
    """Fill a fresh draft without the client's empty upsert probe."""
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

        written = to_text(value, entry.get("digits", wanted), generator.format)
        _check_precision(table, identity, written, entry.get("digits", wanted),
                         lowering=False)

        record = dict(entry)
        record.pop("digits", None)
        entries.add(**params, **record, digits=entry.get("digits", wanted))

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
    generator = FalknerSkanMomentumThickness()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message=(
                "Falkner-Skan upper-branch momentum thicknesses on the "
                "two-decimal beta grid, checked by paired DOP853 integrations"
            ),
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
