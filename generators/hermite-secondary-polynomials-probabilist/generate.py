"""Secondary polynomials of the Hermite polynomials in probabilist's convention -- numberdb.org/T372

For the probabilist's Hermite polynomial He_n, this stores

    q_n(x) = int_{-infinity}^{infinity}
             (He_n(t) - He_n(x)) / (t - x)
             exp(-t^2/2) / sqrt(2*pi) dt,

the secondary polynomial taken against the standard normal probability
density. Thus q_0 = 0, q_1 = 1, q_2 = x, and q_3 = x^2 - 2.
Listed for 0 <= n <= 50, the range of the table of He_n.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

On the NumberDB build machine, where arguments are not passed through
agents/sage.sh, publish with:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
          agents/sage.sh generate.py

**Exact.** Every coefficient is a Sage integer. The polynomials come from the
recurrence q_0 = 0, q_1 = 1, q_(n+1) = x q_n - n q_(n-1), the monic Hermite
recurrence with the numerator-polynomial initial values.

**Every entry is checked before it is returned**, against a computation that
shares no code with the recurrence: the defining integral, evaluated exactly
from the closed form of He_n and the standard normal moments. The continued
fraction Pade property is also checked from the moments. A polynomial failing
any of these is an error, not a table.

Answers numberdb-data#93, for the Hermite sequence in probabilist's convention.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


#: The range of T104, the table of Hermite polynomials in probabilist's
#: convention. Measured before filling the draft: q_50 is under 800 characters,
#: comfortably below the readability target used for polynomial tables.
UP_TO = 50

RING = PolynomialRing(ZZ, "x")
X = RING.gen()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def double_factorial_odd(bound):
    """1 * 3 * ... * bound, with (-1)!! = 1."""
    if bound <= 0:
        return ZZ(1)
    value = ZZ(1)
    for k in range(1, bound + 1, 2):
        value *= ZZ(k)
    return value


def normal_moment(n):
    """The n-th moment of the standard normal distribution."""
    if n % 2:
        return ZZ(0)
    return double_factorial_odd(n - 1)


def hermite_recurrence(up_to):
    """He_0, ..., He_up_to exactly in ZZ[x]."""
    values = [RING(1)]
    if up_to >= 1:
        values.append(X)
    for n in range(1, up_to):
        values.append(X * values[n] - ZZ(n) * values[n - 1])
    return values


def secondary_recurrence(up_to):
    """q_0, ..., q_up_to by the numerator-polynomial recurrence."""
    values = [RING(0)]
    if up_to >= 1:
        values.append(RING(1))
    for n in range(1, up_to):
        values.append(X * values[n] - ZZ(n) * values[n - 1])
    return values


def hermite_closed_form(n):
    """He_n from its closed form, independent of the recurrence."""
    polynomial = RING(0)
    factorial_n = ZZ(n).factorial()
    for r in range(n // 2 + 1):
        denominator = ZZ(2) ** r * ZZ(r).factorial() * ZZ(n - 2 * r).factorial()
        coefficient = factorial_n // denominator
        if r % 2:
            coefficient = -coefficient
        polynomial += coefficient * X ** (n - 2 * r)
    return polynomial


def from_definition(polynomial):
    """The secondary polynomial from the defining integral and moments."""
    secondary = RING(0)
    for degree, coefficient in enumerate(polynomial.list()):
        if coefficient == 0:
            continue
        for i in range(degree):
            secondary += coefficient * normal_moment(i) * X ** (degree - 1 - i)
    return secondary


def reversed_coefficients(polynomial, degree):
    """Coefficients of u^degree * polynomial(1/u)."""
    original = polynomial.list()
    return [
        original[degree - i] if degree - i < len(original) else ZZ(0)
        for i in range(degree + 1)
    ]


def product_coefficient(left, right, index):
    total = ZZ(0)
    for i, coefficient in enumerate(left):
        j = index - i
        if 0 <= j < len(right):
            total += coefficient * right[j]
    return total


def pade_property(hermite, secondary, n):
    """Whether q_n/He_n matches the Cauchy-transform series through u^(2n)."""
    if n == 0:
        return secondary == 0
    denominator = reversed_coefficients(hermite, n)
    numerator = reversed_coefficients(secondary, n)
    cauchy = [ZZ(0)] + [normal_moment(i) for i in range(2 * n)]
    for exponent in range(2 * n + 1):
        left = product_coefficient(denominator, cauchy, exponent)
        right = numerator[exponent] if exponent < len(numerator) else ZZ(0)
        if left != right:
            return False
    return True


_HERMITE = hermite_recurrence(UP_TO)
_SECONDARY = secondary_recurrence(UP_TO)


def checked(n):
    """q_n, after the recurrence and independent checks have agreed."""
    n = int(n)
    if n < 0:
        raise ValueError("n must be nonnegative, not %s" % n)
    if n > UP_TO:
        raise ValueError("this draft covers n <= %d" % UP_TO)

    hermite = _HERMITE[n]
    secondary = _SECONDARY[n]
    closed = hermite_closed_form(n)

    if hermite != closed:
        raise ArithmeticError("n=%d: the Hermite recurrence and closed form disagree" % n)
    if secondary != from_definition(closed):
        raise ArithmeticError("n=%d: the recurrence and the definition disagree" % n)
    if not pade_property(hermite, secondary, n):
        raise ArithmeticError("n=%d: the Pade property failed" % n)

    if n == 0:
        if secondary != 0:
            raise ArithmeticError("q_0 is not 0")
        return secondary
    if secondary.degree() != n - 1:
        raise ArithmeticError(
            "n=%d: degree %d, not %d" % (n, secondary.degree(), n - 1)
        )
    if secondary(-X) != (-1) ** (n - 1) * secondary:
        raise ArithmeticError("n=%d: q_n does not have the parity of n - 1" % n)
    if secondary.leading_coefficient() != 1:
        raise ArithmeticError("n=%d: q_n is not monic" % n)
    if n % 2 == 0 and secondary(0) != 0:
        raise ArithmeticError("n=%d: even q_n should vanish at 0" % n)
    if n % 2 == 1:
        m = (n - 1) // 2
        expected = (-1) ** m * ZZ(2) ** m * ZZ(m).factorial()
        if secondary(0) != expected:
            raise ArithmeticError(
                "n=%d: q_n(0) is %s, not %s" % (n, secondary(0), expected)
            )
    return secondary


def run_integrity_checks():
    for n in range(UP_TO + 1):
        checked(n)
    longest = max((len(str(checked(n))), n) for n in range(UP_TO + 1))
    print("integrity checks passed for %d secondary Hermite polynomials" % (UP_TO + 1))
    print("matched the defining integral from closed-form He_n for every row")
    print("Pade property matched the standard-normal moments through u^(2n)")
    print("longest polynomial has %d characters at n=%d" % longest)


class ProbabilistHermiteSecondary(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T372")
    parameters = ("n",)
    type = "Z[]"
    rigour = "exact"

    def enumerate(self, up_to=UP_TO):
        for n in range(up_to + 1):
            yield {"n": str(n)}

    def value(self, params, digits):
        return checked(params["n"])


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
        attach(table, name, body, run=run, message=message, rigour=generator.rigour)

    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = ProbabilistHermiteSecondary()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(
            fill_draft_once(
                generator,
                message=(
                    "fill secondary polynomials of probabilist Hermite polynomials "
                    "from the exact numerator-polynomial recurrence"
                ),
            )
        )
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
