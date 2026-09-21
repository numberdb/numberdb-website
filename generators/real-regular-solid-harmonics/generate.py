r"""Real regular solid harmonics R_{\ell m}(x,y,z) -- numberdb.org/T361

This draft stores the unnormalised real regular solid harmonics
R_{\ell m}(x,y,z), with R_{1,1}=x, R_{1,-1}=y and R_{1,0}=z.
The entries use the associated-Legendre relation

    R_{\ell 0} = r^\ell P_\ell(z/r),
    R_{\ell m} = (-1)^m r^\ell P_\ell^m(z/r) cos(m phi),
    R_{\ell,-m} = (-1)^m r^\ell P_\ell^m(z/r) sin(m phi),

where P_\ell^m carries the Condon-Shortley phase.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The values are exact rational polynomials. Before any value is returned, the
generator checks the degree-one convention, harmonicity, homogeneity, the
z-axis specialisation, and the exact unit-sphere orthogonality and norms of
all rows in the table.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import binomial
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


TID = os.environ.get("NUMBERDB_TABLE", "T361")
# Measured before publication: l <= 17 gives 324 entries, the longest entry is
# 1130 characters, and the entries block is 144 KB.  The next degree would put
# the longest entry at 1378 characters and the block at 182 KB.
MAX_DEGREE = 17

U_RING = PolynomialRing(QQ, "u")
u = U_RING.gen()

RING = PolynomialRing(QQ, ("x", "y", "z"))
x, y, z = RING.gens()
RADIUS_SQUARED = x ** 2 + y ** 2 + z ** 2


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def factorial(n):
    value = ZZ(1)
    for k in range(2, int(n) + 1):
        value *= ZZ(k)
    return value


def odd_double_factorial(n):
    n = int(n)
    if n <= 0:
        return ZZ(1)
    value = ZZ(1)
    for k in range(1, n + 1, 2):
        value *= ZZ(k)
    return value


def legendre_polynomials(up_to):
    values = [U_RING.one()]
    if up_to == 0:
        return values
    values.append(u)
    for n in range(1, up_to):
        values.append(
            ((2 * n + 1) * u * values[n] - n * values[n - 1])
            * (QQ(1) / QQ(n + 1))
        )
    return values


LEGENDRE = legendre_polynomials(MAX_DEGREE)
VALUES = {}


def derivative(polynomial, order):
    value = polynomial
    for _ in range(int(order)):
        value = value.derivative(u)
    return value


def real_part_power(m):
    value = RING.zero()
    for j in range(0, int(m) + 1, 2):
        value += (
            ZZ(-1) ** (j // 2)
            * ZZ(binomial(m, j))
            * x ** (m - j)
            * y ** j
        )
    return value


def imag_part_power(m):
    value = RING.zero()
    for j in range(1, int(m) + 1, 2):
        value += (
            ZZ(-1) ** ((j - 1) // 2)
            * ZZ(binomial(m, j))
            * x ** (m - j)
            * y ** j
        )
    return value


def angular_part(m):
    if m > 0:
        return real_part_power(m)
    if m < 0:
        return imag_part_power(-m)
    return RING.one()


def solid_harmonic(l, m):
    l = int(l)
    m = int(m)
    key = (l, m)
    if key in VALUES:
        return VALUES[key]
    if l < 0 or abs(m) > l:
        raise ValueError("inadmissible indices l=%s, m=%s" % (l, m))

    a = abs(m)
    d = derivative(LEGENDRE[l], a)
    angular = angular_part(m)
    value = RING.zero()
    for j, coefficient in d.dict().items():
        r_power = l - a - j
        if r_power < 0 or r_power % 2:
            raise ArithmeticError("unexpected Legendre derivative term")
        value += (
            QQ(coefficient)
            * RADIUS_SQUARED ** (r_power // 2)
            * z ** j
            * angular
        )
    VALUES[key] = RING(value)
    return VALUES[key]


def parameters(up_to=MAX_DEGREE):
    for l in range(int(up_to) + 1):
        for m in range(0, l + 1):
            yield {"l": str(l), "m": str(m)}
            if m:
                yield {"l": str(l), "m": str(-m)}


def laplacian(polynomial):
    return (
        polynomial.derivative(x, 2)
        + polynomial.derivative(y, 2)
        + polynomial.derivative(z, 2)
    )


def is_homogeneous(polynomial, degree):
    for exponents in polynomial.dict():
        if sum(exponents) != degree:
            return False
    return True


def restrict_z_axis(polynomial):
    return polynomial(x=0, y=0, z=z)


def sphere_integral_over_4pi(polynomial):
    total = QQ(0)
    for (ex, ey, ez), coefficient in polynomial.dict().items():
        if ex % 2 or ey % 2 or ez % 2:
            continue
        ax = ex // 2
        ay = ey // 2
        az = ez // 2
        numerator = (
            odd_double_factorial(2 * ax - 1)
            * odd_double_factorial(2 * ay - 1)
            * odd_double_factorial(2 * az - 1)
        )
        denominator = odd_double_factorial(2 * (ax + ay + az) + 1)
        total += QQ(coefficient) * QQ(numerator) / QQ(denominator)
    return total


def norm_over_4pi(l, m):
    a = abs(int(m))
    l = int(l)
    if a == 0:
        return QQ(1) / QQ(2 * l + 1)
    return QQ(factorial(l + a)) / (
        QQ(2) * QQ(2 * l + 1) * QQ(factorial(l - a))
    )


def expected_initial_values():
    return {
        (0, 0): RING.one(),
        (1, 1): x,
        (1, -1): y,
        (1, 0): z,
        (2, 0): z ** 2 - (x ** 2 + y ** 2) / QQ(2),
        (2, 1): 3 * x * z,
        (2, -1): 3 * y * z,
        (2, 2): 3 * x ** 2 - 3 * y ** 2,
        (2, -2): 6 * x * y,
    }


_CHECKED = False


def self_check():
    global _CHECKED
    if _CHECKED:
        return

    values = {
        (int(params["l"]), int(params["m"])): solid_harmonic(
            params["l"], params["m"]
        )
        for params in parameters()
    }

    for key, expected in expected_initial_values().items():
        if values[key] != expected:
            raise ArithmeticError("initial row %s is %s, not %s"
                                  % (key, values[key], expected))

    for (l, m), value in values.items():
        if laplacian(value) != 0:
            raise ArithmeticError("Laplacian is not zero at %s" % ((l, m),))
        if not is_homogeneous(value, l):
            raise ArithmeticError("row is not homogeneous at %s" % ((l, m),))
        axis = restrict_z_axis(value)
        expected_axis = z ** l if m == 0 else RING.zero()
        if axis != expected_axis:
            raise ArithmeticError("z-axis check failed at %s: %s"
                                  % ((l, m), axis))

    keys = sorted(values)
    for i, left_key in enumerate(keys):
        for right_key in keys[i:]:
            left = values[left_key]
            right = values[right_key]
            found = sphere_integral_over_4pi(left * right)
            expected = QQ(0)
            if left_key == right_key:
                expected = norm_over_4pi(*left_key)
            if found != expected:
                raise ArithmeticError(
                    "sphere orthogonality failed at %s,%s: %s != %s"
                    % (left_key, right_key, found, expected)
                )

    print("integrity checks passed for l <= %d" % MAX_DEGREE)
    print("checked harmonicity, homogeneity, z-axis values and sphere orthogonality")
    _CHECKED = True


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
        produced_by=_producer(generator),
        upsert=False,
        run=run,
        rigour=generator.rigour,
    )

    files = _source_files(generator)
    stored = []
    for name, body in sorted(files.items()):
        attach(table, name, body, run=run, message=message, rigour=generator.rigour)
        stored.append(name)

    return {
        "tid": answer.get("tid", table),
        "revision": answer.get("revision"),
        "entries": len(entries),
        "files": stored,
    }


class RealRegularSolidHarmonics(numberdb.Generator):

    table = TID
    parameters = ("l", "m")
    type = "Q[]"
    rigour = "exact"

    def enumerate(self, up_to=MAX_DEGREE):
        yield from parameters(up_to)

    def value(self, params, digits):
        self_check()
        return solid_harmonic(params["l"], params["m"])


if __name__ == "__main__":
    _key_from_stdin()
    generator = RealRegularSolidHarmonics()

    if "--publish" in sys.argv or bool(int(os.environ.get("NUMBERDB_PUBLISH", "0"))):
        print(
            fill_draft_once(
                generator,
                message="real regular solid harmonics with l <= %d" % MAX_DEGREE,
            )
        )
    elif "--preview" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "preview":
        print(generator.preview())
    else:
        report = generator.verify(sample=None)
        print(report)
        if not report.ok:
            sys.exit(1)
