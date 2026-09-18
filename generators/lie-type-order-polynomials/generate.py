"""Orders of finite groups of Lie type as polynomials in q -- numberdb.org/T258

This generator stores exact order polynomials in the field-size parameter q.
For families whose simple groups are central quotients, the stored polynomial
is the numerator of the simple-order formula, before the quotient by the
central factor depending on q.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The range is A_n for 1 <= n <= 15, B_n and {}^2A_n for 2 <= n <= 15,
C_n for 3 <= n <= 15, D_n and {}^2D_n for 4 <= n <= 15, and all the
exceptional and Suzuki-Ree families that occur in the Lie-type part of T220.
"""

import os
import sys
from math import gcd

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


TABLE = "T258"
MAX_CLASSICAL_RANK = 15

_R = PolynomialRing(ZZ, "q")
_q = _R.gen()

FAMILIES = (
    "A", "B", "C", "D",
    "E6", "E7", "E8", "F4", "G2",
    "2A", "2D", "2E6", "3D4",
    "2B2", "2F4", "2G2",
)

FIXED_RANKS = {
    "E6": 6,
    "2E6": 6,
    "E7": 7,
    "E8": 8,
    "F4": 4,
    "G2": 2,
    "3D4": 4,
    "2B2": 2,
    "2G2": 2,
    "2F4": 4,
}

CENTER_FACTORS = {
    "A": lambda n, q: gcd(n + 1, q - 1),
    "2A": lambda n, q: gcd(n + 1, q + 1),
    "B": lambda n, q: gcd(2, q - 1),
    "C": lambda n, q: gcd(2, q - 1),
    "D": lambda n, q: gcd(4, q ** n - 1),
    "2D": lambda n, q: gcd(4, q ** n + 1),
    "E6": lambda n, q: gcd(3, q - 1),
    "2E6": lambda n, q: gcd(3, q + 1),
    "E7": lambda n, q: gcd(2, q - 1),
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def product(values):
    out = _R.one()
    for value in values:
        out *= value
    return out


def family_ranks(family):
    if family == "A":
        return range(1, MAX_CLASSICAL_RANK + 1)
    if family in ("B", "2A"):
        return range(2, MAX_CLASSICAL_RANK + 1)
    if family == "C":
        return range(3, MAX_CLASSICAL_RANK + 1)
    if family in ("D", "2D"):
        return range(4, MAX_CLASSICAL_RANK + 1)
    return range(FIXED_RANKS[family], FIXED_RANKS[family] + 1)


def order_polynomial(family, n):
    q = _q
    if family == "A":
        return q ** (n * (n + 1) // 2) * product(q ** i - 1
                                                  for i in range(2, n + 2))
    if family == "2A":
        return q ** (n * (n + 1) // 2) * product(
            q ** i - (-1) ** i for i in range(2, n + 2))
    if family in ("B", "C"):
        return q ** (n * n) * product(q ** (2 * i) - 1
                                      for i in range(1, n + 1))
    if family == "D":
        return (q ** (n * (n - 1)) * (q ** n - 1)
                * product(q ** (2 * i) - 1 for i in range(1, n)))
    if family == "2D":
        return (q ** (n * (n - 1)) * (q ** n + 1)
                * product(q ** (2 * i) - 1 for i in range(1, n)))
    if family == "E6":
        return q ** 36 * product(q ** i - 1 for i in (2, 5, 6, 8, 9, 12))
    if family == "2E6":
        return q ** 36 * product(q ** i - (-1) ** i
                                 for i in (2, 5, 6, 8, 9, 12))
    if family == "E7":
        return q ** 63 * product(q ** i - 1
                                 for i in (2, 6, 8, 10, 12, 14, 18))
    if family == "E8":
        return q ** 120 * product(q ** i - 1
                                  for i in (2, 8, 12, 14, 18, 20, 24, 30))
    if family == "F4":
        return q ** 24 * product(q ** i - 1 for i in (2, 6, 8, 12))
    if family == "G2":
        return q ** 6 * (q ** 2 - 1) * (q ** 6 - 1)
    if family == "3D4":
        return q ** 12 * (q ** 8 + q ** 4 + 1) * (q ** 6 - 1) * (q ** 2 - 1)
    if family == "2B2":
        return q ** 2 * (q ** 2 + 1) * (q - 1)
    if family == "2F4":
        return q ** 12 * (q ** 6 + 1) * (q ** 4 - 1) * (q ** 3 + 1) * (q - 1)
    if family == "2G2":
        return q ** 3 * (q ** 3 + 1) * (q - 1)
    raise ValueError("unknown family %s" % family)


def entries():
    for family in FAMILIES:
        for n in family_ranks(family):
            yield family, n


def _t220_number(t220, family, n, q):
    return ZZ(t220["Numbers"][family][str(n)][str(q)].get("number")
              if isinstance(t220["Numbers"][family][str(n)][str(q)], dict)
              else t220["Numbers"][family][str(n)][str(q)])


def _gap_size(command):
    from sage.interfaces.gap import gap

    return ZZ(gap.eval(command))


def self_check():
    gap_checks = (
        ("A", 1, 4, "SL(2,4)"),
        ("A", 2, 2, "SL(3,2)"),
        ("A", 3, 2, "SL(4,2)"),
        ("2A", 2, 3, "SU(3,3)"),
        ("2A", 3, 2, "SU(4,2)"),
        ("B", 2, 3, "SO(5,3)"),
        ("C", 2, 3, "Sp(4,3)"),
        ("C", 3, 2, "Sp(6,2)"),
    )
    for family, n, q, command in gap_checks:
        got = ZZ(order_polynomial(family, n)(q))
        expected = _gap_size("Size(%s)" % command)
        if got != expected:
            raise AssertionError("%s_%s(%s) is %s, GAP says %s"
                                 % (family, n, q, got, expected))

    t220 = numberdb.table("T220")
    checked = 0
    sample_qs = {
        "A": (4, 5, 7, 8, 9),
        "B": (3, 4, 5),
        "C": (2, 3, 4),
        "D": (2, 3),
        "E6": (2, 3),
        "E7": (2, 3),
        "E8": (2,),
        "F4": (2, 3),
        "G2": (3, 4),
        "2A": (3, 4, 5),
        "2D": (2, 3),
        "2E6": (2, 3),
        "3D4": (2, 3),
        "2B2": (8, 32),
        "2F4": (8, 32),
        "2G2": (27,),
    }
    for family, n in entries():
        for q in sample_qs.get(family, ()):
            try:
                stored = _t220_number(t220, family, n, q)
            except KeyError:
                continue
            factor = CENTER_FACTORS.get(family, lambda n, q: 1)(n, q)
            got = ZZ(order_polynomial(family, n)(q))
            if got != factor * stored:
                raise AssertionError("%s_%s(%s) gives %s, but T220 with "
                                     "central factor gives %s"
                                     % (family, n, q, got, factor * stored))
            checked += 1
    print("checked %d T220 specialisations and %d GAP orders"
          % (checked, len(gap_checks)))


class LieTypeOrderPolynomials(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", TABLE)
    parameters = ("family", "n")
    type = "Z[]"
    rigour = "exact"

    def enumerate(self):
        for family, n in entries():
            yield {"family": family, "n": n}

    def value(self, params, digits):
        return order_polynomial(str(params["family"]), int(params["n"]))


if __name__ == "__main__":
    _key_from_stdin()
    if os.environ.get("NUMBERDB_SELF_CHECK") == "1":
        self_check()
        sys.exit(0)

    generator = LieTypeOrderPolynomials()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="finite Lie-type order polynomials"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
