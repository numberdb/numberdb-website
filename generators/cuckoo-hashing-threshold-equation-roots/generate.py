"""Roots of the cuckoo hashing threshold equation -- numberdb.org/T288.

For k >= 2 and ell >= 1, xi_{k,ell} is the nonnegative auxiliary root used in
the orientability threshold for cuckoo hashing with k choices and bucket
capacity ell. Except for the removable row xi_{2,1} = 0, it is the positive
solution of

    k ell = xi Q(xi, ell) / Q(xi, ell + 1),

where Q(x, s) = P(Poisson(x) >= s). The threshold is

    c^*_{k,ell} = xi / (k Q(xi, ell)^(k - 1)).

This table stores xi_{k,ell} for 2 <= k <= 7 and 1 <= ell <= 6 at 100 digits
in ball arithmetic, matching the companion cuckoo hashing threshold table T274.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The positive root is enclosed by bisection on the sign of
xi Q(xi,ell) / Q(xi,ell+1) - k ell. The signs at both ends of the final
bracket are checked in ball arithmetic, and that bracket is the stored
enclosure. The row (k, ell) = (2, 1) is exact: the root equation is understood
by removable extension at xi = 0.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from decimal import Decimal

import numberdb.sage as numberdb
from numberdb._write import to_text
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField
from sage.rings.real_mpfr import RealField


TABLE = os.environ.get("NUMBERDB_TABLE", "T288")

# The range matches T274, the companion cuckoo hashing threshold table.
K_MIN = 2
K_MAX = 7
ELL_MIN = 1
ELL_MAX = 6

# Bits of working precision beyond what the written digits need. Measured at
# 100 digits: every positive-root ball has radius below 2e-106.
WORKING_GUARD = 64

# Decimal places by which the bracket around xi_{k,ell} is narrower than the
# values written.
BRACKET_GUARD = 6

THRESHOLD_TABLE = "T274"
XORSAT_ROOT_TABLE = "T287"

PUBLISHED_TEN_DIGITS = {
    (3, 1): "0.9179352767",
    (4, 1): "0.9767701649",
    (5, 1): "0.9924383913",
    (6, 1): "0.9973795528",
    (7, 1): "0.9990637588",
    (2, 2): "1.7940237365",
    (3, 2): "1.9764028279",
    (4, 2): "1.9964829679",
    (5, 2): "1.9994487201",
    (6, 2): "1.9999137473",
    (7, 2): "1.9999866878",
    (2, 3): "2.8774628058",
    (3, 3): "2.9918572178",
    (4, 3): "2.9993854302",
    (5, 3): "2.9999554360",
    (6, 3): "2.9999969384",
    (7, 3): "2.9999997987",
    (2, 4): "3.9214790971",
    (3, 4): "3.9970126256",
    (4, 4): "3.9998882644",
    (5, 4): "3.9999962949",
    (6, 4): "3.9999998884",
    (7, 4): "3.9999999969",
    (2, 5): "4.9477568093",
    (3, 5): "4.9988732941",
    (4, 5): "4.9999793407",
    (5, 5): "4.9999996871",
    (6, 5): "4.9999999959",
    (7, 5): "5.0000000000",
    (2, 6): "5.9644362395",
    (3, 6): "5.9995688805",
    (4, 6): "5.9999961417",
    (5, 6): "5.9999999733",
    (6, 6): "5.9999999998",
    (7, 6): "6.0000000000",
}


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


def root_function(x, k, ell):
    """The sign-changing function whose positive zero is xi_{k,ell}."""
    return x * poisson_tail(x, ell) / poisson_tail(x, ell + 1) - k * ell


def threshold_from_xi(x, k, ell):
    """The orientability threshold at a candidate root."""
    if k == 2 and ell == 1:
        return QQ(1) / QQ(2)
    return x / (k * poisson_tail(x, ell) ** (k - 1))


def root(k, ell, digits):
    """A ball enclosing xi_{k,ell}, found by bisection with sign checks."""
    if k == 2 and ell == 1:
        return QQ(0)
    if k < 2:
        raise ValueError("the formula is used here only for k >= 2")
    if ell < 1:
        raise ValueError("the formula is used here only for ell >= 1")

    bits = numberdb.bits(digits, losing=WORKING_GUARD)
    RBF, RR = RealBallField(bits), RealField(bits)
    delta = RR(10) ** (-(digits + BRACKET_GUARD))
    lo = RR("0.1")
    hi = RR(4 * (k + ell) + 10)

    while not (root_function(RBF(lo), k, ell) < 0):
        lo /= 2
        if lo < RR("1e-20"):
            raise ArithmeticError(
                "left endpoint did not have negative sign for k=%s, ell=%s" % (k, ell)
            )
    while not (root_function(RBF(hi), k, ell) > 0):
        hi *= 2
        if hi > 10000:
            raise ArithmeticError(
                "right endpoint did not bracket the root for k=%s, ell=%s" % (k, ell)
            )

    while hi - lo > delta / 4:
        mid = (lo + hi) / 2
        value = root_function(RBF(mid), k, ell)
        if value.contains_zero():
            raise ArithmeticError(
                "could not decide root sign at xi=%s for k=%s, ell=%s" % (mid, k, ell)
            )
        if value < 0:
            lo = mid
        else:
            hi = mid

    x0 = (lo + hi) / 2
    left = root_function(RBF(x0 - delta), k, ell)
    right = root_function(RBF(x0 + delta), k, ell)
    if not (left < 0 and right > 0):
        raise ArithmeticError("no sign change across root bracket for k=%s, ell=%s" % (k, ell))
    return RBF(x0).add_error(delta)


class CuckooHashingThresholdEquationRoots(numberdb.Generator):
    """Generator for T288, the table of roots xi_{k,ell}."""

    table = TABLE
    parameters = ("k", "ell")
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self):
        for k in range(K_MIN, K_MAX + 1):
            for ell in range(ELL_MIN, ELL_MAX + 1):
                yield {"k": str(k), "ell": str(ell)}

    def value(self, params, digits):
        k = int(params["k"])
        ell = int(params["ell"])
        xi = root(k, ell, digits)
        if k == 2 and ell == 1:
            comment = (
                r"This is the removable limiting root; the associated "
                r"threshold is HREF{T274#2,1}[$c^*_{2,1}=1/2$]."
            )
        else:
            comment = (
                r"The associated cuckoo hashing threshold is "
                r"HREF{T274#%d,%d}[$c^*_{%d,%d}$]." % (k, ell, k, ell)
            )
            if ell == 1 and k >= 3:
                comment += r" This is also HREF{T287#%d}[$\xi_{%d}$]." % (k, k)
        return {"number": xi, "comment": comment}


def _mpmath_root(k, ell, digits=120):
    """Independent numerical root using mpmath's incomplete gamma function."""
    from mpmath import mp

    if k == 2 and ell == 1:
        return mp.mpf("0")

    mp.dps = digits + 30

    def q(x, s):
        return mp.gammainc(s, 0, x, regularized=True)

    def g(x):
        return x * q(x, ell) / q(x, ell + 1) - k * ell

    left = mp.mpf("1e-30")
    right = mp.mpf(4 * (k + ell) + 10)
    while g(right) <= 0:
        right *= 2
    for _ in range(4 * digits):
        mid = (left + right) / 2
        if g(mid) < 0:
            left = mid
        else:
            right = mid
    return (left + right) / 2


