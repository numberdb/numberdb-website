"""Characteristic polynomials of connected graphs -- numberdb.org/T237

    phi(G, x) = det(xI - A(G)),

where A(G) is the adjacency matrix of the simple connected graph G. Graphs are
named by their graph6 string after canonical relabelling, matching the
chromatic and Tutte graph-polynomial tables.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The sign convention is det(xI - A), so the polynomial is monic. MathWorld's
worked examples use det(A - xI), which differs by (-1)^|V(G)|.

The generator computes every connected graph on at most seven vertices,
the same finite index used by T125 and T126. It also attaches the 35 common
graph names those tables use, and names connected cospectral mates in entry
comments.

Answers numberdb-data#67, for characteristic polynomials of natural small
matrices.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.graphs.graph import Graph
from sage.graphs.graph_generators import graphs
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.integer_ring import ZZ


#: Largest graph in the table.
#:
#: Seven vertices gives 996 connected graphs, matching T125 and T126. The
#: measured longest entry is 51 characters, so the count is the constraint:
#: eight vertices would already be 11117 connected graphs.
MOST_VERTICES = 7

R = PolynomialRing(ZZ, "x")
x = R.gen()

#: The graph names already used by the chromatic and Tutte polynomial tables.
NAMED = {
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
    "D]{": "wheel $W_4$",
    "Dbk": "house graph",
    "D~{": "complete graph $K_5$",
    "E?Bw": "star $K_{1,5}$",
    "E?~o": "complete bipartite graph $K_{2,4}$",
    "E@YO": "path $P_6$",
    "EFz_": "complete bipartite graph $K_{3,3}$",
    "EIe_": "cycle $C_6$",
    "ELrw": "wheel $W_5$",
    "E~~w": "complete graph $K_6$",
    "F??Fw": "star $K_{1,6}$",
    "F?B~o": "complete bipartite graph $K_{2,5}$",
    "F?~v_": "complete bipartite graph $K_{3,4}$",
    "F@HSO": "path $P_7$",
    "FHQSO": "cycle $C_7$",
    "FIefw": "wheel $W_6$",
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


def connected_graphs(most_vertices=MOST_VERTICES):
    """Canonical connected graphs in the order the table displays them."""
    for order in range(1, most_vertices + 1):
        for graph in graphs.nauty_geng("%d -c" % order):
            yield graph.canonical_label()


def characteristic_polynomial(graph):
    """The monic adjacency characteristic polynomial det(xI - A)."""
    return R(graph.adjacency_matrix().charpoly("x"))


def graph_key(graph):
    return graph.canonical_label().graph6_string()


def graph_from_key(key):
    return Graph(str(key))


def _entry_ref(key):
    # HREF{} is delimited by braces; graph6 keys containing a closing brace
    # cannot be written there without changing the parser's grammar.
    if "}" in key:
        return "the graph with graph6 string `%s`" % key
    return "HREF{#%s}" % key


def _joined_refs(keys):
    refs = [_entry_ref(key) for key in keys]
    if len(refs) == 1:
        return refs[0]
    return ", ".join(refs[:-1]) + " and " + refs[-1]


class CharacteristicPolynomials(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE") or "T237"
    parameters = ("g",)
    type = "Z[]"
    rigour = "exact"

    #: Every polynomial, computed once, because comments name cospectral mates.
    _values = None

    def enumerate(self, most_vertices=MOST_VERTICES):
        for graph in connected_graphs(most_vertices):
            yield {"g": graph_key(graph)}

    def all_values(self):
        if self._values is None:
            values = {}
            for graph in connected_graphs():
                values[graph_key(graph)] = characteristic_polynomial(graph)
            self._values = values
        return self._values

    def value(self, params, digits):
        key = str(params["g"])
        values = self.all_values()
        if key in values:
            polynomial = values[key]
        else:
            polynomial = characteristic_polynomial(graph_from_key(key))

        parts = []
        if key in NAMED:
            parts.append("This is the %s." % NAMED[key])

        partners = [
            other for other, other_polynomial in values.items()
            if other != key and other_polynomial == polynomial
        ]
        if partners:
            parts.append("It is cospectral with %s." % _joined_refs(partners))

        if parts:
            return {"number": polynomial, "comment": " ".join(parts)}
        return polynomial


if __name__ == "__main__":
    _key_from_stdin()
    generator = CharacteristicPolynomials()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(generator.publish(
            message="characteristic polynomials of connected graphs",
            assisted_by=os.environ.get("NUMBERDB_ASSISTED_BY", "codex")))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
