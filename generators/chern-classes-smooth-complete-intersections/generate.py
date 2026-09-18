"""Chern classes of smooth complete intersections -- numberdb.org/T332.

For a smooth complete intersection X in P^n of multidegree
(d_1, ..., d_k), this generator stores the total Chern class

    c(T_X) = [(1 + h)^(n + 1) prod_i (1 + d_i h)^(-1)]_{<= n-k}

as a polynomial in ZZ[h]. The rows use n <= 10, all d_i <= 10, and
prod_i d_i <= 100, with the multidegree written nondecreasing.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

On the NumberDB build machine, where arguments are not passed through
agents/sage.sh, publish with:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
          agents/sage.sh generate.py

The values are exact polynomials over ZZ. The integrity checks compare the
quintic threefold row with the standard printed value, verify the first Chern
class formula on every row, and compare the Euler characteristic obtained from
the top Chern class with Hirzebruch's independent generating function.
"""

import os
import sys
from itertools import combinations_with_replacement

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


TABLE = os.environ.get("NUMBERDB_TABLE", "T332")
MAX_AMBIENT_DIMENSION = 10
MAX_DEGREE_ENTRY = 10
MAX_TOTAL_DEGREE = 100

RING = PolynomialRing(ZZ, "h")
H = RING.gen()

Z_RING = PolynomialRing(ZZ, "z")
Z = Z_RING.gen()


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
    out = ZZ(1)
    for value in values:
        out *= ZZ(value)
    return out


def truncate(polynomial, degree):
    return sum(ZZ(polynomial[j]) * H ** j for j in range(degree + 1))


def degrees_from_text(text):
    return tuple(ZZ(part) for part in str(text).split(",") if part)


def degree_text(degrees):
    return ",".join(str(ZZ(degree)) for degree in degrees)


def degree_tuples(length):
    for degrees in combinations_with_replacement(
            range(2, MAX_DEGREE_ENTRY + 1), length):
        if product(degrees) <= MAX_TOTAL_DEGREE:
            yield tuple(ZZ(degree) for degree in degrees)


def chern_class(n, degrees):
    n = ZZ(n)
    degrees = tuple(ZZ(degree) for degree in degrees)
    dimension = n - len(degrees)
    value = (RING.one() + H) ** (n + 1)
    for degree in degrees:
        inverse = sum((-degree * H) ** j for j in range(dimension + 1))
        value = truncate(value * inverse, dimension)
    return truncate(value, dimension)


def euler_from_chern(n, degrees):
    dimension = ZZ(n) - len(degrees)
    return product(degrees) * ZZ(chern_class(n, degrees)[dimension])


def truncate_z(polynomial, degree):
    return sum(ZZ(polynomial[j]) * Z ** j for j in range(degree + 1))


def inverse_linear_z(coefficient, degree):
    return sum((-ZZ(coefficient) * Z) ** j for j in range(degree + 1))


def hirzebruch_euler_characteristic(dimension, degrees):
    """Euler characteristic from the complete-intersection generating series."""
    dimension = ZZ(dimension)
    series = sum(ZZ(j + 1) * Z ** j for j in range(dimension + 1))
    for degree in degrees:
        series = truncate_z(
            series * inverse_linear_z(ZZ(degree) - 1, dimension),
            dimension,
        )
    return product(degrees) * ZZ(series[dimension])


def notable_comment(n, degrees):
    key = (int(n), tuple(int(degree) for degree in degrees))
    comments = {
        (2, (2,)): "Smooth conic in $\\mathbb P^2$.",
        (3, (3,)): "Cubic surface.",
        (3, (4,)): "Quartic K3 surface.",
        (4, (5,)): (
            "Quintic threefold; integrating the top Chern class gives "
            "Euler characteristic $-200$."
        ),
        (5, (2, 4)): "Calabi-Yau threefold of type $(2,4)$.",
        (5, (3, 3)): "Calabi-Yau threefold of type $(3,3)$.",
        (7, (2, 2, 2, 2)): (
            "Complete intersection of four quadrics; a Calabi-Yau threefold."
        ),
    }
    return comments.get(key)


def row_value(n, degrees):
    value = chern_class(n, degrees)
    comment = notable_comment(n, degrees)
    if comment:
        return {"number": value, "comment": comment}
    return value


def iter_parameters():
    for n in range(2, MAX_AMBIENT_DIMENSION + 1):
        for length in range(1, n):
            for degrees in degree_tuples(length):
                yield {"n": ZZ(n), "d": degree_text(degrees)}


def check_identities():
    rows = list(iter_parameters())
    if len(rows) != 999:
        raise AssertionError("expected 999 rows, got %s" % (len(rows),))

    quintic = chern_class(4, (5,))
    if quintic != RING.one() + 10 * H ** 2 - 40 * H ** 3:
        raise AssertionError("quintic threefold check failed: %s" % (quintic,))

    for params in rows:
        n = ZZ(params["n"])
        degrees = degrees_from_text(params["d"])
        value = chern_class(n, degrees)
        first = ZZ(n + 1 - sum(degrees))
        if ZZ(value[1]) != first:
            raise AssertionError(
                "first Chern class failed at n=%s, d=%s" % (n, params["d"])
            )
        dimension = n - len(degrees)
        via_chern = product(degrees) * ZZ(value[dimension])
        via_hirzebruch = hirzebruch_euler_characteristic(dimension, degrees)
        if via_chern != via_hirzebruch:
            raise AssertionError(
                "Euler characteristic failed at n=%s, d=%s: %s != %s"
                % (n, params["d"], via_chern, via_hirzebruch)
            )

    lengths = [
        (len(str(chern_class(params["n"], degrees_from_text(params["d"])))), params)
        for params in rows
    ]
    longest = max(lengths, key=lambda item: item[0])
    print("integrity checks passed for %d complete-intersection Chern classes"
          % len(rows))
    print("matched the quintic threefold value 1 + 10*h^2 - 40*h^3")
    print("first Chern class and Euler characteristic checks passed on every row")
    print("longest polynomial has %d characters at n=%s, d=%s"
          % (longest[0], longest[1]["n"], longest[1]["d"]))


class CompleteIntersectionChernClasses(numberdb.Generator):

    table = TABLE
    parameters = ("n", "d")
    type = "Z[]"
    rigour = "exact"

    def enumerate(self):
        yield from iter_parameters()

    def value(self, params, digits):
        return row_value(ZZ(params["n"]), degrees_from_text(params["d"]))


def fill_draft_once(generator, message):
    """Fill a fresh prose draft without the client's empty upsert probe."""
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
        attach(table, name, body, run=run, message=message, rigour=generator.rigour)

    return answer


def main():
    _key_from_stdin()
    check_identities()
    generator = CompleteIntersectionChernClasses()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="fill complete-intersection Chern classes from exact formula",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
