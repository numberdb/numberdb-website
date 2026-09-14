"""Independence polynomials of trees -- numberdb.org/T240

For every tree T on at most twelve vertices, named by its canonical graph6
string, this stores

    I(T, x) = sum_k s_k x^k,

where s_k is the number of independent vertex sets of T with k vertices.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The generator computes the coefficients directly from vertex subsets. The
largest tree has twelve vertices, so this is small enough to be clear and gives
an independent comparison point against Sage's clique polynomial of the
complement.
"""

import os
import sys
from collections import defaultdict
from functools import lru_cache
from itertools import combinations

import numberdb.sage as numberdb
from sage.graphs.graph import Graph
from sage.graphs.graph_generators import graphs
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


T240 = "T240"
MAX_VERTICES = 12
TREE_COUNTS = {
    1: 1,
    2: 1,
    3: 1,
    4: 2,
    5: 3,
    6: 6,
    7: 11,
    8: 23,
    9: 47,
    10: 106,
    11: 235,
    12: 551,
}

_R = PolynomialRing(ZZ, "x")
_x = _R.gen()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def canonical_key(graph):
    return graph.canonical_label(algorithm="sage").graph6_string()


@lru_cache(maxsize=None)
def tree_graphs(max_vertices=MAX_VERTICES):
    out = []
    counts = {}
    for n in range(1, max_vertices + 1):
        spec = "%d %d:%d -c" % (n, n - 1, n - 1)
        rows = []
        for graph in graphs.nauty_geng(spec):
            canonical = graph.canonical_label(algorithm="sage")
            if not canonical.is_tree():
                raise ArithmeticError("non-tree from nauty spec %s" % spec)
            rows.append((canonical.graph6_string(), canonical))
        rows.sort(key=lambda item: item[0])
        counts[n] = len(rows)
        out.extend(rows)
    expected = {
        n: count for n, count in TREE_COUNTS.items()
        if n <= max_vertices
    }
    if counts != expected:
        raise ArithmeticError("tree counts %s, expected %s" % (counts, expected))
    return tuple(out)


@lru_cache(maxsize=None)
def graph_by_key(max_vertices=MAX_VERTICES):
    return {key: graph for key, graph in tree_graphs(max_vertices)}


def graph_from_key(key):
    graph = graph_by_key().get(str(key))
    if graph is not None:
        return graph
    return Graph(str(key))


def independent_counts(graph):
    vertices = sorted(graph.vertices())
    counts = [ZZ(0)] * (len(vertices) + 1)
    counts[0] = ZZ(1)
    for size in range(1, len(vertices) + 1):
        total = ZZ(0)
        for subset in combinations(vertices, size):
            if graph.subgraph(subset).num_edges() == 0:
                total += 1
        counts[size] = total
    while counts and counts[-1] == 0:
        counts.pop()
    return tuple(counts)


@lru_cache(maxsize=None)
def independence_polynomial(key):
    counts = independent_counts(graph_from_key(key))
    return sum(_R(count) * _x ** exponent for exponent, count in enumerate(counts))


@lru_cache(maxsize=None)
def polynomial_classes():
    classes = defaultdict(list)
    for key, _graph in tree_graphs():
        classes[str(independence_polynomial(key))].append(key)
    return dict(classes)


def english_list(items):
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return "%s and %s" % (items[0], items[1])
    return "%s, and %s" % (", ".join(items[:-1]), items[-1])


def tree_name(graph):
    n = graph.num_verts()
    degrees = sorted(graph.degree(), reverse=True)
    if n == 1:
        return "path $P_1$"
    if degrees[0] <= 2:
        return "path $P_%d$" % n
    if degrees[0] == n - 1:
        return "star $K_{1,%d}$" % (n - 1)
    return ""


def entry_comment(key):
    graph = graph_from_key(key)
    sentences = []
    name = tree_name(graph)
    if name:
        sentences.append("This is the %s." % name)

    mates = [
        other for other in polynomial_classes()[str(independence_polynomial(key))]
        if other != key
    ]
    if mates:
        labels = ["`%s`" % other for other in mates]
        sentences.append(
            "It has the same independence polynomial as %s."
            % english_list(labels)
        )
    return " ".join(sentences)


class IndependencePolynomialsOfTrees(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", T240)
    parameters = ("g",)
    type = "Z[]"
    rigour = "exact"

    def enumerate(self, max_vertices=MAX_VERTICES):
        for key, _graph in tree_graphs(max_vertices):
            yield {"g": key}

    def value(self, params, digits):
        key = params["g"]
        entry = {"number": independence_polynomial(key)}
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
    generator = IndependencePolynomialsOfTrees()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="independence polynomials of trees"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
