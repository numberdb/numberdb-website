"""Matching-generating polynomials of connected graphs -- numberdb.org/T248

For every connected simple graph G on at most seven vertices, named by its
canonical graph6 string, this stores

    M(G, x) = sum_k m_k x^k,

where m_k is the number of k-edge matchings of G.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The generator counts matchings directly from edge subsets. This keeps the
arithmetic in ZZ and records the matching counts in their ordinary generating
polynomial.
"""

import os
import sys
from functools import lru_cache
from itertools import combinations

import numberdb.sage as numberdb
from sage.graphs.graph import Graph
from sage.graphs.graph_generators import graphs
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


T248 = "T248"
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
    "DBg": "path $P_5$",
    "DBk": "bull graph",
    "DB{": "dart graph",
    "DFw": "complete bipartite graph $K_{2,3}$",
    "DK{": "butterfly graph",
    "DLo": "cycle $C_5$",
    "DN{": "house X graph",
    "D]{": "wheel $W_5$",
    "Dbk": "house graph",
    "D~{": "complete graph $K_5$",
    "E?Bw": "star $K_{1,5}$",
    "E?~o": "complete bipartite graph $K_{2,4}$",
    "E@YO": "path $P_6$",
    "EFz_": "complete bipartite graph $K_{3,3}$",
    "EIe_": "cycle $C_6$",
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
        for graph in graphs.nauty_geng("%d -c" % n):
            canonical = graph.canonical_label(algorithm="sage")
            out.append((canonical.graph6_string(), canonical))
    return tuple(out)


@lru_cache(maxsize=None)
def graph_by_key(max_vertices=MAX_VERTICES):
    return {key: graph for key, graph in connected_graphs(max_vertices)}


def graph_from_key(key):
    return Graph(str(key))


@lru_cache(maxsize=None)
def matching_counts(key):
    graph = graph_by_key().get(key)
    if graph is None:
        graph = graph_from_key(key)
    edges = list(graph.edges(labels=False))
    limit = graph.num_verts() // 2
    counts = [ZZ(0)] * (limit + 1)
    counts[0] = ZZ(1)
    for size in range(1, limit + 1):
        total = ZZ(0)
        for chosen in combinations(edges, size):
            used = []
            for edge in chosen:
                used.extend(edge)
            if len(set(used)) == 2 * size:
                total += 1
        counts[size] = total
    return tuple(counts)


@lru_cache(maxsize=None)
def matching_generating_polynomial(key):
    return sum(
        _R(count) * _x ** k for k, count in enumerate(matching_counts(key))
    )


def entry_comment(key):
    if key in NAMES:
        return "This is the %s." % NAMES[key]
    return ""


class MatchingGeneratingPolynomialsOfConnectedGraphs(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", T248)
    parameters = ("g",)
    type = "Z[]"
    rigour = "exact"

    def enumerate(self, max_vertices=MAX_VERTICES):
        for key, _graph in connected_graphs(max_vertices):
            yield {"g": key}

    def value(self, params, digits):
        del digits
        key = params["g"]
        entry = {"number": matching_generating_polynomial(key)}
        comment = entry_comment(key)
        if comment:
            entry["comment"] = comment
        return entry


if __name__ == "__main__":
    _key_from_stdin()
    generator = MatchingGeneratingPolynomialsOfConnectedGraphs()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="matching-generating polynomials of connected graphs",
            assisted_by=os.environ.get("NUMBERDB_ASSISTED_BY", "")))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
