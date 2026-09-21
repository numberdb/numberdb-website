"""Daubechies extremal-phase scaling filters $h^{(N)}_k$ -- numberdb.org/T391.

For each 1 <= N <= 25 and 0 <= k <= 2N - 1, this generator computes the
low-pass reconstruction filter coefficient h_k of the extremal-phase
Daubechies wavelet dbN, normalised so that sum_k h_k = sqrt(2).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The coefficients are algebraic. The generator builds the exact spectral factor
in QQbar from the Daubechies polynomial P_N(y), chooses the root outside the
unit circle from each reciprocal pair, and converts the exact algebraic
coefficients to real balls for storage. Before writing it checks the
normalisation, vanishing moments, quadrature-mirror orthogonality, and the db2
closed form.
"""

import os
import sys
from functools import lru_cache
from math import comb

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.qqbar import QQbar, _init_qqbar
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


_init_qqbar()

TABLE = os.environ.get("NUMBERDB_TABLE", "T391")
MAX_N = 25
DIGITS = 100
WORKING_GUARD = 128
CHECK_DIGITS = 160
CHECK_GUARD = 256
ROOT_SELECTION_BITS = (256, 384, 512, 768, 1024)
ZERO = QQbar(0)
ONE = QQbar(1)
TWO = QQbar(2)


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def _complex_field(digits, guard=WORKING_GUARD):
    return ComplexBallField(numberdb.bits(digits, losing=guard))


def _real_field(digits, guard=WORKING_GUARD):
    return RealBallField(numberdb.bits(digits, losing=guard))


def _norm_interval(value, bits):
    ball = ComplexBallField(bits)(value)
    return ball.real() * ball.real() + ball.imag() * ball.imag()


def _daubechies_polynomial(n):
    ring = PolynomialRing(QQ, "y")
    y = ring.gen()
    total = ring(0)
    for j in range(n):
        total += QQ(comb(n - 1 + j, j)) * y**j
    return total


def _outside_reciprocal_root(y_root):
    """The z-root outside |z|=1 for y=(2-z-z^-1)/4."""
    a = TWO - QQbar(4) * y_root
    discriminant = a * a - QQbar(4)
    square_root = discriminant.sqrt()
    candidates = ((a + square_root) / TWO, (a - square_root) / TWO)

    for bits in ROOT_SELECTION_BITS:
        norms = [_norm_interval(candidate, bits) for candidate in candidates]
        outside = [i for i, norm in enumerate(norms) if norm > 1]
        inside = [i for i, norm in enumerate(norms) if norm < 1]
        if len(outside) == 1 and len(inside) == 1:
            return candidates[outside[0]]
    raise ArithmeticError("could not separate a reciprocal root pair")


@lru_cache(maxsize=None)
def exact_filter_row(n):
    n = int(n)
    if n < 1:
        raise ValueError("N must be positive")

    ring = PolynomialRing(QQbar, "z")
    z = ring.gen()
    polynomial = (1 + z) ** n
    for y_root in _daubechies_polynomial(n).roots(QQbar, multiplicities=False):
        polynomial *= z - ring(_outside_reciprocal_root(y_root))

    polynomial *= TWO.sqrt() / polynomial(ONE)
    row = tuple(polynomial.list())
    if len(row) != 2 * n:
        raise ArithmeticError("N=%d produced %d coefficients" % (n, len(row)))
    return row


def _as_real_ball(value, digits):
    ball = _complex_field(digits)(value)
    if not ball.imag().contains_zero():
        raise ArithmeticError("coefficient has nonzero imaginary part: %s" % ball)
    return ball.real()


def filter_row(n, digits=DIGITS):
    return tuple(_as_real_ball(value, digits) for value in exact_filter_row(int(n)))


def _assert_contains_zero(label, value):
    if not value.contains_zero():
        raise ArithmeticError("%s does not contain zero: %s" % (label, value))
    field = value.parent()
    if field(value.rad()) > field(10) ** (-120):
        raise ArithmeticError("%s has too wide a zero enclosure: %s" % (label, value))


def _check_normalisation(n, row, field):
    total = sum(row, field(0))
    _assert_contains_zero("N=%d normalisation" % n, total - field(2).sqrt())


