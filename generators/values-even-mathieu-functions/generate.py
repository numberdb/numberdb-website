"""Values of the even Mathieu functions ce_n(z,q) -- numberdb.org/T437.

This generator computes DLMF-normalised values of the even Mathieu functions
ce_n(z,q), with z measured in radians and stored by the parameter z/pi.

Run it with SageMath:

    $ sage -pip install numberdb mpmath scipy
    $ sage -python generate.py
    $ sage -python generate.py --publish

For this repository's build environment, use:

    $ agents/sage.sh agents/table-build/dry_run.py generate.py
    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
        agents/sage.sh generate.py

The computation diagonalises the truncated Fourier matrix for
-d^2/dz^2 + 2q cos(2z) in the orthonormal cosine basis. The values stored in
the table must agree between two working precisions and two truncation lengths.
"""

import math
import os
import sys
from functools import lru_cache

import numberdb.sage as numberdb
import mpmath as mp


TABLE = os.environ.get("NUMBERDB_TABLE", "T437")
DIGITS = 30
N_VALUES = tuple(range(0, 6))
Q_VALUES = ("1", "2", "5", "10")
Z_STEPS = tuple(range(0, 19))  # z/pi = step/36, from 0 to 1/2.

# (working decimal digits, largest cosine frequency included)
LOW_PROFILE = (80, 80)
HIGH_PROFILE = (110, 100)
SCIPY_TOLERANCE = mp.mpf("5e-13")


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
        numberdb.configure(api_key=token)


def _z_param(step):
    if step == 0:
        return "0"
    denominator = 36
    common = math.gcd(step, denominator)
    numerator = step // common
    denominator //= common
    if denominator == 1:
        return str(numerator)
    return "%d/%d" % (numerator, denominator)


def _z_step(params):
    text = str(params["z_over_pi"])
    if text == "0":
        return 0
    if "/" in text:
        numerator, denominator = text.split("/", 1)
        step = int(numerator) * 36 // int(denominator)
    else:
        step = int(text) * 36
    if not 0 <= step <= 18:
        raise ValueError("z/pi=%s is outside this table" % text)
    return step


def _harmonics(parity, max_frequency):
    start = int(parity)
    return tuple(range(start, int(max_frequency) + 1, 2))


def _matrix_entry_coupling(k, q):
    return mp.sqrt(2) * q if k == 0 else q


@lru_cache(maxsize=None)
def _eigensystem(q_text, parity, digits, max_frequency):
    mp.mp.dps = int(digits)
    q = mp.mpf(q_text)
    harmonics = _harmonics(parity, max_frequency)
    dimension = len(harmonics)
    matrix = mp.matrix(dimension)

    for i, k in enumerate(harmonics):
        diagonal = mp.mpf(k * k)
        if k == 1:
            diagonal += q
        matrix[i, i] = diagonal

    for i, k in enumerate(harmonics[:-1]):
        coupling = _matrix_entry_coupling(k, q)
        matrix[i, i + 1] = coupling
        matrix[i + 1, i] = coupling

    eigenvalues, eigenvectors = mp.eigsy(matrix)
    return harmonics, tuple(eigenvalues), eigenvectors


def _rank_for_n(n):
    return int(n) // 2


def _coefficients(n, q_text, profile):
    digits, max_frequency = profile
    parity = int(n) % 2
    harmonics, eigenvalues, eigenvectors = _eigensystem(
        str(q_text), parity, int(digits), int(max_frequency)
    )
    rank = _rank_for_n(n)
    coefficients = [mp.mpf(eigenvectors[row, rank]) for row in range(len(harmonics))]

    anchor = harmonics.index(int(n))
    if coefficients[anchor] < 0:
        coefficients = [-c for c in coefficients]

    return harmonics, eigenvalues[rank], coefficients


def _angle(step):
    return mp.pi * mp.mpf(step) / mp.mpf(36)


def _basis_value(k, z):
    if k == 0:
        return 1 / mp.sqrt(2)
    return mp.cos(mp.mpf(k) * z)


def _raw_value(n, q_text, step, profile):
    harmonics, _eigenvalue, coefficients = _coefficients(n, q_text, profile)
    z = _angle(step)
    total = mp.mpf("0")
    for k, coefficient in zip(harmonics, coefficients):
        total += coefficient * _basis_value(k, z)
    return total


def _format_decimal(value, digits):
    text = mp.nstr(
        value,
        n=int(digits),
        strip_zeros=False,
        min_fixed=-100,
        max_fixed=100,
    )
    if text.startswith("-0."):
        try:
            if mp.mpf(text) == 0:
                return text[1:]
        except ValueError:
            pass
    return text


