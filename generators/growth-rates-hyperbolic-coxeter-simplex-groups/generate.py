r"""Growth rates of hyperbolic Coxeter simplex groups -- numberdb.org/T223

This draft currently stores the compact rank-4 cases, the nine compact
hyperbolic Coxeter tetrahedral groups.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The growth series is computed exactly from Steinberg's formula

    1 / W(t^-1) = sum_{T finite} (-1)^|T| / W_T(t).

For each finite special subgroup, the growth polynomial W_T(t) is the product
of q-integers for the degrees of its finite Coxeter type. The growth rate is
the largest real root greater than 1 of the reciprocal of the reduced
denominator.
"""

import os
import sys
from functools import lru_cache
from itertools import combinations
from math import lcm

import numberdb.sage as numberdb
from sage.misc.latex import latex
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ
from sage.rings.real_mpfi import RealIntervalField


TABLE = "T223"
WORKING_GUARD = 128
CHECK_LENGTH = 9

R = PolynomialRing(QQ, "t")
t = R.gen()
X = PolynomialRing(QQ, "x")


DIAGRAMS = (
    {
        "diagram": "[5,3,4]",
        "witt": r"\overline{BH}_3",
        "edges": ((0, 1, 5), (1, 2, 3), (2, 3, 4)),
    },
    {
        "diagram": "[3,5,3]",
        "witt": r"\overline J_3",
        "edges": ((0, 1, 3), (1, 2, 5), (2, 3, 3)),
    },
    {
        "diagram": "[5,3^{1,1}]",
        "witt": r"\overline{DH}_3",
        "edges": ((0, 1, 5), (1, 2, 3), (1, 3, 3)),
    },
    {
        "diagram": "[(3,3,3,4)]",
        "witt": r"\widehat{AB}_3",
        "edges": ((0, 1, 4), (1, 2, 3), (2, 3, 3), (3, 0, 3)),
    },
    {
        "diagram": "[5,3,5]",
        "witt": r"\overline K_3",
        "edges": ((0, 1, 5), (1, 2, 3), (2, 3, 5)),
    },
    {
        "diagram": "[(3,3,3,5)]",
        "witt": r"\widehat{AH}_3",
        "edges": ((0, 1, 5), (1, 2, 3), (2, 3, 3), (3, 0, 3)),
    },
    {
        "diagram": "[(3,4,3,4)]",
        "witt": r"\widehat{BB}_3",
        "edges": ((0, 1, 4), (1, 2, 3), (2, 3, 4), (3, 0, 3)),
    },
    {
        "diagram": "[(3,4,3,5)]",
        "witt": r"\widehat{BH}_3",
        "edges": ((0, 1, 3), (1, 2, 4), (2, 3, 3), (3, 0, 5)),
    },
    {
        "diagram": "[(3,5,3,5)]",
        "witt": r"\widehat{HH}_3",
        "edges": ((0, 1, 5), (1, 2, 3), (2, 3, 5), (3, 0, 3)),
    },
)


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def q_integer(m):
    return sum(t ** k for k in range(m))


def diagram_record(key):
    for record in DIAGRAMS:
        if record["diagram"] == key:
            return record
    raise ValueError("unknown diagram %r" % key)


def coxeter_matrix(record):
    rank = 4
    matrix = [[1 if i == j else 2 for j in range(rank)] for i in range(rank)]
    for i, j, label in record["edges"]:
        matrix[i][j] = label
        matrix[j][i] = label
    return tuple(tuple(row) for row in matrix)


def all_subsets(rank):
    vertices = tuple(range(rank))
    for size in range(rank + 1):
        for subset in combinations(vertices, size):
            yield subset


def component_vertices(matrix, subset):
    remaining = set(subset)
    components = []
    while remaining:
        start = min(remaining)
        stack = [start]
        remaining.remove(start)
        component = {start}
        while stack:
            node = stack.pop()
            for other in list(remaining):
                if matrix[node][other] > 2:
                    remaining.remove(other)
                    component.add(other)
                    stack.append(other)
        components.append(tuple(sorted(component)))
    return components


