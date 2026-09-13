"""Ehrhart and h-star polynomials of root polytopes -- numberdb.org/T233

For the irreducible crystallographic root systems this stores the Ehrhart
polynomial L_Phi(t) of the full root polytope P_Phi = conv(Phi), in the root
lattice, and its h-star polynomial h^*_{P_Phi}(z).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The h-star rows use the closed forms for the coordinator polynomials of root
lattices. The Ehrhart rows are computed from those rows by the exact binomial
transform

    L_Phi(t) = sum_i h_i^* binomial(t + d - i, d),  d = rank(Phi).

The rings are named rather than taken from `sage.all`, so this runs on a
modular passagemath as well as on a full SageMath.
"""

import os
import sys
from math import comb, factorial

import numberdb.sage as numberdb
from sage.rings.rational_field import QQ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


T233 = "T233"
CLASSICAL_UP_TO_RANK = 20

EXCEPTIONAL_H_STAR = {
    "E6": [1, 66, 645, 1384, 645, 66, 1],
    "E7": [1, 119, 2037, 8211, 8787, 2037, 119, 1],
    "E8": [1, 232, 7228, 55384, 133510, 107224, 24508, 232, 1],
    "F4": [1, 44, 198, 140, 1],
    "G2": [1, 10, 7],
}

_T = PolynomialRing(QQ, "t")
_t = _T.gen()
_Z = PolynomialRing(QQ, "z")
_z = _Z.gen()


def choose(n, k):
    if k < 0 or k > n:
        return 0
    return comb(n, k)


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def binomial_polynomial(shift, degree):
    value = _T.one()
    for j in range(degree):
        value *= _t + QQ(shift - j)
    return value / QQ(factorial(degree))


def parse_type(root_type):
    family = root_type[0]
    rank = int(root_type[1:])
    return family, rank


def h_star_coefficients(root_type):
    if root_type in EXCEPTIONAL_H_STAR:
        return EXCEPTIONAL_H_STAR[root_type]

    family, n = parse_type(root_type)
    if family == "A":
        return [choose(n, k) ** 2 for k in range(n + 1)]
    if family == "B":
        return [
            choose(2 * n + 1, 2 * k) - 2 * n * choose(n - 1, k - 1)
            for k in range(n + 1)
        ]
    if family == "C":
        return [choose(2 * n, 2 * k) for k in range(n + 1)]
    if family == "D":
        return [
            choose(2 * n, 2 * k) - 2 * n * choose(n - 2, k - 1)
            for k in range(n + 1)
        ]
    raise ValueError("unknown root type %r" % (root_type,))


def h_star_polynomial(root_type):
    return sum(QQ(c) * _z ** i for i, c in enumerate(h_star_coefficients(root_type)))


def ehrhart_polynomial(root_type):
    coefficients = h_star_coefficients(root_type)
    degree = len(coefficients) - 1
    return sum(
        QQ(c) * binomial_polynomial(degree - i, degree)
        for i, c in enumerate(coefficients)
    )


def root_types(up_to_rank=CLASSICAL_UP_TO_RANK):
    for n in range(2, up_to_rank + 1):
        yield "A%d" % n
    for n in range(2, up_to_rank + 1):
        yield "B%d" % n
    for n in range(3, up_to_rank + 1):
        yield "C%d" % n
    for n in range(4, up_to_rank + 1):
        yield "D%d" % n
    for root_type in ("E6", "E7", "E8", "F4", "G2"):
        yield root_type


class RootPolytopeEhrhartPolynomials(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", T233)
    parameters = ("type", "form")
    type = "Q[]"
    rigour = "exact"

    def enumerate(self, up_to_rank=CLASSICAL_UP_TO_RANK):
        for root_type in root_types(up_to_rank):
            yield {"type": root_type, "form": "ehrhart"}
            yield {"type": root_type, "form": "h-star"}

    def value(self, params, digits):
        root_type = params["type"]
        form = params["form"]
        if form == "ehrhart":
            return {
                "number": ehrhart_polynomial(root_type),
                "param-latex": "$L_{%s}(t)$" % root_type,
            }
        if form == "h-star":
            return {
                "number": h_star_polynomial(root_type),
                "param-latex": "$h^*_{%s}(z)$" % root_type,
            }
        raise ValueError("unknown form %r" % (form,))


def fill_draft_once(generator, message):
    """Fill a fresh draft without the empty upsert probe."""
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
        attach(table, name, body, run=run, message=message,
               rigour=generator.rigour)
        stored.append(name)

    return {
        "tid": answer.get("tid", table),
        "revision": answer.get("revision"),
        "entries": len(entries),
        "files": stored,
    }


if __name__ == "__main__":
    _key_from_stdin()
    generator = RootPolytopeEhrhartPolynomials()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="root polytope Ehrhart and h-star polynomials"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
