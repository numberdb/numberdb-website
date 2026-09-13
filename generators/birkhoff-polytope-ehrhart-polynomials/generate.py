"""Ehrhart and h-star polynomials of Birkhoff polytopes -- numberdb.org/T232

For n = 3, ..., 6 this stores the Ehrhart polynomial H_n(t) of the
Birkhoff polytope B_n and the corresponding h-star polynomial h^*_{B_n}(z).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The h-star rows are transcribed from OEIS A259473. The Ehrhart polynomials are
computed from those rows by the exact binomial transform

    H_n(t) = sum_i h_i^* binomial(t + d - i, d),  d = (n - 1)^2.

The rings are named rather than taken from `sage.all`, so this runs on a
modular passagemath as well as on a full SageMath.
"""

import os
import sys
from math import factorial

import numberdb.sage as numberdb
from sage.rings.rational_field import QQ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


UP_TO_N = 6

H_STAR_COEFFICIENTS = {
    3: [1, 1, 1],
    4: [1, 14, 87, 148, 87, 14, 1],
    5: [
        1, 103, 4306, 63110, 388615, 1115068, 1575669, 1115068, 388615,
        63110, 4306, 103, 1,
    ],
    6: [
        1, 694, 184015, 15902580, 567296265, 9816969306, 91422589980,
        490333468494, 1583419977390, 3166404385990, 3982599815746,
        3166404385990, 1583419977390, 490333468494, 91422589980,
        9816969306, 567296265, 15902580, 184015, 694, 1,
    ],
}

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


def dimension(n):
    return (n - 1) ** 2


def binomial_polynomial(shift, degree):
    value = _T.one()
    for j in range(degree):
        value *= _t + QQ(shift - j)
    return value / QQ(factorial(degree))


def h_star_polynomial(n):
    return sum(QQ(c) * _z ** i for i, c in enumerate(H_STAR_COEFFICIENTS[n]))


def ehrhart_polynomial(n):
    d = dimension(n)
    return sum(
        QQ(c) * binomial_polynomial(d - i, d)
        for i, c in enumerate(H_STAR_COEFFICIENTS[n])
    )


class BirkhoffPolytopeEhrhartPolynomials(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T232")
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
                "param-latex": "$H_%d(t)$" % n,
            }
        if form == "h-star":
            return {
                "number": h_star_polynomial(n),
                "param-latex": "$h^*_{B_%d}(z)$" % n,
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
    generator = BirkhoffPolytopeEhrhartPolynomials()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="Birkhoff polytope Ehrhart and h-star polynomials"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
