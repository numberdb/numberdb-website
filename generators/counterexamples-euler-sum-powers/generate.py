"""Counterexamples to Euler's sum of powers conjecture -- numberdb.org/T280.

    a_1^k + ... + a_(k-1)^k = b^k

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The table stores exact integer parts of the primitive fourth-power examples
listed by OEIS A003828 up to its stated search bound, and the four known
primitive fifth-power examples listed by Wikipedia and Braun. The fifth-power
rows allow signed summands, following those sources.
"""

import os
import sys
from math import gcd, isqrt, lcm

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ


TABLE = os.environ.get("NUMBERDB_TABLE", "T280")


# Tuples are (a1, a2, a3, b), ordered by the source's increasing b.
QUARTIC_SOLUTIONS = (
    (95800, 217519, 414560, 422481),
    (673865, 1390400, 2767624, 2813001),
    (1705575, 5507880, 8332208, 8707481),
    (5870000, 8282543, 11289040, 12197457),
    (4479031, 12552200, 14173720, 16003017),
    (3642840, 7028600, 16281009, 16430513),
    (2682440, 15365639, 18796760, 20615673),
    (2164632, 31669120, 41084175, 44310257),
    (10409096, 42878560, 65932985, 68711097),
    (34918520, 87865617, 106161120, 117112081),
    (1841160, 121952168, 122055375, 145087793),
    (27450160, 108644015, 146627384, 156646737),
    (186668000, 260052385, 582665296, 589845921),
    (219076465, 275156240, 630662624, 638523249),
    (558424440, 606710871, 769321280, 873822121),
    (588903336, 859396455, 1166705840, 1259768473),
    (50237800, 632671960, 1670617271, 1679142729),
    (686398000, 1237796960, 1662997663, 1787882337),
    (92622401, 1553556440, 1593513080, 1871713857),
)


# The OEIS A003828 b-file, transcribed separately from the triples above.
OEIS_A003828_B_FILE = (
    422481,
    2813001,
    8707481,
    12197457,
    16003017,
    16430513,
    20615673,
    44310257,
    68711097,
    117112081,
    145087793,
    156646737,
    589845921,
    638523249,
    873822121,
    1259768473,
    1679142729,
    1787882337,
    1871713857,
)


# Tuples are (a1, a2, a3, a4, b), ordered by b. The summands are sorted by
# integer value, so the two signed examples put their negative term first.
FIFTH_POWER_SOLUTIONS = (
    (27, 84, 110, 133, 144),
    (-220, 5027, 6237, 14068, 14132),
    (55, 3183, 28969, 85282, 85359),
    (-1340632, 719115, 1331622, 1956213, 1956878),
)


_CHECKED = False


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _gcd_many(values):
    common = 0
    for value in values:
        common = gcd(common, abs(int(value)))
    return common


def _solution_records():
    for a1, a2, a3, b in QUARTIC_SOLUTIONS:
        yield 4, (a1, a2, a3), b
    for a1, a2, a3, a4, b in FIFTH_POWER_SOLUTIONS:
        yield 5, (a1, a2, a3, a4), b


def _by_identity():
    return {(k, b): terms for k, terms, b in _solution_records()}


def _check_identity(k, terms, b):
    if len(terms) != k - 1:
        raise ArithmeticError("%s has %s summands" % ((k, terms, b), len(terms)))
    if tuple(sorted(terms)) != tuple(terms):
        raise ArithmeticError("%s summands are not sorted by value" % ((k, b),))
    if any(term == 0 for term in terms):
        raise ArithmeticError("%s has a zero summand" % ((k, terms, b),))
    if k == 4 and any(term <= 0 for term in terms):
        raise ArithmeticError("%s has a nonpositive fourth-power summand" %
                              ((k, terms, b),))
    if any(left == -right for left in terms for right in terms if left != right):
        raise ArithmeticError("%s has a cancelling pair of summands" %
                              ((k, terms, b),))

    left = sum(ZZ(term) ** k for term in terms)
    right = ZZ(b) ** k
    if left != right:
        raise ArithmeticError("%s does not satisfy the power identity" %
                              ((k, terms, b),))
    if _gcd_many(tuple(terms) + (b,)) != 1:
        raise ArithmeticError("%s is not primitive" % ((k, terms, b),))


