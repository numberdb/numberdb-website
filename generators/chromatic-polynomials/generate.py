"""Chromatic polynomials of connected graphs -- numberdb.org

    P(G, x) counts the proper colourings of G with x colours.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Graphs are named by their graph6 string after a canonical relabelling, so the
name depends on the graph rather than on how its vertices are numbered. The
generator enumerates with nauty rather than reading a stored list, so the
table can be reproduced from this file and nothing else.

Answers numberdb-data#97.
"""

import sys

import numberdb.sage as numberdb
from sage.graphs.graph_generators import graphs

#: Largest graph in the table.
#:
#: Seven leaves 996 graphs and the longest polynomial 62 characters, which is
#: nothing by the standards of this project -- the constraint here is the
#: count rather than the length, and 996 sits inside the thousand-entry
#: guidance. Eight vertices would be 11117 connected graphs.
MOST_VERTICES = 7

#: The graphs here with a name somebody would recognise: 35 of 996.
#:
#: Written out rather than looked up in Sage's catalogue at run time, so that
#: the table does not change when that catalogue does. Families first, since
#: a reader looking for the complete graph on five vertices wants to be told
#: that rather than that it is also something else.
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

class ChromaticPolynomials(numberdb.Generator):

    table = 'T125'
    parameters = ('g',)
    type = 'Z[]'

    #Exact: integer coefficients, counted by deletion and contraction.
    rigour = 'exact'

    def enumerate(self, most_vertices=MOST_VERTICES):
        for order in range(1, most_vertices + 1):
            for graph in graphs.nauty_geng('%d -c' % order):
                yield {'g': graph.canonical_label().graph6_string()}

    def value(self, params, digits):
        from sage.graphs.graph import Graph

        return Graph(str(params['g'])).chromatic_polynomial()

    #The names in NAMED are attached to their entries separately, by
    #`name_the_graphs.py` beside this file, because a generator produces
    #values and the package has no hook for anything else. Re-running this
    #does not disturb them -- checked, not assumed.


if __name__ == '__main__':
    generator = ChromaticPolynomials()

    if '--publish' in sys.argv:
        print(generator.publish(
            message='chromatic polynomials of every connected graph on at '
                    'most seven vertices'))
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
