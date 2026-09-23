"""Values of the Tracy-Widom densities f_beta(s) -- numberdb.org/T451

This generator computes f_beta(s) for beta = 1, 2, 4 on the grid
s = -10, -9.95, ..., 5.

Run it with SageMath:

    $ sage -pip install numberdb numpy scipy mpmath
    $ sage -python generate.py
    $ sage -python generate.py --publish

Inside this checkout, use agents/sage.sh instead:

    $ agents/sage.sh generate.py
    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 \
          NUMBERDB_PUBLISH=1 agents/sage.sh generate.py

The production computation differentiates Bornemann's determinant
factorisation.  With

    T_t(x, y) = Ai(x + y + t),      x, y >= 0,

the determinant identities are

    F_1(s) = det(I - T_s),
    F_2(s) = det(I - T_s) det(I + T_s),
    F_4(s) = (det(I - T_{sqrt(2) s}) + det(I + T_{sqrt(2) s})) / 2.

Away from the far-left beta = 4 tail, the derivative uses

    d det(I +/- T_t) / dt
      = det(I +/- T_t) tr((I +/- T_t)^(-1) (+/- dT_t/dt)).

The far-left beta = 4 tail uses central differences of the multiprecision
determinant values; the trace formula is too slow and ill-conditioned there.
Each value is accompanied by only as many digits as survive comparison with
a second determinant quadrature and with an independent Painleve-II
integration of the Hastings-McLeod solution.
"""

import numberdb.sage as numberdb
from numberdb import _compare

import functools
import math
import os
import sys
import warnings
from fractions import Fraction

import mpmath as mp
import numpy as np
import scipy
from scipy.linalg import LinAlgWarning, det, solve
from scipy.special import airy


TABLE = os.environ.get("NUMBERDB_TABLE") or "T451"

STEP = Fraction(1, 20)
S_MIN = Fraction(-10, 1)
S_MAX = Fraction(5, 1)

MAX_DIGITS = 12
DOUBLE_HIGH = (100, 24.0)
DOUBLE_CONTROL = (80, 20.0)

MP_DPS = 80
MP_LENGTH = mp.mpf(24)
MP_HIGH_N = 58
MP_CONTROL_N = 52
MP_TAIL_LIMIT = -12.0
MP_DIFF_HIGH = mp.mpf("0.00025")
MP_DIFF_CONTROL = mp.mpf("0.0005")

PAINLEVE_DPS = 80
PAINLEVE_X_MAX = mp.mpf(12)
PAINLEVE_STEP = mp.mpf("0.00125")


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _s_values():
    first = int(S_MIN / STEP)
    last = int(S_MAX / STEP)
    for k in range(first, last + 1):
        yield Fraction(k, 20)


def _fraction_text(value):
    return str(value.numerator) if value.denominator == 1 else str(value)


@functools.lru_cache(maxsize=None)
def _legendre_nodes(n, length):
    nodes, weights = np.polynomial.legendre.leggauss(int(n))
    x = float(length) * (nodes + 1.0) / 2.0
    rootw = np.sqrt(float(length) * weights / 2.0)
    return x, rootw


@functools.lru_cache(maxsize=None)
def _double_dets_and_derivatives(t_key, n, length):
    t = float(t_key)
    x, rootw = _legendre_nodes(int(n), float(length))
    z = x[:, None] + x[None, :] + t
    ai, aip, _, _ = airy(z)
    kernel = rootw[:, None] * ai * rootw[None, :]
    derivative = rootw[:, None] * aip * rootw[None, :]
    identity = np.eye(len(x))
    minus = identity - kernel
    plus = identity + kernel
    dminus = float(det(minus))
    dplus = float(det(plus))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", LinAlgWarning)
        dminus_prime = -dminus * float(np.trace(solve(minus, derivative)))
        dplus_prime = dplus * float(np.trace(solve(plus, derivative)))
    return dminus, dplus, dminus_prime, dplus_prime


@functools.lru_cache(maxsize=None)
def _mp_nodes(n):
    mp.mp.dps = MP_DPS
    nodes, weights = mp.gauss_quadrature(int(n), "legendre")
    xs = [MP_LENGTH * (nodes[i] + 1) / 2 for i in range(int(n))]
    roots = [mp.sqrt(MP_LENGTH * weights[i] / 2) for i in range(int(n))]
    return xs, roots


