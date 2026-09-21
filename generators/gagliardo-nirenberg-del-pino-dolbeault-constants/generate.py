"""Sharp Gagliardo-Nirenberg constants of Del Pino and Dolbeault -- numberdb.org/T358.

This generator fills T358 with the sharp constants A_{n,a} in the
Del Pino-Dolbeault Gagliardo-Nirenberg inequality for 3 <= n <= 20 and
rational a of denominator at most 8 in the admissible open range, together
with the Sobolev endpoint a = n/(n-2).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import os
import re
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


TABLE = os.environ.get("NUMBERDB_TABLE", "T358")
DIGITS = 100
WORKING_GUARD = 160
CHECK_GUARD = 256
MAX_N = 20
MAX_DENOMINATOR = 8
SOBOLEV_TABLE = "T92"
FRACTIONAL_SOBOLEV_TABLE = "T354"


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def _real_field(digits, guard=WORKING_GUARD):
    return RealBallField(numberdb.bits(digits, losing=guard))


def _theta(n, a):
    n = QQ(n)
    a = QQ(a)
    return n * (a - 1) / (a * (n + 2 - (n - 2) * a))


def _endpoint(n):
    return QQ(n) / QQ(n - 2)


def _admissible_exponents(n):
    endpoint = _endpoint(n)
    values = {endpoint}
    for denominator in range(1, MAX_DENOMINATOR + 1):
        for numerator in range(denominator + 1, int(endpoint * denominator) + 1):
            a = QQ(numerator) / QQ(denominator)
            if QQ(1) < a < endpoint and a.denominator() <= MAX_DENOMINATOR:
                values.add(a)
    return sorted(values)


def _constant(n, a, digits, guard=WORKING_GUARD):
    field = _real_field(digits, guard)
    n = QQ(n)
    a = QQ(a)
    y = (a + 1) / (a - 1)
    theta = _theta(n, a)
    n_ball = field(n)
    a_ball = field(a)
    y_ball = field(y)
    theta_ball = field(theta)
    return (
        (y_ball * field((a - 1) ** 2) / (2 * field.pi() * n_ball)) ** (theta_ball / 2)
        * ((2 * y_ball - n_ball) / (2 * y_ball)) ** (1 / (2 * a_ball))
        * (y_ball.gamma() / field(y - n / 2).gamma()) ** (theta_ball / n_ball)
    )


def _integral_power_norm(n, exponent, s, digits, guard=CHECK_GUARD):
    field = _real_field(digits, guard)
    n = QQ(n)
    exponent = QQ(exponent)
    s = QQ(s)
    alpha = s * exponent
    integral = (
        field.pi() ** (field(n) / 2)
        * field(alpha - n / 2).gamma()
        / field(alpha).gamma()
    )
    return integral ** (field(QQ(1) / exponent))


def _gradient_norm(n, s, digits, guard=CHECK_GUARD):
    field = _real_field(digits, guard)
    n = QQ(n)
    s = QQ(s)
    beta = 2 * s + 2
    integral = (
        2
        * field(n)
        * field(s) ** 2
        * field.pi() ** (field(n) / 2)
        * field(beta - n / 2 - 1).gamma()
        / field(beta).gamma()
    )
    return integral.sqrt()


def _extremal_ratio(n, a, digits, guard=CHECK_GUARD):
    field = _real_field(digits, guard)
    n = QQ(n)
    a = QQ(a)
    s = QQ(1) / (a - 1)
    theta = _theta(n, a)
    left = _integral_power_norm(n, 2 * a, s, digits, guard)
    grad = _gradient_norm(n, s, digits, guard)
    middle = _integral_power_norm(n, a + 1, s, digits, guard)
    return left / (grad ** field(theta) * middle ** field(1 - theta))


def _sobolev_p2_values():
    table = numberdb.table(SOBOLEV_TABLE)
    values = {}
    for n_text, by_p in (table.get("Numbers") or {}).items():
        if "2" not in by_p:
            continue
        by_q = by_p["2"]
        if len(by_q) != 1:
            raise ArithmeticError("unexpected T92 p=2 row for n=%s" % n_text)
        values[ZZ(n_text)] = next(iter(by_q.values()))
    return values


def _fractional_sobolev_s1_values():
    table = numberdb.table(FRACTIONAL_SOBOLEV_TABLE)
    values = {}
    for n_text, by_s in (table.get("Numbers") or {}).items():
        if "1" in by_s:
            values[ZZ(n_text)] = by_s["1"]
    return values


def _stored_decimal_ball(text, digits, guard=CHECK_GUARD):
    field = _real_field(digits, guard)
    if isinstance(text, dict):
        text = text["number"]
    value = field(str(text))
    found = re.fullmatch(r"-?\d+\.(\d+)(?:[eE](-?\d+))?", str(text))
    if not found:
        return value
    places = len(found.group(1)) - int(found.group(2) or 0)
    return value.add_error(field(10) ** (-places))


def _entry_number(entry):
    if isinstance(entry, dict):
        return entry.get("number")
    return entry


class GagliardoNirenbergDelPinoDolbeaultConstants(numberdb.Generator):
    """Generator for T358, the Del Pino-Dolbeault Gagliardo-Nirenberg constants."""

    table = TABLE
    parameters = ("n", "a")
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self, max_n=MAX_N):
        for n in range(3, max_n + 1):
            for a in _admissible_exponents(n):
                yield {"n": str(n), "a": str(a)}

    def value(self, params, digits):
        n = ZZ(params["n"])
        a = QQ(params["a"])
        value = _constant(n, a, digits)
        if a == _endpoint(n):
            return {
                "number": value,
                "comment": "Sobolev endpoint: this value is $1/S_{%s,2}$." % n,
            }
        return value


def run_integrity_checks():
    field = _real_field(DIGITS, CHECK_GUARD)
    generator = GagliardoNirenbergDelPinoDolbeaultConstants()
    values = {}
    widest_radius = field(0)
    widest_at = None

    for params in generator.enumerate():
        n = ZZ(params["n"])
        a = QQ(params["a"])
        value = _constant(n, a, DIGITS, CHECK_GUARD)
        values[(n, a)] = value
        ratio = _extremal_ratio(n, a, DIGITS, CHECK_GUARD)
        if not (value - ratio).contains_zero():
            raise ArithmeticError(
                "extremal ratio check failed at n=%s, a=%s: %s vs %s"
                % (n, a, value, ratio)
            )
        radius = field(value.rad())
        if radius > widest_radius:
            widest_radius = radius
            widest_at = (n, a)

    sobolev = _sobolev_p2_values()
    fractional = _fractional_sobolev_s1_values()
    endpoint_checked = []
    t92_checked = []
    for n in range(3, MAX_N + 1):
        if ZZ(n) not in fractional:
            raise ArithmeticError("T354 has no s=1 row for n=%s" % n)
        a = _endpoint(n)
        product = values[(ZZ(n), a)] * _stored_decimal_ball(fractional[ZZ(n)], DIGITS)
        if not (product - 1).contains_zero():
            raise ArithmeticError(
                "fractional Sobolev endpoint check failed at n=%s: product %s"
                % (n, product)
            )
        endpoint_checked.append(n)
        if ZZ(n) in sobolev:
            product_t92 = values[(ZZ(n), a)] * _stored_decimal_ball(sobolev[ZZ(n)], DIGITS)
            if not (product_t92 - 1).contains_zero():
                raise ArithmeticError(
                    "T92 endpoint check failed at n=%s: product %s" % (n, product_t92)
                )
            t92_checked.append(n)

    print("integrity checks passed for %d entries" % len(values))
    print("widest value ball radius: %s at n=%s, a=%s" % (
        widest_radius, widest_at[0], widest_at[1]))
    print("Sobolev endpoints checked against %s for n=%s" % (
        FRACTIONAL_SOBOLEV_TABLE, ",".join(str(n) for n in endpoint_checked)))
    print("Sobolev endpoints also checked against %s for n=%s" % (
        SOBOLEV_TABLE, ",".join(str(n) for n in t92_checked)))


def run_stored_checks():
    table = numberdb.table(TABLE)
    numbers = table.get("Numbers") or {}
    if not numbers:
        print("stored checks skipped: %s has no stored numbers yet" % TABLE)
        return

    checked = 0
    endpoint_checked = 0
    sobolev = _sobolev_p2_values()
    fractional = _fractional_sobolev_s1_values()
    for n_text, by_a in numbers.items():
        n = ZZ(n_text)
        for a_text, entry in by_a.items():
            a = QQ(a_text)
            stored = _stored_decimal_ball(_entry_number(entry), DIGITS)
            ratio = _extremal_ratio(n, a, DIGITS, CHECK_GUARD)
            if not (stored - ratio).contains_zero():
                raise ArithmeticError(
                    "stored extremal check failed at n=%s, a=%s: %s vs %s"
                    % (n, a, stored, ratio)
                )
            checked += 1
            if a == _endpoint(n):
                product = stored * _stored_decimal_ball(fractional[n], DIGITS)
                if not (product - 1).contains_zero():
                    raise ArithmeticError(
                        "stored fractional endpoint check failed at n=%s: product %s"
                        % (n, product)
                    )
                if n in sobolev:
                    product_t92 = stored * _stored_decimal_ball(sobolev[n], DIGITS)
                    if not (product_t92 - 1).contains_zero():
                        raise ArithmeticError(
                            "stored T92 endpoint check failed at n=%s: product %s"
                            % (n, product_t92)
                        )
                endpoint_checked += 1
    print("stored checks passed for %d entries and %d endpoints" % (
        checked, endpoint_checked))


def fill_draft_once(generator, message):
    """Fill a fresh prose draft without the client's empty upsert probe."""
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
        attach(table, name, body, run=run, message=message, rigour=generator.rigour)

    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = GagliardoNirenbergDelPinoDolbeaultConstants()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="Del Pino-Dolbeault Gagliardo-Nirenberg constants"))
    else:
        run_stored_checks()
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
