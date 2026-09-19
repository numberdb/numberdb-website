"""Minimisers in the core threshold formula of random k-uniform hypergraphs.

For k >= 2 and r >= 2, except (k, r) = (2, 2), lambda_{k,r} is the
positive value at which

    lambda / (k * P(Poisson(lambda) >= r - 1)^(k - 1))

attains the random k-uniform hypergraph r-core threshold c_{k,r}.

This table stores lambda_{k,r} for 3 <= k <= 8 and 2 <= r <= 8, and for the
graph case k = 2 with 3 <= r <= 12, at 100 digits in ball arithmetic.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The minimiser lambda_{k,r} is enclosed by bisection on the sign of

    g(lambda) = Q(lambda,r-1) - (k-1) exp(-lambda) lambda^(r-1)/(r-2)!,

where Q(lambda,s) = P(Poisson(lambda) >= s). The signs at both ends of the
final bracket are checked in ball arithmetic, and that bracket is the stored
enclosure. The same derivative calculation used in the companion threshold
table proves that this positive zero is unique and gives the global minimum.
"""

import json
import os
import re
import sys
import urllib.request
from decimal import Decimal

import numberdb.sage as numberdb
from numberdb._write import to_text
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField
from sage.rings.real_mpfr import RealField


TABLE = os.environ.get("NUMBERDB_TABLE", "T289")

# The hypergraph rows match T273, the companion core-threshold table. The
# graph rows match T156, where the thresholds are stored but the minimisers are
# only named in entry comments.
HYPERGRAPH_K_MIN = 3
HYPERGRAPH_K_MAX = 8
HYPERGRAPH_R_MIN = 2
HYPERGRAPH_R_MAX = 8
GRAPH_K = 2
GRAPH_R_MIN = 3
GRAPH_R_MAX = 12

# Bits of working precision beyond what the written digits need. Measured at
# 100 digits: every minimiser ball has radius below 2e-106.
WORKING_GUARD = 64

# Decimal places by which the bracket around lambda_{k,r} is narrower than the
# values written.
BRACKET_GUARD = 6

THRESHOLD_TABLE = "T273"
GRAPH_CORE_TABLE = "T156"
THRESHOLD_SLUG = "Core_thresholds_of_random_k-uniform_hypergraphs"
GRAPH_CORE_SLUG = "k-core_thresholds_of_the_Erd\u0151s_R\u00e9nyi_random_graph"


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def poisson_tail(x, s):
    """Q(x,s) = P(Poisson(x) >= s), for integer s >= 1 and a ball x."""
    if s < 1:
        raise ValueError("the finite tail formula here expects s >= 1")
    total = x.parent()(0)
    term = x.parent()(1)
    for j in range(s):
        if j:
            term = term * x / j
        total += term
    return 1 - (-x).exp() * total


def minimiser_function(x, k, r):
    """The numerator of the derivative of lambda / Q(lambda,r-1)^(k-1)."""
    return (
        poisson_tail(x, r - 1)
        - (k - 1) * (-x).exp() * x ** (r - 1) / ZZ(r - 2).factorial()
    )


def threshold_from_lambda(x, k, r):
    """The hypergraph r-core threshold at the minimiser."""
    return x / (k * poisson_tail(x, r - 1) ** (k - 1))


def minimiser(k, r, digits):
    """A ball enclosing the unique positive minimiser lambda_{k,r}."""
    if k < 2:
        raise ValueError("the formula is used here only for k >= 2")
    if r < 2:
        raise ValueError("the formula is used here only for r >= 2")

    bits = numberdb.bits(digits, losing=WORKING_GUARD)
    RBF, RR = RealBallField(bits), RealField(bits)
    delta = RR(10) ** (-(digits + BRACKET_GUARD))
    lo = RR(r - 1) - RR(1) / RR(k - 1)
    hi = RR(4 * (k + r) + 10)

    if not (minimiser_function(RBF(lo), k, r) < 0):
        raise ArithmeticError("left endpoint does not have negative sign for k=%s, r=%s" % (k, r))
    while not (minimiser_function(RBF(hi), k, r) > 0):
        hi *= 2
        if hi > 10000:
            raise ArithmeticError("right endpoint did not bracket the minimiser for k=%s, r=%s" % (k, r))

    while hi - lo > delta / 4:
        mid = (lo + hi) / 2
        value = minimiser_function(RBF(mid), k, r)
        if value.contains_zero():
            raise ArithmeticError(
                "could not decide minimiser sign at lambda=%s for k=%s, r=%s" % (mid, k, r)
            )
        if value < 0:
            lo = mid
        else:
            hi = mid

    x0 = (lo + hi) / 2
    left = minimiser_function(RBF(x0 - delta), k, r)
    right = minimiser_function(RBF(x0 + delta), k, r)
    if not (left < 0 and right > 0):
        raise ArithmeticError("no sign change across minimiser bracket for k=%s, r=%s" % (k, r))
    return RBF(x0).add_error(delta)


class CoreThresholdMinimisers(numberdb.Generator):
    """Generator for T289, the table of minimisers lambda_{k,r}."""

    table = TABLE
    parameters = ("k", "r")
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self):
        for r in range(GRAPH_R_MIN, GRAPH_R_MAX + 1):
            yield {"k": str(GRAPH_K), "r": str(r)}
        for k in range(HYPERGRAPH_K_MIN, HYPERGRAPH_K_MAX + 1):
            for r in range(HYPERGRAPH_R_MIN, HYPERGRAPH_R_MAX + 1):
                yield {"k": str(k), "r": str(r)}

    def value(self, params, digits):
        k = int(params["k"])
        r = int(params["r"])
        lam = minimiser(k, r, digits)
        if k == GRAPH_K:
            comment = (
                r"The corresponding graph $r$-core threshold is "
                r"HREF{%s#%d}[$c_%d$], in average-degree normalisation."
                % (GRAPH_CORE_SLUG, r, r)
            )
        else:
            comment = (
                r"The associated core threshold is "
                r"HREF{%s#%d,%d}[$c_{%d,%d}$]." % (THRESHOLD_SLUG, k, r, k, r)
            )
        return {"number": lam, "comment": comment}


