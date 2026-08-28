"""Tutte polynomials of connected graphs -- numberdb.org

    T(G; x, y) = sum over edge subsets of (x-1)^(r(E)-r(A)) (y-1)^(|A|-r(A))

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Graphs are named by their graph6 string after a canonical relabelling. The
generator enumerates with nauty rather than reading a stored list, so the
table can be reproduced from this file and nothing else.

Answers numberdb-data#96.
"""

import sys

import numberdb.sage as numberdb
from sage.graphs.graph_generators import graphs

#: Largest graph in the table.
#:
#: Seven leaves 996 graphs and the longest polynomial 447 characters. Eight
#: vertices would be 11117 graphs, past the entry guidance, and slower: these
#: take about twelve seconds to compute at seven and grow steeply.
MOST_VERTICES = 7

#: The graphs here with a name somebody would recognise: 35 of 996. Attached
#: to their entries by `name_the_graphs.py` beside the chromatic generator,
#: since the package has no hook for anything but the value. Re-running this
#: does not disturb them -- checked, not assumed.
NAMED = {
    '@': 'complete graph $K_1$',
    'A_': 'complete graph $K_2$',
    'BW': 'path $P_3$',
    'Bw': 'complete graph $K_3$',
    'CF': 'star $K_{1,3}$',
    'CL': 'path $P_4$',
    'C]': 'cycle $C_4$',
    'C^': 'diamond graph',
    'C~': 'complete graph $K_4$',
    'D?{': 'star $K_{1,4}$',
    'DBg': 'path $P_5$',
    'DBk': 'bull graph',
    'DB{': 'dart graph',
    'DFw': 'complete bipartite graph $K_{2,3}$',
    'DK{': 'butterfly graph',
    'DLo': 'cycle $C_5$',
    'DN{': 'house X graph',
    'D]{': 'wheel $W_4$',
    'Dbk': 'house graph',
    'D~{': 'complete graph $K_5$',
    'E?Bw': 'star $K_{1,5}$',
    'E?~o': 'complete bipartite graph $K_{2,4}$',
    'E@YO': 'path $P_6$',
    'EFz_': 'complete bipartite graph $K_{3,3}$',
    'EIe_': 'cycle $C_6$',
    'ELrw': 'wheel $W_5$',
    'E~~w': 'complete graph $K_6$',
    'F??Fw': 'star $K_{1,6}$',
    'F?B~o': 'complete bipartite graph $K_{2,5}$',
    'F?~v_': 'complete bipartite graph $K_{3,4}$',
    'F@HSO': 'path $P_7$',
    'FHQSO': 'cycle $C_7$',
    'FIefw': 'wheel $W_6$',
    'FjaHw': 'Moser spindle',
    'F~~~w': 'complete graph $K_7$',
}


class TuttePolynomials(numberdb.Generator):

    table = 'T126'
    parameters = ('g',)
    type = 'Z[]'

    #Exact: integer coefficients, by deletion and contraction.
    rigour = 'exact'

    def enumerate(self, most_vertices=MOST_VERTICES):
        for order in range(1, most_vertices + 1):
            for graph in graphs.nauty_geng('%d -c' % order):
                yield {'g': graph.canonical_label().graph6_string()}

    def value(self, params, digits):
        from sage.graphs.graph import Graph

        return Graph(str(params['g'])).tutte_polynomial()


if __name__ == '__main__':
    generator = TuttePolynomials()

    if '--publish' in sys.argv:
        print(generator.publish(
            message='Tutte polynomials of every connected graph on at most '
                    'seven vertices'))
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
