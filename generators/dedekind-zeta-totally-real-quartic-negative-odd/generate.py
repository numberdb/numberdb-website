"""Values of Dedekind zeta functions of totally real quartic fields at negative odd integers -- numberdb.org/T366.

For every totally real quartic field K with discriminant D <= 30000, indexed
among fields of the same discriminant by PARI's polredabs reduced defining
polynomial, this stores zeta_K(s) for s = -1, -3, -5.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The stored values are exact rationals. PARI computes zeta_K(s) through
lfun(lfuncreate(f), s), and bestappr is given the denominator bounds obtained
from Serre's estimates for totally real fields of degree 4. Each value is
recomputed at three working precisions, checked against the functional
equation at s = 2, 4, 6, and checked against exact Dirichlet-character
factorisations when the quartic field is abelian.
"""

import math
import os
import sys
import time
import warnings

import numberdb.sage as numberdb

warnings.filterwarnings("ignore", message="Resolving lazy import .* during startup")

from numberdb._generate import _producer
from numberdb._write import Entries, attach, submit_entries
from sage.arith.misc import bernoulli, binomial, kronecker_symbol, valuation
from sage.libs.pari import pari
from sage.modular.dirichlet import DirichletGroup
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ
from sage.rings.real_mpfr import RealField


TABLE = os.environ.get("NUMBERDB_TABLE", "T366")
BOUND = 30000
EXPECTED_FIELDS = 204
ARGUMENTS = (-1, -3, -5)
WORKING_DIGITS = (120, 160, 200)
FUNCTIONAL_DIGITS = 100
FUNCTIONAL_RELATIVE_TOLERANCE = "1e-60"
GROUPS = ("C4", "V4", "D4", "A4", "S4")
PROGRESS = os.environ.get("NUMBERDB_PROGRESS") == "1"
TRANSITIVE_GROUPS = {
    1: r"C_4",
    2: r"C_2 \times C_2",
    3: r"D_4",
    4: r"A_4",
    5: r"S_4",
}

R = PolynomialRing(QQ, "x")
x = R.gen()

_FIELDS = {}
_FIELD_INFO = {}
_ZETA_VALUES = {}
_DIRICHLET_CACHE = {}
_QUADRATIC_SUBFIELDS = {}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def as_QQ(value):
    return QQ(str(value))


def as_ZZ(value):
    return ZZ(str(value))


def _reduced_coefficients(poly):
    reduced = pari(poly).polredabs()
    coefficients = tuple(QQ(c) for c in reduced.Vecrev())
    if len(coefficients) != 5 or coefficients[4] != 1:
        raise ArithmeticError("polredabs of %s is not monic quartic: %s"
                              % (poly, coefficients))
    if any(c.denominator() != 1 for c in coefficients):
        raise ArithmeticError("polredabs of %s is not integral: %s"
                              % (poly, coefficients))
    return tuple(ZZ(c) for c in coefficients[:4])


def quartic_fields(bound=BOUND):
    """The polredabs representatives of totally real quartic fields."""
    if bound in _FIELDS:
        return _FIELDS[bound]

    found = {}
    for group in GROUPS:
        for poly in pari('nflist("%s", [1,%d])' % (group, bound)):
            if int(pari(poly).polsturm()) != 4:
                continue
            D = as_ZZ(pari(poly).nfdisc())
            if not 0 < D <= bound:
                continue
            found.setdefault(D, set()).add(_reduced_coefficients(poly))

    table = {
        D: [
            R([a0, a1, a2, a3, 1])
            for (a0, a1, a2, a3) in sorted(
                polys, key=lambda c: (c[3], c[2], c[1], c[0])
            )
        ]
        for D, polys in found.items()
    }
    count = sum(len(fields) for fields in table.values())
    if bound == BOUND and count != EXPECTED_FIELDS:
        raise ArithmeticError("found %d totally real quartic fields; expected %d"
                              % (count, EXPECTED_FIELDS))

    _FIELDS[bound] = table
    return table