def _exact_zero(n, step):
    return int(n) % 2 == 1 and int(step) == 18


def ce_value_text(n, q_text, step, digits):
    if _exact_zero(n, step):
        return 0

    low = _raw_value(n, q_text, step, LOW_PROFILE)
    high = _raw_value(n, q_text, step, HIGH_PROFILE)
    low_text = _format_decimal(low, digits)
    high_text = _format_decimal(high, digits)
    if low_text != high_text:
        raise ArithmeticError(
            "ce_%s(q=%s,z=%s/36*pi) disagrees between profiles: %s vs %s"
            % (n, q_text, step, low_text, high_text)
        )
    return high_text


def _q_zero_control(n, step, digits):
    mp.mp.dps = digits + 20
    z = _angle(step)
    if int(n) == 0:
        return 1 / mp.sqrt(2)
    return mp.cos(mp.mpf(n) * z)


def _norm_squared(coefficients):
    total = mp.mpf("0")
    for coefficient in coefficients:
        total += coefficient * coefficient
    return total


def _matrix_residual(n, q_text, profile):
    harmonics, eigenvalue, coefficients = _coefficients(n, q_text, profile)
    q = mp.mpf(q_text)
    residual = mp.mpf("0")
    for i, k in enumerate(harmonics):
        left = mp.mpf(k * k) * coefficients[i]
        if k == 1:
            left += q * coefficients[i]
        if i > 0:
            left += _matrix_entry_coupling(harmonics[i - 1], q) * coefficients[i - 1]
        if i + 1 < len(harmonics):
            left += _matrix_entry_coupling(k, q) * coefficients[i + 1]
        residual = max(residual, abs(left - eigenvalue * coefficients[i]))
    return residual


def run_integrity_checks():
    for n in N_VALUES:
        for step in Z_STEPS:
            got = _format_decimal(_raw_value(n, "0", step, HIGH_PROFILE), DIGITS)
            expected = _format_decimal(_q_zero_control(n, step, DIGITS), DIGITS)
            if got != expected:
                raise ArithmeticError(
                    "q=0 control failed for n=%d step=%d: %s != %s"
                    % (n, step, got, expected)
                )

    for q_text in Q_VALUES:
        for n in N_VALUES:
            _progress("checking coefficients for n=%d, q=%s" % (n, q_text))
            _harmonics, _eigenvalue, coefficients = _coefficients(
                n, q_text, HIGH_PROFILE
            )
            if abs(_norm_squared(coefficients) - 1) > mp.mpf("1e-80"):
                raise ArithmeticError("normalization failed for n=%d, q=%s" % (n, q_text))
            if _matrix_residual(n, q_text, HIGH_PROFILE) > mp.mpf("1e-80"):
                raise ArithmeticError("matrix residual failed for n=%d, q=%s" % (n, q_text))

    import scipy.special as scipy_special

    for q_text in Q_VALUES:
        q_float = float(q_text)
        for n in N_VALUES:
            for step in Z_STEPS:
                ours = mp.mpf(ce_value_text(n, q_text, step, DIGITS))
                degrees = 5.0 * step
                scipy_value = mp.mpf(str(scipy_special.mathieu_cem(n, q_float, degrees)[0]))
                if abs(ours - scipy_value) > SCIPY_TOLERANCE:
                    raise ArithmeticError(
                        "SciPy check failed for n=%d, q=%s, z=%d degrees: %s vs %s"
                        % (n, q_text, int(degrees), ours, scipy_value)
                    )


class EvenMathieuFunctionValues(numberdb.Generator):
    table = TABLE
    parameters = ("n", "q", "z_over_pi")
    type = "R"
    digits = DIGITS
    rigour = "heuristic (agreement-checked)"

    def enumerate(self):
        for n in N_VALUES:
            for q_text in Q_VALUES:
                for step in Z_STEPS:
                    yield {
                        "n": str(n),
                        "q": q_text,
                        "z_over_pi": _z_param(step),
                    }

    def value(self, params, digits):
        n = int(params["n"])
        q_text = str(params["q"])
        step = _z_step(params)
        if n not in N_VALUES:
            raise ValueError("n=%s is outside this table" % n)
        if q_text not in Q_VALUES:
            raise ValueError("q=%s is outside this table" % q_text)
        return ce_value_text(n, q_text, step, digits)


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


if __name__ == "__main__":
    _key_from_stdin()
    generator = EvenMathieuFunctionValues()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="fill even Mathieu function values by Fourier matrix agreement"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
