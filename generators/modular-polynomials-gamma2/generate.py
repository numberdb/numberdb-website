"""Modular polynomials for gamma_2 = j^(1/3) -- numberdb.org/T311.

Let gamma_2(tau) be the branch with gamma_2(tau)^3 = j(tau) and
q-expansion q^(-1/3)(1 + O(q)). This generator fills T311 with the primitive
polynomial Phi^{gamma_2}_ell(x,y) over ZZ satisfying

    Phi^{gamma_2}_ell(gamma_2(ell tau), gamma_2(tau)) = 0,

normalised so that the coefficient of x^(ell+1) is 1, for every prime
ell != 3 with ell <= 23.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The rows are computed from the definition by exact q-expansions. With
t = q^(1/3), gamma_2(tau) = t^-1 G(t^3) and
gamma_2(ell tau) = t^-ell G(t^(3 ell)), where G(q)^3 = q j(q). The generator
finds the rational kernel relation among monomials x^a y^b with
0 <= a,b <= ell+1 and ell a + b congruent to ell+1 modulo 3. PARI's
polmodular(ell, 5) is used only as an independent convention check.
"""

import os
import sys
from math import comb

import numberdb.sage as numberdb
from sage.libs.pari import pari
from sage.matrix.constructor import matrix
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


TABLE = os.environ.get("NUMBERDB_TABLE", "T311")
PRIMES = (2, 5, 7, 11, 13, 17, 19, 23)
DIGITS = 100
EXTRA_ROWS = 32

QXY = PolynomialRing(ZZ, ("x", "y"))
poly_x, poly_y = QXY.gens()

_CACHE = {}
_GAMMA2_CACHE = {}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def _truncate(polynomial, degree):
    if polynomial.degree() <= degree:
        return polynomial
    return polynomial.parent()(polynomial.list()[:degree + 1])