def field_info(poly):
    """Return D, class number, roots of unity, and transitive-group number."""
    key = str(poly)
    if key not in _FIELD_INFO:
        g = pari(poly)
        bnf = g.bnfinit(1)
        if bnf.bnfcertify() != 1:
            raise ArithmeticError("bnfcertify did not certify %s" % poly)
        tu = bnf.bnf_get_tu()
        _FIELD_INFO[key] = (
            as_ZZ(g.nfdisc()),
            as_ZZ(bnf.bnf_get_no()),
            as_ZZ(tu[0]),
            int(g.polgalois()[2]),
        )
    return _FIELD_INFO[key]


def denominator_bound(n):
    """Serre's denominator bound for degree 4 and s = 1 - 2n."""
    rq = ZZ(8 * n)
    bound = ZZ(2) ** max(0, valuation(rq, 2) - 2)
    for p in range(3, int(rq) + 2):
        if ZZ(p).is_prime() and rq % (p - 1) == 0:
            bound *= ZZ(p) ** (1 + valuation(rq, p))
    return bound


DENOMINATOR_BOUNDS = {
    -1: denominator_bound(1),
    -3: denominator_bound(2),
    -5: denominator_bound(3),
}

if DENOMINATOR_BOUNDS != {-1: ZZ(30), -3: ZZ(1020), -5: ZZ(8190)}:
    raise ArithmeticError("unexpected Serre denominator bounds: %s"
                          % DENOMINATOR_BOUNDS)


def _set_pari_precision(decimal_digits):
    bits = numberdb.bits(decimal_digits, losing=64)
    pari.default("realprecision", decimal_digits + 20)
    pari.default("realbitprecision", bits)


def zeta_lfun(poly, s, working_digits):
    """Recognise zeta_K(s) with Serre's denominator bound."""
    _set_pari_precision(working_digits)
    bound = DENOMINATOR_BOUNDS[int(s)]
    value = pari("bestappr(lfun(lfuncreate(%s), %d), %s)"
                 % (poly, s, bound))
    return as_QQ(value)


def zeta_lfun_positive(poly, n):
    _set_pari_precision(FUNCTIONAL_DIGITS)
    return pari("lfun(lfuncreate(%s), %d)" % (poly, 2 * n))


def functional_equation(value, D, n):
    """zeta_K(2n) predicted from zeta_K(1 - 2n)."""
    RR = RealField(numberdb.bits(FUNCTIONAL_DIGITS, losing=64))
    D = ZZ(D)
    factorial = math.factorial(2 * n)
    factor = RR(ZZ(2) ** (8 * n)) * RR(n ** 4) * RR.pi() ** (8 * n)
    factor *= RR(D).sqrt()
    factor /= RR(factorial) ** 4 * RR(D) ** (2 * n)
    return RR(value) * factor


def check_functional_equation(poly, D, n, value):
    got = RealField(numberdb.bits(FUNCTIONAL_DIGITS, losing=64))(
        str(zeta_lfun_positive(poly, n))
    )
    want = functional_equation(value, D, n)
    RR = got.parent()
    error = abs(got - want) / max(RR(1), abs(got))
    if error > RR(FUNCTIONAL_RELATIVE_TOLERANCE):
        raise ArithmeticError(
            "functional equation fails for %s, D = %s, s = %s: %s versus %s"
            % (poly, D, 1 - 2 * n, got, want)
        )


def bernoulli_polynomial_at(k, value):
    value = QQ(value)
    return sum(binomial(k, j) * bernoulli(j) * value ** (k - j)
               for j in range(k + 1))


def zeta_rational(n):
    return -bernoulli(2 * n) / QQ(2 * n)


def quadratic_generalized_bernoulli(k, D):
    D = ZZ(D)
    q = abs(D)
    total = QQ(0)
    for a in range(1, q + 1):
        chi = kronecker_symbol(D, a)
        if chi:
            total += chi * bernoulli_polynomial_at(k, QQ(a) / QQ(q))
    return QQ(q) ** (k - 1) * total