def path_labels(matrix, component):
    if len(component) == 1:
        return []
    neighbours = {node: [] for node in component}
    for i, a in enumerate(component):
        for b in component[i + 1:]:
            if matrix[a][b] > 2:
                neighbours[a].append(b)
                neighbours[b].append(a)
    if any(len(neighbours[node]) > 2 for node in component):
        return None
    ends = [node for node in component if len(neighbours[node]) == 1]
    if len(ends) != 2:
        return None
    labels = []
    previous = None
    current = min(ends)
    while True:
        choices = [node for node in neighbours[current] if node != previous]
        if not choices:
            break
        following = choices[0]
        labels.append(matrix[current][following])
        previous, current = current, following
    return labels


def branch_arm_lengths(matrix, component):
    neighbours = {node: [] for node in component}
    for i, a in enumerate(component):
        for b in component[i + 1:]:
            if matrix[a][b] != 3:
                return None
            neighbours[a].append(b)
            neighbours[b].append(a)
    branch = [node for node in component if len(neighbours[node]) == 3]
    if len(branch) != 1:
        return None
    arms = []
    center = branch[0]
    for start in neighbours[center]:
        length = 1
        previous = center
        current = start
        while True:
            choices = [node for node in neighbours[current] if node != previous]
            if not choices:
                break
            if len(choices) > 1:
                return None
            previous, current = current, choices[0]
            length += 1
        arms.append(length)
    return sorted(arms)


def component_degrees(matrix, component):
    n = len(component)
    if n == 0:
        return []
    if n == 1:
        return [2]
    if n == 2:
        label = matrix[component[0]][component[1]]
        if label == 2:
            return [2, 2]
        return [2, label]

    labels = path_labels(matrix, component)
    if labels is not None:
        if labels == [3] * (n - 1):
            return list(range(2, n + 2))
        if labels.count(4) == 1 and labels.count(3) == n - 2:
            if labels[0] == 4 or labels[-1] == 4:
                return list(range(2, 2 * n + 1, 2))
        if n == 3 and sorted(labels) == [3, 5]:
            return [2, 6, 10]
        if n == 4 and (labels == [5, 3, 3] or labels == [3, 3, 5]):
            return [2, 12, 20, 30]
        if n == 4 and labels == [3, 4, 3]:
            return [2, 6, 8, 12]

    arms = branch_arm_lengths(matrix, component)
    if arms is not None:
        if arms[0:2] == [1, 1]:
            return list(range(2, 2 * n, 2)) + [n]
        if arms == [1, 2, 2]:
            return [2, 5, 6, 8, 9, 12]
        if arms == [1, 2, 3]:
            return [2, 6, 8, 10, 12, 14, 18]
        if arms == [1, 2, 4]:
            return [2, 8, 12, 14, 18, 20, 24, 30]

    raise ValueError("subdiagram %s is not a recognized finite type" % (component,))


def finite_degrees(matrix, subset):
    degrees = []
    for component in component_vertices(matrix, subset):
        degrees.extend(component_degrees(matrix, component))
    return degrees


def finite_growth_polynomial(matrix, subset):
    growth = R(1)
    for degree in finite_degrees(matrix, subset):
        growth *= q_integer(degree)
    return growth


@lru_cache(None)
def growth_rational(diagram):
    matrix = coxeter_matrix(diagram_record(diagram))
    rank = len(matrix)
    total = R(0)
    for subset in all_subsets(rank):
        try:
            finite_growth = finite_growth_polynomial(matrix, subset)
        except ValueError:
            continue
        sign = -1 if len(subset) % 2 else 1
        total += QQ(sign) / finite_growth
    return QQ(1) / total(t ** -1)


@lru_cache(None)
def growth_polynomial(diagram):
    denominator = R(growth_rational(diagram).denominator()).monic()
    degree = denominator.degree()
    reversed_denominator = sum(
        denominator[i] * t ** (degree - i) for i in range(degree + 1)
    )
    return R(reversed_denominator).monic()


