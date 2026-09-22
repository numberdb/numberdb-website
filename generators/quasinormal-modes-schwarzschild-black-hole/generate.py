"""Quasinormal modes of the Schwarzschild black hole -- numberdb.org/T399.

This draft stores the dimensionless fundamental frequencies M omega for
Schwarzschild black-hole quasinormal modes, with time dependence exp(-i omega t).

Run it with SageMath:

    $ sage -pip install numberdb mpmath
    $ sage -python generate.py
    $ sage -python generate.py --publish

For this repository's build environment, use:

    $ agents/sage.sh generate.py
    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 agents/sage.sh generate.py
"""

import os
import sys
import time
from decimal import Decimal, localcontext
from functools import lru_cache

import numberdb.sage as numberdb
import mpmath as mp

from numberdb import ComplexInterval, RealInterval


TABLE = os.environ.get("NUMBERDB_TABLE", "T399")
DIGITS = 10
MAX_N = 0

# Each profile is (working decimal digits, Lentz tolerance exponent,
# minimum tail iterations, maximum tail iterations).
DEFAULT_PROFILES = ((50, -10, 300, 4000), (70, -12, 400, 6000))
SCALAR_MONOPOLE_PROFILES = ((60, -10, 300, 4000), (80, -12, 400, 6000))

INITIAL_SEEDS = {
    (0, 0, 0): ("0.11045493908017281", "-0.10489571705618415"),
}


def _key_from_stdin():
    """Let agents/sage.sh pass the API key on stdin."""
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if token:
        if "=" in token and token.split("=", 1)[0].isupper():
            token = token.split("=", 1)[1].strip().strip("'\"")
        numberdb.configure(api_key=token)


def _spin_for_equation(s_abs):
    return -int(s_abs) if int(s_abs) else 0


def _dolan_ottewill_seed(s_abs, ell, n):
    """Dolan-Ottewill large-l expansion, used only as a root seed."""
    s = _spin_for_equation(s_abs)
    L = mp.mpf(ell) + mp.mpf("0.5")
    N = mp.mpf(n) + mp.mpf("0.5")
    beta = 1 - s * s
    I = mp.mpc(0, 1)
    coefficients = {
        -1: mp.mpf(1),
        0: -I * N,
        1: beta / 3 - 5 * N * N / 36 - mp.mpf(115) / 432,
        2: -I * N * (beta / 9 + 235 * N**2 / 3888
                     - mp.mpf(1415) / 15552),
        3: (-beta**2 / 27
            + (204 * N**2 + 211) * beta / 3888
            + (854160 * N**4 - 1664760 * N**2 - 776939)
            / mp.mpf(40310784)),
        4: -I * N * (
            beta**2 / 27
            + (1100 * N**2 - 2719) * beta / 46656
            + (11273136 * N**4 - 52753800 * N**2 + 66480535)
            / mp.mpf(2902376448)),
    }
    omega = mp.mpc(0)
    for power, coefficient in coefficients.items():
        omega += coefficient * L ** (-power)
    return omega / mp.sqrt(27)


def _recurrence_coefficients(omega, s_abs, ell):
    """Cook-Zalutskiy radial recurrence coefficients for a=0."""
    s = _spin_for_equation(s_abs)
    I = mp.mpc(0, 1)
    zeta = I * omega
    xi = -s - I * (2 * omega)
    eta = mp.mpf(0)
    p = zeta

    alpha0 = 1 + s + xi + eta - 2 * zeta + s
    gamma0 = 1 + s + 2 * eta
    delta0 = 1 + s + 2 * xi
    angular = ell * (ell + 1) - s * (s + 1)
    sigma = (
        angular - 8 * omega * omega
        + p * (2 * alpha0 + gamma0 - delta0)
        + (1 + s - (gamma0 + delta0) / 2)
        * (s + (gamma0 + delta0) / 2)
    )

    return (
        delta0,
        4 * p - 2 * alpha0 + gamma0 - delta0 - 2,
        2 * alpha0 - gamma0 + 2,
        alpha0 * (4 * p - delta0) - sigma,
        alpha0 * (alpha0 - gamma0 + 1),
    )


