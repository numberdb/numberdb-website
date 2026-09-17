"""Butcher tableaux of explicit Runge-Kutta methods -- numberdb.org/T304

For each listed rational explicit Runge-Kutta method, this table stores the
nonzero rational entries of its Butcher tableau: nodes c_i, matrix entries
a_{ij}, and order-labelled weights b_i^(q).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The coefficients are transcribed from the cited source revisions. Before any
entry is returned, every tableau is checked over QQ against its stage row sums,
the moment conditions, the rooted-tree order conditions through the stated
order of each weight row, and the SciPy RK23 and RK45 arrays for the
Bogacki-Shampine and Dormand-Prince methods.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.rational_field import QQ


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def Q(value):
    if isinstance(value, str):
        if "/" in value:
            numerator, denominator = value.split("/", 1)
            return QQ(int(numerator)) / QQ(int(denominator))
        return QQ(int(value))
    return QQ(value)


def row(*values):
    return tuple(Q(value) for value in values)


def method(key, name, c, a, weights, advance=None, note=None):
    c = row(*c)
    stages = len(c)
    padded = []
    for i, given in enumerate(a, start=1):
        values = row(*given)
        if len(values) > i - 1:
            raise ValueError("%s stage %d has too many a entries" % (key, i))
        padded.append(values + (Q(0),) * (stages - len(values)))
    if len(padded) != stages:
        raise ValueError("%s has %d c entries and %d a rows" % (key, stages, len(padded)))
    converted_weights = []
    for order, values in weights:
        values = row(*values)
        if len(values) != stages:
            raise ValueError("%s order %d has %d weights for %d stages"
                             % (key, order, len(values), stages))
        converted_weights.append((int(order), values))
    return {
        "key": key,
        "name": name,
        "c": c,
        "a": tuple(padded),
        "weights": tuple(converted_weights),
        "advance": advance,
        "note": note,
    }


METHODS = (
    method(
        "forward-euler",
        "Forward Euler method",
        ("0",),
        ((),),
        ((1, ("1",)),),
    ),
    method(
        "midpoint",
        "Explicit midpoint method",
        ("0", "1/2"),
        ((), ("1/2",)),
        ((2, ("0", "1")),),
    ),
    method(
        "heun-2",
        "Heun's second-order method",
        ("0", "1"),
        ((), ("1",)),
        ((2, ("1/2", "1/2")),),
    ),
    method(
        "ralston-2",
        "Ralston's second-order method",
        ("0", "2/3"),
        ((), ("2/3",)),
        ((2, ("1/4", "3/4")),),
    ),
    method(
        "kutta-3",
        "Kutta's third-order method",
        ("0", "1/2", "1"),
        ((), ("1/2",), ("-1", "2")),
        ((3, ("1/6", "2/3", "1/6")),),
    ),
    method(
        "heun-3",
        "Heun's third-order method",
        ("0", "1/3", "2/3"),
        ((), ("1/3",), ("0", "2/3")),
        ((3, ("1/4", "0", "3/4")),),
    ),
    method(
        "ralston-3",
        "Ralston's third-order method",
        ("0", "1/2", "3/4"),
        ((), ("1/2",), ("0", "3/4")),
        ((3, ("2/9", "1/3", "4/9")),),
    ),
    method(
        "van-der-houwen-wray",
        "Van der Houwen-Wray third-order method",
        ("0", "8/15", "2/3"),
        ((), ("8/15",), ("1/4", "5/12")),
        ((3, ("1/4", "0", "3/4")),),
    ),
    method(
        "ssprk3",
        "Third-order strong stability preserving Runge-Kutta method",
        ("0", "1", "1/2"),
        ((), ("1",), ("1/4", "1/4")),
        ((3, ("1/6", "1/6", "2/3")),),
    ),
    method(
        "rk4",
        "Classic fourth-order Runge-Kutta method",
        ("0", "1/2", "1/2", "1"),
        ((), ("1/2",), ("0", "1/2"), ("0", "0", "1")),
        ((4, ("1/6", "1/3", "1/3", "1/6")),),
    ),
    method(
        "three-eighths",
        "3/8-rule fourth-order method",
        ("0", "1/3", "2/3", "1"),
        ((), ("1/3",), ("-1/3", "1"), ("1", "-1", "1")),
        ((4, ("1/8", "3/8", "3/8", "1/8")),),
    ),
    method(
        "nystrom-5",
        "Nystrom's fifth-order method",
        ("0", "1/3", "2/5", "1", "2/3", "4/5"),
        (
            (),
            ("1/3",),
            ("4/25", "6/25"),
            ("1/4", "-3", "15/4"),
            ("2/27", "10/9", "-50/81", "8/81"),
            ("2/25", "12/25", "2/15", "8/75", "0"),
        ),
        ((5, ("23/192", "0", "125/192", "0", "-27/64", "125/192")),),
    ),
    method(
        "heun-euler",
        "Heun-Euler embedded pair",
        ("0", "1"),
        ((), ("1",)),
        ((2, ("1/2", "1/2")), (1, ("1", "0"))),
        advance=2,
    ),
    method(
        "fehlberg-12",
        "Fehlberg RK1(2) embedded pair",
        ("0", "1/2", "1"),
        ((), ("1/2",), ("1/256", "255/256")),
        ((2, ("1/512", "255/256", "1/512")),
         (1, ("1/256", "255/256", "0"))),
        advance=1,
    ),
    method(
        "bogacki-shampine",
        "Bogacki-Shampine embedded pair",
        ("0", "1/2", "3/4", "1"),
        ((), ("1/2",), ("0", "3/4"), ("2/9", "1/3", "4/9")),
        ((3, ("2/9", "1/3", "4/9", "0")),
         (2, ("7/24", "1/4", "1/3", "1/8"))),
        advance=3,
        note="This is SciPy's RK23 tableau.",
    ),
    method(
        "fehlberg-45",
        "Runge-Kutta-Fehlberg RKF45 embedded pair",
        ("0", "1/4", "3/8", "12/13", "1", "1/2"),
        (
            (),
            ("1/4",),
            ("3/32", "9/32"),
            ("1932/2197", "-7200/2197", "7296/2197"),
            ("439/216", "-8", "3680/513", "-845/4104"),
            ("-8/27", "2", "-3544/2565", "1859/4104", "-11/40"),
        ),
        ((5, ("16/135", "0", "6656/12825", "28561/56430", "-9/50", "2/55")),
         (4, ("25/216", "0", "1408/2565", "2197/4104", "-1/5", "0"))),
        advance=4,
    ),
    method(
        "cash-karp",
        "Cash-Karp embedded pair",
        ("0", "1/5", "3/10", "3/5", "1", "7/8"),
        (
            (),
            ("1/5",),
            ("3/40", "9/40"),
            ("3/10", "-9/10", "6/5"),
            ("-11/54", "5/2", "-70/27", "35/27"),
            ("1631/55296", "175/512", "575/13824", "44275/110592", "253/4096"),
        ),
        ((5, ("37/378", "0", "250/621", "125/594", "0", "512/1771")),
         (4, ("2825/27648", "0", "18575/48384", "13525/55296", "277/14336", "1/4"))),
        advance=5,
    ),
    method(
        "dormand-prince",
        "Dormand-Prince embedded pair",
        ("0", "1/5", "3/10", "4/5", "8/9", "1", "1"),
        (
            (),
            ("1/5",),
            ("3/40", "9/40"),
            ("44/45", "-56/15", "32/9"),
            ("19372/6561", "-25360/2187", "64448/6561", "-212/729"),
            ("9017/3168", "-355/33", "46732/5247", "49/176", "-5103/18656"),
            ("35/384", "0", "500/1113", "125/192", "-2187/6784", "11/84"),
        ),
        ((5, ("35/384", "0", "500/1113", "125/192", "-2187/6784", "11/84", "0")),
         (4, ("5179/57600", "0", "7571/16695", "393/640", "-92097/339200", "187/2100", "1/40"))),
        advance=5,
        note="This is SciPy's RK45 tableau; the seventh stage is the FSAL row.",
    ),
)

METHOD_BY_KEY = {entry["key"]: entry for entry in METHODS}
CHECKED = False


def _tree_order(tree):
    return 1 + sum(_tree_order(child) for child in tree)


def _tree_factorial(tree):
    result = _tree_order(tree)
    for child in tree:
        result *= _tree_factorial(child)
    return result


def _tree_key(tree):
    return (_tree_order(tree), repr(tree))


def _trees_by_order(max_order):
    by_order = {1: ((),)}
    for order in range(2, max_order + 1):
        pool = []
        for child_order in range(1, order):
            for child in by_order[child_order]:
                pool.append((child_order, child))
        pool.sort(key=lambda item: (_tree_key(item[1])))
        found = set()

        def build(start, remaining, children):
            if remaining == 0:
                found.add(tuple(children))
                return
            for index in range(start, len(pool)):
                child_order, child = pool[index]
                if child_order <= remaining:
                    build(index, remaining - child_order, children + [child])

        build(0, order - 1, [])
        by_order[order] = tuple(sorted(found, key=_tree_key))
    return by_order


TREES = _trees_by_order(5)


def _stage_tree_weight(a, stage, tree, memo):
    key = (stage, tree)
    if key in memo:
        return memo[key]
    if tree == ():
        memo[key] = Q(1)
        return memo[key]
    total = Q(1)
    for child in tree:
        child_sum = Q(0)
        for other in range(len(a)):
            child_sum += a[stage][other] * _stage_tree_weight(a, other, child, memo)
        total *= child_sum
    memo[key] = total
    return total


def _check_row_sums(tableau):
    for index, (node, row_values) in enumerate(zip(tableau["c"], tableau["a"]), start=1):
        if sum(row_values) != node:
            raise ArithmeticError("%s: stage %d row sum is %s, not %s"
                                  % (tableau["key"], index, sum(row_values), node))


def _check_moments(tableau, order, weights):
    for power in range(1, order + 1):
        got = sum(weight * node ** (power - 1)
                  for node, weight in zip(tableau["c"], weights))
        expected = Q(1) / Q(power)
        if got != expected:
            raise ArithmeticError("%s order %d: moment %d is %s, not %s"
                                  % (tableau["key"], order, power, got, expected))


def _check_rooted_trees(tableau, order, weights):
    if order > max(TREES):
        raise ValueError("rooted-tree checks are implemented only through order %d"
                         % max(TREES))
    for tree_order in range(1, order + 1):
        for tree in TREES[tree_order]:
            memo = {}
            got = sum(weight * _stage_tree_weight(tableau["a"], stage, tree, memo)
                      for stage, weight in enumerate(weights))
            expected = Q(1) / Q(_tree_factorial(tree))
            if got != expected:
                raise ArithmeticError(
                    "%s order %d: tree %r gives %s, not %s"
                    % (tableau["key"], order, tree, got, expected))


def _check_scipy():
    rk23 = METHOD_BY_KEY["bogacki-shampine"]
    if rk23["c"][:3] != row("0", "1/2", "3/4"):
        raise ArithmeticError("SciPy RK23 nodes disagree")
    if rk23["a"][:3] != (
        row("0", "0", "0", "0"),
        row("1/2", "0", "0", "0"),
        row("0", "3/4", "0", "0"),
    ):
        raise ArithmeticError("SciPy RK23 matrix disagrees")
    high = row("2/9", "1/3", "4/9", "0")
    error = row("5/72", "-1/12", "-1/9", "1/8")
    if dict(rk23["weights"])[3] != high:
        raise ArithmeticError("SciPy RK23 third-order row disagrees")
    if dict(rk23["weights"])[2] != tuple(high[i] + error[i] for i in range(4)):
        raise ArithmeticError("SciPy RK23 error row disagrees")

    rk45 = METHOD_BY_KEY["dormand-prince"]
    if rk45["c"][:6] != row("0", "1/5", "3/10", "4/5", "8/9", "1"):
        raise ArithmeticError("SciPy RK45 nodes disagree")
    expected_a = (
        row("0", "0", "0", "0", "0", "0", "0"),
        row("1/5", "0", "0", "0", "0", "0", "0"),
        row("3/40", "9/40", "0", "0", "0", "0", "0"),
        row("44/45", "-56/15", "32/9", "0", "0", "0", "0"),
        row("19372/6561", "-25360/2187", "64448/6561", "-212/729", "0", "0", "0"),
        row("9017/3168", "-355/33", "46732/5247", "49/176", "-5103/18656", "0", "0"),
    )
    if rk45["a"][:6] != expected_a:
        raise ArithmeticError("SciPy RK45 matrix disagrees")
    high = row("35/384", "0", "500/1113", "125/192", "-2187/6784", "11/84", "0")
    error = row("-71/57600", "0", "71/16695", "-71/1920", "17253/339200",
                "-22/525", "1/40")
    if dict(rk45["weights"])[5] != high:
        raise ArithmeticError("SciPy RK45 fifth-order row disagrees")
    if dict(rk45["weights"])[4] != tuple(high[i] + error[i] for i in range(7)):
        raise ArithmeticError("SciPy RK45 error row disagrees")


def _check_all():
    global CHECKED
    if CHECKED:
        return
    if len(METHODS) != 18:
        raise ArithmeticError("expected 18 methods, got %d" % len(METHODS))
    if len(METHOD_BY_KEY) != len(METHODS):
        raise ArithmeticError("method keys are not unique")
    for tableau in METHODS:
        _check_row_sums(tableau)
        for order, weights in tableau["weights"]:
            _check_moments(tableau, order, weights)
            _check_rooted_trees(tableau, order, weights)
    _check_scipy()
    CHECKED = True


def _latex_rational(value):
    value = Q(value)
    numerator = int(value.numerator())
    denominator = int(value.denominator())
    if denominator == 1:
        return str(numerator)
    sign = "-" if numerator < 0 else ""
    return r"%s\tfrac{%d}{%d}" % (sign, abs(numerator), denominator)


def _plain_rational(value):
    value = Q(value)
    numerator = int(value.numerator())
    denominator = int(value.denominator())
    if denominator == 1:
        return str(numerator)
    return "%d/%d" % (numerator, denominator)


def _coefficient_label(key):
    if key.startswith("c"):
        return "$c_%s$" % key[1:]
    if key.startswith("a"):
        i, j = key[1:].split("_")
        return "$a_{%s%s}$" % (i, j)
    if key.startswith("b"):
        order, stage = key[1:].split("_")
        return "$b^{(%s)}_%s$" % (order, stage)
    raise ValueError("unknown coefficient key %r" % key)


def _entries(tableau):
    out = []
    stages = len(tableau["c"])
    for stage in range(1, stages + 1):
        node = tableau["c"][stage - 1]
        if node != 0:
            key = "c%d" % stage
            out.append((key, _coefficient_label(key), node))
        for previous in range(1, stage):
            value = tableau["a"][stage - 1][previous - 1]
            if value == 0:
                continue
            key = "a%d_%d" % (stage, previous)
            out.append((key, _coefficient_label(key), value))
    for order, weights in tableau["weights"]:
        for stage, value in enumerate(weights, start=1):
            if value == 0:
                continue
            key = "b%d_%d" % (order, stage)
            out.append((key, _coefficient_label(key), value))
    return tuple(out)


def _weight_row_comment(order, weights):
    values = ", ".join(_latex_rational(value) for value in weights)
    return "$b^{(%d)}=(%s)$" % (order, values)


def _method_comment(tableau):
    rows = "; ".join(_weight_row_comment(order, weights)
                     for order, weights in tableau["weights"])
    sentence = "%s: %s." % (tableau["name"], rows)
    if tableau["advance"] is not None and len(tableau["weights"]) > 1:
        sentence += " The order-%d row is the advancing formula." % tableau["advance"]
    if tableau["note"]:
        sentence += " " + tableau["note"]
    return sentence


class ExplicitRungeKuttaTableaux(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T304")
    parameters = ("method", "coefficient")
    type = "Q"
    rigour = "exact"

    def enumerate(self):
        _check_all()
        for tableau in METHODS:
            for key, _label, _value in _entries(tableau):
                yield {"method": tableau["key"], "coefficient": key}

    def value(self, params, digits=None):
        _check_all()
        tableau = METHOD_BY_KEY[params["method"]]
        entries = _entries(tableau)
        for index, (key, label, value) in enumerate(entries):
            if key != params["coefficient"]:
                continue
            record = {"number": value, "param-latex": label}
            if index == 0:
                record["comment"] = _method_comment(tableau)
            return record
        raise ValueError("no coefficient %r for %s"
                         % (params["coefficient"], params["method"]))


if __name__ == "__main__":
    _key_from_stdin()
    generator = ExplicitRungeKuttaTableaux()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="explicit Runge-Kutta Butcher tableaux"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
