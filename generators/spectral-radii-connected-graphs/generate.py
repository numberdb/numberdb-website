"""Spectral radii of connected graphs -- numberdb.org/T397

For every connected simple graph G on at most seven vertices, named by its
canonical graph6 string, this stores the largest eigenvalue lambda_1(G) of
the 0-1 adjacency matrix A(G).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The generator computes the exact characteristic polynomial over ZZ, isolates
its roots in AA, and converts the largest root to a real interval before
storing it. Rational Perron roots are returned exactly.
"""

import os
import sys
from functools import lru_cache

import numberdb.sage as numberdb
from sage.graphs.graph import Graph
from sage.graphs.graph_generators import graphs
from sage.rings.qqbar import AA
from sage.rings.rational_field import QQ
from sage.rings.real_mpfi import RealIntervalField


T397 = "T397"
MAX_VERTICES = 7
WORKING_GUARD = 64

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


def generated_keys():
    return [key for key, _graph in connected_graphs()]


def assert_t237_keys():
    expected = list(numberdb.table("T237")["Numbers"])
    actual = generated_keys()
    if actual != expected:
        raise RuntimeError(
            "generated graph keys do not match T237: %d generated, %d stored"
            % (len(actual), len(expected))
        )


@lru_cache(maxsize=None)
def characteristic_polynomial(key):
    graph = graph_by_key().get(key)
    if graph is None:
        graph = graph_from_key(key).canonical_label(algorithm="sage")
    return graph.adjacency_matrix().charpoly()


@lru_cache(maxsize=None)
def perron_root(key):
    graph = graph_by_key().get(key)
    order = graph.num_verts() if graph is not None else graph_from_key(key).num_verts()
    roots = characteristic_polynomial(key).roots(ring=AA)
    if sum(multiplicity for _root, multiplicity in roots) != order:
        raise ArithmeticError("the adjacency characteristic polynomial did not split over AA")
    return max(root for root, _multiplicity in roots)


def exact_rational(root):
    try:
        rational = QQ(root)
    except (TypeError, ValueError, ArithmeticError):
        return None
    if AA(rational) != root:
        return None
    return rational


def spectral_radius(key, digits):
    root = perron_root(key)
    rational = exact_rational(root)
    if rational is not None:
        return rational
    field = RealIntervalField(numberdb.bits(digits, losing=WORKING_GUARD))
    value = field(root)
    if value.lower() == value.upper():
        raise ArithmeticError("the certified interval has zero width")
    return value


def entry_comment(key):
    if key in NAMES:
        return "This is the %s." % NAMES[key]
    return ""


class SpectralRadiiOfConnectedGraphs(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", T397)
    parameters = ("g",)
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self, max_vertices=MAX_VERTICES):
        for key, _graph in connected_graphs(max_vertices):
            yield {"g": key}

    def value(self, params, digits):
        key = params["g"]
        entry = {"number": spectral_radius(key, digits)}
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

    assert_t237_keys()

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
    generator = SpectralRadiiOfConnectedGraphs()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="spectral radii of connected graphs"))
    else:
        assert_t237_keys()
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
