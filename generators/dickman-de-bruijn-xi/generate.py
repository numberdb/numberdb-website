"""Values of xi(u) in the Dickman-de Bruijn estimate -- numberdb.org/T423.

For u > 1, xi(u) is the positive root of

    exp(x) - 1 = u*x.

The row u = 1 stores the limiting value 0 exactly. The table stores every
two-decimal argument 1.00 <= u <= 12.00.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

Each non-boundary row is enclosed by bisection on exp(x) - 1 - u*x. The signs
at the final bracket endpoints are checked in ball arithmetic, and the bracket
is the stored enclosure.
"""

import os
import sys

import numberdb.sage as numberdb
from numberdb._write import to_text
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField
from sage.rings.real_mpfr import RealField


TABLE = os.environ.get("NUMBERDB_TABLE", "T423")
DIGITS = 100
U_MIN_CENTS = 100
U_MAX_CENTS = 1200

# Bits of working precision beyond what the written digits need. Measured at
# 100 digits: the narrowest final sign check occurs near u = 1.01, and still
# has enough margin to decide every bracket endpoint.
WORKING_GUARD = 64

# Decimal places by which the root bracket is narrower than the values written.
BRACKET_GUARD = 8

HYPERGRAPH_MINIMISER_TABLE = (
    "Minimisers_in_the_core_threshold_formula_of_random_k-uniform_hypergraphs"
)


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _fields(digits, guard=WORKING_GUARD):
    bits = numberdb.bits(digits, losing=guard)
    return RealBallField(bits), RealField(bits)


def _root_function(x, u):
    return x.exp() - 1 - u * x


def xi(u, digits, guard=WORKING_GUARD):
    """A ball enclosing the positive root of exp(x) - 1 = u*x."""
    u = QQ(u)
    if u == 1:
        return 0
    if u < 1:
        raise ValueError("this table uses the positive branch for u >= 1")

    RBF, RR = _fields(digits, guard)
    ub = RBF(u)
    ur = RR(u)
    delta = RR(10) ** (-(digits + BRACKET_GUARD))

    lo = RR(0)
    hi = RR(1)
    while _root_function(RBF(hi), ub) <= 0:
        hi *= 2

    # The zero root is always present, so bisection starts with lo = 0 and
    # never accepts that endpoint as the root.
    while hi - lo > delta / 4:
        mid = (lo + hi) / 2
        if mid == 0:
            mid = delta
        value = _root_function(RBF(mid), ub)
        if value.contains_zero():
            raise ArithmeticError("could not decide sign at x=%s for u=%s" % (mid, u))
        if value < 0:
            lo = mid
        else:
            hi = mid

    x0 = (lo + hi) / 2
    left = _root_function(RBF(x0 - delta), ub)
    right = _root_function(RBF(x0 + delta), ub)
    if not (left < 0 and right > 0):
        raise ArithmeticError("no sign change across xi(u) bracket for u=%s" % u)

    root = RBF(x0).add_error(delta)
    residual = _root_function(root, ub)
    if not residual.contains_zero():
        raise ArithmeticError("root enclosure fails defining equation for u=%s" % u)
    if not root > 0:
        raise ArithmeticError("positive root enclosure is not positive for u=%s" % u)

    # Keep `ur` live in this function so accidental float coercions are caught
    # by the type checks during development.
    assert ur > 1
    return root


def _u_values():
    for cents in range(U_MIN_CENTS, U_MAX_CENTS + 1):
        yield QQ(cents) / QQ(100)


def _integer_u(u):
    return u.denominator() == 1 and 2 <= int(u) <= 7


def _integer_entry(u):
    k = int(u) + 1
    return {
        "equals": (
            r"HREF{%s#%d,2}[$\lambda_{%d,2}$]"
            % (HYPERGRAPH_MINIMISER_TABLE, k, k)
        ),
        "comment": (
            r"This is the $r=2$ core-threshold minimiser "
            r"$\lambda_{%d,2}$." % k
        ),
    }


class DickmanDeBruijnXi(numberdb.Generator):

    table = TABLE
    parameters = ("u",)
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self):
        for u in _u_values():
            yield {"u": str(u)}

    def value(self, params, digits):
        u = QQ(params["u"])
        if u == 1:
            return {
                "number": 0,
                "comment": (
                    r"The positive branch used for $u>1$ has limiting value "
                    r"$0$ at $u=1$."
                ),
            }

        entry = {"number": xi(u, digits)}
        if _integer_u(u):
            entry.update(_integer_entry(u))
        return entry


def _mpmath_lambert_xi(u, digits=140):
    """Independent computation from the Lambert W formula."""
    from mpmath import mp

    mp.dps = digits + 30
    u = QQ(u)
    u = mp.mpf(int(u.numerator())) / mp.mpf(int(u.denominator()))
    value = -mp.lambertw(-mp.e ** (-1 / u) / u, -1) - 1 / u
    if abs(mp.im(value)) > mp.mpf(10) ** (-(digits + 10)):
        raise ArithmeticError("Lambert W check produced a non-real value")
    return mp.re(value)


def _check_lambert_formula():
    RBF, _RR = _fields(120, guard=WORKING_GUARD)
    tolerance = RBF("1e-95")
    for u in _u_values():
        if u == 1:
            continue
        computed = xi(u, DIGITS)
        independent = RBF(str(_mpmath_lambert_xi(u)))
        if not (abs(computed - independent) < tolerance):
            raise ArithmeticError(
                "Lambert W comparison failed for u=%s: %s vs %s"
                % (u, computed, independent)
            )


def _check_hypergraph_minimisers():
    table = numberdb.table("T289")
    numbers = table["Numbers"]
    RBF, _RR = _fields(120, guard=WORKING_GUARD)
    tolerance = RBF("1e-98")

    for u in range(2, 8):
        ours = xi(QQ(u), DIGITS)
        k = str(u + 1)
        theirs = numbers[k]["2"]
        if isinstance(theirs, dict):
            theirs = theirs["number"]
        other = RBF(theirs)
        if not (abs(ours - other) < tolerance):
            raise ArithmeticError(
                "T289 comparison failed for u=%d: %s vs %s" % (u, ours, other)
            )


def run_integrity_checks():
    """Independent checks for the identities stated in the table."""
    _check_lambert_formula()
    _check_hypergraph_minimisers()


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
        produced_by=_producer(
            generator,
            assisted_by=os.environ.get("NUMBERDB_ASSISTED_BY", "codex"),
        ),
        upsert=False,
        run=run,
        rigour=generator.rigour,
    )

    stored = []
    for name, body in sorted(_source_files(generator).items()):
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
    generator = DickmanDeBruijnXi()
    run_integrity_checks()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message=(
                "xi(u) in the Dickman-de Bruijn estimate on the two-decimal "
                "grid 1 <= u <= 12"
            ),
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
