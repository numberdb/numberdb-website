"""Poincaré polynomials of the finite Coxeter groups -- numberdb.org/T257

For a finite irreducible Coxeter group W, this stores the exact polynomial

    W(t) = sum_{w in W} t^length(w).

The entries are computed from the degrees of W as prod_i (1 + ... + t^(d_i-1)).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The range is A_n for 1 <= n <= 9, B_n for 2 <= n <= 9, D_n for
4 <= n <= 9, the exceptional finite Coxeter groups, and I_2(m) for
5 <= m <= 12 with m != 6.  The omitted I_2(3), I_2(4) and I_2(6) rows are
A_2, B_2 and G_2.
"""

import os
import sys
import urllib.request
from itertools import combinations

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


TABLE = "T257"
MAX_CLASSICAL_RANK = 9
MAX_DIHEDRAL_M = 12

_R = PolynomialRing(ZZ, "t")
_t = _R.gen()


EXCEPTIONAL_DEGREES = {
    "E6": (2, 5, 6, 8, 9, 12),
    "E7": (2, 6, 8, 10, 12, 14, 18),
    "E8": (2, 8, 12, 14, 18, 20, 24, 30),
    "F4": (2, 6, 8, 12),
    "G2": (2, 6),
    "H3": (2, 6, 10),
    "H4": (2, 12, 20, 30),
}

