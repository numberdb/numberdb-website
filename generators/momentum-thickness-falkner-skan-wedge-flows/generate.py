"""Momentum thickness delta_2 of the Falkner-Skan wedge flows -- numberdb.org/T416

This fills both normalisations of the upper-branch momentum thickness for
two-decimal Hartree parameters -0.19 <= beta <= 1.33.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

For this repository's build environment, use:

    $ agents/sage.sh generate.py
    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
        agents/sage.sh generate.py

The computation shoots on f''(0) in the Hartree form

    f''' + f f'' + beta (1 - (f')^2) = 0,
    f(0) = f'(0) = 0, f'(infinity) = 1.

The ODE system also integrates delta_1 and delta_2. Continuation in beta keeps
the secant iteration on the upper branch; every root is checked by the
Hartree momentum integral. The 30 stored digits must agree between 42- and
50-decimal working precision runs.
"""

import gc
import os
import sys

import numberdb.sage as numberdb
from sage.rings.rational_field import QQ

from mpmath import mp


TABLE = "T416"
DIGITS = 30
ETA_MAX_TEXT = "18"
LOW_EXTRA_DIGITS = 12
HIGH_EXTRA_DIGITS = 20
NORMALISATIONS = ("wedge", "hartree")
BETAS = tuple(QQ(k) / QQ(100) for k in range(-19, 134))

_CACHE = {}


def _progress(message):
    print(message, flush=True)


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _mpq(q):
    return mp.mpf(str(q.numerator())) / mp.mpf(str(q.denominator()))


def _beta_key(beta):
    beta = QQ(beta)
    return str(beta)


def _format_decimal(value, digits):
    return mp.nstr(
        value,
        n=digits,
        strip_zeros=False,
        min_fixed=-100,
        max_fixed=100,
    )


def _integrate(beta, shear, dps):
    mp.dps = dps
    beta_mp = _mpq(beta)
    shear = mp.mpf(shear)
    eta_max = mp.mpf(ETA_MAX_TEXT)

    def rhs(_eta, y):
        f, fp, fpp, d1, d2 = y
        return [
            fp,
            fpp,
            -f * fpp - beta_mp * (1 - fp * fp),
            1 - fp,
            fp * (1 - fp),
        ]

    sol = mp.odefun(
        rhs,
        mp.mpf("0"),
        (mp.mpf("0"), mp.mpf("0"), shear, mp.mpf("0"), mp.mpf("0")),
        tol=mp.mpf(10) ** (-(dps - 12)),
        degree=30,
    )
    value = sol(eta_max)
    del sol
    gc.collect()
    return value


def _residual(beta, shear, dps):
    return _integrate(beta, shear, dps)[1] - 1


def _momentum_residual(beta, shear, end):
    beta_mp = _mpq(beta)
    delta1, delta2 = end[3], end[4]
    return shear - (beta_mp * delta1 + (1 + beta_mp) * delta2)


def _valid_root(beta, shear, end, dps):
    fp_residual = abs(end[1] - 1)
    fpp_end = abs(end[2])
    identity = abs(_momentum_residual(beta, shear, end))
    return (
        fp_residual < mp.mpf(10) ** (-(dps - 20))
        and fpp_end < mp.mpf("1e-16")
        and identity < mp.mpf("1e-16")
    )


def _solve_secant(beta, guess0, guess1, dps):
    mp.dps = dps
    x0 = mp.mpf(guess0)
    x1 = mp.mpf(guess1)
    y0 = _residual(beta, x0, dps)
    y1 = _residual(beta, x1, dps)

    for _ in range(10):
        if y1 == y0:
            break
        x2 = x1 - y1 * (x1 - x0) / (y1 - y0)
        y2 = _residual(beta, x2, dps)
        x0, y0, x1, y1 = x1, y1, x2, y2
        if abs(y1) < mp.mpf(10) ** (-(dps - 20)):
            break

    end = _integrate(beta, x1, dps)
    if not _valid_root(beta, x1, end, dps):
        raise ArithmeticError(
            "bad upper-branch root at beta=%s: shear=%s, fp=%s, fpp=%s, "
            "momentum residual=%s"
            % (
                beta,
                mp.nstr(x1, 25),
                mp.nstr(end[1], 8),
                mp.nstr(end[2], 8),
                mp.nstr(_momentum_residual(beta, x1, end), 8),
            )
        )
    return x1, end


def _solve_near(beta, predicted, dps):
    last = None
    for width in ("0.003", "0.006", "0.012", "0.024"):
        width = mp.mpf(width)
        try:
            return _solve_secant(beta, predicted - width, predicted + width, dps)
        except ArithmeticError as trouble:
            last = trouble
    raise last


def _solve_from_seed(beta, seed, dps):
    last = None
    for width in ("1e-8", "1e-6", "1e-4", "1e-3"):
        width = mp.mpf(width)
        try:
            return _solve_secant(beta, mp.mpf(seed) - width, mp.mpf(seed) + width, dps)
        except ArithmeticError as trouble:
            last = trouble
    raise last


