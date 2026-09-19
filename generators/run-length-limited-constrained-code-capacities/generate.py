"""numberdb.org/T340 -- capacity of the $(d,k)$ run-length-limited constrained codes.

This generator fills the draft table of capacities of binary $(d,k)$
run-length-limited constrained codes, in nats and bits.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import math
import os
import sys

import numberdb.sage as numberdb
from sage.rings.rational_field import QQ
from sage.rings.real_mpfi import RealIntervalField


TABLE = os.environ.get("NUMBERDB_TABLE", "T340")
DIGITS = 100
WORKING_GUARD = 96
MAX_K = 28
MAX_D_INFINITY = 28
BISECTION_STEPS = 520


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _parse_k(value):
    if value == "inf":
        return None
    return int(value)


def _root_function(d, k, x):
    if k is None:
        return x ** (d + 1) + x - 1
    total = QQ(0)
    power = x ** (d + 1)
    for _ in range(d + 1, k + 2):
        total += power
        power *= x
    return total - 1


def root_bracket(d, k):
    """Return exact rationals lo < rho < hi for the unique root."""
    lo = QQ(0)
    hi = QQ(1)
    for _ in range(BISECTION_STEPS):
        mid = (lo + hi) / 2
        value = _root_function(d, k, mid)
        if value < 0:
            lo = mid
        elif value > 0:
            hi = mid
        else:
            return mid, mid
    if _root_function(d, k, lo) > 0 or _root_function(d, k, hi) < 0:
        raise ArithmeticError("root is not bracketed for d=%s, k=%s" % (d, k))
    return lo, hi


def capacity_interval(d, k, unit, digits=DIGITS):
    bits = numberdb.bits(digits, losing=WORKING_GUARD)
    field = RealIntervalField(bits)
    lo, hi = root_bracket(d, k)
    if lo == hi:
        rho = field(lo)
    else:
        rho = field(lo, hi)
    value = -rho.log()
    if unit == "bits":
        value = value / field(2).log()
    return value


def _entry_comment(d, k, unit):
    if d == 0 and k is None and unit == "nats":
        return "The corresponding bits value is exactly $1$ and is omitted."
    if d == 1 and k is None:
        return "$C(1,\\infty)=\\log\\varphi$, the topological entropy of the golden-mean shift."
    if d == 1 and k == 2:
        return "$1/\\rho$ is the plastic number, the real root of $x^3=x+1$."
    return None


def _finite_state_lambda(d, k):
    import numpy

    if k is None:
        states = d + 1

        def zero_target(state):
            return min(state + 1, d)

        def one_allowed(state):
            return state >= d
    else:
        states = k + 1

        def zero_target(state):
            return state + 1

        def one_allowed(state):
            return state >= d

    matrix = numpy.zeros((states, states), dtype=float)
    for state in range(states):
        if k is None or state < k:
            matrix[state, zero_target(state)] += 1.0
        if one_allowed(state):
            matrix[state, 0] += 1.0
    return max(abs(value) for value in numpy.linalg.eigvals(matrix))


def _lambda_midpoint(d, k):
    lo, hi = root_bracket(d, k)
    if lo == hi:
        return 1.0 / float(lo)
    return 2.0 / (float(lo) + float(hi))


def _all_parameter_pairs():
    for d in range(0, MAX_K):
        for k in range(d + 1, MAX_K + 1):
            yield d, k
    for d in range(0, MAX_D_INFINITY + 1):
        yield d, None


class RunLengthLimitedCapacity(numberdb.Generator):
    """Generator for T340, the table of $(d,k)$ RLL capacities."""

    table = TABLE
    parameters = ("d", "k", "unit")
    type = "R"
    rigour = "proven"
    digits = DIGITS

    def enumerate(self):
        for d, k in _all_parameter_pairs():
            k_key = "inf" if k is None else str(k)
            for unit in ("nats", "bits"):
                if d == 0 and k is None and unit == "bits":
                    continue
                yield {"d": str(d), "k": k_key, "unit": unit}

    def value(self, params, digits):
        d = int(params["d"])
        k = _parse_k(params["k"])
        unit = params["unit"]
        value = capacity_interval(d, k, unit, digits)
        comment = _entry_comment(d, k, unit)
        if comment is None:
            return value
        return {"number": value, "comment": comment}


def run_integrity_checks():
    largest_difference = 0.0
    worst = None
    for d, k in _all_parameter_pairs():
        lo, hi = root_bracket(d, k)
        if lo != hi and not (_root_function(d, k, lo) < 0 < _root_function(d, k, hi)):
            raise ArithmeticError("bad root bracket for d=%s, k=%s" % (d, k))
        from_graph = _finite_state_lambda(d, k)
        from_root = _lambda_midpoint(d, k)
        difference = abs(from_graph - from_root)
        if difference > largest_difference:
            largest_difference = difference
            worst = (d, k)
        if difference > 5e-12:
            raise ArithmeticError(
                "Perron eigenvalue check failed for d=%s, k=%s: %.17g vs %.17g"
                % (d, k, from_root, from_graph)
            )

    phi = (1.0 + math.sqrt(5.0)) / 2.0
    if abs(_lambda_midpoint(1, None) - phi) > 1e-14:
        raise ArithmeticError("C(1, infinity) did not recover the golden ratio")

    plastic = 1.324717957244746
    if abs(_lambda_midpoint(1, 2) - plastic) > 1e-14:
        raise ArithmeticError("C(1,2) did not recover the plastic number")

    print("checked %d RLL constraints against finite-state Perron roots" % (
        sum(1 for _ in _all_parameter_pairs())))
    print("largest Perron-root difference %.3g at d=%s, k=%s" % (
        largest_difference,
        worst[0],
        "inf" if worst[1] is None else worst[1],
    ))


def fill_draft_once(generator, message):
    """Fill a fresh prose draft without the client's empty upsert probe."""
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
        produced_by=_producer(generator, os.environ.get("NUMBERDB_ASSISTED_BY", "")),
        upsert=False,
        run=run,
        rigour=generator.rigour,
    )

    for name, body in sorted(_source_files(generator).items()):
        attach(table, name, body, run=run, message=message, rigour=generator.rigour)

    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = RunLengthLimitedCapacity()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="fill RLL constrained-code capacities from isolated roots",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
