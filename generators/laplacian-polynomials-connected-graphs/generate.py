"""Laplacian polynomials of connected graphs -- numberdb.org/T238

For every connected simple graph G on at most seven vertices, named by its
canonical graph6 string, this stores det(xI - L(G)), where L(G) = D(G) - A(G)
is the combinatorial Laplacian.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The determinant is expanded directly over permutations rather than through a
polynomial matrix, because the named imports used here do not initialise every
Sage module that matrix(...).determinant() reaches for. The largest matrix is
only 7 by 7.
"""

import os
import sys
from collections import defaultdict
from functools import lru_cache
from itertools import permutations

import numberdb.sage as numberdb
from sage.graphs.graph_generators import graphs
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


T238 = "T238"
MAX_VERTICES = 7

_R = PolynomialRing(ZZ, "x")
_x = _R.gen()

NAMES = {
    "@": "complete graph $K_1$",
    "A_": "complete graph $K_2$",
    "BW": "path $P_3$",
    "Bw": "complete graph $K_3$",
    "CF": "star $K_{1,3}$",
    "CL": "path $P_4$",
    "C]": "cycle $C_4$",
    "C^": "diamond graph",
    "C~": "complete graph $K_4$",
    "D?{": "star $K_{1,4}$",
    "DBk": "bull graph",
    "DB{": "dart graph",
    "DFw": "complete bipartite graph $K_{2,3}$",
    "DBg": "path $P_5$",
    "DK{": "butterfly graph",
    "DLo": "cycle $C_5$",
    "Dbk": "house graph",
    "DN{": "house X graph",
    "D]{": "wheel $W_5$",
    "D~{": "complete graph $K_5$",
    "E?Bw": "star $K_{1,5}$",
    "E?~o": "complete bipartite graph $K_{2,4}$",
    "E@YO": "path $P_6$",
    "EIe_": "cycle $C_6$",
    "EFz_": "complete bipartite graph $K_{3,3}$",
    "ELrw": "wheel $W_6$",
    "E~~w": "complete graph $K_6$",
    "F??Fw": "star $K_{1,6}$",
    "F?B~o": "complete bipartite graph $K_{2,5}$",
    "F?~v_": "complete bipartite graph $K_{3,4}$",
    "F@HSO": "path $P_7$",
    "FHQSO": "cycle $C_7$",
    "FIefw": "wheel $W_7$",
    "FjaHw": "Moser spindle",
    "F~~~w": "complete graph $K_7$",
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


@lru_cache(maxsize=None)
def connected_graphs(max_vertices=MAX_VERTICES):
    out = []
    for n in range(1, max_vertices + 1):
        for graph in graphs(n):
            if graph.is_connected():
                canonical = graph.canonical_label(algorithm="sage")
                out.append((canonical.graph6_string(), canonical))
    return tuple(out)


@lru_cache(maxsize=None)
def graph_by_key(max_vertices=MAX_VERTICES):
    return {key: graph for key, graph in connected_graphs(max_vertices)}


def permutation_sign(perm):
    inversions = 0
    for i in range(len(perm)):
        for j in range(i + 1, len(perm)):
            if perm[i] > perm[j]:
                inversions += 1
    return -1 if inversions % 2 else 1


def determinant(entries):
    total = _R(0)
    for perm in permutations(range(len(entries))):
        term = _R(permutation_sign(perm))
        for row, col in enumerate(perm):
            term *= entries[row][col]
        total += term
    return total


def laplacian_entries(graph):
    vertices = sorted(graph.vertices())
    index = {vertex: i for i, vertex in enumerate(vertices)}
    size = len(vertices)
    entries = [[_R(0) for _ in range(size)] for _ in range(size)]
    for vertex in vertices:
        entries[index[vertex]][index[vertex]] = _R(graph.degree(vertex))
    for u, v, _label in graph.edges():
        i = index[u]
        j = index[v]
        entries[i][j] = _R(-1)
        entries[j][i] = _R(-1)
    return entries


@lru_cache(maxsize=None)
def laplacian_polynomial(key):
    graph = graph_by_key()[key]
    size = graph.num_verts()
    laplacian = laplacian_entries(graph)
    return determinant([
        [(_x if i == j else _R(0)) - laplacian[i][j] for j in range(size)]
        for i in range(size)
    ])


@lru_cache(maxsize=None)
def polynomial_classes():
    classes = defaultdict(list)
    for key, _graph in connected_graphs():
        classes[str(laplacian_polynomial(key))].append(key)
    return dict(classes)


def english_list(items):
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return "%s and %s" % (items[0], items[1])
    return "%s, and %s" % (", ".join(items[:-1]), items[-1])


def entry_comment(key):
    sentences = []
    if key in NAMES:
        sentences.append("This is the %s." % NAMES[key])

    mates = [
        other for other in polynomial_classes()[str(laplacian_polynomial(key))]
        if other != key
    ]
    if mates:
        sentences.append(
            "It has the same Laplacian polynomial as %s."
            % english_list(mates)
        )

    return " ".join(sentences)


class LaplacianPolynomialsOfConnectedGraphs(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", T238)
    parameters = ("g",)
    type = "Z[]"
    rigour = "exact"

    def enumerate(self, max_vertices=MAX_VERTICES):
        for key, _graph in connected_graphs(max_vertices):
            yield {"g": key}

    def value(self, params, digits):
        key = params["g"]
        entry = {"number": laplacian_polynomial(key)}
        comment = entry_comment(key)
        if comment:
            entry["comment"] = comment
        return entry


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
    generator = LaplacianPolynomialsOfConnectedGraphs()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="Laplacian polynomials of connected graphs"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