def _factor_series(ring, step, exponent, degree):
    """The truncation of (1 - q^step)^exponent through q^degree."""
    coeffs = [ZZ(0)] * (degree + 1)
    if exponent >= 0:
        for r in range(0, min(exponent, degree // step) + 1):
            coeffs[r * step] = ZZ((-1) ** r) * ZZ(comb(exponent, r))
    else:
        k = -exponent
        for r in range(0, degree // step + 1):
            coeffs[r * step] = ZZ(comb(k + r - 1, r))
    return ring(coeffs)


def _product_factors(ring, degree, exponent):
    product = ring(1)
    for n in range(1, degree + 1):
        product = _truncate(product * _factor_series(ring, n, exponent, degree), degree)
    return product


def _sigma3(n):
    total = ZZ(0)
    for divisor in range(1, n + 1):
        if n % divisor == 0:
            total += ZZ(divisor) ** 3
    return total


def _j_shifted_series(ring, degree):
    """J(q), where j(q) = q^-1 J(q)."""
    inv_delta_tail = _product_factors(ring, degree, -24)
    e4 = ring([ZZ(1)] + [ZZ(240) * _sigma3(n) for n in range(1, degree + 1)])
    return _truncate(e4 ** 3 * inv_delta_tail, degree)


def _gamma2_coefficients(degree):
    """Coefficients of G(q), where G(q)^3 = q j(q) and G(0) = 1."""
    if degree in _GAMMA2_CACHE:
        return _GAMMA2_CACHE[degree]

    smaller = [bound for bound in _GAMMA2_CACHE if bound >= degree]
    if smaller:
        return _GAMMA2_CACHE[min(smaller)][:degree + 1]

    q_ring = PolynomialRing(ZZ, "q")
    shifted_j = _j_shifted_series(q_ring, degree)
    j_coeffs = [ZZ(shifted_j[n]) for n in range(degree + 1)]
    coeffs = [ZZ(0)] * (degree + 1)
    coeffs[0] = ZZ(1)

    for n in range(1, degree + 1):
        known = ZZ(0)
        for i in range(n + 1):
            for j in range(n + 1 - i):
                k = n - i - j
                if i == n or j == n or k == n:
                    continue
                known += coeffs[i] * coeffs[j] * coeffs[k]
        numerator = j_coeffs[n] - known
        if numerator % 3:
            raise ArithmeticError("gamma_2 coefficient %d is not integral" % n)
        coeffs[n] = numerator // 3

    _GAMMA2_CACHE[degree] = coeffs
    return coeffs


def _gamma2_t_series(t_ring, q_step, degree):
    coeffs = [ZZ(0)] * (degree + 1)
    gamma_coeffs = _gamma2_coefficients(degree // (3 * q_step))
    for n, coefficient in enumerate(gamma_coeffs):
        exponent = 3 * q_step * n
        if exponent <= degree:
            coeffs[exponent] = coefficient
    return t_ring(coeffs)


def _monomials(ell):
    target = (ell + 1) % 3
    return [
        (a, b)
        for b in range(ell + 2)
        for a in range(ell + 2)
        if (ell * a + b - target) % 3 == 0
    ]


def _row_exponents(ell, monomials):
    target = (ell + 1) % 3
    max_shift = max(ell * a + b for a, b in monomials)
    exponent = -max_shift
    while exponent % 3 != (-target) % 3:
        exponent += 1
    return [exponent + 3 * i for i in range(len(monomials) + EXTRA_ROWS)]


def _normalised_kernel_vector(mat, monomials, lead_monomial):
    kernel = mat.right_kernel().basis()
    if len(kernel) != 1:
        raise ArithmeticError(
            "kernel dimension %d, rows=%d, cols=%d"
            % (len(kernel), mat.nrows(), mat.ncols())
        )

    vector = kernel[0]
    denominator = ZZ(1)
    for coefficient in vector:
        denominator = denominator.lcm(ZZ(coefficient.denominator()))
    coeffs = [ZZ(coefficient * denominator) for coefficient in vector]

    content = ZZ(0)
    for coefficient in coeffs:
        content = content.gcd(coefficient)
    coeffs = [coefficient // content for coefficient in coeffs]

    lead = coeffs[monomials.index(lead_monomial)]
    if lead < 0:
        coeffs = [-coefficient for coefficient in coeffs]
        lead = -lead
    if lead != 1:
        raise ArithmeticError("leading coefficient is %s, not 1" % (lead,))
    return coeffs


def _from_q_expansions(ell):
    monomials = _monomials(ell)
    rows_at = _row_exponents(ell, monomials)
    max_shift = max(ell * a + b for a, b in monomials)
    series_degree = max_shift + rows_at[-1]

    t_ring = PolynomialRing(ZZ, "t")
    gamma_tau = _gamma2_t_series(t_ring, 1, series_degree)
    gamma_ell_tau = _gamma2_t_series(t_ring, ell, series_degree)

    powers_tau = [t_ring(1)]
    powers_ell_tau = [t_ring(1)]
    for _ in range(ell + 1):
        powers_tau.append(_truncate(powers_tau[-1] * gamma_tau, series_degree))
        powers_ell_tau.append(_truncate(powers_ell_tau[-1] * gamma_ell_tau, series_degree))

    series_by_monomial = {
        (a, b): _truncate(powers_ell_tau[a] * powers_tau[b], series_degree)
        for a, b in monomials
    }

    rows = []
    for exponent in rows_at:
        row = []
        for a, b in monomials:
            shifted = exponent + ell * a + b
            row.append(
                ZZ(0)
                if shifted < 0 or shifted > series_degree
                else ZZ(series_by_monomial[(a, b)][shifted])
            )
        rows.append(row)

    coeffs = _normalised_kernel_vector(
        matrix(QQ, rows), monomials, (ell + 1, 0)
    )

    polynomial = QXY(0)
    for coefficient, (a, b) in zip(coeffs, monomials):
        if coefficient:
            polynomial += coefficient * poly_x ** a * poly_y ** b
    return polynomial


def _pari_polynomial(ell):
    return QXY(pari.polmodular(ell, 5))


def gamma2_modular_polynomial(ell):
    """Return Phi^{gamma_2}_ell(x,y)."""
    ell = ZZ(ell)
    if ell % 3 == 0:
        raise ValueError("ell=%s is excluded" % (ell,))
    if ell in _CACHE:
        return _CACHE[ell]

    polynomial = _from_q_expansions(int(ell))
    if polynomial.degree(poly_x) != ell + 1:
        raise ArithmeticError("ell=%s: degree in x is %s" % (
            ell, polynomial.degree(poly_x)))

    pari_polynomial = _pari_polynomial(ell)
    if polynomial != pari_polynomial:
        raise ArithmeticError(
            "ell=%s: q-expansions give %s but PARI polmodular gives %s"
            % (ell, polynomial, pari_polynomial)
        )

    _CACHE[ell] = polynomial
    return polynomial


def entry_comment(ell, polynomial):
    degree_y = polynomial.degree(poly_y)
    if degree_y == ell + 1:
        return None
    return r"$\deg_y\Phi^{\gamma_2}_{%s}=%s$." % (ell, degree_y)


class Gamma2ModularPolynomials(numberdb.Generator):
    """Generator for T311, modular polynomials for gamma_2."""

    table = TABLE
    parameters = ("ell",)
    type = "Z[]"
    rigour = "exact"
    digits = DIGITS

    def enumerate(self):
        for ell in PRIMES:
            yield {"ell": str(ell)}

    def value(self, params, digits):
        ell = ZZ(params["ell"])
        polynomial = gamma2_modular_polynomial(ell)
        comment = entry_comment(ell, polynomial)
        if comment is None:
            return polynomial
        return {"number": polynomial, "comment": comment}


def run_integrity_checks():
    values = {}
    for ell in PRIMES:
        polynomial = gamma2_modular_polynomial(ell)
        values[ell] = polynomial
        if polynomial.degree(poly_x) != ell + 1:
            raise ArithmeticError("ell=%s has wrong degree in x" % (ell,))
        if polynomial != _pari_polynomial(ell):
            raise ArithmeticError("ell=%s does not match PARI polmodular" % (ell,))

    longest = max((len(str(polynomial)), ell) for ell, polynomial in values.items())
    y_degrees = ", ".join(
        "%s:%s" % (ell, values[ell].degree(poly_y))
        for ell in PRIMES
        if values[ell].degree(poly_y) != ell + 1
    )
    print("integrity checks passed for %d gamma_2 modular polynomials" % len(values))
    print("matched PARI polmodular(ell, 5) for ell=%s" % (
        ",".join(str(ell) for ell in PRIMES)))
    print("all rows have degree ell+1 in y" if not y_degrees
          else "exceptional y-degrees: %s" % y_degrees)
    print("longest polynomial has %d characters at ell=%s" % longest)


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
    generator = Gamma2ModularPolynomials()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="fill gamma2 modular polynomial draft from exact q-expansions",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
