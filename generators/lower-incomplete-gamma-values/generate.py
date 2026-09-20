"""Values of the lower incomplete gamma function gamma(a,x) -- numberdb.org/T352

For each a in (1/2)Z with -1/2 <= a <= 5/2, excluding the pole a = 0,
and each argument x = k/10 with 1 <= k <= 100, this stores the lower
incomplete gamma function gamma(a,x).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

For this repository's build environment, use:

    $ agents/sage.sh generate.py
    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 agents/sage.sh generate.py

Values are computed as real parts of complex balls using arb's complete and
upper incomplete gamma functions. The imaginary parts are checked to contain
zero. The ``self_check()`` function verifies the recurrence, special-value
identities, and the Kummer M relation.
"""

import os
import sys
from math import factorial

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.rational_field import QQ


TABLE = "T352"
WORKING_GUARD = 64
A_VALUES = tuple(
    sorted(
        (QQ(n) / QQ(2) for n in range(-1, 6) if n != 0),
        key=lambda a: (abs(a), a < 0, a),
    )
)
X_VALUES = tuple(QQ(k) / QQ(10) for k in range(1, 101))


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _field(digits):
    return ComplexBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def _real(value, label):
    if not value.real().is_finite() or not value.imag().is_finite():
        raise ArithmeticError("computed a non-finite ball for %s" % (label,))
    if not value.imag().contains_zero():
        raise ArithmeticError("expected a real value for %s: %s" % (label, value))
    return value.real()


def _gamma_lower(a, x, digits):
    field = _field(digits)
    aa = field(a)
    xx = field(x)
    value = aa.gamma() - aa.gamma_inc(xx)
    return _real(value, "gamma(%s,%s)" % (a, x))


def _integer_formula(n, x, digits):
    field = _field(digits)
    total = field(0)
    for k in range(n + 1):
        total += field(x) ** k / field(factorial(k))
    value = field(factorial(n)) * (field(1) - (-field(x)).exp() * total)
    return _real(value, "integer formula n=%s, x=%s" % (n, x))


def _kummer_formula(a, x, digits):
    field = _field(digits)
    aa = field(a)
    xx = field(x)
    value = (xx ** aa) * (-xx).hypergeometric([aa], [aa + 1]) / aa
    return _real(value, "Kummer formula a=%s, x=%s" % (a, x))


def _check_contains_zero(value, label):
    if hasattr(value, "real") and hasattr(value, "imag"):
        if not value.real().is_finite() or not value.imag().is_finite():
            raise ArithmeticError(
                "%s produced a non-finite difference" % (label,))
        if not value.real().contains_zero() or not value.imag().contains_zero():
            raise ArithmeticError("%s failed: %s" % (label, value))
        return
    if not value.is_finite():
        raise ArithmeticError("%s produced a non-finite difference" % (label,))
    if not value.contains_zero():
        raise ArithmeticError("%s failed: %s" % (label, value))


class LowerIncompleteGammaValues(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", TABLE)
    parameters = ("a", "x")
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self):
        for a in A_VALUES:
            for x in X_VALUES:
                yield {"a": str(a), "x": str(x)}

    def value(self, params, digits):
        return _gamma_lower(QQ(params["a"]), QQ(params["x"]), digits)


def self_check(digits=100):
    values = {}
    for a in A_VALUES:
        for x in X_VALUES:
            values[(a, x)] = _gamma_lower(a, x, digits)

    field = _field(digits)

    for a in A_VALUES:
        if a + 1 not in A_VALUES:
            continue
        for x in X_VALUES:
            expected = field(a) * values[(a, x)] - field(x) ** field(a) * (
                -field(x)).exp()
            _check_contains_zero(
                values[(a + 1, x)] - expected,
                "recurrence at a=%s, x=%s" % (a, x),
            )

    for x in X_VALUES:
        expected = field.pi().sqrt() * field(x).sqrt().erf()
        _check_contains_zero(
            values[(QQ(1) / QQ(2), x)] - expected,
            "erf identity at x=%s" % (x,),
        )

    for n in (0, 1):
        a = QQ(n + 1)
        for x in X_VALUES:
            _check_contains_zero(
                values[(a, x)] - _integer_formula(n, x, digits),
                "integer formula at a=%s, x=%s" % (a, x),
            )

    for a in A_VALUES:
        for x in X_VALUES:
            _check_contains_zero(
                values[(a, x)] - _kummer_formula(a, x, digits),
                "Kummer formula at a=%s, x=%s" % (a, x),
            )

    print("self-check passed: recurrence, erf identity, integer rows, and Kummer formula")


def fill_draft_once(generator, message):
    """Fill a fresh draft without the empty upsert probe."""
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
        produced_by=_producer(
            generator,
            assisted_by=os.environ.get("NUMBERDB_ASSISTED_BY", "codex-cli"),
        ),
        upsert=False,
        run=run,
        rigour=generator.rigour,
    )

    stored = []
    for name, body in sorted(_source_files(generator).items()):
        attach(table, name, body, run=run, message=message,
               rigour=generator.rigour)
        stored.append(name)

    return {
        "tid": answer.get("tid", table),
        "revision": answer.get("revision"),
        "entries": len(entries),
        "files": stored,
    }


def main():
    _key_from_stdin()
    generator = LowerIncompleteGammaValues()
    if os.environ.get("NUMBERDB_SELF_CHECK") == "1":
        self_check(generator.digits)
        return
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="lower incomplete gamma values on the half-integer grid"))
        return
    if os.environ.get("NUMBERDB_PUBLISH") == "preview" or "--preview" in sys.argv:
        print(generator.preview())
        return
    report = generator.verify(sample=None)
    print(report)
    sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