EXPECTED_ORDERS = {
    "E6": ZZ(51840),
    "E7": ZZ(2903040),
    "E8": ZZ(696729600),
    "F4": ZZ(1152),
    "G2": ZZ(12),
    "H3": ZZ(120),
    "H4": ZZ(14400),
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def type_names():
    for n in range(1, MAX_CLASSICAL_RANK + 1):
        yield "A%d" % n
    for n in range(2, MAX_CLASSICAL_RANK + 1):
        yield "B%d" % n
    for n in range(4, MAX_CLASSICAL_RANK + 1):
        yield "D%d" % n
    for name in ("E6", "E7", "E8", "F4", "G2", "H3", "H4"):
        yield name
    for m in range(5, MAX_DIHEDRAL_M + 1):
        if m != 6:
            yield "I2(%d)" % m


def degrees(type_name):
    family, parameter = parse_type(type_name)
    if family == "A":
        return tuple(range(2, parameter + 2))
    if family == "B":
        return tuple(2 * i for i in range(1, parameter + 1))
    if family == "D":
        return tuple(sorted(list(range(2, 2 * parameter - 1, 2)) + [parameter]))
    if family == "I":
        return (2, parameter)
    try:
        return EXCEPTIONAL_DEGREES[type_name]
    except KeyError:
        raise ValueError("unknown Coxeter type %r" % (type_name,))


def parse_type(type_name):
    if type_name.startswith("I2(") and type_name.endswith(")"):
        return "I", int(type_name[3:-1])
    family = type_name[0]
    if family in "ABD":
        return family, int(type_name[1:])
    return type_name, None


def poincare_from_degrees(degree_list):
    polynomial = _R.one()
    for degree in degree_list:
        factor = _R.zero()
        for k in range(degree):
            factor += _t ** k
        polynomial *= factor
    return polynomial


def poincare_polynomial(type_name):
    return poincare_from_degrees(degrees(type_name))


def diagram(type_name):
    family, parameter = parse_type(type_name)
    if family == "A":
        return chain(parameter, [3] * (parameter - 1))
    if family == "B":
        return chain(parameter, [4] + [3] * (parameter - 2))
    if family == "D":
        return armed_tree((1, 1, parameter - 3))
    if family == "I":
        return 2, [(0, 1, parameter)]
    if type_name == "E6":
        return armed_tree((1, 2, 2))
    if type_name == "E7":
        return armed_tree((1, 2, 3))
    if type_name == "E8":
        return armed_tree((1, 2, 4))
    if type_name == "F4":
        return chain(4, [3, 4, 3])
    if type_name == "G2":
        return 2, [(0, 1, 6)]
    if type_name == "H3":
        return chain(3, [5, 3])
    if type_name == "H4":
        return chain(4, [5, 3, 3])
    raise ValueError("unknown Coxeter type %r" % (type_name,))


def chain(rank, labels):
    if rank == 1:
        return 1, []
    if len(labels) != rank - 1:
        raise ValueError("rank %d chain needs %d labels" % (rank, rank - 1))
    return rank, [(i, i + 1, labels[i]) for i in range(rank - 1)]


def armed_tree(arms):
    edges = []
    next_node = 1
    for length in arms:
        previous = 0
        for _ in range(length):
            current = next_node
            next_node += 1
            edges.append((previous, current, 3))
            previous = current
    return next_node, edges


def connected_components(vertices, edges):
    vertices = set(vertices)
    neighbours = {vertex: set() for vertex in vertices}
    edge_labels = {}
    for a, b, label in edges:
        if a in vertices and b in vertices:
            neighbours[a].add(b)
            neighbours[b].add(a)
            edge_labels[frozenset((a, b))] = label

    components = []
    while vertices:
        start = vertices.pop()
        stack = [start]
        component = {start}
        while stack:
            vertex = stack.pop()
            for neighbour in neighbours[vertex]:
                if neighbour in component:
                    continue
                component.add(neighbour)
                vertices.discard(neighbour)
                stack.append(neighbour)
        component_edges = []
        for pair, label in edge_labels.items():
            a, b = tuple(pair)
            if a in component and b in component:
                component_edges.append((a, b, label))
        components.append((component, component_edges))
    return components


def component_degrees(component, component_edges):
    rank = len(component)
    if rank == 1:
        return (2,)

    labels = [label for _, _, label in component_edges]
    if len(component_edges) != rank - 1:
        raise ValueError("component is not a tree: %r" % (component_edges,))

    degree_by_vertex = {vertex: 0 for vertex in component}
    neighbours = {vertex: [] for vertex in component}
    for a, b, label in component_edges:
        degree_by_vertex[a] += 1
        degree_by_vertex[b] += 1
        neighbours[a].append((b, label))
        neighbours[b].append((a, label))

    if rank == 2:
        return (2, labels[0])

    if max(degree_by_vertex.values()) <= 2:
        path_labels = labels_along_path(component, neighbours)
        if all(label == 3 for label in path_labels):
            return tuple(range(2, rank + 2))
        if path_labels.count(4) == 1 and path_labels[0] == 4 and all(
                label == 3 for label in path_labels[1:]):
            return tuple(2 * i for i in range(1, rank + 1))
        if path_labels.count(4) == 1 and path_labels[-1] == 4 and all(
                label == 3 for label in path_labels[:-1]):
            return tuple(2 * i for i in range(1, rank + 1))
        if rank == 4 and path_labels == [3, 4, 3]:
            return EXCEPTIONAL_DEGREES["F4"]
        if rank == 3 and path_labels == [5, 3]:
            return EXCEPTIONAL_DEGREES["H3"]
        if rank == 3 and path_labels == [3, 5]:
            return EXCEPTIONAL_DEGREES["H3"]
        if rank == 4 and (path_labels == [5, 3, 3]
                          or path_labels == [3, 3, 5]):
            return EXCEPTIONAL_DEGREES["H4"]

    if all(label == 3 for label in labels) and max(degree_by_vertex.values()) == 3:
        arms = sorted(arm_lengths(component, neighbours))
        if arms[0:2] == [1, 1]:
            return tuple(sorted(list(range(2, 2 * rank - 1, 2)) + [rank]))
        if arms == [1, 2, 2]:
            return EXCEPTIONAL_DEGREES["E6"]
        if arms == [1, 2, 3]:
            return EXCEPTIONAL_DEGREES["E7"]
        if arms == [1, 2, 4]:
            return EXCEPTIONAL_DEGREES["E8"]

    raise ValueError("cannot classify parabolic component with edges %r"
                     % (component_edges,))


def labels_along_path(component, neighbours):
    endpoints = [vertex for vertex in component if len(neighbours[vertex]) == 1]
    if len(endpoints) != 2:
        raise ValueError("not a path")
    labels = []
    previous = None
    current = endpoints[0]
    while current != endpoints[1]:
        choices = [(vertex, label) for vertex, label in neighbours[current]
                   if vertex != previous]
        if len(choices) != 1:
            raise ValueError("path is ambiguous")
        previous, (current, label) = current, choices[0]
        labels.append(label)
    return labels


def arm_lengths(component, neighbours):
    centers = [vertex for vertex in component if len(neighbours[vertex]) == 3]
    if len(centers) != 1:
        raise ValueError("not a three-armed tree")
    center = centers[0]
    lengths = []
    for start, _label in neighbours[center]:
        length = 1
        previous = center
        current = start
        while len(neighbours[current]) != 1:
            choices = [(vertex, label) for vertex, label in neighbours[current]
                       if vertex != previous]
            if len(choices) != 1:
                raise ValueError("arm is ambiguous")
            previous, (current, _label) = current, choices[0]
            length += 1
        lengths.append(length)
    return lengths


def parabolic_polynomial(vertices, edges, subset):
    polynomial = _R.one()
    for component, component_edges in connected_components(subset, edges):
        polynomial *= poincare_from_degrees(
            component_degrees(component, component_edges))
    return polynomial


def solomon_identity_holds(type_name):
    rank, edges = diagram(type_name)
    vertices = tuple(range(rank))
    full = poincare_polynomial(type_name)
    total = _R.zero()
    for size in range(rank + 1):
        sign = ZZ(1) if size % 2 == 0 else ZZ(-1)
        for subset in combinations(vertices, size):
            parabolic = parabolic_polynomial(vertices, edges, set(subset))
            quotient, remainder = full.quo_rem(parabolic)
            if remainder != 0:
                raise ArithmeticError("%s parabolic %s did not divide"
                                      % (type_name, subset))
            total += sign * quotient
    return total == _t ** full.degree()


def mahonian_rows_from_oeis(up_to_n):
    url = "https://oeis.org/A008302/b008302.txt"
    request = urllib.request.Request(
        url, headers={"User-Agent": "numberdb-coxeter-poincare-check"})
    with urllib.request.urlopen(request, timeout=60) as answer:
        terms = [int(line.decode("ascii").split()[1])
                 for line in answer
                 if line.strip() and not line.startswith(b"#")]

    rows = {}
    offset = 0
    for n in range(up_to_n + 1):
        width = n * (n + 1) // 2 + 1
        rows[n] = terms[offset:offset + width]
        if len(rows[n]) != width:
            raise ValueError("OEIS A008302 ended before row %d" % n)
        offset += width
    return rows


def coefficients(poly):
    return [ZZ(poly[i]) for i in range(poly.degree() + 1)]


def self_check():
    checked = 0
    oeis_rows = mahonian_rows_from_oeis(MAX_CLASSICAL_RANK)
    for type_name in type_names():
        poly = poincare_polynomial(type_name)
        degree_sum = sum(degree - 1 for degree in degrees(type_name))
        if poly.degree() != degree_sum:
            raise AssertionError("%s has degree %s, expected %s"
                                 % (type_name, poly.degree(), degree_sum))
        if _t ** poly.degree() * poly(ZZ(1) / _t) != poly:
            raise AssertionError("%s is not palindromic" % type_name)
        order = poly(1)
        product = ZZ(1)
        for degree in degrees(type_name):
            product *= ZZ(degree)
        if order != product:
            raise AssertionError("%s evaluates to %s, not %s"
                                 % (type_name, order, product))
        if type_name in EXPECTED_ORDERS and order != EXPECTED_ORDERS[type_name]:
            raise AssertionError("%s order %s does not match expected %s"
                                 % (type_name, order, EXPECTED_ORDERS[type_name]))
        if not solomon_identity_holds(type_name):
            raise AssertionError("Solomon identity failed for %s" % type_name)
        family, parameter = parse_type(type_name)
        if family == "A":
            if coefficients(poly) != [ZZ(c) for c in oeis_rows[parameter]]:
                raise AssertionError("%s does not match OEIS A008302 row %d"
                                     % (type_name, parameter))
        checked += 1
    print("checked %d Coxeter types" % checked)


class FiniteCoxeterPoincarePolynomials(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", TABLE)
    parameters = ("type",)
    type = "Z[]"
    rigour = "exact"

    def enumerate(self):
        for type_name in type_names():
            yield {"type": type_name}

    def value(self, params, digits):
        return poincare_polynomial(params["type"])


if __name__ == "__main__":
    _key_from_stdin()
    if os.environ.get("NUMBERDB_SELF_CHECK") == "1":
        self_check()
        sys.exit(0)

    generator = FiniteCoxeterPoincarePolynomials()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="finite Coxeter group Poincare polynomials"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
