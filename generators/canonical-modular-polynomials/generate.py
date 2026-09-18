"""Canonical modular polynomials Phi^c_ell -- numberdb.org/T309.

For a prime ell, let

    s = 12 / gcd(12, ell - 1),
    v = s(ell - 1) / 12,
    m_ell(tau) = ell^s (eta(ell tau) / eta(tau))^(2s).

This generator fills T309 with the primitive polynomial Phi^c_ell(x, y) over
ZZ satisfying Phi^c_ell(m_ell(tau), j(tau)) = 0, with coefficient 1 on
x^(ell+1), for every prime ell <= 43.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The rows are computed from the definition by exact q-expansions. The search
space is the monomials x^a y^b with 0 <= a <= ell+1 and 0 <= b <= v. A
rational kernel relation is accepted only after its q-expansion vanishes past
the total pole order v(2 ell + 2) on X_0(ell). PARI's ellmodulareqn is used
only as an independent check on the levels where its data is canonical type 0.
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


TABLE = os.environ.get("NUMBERDB_TABLE", "T309")
PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43)
PARI_CANONICAL_PRIMES = (2, 3, 5, 7, 13, 37)
T96_CHECK_PRIMES = (2, 3, 5, 7, 11)
DIGITS = 100

QXY = PolynomialRing(ZZ, ("x", "y"))
poly_x, poly_y = QXY.gens()

_CACHE = {}


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


def _product_factors(ring, degree, exponent, skip_multiple=None):
    product = ring(1)
    for n in range(1, degree + 1):
        if skip_multiple is not None and n % skip_multiple == 0:
            continue
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


def _m_shifted_series(ell, ring, degree):
    """M(q), where m_ell(q) = q^v M(q)."""
    s = ZZ(12) // ZZ(12).gcd(ZZ(ell) - 1)
    product = _product_factors(ring, degree, -2 * int(s), skip_multiple=ell)
    return _truncate(ZZ(ell) ** s * product, degree)


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


def _parameters(ell):
    ell = ZZ(ell)
    s = ZZ(12) // ZZ(12).gcd(ell - 1)
    v = s * (ell - 1) // 12
    return s, v


def canonical_modular_polynomial(ell):
    """Return Phi^c_ell(x,y)."""
    ell = ZZ(ell)
    if ell in _CACHE:
        return _CACHE[ell]

    _, v = _parameters(ell)
    pole_bound = ZZ(v) * (2 * ell + 2)
    degree = int(pole_bound + v)

    q_ring = PolynomialRing(ZZ, "q")
    m0 = _m_shifted_series(int(ell), q_ring, degree)
    j0 = _j_shifted_series(q_ring, degree)

    monomials = [
        (a, b)
        for b in range(int(v) + 1)
        for a in range(int(ell) + 2)
    ]

    series_by_monomial = {}
    shifts = {}
    j_power = q_ring(1)
    for b in range(int(v) + 1):
        current = j_power
        for a in range(int(ell) + 2):
            if a:
                current = _truncate(current * m0, degree)
            series_by_monomial[(a, b)] = current
            shifts[(a, b)] = a * int(v) - b
        j_power = _truncate(j_power * j0, degree)

    rows = []
    for exponent in range(-int(v), int(pole_bound) + 1):
        row = []
        for monomial in monomials:
            k = exponent - shifts[monomial]
            row.append(
                ZZ(0)
                if k < 0 or k > degree
                else ZZ(series_by_monomial[monomial][k])
            )
        rows.append(row)

    coeffs = _normalised_kernel_vector(
        matrix(QQ, rows), monomials, (int(ell) + 1, 0)
    )

    polynomial = QXY(0)
    for coefficient, (a, b) in zip(coeffs, monomials):
        if coefficient:
            polynomial += coefficient * poly_x ** a * poly_y ** b

    if polynomial.degree(poly_x) != ell + 1 or polynomial.degree(poly_y) != v:
        raise ArithmeticError("ell=%s: unexpected bidegree %s, %s" % (
            ell, polynomial.degree(poly_x), polynomial.degree(poly_y)))

    _CACHE[ell] = polynomial
    return polynomial


def _expected_genus_zero(ell):
    if ell == 2:
        return (poly_x + 16) ** 3 - poly_x * poly_y
    if ell == 3:
        return (poly_x + 27) * (poly_x + 3) ** 3 - poly_x * poly_y
    if ell == 5:
        return (poly_x ** 2 + 10 * poly_x + 5) ** 3 - poly_x * poly_y
    if ell == 7:
        return (
            (poly_x ** 2 + 13 * poly_x + 49)
            * (poly_x ** 2 + 5 * poly_x + 1) ** 3
            - poly_x * poly_y
        )
    if ell == 13:
        return (
            (poly_x ** 2 + 5 * poly_x + 13)
            * (poly_x ** 4 + 7 * poly_x ** 3 + 20 * poly_x ** 2 + 19 * poly_x + 1) ** 3
            - poly_x * poly_y
        )
    raise ValueError(ell)


def _primitive_part(polynomial):
    content = polynomial.content()
    if content < 0:
        content = -content
    out = polynomial // content
    return -out if out.leading_coefficient() < 0 else out


def _classical_from_canonical(ell):
    """Eliminate m_ell to get a polynomial in j(tau) and j(ell*tau)."""
    polynomial = canonical_modular_polynomial(ell)
    s, _ = _parameters(ell)

    ring = PolynomialRing(ZZ, ("x", "y", "z"))
    x, y, z = ring.gens()
    first = ring(polynomial)

    fricke = ring(0)
    for (a, b), coefficient in polynomial.dict().items():
        fricke += (
            ZZ(coefficient)
            * (ZZ(ell) ** (s * a))
            * x ** (ell + 1 - a)
            * z ** b
        )
    return _primitive_part(first.resultant(fricke, x))


def _stored_t96_polynomial(ell):
    row = numberdb.table("T96")["Numbers"][str(ell)]
    ring2 = PolynomialRing(ZZ, ("x", "y"))
    x2, y2 = ring2.gens()
    stored = ring2(row)

    ring3 = PolynomialRing(ZZ, ("x", "y", "z"))
    _, y3, z3 = ring3.gens()
    out = ring3(0)
    for (a, b), coefficient in stored.dict().items():
        out += ZZ(coefficient) * z3 ** a * y3 ** b
    return _primitive_part(out)


def _pari_canonical_polynomial(ell):
    equation = pari.ellmodulareqn(ell)
    kind = ZZ(equation[1])
    if kind != 0:
        raise ArithmeticError("PARI ellmodulareqn(%s) has type %s, not 0" % (ell, kind))
    return QXY(equation[0])


def entry_comment(ell):
    _, v = _parameters(ell)
    return r"$\deg_y\Phi^c_{%s}=%s$." % (ell, v)


class CanonicalModularPolynomials(numberdb.Generator):
    """Generator for T309, canonical modular polynomials Phi^c_ell."""

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
        return {
            "number": canonical_modular_polynomial(ell),
            "comment": entry_comment(ell),
        }


def run_integrity_checks():
    values = {}
    for ell in PRIMES:
        polynomial = canonical_modular_polynomial(ell)
        values[ell] = polynomial
        _, v = _parameters(ell)
        if polynomial.degree(poly_x) != ell + 1 or polynomial.degree(poly_y) != v:
            raise ArithmeticError("ell=%s has wrong bidegree" % (ell,))

    for ell in (2, 3, 5, 7, 13):
        if values[ell] != _expected_genus_zero(ell):
            raise ArithmeticError("ell=%s does not match the genus-zero formula" % (ell,))

    for ell in PARI_CANONICAL_PRIMES:
        pari_polynomial = _pari_canonical_polynomial(ell)
        if values[ell] != pari_polynomial:
            raise ArithmeticError("ell=%s does not match PARI's canonical data" % (ell,))

    for ell in T96_CHECK_PRIMES:
        resultant = _classical_from_canonical(ell)
        stored = _stored_t96_polynomial(ell)
        if resultant != stored and resultant % stored != 0:
            raise ArithmeticError("ell=%s does not eliminate to T96" % (ell,))

    longest = max((len(str(polynomial)), ell) for ell, polynomial in values.items())
    print("integrity checks passed for %d canonical modular polynomials" % len(values))
    print("matched genus-zero formulas for ell=2,3,5,7,13")
    print("matched PARI canonical type-0 data for ell=%s" % (
        ",".join(str(ell) for ell in PARI_CANONICAL_PRIMES)))
    print("eliminated to the T96 classical modular polynomial for ell=%s" % (
        ",".join(str(ell) for ell in T96_CHECK_PRIMES)))
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
    generator = CanonicalModularPolynomials()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="fill canonical modular polynomial draft from exact q-expansions",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
