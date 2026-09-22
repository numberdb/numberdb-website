"""Eigenvalues of pure even-power oscillators -- numberdb.org/T405.

For m >= 2 this computes E_n^(m), the eigenvalues of

    -y'' + x^(2m) y = E y

on L^2(R), with n = 0 for the ground state.  The listed draft uses
m = 2, 3, 4, 5 and n = 0, ..., 19.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

Under the repository's agent runner, pipe the API key on stdin:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 \
        NUMBERDB_PUBLISH=1 agents/sage.sh generators/pure-even-power-oscillator-eigenvalues/generate.py

The computation uses the Hermite-function basis of the harmonic oscillator.
The finite Galerkin matrix is banded, and its eigenvalues are isolated by
Sturm counts from an LDL^T factorisation rather than by a dense eigensolver.
"""

import os
import sys
from functools import lru_cache

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_double import RDF
from sage.rings.real_mpfi import RealIntervalField
from sage.rings.real_mpfr import RealField


TABLE = os.environ.get("NUMBERDB_TABLE", "T405")
DIGITS = 50
WORKING_BITS = 260
BISECTION_STEPS = 230
M_VALUES = (2, 3, 4, 5)
MAX_LEVEL = 19
BASIS_SIZES = (96, 112)

# The two frequencies are deliberately close rather than identical tests of
# the same basis.  They grow with the power of the confining potential.
OMEGAS = {
    1: (QQ(1), QQ(1)),
    2: (QQ(5) / QQ(2), QQ(7) / QQ(2)),
    3: (QQ(3), QQ(9) / QQ(2)),
    4: (QQ(7) / QQ(2), QQ(11) / QQ(2)),
    5: (QQ(4), QQ(6)),
}

QUARTIC_GROUND_STATE = "1.060362090484182899647046016692"


def configure_key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        numberdb.configure(api_key=token)


def _add_to(mapping, key, value):
    mapping[key] = mapping.get(key, value.parent()(0)) + value


def _x_power_rows(power, parity, size, omega, field):
    """Rows of x^power on one parity subspace of the oscillator basis."""
    selected = {parity + 2 * r: r for r in range(size)}
    rows = [dict() for _ in range(size)]
    scale = field(1) / (field(2) * omega).sqrt()

    for col in range(size):
        full_col = parity + 2 * col
        vector = {full_col: field(1)}
        for _ in range(power):
            updated = {}
            for index, coefficient in vector.items():
                if index:
                    _add_to(updated, index - 1,
                            coefficient * field(index).sqrt() * scale)
                _add_to(updated, index + 1,
                        coefficient * field(index + 1).sqrt() * scale)
            vector = updated
        for full_row, coefficient in vector.items():
            row = selected.get(full_row)
            if row is not None:
                rows[row][col] = coefficient
    return rows


@lru_cache(maxsize=None)
def _matrix_rows(m, parity, size, omega_text, bits):
    field = RealField(bits)
    omega = field(QQ(omega_text))
    x2 = _x_power_rows(2, parity, size, omega, field)
    x2m = _x_power_rows(2 * m, parity, size, omega, field)
    rows = [dict() for _ in range(size)]

    for row in range(size):
        full_row = parity + 2 * row
        columns = set(x2[row]) | set(x2m[row]) | {row}
        for col in columns:
            value = x2m[row].get(col, field(0)) - omega * omega * x2[row].get(col, field(0))
            if row == col:
                value += field(2 * full_row + 1) * omega
            if value:
                rows[row][col] = value
    return tuple(tuple(sorted(row.items())) for row in rows)


def _row_dicts(packed):
    return [dict(row) for row in packed]


def _entry(rows, i, j, zero):
    return rows[i].get(j, rows[j].get(i, zero))


def _sturm_count(packed_rows, band, point):
    rows = _row_dicts(packed_rows)
    size = len(rows)
    field = point.parent()
    zero = field(0)
    pivots = []
    lower = [dict() for _ in range(size)]
    count = 0

    for i in range(size):
        pivot = rows[i].get(i, zero) - point
        for k, coefficient in lower[i].items():
            pivot -= coefficient * coefficient * pivots[k]
        if not pivot:
            raise ArithmeticError("Sturm pivot vanished at row %s" % i)
        pivots.append(pivot)
        if pivot < 0:
            count += 1

        for j in range(i + 1, min(size, i + band + 1)):
            value = _entry(rows, j, i, zero)
            for k, coefficient in lower[i].items():
                other = lower[j].get(k)
                if other is not None:
                    value -= other * coefficient * pivots[k]
            lower[j][i] = value / pivot
    return count


