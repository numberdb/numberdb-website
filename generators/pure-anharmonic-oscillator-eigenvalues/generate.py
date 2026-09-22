"""Eigenvalues of the pure quartic, sextic, octic and decic oscillators -- numberdb.org/T408.

This computes the first three eigenvalues E_n^(m) of

    -y'' + x^(2m) y = E y

on L^2(R), for m = 2, 3, 4, 5 and n = 0, 1, 2.  The finite Galerkin
matrices are formed in a harmonic-oscillator basis and their eigenvalues are
located by bisection with an LDL^T Sturm count.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

For this repository's build environment, use:

    $ agents/sage.sh generate.py
    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 agents/sage.sh generate.py
"""

import os
import sys
from decimal import Decimal
from functools import lru_cache

import numberdb.sage as numberdb
import sage.rings.polynomial.laurent_polynomial_ring
from sage.rings.rational_field import QQ
from sage.rings.real_mpfr import RealField


TABLE = os.environ.get("NUMBERDB_TABLE", "T408")
DIGITS = 50
MAX_N = 2

CONFIGS = {
    2: ((700, "2"), (900, "2"), (700, "5/2"), (900, "5/2")),
    3: ((700, "2"), (900, "2"), (700, "5/2"), (900, "5/2")),
    4: ((800, "3"), (1000, "3"), (800, "7/2"), (1000, "7/2")),
    5: ((1600, "4"), (2000, "4"), (1600, "5"), (2000, "5")),
}

