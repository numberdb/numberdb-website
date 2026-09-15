r"""Zernike polynomials -- numberdb.org/T251

This draft stores the unnormalised Zernike radial polynomials
R_n^m(rho), for n <= 20 with m < n, and the unnormalised Cartesian
polynomials Z_n^l(x,y), for n <= 12, omitting only the monomials 1, x
and y.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The coefficients are exact integers. The radial polynomials are computed from
the binomial formula, and the Cartesian forms are built from
Re((x+i y)^m) and Im((x+i y)^m). Before any value is returned, the generator
checks the printed small radial examples, the Jacobi-polynomial identity by an
independent exact formula for P_s^(m,0), the m=0 Legendre recurrence, the exact
radial orthogonality relation, the Cartesian restrictions on the x-axis, and
the initial single-index tables.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import binomial
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


TID = "T251"
RADIAL_UP_TO = 20
CARTESIAN_UP_TO = 12

RHO_ZZ = PolynomialRing(ZZ, "rho")
rho = RHO_ZZ.gen()

XY_ZZ = PolynomialRing(ZZ, ("x", "y"))
x, y = XY_ZZ.gens()

RHO_QQ = PolynomialRing(QQ, "rho")
rho_q = RHO_QQ.gen()

U_QQ = PolynomialRing(QQ, "u")
u = U_QQ.gen()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def admissible(n, l):
    return abs(l) <= n and (n - l) % 2 == 0


def radial_terms(n, m):
    """The (exponent, coefficient) terms of R_n^m(rho)."""
    if m < 0 or m > n or (n - m) % 2:
        raise ValueError("inadmissible radial indices n=%s, m=%s" % (n, m))
    terms = []
    half = (n - m) // 2
    for k in range(half + 1):
        exponent = n - 2 * k
        coefficient = (
            ZZ(-1) ** k
            * ZZ(binomial(n - k, k))
            * ZZ(binomial(n - 2 * k, half - k))
        )
        terms.append((exponent, coefficient))
    return terms


_RADIAL = {}
_CARTESIAN = {}


def radial_polynomial(n, m):
    key = (int(n), int(m))
    if key not in _RADIAL:
        value = RHO_ZZ.zero()
        for exponent, coefficient in radial_terms(*key):
            value += coefficient * rho ** exponent
        _RADIAL[key] = value
    return _RADIAL[key]


def real_part_power(m):
    value = XY_ZZ.zero()
    for j in range(0, m + 1, 2):
        value += ZZ(-1) ** (j // 2) * ZZ(binomial(m, j)) * x ** (m - j) * y ** j
    return value


def imag_part_power(m):
    value = XY_ZZ.zero()
    for j in range(1, m + 1, 2):
        value += (
            ZZ(-1) ** ((j - 1) // 2)
            * ZZ(binomial(m, j))
            * x ** (m - j)
            * y ** j
        )
    return value


def cartesian_polynomial(n, l):
    key = (int(n), int(l))
    if key not in _CARTESIAN:
        n, l = key
        if not admissible(n, l):
            raise ValueError("inadmissible Cartesian indices n=%s, l=%s" % (n, l))
        m = abs(l)
        if l > 0:
            angular = real_part_power(m)
        elif l < 0:
            angular = imag_part_power(m)
        else:
            angular = XY_ZZ.one()

        radius_squared = x ** 2 + y ** 2
        value = XY_ZZ.zero()
        for exponent, coefficient in radial_terms(n, m):
            value += coefficient * radius_squared ** ((exponent - m) // 2) * angular
        _CARTESIAN[key] = XY_ZZ(value)
    return _CARTESIAN[key]


def jacobi_polynomial(k, alpha, beta):
    """P_k^(alpha,beta)(u), by the exact binomial formula."""
    value = U_QQ.zero()
    for j in range(k + 1):
        value += (
            QQ(binomial(k + alpha, k - j))
            * QQ(binomial(k + beta, j))
            * ((u - 1) / QQ(2)) ** j
            * ((u + 1) / QQ(2)) ** (k - j)
        )
    return value


def jacobi_radial(n, m):
    s = (n - m) // 2
    p = jacobi_polynomial(s, m, 0)
    argument = RHO_QQ(1) - QQ(2) * rho_q ** 2
    return RHO_QQ(((-1) ** s) * rho_q ** m * p(argument))


def legendre_polynomials(up_to):
    polynomials = [U_QQ.one()]
    if up_to == 0:
        return polynomials
    polynomials.append(u)
    for k in range(1, up_to):
        polynomials.append(
            ((2 * k + 1) * u * polynomials[k] - k * polynomials[k - 1])
            * (QQ(1) / QQ(k + 1))
        )
    return polynomials


def integral_with_weight(poly):
    """Integral of poly(rho) * rho from 0 to 1."""
    total = QQ(0)
    for exponent, coefficient in RHO_QQ(poly).dict().items():
        total += QQ(coefficient) / QQ(exponent + 2)
    return total


def noll_index(n, l):
    base = n * (n + 1) // 2 + abs(l)
    residue = n % 4
    if (l > 0 and residue in (0, 1)) or (l < 0 and residue in (2, 3)):
        epsilon = 0
    else:
        epsilon = 1
    return base + epsilon


def osa_index(n, l):
    return (n * (n + 2) + l) // 2


def fringe_index(n, l):
    sign = 1 if l > 0 else -1 if l < 0 else 0
    q = (n + abs(l)) // 2
    return (1 + q) ** 2 - 2 * abs(l) + (1 - sign) // 2


def wyant_index(n, l):
    return fringe_index(n, l) - 1


MODE_NAMES = {
    (0, 0): "piston",
    (1, -1): "vertical tilt",
    (1, 1): "horizontal tilt",
    (2, -2): "oblique astigmatism",
    (2, 0): "defocus",
    (2, 2): "vertical astigmatism",
    (3, -3): "vertical trefoil",
    (3, -1): "vertical coma",
    (3, 1): "horizontal coma",
    (3, 3): "oblique trefoil",
    (4, -4): "oblique quadrafoil",
    (4, -2): "oblique secondary astigmatism",
    (4, 0): "primary spherical aberration",
    (4, 2): "vertical secondary astigmatism",
    (4, 4): "vertical quadrafoil",
}


WIKI_INDEX_ROWS = [
    (0, 0, 1, 0, 1, 0),
    (1, 1, 2, 2, 2, 1),
    (1, -1, 3, 1, 3, 2),
    (2, 0, 4, 4, 4, 3),
    (2, -2, 5, 3, 6, 5),
    (2, 2, 6, 5, 5, 4),
    (3, -1, 7, 7, 8, 7),
    (3, 1, 8, 8, 7, 6),
    (3, -3, 9, 6, 11, 10),
    (3, 3, 10, 9, 10, 9),
    (4, 0, 11, 12, 9, 8),
    (4, 2, 12, 13, 12, 11),
    (4, -2, 13, 11, 13, 12),
    (4, 4, 14, 14, 17, 16),
    (4, -4, 15, 10, 18, 17),
    (5, 1, 16, 18, 14, 13),
    (5, -1, 17, 17, 15, 14),
    (5, 3, 18, 19, 19, 18),
    (5, -3, 19, 16, 20, 19),
    (5, 5, 20, 20, 26, 25),
]


RADIAL_EXAMPLES = {
    (0, 0): RHO_ZZ(1),
    (1, 1): rho,
    (2, 0): 2 * rho ** 2 - 1,
    (2, 2): rho ** 2,
    (3, 1): 3 * rho ** 3 - 2 * rho,
    (3, 3): rho ** 3,
    (4, 0): 6 * rho ** 4 - 6 * rho ** 2 + 1,
    (4, 2): 4 * rho ** 4 - 3 * rho ** 2,
    (4, 4): rho ** 4,
    (5, 1): 10 * rho ** 5 - 12 * rho ** 3 + 3 * rho,
    (5, 3): 5 * rho ** 5 - 4 * rho ** 3,
    (5, 5): rho ** 5,
    (6, 0): 20 * rho ** 6 - 30 * rho ** 4 + 12 * rho ** 2 - 1,
    (6, 2): 15 * rho ** 6 - 20 * rho ** 4 + 6 * rho ** 2,
    (6, 4): 6 * rho ** 6 - 5 * rho ** 4,
    (6, 6): rho ** 6,
}


CARTESIAN_EXAMPLES = {
    (2, -2): 2 * x * y,
    (2, 0): 2 * x ** 2 + 2 * y ** 2 - 1,
    (2, 2): x ** 2 - y ** 2,
    (3, -1): 3 * x ** 2 * y + 3 * y ** 3 - 2 * y,
    (3, 1): 3 * x ** 3 + 3 * x * y ** 2 - 2 * x,
    (3, -3): 3 * x ** 2 * y - y ** 3,
    (3, 3): x ** 3 - 3 * x * y ** 2,
}


_CHECKED = False


def self_check():
    global _CHECKED
    if _CHECKED:
        return

    for key, expected in RADIAL_EXAMPLES.items():
        if radial_polynomial(*key) != expected:
            raise ArithmeticError("radial example %s disagrees with the source" % (key,))

    for key, expected in CARTESIAN_EXAMPLES.items():
        if cartesian_polynomial(*key) != expected:
            raise ArithmeticError("Cartesian example %s disagrees with the source" % (key,))

    for n in range(RADIAL_UP_TO + 1):
        for m in range(n + 1):
            if (n - m) % 2:
                continue
            radial = radial_polynomial(n, m)
            if radial(ZZ(1)) != 1:
                raise ArithmeticError("R_%d^%d(1) is not 1" % (n, m))
            if RHO_QQ(radial) != jacobi_radial(n, m):
                raise ArithmeticError("R_%d^%d disagrees with the Jacobi identity" % (n, m))

    legendre = legendre_polynomials(RADIAL_UP_TO // 2)
    argument = QQ(2) * rho_q ** 2 - QQ(1)
    for k, polynomial in enumerate(legendre):
        if RHO_QQ(radial_polynomial(2 * k, 0)) != RHO_QQ(polynomial(argument)):
            raise ArithmeticError("R_%d^0 disagrees with the Legendre recurrence" % (2 * k,))

    for m in range(RADIAL_UP_TO + 1):
        degrees = [n for n in range(m, RADIAL_UP_TO + 1, 2)]
        for n in degrees:
            for other in degrees:
                found = integral_with_weight(radial_polynomial(n, m) * radial_polynomial(other, m))
                expected = QQ(1) / QQ(2 * n + 2) if n == other else QQ(0)
                if found != expected:
                    raise ArithmeticError(
                        "orthogonality failed for m=%d, n=%d, n'=%d" % (m, n, other)
                    )

    for n in range(CARTESIAN_UP_TO + 1):
        for l in range(0, n + 1):
            if not admissible(n, l):
                continue
            value = cartesian_polynomial(n, l)(rho_q, 0)
            expected = RHO_QQ(radial_polynomial(n, l))
            if value != expected:
                raise ArithmeticError("Z_%d^%d(rho,0) is not R_%d^%d" % (n, l, n, l))
            if l > 0 and cartesian_polynomial(n, -l)(rho_q, 0) != RHO_QQ.zero():
                raise ArithmeticError("Z_%d^%d(rho,0) is not zero" % (n, -l))

    for n, l, noll, osa, fringe, wyant in WIKI_INDEX_ROWS:
        if (noll_index(n, l), osa_index(n, l), fringe_index(n, l), wyant_index(n, l)) != (
            noll,
            osa,
            fringe,
            wyant,
        ):
            raise ArithmeticError("single-index formulas fail at n=%d, l=%d" % (n, l))

    _CHECKED = True


def mode_indices(n, l):
    text = (
        "Noll $j=%d$, OSA/ANSI $j=%d$, Fringe $j=%d$, Wyant $j=%d$"
        % (noll_index(n, l), osa_index(n, l), fringe_index(n, l), wyant_index(n, l))
    )
    name = MODE_NAMES.get((n, l))
    if name:
        text += "; %s" % name
    return text


def entry_comment(n, l, form):
    if form == "cartesian":
        return mode_indices(n, l) + "."
    if l == 0:
        return "Radial part for %s." % mode_indices(n, 0)
    return (
        "Radial part for $l=%d$ (%s) and $l=%d$ (%s)."
        % (l, mode_indices(n, l), -l, mode_indices(n, -l))
    )


def is_omitted_monomial(n, l, form):
    if form == "radial":
        return l == n
    return (n, l) in ((0, 0), (1, 1), (1, -1))


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
        attach(
            table,
            name,
            body,
            run=run,
            message=message,
            rigour=generator.rigour,
        )
        stored.append(name)

    return {
        "tid": answer.get("tid", table),
        "revision": answer.get("revision"),
        "entries": len(entries),
        "files": stored,
    }


class ZernikePolynomials(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", TID)
    parameters = ("n", "l", "form")
    type = "Z[]"
    rigour = "exact"

    def enumerate(self, radial_up_to=RADIAL_UP_TO, cartesian_up_to=CARTESIAN_UP_TO):
        for n in range(max(radial_up_to, cartesian_up_to) + 1):
            for m in range(n + 1):
                if (n - m) % 2:
                    continue
                if n <= radial_up_to and not is_omitted_monomial(n, m, "radial"):
                    yield {"n": str(n), "l": str(m), "form": "radial"}
                if n <= cartesian_up_to:
                    signs = [0] if m == 0 else [m, -m]
                    for l in signs:
                        if not is_omitted_monomial(n, l, "cartesian"):
                            yield {"n": str(n), "l": str(l), "form": "cartesian"}

    def value(self, params, digits):
        self_check()
        n = int(params["n"])
        l = int(params["l"])
        form = params["form"]
        if form == "radial":
            number = radial_polynomial(n, l)
        elif form == "cartesian":
            number = cartesian_polynomial(n, l)
        else:
            raise ValueError("unknown form %r" % (form,))
        return {"number": number, "comment": entry_comment(n, l, form)}


if __name__ == "__main__":
    _key_from_stdin()
    generator = ZernikePolynomials()
    mode = os.environ.get("NUMBERDB_PUBLISH")
    if mode == "1" or "--publish" in sys.argv:
        print(
            fill_draft_once(
                generator,
                message=(
                    "Zernike polynomials: radial n <= %d and Cartesian n <= %d, "
                    "with monomial rows omitted"
                )
                % (RADIAL_UP_TO, CARTESIAN_UP_TO)
            )
        )
    elif mode == "preview" or "--preview" in sys.argv:
        print(generator.preview())
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
