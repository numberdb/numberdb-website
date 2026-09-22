"""Wall heat transfer of the thermal Falkner-Skan boundary layer -- numberdb.org/T417.

For the upper branch of the Falkner-Skan profile, this computes

    -theta'(0)

for the constant-property thermal boundary layer with uniform wall
temperature and no viscous dissipation.  The computation is made in Hartree
variables,

    f''' + f f'' + beta (1 - f'^2) = 0,
    theta'' + Pr f theta' = 0,

and then converted to the wedge normalisation by

    -theta'_wedge(0) = (2 - beta)^(-1/2) * [-theta'_Hartree(0)].

Run it under the repository's Sage wrapper:

    $ agents/sage.sh generators/thermal-falkner-skan-wall-heat-transfer/generate.py
    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
        agents/sage.sh generators/thermal-falkner-skan-wall-heat-transfer/generate.py
"""

from functools import lru_cache
from fractions import Fraction
import multiprocessing
import os
import sys

import numberdb.sage as numberdb
from mpmath import mp


TABLE = os.environ.get("NUMBERDB_TABLE", "T417")
DIGITS = 12
WORKING_DIGITS = (24, 30)
BRANCHES = ("upper",)
NORMALISATIONS = ("wedge", "hartree")

BETA_VALUES = tuple(
    sorted(
        [Fraction(-19, 100), Fraction(-1, 10)]
        + [Fraction(n, 10) for n in range(11)],
        key=lambda value: (abs(value), value < 0, value),
    )
)

PRANDTL_VALUES = (
    Fraction(1, 1000),
    Fraction(3, 1000),
    Fraction(1, 100),
    Fraction(3, 100),
    Fraction(1, 10),
    Fraction(3, 10),
    Fraction(3, 5),
    Fraction(7, 10),
    Fraction(18, 25),
    Fraction(1),
    Fraction(2),
    Fraction(3),
    Fraction(5),
    Fraction(7),
    Fraction(10),
    Fraction(30),
    Fraction(100),
    Fraction(300),
    Fraction(1000),
)

BLASIUS_WEDGE_SHEAR = mp.mpf("0.3320573362151962989371801")


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def _mp_fraction(value):
    value = Fraction(value)
    return mp.mpf(value.numerator) / mp.mpf(value.denominator)


def _as_text(value, working):
    return mp.nstr(value, working - 8, min_fixed=-100, max_fixed=100,
                   strip_zeros=False)


def _eta_limit(beta):
    if beta <= Fraction(-19, 100):
        return mp.mpf("40")
    if beta < 0:
        return mp.mpf("32")
    if beta < Fraction(1, 2):
        return mp.mpf("26")
    return mp.mpf("22")


def _shooting_guess(beta):
    beta = _mp_fraction(beta)
    guess = mp.mpf("0.4695999883610133") + mp.mpf("0.88") * beta
    guess += mp.mpf("0.05") * beta * beta
    return max(mp.mpf("0.015"), guess)


def _ode_tolerance():
    return mp.mpf(10) ** (-(mp.dps - 8))


def _end_slope(beta, shear, eta_max):
    def ode(_eta, state):
        f, fp, fpp = state
        return [fp, fpp, -f * fpp - beta * (1 - fp * fp)]

    solution = mp.odefun(
        ode,
        mp.mpf("0"),
        [mp.mpf("0"), mp.mpf("0"), shear],
        tol=_ode_tolerance(),
    )
    return solution(eta_max)[1]