def _leaver_equation(omega, s_abs, ell, n_inv, tail_tolerance,
                     min_tail, max_tail):
    D0, D1, D2, D3, D4 = _recurrence_coefficients(omega, s_abs, ell)

    def alpha(k):
        return k * k + (D0 + 1) * k + D0

    def beta(k):
        return -2 * k * k + (D1 + 2) * k + D3

    def gamma(k):
        return k * k + (D2 - 3) * k + D4 - D2 + 2

    left = mp.mpc(0)
    for k in range(n_inv):
        left = alpha(k) / (beta(k) - gamma(k) * left)

    tiny = mp.mpf(10) ** (-(mp.mp.dps - 10))
    f_old = mp.mpc(tiny)
    C_old = mp.mpc(tiny)
    D_old = mp.mpc(0)
    f_new = f_old
    k = n_inv
    for step in range(1, max_tail + 1):
        a_k = -alpha(k) / gamma(k)
        k += 1
        b_k = beta(k) / gamma(k)

        D_new = b_k + a_k * D_old
        if D_new == 0:
            D_new = tiny
        C_new = b_k + a_k / C_old
        if C_new == 0:
            C_new = tiny

        D_new = 1 / D_new
        delta = C_new * D_new
        f_new = f_old * delta
        D_old = D_new
        C_old = C_new
        f_old = f_new

        if step >= min_tail and abs(delta - 1) < tail_tolerance:
            break

    return beta(n_inv) - gamma(n_inv) * left + gamma(n_inv) * f_new


def _solve_one(s_abs, ell, n, seed, profile):
    working_digits, tolerance_exponent, min_tail, max_tail = profile
    mp.mp.dps = working_digits
    tail_tolerance = mp.mpf(10) ** tolerance_exponent
    seed = mp.mpc(seed)

    def real_part(x, y):
        return mp.re(_leaver_equation(
            mp.mpc(x, y), s_abs, ell, n, tail_tolerance, min_tail, max_tail))

    def imag_part(x, y):
        return mp.im(_leaver_equation(
            mp.mpc(x, y), s_abs, ell, n, tail_tolerance, min_tail, max_tail))

    x, y = mp.findroot(
        (real_part, imag_part),
        (mp.re(seed), mp.im(seed)),
        tol=mp.mpf(10) ** (-(working_digits - 20)),
        maxsteps=80,
    )
    omega = mp.mpc(x, y)
    if mp.re(omega) < 0 and mp.im(omega) < 0:
        omega = -mp.conj(omega)
    return omega


@lru_cache(maxsize=None)
def _sequence(s_abs, ell, profile):
    roots = []
    for n in range(MAX_N + 1):
        initial = INITIAL_SEEDS.get((int(s_abs), int(ell), n))
        if initial is not None:
            seed = mp.mpc(mp.mpf(initial[0]), mp.mpf(initial[1]))
        elif n < 2:
            seed = _dolan_ottewill_seed(s_abs, ell, n)
        else:
            seed = roots[-1] + (roots[-1] - roots[-2])
        roots.append(_solve_one(s_abs, ell, n, seed, profile))
    return tuple(roots)


def _profiles_for(s_abs, ell):
    if int(s_abs) == 0 and int(ell) == 0:
        return SCALAR_MONOPOLE_PROFILES
    return DEFAULT_PROFILES


def _as_fraction(value, digits=45):
    return str(mp.nstr(value, digits, min_fixed=-100, max_fixed=100))


def _last_decimal_place(text):
    mantissa, _, exponent = text.lower().partition("e")
    power = int(exponent or 0)
    mantissa = mantissa.lstrip("+-")
    if "." in mantissa:
        power -= len(mantissa.rsplit(".", 1)[1])
    return Decimal(1).scaleb(power)


def _decimal_endpoint(value):
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _widened_equal_endpoints(text):
    digits = sum(1 for character in text if character.isdigit())
    with localcontext() as context:
        context.prec = digits + 5
        midpoint = Decimal(text)
        step = _last_decimal_place(text)
        return (
            _decimal_endpoint(midpoint - step),
            _decimal_endpoint(midpoint + step),
        )