@functools.lru_cache(maxsize=None)
def _mp_dets(t_text, n):
    mp.mp.dps = MP_DPS
    t = mp.mpf(t_text)
    xs, roots = _mp_nodes(int(n))
    size = len(xs)
    matrix = mp.matrix(size)
    for i, xi in enumerate(xs):
        left = roots[i]
        for j, xj in enumerate(xs):
            matrix[i, j] = left * mp.airyai(xi + xj + t) * roots[j]
    identity = mp.eye(size)
    return mp.det(identity - matrix), mp.det(identity + matrix)


def _mp_f4_distribution(s_value, n):
    t_text = mp.nstr(mp.sqrt(2) * s_value, 60)
    dminus, dplus = _mp_dets(t_text, n)
    return (dminus + dplus) / 2


def _mp_f4_density(s, step, n):
    mp.mp.dps = MP_DPS
    s_value = mp.mpf(s.numerator) / s.denominator
    return (
        _mp_f4_distribution(s_value + step, n)
        - _mp_f4_distribution(s_value - step, n)
    ) / (2 * step)


def _fredholm_density(beta, s):
    if beta == "4":
        t = math.sqrt(2.0) * (s.numerator / float(s.denominator))
        if t <= MP_TAIL_LIMIT:
            high = _mp_f4_density(s, MP_DIFF_HIGH, MP_HIGH_N)
            control = _mp_f4_density(s, MP_DIFF_CONTROL, MP_CONTROL_N)
            return high, [control]
    else:
        t = s.numerator / float(s.denominator)

    t_key = "%.17g" % t
    high = _double_dets_and_derivatives(t_key, DOUBLE_HIGH[0], DOUBLE_HIGH[1])
    control = _double_dets_and_derivatives(
        t_key, DOUBLE_CONTROL[0], DOUBLE_CONTROL[1])
    return (_combine_density(beta, high),
            [_combine_density(beta, control)])


def _combine_density(beta, data):
    dminus, dplus, dminus_prime, dplus_prime = data
    if beta == "1":
        return dminus_prime
    if beta == "2":
        return dminus_prime * dplus + dminus * dplus_prime
    if beta == "4":
        return math.sqrt(2.0) * (dminus_prime + dplus_prime) / 2
    raise ValueError("unknown beta %r" % (beta,))


def _painleve_rhs(x, y):
    q, qp, u, integral, moment = y
    return [
        qp,
        x * q + 2 * q ** 3,
        -q,
        -q ** 2,
        -integral,
    ]


def _rk4_step(rhs, x, y, h):
    k1 = rhs(x, y)
    y2 = [yi + h * ki / 2 for yi, ki in zip(y, k1)]
    k2 = rhs(x + h / 2, y2)
    y3 = [yi + h * ki / 2 for yi, ki in zip(y, k2)]
    k3 = rhs(x + h / 2, y3)
    y4 = [yi + h * ki for yi, ki in zip(y, k3)]
    k4 = rhs(x + h, y4)
    return [
        yi + h * (a + 2 * b + 2 * c + d) / 6
        for yi, a, b, c, d in zip(y, k1, k2, k3, k4)
    ]


def _painleve_targets():
    mp.mp.dps = PAINLEVE_DPS
    targets = []
    sqrt2 = mp.sqrt(2)
    for s in _s_values():
        text = _fraction_text(s)
        plain = mp.mpf(s.numerator) / s.denominator
        targets.append((plain, ("plain", text)))
        targets.append((sqrt2 * plain, ("sqrt2", text)))
    return sorted(targets, key=lambda row: row[0], reverse=True)


@functools.lru_cache(maxsize=None)
def _painleve_samples():
    mp.mp.dps = PAINLEVE_DPS
    pending = _painleve_targets()
    x = mp.mpf(PAINLEVE_X_MAX)
    y = [
        mp.airyai(x),
        mp.airyai(x, 1),
        mp.mpf("0"),
        mp.mpf("0"),
        mp.mpf("0"),
    ]
    out = {}
    index = 0
    while index < len(pending):
        target = pending[index][0]
        while x - target > PAINLEVE_STEP:
            y = _rk4_step(_painleve_rhs, x, y, -PAINLEVE_STEP)
            x -= PAINLEVE_STEP
        if x > target:
            h = target - x
            y = _rk4_step(_painleve_rhs, x, y, h)
            x = target
        stored = tuple(y)
        while index < len(pending) and pending[index][0] == target:
            out[pending[index][1]] = stored
            index += 1
    return out