def quadratic_l_value(D, n):
    return -quadratic_generalized_bernoulli(2 * n, D) / QQ(2 * n)


def dirichlet_l_value(chi, n):
    chi = chi.primitive_character()
    q = int(chi.modulus())
    k = 2 * n
    total = chi.parent().base_ring()(0)
    for a in range(1, q + 1):
        if ZZ(a).gcd(q) == 1:
            total += chi(a) * bernoulli_polynomial_at(k, QQ(a) / QQ(q))
    return -(QQ(q) ** (k - 1)) * total / QQ(k)


def cyclic_character_values(D, n):
    """Exact zeta_K(1 - 2n) from the characters of an abelian C4 field."""
    key = (int(D), int(n))
    if key in _DIRICHLET_CACHE:
        return _DIRICHLET_CACHE[key]

    values = set()
    root = math.isqrt(int(D))
    for q in range(1, root + 1):
        if D % (q * q) != 0:
            continue
        for chi in DirichletGroup(q):
            if not chi.is_primitive() or not chi.is_even() or chi.multiplicative_order() != 4:
                continue
            quadratic_conductor = int((chi ** 2).conductor())
            if q * q * quadratic_conductor != int(D):
                continue
            value = (
                zeta_rational(n)
                * dirichlet_l_value(chi, n)
                * dirichlet_l_value(chi ** 2, n)
                * dirichlet_l_value(chi ** 3, n)
            )
            values.add(QQ(value))

    _DIRICHLET_CACHE[key] = values
    return values


def quadratic_subfield_discriminants(poly):
    key = str(poly)
    if key in _QUADRATIC_SUBFIELDS:
        return _QUADRATIC_SUBFIELDS[key]
    rows = pari("nfsubfields(%s, 2)" % poly)
    discriminants = []
    for row in rows:
        discriminants.append(as_ZZ(pari(row[0]).nfdisc()))
    discriminants.sort()
    if len(discriminants) != 3:
        raise ArithmeticError("%s has %d quadratic subfields, not 3"
                              % (poly, len(discriminants)))
    _QUADRATIC_SUBFIELDS[key] = tuple(discriminants)
    return _QUADRATIC_SUBFIELDS[key]


def biquadratic_exact_value(poly, n):
    value = zeta_rational(n)
    for D in quadratic_subfield_discriminants(poly):
        value *= quadratic_l_value(D, n)
    return QQ(value)


def check_abelian_factorisation(poly, D, transitive_group, n, value):
    if transitive_group == 1:
        exact_values = cyclic_character_values(D, n)
        if value not in exact_values:
            raise ArithmeticError(
                "no exact C4 character factorisation gives %s for %s at s = %s; "
                "candidates were %s" % (value, poly, 1 - 2 * n, sorted(exact_values))
            )
    elif transitive_group == 2:
        exact = biquadratic_exact_value(poly, n)
        if exact != value:
            raise ArithmeticError(
                "exact V4 character factorisation gives %s, not %s, for %s at s = %s"
                % (exact, value, poly, 1 - 2 * n)
            )


def zeta_values(poly):
    key = str(poly)
    if key not in _ZETA_VALUES:
        D, h, w, transitive_group = field_info(poly)
        values = {}
        for s in ARGUMENTS:
            n = (1 - s) // 2
            recognised = {
                working: zeta_lfun(poly, s, working)
                for working in WORKING_DIGITS
            }
            if len(set(recognised.values())) != 1:
                raise ArithmeticError(
                    "PARI values for %s at s = %s depend on working precision: %s"
                    % (poly, s, recognised)
                )
            value = recognised[max(WORKING_DIGITS)]
            if value <= 0:
                raise ArithmeticError("unexpected nonpositive value for %s at s = %s: %s"
                                      % (poly, s, value))
            if DENOMINATOR_BOUNDS[s] % value.denominator() != 0:
                raise ArithmeticError(
                    "%s at s = %s has denominator %s outside Serre bound %s"
                    % (poly, s, value.denominator(), DENOMINATOR_BOUNDS[s])
                )
            check_functional_equation(poly, D, n, value)
            check_abelian_factorisation(poly, D, transitive_group, n, value)
            values[s] = value
        _ZETA_VALUES[key] = values
    return _ZETA_VALUES[key]