def _real_interval(a, b):
    low, high = (_as_fraction(a), _as_fraction(b))
    if low == high:
        low, high = _widened_equal_endpoints(low)
    elif mp.mpf(high) < mp.mpf(low):
        low, high = high, low
    return RealInterval(low, high)


def _complex_interval(first, second):
    return ComplexInterval(
        _real_interval(mp.re(first), mp.re(second)),
        _real_interval(mp.im(first), mp.im(second)),
    )


REFERENCE_VALUES = {
    # Berti's Schwarzschild files give 2 M omega_R, 2 M omega_I, error, n.
    (2, 2, 0): ("0.3736716844180419", "-0.0889623156889357", "1e-10"),
    (1, 1, 0): ("0.2482632641781087", "-0.0924877179529422", "1e-10"),
}

QNM_CACHE_VALUES = {
    # qnm's bundled Schwarzschild cache is double precision.
    (2, 2, 0): ("0.37367168441804166", "-0.0889623156889341", "1e-10"),
    (2, 3, 0): ("0.5994432884374916", "-0.0927030479449472", "1e-10"),
    (2, 4, 0): ("0.8091783775324655", "-0.09416396098885733", "1e-10"),
    (2, 5, 0): ("1.012295312135361", "-0.09487051608160832", "1e-10"),
    (2, 6, 0): ("1.2120098206521313", "-0.0952658458420826", "1e-10"),
    (0, 0, 0): ("0.11045493908017281", "-0.10489571705618415", "1e-8"),
    (0, 1, 0): ("0.2929361332672891", "-0.09765998891357464", "1e-10"),
    (0, 2, 0): ("0.48364387221070165", "-0.09675877597824928", "1e-10"),
    (0, 3, 0): ("0.6753662325366203", "-0.09649962773400965", "1e-10"),
    (0, 4, 0): ("0.8674156417378787", "-0.0963916923480232", "1e-10"),
    (1, 1, 0): ("0.24826326417811548", "-0.09248771795293224", "1e-10"),
    (1, 2, 0): ("0.45759551162985473", "-0.09500442581947034", "1e-10"),
    (1, 3, 0): ("0.6568986704624161", "-0.09561621792815873", "1e-10"),
    (1, 4, 0): ("0.853095192997699", "-0.09585993482802584", "1e-10"),
    (1, 5, 0): ("1.047912781931858", "-0.09598167202949734", "1e-10"),
}


def _check_one_reference(s_abs, ell, n, omega, reference):
    re_text, im_text, tolerance_text = reference
    target = mp.mpc(mp.mpf(re_text), mp.mpf(im_text))
    tolerance = mp.mpf(tolerance_text)
    if abs(omega - target) > tolerance:
        raise ArithmeticError(
            "reference check failed for s=%s, l=%s, n=%s: got %s, wanted %s"
            % (s_abs, ell, n, mp.nstr(omega, 30), mp.nstr(target, 30)))


def _check_reference(s_abs, ell, n, omega):
    for references in (REFERENCE_VALUES, QNM_CACHE_VALUES):
        reference = references.get((s_abs, ell, n))
        if reference is not None:
            _check_one_reference(s_abs, ell, n, omega, reference)


class SchwarzschildQuasinormalModes(numberdb.Generator):
    """Generator for T399."""

    table = TABLE
    parameters = ("s", "l", "n")
    type = "C"
    digits = DIGITS
    rigour = "heuristic (agreement-checked)"
    files = ("generate.py",)

    def enumerate(self):
        for s_abs in (2, 0, 1):
            for ell in range(s_abs, s_abs + 5):
                for n in range(MAX_N + 1):
                    yield {"s": s_abs, "l": ell, "n": n}

    def value(self, params, digits):
        s_abs = int(params["s"])
        ell = int(params["l"])
        n = int(params["n"])
        roots = [_sequence(s_abs, ell, profile)[n]
                 for profile in _profiles_for(s_abs, ell)]
        for root in roots:
            _check_reference(s_abs, ell, n, root)
        return _complex_interval(roots[0], roots[1])


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
        asked = generator.digits_for(params)
        entry = generator._entry(params, asked)
        wanted = entry.get("digits", asked)
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
    generator = SchwarzschildQuasinormalModes()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="Schwarzschild quasinormal modes from Leaver continued fractions"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