def _solve_direction(betas, first_guesses, dps):
    out = {}
    shears = []
    for index, beta in enumerate(betas):
        if index == 0:
            shear, end = _solve_secant(beta, first_guesses[0], first_guesses[1], dps)
        elif index == 1:
            step = mp.mpf("0.01") if betas[1] > betas[0] else -mp.mpf("0.01")
            shear, end = _solve_secant(beta, shears[-1] + step, shears[-1] + 2 * step, dps)
        else:
            predicted = shears[-1] + (shears[-1] - shears[-2])
            shear, end = _solve_near(beta, predicted, dps)
        out[beta] = (shear, end)
        shears.append(shear)
        if index % 10 == 0 or index + 1 == len(betas):
            _progress("  dps %d beta %s" % (dps, beta))
    return out


def _solve_grid(dps, seeds=None):
    mp.dps = dps
    _progress("computing Falkner-Skan grid at %d decimal digits" % (dps,))
    if seeds is not None:
        out = {}
        for index, beta in enumerate(BETAS):
            out[beta] = _solve_from_seed(beta, seeds[beta], dps)
            if index % 10 == 0 or index + 1 == len(BETAS):
                _progress("  dps %d beta %s" % (dps, beta))
        return out

    zero = QQ(0)
    positives = [QQ(k) / QQ(100) for k in range(0, 134)]
    negatives = [QQ(k) / QQ(100) for k in range(-1, -20, -1)]

    out = _solve_direction(positives, (mp.mpf("0.46"), mp.mpf("0.48")), dps)
    zero_shear = out[zero][0]
    out.update(
        _solve_direction(
            negatives,
            (zero_shear - mp.mpf("0.01"), zero_shear - mp.mpf("0.02")),
            dps,
        )
    )
    return out


def _topfer_blasius_shear(dps):
    end = _integrate(QQ(0), mp.mpf(1), dps)
    return end[1] ** (-mp.mpf(3) / mp.mpf(2))


def _values_for_digits(digits):
    low_dps = digits + LOW_EXTRA_DIGITS
    high_dps = digits + HIGH_EXTRA_DIGITS

    low = _solve_grid(low_dps)
    seeds = {beta: low[beta][0] for beta in low}
    high = _solve_grid(high_dps, seeds=seeds)

    topfer = _topfer_blasius_shear(high_dps)
    blasius = high[QQ(0)][1][4]
    if abs(topfer - blasius) > mp.mpf("1e-32"):
        raise ArithmeticError(
            "Toepfer Blasius check failed: %s versus %s"
            % (mp.nstr(topfer, 40), mp.nstr(blasius, 40))
        )

    values = {}
    for beta in BETAS:
        beta_mp = _mpq(beta)
        wedge_factor = mp.sqrt(2 - beta_mp)
        for normalisation in NORMALISATIONS:
            if normalisation == "hartree":
                low_value = low[beta][1][4]
                high_value = high[beta][1][4]
            else:
                low_value = wedge_factor * low[beta][1][4]
                high_value = wedge_factor * high[beta][1][4]
            low_text = _format_decimal(low_value, digits)
            high_text = _format_decimal(high_value, digits)
            if low_text != high_text:
                raise ArithmeticError(
                    "%s %s disagrees between working precisions: %s vs %s"
                    % (beta, normalisation, low_text, high_text)
                )
            values[(str(beta), normalisation)] = high_text

    # Schlichting and Gersten's Hartree-profile table prints beta_2=0.746 at
    # beta=-0.1 in this wedge normalisation.
    if not values[(str(QQ(-1) / QQ(10)), "wedge")].startswith("0.746"):
        raise ArithmeticError("Schlichting beta=-0.1 check failed")

    return values


def _ensure_cache(digits):
    if digits not in _CACHE:
        _CACHE[digits] = _values_for_digits(digits)
    return _CACHE[digits]


class FalknerSkanMomentumThickness(numberdb.Generator):
    table = os.environ.get("NUMBERDB_TABLE", TABLE)
    parameters = ("beta", "branch", "normalisation")
    type = "R"
    digits = DIGITS
    rigour = "heuristic (agreement-checked)"

    def enumerate(self):
        for beta in BETAS:
            for normalisation in NORMALISATIONS:
                yield {
                    "beta": str(beta),
                    "branch": "upper",
                    "normalisation": normalisation,
                }

    def value(self, params, digits):
        if params["branch"] != "upper":
            raise ValueError("only the upper branch is filled")
        beta = _beta_key(params["beta"])
        normalisation = params["normalisation"]
        if normalisation not in NORMALISATIONS:
            raise ValueError("unknown normalisation %r" % (normalisation,))
        return _ensure_cache(digits)[(beta, normalisation)]


def self_check(digits=DIGITS):
    values = _ensure_cache(digits)
    print("self-check passed for %d entries" % (len(values),))
    for beta in ("-19/100", "-1/10", "0", "1/2", "1", "133/100"):
        print(
            "beta %s: hartree %s, wedge %s"
            % (beta, values[(beta, "hartree")], values[(beta, "wedge")])
        )


if __name__ == "__main__":
    _key_from_stdin()
    generator = FalknerSkanMomentumThickness()
    mode = os.environ.get("NUMBERDB_PUBLISH")
    if mode == "1":
        print(generator.publish(message="computed Falkner-Skan momentum thickness values"))
    elif mode == "preview" or "--preview" in sys.argv:
        print(generator.preview())
    else:
        self_check(generator.digits)
        if os.environ.get("NUMBERDB_API_KEY"):
            report = generator.verify(sample=None)
            print(report)
            sys.exit(0 if report.ok else 1)
        print("NUMBERDB_API_KEY is not set, so verify() was skipped")