def _check_vanishing_moments(n, row):
    for moment in range(n):
        total = sum(
            ((-1) ** k) * (k ** moment) * row[k]
            for k in range(2 * n)
        )
        _assert_contains_zero("N=%d moment=%d" % (n, moment), total)


def _check_orthogonality(n, row, field):
    for shift in range(-(n - 1), n):
        total = field(0)
        for k in range(2 * n):
            other = k - 2 * shift
            if 0 <= other < 2 * n:
                total += row[k] * row[other]
        expected = field(1) if shift == 0 else field(0)
        if not (total - expected).contains_zero():
            raise ArithmeticError(
                "N=%d even autocorrelation shift %d is %s, not %s"
                % (n, shift, total, expected)
            )
        _assert_contains_zero(
            "N=%d even autocorrelation shift %d" % (n, shift), total - expected
        )


def _check_db2_closed_form(row):
    sqrt2 = TWO.sqrt()
    sqrt3 = QQbar(3).sqrt()
    expected = (
        (ONE + sqrt3) / (QQbar(4) * sqrt2),
        (QQbar(3) + sqrt3) / (QQbar(4) * sqrt2),
        (QQbar(3) - sqrt3) / (QQbar(4) * sqrt2),
        (ONE - sqrt3) / (QQbar(4) * sqrt2),
    )
    for k, (got, want) in enumerate(zip(row, expected)):
        if got != want:
            raise ArithmeticError("db2 coefficient %d disagrees" % k)


def run_integrity_checks(max_n=MAX_N):
    field = _real_field(CHECK_DIGITS, CHECK_GUARD)
    for n in range(1, max_n + 1):
        exact_row = exact_filter_row(n)
        row = tuple(_as_real_ball(value, CHECK_DIGITS) for value in exact_row)
        _check_normalisation(n, row, field)
        _check_vanishing_moments(n, row)
        _check_orthogonality(n, row, field)
        if n == 2:
            _check_db2_closed_form(exact_row)


class DaubechiesExtremalPhaseScalingFilters(numberdb.Generator):

    table = TABLE
    parameters = ("N", "k")
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self, max_n=MAX_N):
        for n in range(1, max_n + 1):
            for k in range(2 * n):
                yield {"N": str(n), "k": str(k)}

    def value(self, params, digits):
        n = int(params["N"])
        k = int(params["k"])
        return filter_row(n, digits)[k]


def fill_full_draft_once(generator, message):
    """Write the finished draft document and attach this generator."""
    import yaml
    from numberdb._generate import (
        _check_precision,
        _check_rigour,
        _producer,
        _run_name,
        _source_files,
    )
    from numberdb._write import Entries, attach, to_text

    run = _run_name(generator)
    entries = Entries(*generator.parameters)

    for params in generator.enumerate():
        params = dict(params)
        wanted = generator.digits_for(params)
        entry = generator._entry(params, wanted)
        value = entry["number"]
        identity = ",".join(str(params[name]) for name in generator.parameters)
        _check_rigour(generator, generator.table, identity, value)
        written = to_text(value, wanted, generator.format)
        _check_precision(generator.table, identity, written, wanted, lowering=False)

        record = dict(entry)
        record.pop("digits", None)
        entries.add(**params, **record, digits=wanted)

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "table.yaml"), encoding="utf8") as handle:
        document = yaml.load(handle, Loader=yaml.BaseLoader)
    document["Numbers"] = entries.as_list()

    client = numberdb.Client()
    headers = {
        "X-Produced-By": _producer(
            generator, os.environ.get("NUMBERDB_ASSISTED_BY", "")
        ),
        "X-Edit-Message": message,
        "X-Run-Id": run,
        "X-Numberdb-Client": "numberdb-python/%s" % numberdb.__version__,
    }
    answer = client.submit(
        "/api/table/%s" % str(generator.table).lstrip("tT"),
        yaml.dump(document, sort_keys=False, allow_unicode=True),
        headers,
    )

    attached = []
    for name, body in sorted(_source_files(generator).items()):
        attach(
            generator.table,
            name,
            body,
            run=run,
            client=client,
            message=message,
            rigour=generator.rigour,
        )
        attached.append(name)
    answer["attached"] = attached
    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = DaubechiesExtremalPhaseScalingFilters()
    run_integrity_checks()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_full_draft_once(
            generator,
            message="Daubechies extremal-phase scaling filter coefficients"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
