"""Characteristic polynomials of matroids -- numberdb.org/T396

For a finite matroid M on ground set E, this stores

    chi_M(q) = sum_{S subset E} (-1)^|S| q^(r(E)-r(S)).

The table uses one symbolic parameter, ``matroid``. Uniform matroids are named
``U(r,n)``. The other rows use Sage's catalog names, excluding graphic catalog
matroids and the catalog's uniform aliases because those are represented by the
``U(r,n)`` rows.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The generator computes every uniform matroid U(r,n) with 2 <= r <= n <= 11 and
every simple non-graphic matroid in sage.matroids.catalog with at most 600
flats, apart from catalog aliases for uniform matroids.
"""

import inspect
import os
import re
import sys
import warnings

import numberdb.sage as numberdb
import sage.matroids.catalog as catalog
from sage.matroids.matroids_catalog import Uniform
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


warnings.filterwarnings("ignore", message="Resolving lazy import .*")

MOST_UNIFORM_ELEMENTS = 11
CATALOG_FLAT_LIMIT = 600

UNIFORM_ALIASES = {
    "U24": "U(2,4)",
    "U25": "U(2,5)",
    "U35": "U(3,5)",
    "U36": "U(3,6)",
}

# These are cycle matroids of named graphs in the catalog. The family issue
# keeps graphic matroids under the graph-indexed tables and uses M(K_4), M(K_5)
# only as checks.
GRAPHIC_CATALOG_NAMES = {"K4", "K5", "K33", "Wheel4"}

R = PolynomialRing(ZZ, "q")
q = R.gen()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def uniform_key(r, n):
    return "U(%d,%d)" % (r, n)


def parse_uniform_key(key):
    found = re.fullmatch(r"U\((\d+),(\d+)\)", str(key))
    if not found:
        return None
    return int(found.group(1)), int(found.group(2))


def uniform_matroid(r, n):
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Resolving lazy import .*")
        return Uniform(r, n)


def flat_count(matroid):
    return sum(len(list(matroid.flats(rank)))
               for rank in range(matroid.rank() + 1))


def catalog_constructor_names():
    for name in sorted(candidate for candidate in dir(catalog)
                       if not candidate.startswith("_")):
        constructor = getattr(catalog, name)
        if not callable(constructor):
            continue
        try:
            signature = inspect.signature(constructor)
        except (TypeError, ValueError):
            continue
        required = [
            parameter for parameter in signature.parameters.values()
            if parameter.default is inspect._empty
            and parameter.kind in (
                parameter.POSITIONAL_ONLY,
                parameter.POSITIONAL_OR_KEYWORD,
                parameter.KEYWORD_ONLY,
            )
        ]
        if not required:
            yield name


def catalog_matroid(name):
    return getattr(catalog, str(name))()


def catalog_row(name):
    matroid = catalog_matroid(name)
    if name in UNIFORM_ALIASES or name in GRAPHIC_CATALOG_NAMES:
        return None
    if not matroid.is_simple():
        return None
    flats = flat_count(matroid)
    if flats > CATALOG_FLAT_LIMIT:
        return None
    return {
        "rank": matroid.rank(),
        "size": matroid.size(),
        "kind": 1,
        "key": name,
        "flats": flats,
    }


def ordered_rows():
    rows = []
    for n in range(2, MOST_UNIFORM_ELEMENTS + 1):
        for r in range(2, n + 1):
            matroid = uniform_matroid(r, n)
            rows.append({
                "rank": r,
                "size": matroid.size(),
                "kind": 0,
                "key": uniform_key(r, n),
                "flats": flat_count(matroid),
            })

    for name in catalog_constructor_names():
        row = catalog_row(name)
        if row is not None:
            rows.append(row)

    return sorted(rows, key=lambda row: (
        row["rank"], row["size"], row["kind"], row["key"]
    ))


def matroid_from_key(key):
    uniform = parse_uniform_key(key)
    if uniform is not None:
        return uniform_matroid(*uniform)
    return catalog_matroid(str(key))


def characteristic_polynomial(matroid):
    return R(matroid.characteristic_polynomial(q))


class CharacteristicPolynomialsOfMatroids(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE") or "T396"
    parameters = ("matroid",)
    type = "Z[]"
    rigour = "exact"

    _rows = None

    def rows(self):
        if self._rows is None:
            self._rows = ordered_rows()
        return self._rows

    def enumerate(self):
        for row in self.rows():
            yield {"matroid": row["key"]}

    def value(self, params, digits):
        return characteristic_polynomial(matroid_from_key(params["matroid"]))


if __name__ == "__main__":
    _key_from_stdin()
    generator = CharacteristicPolynomialsOfMatroids()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(generator.publish(
            message="characteristic polynomials of matroids",
            assisted_by=os.environ.get("NUMBERDB_ASSISTED_BY", "codex")))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
