"""Minimum dilatations of pseudo-Anosov maps -- numberdb.org/T285

This table holds the exact values of the orientable-foliation minimum
dilatations delta_g^+ for closed orientable surfaces of genus 1 through 5,
and genus 7 and 8. The values are largest real roots of the polynomials
stated by Lanneau and Thiffeault, with the genus 7 and 8 bounds realized by
the later cited constructions.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ
from sage.rings.real_mpfi import RealIntervalField


TABLE = "T285"
WORKING_GUARD = 160

R = PolynomialRing(QQ, "x")
x = R.gen()

POLYNOMIALS = {
    1: x**2 - 3 * x + 1,
    2: x**4 - x**3 - x**2 - x + 1,
    3: x**6 - x**4 - x**3 - x**2 + 1,
    4: x**8 - x**5 - x**4 - x**3 + 1,
    5: x**10 + x**9 - x**7 - x**6 - x**5 - x**4 - x**3 + x + 1,
    7: x**14 + x**13 - x**9 - x**8 - x**7 - x**6 - x**5 + x + 1,
    8: x**16 - x**9 - x**8 - x**7 + 1,
}

SOURCE_ROUNDED = {
    2: "1.72208",
    3: "1.40127",
    4: "1.28064",
    5: "1.17628",
    7: "1.11548110945659",
    8: "1.12876",
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _rounded_interval(text):
    whole, fractional = text.split(".", 1)
    scale = ZZ(10) ** len(fractional)
    centre = QQ(ZZ(whole) * scale + ZZ(fractional)) / QQ(scale)
    radius = QQ(1) / QQ(2 * scale)
    return centre - radius, centre + radius


def _root_greater_than_one(polynomial, digits):
    field = RealIntervalField(numberdb.bits(digits, losing=WORKING_GUARD))
    roots = []
    for root, multiplicity in polynomial.roots(field):
        if multiplicity != 1:
            raise ArithmeticError("multiple real root in %s" % polynomial)
        if root.lower() > 1:
            roots.append(root)
    if len(roots) != 1:
        raise ArithmeticError("%s has %d real roots greater than 1"
                              % (polynomial, len(roots)))
    root = roots[0]
    low_value = polynomial(root.lower())
    high_value = polynomial(root.upper())
    if not ((low_value <= 0 <= high_value)
            or (high_value <= 0 <= low_value)):
        raise ArithmeticError("root interval for %s does not bracket a zero"
                              % polynomial)
    return root


def _check_against_source(g, root):
    if g == 1:
        field = root.parent()
        exact = (field(3) + field(5).sqrt()) / 2
        if not root.overlaps(exact):
            raise ArithmeticError("genus-one root does not contain (3+sqrt(5))/2")
        return
    low, high = _rounded_interval(SOURCE_ROUNDED[g])
    if not (root.lower() >= low and root.upper() < high):
        raise ArithmeticError(
            "root interval %s is not compatible with source value %s"
            % (root, SOURCE_ROUNDED[g]))


def _entry_comment(g):
    if g == 1:
        return "This is $(3+\\sqrt5)/2$."
    if g == 5:
        return "This is HREF{T284#1,1,0,-1,-1,-1}[Lehmer's number]."
    if g == 7:
        return ("Aaber and Dunfield, and independently Kin and Takasawa, "
                "realized Lanneau and Thiffeault's lower bound for this "
                "genus CITE{AD} CITE{KT}.")
    if g == 8:
        return ("Hironaka realized Lanneau and Thiffeault's lower bound for "
                "this genus CITE{Hironaka}.")
    return None


class MinimumPseudoAnosovDilatations(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE") or TABLE
    parameters = ("g",)
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self):
        for g in sorted(POLYNOMIALS):
            yield {"g": str(g)}

    def value(self, params, digits):
        g = int(params["g"])
        root = _root_greater_than_one(POLYNOMIALS[g], digits)
        _check_against_source(g, root)
        comment = _entry_comment(g)
        if comment:
            return {"number": root, "comment": comment}
        return root


def main():
    _key_from_stdin()
    generator = MinimumPseudoAnosovDilatations()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="isolated polynomial roots"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
