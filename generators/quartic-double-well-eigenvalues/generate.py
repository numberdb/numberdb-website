"""Eigenvalues of the quartic double well -- numberdb.org/T411

For a > 0, this table stores the eigenvalues E_n(a) of

    -y'' + (x^2 - a^2)^2 y = E y

on L^2(R), with n = 0 for the ground state.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The computation uses even and odd harmonic-oscillator Galerkin subspaces. In
the basis for -d^2 + omega^2 x^2, the operator is a symmetric banded matrix:
x^2 couples basis vectors whose indices differ by 2, and x^4 by 4. The finite
matrix eigenvalues are isolated by Sturm counts from a banded LDL^T
factorisation and by bisection.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.rational_field import QQ
from sage.rings.real_mpfi import RealIntervalField
from sage.rings.real_mpfr import RealField


A_VALUES = ("1/2", "1", "3/2", "2", "5/2", "3")
LEVELS = 10
CONFIGS = ((320, "1"), (460, "1"), (320, "13/10"), (460, "13/10"))
WORKING_BITS = 560
BISECTION_STEPS = 240

_ROOT_CACHE = {}
_CONTROLS_CHECKED = False


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _real_from_text(field, text):
    text = str(text)
    if "/" in text:
        numerator, denominator = text.split("/", 1)
        return field(QQ(int(numerator)) / QQ(int(denominator)))
    return field(text)


def _bands(size, parity, a_value, omega_text, bits=WORKING_BITS):
    field = RealField(bits)
    a = field(a_value)
    omega = _real_from_text(field, omega_text)
    a2 = a * a
    c2 = -(omega * omega + 2 * a2) / (2 * omega)
    c4 = 1 / (4 * omega * omega)
    shift = a2 * a2

    diagonal = []
    off1 = [field(0)] * size
    off2 = [field(0)] * size
    for i in range(size):
        n = parity + 2 * i
        rn = field(n)
        diagonal.append(
            omega * (2 * rn + 1)
            + shift
            + c2 * (2 * rn + 1)
            + c4 * (6 * rn * rn + 6 * rn + 3)
        )
        if i >= 1:
            m = parity + 2 * (i - 1)
            rm = field(m)
            b2 = field((m + 1) * (m + 2)).sqrt()
            b4 = 2 * (2 * rm + 3) * b2
            off1[i] = c2 * b2 + c4 * b4
        if i >= 2:
            m = parity + 2 * (i - 2)
            b4 = field((m + 1) * (m + 2) * (m + 3) * (m + 4)).sqrt()
            off2[i] = c4 * b4
    return diagonal, off1, off2


def _sturm_count(bands, energy):
    diagonal, off1, off2 = bands
    field = diagonal[0].parent()
    energy = field(energy)
    size = len(diagonal)
    d = [field(0)] * size
    l1 = [field(0)] * size
    l2 = [field(0)] * size
    negatives = 0
    for k in range(size):
        pivot = diagonal[k] - energy
        if k >= 1:
            pivot -= l1[k] * l1[k] * d[k - 1]
        if k >= 2:
            pivot -= l2[k] * l2[k] * d[k - 2]
        if pivot == 0:
            pivot = field(2) ** (-(field.prec() // 2))
        d[k] = pivot
        if pivot < 0:
            negatives += 1
        if k + 1 < size:
            numerator = off1[k + 1]
            if k >= 1:
                numerator -= l2[k + 1] * d[k - 1] * l1[k]
            l1[k + 1] = numerator / pivot
        if k + 2 < size:
            l2[k + 2] = off2[k + 2] / pivot
    return negatives


def _eigenvalue(size, parity, a_value, omega_text, index,
                bits=WORKING_BITS):
    field = RealField(bits)
    bands = _bands(size, parity, a_value, omega_text, bits)
    left = field(0)
    if _sturm_count(bands, left) > index:
        raise ArithmeticError("left endpoint is too high")
    right = field(1)
    while _sturm_count(bands, right) <= index:
        right *= 2
    for _ in range(BISECTION_STEPS):
        middle = (left + right) / 2
        if _sturm_count(bands, middle) <= index:
            left = middle
        else:
            right = middle
    return left, right


def _midpoint(bracket):
    left, right = bracket
    return (left + right) / 2


def _roots_for_config(size, omega_text, levels, a_value, bits=WORKING_BITS):
    roots = []
    for n in range(levels):
        roots.append(
            _eigenvalue(size, n % 2, a_value, omega_text, n // 2, bits))
    return roots


def _root_sets(a_text, levels=LEVELS, bits=WORKING_BITS):
    _check_controls()
    key = (str(a_text), levels, bits, CONFIGS)
    if key not in _ROOT_CACHE:
        field = RealField(bits)
        a_value = _real_from_text(field, a_text)
        roots = [
            _roots_for_config(size, omega, levels, a_value, bits)
            for size, omega in CONFIGS
        ]
        for root_set in roots:
            for left, right in zip(root_set, root_set[1:]):
                if not _midpoint(left) < _midpoint(right):
                    raise ArithmeticError("computed eigenvalues are not ordered")
        _ROOT_CACHE[key] = roots
    return _ROOT_CACHE[key]


def _agreement_interval(a_text, n, bits=WORKING_BITS):
    roots = [root_set[n] for root_set in _root_sets(a_text, bits=bits)]
    interval = RealIntervalField(bits)(
        min(left for left, _right in roots),
        max(right for _left, right in roots),
    )
    if interval.lower() == interval.upper():
        raise ArithmeticError("agreement interval has zero width")
    return interval


def _check_controls():
    global _CONTROLS_CHECKED
    if _CONTROLS_CHECKED:
        return
    _CONTROLS_CHECKED = True
    _check_pure_quartic_limit()
    _check_ronto_pollak_scaling()


def _check_pure_quartic_limit():
    expected = (
        "1.0603620904841828996470460166926635455152087285290",
        "3.7996730298013941687830941885125689577660654673274",
        "7.4556979379867383921565913471857674881378195367491",
    )
    field = RealField(WORKING_BITS)
    roots = _roots_for_config(460, "1", len(expected), field(0))
    for n, (computed, text) in enumerate(zip(roots, expected)):
        if abs(_midpoint(computed) - field(text)) > field("1e-48"):
            raise ArithmeticError(
                "a=0 pure quartic control failed at n=%d" % n)


def _check_ronto_pollak_scaling():
    field = RealField(WORKING_BITS)
    two = field(2)
    scale = two ** (field(2) / field(3))
    a2 = field(6) * two ** (-field(2) / field(3))
    a_value = a2.sqrt()
    shift = a2 * a2
    expected = (
        "-6.64272703",
        "-6.64062823",
        "-2.45118605",
        "-2.3155705",
        "0.41561275",
        "1.67849653",
    )
    roots = _roots_for_config(460, "1", len(expected), a_value)
    for n, (computed, text) in enumerate(zip(roots, expected)):
        scaled = (_midpoint(computed) - shift) / scale
        if abs(scaled - field(text)) > field("5e-8"):
            raise ArithmeticError(
                "Ronto-Pollak double-well control failed at n=%d" % n)


class QuarticDoubleWellEigenvalues(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T411")
    parameters = ("a", "n")
    type = "R"
    digits = 50
    rigour = "heuristic (agreement-checked)"

    def enumerate(self):
        for a in A_VALUES:
            for n in range(LEVELS):
                yield {"a": a, "n": str(n)}

    def value(self, params, digits):
        if digits > self.digits:
            raise ValueError("this generator was measured for 50 digits")
        return _agreement_interval(params["a"], int(params["n"]))


if __name__ == "__main__":
    _key_from_stdin()
    generator = QuarticDoubleWellEigenvalues()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="filled quartic double well eigenvalues"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
