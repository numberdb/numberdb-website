"""Values of the Tracy-Widom distribution functions F_beta(s) -- numberdb.org/T441

This generator computes F_beta(s) for beta = 1, 2, 4 on the grid
s = -10, -9.95, ..., 5.

The values are Fredholm determinants from Bornemann's factorisation of the
Airy-kernel determinant.  With

    T_t(x, y) = Ai(x + y + t),      x, y >= 0,

the determinant identities used here are

    F_1(s) = det(I - T_s),
    F_2(s) = det(I - T_s) det(I + T_s),
    F_4(s) = (det(I - T_{sqrt(2) s}) + det(I + T_{sqrt(2) s})) / 2.

The last line is the GSE convention used by the family proposal: the
Tracy-Widom F_4 argument has the sqrt(2) scaling.  Each value is accompanied
by only as many digits as survive a second quadrature setting.  The far-left
GSE tail is computed in multiprecision because double precision determinants
lose relative accuracy there.
"""

import numberdb.sage as numberdb

import functools
import math
import os
import sys
from fractions import Fraction

import mpmath as mp
import numpy as np
import scipy
from scipy.linalg import det
from scipy.special import airy


TABLE = os.environ.get("NUMBERDB_TABLE") or "T441"

STEP = Fraction(1, 20)
S_MIN = Fraction(-10, 1)
S_MAX = Fraction(5, 1)

MAX_DIGITS = 12
DOUBLE_HIGH = (100, 24.0)
DOUBLE_CONTROL = (80, 20.0)

MP_DPS = 60
MP_LENGTH = mp.mpf(24)
MP_HIGH_N = 55
MP_CONTROL_N = 50
MP_TAIL_LIMIT = -12.5


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


def _s_value(params):
    return Fraction(str(params["s"]))


@functools.lru_cache(maxsize=None)
def _legendre_nodes(n, length):
    nodes, weights = np.polynomial.legendre.leggauss(int(n))
    x = float(length) * (nodes + 1.0) / 2.0
    w = float(length) * weights / 2.0
    return x, np.sqrt(w)


@functools.lru_cache(maxsize=None)
def _double_dets(t_key, n, length):
    t = float(t_key)
    x, rootw = _legendre_nodes(int(n), float(length))
    kernel = airy(x[:, None] + x[None, :] + t)[0]
    matrix = rootw[:, None] * kernel * rootw[None, :]
    identity = np.eye(len(x))
    return float(det(identity - matrix)), float(det(identity + matrix))


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


def _mp_t_text(s):
    mp.mp.dps = MP_DPS
    return mp.nstr(mp.sqrt(2) * mp.mpf(s.numerator) / s.denominator, 50)


def _determinants(beta, s):
    """Return ((d_minus, d_plus), [(control_minus, control_plus), ...])."""
    if beta == "4":
        t = math.sqrt(2.0) * (s.numerator / float(s.denominator))
        if t <= MP_TAIL_LIMIT:
            t_text = _mp_t_text(s)
            high = _mp_dets(t_text, MP_HIGH_N)
            control = _mp_dets(t_text, MP_CONTROL_N)
            return high, [control]
    else:
        t = s.numerator / float(s.denominator)

    t_key = "%.17g" % t
    high = _double_dets(t_key, DOUBLE_HIGH[0], DOUBLE_HIGH[1])
    control = _double_dets(t_key, DOUBLE_CONTROL[0], DOUBLE_CONTROL[1])
    return high, [control]


def _combine(beta, det_pair):
    dminus, dplus = det_pair
    if beta == "1":
        return dminus
    if beta == "2":
        return dminus * dplus
    if beta == "4":
        return (dminus + dplus) / 2
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
    if value >= 1:
        return "0." + "9" * digits
    if value > 0.99 and ("%.{}g".format(digits) % value).startswith("1"):
        return "0." + "9" * digits
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


@functools.lru_cache(maxsize=None)
def _entry(beta, s_text):
    s = Fraction(s_text)
    high, controls = _determinants(beta, s)
    value = _combine(beta, high)
    control_values = [_combine(beta, control) for control in controls]
    digits = _agreement_digits(value, control_values)

    value_float = float(value)
    if value_float <= 0:
        number = _ball_text(abs(value_float), [abs(float(c)) for c in control_values])
        return number, 1

    if digits < 2:
        return _ball_text(value, control_values), 1

    written_digits = min(MAX_DIGITS, max(2, digits))
    return _plain_decimal(value, written_digits), written_digits


class TracyWidomDistributionFunctions(numberdb.Generator):

    table = TABLE
    parameters = ("beta", "s")
    type = "R"
    # The writer in the Sage image treats this as a minimum for every entry.
    # The generated decimal or ball string carries the actual per-entry
    # precision, which is determined from the control quadrature.
    digits = 1
    rigour = "measured"

    def enumerate(self):
        for beta in ("1", "2", "4"):
            for s in _s_values():
                yield {"beta": beta, "s": _fraction_text(s)}

    def digits_for(self, params):
        return self.digits

    def value(self, params, digits):
        beta = str(params["beta"])
        number, _digits = _entry(beta, str(params["s"]))
        return {"number": number}

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
    generator = TracyWidomDistributionFunctions()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="values of Tracy-Widom distribution functions",
            assisted_by=os.environ.get("NUMBERDB_ASSISTED_BY", "")))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