def real_roots_greater_than_one(poly, bits):
    RIF = RealIntervalField(bits)
    roots = []
    for root, multiplicity in poly.roots(RIF):
        if root.upper() > 1 and root.lower() > 1:
            roots.append(root)
    roots.sort(key=lambda root: root.lower())
    return roots


@lru_cache(None)
def minimal_polynomial_text(diagram):
    poly = growth_polynomial(diagram)
    best = None
    for factor, multiplicity in poly.factor():
        roots = real_roots_greater_than_one(R(factor), 160)
        if not roots:
            continue
        candidate = (roots[-1].lower(), R(factor).monic())
        if best is None or candidate[0] > best[0]:
            best = candidate
    if best is None:
        raise ArithmeticError("no growth root found for %s" % (diagram,))
    return str(best[1])


@lru_cache(None)
def minimal_polynomial(diagram):
    return R(minimal_polynomial_text(diagram))


@lru_cache(None)
def minimal_polynomial_latex(diagram):
    poly = minimal_polynomial(diagram)
    display = X([poly[i] for i in range(poly.degree() + 1)])
    return latex(display)


def growth_rate(diagram, digits):
    poly = minimal_polynomial(diagram)
    if poly.degree() == 1:
        root = -poly[0] / poly[1]
        if root.denominator() == 1:
            return ZZ(root.numerator())
        return root
    bits = numberdb.bits(digits, losing=WORKING_GUARD)
    roots = real_roots_greater_than_one(poly, bits)
    if not roots:
        raise ArithmeticError("no real root greater than one for %s" % poly)
    return roots[-1]


def entry_comment(diagram):
    record = diagram_record(diagram)
    sentence = (
        r"$%s$, Witt symbol $%s$. The minimal polynomial of $\tau$ is $%s$."
        % (diagram, record["witt"], minimal_polynomial_latex(diagram))
    )
    if diagram == "[3,5,3]":
        sentence += (
            r" This is the unique minimum among cocompact hyperbolic Coxeter "
            r"groups in $\mathbb{H}^3$ CITE{Kellerhals}."
        )
    return sentence


def polynomial_coefficients(poly, n):
    return [poly[i] if i <= poly.degree() else QQ(0) for i in range(n + 1)]


def growth_coefficients(diagram, n):
    rational = growth_rational(diagram)
    numerator = R(rational.numerator())
    denominator = R(rational.denominator())
    if denominator[0] != 1:
        numerator = numerator / denominator[0]
        denominator = denominator / denominator[0]
    p_coeffs = polynomial_coefficients(numerator, n)
    q_coeffs = polynomial_coefficients(denominator, min(n, denominator.degree()))
    coefficients = []
    for k in range(n + 1):
        total = p_coeffs[k]
        for i in range(1, min(k, denominator.degree()) + 1):
            total -= q_coeffs[i] * coefficients[k - i]
        if total.denominator() != 1:
            raise ArithmeticError("nonintegral coefficient %s at %d" % (total, k))
        coefficients.append(int(total))
    return coefficients


def matrix_multiply(a, b):
    rank = len(a)
    return tuple(
        tuple(sum(a[i][k] * b[k][j] for k in range(rank)) for j in range(rank))
        for i in range(rank)
    )


def matrix_power(a, exponent):
    rank = len(a)
    out = tuple(
        tuple(QQ(1) if i == j else QQ(0) for j in range(rank))
        for i in range(rank)
    )
    for _ in range(exponent):
        out = matrix_multiply(out, a)
    return out


def tits_generators(diagram):
    from sage.rings.number_field.number_field import CyclotomicField

    matrix = coxeter_matrix(diagram_record(diagram))
    finite = [matrix[i][j] for i in range(len(matrix)) for j in range(i + 1, len(matrix))
              if matrix[i][j] is not None]
    order = 1
    for m in finite:
        order = lcm(order, 2 * m)
    K = QQ if order == 1 else CyclotomicField(order)
    zeta = None if order == 1 else K.gen()

    def cosine(m):
        power = order // (2 * m)
        return (zeta ** power + zeta ** (-power)) / K(2)

    cosines = {}
    for i in range(len(matrix)):
        for j in range(len(matrix)):
            if i == j:
                continue
            cosines[(i, j)] = K(0) if matrix[i][j] == 2 else cosine(matrix[i][j])

    generators = []
    for i in range(len(matrix)):
        row_data = [[K(1) if row == col else K(0) for col in range(len(matrix))]
                    for row in range(len(matrix))]
        for col in range(len(matrix)):
            if col == i:
                row_data[i][col] = K(-1)
            else:
                row_data[i][col] = K(2) * cosines[(i, col)]
        generators.append(tuple(tuple(row) for row in row_data))
    return generators