def poly_latex(poly, var="x"):
    coefficients = [ZZ(c) for c in poly.list()]
    terms = []
    for i in range(len(coefficients) - 1, -1, -1):
        coefficient = coefficients[i]
        if coefficient == 0:
            continue
        power = "" if i == 0 else (var if i == 1 else "%s^%d" % (var, i))
        magnitude = abs(coefficient)
        body = ("" if magnitude == 1 and i > 0 else str(magnitude)) + power
        terms.append(("-" if coefficient < 0 else ("+" if terms else "")) + body)
    return "".join(terms) or "0"


def field_label(D, k):
    return "4.4.%s.%s" % (D, k)


def comment(poly, D, k, h, w, transitive_group):
    group = TRANSITIVE_GROUPS.get(transitive_group, "4T%d" % transitive_group)
    return (
        "$%s=0$; signature $(4,0)$; Galois group $%s$ (4T%d); "
        "$h_K=%d$; $w_K=%d$; LMFDB %s."
        % (poly_latex(poly), group, transitive_group, h, w, field_label(D, k))
    )


class TotallyRealQuarticZetaNegativeOdd(numberdb.Generator):
    """Generator for T366."""

    table = TABLE
    parameters = ("D", "k", "s")
    type = "Q"
    rigour = "exact"
    files = ("generate.py",)

    def enumerate(self, bound=BOUND):
        fields = quartic_fields(bound)
        for D in sorted(fields):
            for k in range(1, len(fields[D]) + 1):
                for s in ARGUMENTS:
                    yield {"D": int(D), "k": k, "s": s}

    def value(self, params, digits):
        D = ZZ(params["D"])
        k = int(params["k"])
        s = int(params["s"])
        if s not in ARGUMENTS:
            raise ValueError("s must be one of %s, not %s" % (ARGUMENTS, s))
        fields = quartic_fields()
        if D not in fields or not 1 <= k <= len(fields[D]):
            raise ValueError("no totally real quartic field with D = %s, k = %s "
                             "and D <= %d" % (D, k, BOUND))
        poly = fields[D][k - 1]
        if PROGRESS and s == ARGUMENTS[0]:
            print("checking D = %s, k = %s, polynomial %s" % (D, k, poly),
                  file=sys.stderr, flush=True)
        field_D, h, w, transitive_group = field_info(poly)
        if field_D != D:
            raise ArithmeticError("the field of %s has D = %s, not %s"
                                  % (poly, field_D, D))
        return {
            "number": zeta_values(poly)[s],
            "comment": comment(poly, D, k, h, w, transitive_group),
        }


def _source_path(filename):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


def fill_draft_once(generator, message):
    """Fill a fresh prose draft without the client's empty upsert probe."""
    run = "totally-real-quartic-zeta-negative-odd-%d" % int(time.time())
    entries = Entries(*generator.parameters)
    for params in generator.enumerate():
        entries.add(**params, **generator.value(params, generator.digits))

    answer = submit_entries(
        generator.table,
        entries,
        message=message,
        produced_by=_producer(generator),
        upsert=False,
        run=run,
        rigour=generator.rigour,
    )
    for filename in generator.files:
        with open(_source_path(filename), encoding="utf8") as handle:
            attach(
                generator.table,
                filename,
                handle.read(),
                run=run,
                message=message,
                rigour=generator.rigour,
            )
    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = TotallyRealQuarticZetaNegativeOdd()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            "zeta_K(s) at s = -1, -3, -5 for totally real quartic fields "
            "with D <= %d, from PARI lfun values recognised with Serre "
            "denominator bounds and checked against the functional equation "
            "and abelian character factorizations" % BOUND,
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
