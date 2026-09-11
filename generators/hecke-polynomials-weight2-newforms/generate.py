"""Hecke polynomials of weight 2 newforms -- numberdb.org/T217.

    chi_{f,p}(x) = det(x I - multiplication by a_p | K_f)

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The values are computed exactly from Sage's newform q-expansions. The generator
uses the LMFDB label order for weight 2, trivial-character newform orbits of
level at most 100, omits the dimension-one orbits, and checks the product over
all newform orbits at a level against PARI/GP's newspace Hecke matrix.
"""

import os
import sys
from itertools import permutations

import numberdb.sage as numberdb
# Sage's Newforms path needs this module initialised explicitly in this image.
import sage.rings.polynomial.laurent_polynomial_ring  # noqa: F401
from sage.libs.pari import pari
from sage.modular.modform.constructor import Newforms
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ

MAX_LEVEL = 100
#: The primes the table runs over.
#:
#: More of them rather than more levels, because the newforms are the
#: expensive part and these are free once a form is known -- and because the
#: bigger p is, the likelier a_p is to generate the coefficient field, which
#: is the only case this table has anything to say about.
PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59)
LETTERS = "abcdefghijklmnopqrstuvwxyz"

EXPECTED_ORBITS = (
    ("23.2.a.a", 2),
    ("29.2.a.a", 2),
    ("31.2.a.a", 2),
    ("35.2.a.b", 2),
    ("39.2.a.b", 2),
    ("41.2.a.a", 3),
    ("43.2.a.b", 2),
    ("47.2.a.a", 4),
    ("51.2.a.b", 2),
    ("53.2.a.b", 3),
    ("55.2.a.b", 2),
    ("59.2.a.a", 5),
    ("61.2.a.b", 3),
    ("62.2.a.b", 2),
    ("63.2.a.b", 2),
    ("65.2.a.b", 2),
    ("65.2.a.c", 2),
    ("67.2.a.b", 2),
    ("67.2.a.c", 2),
    ("68.2.a.a", 2),
    ("69.2.a.b", 2),
    ("71.2.a.a", 3),
    ("71.2.a.b", 3),
    ("73.2.a.b", 2),
    ("73.2.a.c", 2),
    ("74.2.a.a", 2),
    ("74.2.a.b", 2),
    ("77.2.a.d", 2),
    ("79.2.a.b", 5),
    ("81.2.a.a", 2),
    ("82.2.a.b", 2),
    ("83.2.a.b", 6),
    ("85.2.a.b", 2),
    ("85.2.a.c", 2),
    ("86.2.a.a", 2),
    ("86.2.a.b", 2),
    ("87.2.a.a", 2),
    ("87.2.a.b", 3),
    ("88.2.a.b", 2),
    ("89.2.a.c", 5),
    ("91.2.a.c", 2),
    ("91.2.a.d", 3),
    ("93.2.a.a", 2),
    ("93.2.a.b", 3),
    ("94.2.a.b", 2),
    ("95.2.a.a", 3),
    ("95.2.a.b", 4),
    ("97.2.a.a", 3),
    ("97.2.a.b", 4),
    ("98.2.a.b", 2),
)

QX = PolynomialRing(QQ, "x")
xq = QX.gen()
ZX = PolynomialRing(ZZ, "x")
xz = ZX.gen()

_FORMS = {}
_RECORDS = None
_CHARPOLY = {}
_CHECKED = False


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _letter(index):
    if index >= len(LETTERS):
        raise ValueError("the label alphabet here only covers 26 orbits")
    return LETTERS[index]


def _forms(level):
    level = ZZ(level)
    if level not in _FORMS:
        _FORMS[level] = list(Newforms(int(level), 2, names="a"))
    return _FORMS[level]


def _degree(form):
    try:
        return ZZ(form.base_ring().degree())
    except AttributeError:
        return ZZ(1)


def _all_records():
    global _RECORDS
    if _RECORDS is not None:
        return _RECORDS
    records = []
    for level in range(1, MAX_LEVEL + 1):
        for index, form in enumerate(_forms(level)):
            degree = _degree(form)
            label = "%s.2.a.%s" % (level, _letter(index))
            records.append({
                "level": ZZ(level),
                "label": label,
                "index": ZZ(index),
                "degree": degree,
                "form": form,
            })
    _RECORDS = records
    return records


def _selected_records():
    return [record for record in _all_records() if record["degree"] >= 2]


def _generates_the_field(record, prime):
    """Whether a_p generates K_f, which is when this entry says anything.

    The characteristic polynomial of multiplication by a_p has the degree of
    K_f whatever a_p is. When a_p is rational it is (x - a_p)^d: the degree
    comes from the field and the content is one small integer, so the entry
    is an ordinary polynomial wearing a disguise. An earlier draft held 89
    entries of which 78 were (x - a)^2 for a = 0..7 -- perfect squares of a
    linear polynomial, which would have answered a search for x^2 - 6x + 9
    with a table about modular forms.

    Irreducible is the test: then the characteristic polynomial is the
    minimal polynomial of a_p, a_p generates K_f, and the entry records
    something a reader cannot get by inspection.
    """
    polynomial = _coefficient_charpoly(record, prime)
    return polynomial.degree() >= 2 and polynomial.is_irreducible()


def _permutation_sign(perm):
    inversions = 0
    for i in range(len(perm)):
        for j in range(i + 1, len(perm)):
            if perm[i] > perm[j]:
                inversions += 1
    return -1 if inversions % 2 else 1