QUARTIC_REFERENCE = {
    0: "1.060362090484182899647046016693",
    1: "3.799673029801394168783094188513",
    2: "7.455697937986738392156591347186",
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def _basis_size(full_N, parity):
    return (full_N + (1 - parity)) // 2


def _apply_x_power(start, power, omega, field):
    q = (field(2) * omega).sqrt() ** -1
    state = {start: field(1)}
    for _ in range(power):
        new = {}
        for j, coefficient in state.items():
            up = coefficient * q * field(j + 1).sqrt()
            new[j + 1] = new.get(j + 1, field(0)) + up
            if j:
                down = coefficient * q * field(j).sqrt()
                new[j - 1] = new.get(j - 1, field(0)) + down
        state = new
    return state


def _lower_block(m, full_N, omega, field, parity):
    dim = _basis_size(full_N, parity)
    rows = [dict() for _ in range(dim)]

    def add(row, column, value):
        rows[row][column] = rows[row].get(column, field(0)) + value

    for column in range(dim):
        j = parity + 2 * column
        add(column, column, field(2 * j + 1) * omega)
        for power, scale in ((2 * m, field(1)), (2, -omega * omega)):
            for i, coefficient in _apply_x_power(j, power, omega, field).items():
                if i % 2 != parity:
                    continue
                row = (i - parity) // 2
                if column <= row < dim:
                    add(row, column, scale * coefficient)
    return rows


def _entry(rows, i, j):
    if i < j:
        i, j = j, i
    return rows[i].get(j, rows[0].get(-1, 0))


def _sturm_count(rows, x, bandwidth, field):
    dim = len(rows)
    diagonal = []
    lower = [dict() for _ in range(dim)]
    tiny = field(2) ** (-(field.precision() - 10))
    count = 0

    for k in range(dim):
        pivot = _entry(rows, k, k) - x
        for j, value in lower[k].items():
            pivot -= value * value * diagonal[j]
        if pivot == 0:
            pivot = tiny
        if pivot < 0:
            count += 1
        diagonal.append(pivot)

        for i in range(k + 1, min(dim, k + bandwidth + 1)):
            value = _entry(rows, i, k)
            for j, lower_kj in lower[k].items():
                lower_ij = lower[i].get(j)
                if lower_ij is not None:
                    value -= lower_ij * lower_kj * diagonal[j]
            if value:
                lower[i][k] = value / pivot
    return count


def _finite_eigenvalue(rows, local_index, bandwidth, field, digits):
    lo = field(0)
    hi = field(max(1, 2 * local_index + 3))
    while _sturm_count(rows, hi, bandwidth, field) <= local_index:
        hi *= 2

    for _ in range(numberdb.bits(digits, losing=100)):
        mid = (lo + hi) / 2
        if _sturm_count(rows, mid, bandwidth, field) <= local_index:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


@lru_cache(maxsize=None)
def _spectrum(m, full_N, omega_text, max_n=MAX_N, digits=DIGITS + 30):
    field = RealField(numberdb.bits(digits, losing=260))
    omega = field(QQ(omega_text))
    values = {}
    for parity in (0, 1):
        rows = _lower_block(m, full_N, omega, field, parity)
        for local in range((max_n + 2 - parity) // 2):
            n = parity + 2 * local
            values[n] = _finite_eigenvalue(rows, local, m, field, digits)
    return tuple(values[n] for n in range(max_n + 1))


def _significant_prefix(texts):
    count = 0
    for index, char in enumerate(texts[0]):
        if not all(index < len(text) and text[index] == char for text in texts):
            return count
        if char.isdigit():
            count += 1
    return count


def _agreed_value(m, n, digits):
    spectra = [_spectrum(m, full_N, omega) for full_N, omega in CONFIGS[m]]
    long_texts = [values[n].str(digits=digits + 15) for values in spectra]
    retained = _significant_prefix(long_texts)
    if retained < digits:
        raise ArithmeticError(
            "m=%d, n=%d retained only %d common digits" % (m, n, retained)
        )
    texts = [values[n].str(digits=digits) for values in spectra]
    if len(set(texts)) != 1:
        raise ArithmeticError(
            "m=%d, n=%d does not round consistently to %d digits: %s"
            % (m, n, digits, texts)
        )
    return texts[0]


def _assert_quartic_reference():
    for n, reference in QUARTIC_REFERENCE.items():
        produced = _agreed_value(2, n, 40)
        if abs(Decimal(produced) - Decimal(reference)) > Decimal("5e-31"):
            raise ArithmeticError(
                "quartic reference mismatch n=%d: %s != %s"
                % (n, produced, reference)
            )


def _assert_harmonic_control():
    values = [_spectrum(1, 80, "2", max_n=MAX_N, digits=40)[n]
              for n in range(MAX_N + 1)]
    for n, value in enumerate(values):
        expected = value.parent()(2 * n + 1)
        if abs(value - expected) > value.parent()(10) ** -30:
            raise ArithmeticError("harmonic control failed at n=%d: %s" % (n, value))


class PureAnharmonicOscillatorEigenvalues(numberdb.Generator):
    table = TABLE
    parameters = ("m", "n")
    type = "R"
    digits = DIGITS
    rigour = "heuristic (agreement-checked)"

    def enumerate(self):
        for m in (2, 3, 4, 5):
            for n in range(MAX_N + 1):
                yield {"m": str(m), "n": str(n)}

    def value(self, params, digits):
        m = int(params["m"])
        n = int(params["n"])
        if m not in CONFIGS:
            raise ValueError("m=%d is outside this table" % (m,))
        if n < 0 or n > MAX_N:
            raise ValueError("n=%d is outside this table" % (n,))
        return _agreed_value(m, n, digits)


def self_check():
    _assert_harmonic_control()
    _assert_quartic_reference()
    generator = PureAnharmonicOscillatorEigenvalues()
    values = {
        "%s,%s" % (params["m"], params["n"]): generator.value(params, DIGITS)
        for params in generator.enumerate()
    }
    print("computed %d entries" % len(values))
    print("first row", values["2,0"])


if __name__ == "__main__":
    _key_from_stdin()
    self_check()
    if (os.environ.get("NUMBERDB_SELF_CHECK_ONLY") == "1"
            or (not os.environ.get("NUMBERDB_API_KEY")
                and os.environ.get("NUMBERDB_PUBLISH") != "1")):
        sys.exit(0)
    generator = PureAnharmonicOscillatorEigenvalues()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        outcome = generator.publish(
            message="filled eigenvalues from harmonic-basis agreement checks",
            restating=os.environ.get("NUMBERDB_RESTATING") == "1",
            lowering=os.environ.get("NUMBERDB_LOWERING") == "1",
        )
        print(outcome)
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
