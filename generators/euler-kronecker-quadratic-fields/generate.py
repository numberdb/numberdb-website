"""Euler-Kronecker constants of quadratic fields -- numberdb.org/T230

For each fundamental discriminant D with |D| <= 1000 and D != 1, this stores
Ihara's Euler-Kronecker constant gamma_K = c_0 / c_{-1} for
K = Q(sqrt D), where

    zeta_K(s) = c_{-1} (s - 1)^-1 + c_0 + O(s - 1).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Values are computed as real balls. Since
zeta_K(s) = zeta(s) L(s, chi_D), the value is
gamma + L'(1, chi_D) / L(1, chi_D). The L-series and its derivative are
computed from the Hurwitz-zeta expansion with the pole deflated before the
Kronecker-character sum is formed.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import is_squarefree, kronecker_symbol
from sage.rings.complex_arb import ComplexBallField
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


BOUND = 1000
WORKING_GUARD = 96

_RING_CACHE = {}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def is_fundamental_discriminant(D):
    """Whether D is the discriminant of a quadratic field."""
    D = ZZ(D)
    if D == 0 or D == 1:
        return False
    if D % 4 == 1:
        return is_squarefree(D)
    if D % 4 == 0:
        m = D // 4
        return m % 4 in (2, 3) and is_squarefree(m)
    return False


def fundamental_discriminants(bound):
    """Fundamental discriminants with |D| <= bound, ordered as in T128."""
    return [ZZ(D) for D in sorted(range(-bound, bound + 1),
                                  key=lambda d: (abs(d), d))
            if is_fundamental_discriminant(D)]


def squarefree_part(D):
    D = ZZ(D)
    return D if D % 4 == 1 else D // 4


def field_name(D):
    d = squarefree_part(D)
    if d == -1:
        return r"\mathbb{Q}(i)"
    return r"\mathbb{Q}(\sqrt{%d})" % d


def _field_and_series_ring(digits):
    bits = numberdb.bits(digits, losing=WORKING_GUARD)
    if bits not in _RING_CACHE:
        field = ComplexBallField(bits)
        ring = PolynomialRing(field, "t")
        _RING_CACHE[bits] = (field, ring, ring.gen())
    return _RING_CACHE[bits]


def _l_series_at_one(D, digits):
    """Return L(1, chi_D) and L'(1, chi_D) as complex balls."""
    field, ring, t = _field_and_series_ring(digits)
    N = abs(ZZ(D))
    total = ring(0)
    point = field(1) + t
    for a in range(1, int(N) + 1):
        chi = kronecker_symbol(D, a)
        if chi:
            total += chi * point._zeta_series(
                2, field(QQ(a) / QQ(N)), True)

    log_N = field(N).log()
    # N^(-1-t) = N^-1 (1 - log(N) t + O(t^2)).
    factor = field(1) / field(N) * (ring(1) - log_N * t)
    series = (factor * total).truncate(2)
    return series[0], series[1]


def _real(value, label):
    if not value.real().is_finite() or not value.imag().is_finite():
        raise ArithmeticError("computed a non-finite ball for %s" % (label,))
    if not value.imag().contains_zero():
        raise ArithmeticError("expected a real value for %s" % (label,))
    return value.real()


def _complex_finite(value):
    return value.real().is_finite() and value.imag().is_finite()


def euler_kronecker(D, digits):
    L1, Lprime = _l_series_at_one(D, digits)
    if not (_complex_finite(L1) and _complex_finite(Lprime)):
        raise ArithmeticError("non-finite L-series ball for D = %s" % D)
    field = ComplexBallField(numberdb.bits(digits, losing=WORKING_GUARD))
    real_field = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
    gamma = field(real_field.euler_constant())
    return _real(gamma + Lprime / L1, "gamma_K for D = %s" % D)


def _comment(D):
    D = ZZ(D)
    if D == -4:
        return (r"$\mathbb{Q}(i)$; "
                r"$2\gamma+2\log 2+3\log\pi-4\log\Gamma(1/4)$.")
    return "$%s$." % field_name(D)


class EulerKroneckerQuadraticFields(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T230")
    parameters = ("D",)
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self, bound=BOUND):
        for D in fundamental_discriminants(bound):
            yield {"D": int(D)}

    def value(self, params, digits):
        D = ZZ(params["D"])
        return {"number": euler_kronecker(D, digits), "comment": _comment(D)}


def fill_draft_once(generator, message):
    """Fill a fresh draft without the empty upsert probe.

    Generator.publish() first sends an empty upsert as a writeability check.
    A draft created with no Numbers section can reject that harmless probe
    while rebuilding its search rows, so this sends the complete non-empty
    block once and still uses the package's entry formatting and source
    attachment.
    """
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
    generator = EulerKroneckerQuadraticFields()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="Euler-Kronecker constants of quadratic fields"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
