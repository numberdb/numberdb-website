"""Eigenvalues of the quartic anharmonic oscillator -- numberdb.org/T404.

This computes E_n(lambda), the eigenvalues of

    -y'' + (x^2 + lambda x^4) y = E y

on L^2(R), with n = 0 for the ground state. The listed draft uses
lambda = 10^k for -3 <= k <= 3 and n = 0, ..., 10.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

Under the repository's agent runner, pipe the API key on stdin:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 \
        NUMBERDB_PUBLISH=1 agents/sage.sh generators/quartic-anharmonic-oscillator-eigenvalues/generate.py

The computation uses the Hermite-function basis of the harmonic oscillator.
The finite Galerkin matrix is pentadiagonal after separating parity, and its
eigenvalues are isolated by Sturm counts from an LDL^T factorisation rather
than by a dense eigensolver.
"""

import os
import sys
from functools import lru_cache

import numberdb.sage as numberdb
from numberdb._write import to_text
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_mpfi import RealIntervalField
from sage.rings.real_mpfr import RealField


TABLE = os.environ.get("NUMBERDB_TABLE", "T404")
DIGITS = 50
WORKING_DIGITS = 80
LAMBDA_VALUES = ("1/1000", "1/100", "1/10", "1", "10", "100", "1000")
MAX_LEVEL = 10
BASIS_SIZES = (180, 260)
OMEGA_FACTOR = QQ(59) / QQ(50)

BENCHMARKS = {
    ("1/1000", 0): "1.00074869267318569953848500930",
    ("1/1000", 2): "5.00971187278810748703699224736",
    ("1/1000", 4): "9.03054956607471081538727951165",
    ("1/1000", 6): "13.0631635776784842765593222201",
    ("1/1000", 8): "17.1074577926534729419799765127",
    ("1/1000", 10): "21.1633381057038205341724410607",
    ("1/100", 0): "1.00737367208138246053384390598",
    ("1/100", 2): "5.09393913274230922537730488023",
    ("1/100", 4): "9.28947981631188566821916117362",
    ("1/100", 6): "13.5867158015895900122761824546",
    ("1/100", 8): "17.9795105837112184301777564069",
    ("1/100", 10): "22.4626056421661578127162214995",
    ("1/10", 0): "1.06528550954371768885709162879",
    ("1/10", 2): "5.74795926883356330473350311848",
    ("1/10", 4): "11.0985956226330430110864587493",
    ("1/10", 6): "16.9547946861441513376926165088",
    ("1/10", 8): "23.2295521799392890706470874343",
    ("1/10", 10): "29.8665252346712780183652389140",
    ("1", 0): "1.39235164153029185565750787661",
    ("1", 2): "8.65504995775930968811653945738",
    ("1", 4): "18.0575574363032528947712396465",
    ("1", 6): "28.8353384595042488401336357155",
    ("1", 8): "40.6903860821064447252789314816",
    ("1", 10): "53.4491021396652646008315064598",
    ("10", 0): "2.44917407211838691826879390619",
    ("10", 2): "16.6359214924137577833619179322",
    ("10", 4): "35.8851712222538737122812690982",
    ("10", 6): "58.2412987397532402851042176544",
    ("10", 8): "83.0038670375852900204307960934",
    ("10", 10): "109.772570864332974973673879837",
    ("100", 0): "4.99941754513758782929463203735",
    ("100", 2): "34.8739842619947775464121035612",
    ("100", 4): "75.8770040286697241808400119029",
    ("100", 6): "123.640697626678167674110965464",
    ("100", 8): "176.628655957714353603604728193",
    ("100", 10): "233.966225876235944863913218793",
    ("1000", 0): "10.6397887113280460636220426694",
    ("1000", 2): "74.6814042001648132608522697991",
    ("1000", 4): "162.802374196975230178579711889",
    ("1000", 6): "265.519951678280012371053662368",
    ("1000", 8): "379.511311178728667693290769435",
    ("1000", 10): "502.886399284715911615348140903",
}


def configure_key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        numberdb.configure(api_key=token)


def _lambda_field(text, field):
    return field(QQ(text))


def _base_omega(lambda_text):
    field = RealField(200)
    lam = _lambda_field(lambda_text, field)
    root = (field(1) + field(3) * lam) ** (field(1) / field(3))
    floor = field("1.3")
    return floor if root < floor else root


def _omega_texts(lambda_text):
    base = _base_omega(lambda_text)
    field = base.parent()
    return (str(base), str(base * field(OMEGA_FACTOR)))


@lru_cache(maxsize=None)
def _matrix_arrays(lambda_text, parity, size, omega_text, bits):
    field = RealField(bits)
    lam = _lambda_field(lambda_text, field)
    omega = field(omega_text)
    diag = []
    off1 = []
    off2 = []
    x2_scale = field(1) / (field(2) * omega)
    x4_scale = field(1) / (field(4) * omega * omega)

    for i in range(size):
        k = parity + 2 * i
        x2_diag = field(2 * k + 1) * x2_scale
        x4_diag = field(3 * (2 * k * k + 2 * k + 1)) * x4_scale
        diag.append(
            field(2 * k + 1) * omega
            + (field(1) - omega * omega) * x2_diag
            + lam * x4_diag
        )
        if i < size - 1:
            step = field((k + 1) * (k + 2)).sqrt()
            x2 = step * x2_scale
            x4 = step * field(2 * k + 3) / (field(2) * omega * omega)
            off1.append((field(1) - omega * omega) * x2 + lam * x4)
        if i < size - 2:
            step = field((k + 1) * (k + 2) * (k + 3) * (k + 4)).sqrt()
            off2.append(lam * step * x4_scale)

    return tuple(diag), tuple(off1), tuple(off2)


