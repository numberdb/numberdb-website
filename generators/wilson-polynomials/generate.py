"""Wilson polynomials W_n(x^2; a,b,c,d) -- numberdb.org/T271.

This generator fills the table of DLMF/KLS Wilson polynomials

    W_n(x^2; a,b,c,d)
      = (a+b)_n (a+c)_n (a+d)_n
        _4F_3(-n, n+a+b+c+d-1, a+ix, a-ix; a+b, a+c, a+d; 1).

The table stores the polynomial in y = x^2. Since the Wilson polynomial is
symmetric in a,b,c,d, entries use the nondecreasing representative of the
positive rational shape parameters.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import json
import os
import sys
import urllib.request
from itertools import permutations

import numberdb.sage as numberdb
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


TABLE = os.environ.get("NUMBERDB_TABLE", "T271")

# Measured before filling the draft: these five half-integer or integer shape
# values, up to symmetry, and 0 <= n <= 10 give 770 entries. The longest
# written value has 450 characters, and the entries block is 141.3 KB in the
# dry-run measurement.
PARAMETER_VALUES = (
    QQ(1) / QQ(2),
    QQ(1),
    QQ(3) / QQ(2),
    QQ(2),
    QQ(3),
)
UP_TO = 10

R = PolynomialRing(QQ, "y")
y = R.gen()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _rising_scalar(argument, count):
    """The scalar Pochhammer symbol (argument)_count over QQ."""
    value = QQ(1)
    argument = QQ(argument)
    for offset in range(count):
        value *= argument + QQ(offset)
    return value


def _rising_quadratic(argument, count):
    """The product (argument+ix)_count (argument-ix)_count in QQ[y]."""
    value = R.one()
    argument = QQ(argument)
    for offset in range(count):
        value *= (argument + QQ(offset)) ** 2 + y
    return R(value)


def wilson_polynomial(a, b, c, d, n):
    """The DLMF/KLS Wilson polynomial W_n(y; a,b,c,d), with y=x^2."""
    a, b, c, d = QQ(a), QQ(b), QQ(c), QQ(d)
    n = int(n)
    prefactor = (
        _rising_scalar(a + b, n)
        * _rising_scalar(a + c, n)
        * _rising_scalar(a + d, n)
    )
    total = R.zero()
    for k in range(n + 1):
        coefficient = (
            prefactor
            * _rising_scalar(-n, k)
            * _rising_scalar(QQ(n) + a + b + c + d - 1, k)
            / (
                _rising_scalar(a + b, k)
                * _rising_scalar(a + c, k)
                * _rising_scalar(a + d, k)
                * _rising_scalar(1, k)
            )
        )
        total += coefficient * _rising_quadratic(a, k)
    return R(total)


def _shape_tuples():
    values = PARAMETER_VALUES
    for i, a in enumerate(values):
        for j in range(i, len(values)):
            b = values[j]
            for k in range(j, len(values)):
                c = values[k]
                for ell in range(k, len(values)):
                    d = values[ell]
                    yield a, b, c, d


class WilsonPolynomials(numberdb.Generator):
    """Generator for T271, the Wilson polynomials W_n(x^2; a,b,c,d)."""

    table = TABLE
    parameters = ("a", "b", "c", "d", "n")
    type = "Q[]"
    rigour = "exact"

    def enumerate(self, up_to=UP_TO):
        for a, b, c, d in _shape_tuples():
            for n in range(up_to + 1):
                yield {
                    "a": str(a),
                    "b": str(b),
                    "c": str(c),
                    "d": str(d),
                    "n": str(n),
                }

    def value(self, params, digits):
        return wilson_polynomial(
            QQ(params["a"]),
            QQ(params["b"]),
            QQ(params["c"]),
            QQ(params["d"]),
            int(params["n"]),
        )


def _computed_values():
    return {
        (a, b, c, d, n): wilson_polynomial(a, b, c, d, n)
        for a, b, c, d in _shape_tuples()
        for n in range(UP_TO + 1)
    }


def _check_parameter_symmetry(values):
    for (a, b, c, d, n), polynomial in values.items():
        for permuted in set(permutations((a, b, c, d))):
            if wilson_polynomial(*permuted, n) != polynomial:
                raise ArithmeticError(
                    "symmetry failed at a=%s, b=%s, c=%s, d=%s, n=%d"
                    % (a, b, c, d, n)
                )


def _check_special_values(values):
    for (a, b, c, d, n), polynomial in values.items():
        parameters = (a, b, c, d)
        for index, parameter in enumerate(parameters):
            others = parameters[:index] + parameters[index + 1:]
            expected = QQ(1)
            for other in others:
                expected *= _rising_scalar(parameter + other, n)
            if polynomial(-(parameter ** 2)) != expected:
                raise ArithmeticError(
                    "special value failed at a=%s, b=%s, c=%s, d=%s, n=%d, parameter=%s"
                    % (a, b, c, d, n, parameter)
                )


def _check_leading_coefficient(values):
    for (a, b, c, d, n), polynomial in values.items():
        expected = QQ((-1) ** n) * _rising_scalar(QQ(n) + a + b + c + d - 1, n)
        if polynomial.monomial_coefficient(y ** n) != expected:
            raise ArithmeticError(
                "leading coefficient failed at a=%s, b=%s, c=%s, d=%s, n=%d"
                % (a, b, c, d, n)
            )


def _rising_in(parent, argument, count):
    value = parent.one()
    argument = parent(argument)
    for offset in range(count):
        value *= argument + parent(offset)
    return value


def _conjugate_rising_product(parent, start, variable, count):
    value = parent.one()
    start = parent(start)
    variable = parent(variable)
    for offset in range(count):
        value *= (start + parent(offset)) ** 2 + variable ** 2
    return value


def _limit_at_infinity(fraction, polynomial_ring):
    fraction = fraction.parent()(fraction)
    numerator = polynomial_ring(fraction.numerator())
    denominator = polynomial_ring(fraction.denominator())
    num_degree = numerator.degree()
    den_degree = denominator.degree()
    if num_degree < den_degree:
        return QQ(0)
    if num_degree == den_degree:
        return QQ(numerator.leading_coefficient()) / QQ(denominator.leading_coefficient())
    raise ArithmeticError("coefficient has no finite limit at infinity: %s" % (fraction,))


def _general_binomial(top, bottom):
    if bottom < 0:
        return QQ(0)
    value = QQ(1)
    top = QQ(top)
    for offset in range(bottom):
        value *= (top - QQ(offset)) / QQ(offset + 1)
    return value


def _jacobi_polynomial(alpha, beta, n):
    QX = PolynomialRing(QQ, "X")
    X = QX.gen()
    total = QX.zero()
    for m in range(n + 1):
        total += (
            _general_binomial(QQ(n) + alpha, n - m)
            * _general_binomial(QQ(n) + beta, m)
            * ((X - 1) / QQ(2)) ** m
            * ((X + 1) / QQ(2)) ** (n - m)
        )
    return QX(total)


def _wilson_jacobi_limit(alpha, beta, n):
    S = PolynomialRing(QQ, "T")
    T = S.gen()
    K = S.fraction_field()
    XRing = PolynomialRing(K, "X")
    X = XRing.gen()
    T_in_K = K(T)
    A = (K(alpha) + K(1)) / K(2)
    B = (K(beta) + K(1)) / K(2)
    y_substitution = (K(1) - X) * T_in_K ** 2 / K(2)

    prefactor = (
        _rising_in(K, 2 * A, n)
        * _conjugate_rising_product(K, A + B, T_in_K, n)
    )
    total = XRing.zero()
    for k in range(n + 1):
        quadratic = XRing.one()
        for offset in range(k):
            quadratic *= (A + K(offset)) ** 2 + y_substitution
        coefficient = (
            prefactor
            * _rising_in(K, -n, k)
            * _rising_in(K, K(n) + 2 * A + 2 * B - K(1), k)
            / (
                _rising_in(K, 2 * A, k)
                * _conjugate_rising_product(K, A + B, T_in_K, k)
                * _rising_in(K, 1, k)
            )
        )
        total += coefficient * quadratic

    normalized = XRing(total / (T_in_K ** (2 * n) * _rising_in(K, 1, n)))
    QX = PolynomialRing(QQ, "X")
    out = QX.zero()
    XX = QX.gen()
    for degree in range(n + 1):
        out += _limit_at_infinity(
            normalized.monomial_coefficient(X ** degree),
            S,
        ) * XX ** degree
    return QX(out)


def _check_jacobi_limit():
    for alpha, beta in ((QQ(0), QQ(0)), (QQ(1), QQ(2)), (QQ(1) / QQ(2), QQ(1) / QQ(2))):
        for n in range(UP_TO + 1):
            got = _wilson_jacobi_limit(alpha, beta, n)
            expected = _jacobi_polynomial(alpha, beta, n)
            if got != expected:
                raise ArithmeticError(
                    "Wilson-Jacobi limit failed at alpha=%s, beta=%s, n=%d"
                    % (alpha, beta, n)
                )


def run_integrity_checks(values=None):
    if values is None:
        values = _computed_values()
    _check_parameter_symmetry(values)
    _check_special_values(values)
    _check_leading_coefficient(values)
    _check_jacobi_limit()


def stored_values():
    """Read the draft from the API and parse its stored polynomials."""
    key = os.environ.get("NUMBERDB_API_KEY")
    if not key:
        raise RuntimeError("NUMBERDB_API_KEY is not set")
    request = urllib.request.Request(
        "https://numberdb.org/api/table?id=%s" % TABLE,
        headers={"Authorization": "Bearer " + key},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        tree = json.load(response)
    if "error" in tree:
        raise RuntimeError(tree["error"])

    found = {}
    for a_text, by_b in tree.get("Numbers", {}).items():
        for b_text, by_c in by_b.items():
            for c_text, by_d in by_c.items():
                for d_text, by_n in by_d.items():
                    for n_text, polynomial_text in by_n.items():
                        found[
                            (QQ(a_text), QQ(b_text), QQ(c_text), QQ(d_text), int(n_text))
                        ] = R(polynomial_text)

    expected_keys = set(_computed_values())
    if set(found) != expected_keys:
        missing = sorted(expected_keys - set(found))[:5]
        extra = sorted(set(found) - expected_keys)[:5]
        raise ArithmeticError(
            "stored key set disagrees, missing=%s extra=%s" % (missing, extra)
        )
    return found


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
    generator = WilsonPolynomials()
    run_integrity_checks()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="exact Wilson polynomials in the DLMF normalisation"))
    elif os.environ.get("NUMBERDB_API_KEY"):
        report = generator.verify(sample=None)
        print(report)
        if not report.ok:
            sys.exit(1)
        run_integrity_checks(stored_values())
        print("stored identity checks passed")
    else:
        print("identity checks passed; NUMBERDB_API_KEY is not set, so verify() was skipped")