def _mpmath_minimiser(k, r, digits=120):
    """Independent numerical minimiser using mpmath's incomplete gamma function."""
    from mpmath import mp

    mp.dps = digits + 30
    factorial = mp.factorial(r - 2)

    def q(x):
        return mp.gammainc(r - 1, 0, x, regularized=True)

    def g(x):
        return q(x) - (k - 1) * mp.e ** (-x) * x ** (r - 1) / factorial

    left = mp.mpf(r - 1) - mp.mpf(1) / mp.mpf(k - 1)
    right = mp.mpf(4 * (k + r) + 10)
    while g(right) <= 0:
        right *= 2
    for _ in range(4 * digits):
        mid = (left + right) / 2
        if g(mid) < 0:
            left = mid
        else:
            right = mid
    return (left + right) / 2


def _api_table(tid):
    """Read a public table, or a draft when NUMBERDB_API_KEY may see it."""
    headers = {}
    token = os.environ.get("NUMBERDB_API_KEY", "").strip()
    if token:
        headers["Authorization"] = "Bearer %s" % token
    request = urllib.request.Request(
        "https://numberdb.org/api/table?id=%s" % tid,
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def _stored_number(table, k, r=None):
    numbers = table.get("Numbers") or {}
    if r is None:
        record = numbers[str(k)]
    else:
        record = numbers[str(k)][str(r)]
    return record["number"] if isinstance(record, dict) else record


def _stored_comment(table, k, r=None):
    numbers = table.get("Numbers") or {}
    if r is None:
        record = numbers[str(k)]
    else:
        record = numbers[str(k)][str(r)]
    return record.get("comment", "") if isinstance(record, dict) else ""


def _stored_real_ball(field, text):
    """Read the database's exact rational or decimal spelling as a ball."""
    text = str(text)
    if "/" in text and "." not in text and "e" not in text.lower():
        return field(QQ(text))
    return field(text)


def _round_decimal(text, places):
    return str(Decimal(text).quantize(Decimal("1e-%d" % places)))


def _comment_minimiser_prefix(comment):
    match = re.search(r"\\lambda_\{?\d+(?:,\d+)?\}?=([0-9.]+)", comment)
    if not match:
        raise ArithmeticError("could not read minimiser from comment: %s" % comment)
    return match.group(1)


def run_integrity_checks():
    """Checks that do not share the generator's finite-sum implementation."""
    bits = numberdb.bits(120, losing=WORKING_GUARD)
    RBF = RealBallField(bits)
    tolerance = RBF("1e-95")

    threshold_table = _api_table(THRESHOLD_TABLE)
    graph_table = _api_table(GRAPH_CORE_TABLE)

    for k in range(HYPERGRAPH_K_MIN, HYPERGRAPH_K_MAX + 1):
        for r in range(HYPERGRAPH_R_MIN, HYPERGRAPH_R_MAX + 1):
            lam = minimiser(k, r, 100)

            independent_lam = _mpmath_minimiser(k, r)
            independent = RBF(str(independent_lam))
            if not (abs(lam - independent) < tolerance):
                raise ArithmeticError("mpmath minimiser comparison failed for k=%d, r=%d" % (k, r))

            threshold = threshold_from_lambda(lam, k, r)
            stored_threshold = _stored_real_ball(RBF, _stored_number(threshold_table, k, r))
            if not (abs(RBF(threshold) - stored_threshold) < tolerance):
                raise ArithmeticError(
                    "T273 threshold comparison failed for k=%d, r=%d" % (k, r)
                )

            expected = _comment_minimiser_prefix(_stored_comment(threshold_table, k, r))
            places = len(expected.split(".")[1])
            rounded = _round_decimal(to_text(lam, 30), places)
            if rounded != expected:
                raise ArithmeticError(
                    "T273 comment minimiser check failed for k=%d, r=%d: %s != %s"
                    % (k, r, rounded, expected)
                )

    for r in range(GRAPH_R_MIN, GRAPH_R_MAX + 1):
        graph_lam = minimiser(2, r, 100)
        graph_comment = _stored_comment(graph_table, r)
        expected = _comment_minimiser_prefix(graph_comment)
        places = len(expected.split(".")[1])
        rounded = _round_decimal(to_text(graph_lam, 30), places)
        if rounded != expected:
            raise ArithmeticError(
                "T156 graph minimiser check failed for r=%d: %s != %s" % (r, rounded, expected)
            )

        graph_threshold = threshold_from_lambda(graph_lam, 2, r)
        stored_half = _stored_real_ball(RBF, _stored_number(graph_table, r)) / 2
        if not (abs(RBF(graph_threshold) - stored_half) < tolerance):
            raise ArithmeticError("T156 half-threshold comparison failed for r=%d" % r)


def fill_draft_once(generator, message):
    """Fill a fresh draft without the client's empty upsert probe."""
    from numberdb._generate import (
        _check_precision,
        _check_rigour,
        _producer,
        _run_name,
        _source_files,
    )
    from numberdb._write import Entries, attach, submit_entries

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
    generator = CoreThresholdMinimisers()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(generator.publish(
            overwrite=False,
            message=(
                "added graph-case minimisers lambda_{2,r} for 3 <= r <= 12"
            ),
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
