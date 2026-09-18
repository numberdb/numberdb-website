r"""Clebsch-Gordan coefficients and Wigner 3j symbols -- numberdb.org/T252

This draft stores every nonzero Clebsch-Gordan coefficient
<j1 m1, j2 m2 | j3 m> with j1, j2, j3 <= 2, and the corresponding Wigner
3j symbol (j1 j2 j3; m1 m2 -m), using the same six angular-momentum
parameters and a `normalisation` parameter.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The values are computed from the Racah finite sum in exact rational
arithmetic, represented as a rational multiple of the square root of a
rational number, and then converted to Arb balls for storage. Values that are
exact rationals are written exactly. Before any entry is returned, the whole
range is checked against Sage's exact Wigner and Clebsch-Gordan functions,
against the row-by-row conversion between the two normalisations, against the
orthogonality relations for Clebsch-Gordan coefficients, and against the
Legendre triple-product identity in the m_i = 0 special case.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import factorial
from sage.functions.wigner import wigner_3j as sage_wigner_3j
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


TID = "T252"
TWICE_J_UP_TO = 4
DIGITS = 100
WORKING_GUARD = 96


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def half_text(twice):
    twice = int(twice)
    if twice % 2 == 0:
        return str(twice // 2)
    sign = "-" if twice < 0 else ""
    return "%s%d/2" % (sign, abs(twice))


def parse_half(text):
    value = QQ(str(text))
    twice = 2 * value
    if twice.denominator() != 1:
        raise ValueError("%s is not an integer or half-integer" % (text,))
    return int(twice)


def half(twice):
    return QQ(twice) / QQ(2)


def sage_half(twice):
    if twice % 2 == 0:
        return ZZ(twice // 2)
    return QQ(twice) / QQ(2)


def phase(exponent_twice):
    if exponent_twice % 2:
        raise ValueError("phase exponent is not an integer")
    return ZZ(-1) ** (exponent_twice // 2)


def factorial_int(n):
    if n < 0:
        raise ValueError("negative factorial argument %d" % (n,))
    return ZZ(factorial(int(n)))


def factorial_ratio(numerators, denominators):
    value = QQ(1)
    for n in numerators:
        value *= QQ(factorial_int(n))
    for n in denominators:
        value /= QQ(factorial_int(n))
    return value


def triangle(a, b, c):
    return abs(a - b) <= c <= a + b and (a + b + c) % 2 == 0


def magnetic_values(j_twice):
    return range(-j_twice, j_twice + 1, 2)


def admissible_coupling(a, b, c, p, q, r):
    return (
        triangle(a, b, c)
        and -a <= p <= a
        and -b <= q <= b
        and -c <= r <= c
        and (a - p) % 2 == 0
        and (b - q) % 2 == 0
        and (c - r) % 2 == 0
        and p + q == r
    )


def wigner_multiplier_radicand(a, b, c, p, q, r):
    """Return q, R with Wigner 3j = q * sqrt(R), for m3 = -m."""
    if not admissible_coupling(a, b, c, p, q, r):
        return QQ(0), QQ(1)

    # Wigner's lower row is m1, m2, -m, so m3_twice = -r.
    A = (a + b - c) // 2
    B = (a - b + c) // 2
    C = (-a + b + c) // 2
    D = (a + b + c) // 2 + 1

    m_factor_args = [
        (a + p) // 2,
        (a - p) // 2,
        (b + q) // 2,
        (b - q) // 2,
        (c - r) // 2,
        (c + r) // 2,
    ]
    radicand = factorial_ratio([A, B, C] + m_factor_args, [D])

    s_lower = max(0, -((c - b + p) // 2), -((c - a - q) // 2))
    s_upper = min(A, (a - p) // 2, (b + q) // 2)
    total = QQ(0)
    for s in range(s_lower, s_upper + 1):
        denominator_args = [
            s,
            A - s,
            (a - p) // 2 - s,
            (b + q) // 2 - s,
            (c - b + p) // 2 + s,
            (c - a - q) // 2 + s,
        ]
        denominator = ZZ(1)
        for n in denominator_args:
            denominator *= factorial_int(n)
        total += QQ((-1) ** s) / QQ(denominator)

    if total == 0:
        return QQ(0), QQ(1)
    return QQ(phase(a - b + r)) * total, radicand


def clebsch_multiplier_radicand(a, b, c, p, q, r):
    multiplier, radicand = wigner_multiplier_radicand(a, b, c, p, q, r)
    if multiplier == 0:
        return QQ(0), QQ(1)
    return QQ(phase(a - b + r)) * multiplier, QQ(c + 1) * radicand


def exact_rational_square_root(value):
    numerator = ZZ(value.numerator())
    denominator = ZZ(value.denominator())
    n_root, n_remainder = numerator.sqrtrem()
    d_root, d_remainder = denominator.sqrtrem()
    if n_remainder == 0 and d_remainder == 0:
        return QQ(n_root) / QQ(d_root)
    return None


def exact_or_ball(multiplier, radicand, digits):
    if multiplier == 0:
        return QQ(0)
    exact = exact_rational_square_root(radicand)
    if exact is not None:
        return multiplier * exact
    field = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
    value = field(multiplier) * field(radicand).sqrt()
    if not value.is_finite():
        raise ArithmeticError("non-finite ball for %s * sqrt(%s)" % (multiplier, radicand))
    return value


def exact_pair(normalisation, a, b, c, p, q, r):
    if normalisation == "wigner-3j":
        return wigner_multiplier_radicand(a, b, c, p, q, r)
    if normalisation == "clebsch-gordan":
        return clebsch_multiplier_radicand(a, b, c, p, q, r)
    raise ValueError("unknown normalisation %r" % (normalisation,))


def exact_value(normalisation, a, b, c, p, q, r, digits=DIGITS):
    multiplier, radicand = exact_pair(normalisation, a, b, c, p, q, r)
    return exact_or_ball(multiplier, radicand, digits)


def overlaps(value, other, digits=DIGITS):
    field = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
    return field(value).overlaps(field(other))


def nonzero_entry(a, b, c, p, q, r):
    multiplier, _ = wigner_multiplier_radicand(a, b, c, p, q, r)
    return multiplier != 0


def enumerate_indices(up_to=TWICE_J_UP_TO):
    for a in range(up_to + 1):
        for b in range(up_to + 1):
            for c in range(abs(a - b), min(up_to, a + b) + 1):
                if not triangle(a, b, c):
                    continue
                for p in magnetic_values(a):
                    for q in magnetic_values(b):
                        r = p + q
                        if admissible_coupling(a, b, c, p, q, r) and nonzero_entry(a, b, c, p, q, r):
                            yield a, b, c, p, q, r


def sage_value(normalisation, a, b, c, p, q, r):
    j1, j2, j3 = sage_half(a), sage_half(b), sage_half(c)
    m1, m2, m = sage_half(p), sage_half(q), sage_half(r)
    if normalisation == "wigner-3j":
        return sage_wigner_3j(j1, j2, j3, m1, m2, -m)
    if normalisation == "clebsch-gordan":
        return phase(a - b + r) * (2 * j3 + 1).sqrt() * sage_wigner_3j(
            j1, j2, j3, m1, m2, -m
        )
    raise ValueError("unknown normalisation %r" % (normalisation,))


def legendre_triple_integral(l1, l2, l3):
    from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing

    R = PolynomialRing(QQ, "x")
    x = R.gen()
    polynomials = [R(1)]
    if max(l1, l2, l3) > 0:
        polynomials.append(x)
    for n in range(1, max(l1, l2, l3)):
        polynomials.append(
            ((2 * n + 1) * x * polynomials[n] - n * polynomials[n - 1])
            * (QQ(1) / QQ(n + 1))
        )
    product = polynomials[l1] * polynomials[l2] * polynomials[l3]
    total = QQ(0)
    for degree, coefficient in product.dict().items():
        if degree % 2 == 0:
            total += QQ(2) * QQ(coefficient) / QQ(degree + 1)
    return total


_CHECKED = False


def self_check():
    global _CHECKED
    if _CHECKED:
        return

    field = RealBallField(numberdb.bits(DIGITS, losing=WORKING_GUARD))
    for a, b, c, p, q, r in enumerate_indices():
        wigner = exact_value("wigner-3j", a, b, c, p, q, r)
        clebsch = exact_value("clebsch-gordan", a, b, c, p, q, r)

        if not overlaps(wigner, sage_value("wigner-3j", a, b, c, p, q, r)):
            raise ArithmeticError("Wigner value disagrees with Sage at %s" % ((a, b, c, p, q, r),))
        if not overlaps(clebsch, sage_value("clebsch-gordan", a, b, c, p, q, r)):
            raise ArithmeticError("Clebsch-Gordan value disagrees with Sage at %s" % ((a, b, c, p, q, r),))

        phase_factor = field(phase(a - b + r))
        related = phase_factor * field(c + 1).sqrt() * field(wigner)
        if not field(clebsch).overlaps(related):
            raise ArithmeticError("normalisations disagree at %s" % ((a, b, c, p, q, r),))

    for a in range(TWICE_J_UP_TO + 1):
        for b in range(TWICE_J_UP_TO + 1):
            basis = [(p, q) for p in magnetic_values(a) for q in magnetic_values(b)]
            states = {}
            for c in range(abs(a - b), min(TWICE_J_UP_TO, a + b) + 1):
                if not triangle(a, b, c):
                    continue
                for r in magnetic_values(c):
                    vector = []
                    for p, q in basis:
                        if admissible_coupling(a, b, c, p, q, r):
                            vector.append(field(exact_value("clebsch-gordan", a, b, c, p, q, r)))
                        else:
                            vector.append(field(0))
                    states[(c, r)] = vector
            keys = sorted(states)
            for i, left in enumerate(keys):
                for right in keys[i:]:
                    dot = sum(x * y for x, y in zip(states[left], states[right]))
                    expected = field(1 if left == right else 0)
                    if not dot.overlaps(expected):
                        raise ArithmeticError(
                            "orthogonality failed for j1=%s j2=%s at %s, %s"
                            % (half_text(a), half_text(b), left, right)
                        )

    for l1 in range(TWICE_J_UP_TO + 1):
        for l2 in range(TWICE_J_UP_TO + 1):
            for l3 in range(TWICE_J_UP_TO + 1):
                if l1 % 2 or l2 % 2 or l3 % 2:
                    continue
                a, b, c = l1, l2, l3
                if not triangle(a, b, c):
                    continue
                wigner = field(exact_value("wigner-3j", a, b, c, 0, 0, 0))
                right = field(2) * wigner * wigner
                left = field(legendre_triple_integral(l1 // 2, l2 // 2, l3 // 2))
                if not left.overlaps(right):
                    raise ArithmeticError(
                        "Legendre triple product failed for %d,%d,%d"
                        % (l1 // 2, l2 // 2, l3 // 2)
                    )

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


class ClebschGordanWigner3j(numberdb.Generator):
    table = os.environ.get("NUMBERDB_TABLE", TID)
    parameters = ("j1", "j2", "j3", "m1", "m2", "m", "normalisation")
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self, twice_j_up_to=TWICE_J_UP_TO):
        for a, b, c, p, q, r in enumerate_indices(twice_j_up_to):
            params = {
                "j1": half_text(a),
                "j2": half_text(b),
                "j3": half_text(c),
                "m1": half_text(p),
                "m2": half_text(q),
                "m": half_text(r),
            }
            for normalisation in ("clebsch-gordan", "wigner-3j"):
                record = dict(params)
                record["normalisation"] = normalisation
                yield record

    def value(self, params, digits):
        self_check()
        a = parse_half(params["j1"])
        b = parse_half(params["j2"])
        c = parse_half(params["j3"])
        p = parse_half(params["m1"])
        q = parse_half(params["m2"])
        r = parse_half(params["m"])
        return exact_value(params["normalisation"], a, b, c, p, q, r, digits)


if __name__ == "__main__":
    _key_from_stdin()
    generator = ClebschGordanWigner3j()
    mode = os.environ.get("NUMBERDB_PUBLISH")
    if mode == "1" or "--publish" in sys.argv:
        print(
            fill_draft_once(
                generator,
                message="Clebsch-Gordan and Wigner 3j coefficients with j <= 2",
            )
        )
    elif mode == "preview" or "--preview" in sys.argv:
        print(generator.preview())
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
