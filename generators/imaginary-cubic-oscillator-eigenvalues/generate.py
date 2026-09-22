"""Eigenvalues of the imaginary cubic oscillator -- numberdb.org/T407

The first five eigenvalues of -y'' + i*x^3*y = E*y on L^2(R).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The computation uses harmonic-oscillator Galerkin truncations. Multiplying
the nth basis vector by i^n turns the matrix for -d^2 + i*x^3 into a real
banded matrix: -d^2 couples levels differing by 2, and i*x^3 gives real
skew couplings between levels differing by 1 and 3. Roots of the truncated
determinant are found by bisection, and each stored value is the interval
spanned by two truncation sizes and two basis frequencies.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.real_mpfi import RealIntervalField
from sage.rings.real_mpfr import RealField


# The range is deliberately short. With the same method, the comparison
# (N=140,160 and omega=1.3,1.5) retained only 5.1 digits by n=17. For
# n=0..4, these stronger settings retained at least 56.7 decimal digits.
LEVELS = 5
CONFIGS = ((320, "1.39"), (360, "1.39"), (320, "1.41"), (360, "1.41"))
WORKING_BITS = 560
BISECTION_STEPS = 185
SCAN_STEP = "0.25"

HANDY_BOUNDS = (
    ("1.15626707198811324", "1.15626707198811335"),
    ("4.109228752806", "4.109228752812"),
    ("7.5622738549", "7.5622738551"),
    ("11.314421818", "11.314421824"),
    ("15.29155375037", "15.29155375041"),
)

_ROOT_CACHE = {}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _entry(field, omega, row, column):
    n = column
    offset = row - column
    if offset == 0:
        return omega * field(2 * n + 1) / 2
    if offset == -2 and n >= 2:
        return omega * field(n * (n - 1)).sqrt() / 2
    if offset == 2:
        return omega * field((n + 1) * (n + 2)).sqrt() / 2

    denominator = (field(2) * omega) ** (field(3) / field(2))
    if offset == -3 and n >= 3:
        return field(n * (n - 1) * (n - 2)).sqrt() / denominator
    if offset == -1 and n >= 1:
        return -field(3 * n) * field(n).sqrt() / denominator
    if offset == 1:
        return field(3 * (n + 1)) * field(n + 1).sqrt() / denominator
    if offset == 3:
        return -field((n + 1) * (n + 2) * (n + 3)).sqrt() / denominator
    return field(0)


def _base_rows(size, omega_text, bits):
    field = RealField(bits)
    omega = field(omega_text)
    rows = []
    for row_index in range(size):
        row = {}
        for column in range(max(0, row_index - 3),
                            min(size, row_index + 4)):
            value = _entry(field, omega, row_index, column)
            if value:
                row[column] = value
        rows.append(row)
    return rows


def _determinant(base_rows, energy, bits):
    field = RealField(bits)
    rows = [row.copy() for row in base_rows]
    energy = field(energy)
    for index in range(len(rows)):
        rows[index][index] = rows[index].get(index, field(0)) - energy

    determinant = field(1)
    size = len(rows)
    for column in range(size):
        pivot = rows[column].get(column, field(0))
        if pivot == 0:
            return field(0)
        determinant *= pivot
        for row_index in range(column + 1, min(size, column + 4)):
            below = rows[row_index].get(column, field(0))
            if not below:
                continue
            factor = below / pivot
            rows[row_index][column] = field(0)
            for update in range(column + 1, min(size, column + 4)):
                rows[row_index][update] = (
                    rows[row_index].get(update, field(0))
                    - factor * rows[column].get(update, field(0)))
    return determinant


def _sign(value):
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _bisect(base_rows, left, right, bits):
    field = RealField(bits)
    left = field(left)
    right = field(right)
    left_value = _determinant(base_rows, left, bits)
    right_value = _determinant(base_rows, right, bits)
    if _sign(left_value) == _sign(right_value):
        raise ValueError("the bracket [%s, %s] does not change sign"
                         % (left, right))

    for _ in range(BISECTION_STEPS):
        middle = (left + right) / 2
        middle_value = _determinant(base_rows, middle, bits)
        if _sign(middle_value) == _sign(left_value):
            left = middle
            left_value = middle_value
        else:
            right = middle
            right_value = middle_value
    return (left + right) / 2


def _scan_roots(size, omega_text, count, bits):
    field = RealField(bits)
    rows = _base_rows(size, omega_text, bits)
    step = field(SCAN_STEP)
    left = field(0)
    left_value = _determinant(rows, left, bits)
    left_sign = _sign(left_value)
    roots = []
    right = step
    while len(roots) < count and right < 50:
        right_value = _determinant(rows, right, bits)
        right_sign = _sign(right_value)
        if left_sign and right_sign and left_sign != right_sign:
            roots.append(_bisect(rows, left, right, bits))
        left = right
        left_value = right_value
        left_sign = _sign(left_value)
        right += step
    if len(roots) != count:
        raise ValueError("found %s roots, wanted %s" % (len(roots), count))
    return roots


def _roots_near(size, omega_text, guesses, bits):
    field = RealField(bits)
    rows = _base_rows(size, omega_text, bits)
    roots = []
    for guess in guesses:
        width = field("0.01")
        while True:
            left = field(guess) - width
            right = field(guess) + width
            left_sign = _sign(_determinant(rows, left, bits))
            right_sign = _sign(_determinant(rows, right, bits))
            if left_sign and right_sign and left_sign != right_sign:
                roots.append(_bisect(rows, left, right, bits))
                break
            width *= 2
            if width > 2:
                raise ValueError(
                    "could not bracket a root near %s for N=%s, omega=%s"
                    % (guess, size, omega_text))
    return roots


def _root_sets(bits=WORKING_BITS):
    key = (bits, LEVELS, CONFIGS)
    if key in _ROOT_CACHE:
        return _ROOT_CACHE[key]

    first_size, first_omega = CONFIGS[0]
    roots = [_scan_roots(first_size, first_omega, LEVELS, bits)]
    for size, omega_text in CONFIGS[1:]:
        roots.append(_roots_near(size, omega_text, roots[0], bits))
    _check_handy_bounds(roots, bits)
    _ROOT_CACHE[key] = roots
    return roots


def _check_handy_bounds(root_sets, bits):
    field = RealField(bits)
    for index, (lower_text, upper_text) in enumerate(HANDY_BOUNDS):
        lower = field(lower_text)
        upper = field(upper_text)
        for roots in root_sets:
            value = roots[index]
            if not (lower <= value <= upper):
                raise ArithmeticError(
                    "E_%s=%s is outside Handy's EMM bounds [%s, %s]"
                    % (index, value, lower, upper))


def _agreement_interval(index, bits=WORKING_BITS):
    roots = [root_set[index] for root_set in _root_sets(bits)]
    low = min(roots)
    high = max(roots)
    interval = RealIntervalField(bits)(low, high)
    if interval.lower() == interval.upper():
        raise ArithmeticError("the agreement interval has zero width")
    return interval


class ImaginaryCubicOscillatorEigenvalues(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE") or "T407"
    parameters = ("n",)
    type = "R"
    digits = 50
    rigour = "heuristic (agreement-checked)"

    def enumerate(self):
        for n in range(LEVELS):
            yield {"n": n}

    def value(self, params, digits):
        if digits > self.digits:
            raise ValueError("this generator was measured for 50 digits")
        return _agreement_interval(int(params["n"]))


if __name__ == "__main__":
    _key_from_stdin()
    generator = ImaginaryCubicOscillatorEigenvalues()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="filled first five imaginary cubic oscillator eigenvalues"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
