"""Euler characteristics of smooth complete intersections -- numberdb.org/T333.

For a smooth complete intersection X in P^n of multidegree
(d_1, ..., d_k), this generator stores the topological Euler characteristic

    chi(X) = (prod_i d_i) [h^(n-k)] (1 + h)^(n + 1)
             prod_i (1 + d_i h)^(-1)

as an exact integer. The rows use n <= 10, all d_i <= 10, and
prod_i d_i <= 100, with the multidegree written nondecreasing.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

On the NumberDB build machine, where arguments are not passed through
agents/sage.sh, publish with:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
          agents/sage.sh generate.py

The values are exact integers. The integrity checks compare standard complete
intersection values and verify Hirzebruch's generating-series formula on every
row. After the draft has been filled, a non-publish run also checks the same
identities on the values read back from the API.
"""

import os
import sys
from itertools import combinations_with_replacement

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


TABLE = os.environ.get("NUMBERDB_TABLE", "T333")
MAX_AMBIENT_DIMENSION = 10
MAX_DEGREE_ENTRY = 10
MAX_TOTAL_DEGREE = 100

H_RING = PolynomialRing(ZZ, "h")
H = H_RING.gen()

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


def truncate_h(polynomial, degree):
    return sum(ZZ(polynomial[j]) * H ** j for j in range(degree + 1))


def truncate_z(polynomial, degree):
    return sum(ZZ(polynomial[j]) * Z ** j for j in range(degree + 1))


def degrees_from_text(text):
    return tuple(ZZ(part) for part in str(text).split(",") if part)


def degree_text(degrees):
    return ",".join(str(ZZ(degree)) for degree in degrees)


def degree_tuples(length):
    for degrees in combinations_with_replacement(
            range(2, MAX_DEGREE_ENTRY + 1), length):
        if product(degrees) <= MAX_TOTAL_DEGREE:
            yield tuple(ZZ(degree) for degree in degrees)


def iter_parameters():
    for n in range(2, MAX_AMBIENT_DIMENSION + 1):
        for length in range(1, n):
            for degrees in degree_tuples(length):
                yield {"n": ZZ(n), "d": degree_text(degrees)}


def euler_from_chern_formula(n, degrees):
    n = ZZ(n)
    degrees = tuple(ZZ(degree) for degree in degrees)
    dimension = n - len(degrees)
    value = (H_RING.one() + H) ** (n + 1)
    for degree in degrees:
        inverse = sum((-degree * H) ** j for j in range(dimension + 1))
        value = truncate_h(value * inverse, dimension)
    return product(degrees) * ZZ(value[dimension])


def inverse_one_minus_z(degree):
    return sum(Z ** j for j in range(degree + 1))


def inverse_one_plus_coefficient_z(coefficient, degree):
    coefficient = ZZ(coefficient)
    return sum((-coefficient * Z) ** j for j in range(degree + 1))


def euler_from_hirzebruch_series(n, degrees):
    """Euler characteristic from the complete-intersection generating series."""
    n = ZZ(n)
    degrees = tuple(ZZ(degree) for degree in degrees)
    dimension = n - len(degrees)
    series = inverse_one_minus_z(dimension) ** 2
    series = truncate_z(series, dimension)
    for degree in degrees:
        series = truncate_z(
            series * inverse_one_plus_coefficient_z(degree - 1, dimension),
            dimension,
        )
    return product(degrees) * ZZ(series[dimension])


def notable_comment(n, degrees):
    key = (int(n), tuple(int(degree) for degree in degrees))
    comments = {
        (2, (2,)): "Smooth conic in $\\mathbb P^2$.",
        (3, (3,)): "Cubic surface.",
        (3, (4,)): "Quartic K3 surface.",
        (4, (5,)): "Quintic threefold.",
        (5, (2, 4)): "Calabi-Yau threefold of type $(2,4)$.",
        (5, (3, 3)): "Calabi-Yau threefold of type $(3,3)$.",
        (7, (2, 2, 2, 2)): (
            "Complete intersection of four quadrics; a Calabi-Yau threefold."
        ),
    }
    return comments.get(key)


def row_value(n, degrees):
    value = euler_from_chern_formula(n, degrees)
    comment = notable_comment(n, degrees)
    if comment:
        return {"number": value, "comment": comment}
    return value


def _plain_number(value):
    if isinstance(value, dict):
        return ZZ(value["number"])
    return ZZ(value)


def check_identities():
    rows = list(iter_parameters())
    if len(rows) != 999:
        raise AssertionError("expected 999 rows, got %s" % (len(rows),))

    known = {
        (2, (2,)): 2,
        (3, (3,)): 9,
        (3, (4,)): 24,
        (4, (5,)): -200,
    }
    for key, expected in known.items():
        found = euler_from_chern_formula(key[0], key[1])
        if found != ZZ(expected):
            raise AssertionError(
                "known value failed at n=%s, d=%s: %s != %s"
                % (key[0], degree_text(key[1]), found, expected)
            )

    for params in rows:
        n = ZZ(params["n"])
        degrees = degrees_from_text(params["d"])
        via_chern = euler_from_chern_formula(n, degrees)
        via_series = euler_from_hirzebruch_series(n, degrees)
        if via_chern != via_series:
            raise AssertionError(
                "Hirzebruch series failed at n=%s, d=%s: %s != %s"
                % (n, params["d"], via_chern, via_series)
            )

    values = [_plain_number(row_value(p["n"], degrees_from_text(p["d"])))
              for p in rows]
    longest = max(
        ((len(str(value)), row) for value, row in zip(values, rows)),
        key=lambda item: item[0],
    )
    print("integrity checks passed for %d complete-intersection Euler characteristics"
          % len(rows))
    print("matched conic, cubic surface, quartic K3 surface and quintic threefold values")
    print("Hirzebruch generating-series check passed on every row")
    print("longest integer has %d characters at n=%s, d=%s"
          % (longest[0], longest[1]["n"], longest[1]["d"]))


def _flatten_numbers(node, path=()):
    if isinstance(node, list):
        for item in node:
            yield from _flatten_numbers(item, path)
    elif isinstance(node, dict) and "number" in node:
        params = node.get("params") or {}
        yield params, node["number"]
    elif isinstance(node, dict):
        for key, value in node.items():
            yield from _flatten_numbers(value, path + (key,))


def stored_values():
    table = numberdb.table(TABLE)
    values = {}
    for params, number in _flatten_numbers(table.get("Numbers") or []):
        if not params:
            continue
        values[(str(params["n"]), str(params["d"]))] = ZZ(number)
    return values


def check_stored_identities():
    values = stored_values()
    rows = list(iter_parameters())
    if len(values) != len(rows):
        raise AssertionError("stored table has %s values, expected %s"
                             % (len(values), len(rows)))
    for params in rows:
        key = (str(params["n"]), str(params["d"]))
        expected = euler_from_hirzebruch_series(params["n"],
                                                degrees_from_text(params["d"]))
        if values.get(key) != expected:
            raise AssertionError(
                "stored value failed at n=%s, d=%s: %s != %s"
                % (params["n"], params["d"], values.get(key), expected)
            )
    print("stored values satisfy the Hirzebruch generating-series formula")


class CompleteIntersectionEulerCharacteristics(numberdb.Generator):

    table = TABLE
    parameters = ("n", "d")
    type = "Z"
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
    generator = CompleteIntersectionEulerCharacteristics()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="fill complete-intersection Euler characteristics from exact formula",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        if not report.ok:
            sys.exit(1)
        check_stored_identities()


if __name__ == "__main__":
    main()