def _bisect_eigenvalue(packed_rows, band, index):
    field = RealField(WORKING_BITS)
    low = field(0)
    high = field(2)
    while _sturm_count(packed_rows, band, high) <= index:
        high *= 2
    for _ in range(BISECTION_STEPS):
        middle = (low + high) / 2
        if _sturm_count(packed_rows, band, middle) <= index:
            low = middle
        else:
            high = middle
    return (low + high) / 2


@lru_cache(maxsize=None)
def _spectrum(m, parity, size, omega_text, count):
    packed = _matrix_rows(m, parity, size, omega_text, WORKING_BITS)
    band = max(1, m)
    return tuple(_bisect_eigenvalue(packed, band, k) for k in range(count))


def _estimate(m, n, size, omega):
    parity = n % 2
    index = n // 2
    values = _spectrum(m, parity, size, str(omega), MAX_LEVEL // 2 + 1)
    return values[index]


def _decimal(value, digits):
    return value.str(digits=digits)


def _agreement_interval(m, n, digits):
    interval_field = RealIntervalField(numberdb.bits(digits + 12))
    interval = None
    for size in BASIS_SIZES:
        for omega in OMEGAS[m]:
            value = _estimate(m, n, size, omega)
            part = interval_field(_decimal(value, digits + 12))
            interval = part if interval is None else interval.union(part)
    return interval


def _relative_error(a, b):
    field = RealField(120)
    return abs((field(a) - field(b)) / field(b))


def _wkb(m, n):
    field = RealField(120)
    half = QQ(1) / QQ(2)
    m_q = QQ(m)
    factor = (field.pi().sqrt()
              * field(QQ(3) / QQ(2) + QQ(1) / (2 * m_q)).gamma()
              / field(QQ(1) + QQ(1) / (2 * m_q)).gamma())
    exponent = field(2 * m_q / (m_q + 1))
    return (factor * field(QQ(n) + half)) ** exponent


def run_integrity_checks():
    harmonic = _spectrum(1, 0, 24, "1", 5)
    for index, value in enumerate(harmonic):
        expected = ZZ(4 * index + 1)
        if abs(value - expected) > RealField(WORKING_BITS)("1e-60"):
            raise ArithmeticError("harmonic even control failed at %s" % index)
    harmonic = _spectrum(1, 1, 24, "1", 5)
    for index, value in enumerate(harmonic):
        expected = ZZ(4 * index + 3)
        if abs(value - expected) > RealField(WORKING_BITS)("1e-60"):
            raise ArithmeticError("harmonic odd control failed at %s" % index)

    quartic = _agreement_interval(2, 0, 60)
    reference = RealIntervalField(numberdb.bits(70))(QUARTIC_GROUND_STATE)
    if not quartic.overlaps(reference):
        raise ArithmeticError("quartic ground state disagrees with the reference value")

    for m in M_VALUES:
        e10 = _agreement_interval(m, 10, 30).center()
        e19 = _agreement_interval(m, 19, 30).center()
        if _relative_error(e19, _wkb(m, 19)) >= _relative_error(e10, _wkb(m, 10)):
            raise ArithmeticError("WKB control did not improve from n=10 to n=19 for m=%s" % m)


class PureEvenPowerOscillatorEigenvalues(numberdb.Generator):
    table = TABLE
    parameters = ("m", "n")
    type = "R"
    digits = DIGITS
    rigour = "heuristic (agreement-checked)"

    def enumerate(self):
        for m in M_VALUES:
            for n in range(MAX_LEVEL + 1):
                yield {"m": str(m), "n": str(n)}

    def value(self, params, digits):
        m = int(params["m"])
        n = int(params["n"])
        if m not in M_VALUES:
            raise ValueError("m=%s is outside this draft" % m)
        if n < 0 or n > MAX_LEVEL:
            raise ValueError("n=%s is outside this draft" % n)
        return _agreement_interval(m, n, digits)


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
        attach(table, name, body, run=run, message=message,
               rigour=generator.rigour)
    return answer


def main():
    configure_key_from_stdin()
    generator = PureEvenPowerOscillatorEigenvalues()
    mode = os.environ.get("NUMBERDB_PUBLISH")
    if "--publish" in sys.argv or mode == "1":
        run_integrity_checks()
        print(fill_draft_once(
            generator,
            message="pure even-power oscillator eigenvalues for m=2..5"))
        return
    if "--preview" in sys.argv or mode == "preview":
        run_integrity_checks()
        print(generator.preview())
        return
    run_integrity_checks()
    report = generator.verify(sample=None)
    print(report)
    sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