def _sturm_count(diag, off1, off2, point):
    field = point.parent()
    size = len(diag)
    pivots = [field(0)] * size
    first = [field(0)] * size
    second = [field(0)] * size
    negative = 0

    for i in range(size):
        pivot = diag[i] - point
        if i >= 1:
            pivot -= first[i] * first[i] * pivots[i - 1]
        if i >= 2:
            pivot -= second[i] * second[i] * pivots[i - 2]
        if not pivot:
            raise ArithmeticError("Sturm pivot vanished at row %s" % i)
        pivots[i] = pivot
        if pivot < 0:
            negative += 1
        if i + 1 < size:
            correction = field(0)
            if i >= 1:
                correction = second[i + 1] * pivots[i - 1] * first[i]
            first[i + 1] = (off1[i] - correction) / pivot
        if i + 2 < size:
            second[i + 2] = off2[i] / pivot

    return negative


def _safe_sturm_count(diag, off1, off2, point):
    try:
        return _sturm_count(diag, off1, off2, point)
    except ArithmeticError as trouble:
        if "pivot vanished" not in str(trouble):
            raise
        field = point.parent()
        shifted = point + field(2) ** (-(field.precision() // 2))
        return _sturm_count(diag, off1, off2, shifted)


@lru_cache(maxsize=None)
def _estimate(lambda_text, n, size, omega_text):
    working_bits = numberdb.bits(WORKING_DIGITS, losing=80)
    parity = n % 2
    index = n // 2
    diag, off1, off2 = _matrix_arrays(lambda_text, parity, size, omega_text, working_bits)
    field = diag[0].parent()
    low = field(0)
    high = field(max(diag) + 10)
    while _safe_sturm_count(diag, off1, off2, high) <= index:
        high *= 2
    for _ in range(numberdb.bits(WORKING_DIGITS, losing=30)):
        middle = (low + high) / 2
        if _safe_sturm_count(diag, off1, off2, middle) <= index:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def _agreement_interval(lambda_text, n, digits):
    interval_field = RealIntervalField(numberdb.bits(digits + 18, losing=80))
    interval = None
    for size in BASIS_SIZES:
        for omega_text in _omega_texts(lambda_text):
            value = _estimate(lambda_text, n, size, omega_text)
            part = interval_field(value.str(digits=digits + 18))
            interval = part if interval is None else interval.union(part)
    return interval


def _written_digits(interval, digits):
    text = to_text(interval, digits)
    return sum(1 for char in text if char.isdigit()), text


def _printed_decimal_interval(field, text):
    places = len(text.split(".", 1)[1]) if "." in text else 0
    center = field(text)
    unit = field(10) ** (-places)
    return field(center - 2 * unit, center + 2 * unit)


def run_integrity_checks():
    harmonic_tolerance = RealField(120)("1e-70")
    for n in range(MAX_LEVEL + 1):
        value = _agreement_interval("0", n, 60).center()
        if abs(value - ZZ(2 * n + 1)) > harmonic_tolerance:
            raise ArithmeticError("harmonic oscillator control failed at n=%s" % n)

    benchmark_field = RealIntervalField(numberdb.bits(70, losing=64))
    for (lambda_text, n), reference_text in BENCHMARKS.items():
        computed = _agreement_interval(lambda_text, n, 60)
        reference = _printed_decimal_interval(benchmark_field, reference_text)
        if not computed.overlaps(reference):
            raise ArithmeticError(
                "benchmark disagreement at lambda=%s, n=%s" % (lambda_text, n)
            )

    worst = None
    for lambda_text in LAMBDA_VALUES:
        for n in range(MAX_LEVEL + 1):
            interval = _agreement_interval(lambda_text, n, DIGITS)
            count, text = _written_digits(interval, DIGITS)
            if count < DIGITS:
                raise ArithmeticError(
                    "only %s digits retained at lambda=%s, n=%s: %s"
                    % (count, lambda_text, n, text)
                )
            item = (count, lambda_text, n)
            worst = item if worst is None or count < worst[0] else worst
    print("worst retained digits: %s at lambda=%s, n=%s" % worst)


class QuarticAnharmonicOscillatorEigenvalues(numberdb.Generator):
    table = TABLE
    parameters = ("lambda", "n")
    type = "R"
    digits = DIGITS
    rigour = "heuristic (agreement-checked)"

    def enumerate(self):
        for lambda_text in LAMBDA_VALUES:
            for n in range(MAX_LEVEL + 1):
                yield {"lambda": lambda_text, "n": str(n)}

    def value(self, params, digits):
        lambda_text = params["lambda"]
        n = int(params["n"])
        if lambda_text not in LAMBDA_VALUES:
            raise ValueError("lambda=%s is outside this draft" % lambda_text)
        if n < 0 or n > MAX_LEVEL:
            raise ValueError("n=%s is outside this draft" % n)
        return _agreement_interval(lambda_text, n, digits)


def fill_draft_once(generator, message):
    """Fill a fresh draft without the client's empty upsert probe."""
    from numberdb._generate import (
        _check_precision,
        _check_rigour,
        _producer,
        _run_name,
        _source_files,
    )
    from numberdb._write import Entries, attach, submit_entries

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
    generator = QuarticAnharmonicOscillatorEigenvalues()
    mode = os.environ.get("NUMBERDB_PUBLISH")
    if "--publish" in sys.argv or mode == "1":
        run_integrity_checks()
        print(fill_draft_once(
            generator,
            message="quartic anharmonic oscillator eigenvalues"))
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