def _sqrt_rational_square(value):
    numerator = ZZ(value.numerator())
    denominator = ZZ(value.denominator())
    root_num = isqrt(int(numerator))
    root_den = isqrt(int(denominator))
    if root_num ** 2 != numerator or root_den ** 2 != denominator:
        raise ArithmeticError("%s is not a rational square" % value)
    return QQ(root_num) / QQ(root_den)


def _clear_and_primitive(values):
    denominator = 1
    for value in values:
        denominator = lcm(denominator, int(value.denominator()))
    integers = tuple(ZZ(value * denominator) for value in values)
    common = _gcd_many(integers)
    return tuple(ZZ(value // common) for value in integers)


def _elkies_v_minus_31_over_467():
    """Elkies' parametrisation at v = -31/467, reduced to integers."""
    v = -QQ(31) / QQ(467)
    u_squared = (QQ(22030) + QQ(28849) * v - QQ(56158) * v ** 2
                 + QQ(36941) * v ** 3 - QQ(31790) * v ** 4)
    u = _sqrt_rational_square(u_squared)
    a = QQ(85) * v ** 2 + QQ(484) * v - QQ(313)
    b = QQ(68) * v ** 2 - QQ(586) * v + QQ(10)
    c = QQ(2) * u
    d = QQ(357) * v ** 2 - QQ(204) * v + QQ(363)
    integers = _clear_and_primitive((a, b, c, d))
    return tuple(sorted(abs(int(value)) for value in integers[:3])), abs(int(integers[3]))


def _check_data():
    global _CHECKED
    if _CHECKED:
        return

    quartic_b = tuple(row[-1] for row in QUARTIC_SOLUTIONS)
    if quartic_b != OEIS_A003828_B_FILE:
        raise ArithmeticError("quartic b values do not match OEIS A003828")
    if list(quartic_b) != sorted(quartic_b):
        raise ArithmeticError("quartic rows are not ordered by b")

    fifth_b = tuple(row[-1] for row in FIFTH_POWER_SOLUTIONS)
    if fifth_b != (144, 14132, 85359, 1956878):
        raise ArithmeticError("fifth-power target values changed")
    if list(fifth_b) != sorted(fifth_b):
        raise ArithmeticError("fifth-power rows are not ordered by b")

    identities = set()
    for k, terms, b in _solution_records():
        identity = (k, b)
        if identity in identities:
            raise ArithmeticError("duplicate identity %s" % (identity,))
        identities.add(identity)
        _check_identity(k, terms, b)

    elkies_terms, elkies_b = _elkies_v_minus_31_over_467()
    if (elkies_terms, elkies_b) != ((2682440, 15365639, 18796760), 20615673):
        raise ArithmeticError("Elkies' parametrisation check failed")

    _CHECKED = True


class EulerSumPowersCounterexamples(numberdb.Generator):

    table = TABLE
    parameters = ("k", "b", "part")
    type = "Z"
    rigour = "exact"

    def enumerate(self):
        _check_data()
        for k, terms, b in _solution_records():
            for index in range(len(terms)):
                yield {"k": str(k), "b": str(b), "part": "a%d" % (index + 1)}
            yield {"k": str(k), "b": str(b), "part": "b"}

    def value(self, params, digits):
        _check_data()
        k = int(params["k"])
        b = int(params["b"])
        terms = _by_identity()[(k, b)]
        part = params["part"]
        if part == "b":
            return ZZ(b)
        if part.startswith("a"):
            index = int(part[1:]) - 1
            if not 0 <= index < len(terms):
                raise ValueError("part %s is not present for k=%s" % (part, k))
            return ZZ(terms[index])
        raise ValueError("unknown part %s" % part)


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
        attach(table, name, body, run=run, message=message,
               rigour=generator.rigour)

    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = EulerSumPowersCounterexamples()
    _check_data()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="exact Euler sum-of-powers counterexample parts"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