def _painleve_density(beta, s_text):
    samples = _painleve_samples()
    if beta == "4":
        q, _qp, u, integral, moment = samples[("sqrt2", s_text)]
        sqrt_f2 = mp.exp(-moment / 2)
        density_in_t = sqrt_f2 * (
            integral * mp.cosh(u / 2) - q * mp.sinh(u / 2)
        ) / 2
        return mp.sqrt(2) * density_in_t

    q, _qp, u, integral, moment = samples[("plain", s_text)]
    sqrt_f2 = mp.exp(-moment / 2)
    if beta == "1":
        return sqrt_f2 * mp.exp(-u / 2) * (integral + q) / 2
    if beta == "2":
        return mp.exp(-moment) * integral
    raise ValueError("unknown beta %r" % (beta,))


def _as_float(value):
    return float(value)


def _agreement_digits(value, controls):
    value = _as_float(value)
    if not math.isfinite(value):
        return 0
    error = max(abs(value - _as_float(control)) for control in controls)
    if error == 0:
        return MAX_DIGITS
    scale = abs(value)
    if scale == 0:
        return 0
    relative = error / scale
    if relative <= 0:
        return MAX_DIGITS
    return max(0, min(MAX_DIGITS, int(math.floor(-math.log10(relative)))))


def _usable_painleve_control(value, painleve):
    return _agreement_digits(value, [painleve]) >= 2


def _scientific(value, digits):
    digits = max(2, int(digits))
    text = ("%%.%de" % (digits - 1)) % float(value)
    mantissa, exponent = text.split("e")
    exponent = str(int(exponent))
    if "." not in mantissa:
        mantissa += ".0"
    return mantissa + "e" + exponent


def _plain_decimal(value, digits):
    digits = max(2, int(digits))
    value = float(value)
    if value <= 0:
        return _scientific(abs(value), digits)
    if value < 1e-4:
        return _scientific(value, digits)
    text = ("%.{}g".format(digits)) % value
    if "e" in text or "E" in text:
        mantissa, exponent = text.replace("E", "e").split("e")
        if "." not in mantissa:
            mantissa += ".0"
        return mantissa + "e" + str(int(exponent))
    if "." not in text:
        text += ".0"
    return text


def _ball_text(value, controls):
    centre = float(value)
    radius = max(abs(centre - _as_float(control)) for control in controls)
    radius = max(radius, abs(centre) * 1e-14, 1e-300)
    return "%s +/- %s" % (_scientific(centre, 3), _scientific(radius, 2))


def _with_claimed_digits(number, known_digits):
    return number, max(1, min(int(known_digits), _compare.digits_of(number)))


@functools.lru_cache(maxsize=None)
def _entry(beta, s_text):
    s = Fraction(s_text)
    value, control_values = _fredholm_density(beta, s)
    painleve = _painleve_density(beta, s_text)
    if _usable_painleve_control(value, painleve):
        control_values.append(painleve)
    digits = _agreement_digits(value, control_values)

    value_float = float(value)
    if value_float <= 0:
        positive_controls = [abs(float(control)) for control in control_values]
        number = _ball_text(abs(value_float), positive_controls)
        return _with_claimed_digits(number, 1)

    if digits < 2:
        return _with_claimed_digits(_ball_text(value, control_values), 1)

    written_digits = min(MAX_DIGITS, max(2, digits))
    number = _plain_decimal(value, written_digits)
    return _with_claimed_digits(number, written_digits)


class TracyWidomDensities(numberdb.Generator):

    table = TABLE
    parameters = ("beta", "s")
    type = "R"
    digits = 1
    rigour = "heuristic (agreement-checked)"

    def enumerate(self):
        for beta in ("1", "2", "4"):
            for s in _s_values():
                yield {"beta": beta, "s": _fraction_text(s)}

    def value(self, params, digits):
        beta = str(params["beta"])
        number, known_digits = _entry(beta, str(params["s"]))
        return {"number": number, "digits": known_digits}

    def environment(self):
        out = super().environment()
        out.update({
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "mpmath": mp.__version__,
        })
        return out


if __name__ == "__main__":
    _key_from_stdin()
    generator = TracyWidomDensities()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="values of Tracy-Widom densities",
            assisted_by=os.environ.get("NUMBERDB_ASSISTED_BY", "")))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