def _round_decimal(text, places):
    return str(Decimal(text).quantize(Decimal("1e-%d" % places)))


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


def _stored_number(table, k, ell=None):
    numbers = table.get("Numbers") or {}
    if ell is None:
        record = numbers[str(k)]
    else:
        record = numbers[str(k)][str(ell)]
    return record["number"] if isinstance(record, dict) else record


def _stored_real_ball(field, text):
    """Read the database's exact rational or decimal spelling as a ball."""
    text = str(text)
    if "/" in text and "." not in text and "e" not in text.lower():
        return field(QQ(text))
    return field(text)


def run_integrity_checks():
    """Checks that do not share the generator's finite-sum root computation."""
    bits = numberdb.bits(120, losing=WORKING_GUARD)
    RBF = RealBallField(bits)
    tolerance = RBF("1e-95")

    threshold_table = _api_table(THRESHOLD_TABLE)
    try:
        xorsat_root_table = _api_table(XORSAT_ROOT_TABLE)
    except (urllib.error.HTTPError, urllib.error.URLError, KeyError):
        xorsat_root_table = None

    for k in range(K_MIN, K_MAX + 1):
        for ell in range(ELL_MIN, ELL_MAX + 1):
            xi = root(k, ell, 100)
            independent_xi = _mpmath_root(k, ell)
            independent = RBF(str(independent_xi))
            if not (abs(RBF(xi) - independent) < tolerance):
                raise ArithmeticError("mpmath root comparison failed for k=%d, ell=%d" % (k, ell))

            threshold = threshold_from_xi(xi, k, ell)
            expected = PUBLISHED_TEN_DIGITS.get((k, ell))
            if expected is not None:
                places = len(expected.split(".")[1])
                rounded = _round_decimal(to_text(threshold, 30), places)
                if rounded != expected:
                    raise ArithmeticError(
                        "published threshold check failed for k=%d, ell=%d: %s != %s"
                        % (k, ell, rounded, expected)
                    )

            stored_threshold = _stored_real_ball(RBF, _stored_number(threshold_table, k, ell))
            if not (abs(RBF(threshold) - stored_threshold) < tolerance):
                raise ArithmeticError(
                    "T274 threshold comparison failed for k=%d, ell=%d" % (k, ell)
                )

            if ell == 1 and k >= 3 and xorsat_root_table is not None:
                stored_xorsat = _stored_real_ball(RBF, _stored_number(xorsat_root_table, k))
                if not (abs(RBF(xi) - stored_xorsat) < tolerance):
                    raise ArithmeticError("T287 root comparison failed for k=%d" % k)


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
    generator = CuckooHashingThresholdEquationRoots()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message=(
                "roots xi_{k,ell} of the cuckoo hashing threshold equation "
                "for 2 <= k <= 7 and 1 <= ell <= 6"
            ),
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
