"""$x$-coordinates of torsion points of elliptic curves over Q -- numberdb.org/T346.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The generator reads Sage's mini Cremona database, keeps every curve of
conductor N <= 17, and lists the roots of PARI/GP's x-coordinate division
polynomial elldivpol(E,n) for 2 <= n <= 5.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.databases.cremona import CremonaDatabase
from sage.libs.pari import pari
from sage.rings.complex_interval_field import ComplexIntervalField
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.qqbar import QQbar
from sage.rings.rational_field import QQ


TABLE = os.environ.get("NUMBERDB_TABLE", "T346")
CONDUCTOR_BOUND = 17
TORSION_LEVELS = (2, 3, 4, 5)
INTERVAL_BITS = 350

R = PolynomialRing(QQ, "x")
x = R.gen()
CIF = ComplexIntervalField(INTERVAL_BITS)


def key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def curve_rows(bound=CONDUCTOR_BOUND):
    database = CremonaDatabase()
    rows = []
    for conductor in range(1, bound + 1):
        for label_tail, data in sorted(database.allcurves(conductor).items()):
            ainvs, _rank, _torsion_order = data
            rows.append(
                {
                    "N": conductor,
                    "label": "%s%s" % (conductor, label_tail),
                    "ainvs": tuple(QQ(a) for a in ainvs),
                }
            )
    if len(rows) != 21:
        raise ArithmeticError("expected 21 curves with N <= 17, got %d" % len(rows))
    return rows


def b_invariants(ainvs):
    a1, a2, a3, a4, a6 = ainvs
    b2 = a1 * a1 + 4 * a2
    b4 = 2 * a4 + a1 * a3
    b6 = a3 * a3 + 4 * a6
    b8 = a1 * a1 * a6 + 4 * a2 * a6 - a1 * a3 * a4 + a2 * a3 * a3 - a4 * a4
    return b2, b4, b6, b8


def recurrence_polynomials(ainvs):
    b2, b4, b6, b8 = b_invariants(ainvs)
    f2 = 4 * x**3 + b2 * x**2 + 2 * b4 * x + b6
    f3 = 3 * x**4 + b2 * x**3 + 3 * b4 * x**2 + 3 * b6 * x + b8
    g4 = (
        2 * x**6
        + b2 * x**5
        + 5 * b4 * x**4
        + 10 * b6 * x**3
        + 10 * b8 * x**2
        + (b2 * b8 - b4 * b6) * x
        + b4 * b8
        - b6**2
    )
    return {
        2: f2,
        3: f3,
        4: f2 * g4,
        5: f2**2 * g4 - f3**3,
    }


def pari_polynomial(ainvs, n):
    expression = str(pari([int(a) for a in ainvs]).ellinit().elldivpol(n))
    return R(expression.replace("^", "**"))


def torsion_polynomial(ainvs, n):
    polynomial = pari_polynomial(ainvs, n)
    independent = recurrence_polynomials(ainvs)[n]
    if polynomial != independent:
        raise ArithmeticError("PARI elldivpol disagrees with recurrence at n=%s" % n)
    return polynomial


def expected_degree(n):
    if n % 2:
        return (n * n - 1) // 2
    return n * n // 2 + 1


def _center(interval):
    return interval.center()


def root_sort_key(root):
    z = CIF(root)
    return (_center(z.real()), _center(z.imag()))


def sorted_roots(polynomial):
    roots = polynomial.roots(QQbar, multiplicities=False)
    roots.sort(key=root_sort_key)
    if len(roots) != polynomial.degree():
        raise ArithmeticError(
            "expected %d distinct roots, got %d" % (polynomial.degree(), len(roots))
        )
    return roots


def rational_root(root, rational_roots):
    for value in rational_roots:
        if root == QQbar(value):
            return value
    return None


def complex_value(root, rational_roots):
    rational = rational_root(root, rational_roots)
    if rational is not None:
        return rational
    value = CIF(root)
    if not is_finite_interval(value.real()) or not is_finite_interval(value.imag()):
        raise ArithmeticError("non-finite root interval: %s" % value)
    return value


def is_finite_interval(interval):
    if hasattr(interval, "is_finite"):
        return bool(interval.is_finite())
    try:
        return not (interval.lower().is_infinity() or interval.upper().is_infinity())
    except AttributeError:
        return True


class EllipticCurveTorsionXCoordinates(numberdb.Generator):
    table = TABLE
    parameters = ("N", "c4", "c6", "n", "k")
    type = "C"
    digits = 100
    rigour = "proven"
    files = ("generate.py",)

    def __init__(self):
        super().__init__()
        self._rows = curve_rows()
        self._curves = {}
        self._root_data = {}
        self._checked = False
        for row in self._rows:
            c4, c6 = self._c_invariants(row["ainvs"])
            keyed = dict(row)
            keyed["c4"] = c4
            keyed["c6"] = c6
            self._curves[(row["N"], c4, c6)] = keyed

    def _c_invariants(self, ainvs):
        b2, b4, b6, b8 = b_invariants(ainvs)
        c4 = b2 * b2 - 24 * b4
        c6 = -b2**3 + 36 * b2 * b4 - 216 * b6
        if c4.denominator() != 1 or c6.denominator() != 1:
            raise ArithmeticError("nonintegral c-invariants for %s" % (ainvs,))
        return int(c4), int(c6)

    def _ensure_roots(self, N, c4, c6, n):
        key = (int(N), int(c4), int(c6), int(n))
        if key in self._root_data:
            return self._root_data[key]
        curve = self._curves[(int(N), int(c4), int(c6))]
        polynomial = torsion_polynomial(curve["ainvs"], int(n))
        if polynomial.degree() != expected_degree(int(n)):
            raise ArithmeticError(
                "%s n=%s has degree %s" % (curve["label"], n, polynomial.degree())
            )
        roots = sorted_roots(polynomial)
        rational_roots = [root for root, _multiplicity in polynomial.roots(QQ)]
        self._root_data[key] = (curve, polynomial, roots, rational_roots)
        return self._root_data[key]

    def enumerate(self):
        for row in self._rows:
            c4, c6 = self._c_invariants(row["ainvs"])
            for n in TORSION_LEVELS:
                _curve, _polynomial, roots, _rational_roots = self._ensure_roots(
                    row["N"], c4, c6, n
                )
                for k in range(1, len(roots) + 1):
                    yield {
                        "N": row["N"],
                        "c4": c4,
                        "c6": c6,
                        "n": n,
                        "k": k,
                    }

    def value(self, params, digits):
        curve, _polynomial, roots, rational_roots = self._ensure_roots(
            params["N"], params["c4"], params["c6"], params["n"]
        )
        root = roots[int(params["k"]) - 1]
        return {
            "number": complex_value(root, rational_roots),
            "comment": "Cremona label %s." % curve["label"],
        }

    def run_integrity_checks(self):
        if self._checked:
            return
        rows = list(self.enumerate())
        if len(rows) != 21 * (3 + 4 + 9 + 12):
            raise ArithmeticError("unexpected entry count: %d" % len(rows))
        curve = self._curves[(11, 16, -152)]
        polynomial = torsion_polynomial(curve["ainvs"], 5)
        rational_roots = sorted(root for root, _multiplicity in polynomial.roots(QQ))
        if rational_roots != [QQ(0), QQ(1)]:
            raise ArithmeticError("11a3 n=5 rational roots are %s" % rational_roots)
        for key, (_curve, polynomial, roots, _rational_roots) in self._root_data.items():
            if len(roots) != expected_degree(key[3]):
                raise ArithmeticError("%s has wrong root count" % (key,))
            for root in roots:
                if polynomial(root) != 0:
                    raise ArithmeticError("%s is not a root of %s" % (root, polynomial))
        self._checked = True


def main():
    key_from_stdin()
    generator = EllipticCurveTorsionXCoordinates()
    generator.run_integrity_checks()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="filled torsion x-coordinate roots"))
        return
    report = generator.verify(sample=None)
    print(report)
    raise SystemExit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