def bfs_counts(diagram, length):
    rank = 4
    identity = tuple(
        tuple(QQ(1) if row == col else QQ(0) for col in range(rank))
        for row in range(rank)
    )
    generators = tits_generators(diagram)
    seen = {identity}
    frontier = {identity}
    counts = [1]
    for step in range(1, length + 1):
        next_frontier = set()
        for element in frontier:
            for generator in generators:
                candidate = matrix_multiply(element, generator)
                if candidate not in seen:
                    seen.add(candidate)
                    next_frontier.add(candidate)
        counts.append(len(next_frontier))
        frontier = next_frontier
    return counts


def check_tits_relations(diagram):
    matrix = coxeter_matrix(diagram_record(diagram))
    generators = tits_generators(diagram)
    identity = tuple(
        tuple(QQ(1) if row == col else QQ(0) for col in range(len(matrix)))
        for row in range(len(matrix))
    )
    for i in range(len(matrix)):
        if matrix_multiply(generators[i], generators[i]) != identity:
            raise ArithmeticError("%s: generator %d is not an involution" % (diagram, i))
    for i in range(len(matrix)):
        for j in range(i + 1, len(matrix)):
            product = matrix_multiply(generators[i], generators[j])
            if matrix_power(product, matrix[i][j]) != identity:
                raise ArithmeticError(
                    "%s: generators %d,%d do not have order %d"
                    % (diagram, i, j, matrix[i][j])
                )


def check_identities():
    controls = {
        "[3,5,3]": "t^10 - t^9 - t^6 + t^5 - t^4 - t + 1",
    }
    for diagram, expected in controls.items():
        got = minimal_polynomial(diagram)
        if got != R(expected):
            raise ArithmeticError("%s polynomial %s, expected %s" % (diagram, got, expected))

    for record in DIAGRAMS:
        diagram = record["diagram"]
        check_tits_relations(diagram)
        series = growth_coefficients(diagram, CHECK_LENGTH)
        counted = bfs_counts(diagram, CHECK_LENGTH)
        if series != counted:
            raise ArithmeticError(
                "%s series counts %s, BFS counts %s" % (diagram, series, counted)
            )
        print("%s counts through length %d: %s" % (diagram, CHECK_LENGTH, counted))

    rates = [(growth_rate(record["diagram"], 30).lower(), record["diagram"])
             for record in DIAGRAMS]
    smallest = min(rates)[1]
    if smallest != "[3,5,3]":
        raise ArithmeticError("smallest compact H3 rate is %s, not [3,5,3]" % smallest)

    print("checked %d compact tetrahedral groups" % len(DIAGRAMS))


class HyperbolicCoxeterSimplexGrowth(numberdb.Generator):
    table = os.environ.get("NUMBERDB_TABLE") or TABLE
    parameters = ("n", "diagram")
    type = "R"
    digits = 100
    rigour = "proven"
    files = ("generate.py",)

    def enumerate(self):
        for record in DIAGRAMS:
            yield {"n": "3", "diagram": record["diagram"]}

    def value(self, params, digits):
        if params["n"] != "3":
            raise ValueError("this draft currently holds only n=3")
        diagram = params["diagram"]
        return {
            "number": growth_rate(diagram, digits),
            "comment": entry_comment(diagram),
        }


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
    generator = HyperbolicCoxeterSimplexGrowth()
    if os.environ.get("NUMBERDB_CHECK_IDENTITIES") == "1":
        check_identities()
    elif "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="growth rates of compact hyperbolic Coxeter tetrahedral groups"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
