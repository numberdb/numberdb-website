"""Khovanov polynomials of the prime knots with at most ten crossings -- numberdb.org/T315

    q^(-a) t^(-b) Kh_K(q,t,T) in Z[q,t,T],

for the unknot 0_1, for every prime knot K = n_k of the Rolfsen table with
3 <= n <= 10 crossings, numbered after Perko, and for the mirror image of
each chiral one. The knot K is the one KnotInfo draws. The entry `mirror` is
its mirror image.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The source values are KnotInfo's unreduced integral Khovanov vectors from
database_knotinfo 2026.9.1. Each vector entry is
[modulus, rank, homological grading, quantum grading]. A modulus of 0 records
a free summand. A positive modulus records torsion, written as T to that
modulus. Each value is shifted in q and t so the lowest exponent of each is
zero; the removed exponents are recorded in the entry comment.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing

from knotinfo_khovanov_data import AMPHICHIRAL, KNOTINFO_KHOVANOV, names

ZQTT = PolynomialRing(ZZ, ("q", "t", "T"))
q, t, torsion_variable = ZQTT.gens()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def terms_from_vector(vector):
    """KnotInfo's Khovanov vector as {(q exponent, t exponent, T exponent): coefficient}."""
    terms = {}
    for item in vector:
        if len(item) != 4:
            raise ArithmeticError("Khovanov vector entry has %d components, not 4" % len(item))
        modulus, rank, homological, quantum = (ZZ(x) for x in item)
        if modulus == 1:
            raise ArithmeticError("modulus 1 appears in an integral Khovanov vector")
        if rank <= 0:
            raise ArithmeticError("rank %s is not positive" % rank)
        torsion = ZZ(0) if modulus == 0 else modulus
        key = (quantum, homological, torsion)
        terms[key] = terms.get(key, ZZ(0)) + rank
    return {key: coefficient for key, coefficient in terms.items() if coefficient}


def mirror_terms(terms):
    """The unreduced integral Khovanov polynomial of the mirror image."""
    out = {}
    for (quantum, homological, torsion), coefficient in terms.items():
        if torsion == 0:
            image = (-quantum, -homological, torsion)
        else:
            image = (-quantum, 1 - homological, torsion)
        out[image] = out.get(image, ZZ(0)) + coefficient
    return out


def shifted(terms):
    """Return the shifted polynomial and the q, t exponents removed."""
    if not terms:
        return ZQTT(0), (ZZ(0), ZZ(0))
    low_q = min(quantum for quantum, _homological, _torsion in terms)
    low_t = min(homological for _quantum, homological, _torsion in terms)
    low_T = min(torsion for _quantum, _homological, torsion in terms)
    if low_T != 0:
        raise ArithmeticError("Khovanov polynomial has lowest T exponent %s, not 0" % low_T)
    total = ZQTT(0)
    for (quantum, homological, torsion), coefficient in terms.items():
        total += (
            ZQTT(coefficient)
            * q ** (quantum - low_q)
            * t ** (homological - low_t)
            * torsion_variable ** torsion
        )
    return total, (low_q, low_t)


def jones_vector_to_terms(vector):
    """KnotInfo's Jones vector as {t exponent: coefficient}."""
    low_t, high_t = ZZ(vector[0]), ZZ(vector[1])
    coefficients = vector[2:]
    if len(coefficients) != int(high_t - low_t + 1):
        raise ArithmeticError("Jones vector has the wrong number of coefficients")
    return {
        low_t + index: ZZ(coefficient)
        for index, coefficient in enumerate(coefficients)
        if ZZ(coefficient)
    }


def khovanov_euler_characteristic(terms):
    """The q-graded Euler characteristic of the free part."""
    out = {}
    for (quantum, homological, torsion), coefficient in terms.items():
        if torsion != 0:
            continue
        sign = -1 if homological % 2 else 1
        out[quantum] = out.get(quantum, ZZ(0)) + sign * coefficient
    return {exponent: coefficient for exponent, coefficient in out.items() if coefficient}


def unreduced_jones_characteristic(jones_terms):
    """(q + q^-1) V(q^2), as a dictionary in q exponents."""
    out = {}
    for exponent, coefficient in jones_terms.items():
        for shift in (-1, 1):
            q_exponent = 2 * exponent + shift
            out[q_exponent] = out.get(q_exponent, ZZ(0)) + coefficient
    return {exponent: coefficient for exponent, coefficient in out.items() if coefficient}


def reciprocal_jones(jones_terms):
    return {-exponent: coefficient for exponent, coefficient in jones_terms.items()}


def check_euler_characteristic(n, k, terms, jones_terms):
    got = khovanov_euler_characteristic(terms)
    expected = unreduced_jones_characteristic(jones_terms)
    if got != expected:
        raise ArithmeticError(
            "%d_%d: Khovanov Euler characteristic gives %s, not %s"
            % (n, k, got, expected)
        )


def comment(lows):
    parts = []
    if lows[0] != 0:
        parts.append("a=%s" % lows[0])
    if lows[1] != 0:
        parts.append("b=%s" % lows[1])
    return "$%s$" % ", ".join(parts) if parts else ""


class KhovanovPolynomials(numberdb.Generator):

    table = "T315"
    parameters = ("n", "k", "knot")
    type = "Z[]"
    rigour = "exact"
    files = ("generate.py", "knotinfo_khovanov_data.py")

    _knots = None

    def enumerate(self):
        for n, k in names():
            yield {"n": int(n), "k": int(k), "knot": "K"}
            if (n, k) != (0, 1) and (n, k) not in AMPHICHIRAL:
                yield {"n": int(n), "k": int(k), "knot": "mirror"}

    def knot(self, n, k):
        record = KNOTINFO_KHOVANOV[(n, k)]
        terms = terms_from_vector(record["khovanov"])
        mirror = mirror_terms(terms)

        jones = jones_vector_to_terms(record["jones"])
        check_euler_characteristic(n, k, terms, jones)
        check_euler_characteristic(n, k, mirror, reciprocal_jones(jones))

        if (n, k) in AMPHICHIRAL and mirror != terms:
            raise ArithmeticError("%d_%d is amphichiral, but the mirror polynomial differs" % (n, k))
        return terms, mirror

    def all_knots(self):
        if self._knots is None:
            self._knots = {(n, k): self.knot(n, k) for n, k in names()}
        return self._knots

    def value(self, params, digits):
        n, k = int(params["n"]), int(params["k"])
        image = params["knot"]
        if image not in ("K", "mirror"):
            raise ValueError("knot is 'K' or 'mirror', not %r" % image)
        if image == "mirror" and ((n, k) == (0, 1) or (n, k) in AMPHICHIRAL):
            raise ValueError("%d_%d is its own mirror image and has one entry" % (n, k))

        terms, mirror = self.all_knots()[(n, k)]
        polynomial, lows = shifted(terms if image == "K" else mirror)
        entry = {"number": polynomial}
        note = comment(lows)
        if note:
            entry["comment"] = note
        return entry


def fill_draft_once(generator, message):
    """Fill a fresh draft without the client's empty upsert probe."""
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

    stored = []
    for name, body in sorted(_source_files(generator).items()):
        attach(table, name, body, run=run, message=message, rigour=generator.rigour)
        stored.append(name)

    return {
        "tid": answer.get("tid", table),
        "revision": answer.get("revision"),
        "entries": len(entries),
        "files": stored,
    }


if __name__ == "__main__":
    _key_from_stdin()
    generator = KhovanovPolynomials()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="unreduced integral Khovanov polynomials of the unknot, the prime knots with at most ten crossings as KnotInfo draws them, and the mirror images of the chiral ones"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