def _charpoly_from_rows(rows):
    dim = len(rows)
    if dim == 0:
        return ZX(1)
    total = QX(0)
    for perm in permutations(range(dim)):
        term = QX(1)
        for row, col in enumerate(perm):
            entry = xq if row == col else QX(0)
            entry -= rows[row][col]
            term *= entry
        if _permutation_sign(perm) == 1:
            total += term
        else:
            total -= term

    coefficients = []
    for coefficient in total.list():
        if coefficient.denominator() != 1:
            raise ArithmeticError("nonintegral characteristic coefficient %s"
                                  % coefficient)
        coefficients.append(ZZ(coefficient))
    return ZX(coefficients)


def _coefficient_charpoly(record, prime):
    key = (record["label"], ZZ(prime))
    if key in _CHARPOLY:
        return _CHARPOLY[key]

    coefficient = record["form"].coefficient(int(prime))
    if record["degree"] == 1:
        polynomial = xz - ZZ(coefficient)
    else:
        rows = [[QQ(c) for c in row] for row in coefficient.matrix().rows()]
        polynomial = _charpoly_from_rows(rows)

    if polynomial.degree() != record["degree"]:
        raise ArithmeticError(
            "%s, p=%s: degree %s polynomial for degree %s field"
            % (record["label"], prime, polynomial.degree(), record["degree"]))
    _CHARPOLY[key] = polynomial
    return polynomial


def _pari_newspace_charpoly(level, prime):
    raw = pari("charpoly(mfheckemat(mfinit([%d,2],0),%d))" % (level, prime))
    return ZX([ZZ(c) for c in raw.Vecrev()])


def _check_global():
    global _CHECKED
    if _CHECKED:
        return

    found = tuple((record["label"], int(record["degree"]))
                  for record in _selected_records())
    if found != EXPECTED_ORBITS:
        raise ArithmeticError(
            "Sage newform order disagrees with the LMFDB label list")

    #How many orbits, which is the fact about the mathematics. The row count
    #was written here as 400, which is that number times the eight primes the
    #table ran over at the time, so adding a prime broke a check that was not
    #about primes at all. The orbit list above pins each one by label and
    #degree; this pins how many there are.
    if len(_selected_records()) != 50:
        raise ArithmeticError("got %s orbits of degree >= 2, expected 50"
                              % len(_selected_records()))

    required = {
        ("23.2.a.a", 2): xz**2 + xz - 1,
        ("23.2.a.a", 13): xz**2 - 6 * xz + 9,
        ("83.2.a.b", 2): (xz**6 - xz**5 - 9 * xz**4 + 7 * xz**3
                           + 20 * xz**2 - 12 * xz - 8),
        ("97.2.a.a", 2): xz**3 + 4 * xz**2 + 3 * xz - 1,
    }
    by_label = {record["label"]: record for record in _selected_records()}
    for (label, prime), expected in required.items():
        found_polynomial = _coefficient_charpoly(by_label[label], prime)
        if found_polynomial != expected:
            raise ArithmeticError(
                "%s, p=%s: got %s, expected %s"
                % (label, prime, found_polynomial, expected))

    by_level = {}
    for record in _all_records():
        by_level.setdefault(record["level"], []).append(record)
    for level, records in by_level.items():
        for prime in PRIMES:
            product = ZX(1)
            for record in records:
                product *= _coefficient_charpoly(record, prime)
            expected = _pari_newspace_charpoly(level, prime)
            if product != expected:
                raise ArithmeticError(
                    "level %s, p=%s: product over Sage orbits is %s, "
                    "but PARI newspace gives %s"
                    % (level, prime, product, expected))
    _CHECKED = True


def _record_by_label(label):
    for record in _selected_records():
        if record["label"] == label:
            return record
    raise ValueError("no selected newform orbit %s" % label)


def _comment(record, prime):
    parts = []
    if (ZZ(prime) ** 2).divides(record["level"]):
        parts.append(
            "Here $p^2$ divides the level $N$, so $a_p=0$."
        )
    if not _coefficient_charpoly(record, prime).is_irreducible():
        parts.append(
            "The characteristic polynomial is reducible over $\\mathbb{Q}$; "
            "$a_{%s}$ does not generate the full coefficient field $K_f$."
            % prime
        )
    return " ".join(parts) if parts else None


class WeightTwoNewformHeckePolynomials(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T217")
    parameters = ("label", "p")
    type = "Z[]"
    rigour = "exact"

    def enumerate(self):
        _check_global()
        for record in _selected_records():
            for prime in PRIMES:
                if not _generates_the_field(record, prime):
                    continue
                yield {"label": record["label"], "p": ZZ(prime)}

    def value(self, params, digits):
        label = str(params["label"])
        prime = ZZ(params["p"])
        if prime not in PRIMES:
            raise ValueError("prime outside this table: p=%s" % prime)
        record = _record_by_label(label)
        polynomial = _coefficient_charpoly(record, prime)
        comment = _comment(record, prime)
        if comment:
            return {"number": polynomial, "comment": comment}
        return polynomial


if __name__ == "__main__":
    _key_from_stdin()
    generator = WeightTwoNewformHeckePolynomials()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="Hecke polynomials of weight 2 newforms, N <= %d"
                    % (MAX_LEVEL,)))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
