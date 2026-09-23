"""Growth constants of the classes of trees -- numberdb.org/T448

The table stores growth constants for standard classes of trees, following the
shared convention of numberdb-data issue #203: ordinary generating functions
for unlabelled classes, exponential generating functions for labelled classes,
and the size parameter recorded as nodes.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.real_arb import RealBallField


DIGITS = 50
WORKING_GUARD = 80

OTTER = "2.9557652856519949747148175241231945883754923046636"
IDENTITY = "2.5175403526320038907953545984634472773359812668031"
SERIES_REDUCED = "2.1894619856608505638870275771145449673317087442385"
WEAKLY_BINARY = "2.4832535361726368585622885181782212891886973408144"
ROOTED_TERNARY = "2.8154600331761507465266167782426995425365065396907"


ROWS = [
    {
        "class": "rooted",
        "size": "nodes",
        "labelling": "unlabelled",
        "number": OTTER,
        "comment": "Otter's constant for unlabelled rooted trees CITE{OEISOtter}.",
    },
    {
        "class": "free",
        "size": "nodes",
        "labelling": "unlabelled",
        "number": OTTER,
        "comment": "The same growth constant as for rooted trees, with exponent $5/2$ rather than $3/2$ in the subexponential factor CITE{OEISOtter}.",
    },
    {
        "class": "planted",
        "size": "nodes",
        "labelling": "unlabelled",
        "number": OTTER,
        "comment": "Planted trees differ from rooted trees by the planted root convention, and have the same exponential growth constant.",
    },
    {
        "class": "identity-rooted",
        "size": "nodes",
        "labelling": "unlabelled",
        "number": IDENTITY,
        "comment": "Rooted identity trees have trivial automorphism group CITE{OEISIdentityRooted}.",
    },
    {
        "class": "identity-free",
        "size": "nodes",
        "labelling": "unlabelled",
        "number": IDENTITY,
        "comment": "Free identity trees are asymmetric unlabelled trees CITE{OEISIdentityFree}.",
    },
    {
        "class": "series-reduced-planted",
        "size": "nodes",
        "labelling": "unlabelled",
        "number": SERIES_REDUCED,
        "comment": "Series-reduced planted trees have no non-root vertex of degree $2$ CITE{OEISSeriesPlanted}.",
    },
    {
        "class": "series-reduced-rooted",
        "size": "nodes",
        "labelling": "unlabelled",
        "number": SERIES_REDUCED,
        "comment": "Series-reduced rooted trees are also called homeomorphically irreducible rooted trees CITE{OEISSeriesRooted}.",
    },
    {
        "class": "series-reduced-free",
        "size": "nodes",
        "labelling": "unlabelled",
        "number": SERIES_REDUCED,
        "comment": "Series-reduced free trees are homeomorphically irreducible free trees CITE{OEISSeriesFree}.",
    },
    {
        "class": "degree-bounded-2",
        "size": "nodes",
        "labelling": "unlabelled",
        "number": WEAKLY_BINARY,
        "comment": "Children are unordered and every vertex has outdegree at most $2$ CITE{OEISWeaklyBinary}.",
    },
    {
        "class": "degree-bounded-3",
        "size": "nodes",
        "labelling": "unlabelled",
        "number": ROOTED_TERNARY,
        "comment": "Children are unordered and every vertex has outdegree at most $3$ CITE{OEISTernary}.",
    },
    {
        "class": "plane",
        "size": "nodes",
        "labelling": "unlabelled",
        "number": ZZ(4),
        "comment": "The row is exact: rooted plane trees with $n$ nodes are counted by $C_{n-1}$ CITE{OEISCatalan}.",
    },
    {
        "class": "plane-binary",
        "size": "nodes",
        "labelling": "unlabelled",
        "number": ZZ(3),
        "comment": "The row is exact: rooted plane trees with outdegree at most $2$ are counted by Motzkin numbers shifted by one node CITE{OEISMotzkin}.",
    },
    {
        "class": "labelled-rooted",
        "size": "nodes",
        "labelling": "labelled",
        "number": "e",
        "comment": "Exactly HREF{E}[$e$], by Cayley's formula $n^{n-1}$ CITE{WikiCayley}.",
    },
    {
        "class": "labelled-free",
        "size": "nodes",
        "labelling": "labelled",
        "number": "e",
        "comment": "Exactly HREF{E}[$e$], by Cayley's formula $n^{n-2}$ CITE{WikiCayley}.",
    },
]


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


class TreeGrowthConstants(numberdb.Generator):
    table = os.environ.get("NUMBERDB_TABLE") or "T448"
    parameters = ("class", "size", "labelling")
    type = "R"
    digits = DIGITS
    rigour = "heuristic (agreement-checked)"

    def enumerate(self):
        for row in ROWS:
            yield {
                "class": row["class"],
                "size": row["size"],
                "labelling": row["labelling"],
            }

    def value(self, params, digits):
        for row in ROWS:
            if all(str(params[key]) == row[key] for key in self.parameters):
                number = row["number"]
                if number == "e":
                    field = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
                    number = field(1).exp()
                return {"number": number, "comment": row["comment"]}
        raise KeyError("unknown tree-growth row %r" % (params,))


if __name__ == "__main__":
    _key_from_stdin()
    generator = TreeGrowthConstants()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(generator.publish(message="growth constants for tree classes"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
