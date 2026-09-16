"""Davenport-Stothers polynomial triples -- numberdb.org/T281.

    h(t) = f(t)^3 - g(t)^2,  deg(f) = 2M,  deg(h) = M + 1

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The table stores the five printed representatives from Montanus: the unique
classes for M <= 4 and Birch's symmetric M = 5 example. Montanus prints f and
h for these examples; g is recovered as the exact square root of f^3 - h. The
M = 5 row is independently checked against Sijsling and Voight's Example 1.8,
which prints f, g and h, and against its t = +/- 9 Hall-triple specialisations.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


TABLE = os.environ.get("NUMBERDB_TABLE", "T281")

R = PolynomialRing(QQ, "t")
t = R.gen()


SOURCE_F_H = {
    (1, "unique"): (4 * t**2 + 1, 1 + 3 * t**2),
    (2, "unique"): (t**4 + 4 * t, -8 * t**3 - 36),
    (3, "unique"): (
        t**6 + 4 * t**4 + 10 * t**2 + 6,
        QQ(27) / QQ(4) * (4 * t**4 + 13 * t**2 + 32),
    ),
    (4, "unique"): (
        t**8 - 2 * t**7 + 7 * t**6 - 6 * t**5
        + 11 * t**4 + 4 * t**3 + 12 * t + 1,
        -QQ(27) / QQ(4) * (
            4 * t**5 - 5 * t**4 + 18 * t**3 - 3 * t**2 + 14 * t + 31
        ),
    ),
    (5, "Birch"): (
        QQ(1) / QQ(9) * (t**10 + 6 * t**7 + 15 * t**4 + 12 * t),
        -QQ(1) / QQ(108) * (3 * t**6 + 14 * t**3 + 27),
    ),
}

SIJSLING_VOIGHT_M5 = (
    QQ(1) / QQ(9) * (t**10 + 6 * t**7 + 15 * t**4 + 12 * t),
    QQ(1) / QQ(54) * (
        2 * t**15 + 18 * t**12 + 72 * t**9 + 144 * t**6 + 135 * t**3 + 27
    ),
    -QQ(1) / QQ(108) * (3 * t**6 + 14 * t**3 + 27),
)

_CHECKED = False
_TRIPLES = None


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _rational_square_root(value):
    root = QQ(value).sqrt()
    if root not in QQ:
        raise ArithmeticError("%s is not a rational square" % value)
    return root


def _polynomial_square_root(poly):
    """Return the rational polynomial root without calling Sage factorisation."""
    if poly == 0:
        return R(0)
    degree = poly.degree()
    if degree % 2:
        raise ArithmeticError("polynomial has odd degree")
    root_degree = degree // 2
    lead_root = _rational_square_root(poly[degree])

    coeffs = [QQ(0)] * (root_degree + 1)
    coeffs[root_degree] = lead_root
    for exponent in range(degree - 1, root_degree - 1, -1):
        root_index = exponent - root_degree
        known = QQ(0)
        for i in range(root_index + 1, root_degree + 1):
            j = exponent - i
            if 0 <= j <= root_degree:
                known += coeffs[i] * coeffs[j]
        coeffs[root_index] = (poly[exponent] - known) / (2 * lead_root)

    root = R(coeffs)
    if root**2 != poly:
        raise ArithmeticError("polynomial is not a square")
    return root


def _triples():
    global _TRIPLES
    if _TRIPLES is not None:
        return _TRIPLES
    triples = {}
    for key, (f, h) in SOURCE_F_H.items():
        g = _polynomial_square_root(f**3 - h)
        if g.leading_coefficient() < 0:
            g = -g
        triples[key] = (f, g, h)
    _TRIPLES = triples
    return triples


def _check_degree_conditions(M, f, g, h):
    if f.degree() != 2 * M:
        raise ArithmeticError("f has the wrong degree for M=%s" % M)
    if g.degree() != 3 * M:
        raise ArithmeticError("g has the wrong degree for M=%s" % M)
    if h.degree() != M + 1:
        raise ArithmeticError("h has the wrong degree for M=%s" % M)
    if h != f**3 - g**2:
        raise ArithmeticError("h != f^3 - g^2 for M=%s" % M)


def _check_birch_specialisations(f, g, h):
    expected = {
        -9: (384242766, 7531969451458, -14668),
        9: (390620082, 7720258643465, -14857),
    }
    for value, wanted in expected.items():
        got = (f(value), abs(g(value)), h(value))
        if got != wanted:
            raise ArithmeticError("Birch specialisation t=%s gave %s" %
                                  (value, got))


def _check_data():
    global _CHECKED
    if _CHECKED:
        return

    triples = _triples()
    if set(triples) != set(SOURCE_F_H):
        raise ArithmeticError("source keys changed")

    for (M, _tree), (f, g, h) in triples.items():
        _check_degree_conditions(M, f, g, h)

    if triples[(5, "Birch")] != SIJSLING_VOIGHT_M5:
        raise ArithmeticError("Birch row does not match Sijsling-Voight")
    _check_birch_specialisations(*triples[(5, "Birch")])

    _CHECKED = True


class DavenportStothersPolynomialTriples(numberdb.Generator):

    table = TABLE
    parameters = ("M", "tree", "part")
    type = "Q[]"
    rigour = "exact"

    def enumerate(self):
        _check_data()
        for M, tree_name in sorted(_triples()):
            for part in ("f", "g", "h"):
                yield {"M": str(M), "tree": tree_name, "part": part}

    def value(self, params, digits):
        _check_data()
        M = int(params["M"])
        key = (M, params["tree"])
        f, g, h = _triples()[key]
        part = params["part"]
        if part == "f":
            return f
        if part == "g":
            return g
        if part == "h":
            return h
        raise ValueError("unknown part %s" % part)


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
        attach(table, name, body, run=run, message=message,
               rigour=generator.rigour)

    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = DavenportStothersPolynomialTriples()
    _check_data()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="exact Davenport-Stothers triples from Montanus"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
