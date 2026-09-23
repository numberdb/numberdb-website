"""Wall heat transfer -theta'(0) of the thermal Falkner-Skan boundary layer -- numberdb.org/T417.

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
DIGITS = 9
WORKING_DIGITS = (30, 36)
WORKING_STEPS = {
    24: Fraction(1, 500),
    30: Fraction(1, 1000),
    36: Fraction(1, 2000),
}
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
    if beta >= 0:
        guess = mp.mpf("0.4695999883610133")
        guess += mp.mpf("0.95") * beta
        guess -= mp.mpf("0.19") * beta * beta
        return max(mp.mpf("0.05"), guess)
    guess = mp.mpf("0.4695999883610133") + mp.mpf("0.88") * beta
    guess += mp.mpf("0.05") * beta * beta
    return max(mp.mpf("0.015"), guess)


def _ode_tolerance():
    return mp.mpf(10) ** (-(mp.dps - 8))


def _step_for(working):
    return _mp_fraction(WORKING_STEPS.get(working, Fraction(1, 1000)))


def _rk4_count(eta_max, step):
    n = int(mp.ceil(eta_max / step))
    if n % 2:
        n += 1
    return n, eta_max / n


def _velocity_rhs(beta, f, fp, fpp):
    return fp, fpp, -f * fpp - beta * (1 - fp * fp)


def _rk4_velocity_end(beta, shear, eta_max, step):
    n, h = _rk4_count(eta_max, step)
    f = mp.mpf("0")
    fp = mp.mpf("0")
    fpp = shear
    for _ in range(n):
        k1 = _velocity_rhs(beta, f, fp, fpp)
        k2 = _velocity_rhs(
            beta,
            f + h * k1[0] / 2,
            fp + h * k1[1] / 2,
            fpp + h * k1[2] / 2,
        )
        k3 = _velocity_rhs(
            beta,
            f + h * k2[0] / 2,
            fp + h * k2[1] / 2,
            fpp + h * k2[2] / 2,
        )
        k4 = _velocity_rhs(
            beta,
            f + h * k3[0],
            fp + h * k3[1],
            fpp + h * k3[2],
        )
        f += h * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]) / 6
        fp += h * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]) / 6
        fpp += h * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2]) / 6
    return f, fp, fpp


def _shoot(beta_fraction, step):
    beta = _mp_fraction(beta_fraction)
    eta_max = _eta_limit(beta_fraction)

    def residual(shear):
        return _rk4_velocity_end(beta, shear, eta_max, step)[1] - 1

    guess = _shooting_guess(beta_fraction)
    threshold = mp.mpf(10) ** (-min(14, max(8, mp.dps // 2)))
    root = _root_near_guess(residual, guess, threshold)
    if root is not None:
        return root

    pairs = (
        (guess * mp.mpf("0.95"), guess * mp.mpf("1.05")),
        (guess * mp.mpf("0.90"), guess * mp.mpf("1.10")),
        (guess * mp.mpf("0.75"), guess * mp.mpf("1.25")),
        (guess * mp.mpf("0.45"), guess * mp.mpf("1.60")),
        (mp.mpf("0.01"), max(mp.mpf("0.08"), guess)),
        (mp.mpf("0.05"), mp.mpf("1.0")),
        (mp.mpf("0.25"), mp.mpf("3.0")),
    )
    for low, high in pairs:
        root = _root_from_bracket(residual, low, high, threshold)
        if root is not None:
            return root

        try:
            flow = residual(low)
            fhigh = residual(high)
        except Exception:
            continue
        if not (_reasonable_residual(flow) and _reasonable_residual(fhigh)):
            continue
        try:
            root = mp.findroot(
                residual,
                (low, high),
                tol=threshold,
                maxsteps=12,
            )
        except Exception:
            root = None
        if root is not None and root > 0 and mp.isfinite(root):
            if abs(residual(root)) < threshold:
                return root

    return _scan_for_positive_root(residual, threshold)


def _reasonable_residual(value):
    return mp.isfinite(value) and abs(value) < mp.mpf("1.0e6")


def _root_near_guess(residual, guess, threshold):
    try:
        fguess = residual(guess)
    except Exception:
        return None
    if abs(fguess) < threshold:
        return guess
    if not _reasonable_residual(fguess):
        return None

    upper_factors = (
        "1.005", "1.01", "1.02", "1.05", "1.10", "1.20", "1.35",
    )
    for factor in upper_factors:
        root = _root_from_bracket(
            residual, guess, guess * mp.mpf(factor), threshold,
            flow=fguess)
        if root is not None:
            return root

    lower_factors = (
        "0.995", "0.99", "0.98", "0.95", "0.90", "0.80", "0.65",
    )
    for factor in lower_factors:
        root = _root_from_bracket(
            residual, guess * mp.mpf(factor), guess, threshold,
            fhigh=fguess)
        if root is not None:
            return root
    return None


def _root_from_bracket(residual, low, high, threshold,
                       flow=None, fhigh=None):
    try:
        if flow is None:
            flow = residual(low)
        if fhigh is None:
            fhigh = residual(high)
    except Exception:
        return None
    if abs(flow) < threshold:
        return low
    if abs(fhigh) < threshold:
        return high
    if not (_reasonable_residual(flow) and _reasonable_residual(fhigh)):
        return None
    if flow * fhigh >= 0:
        return None
    try:
        root = mp.findroot(
            residual, (low, high), tol=threshold, maxsteps=12)
        if low <= root <= high and abs(residual(root)) < threshold:
            return root
    except Exception:
        pass
    root = _bisect_positive_root(residual, low, high, flow)
    try:
        if abs(residual(root)) < threshold:
            return root
    except Exception:
        return None
    return None


def _scan_for_positive_root(residual, threshold):
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
        if abs(last_value) < threshold:
            return last_point
        if abs(value) < threshold:
            return point
        if (
            _reasonable_residual(last_value)
            and _reasonable_residual(value)
            and last_value * value < 0
        ):
            brackets.append((last_point, point, last_value, value))
        last_point, last_value = point, value

    for low, high, flow, fhigh in reversed(brackets):
        root = _root_from_bracket(
            residual, low, high, threshold, flow=flow, fhigh=fhigh)
        if root is not None:
            return root
    raise RuntimeError("could not bracket the upper Falkner-Skan branch")


def _bisect_positive_root(residual, low, high, flow):
    for _ in range(52):
        mid = (low + high) / 2
        fmid = residual(mid)
        if flow * fmid <= 0:
            high = mid
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


def _profile_integral_grid(beta, shear, eta_max, step):
    n, h = _rk4_count(eta_max, step)
    f = mp.mpf("0")
    fp = mp.mpf("0")
    fpp = shear
    integral_f = mp.mpf("0")
    grid = [integral_f]

    def rhs(f_value, fp_value, fpp_value):
        df, dfp, dfpp = _velocity_rhs(beta, f_value, fp_value, fpp_value)
        return df, dfp, dfpp, f_value

    for _ in range(n):
        k1 = rhs(f, fp, fpp)
        k2 = rhs(
            f + h * k1[0] / 2,
            fp + h * k1[1] / 2,
            fpp + h * k1[2] / 2,
        )
        k3 = rhs(
            f + h * k2[0] / 2,
            fp + h * k2[1] / 2,
            fpp + h * k2[2] / 2,
        )
        k4 = rhs(
            f + h * k3[0],
            fp + h * k3[1],
            fpp + h * k3[2],
        )
        f += h * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0]) / 6
        fp += h * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1]) / 6
        fpp += h * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2]) / 6
        integral_f += h * (k1[3] + 2 * k2[3] + 2 * k3[3] + k4[3]) / 6
        grid.append(integral_f)
    return f, fp, fpp, integral_f, h, grid


def _simpson_exponential_integral(prandtl, h, grid):
    total = mp.e ** (-prandtl * grid[0]) + mp.e ** (-prandtl * grid[-1])
    odd = mp.mpf("0")
    even = mp.mpf("0")
    for index, value in enumerate(grid[1:-1], start=1):
        term = mp.e ** (-prandtl * value)
        if index % 2:
            odd += term
        else:
            even += term
    return h * (total + 4 * odd + 2 * even) / 3


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
    step = _step_for(working)
    shear = _shoot(beta_fraction, step)
    prandtls = tuple(_mp_fraction(prandtl) for prandtl in PRANDTL_VALUES)
    scale = 1 / mp.sqrt(2 - beta)
    f_at_end, fp_at_end, _fpp_at_end, integral_f, h, grid = \
        _profile_integral_grid(beta, shear, eta_max, step)
    residual = abs(fp_at_end - 1)
    residual_limit = mp.mpf(10) ** (-min(10, max(8, mp.dps // 2)))
    if residual > residual_limit:
        raise RuntimeError(
            "shooting residual %s exceeds %s for beta=%s"
            % (_as_text(residual, working), _as_text(residual_limit, working),
               beta_text)
        )

    values = {}
    for index, prandtl_fraction in enumerate(PRANDTL_VALUES):
        prandtl = prandtls[index]
        integral = _simpson_exponential_integral(prandtl, h, grid)
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


def _only_params(argument):
    requested = {}
    for item in argument.split(","):
        if not item:
            continue
        key, value = item.split("=", 1)
        requested[key.strip()] = value.strip()
    return requested


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
    if "--only" in sys.argv:
        index = sys.argv.index("--only")
        params = _only_params(sys.argv[index + 1])
        print(generator.value(params, generator.digits))
    elif os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="thermal Falkner-Skan wall heat transfer on the upper branch",
            lowering=os.environ.get("NUMBERDB_LOWERING") == "1"
            or "--lowering" in sys.argv))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
