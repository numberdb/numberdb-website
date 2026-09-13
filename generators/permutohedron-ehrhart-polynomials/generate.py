"""Ehrhart and h-star polynomials of permutohedra -- numberdb.org/T235

For n = 3, ..., 20 this stores the Ehrhart polynomial L_{Pi_n}(t) of the
permutohedron Pi_n and the corresponding h-star polynomial h^*_{Pi_n}(z).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

Stanley's graphical-zonotope formula says that

    L_{Pi_n}(t) = sum_k f_{n,k} t^k,

where f_{n,k} is the number of forests on n labelled vertices with k edges.
The forest numbers are computed by the exact recurrence that chooses the
tree component containing vertex 1. The h-star polynomial is then the
numerator of the Ehrhart series with denominator (1-z)^n.
"""

import os
import sys
from math import comb

import numberdb.sage as numberdb
from sage.rings.rational_field import QQ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


T235 = "T235"
UP_TO_N = 20

_T = PolynomialRing(QQ, "t")
_t = _T.gen()
_Z = PolynomialRing(QQ, "z")
_z = _Z.gen()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def tree_count(vertices):
    if vertices == 1:
        return 1
    return vertices ** (vertices - 2)


def forest_counts(n):
    """Return [f_{n,0}, ..., f_{n,n-1}] for forests of K_n by edge count."""
    by_components = [[0 for _ in range(n + 1)] for _ in range(n + 1)]
    by_components[0][0] = 1

    for vertices in range(1, n + 1):
        for components in range(1, vertices + 1):
            total = 0
            for size in range(1, vertices + 1):
                total += (
                    comb(vertices - 1, size - 1)
                    * tree_count(size)
                    * by_components[vertices - size][components - 1]
                )
            by_components[vertices][components] = total

    return [
        by_components[n][n - edges]
        for edges in range(n)
    ]


def ehrhart_polynomial(n):
    return sum(QQ(c) * _t ** i for i, c in enumerate(forest_counts(n)))


def h_star_coefficients(n):
    ehrhart = ehrhart_polynomial(n)
    coefficients = []
    for m in range(n):
        coefficient = QQ(0)
        for j in range(m + 1):
            coefficient += QQ((-1) ** j * comb(n, j)) * ehrhart(m - j)
        assert coefficient.denominator() == 1
        coefficients.append(coefficient)
    while coefficients and coefficients[-1] == 0:
        coefficients.pop()
    return coefficients


def h_star_polynomial(n):
    return sum(QQ(c) * _z ** i for i, c in enumerate(h_star_coefficients(n)))


class PermutohedronEhrhartPolynomials(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", T235)
    parameters = ("n", "form")
    type = "Q[]"
    rigour = "exact"

    def enumerate(self, up_to_n=UP_TO_N):
        for n in range(3, up_to_n + 1):
            yield {"n": str(n), "form": "ehrhart"}
            yield {"n": str(n), "form": "h-star"}

    def value(self, params, digits):
        n = int(params["n"])
        form = params["form"]
        if form == "ehrhart":
            return {
                "number": ehrhart_polynomial(n),
                "param-latex": "$L_{\\Pi_%d}(t)$" % n,
            }
        if form == "h-star":
            return {
                "number": h_star_polynomial(n),
                "param-latex": "$h^*_{\\Pi_%d}(z)$" % n,
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
    generator = PermutohedronEhrhartPolynomials()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="permutohedron Ehrhart and h-star polynomials"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