def _shoot(beta_fraction):
    beta = _mp_fraction(beta_fraction)
    eta_max = _eta_limit(beta_fraction)

    def residual(shear):
        return _end_slope(beta, shear, eta_max) - 1

    guess = _shooting_guess(beta_fraction)
    pairs = (
        (guess * mp.mpf("0.75"), guess * mp.mpf("1.25")),
        (guess * mp.mpf("0.45"), guess * mp.mpf("1.60")),
        (mp.mpf("0.01"), max(mp.mpf("0.08"), guess)),
        (mp.mpf("0.05"), mp.mpf("1.0")),
        (mp.mpf("0.25"), mp.mpf("3.0")),
    )
    for a, b in pairs:
        try:
            root = mp.findroot(
                residual,
                (a, b),
                tol=mp.mpf(10) ** (-(mp.dps - 10)),
                maxsteps=25,
            )
        except Exception:
            continue
        if root > 0 and mp.isfinite(root):
            if abs(residual(root)) < mp.mpf(10) ** (-(mp.dps // 2)):
                return root

    return _scan_for_positive_root(residual)


def _scan_for_positive_root(residual):
    points = [mp.mpf("0")]
    point = mp.mpf("0.004")
    while point < mp.mpf("5"):
        points.append(point)
        point *= mp.mpf("1.18")
    points.append(mp.mpf("5"))

    last_point = points[0]
    last_value = residual(last_point)
    brackets = []
    for point in points[1:]:
        value = residual(point)
        if last_value == 0:
            return last_point
        if value == 0:
            return point
        if last_value * value < 0:
            brackets.append((last_point, point, last_value, value))
        last_point, last_value = point, value

    if not brackets:
        raise RuntimeError("could not bracket the upper Falkner-Skan branch")

    low, high, flow, fhigh = brackets[-1]
    for _ in range(max(80, 2 * mp.dps)):
        mid = (low + high) / 2
        fmid = residual(mid)
        if flow * fmid <= 0:
            high, fhigh = mid, fmid
        else:
            low, flow = mid, fmid
    return (low + high) / 2


def _thermal_tail(prandtl, integral_f, f_at_end, working):
    if prandtl * integral_f > (working + 15) * mp.log(10):
        return mp.mpf("0")
    z = f_at_end * mp.sqrt(prandtl / 2)
    return (
        mp.e ** (-prandtl * integral_f)
        * mp.sqrt(mp.pi / (2 * prandtl))
        * mp.e ** (prandtl * f_at_end * f_at_end / 2)
        * mp.erfc(z)
    )


@lru_cache(maxsize=None)
def _values_for_beta(beta_text, working):
    context = multiprocessing.get_context("fork")
    reader, writer = context.Pipe(duplex=False)
    child = context.Process(
        target=lambda: writer.send(_compute_values_for_beta(beta_text, working))
    )
    child.start()
    writer.close()
    try:
        values = reader.recv()
    except EOFError:
        child.join()
        raise RuntimeError(
            "the child computing beta=%s at %s digits exited with code %s"
            % (beta_text, working, child.exitcode)
        )
    child.join()
    if child.exitcode:
        raise RuntimeError(
            "the child computing beta=%s at %s digits exited with code %s"
            % (beta_text, working, child.exitcode)
        )
    return values


def _compute_values_for_beta(beta_text, working):
    mp.dps = int(working)
    beta_fraction = Fraction(beta_text)
    beta = _mp_fraction(beta_fraction)
    eta_max = _eta_limit(beta_fraction)
    shear = _shoot(beta_fraction)
    prandtls = tuple(_mp_fraction(prandtl) for prandtl in PRANDTL_VALUES)
    scale = 1 / mp.sqrt(2 - beta)

    def ode(_eta, state):
        f, fp, fpp, integral_f = state[:4]
        out = [fp, fpp, -f * fpp - beta * (1 - fp * fp), f]
        for prandtl in prandtls:
            out.append(mp.e ** (-prandtl * integral_f))
        return out

    initial = [mp.mpf("0"), mp.mpf("0"), shear, mp.mpf("0")]
    initial.extend([mp.mpf("0")] * len(prandtls))
    solution = mp.odefun(ode, mp.mpf("0"), initial, tol=_ode_tolerance())
    at_end = solution(eta_max)
    f_at_end = at_end[0]
    integral_f = at_end[3]

    values = {}
    for index, prandtl_fraction in enumerate(PRANDTL_VALUES):
        prandtl = prandtls[index]
        integral = at_end[4 + index]
        integral += _thermal_tail(prandtl, integral_f, f_at_end, working)
        hartree = 1 / integral
        values[(str(prandtl_fraction), "hartree")] = _as_text(hartree, working)
        values[(str(prandtl_fraction), "wedge")] = _as_text(scale * hartree, working)
    values[("_wall_shear_hartree", "hartree")] = _as_text(shear, working)
    values[("_wall_shear_hartree", "wedge")] = _as_text(scale * shear, working)
    return values


def _entry_text(beta, prandtl, normalisation, working):
    values = _values_for_beta(str(beta), working)
    return values[(str(prandtl), normalisation)]


def check_controls():
    mp.dps = max(WORKING_DIGITS) + 10
    values = _values_for_beta("0", max(WORKING_DIGITS))
    wedge_heat = mp.mpf(values[("1", "wedge")])
    wedge_shear = mp.mpf(values[("_wall_shear_hartree", "wedge")])
    if abs(wedge_heat - BLASIUS_WEDGE_SHEAR) > mp.mpf("1e-10"):
        raise SystemExit(
            "Blasius/Reynolds control failed: heat %s against %s"
            % (_as_text(wedge_heat, 40), _as_text(BLASIUS_WEDGE_SHEAR, 40))
        )
    if abs(wedge_heat - wedge_shear) > mp.mpf("1e-10"):
        raise SystemExit(
            "Reynolds analogy failed: heat %s against shear %s"
            % (_as_text(wedge_heat, 40), _as_text(wedge_shear, 40))
        )
    print("Blasius/Reynolds controls passed", flush=True)


class ThermalFalknerSkanWallHeatTransfer(numberdb.Generator):

    table = TABLE
    parameters = ("beta", "branch", "prandtl", "normalisation")
    type = "R"
    rigour = "heuristic (agreement-checked)"
    digits = DIGITS

    def enumerate(self):
        for beta in BETA_VALUES:
            for branch in BRANCHES:
                for prandtl in PRANDTL_VALUES:
                    for normalisation in NORMALISATIONS:
                        yield {
                            "beta": beta,
                            "branch": branch,
                            "prandtl": prandtl,
                            "normalisation": normalisation,
                        }

    def value(self, params, digits=None):
        if params["branch"] != "upper":
            raise ValueError("only the upper branch is computed in this draft")
        beta = Fraction(params["beta"])
        prandtl = Fraction(params["prandtl"])
        normalisation = str(params["normalisation"])
        if normalisation not in NORMALISATIONS:
            raise ValueError("unknown normalisation %r" % normalisation)
        return numberdb.agreeing(
            lambda working: _entry_text(beta, prandtl, normalisation, working),
            at=WORKING_DIGITS,
        )


def main():
    _key_from_stdin()
    check_controls()
    generator = ThermalFalknerSkanWallHeatTransfer()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="thermal Falkner-Skan wall heat transfer on the upper branch"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
