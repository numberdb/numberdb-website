"""Markov forms -- numberdb.org/T429.

For each normalized Markov triple (m1,m2,m3), this stores Markov's binary
quadratic form

    m3*x^2 + (3*m3 - 2*k)*x*y + (l - 3*k)*y^2,

where 0 <= k <= m3/2 satisfies k*m2 = +/- m1 mod m3 and l = (k^2 + 1)/m3.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py --check    # run the independent checks
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The generator finds triples from (1,1,1) by Vieta involutions and keeps every
triple with m3 <= 10^12. The published rows are grouped by m1 because NumberDB
stores a multi-parameter table nested by its parameter order.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import gcd
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


TABLE = os.environ.get("NUMBERDB_TABLE", "T429")
MAX_M3 = 10 ** 12

R = PolynomialRing(ZZ, ("x", "y"))
X, Y = R.gens()

OEIS_TRIPLES = (
    (1, 1, 1),
    (1, 1, 2),
    (1, 2, 5),
    (1, 5, 13),
    (2, 5, 29),
    (1, 13, 34),
    (1, 34, 89),
    (2, 29, 169),
    (5, 13, 194),
    (1, 89, 233),
    (5, 29, 433),
    (1, 233, 610),
    (2, 169, 985),
    (13, 34, 1325),
    (1, 610, 1597),
    (5, 194, 2897),
    (1, 1597, 4181),
    (2, 985, 5741),
    (5, 433, 6466),
    (13, 194, 7561),
    (34, 89, 9077),
    (1, 4181, 10946),
    (29, 169, 14701),
)

OEIS_K = (
    0,
    1,
    2,
    5,
    12,
    13,
    34,
    70,
    75,
    89,
    179,
    233,
    408,
    507,
    610,
    1120,
    1597,
    2378,
    2673,
    2923,
    3468,
    4181,
    6089,
    10946,
    13860,
    15571,
    16725,
    19760,
    23763,
    28657,
    39916,
    51709,
    80782,
    75025,
    113922,
    162867,
    206855,
    196418,
    249755,
    353702,
)

EXPECTED_FIRST_FORMS = {
    (1, 1, 1): X ** 2 + 3 * X * Y + Y ** 2,
    (1, 1, 2): 2 * X ** 2 + 4 * X * Y - 2 * Y ** 2,
    (1, 2, 5): 5 * X ** 2 + 11 * X * Y - 5 * Y ** 2,
    (1, 5, 13): 13 * X ** 2 + 29 * X * Y - 13 * Y ** 2,
    (2, 5, 29): 29 * X ** 2 + 63 * X * Y - 31 * Y ** 2,
    (1, 13, 34): 34 * X ** 2 + 76 * X * Y - 34 * Y ** 2,
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip(chr(34)).strip(chr(39))
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def _mutations(triple):
    values = list(triple)
    for index in range(3):
        changed = list(values)
        other = [i for i in range(3) if i != index]
        changed[index] = 3 * changed[other[0]] * changed[other[1]] - changed[index]
        yield tuple(sorted(changed))


def markov_triples(limit=MAX_M3):
    """Normalized Markov triples with largest entry at most limit."""
    root = (ZZ(1), ZZ(1), ZZ(1))
    seen = {root}
    stack = [root]
    while stack:
        triple = stack.pop()
        for candidate in _mutations(triple):
            if candidate[0] <= 0 or candidate[2] > limit or candidate in seen:
                continue
            seen.add(candidate)
            stack.append(candidate)
    return sorted(seen, key=lambda triple: (triple[2], triple[1], triple[0]))


def markov_k(m1, m2, m3):
    """The representative 0 <= k <= m3/2 with k*m2 = +/- m1 mod m3."""
    m1, m2, m3 = ZZ(m1), ZZ(m2), ZZ(m3)
    if m3 == 1:
        return ZZ(0)
    residue = (m1 * ZZ(pow(int(m2), -1, int(m3)))) % m3
    k = min(residue, (-residue) % m3)
    if 2 * k > m3:
        raise ArithmeticError("selected k outside the closed range")
    return ZZ(k)


def markov_form(m1, m2, m3):
    m1, m2, m3 = ZZ(m1), ZZ(m2), ZZ(m3)
    k = markov_k(m1, m2, m3)
    numerator = k ** 2 + 1
    if numerator % m3 != 0:
        raise ArithmeticError("k^2 + 1 is not divisible by m3")
    ell = numerator // m3
    return m3 * X ** 2 + (3 * m3 - 2 * k) * X * Y + (ell - 3 * k) * Y ** 2


def _coefficients(form):
    return tuple(ZZ(coefficient) for coefficient in (
        form.monomial_coefficient(X ** 2),
        form.monomial_coefficient(X * Y),
        form.monomial_coefficient(Y ** 2),
    ))


def _check_row(triple):
    m1, m2, m3 = (ZZ(value) for value in triple)
    if not (0 < m1 <= m2 <= m3):
        raise ArithmeticError("triple is not normalized: %s" % (triple,))
    if m1 ** 2 + m2 ** 2 + m3 ** 2 != 3 * m1 * m2 * m3:
        raise ArithmeticError("Markov equation failed for %s" % (triple,))

    k = markov_k(m1, m2, m3)
    if ((k * m2 - m1) % m3 != 0) and ((k * m2 + m1) % m3 != 0):
        raise ArithmeticError("k congruence failed for %s" % (triple,))

    form = markov_form(m1, m2, m3)
    a, b, c = _coefficients(form)
    if b ** 2 - 4 * a * c != 9 * m3 ** 2 - 4:
        raise ArithmeticError("discriminant failed for %s" % (triple,))

    expected_content = ZZ(2) if m3 % 2 == 0 else ZZ(1)
    content = gcd(gcd(abs(a), abs(b)), abs(c))
    if content != expected_content:
        raise ArithmeticError(
            "content %s, expected %s for %s"
            % (content, expected_content, triple)
        )
    return form


def run_integrity_checks():
    triples = markov_triples()
    if len(triples) != 152:
        raise ArithmeticError("expected 152 triples, found %d" % len(triples))
    if tuple(tuple(int(v) for v in triple) for triple in triples[:len(OEIS_TRIPLES)]) != OEIS_TRIPLES:
        raise ArithmeticError("initial triples do not match OEIS A291694")

    k_values = tuple(int(markov_k(*triple)) for triple in triples[:len(OEIS_K)])
    if k_values != OEIS_K:
        raise ArithmeticError("initial k values do not match OEIS A305310")

    for triple in triples:
        form = _check_row(triple)
        expected = EXPECTED_FIRST_FORMS.get(tuple(int(v) for v in triple))
        if expected is not None and form != expected:
            raise ArithmeticError("displayed first form failed for %s" % (triple,))


class MarkovForms(numberdb.Generator):

    table = TABLE
    parameters = ("m1", "m2", "m3")
    type = "Z[]"
    rigour = "exact"

    def enumerate(self, limit=MAX_M3):
        triples = sorted(
            markov_triples(limit),
            key=lambda triple: (triple[0], triple[2], triple[1]),
        )
        for m1, m2, m3 in triples:
            yield {"m1": str(m1), "m2": str(m2), "m3": str(m3)}

    def value(self, params, digits):
        return markov_form(params["m1"], params["m2"], params["m3"])


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

    for name, body in sorted(_source_files(generator).items()):
        attach(table, name, body, run=run, message=message, rigour=generator.rigour)

    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = MarkovForms()
    run_integrity_checks()
    if "--check" in sys.argv or os.environ.get("NUMBERDB_CHECK") == "1":
        print("integrity checks passed for %d Markov forms" % len(markov_triples()))
    elif "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(generator, message="exact Markov forms"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
