"""Best known packings of equal circles in an equilateral triangle -- numberdb.org/T449

For 2 <= n <= 15, this computes the proven optimal side length S_n of the
smallest equilateral triangle containing n non-overlapping unit circles, and
the equivalent point separation d_n in a unit-side equilateral triangle:

    S_n = 2*sqrt(3) + 2/d_n.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


TABLE = os.environ.get("NUMBERDB_TABLE") or "T449"
DIGITS = 100
WORKING_GUARD = 64
NORMALISATIONS = ("separation", "container")


def q(numerator, denominator=1):
    return QQ(ZZ(numerator)) / QQ(ZZ(denominator))


# Each term is (coefficient, radicand). A radicand of None means a rational
# constant. These are the side lengths printed in the source table.
CONTAINER_TERMS = {
    2: ((q(2), None), (q(2), 3)),
    3: ((q(2), None), (q(2), 3)),
    4: ((q(4), 3),),
    5: ((q(4), None), (q(2), 3)),
    6: ((q(4), None), (q(2), 3)),
    7: ((q(2), None), (q(4), 3)),
    8: ((q(2), None), (q(2), 3), (q(2, 3), 33)),
    9: ((q(6), None), (q(2), 3)),
    10: ((q(6), None), (q(2), 3)),
    11: ((q(4), None), (q(2), 3), (q(4, 3), 6)),
    12: ((q(4), None), (q(4), 3)),
    13: ((q(4), None), (q(10, 3), 3), (q(2, 3), 6)),
    14: ((q(8), None), (q(2), 3)),
    15: ((q(8), None), (q(2), 3)),
}

SOURCE_PREFIX = {
    2: "5.464",
    3: "5.464",
    4: "6.928",
    5: "7.464",
    6: "7.464",
    7: "8.928",
    8: "9.293",
    9: "9.464",
    10: "9.464",
    11: "10.730",
    12: "10.928",
    13: "11.406",
    14: "11.464",
    15: "11.464",
}

CONTAINER_LATEX = {
    2: r"$S_2=2+2\sqrt3$",
    3: r"$S_3=2+2\sqrt3$",
    4: r"$S_4=4\sqrt3$",
    5: r"$S_5=4+2\sqrt3$",
    6: r"$S_6=4+2\sqrt3$",
    7: r"$S_7=2+4\sqrt3$",
    8: r"$S_8=2+2\sqrt3+\frac{2}{3}\sqrt{33}$",
    9: r"$S_9=6+2\sqrt3$",
    10: r"$S_{10}=6+2\sqrt3$",
    11: r"$S_{11}=4+2\sqrt3+\frac{4}{3}\sqrt6$",
    12: r"$S_{12}=4+4\sqrt3$",
    13: r"$S_{13}=4+\frac{10}{3}\sqrt3+\frac{2}{3}\sqrt6$",
    14: r"$S_{14}=8+2\sqrt3$",
    15: r"$S_{15}=8+2\sqrt3$",
}

SEPARATION_LATEX = {
    2: r"$d_2=1$",
    3: r"$d_3=1$",
    4: r"$d_4=\sqrt3/3$",
    5: r"$d_5=1/2$",
    6: r"$d_6=1/2$",
    7: r"$d_7=(\sqrt3-1)/2$",
    8: r"$d_8=(\sqrt{33}-3)/8$",
    9: r"$d_9=1/3$",
    10: r"$d_{10}=1/3$",
    11: r"$d_{11}=(3-\sqrt6)/2$",
    12: r"$d_{12}=2-\sqrt3$",
    13: r"$d_{13}=3/(6+2\sqrt3+\sqrt6)$",
    14: r"$d_{14}=1/4$",
    15: r"$d_{15}=1/4$",
}

EXACT_SEPARATIONS = {
    2: q(1),
    3: q(1),
    5: q(1, 2),
    6: q(1, 2),
    9: q(1, 3),
    10: q(1, 3),
    14: q(1, 4),
    15: q(1, 4),
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def field(digits):
    return RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def container_side(n, digits):
    R = field(digits)
    total = R(0)
    for coefficient, radicand in CONTAINER_TERMS[n]:
        term = R(coefficient)
        if radicand is not None:
            term *= R(radicand).sqrt()
        total += term
    if not total.is_finite():
        raise ArithmeticError("non-finite side length for n=%s" % n)
    return total


def separation(n, digits):
    if n in EXACT_SEPARATIONS:
        return EXACT_SEPARATIONS[n]
    R = field(digits)
    side = container_side(n, digits)
    sep = R(2) / (side - R(2) * R(3).sqrt())
    if not sep.is_finite():
        raise ArithmeticError("non-finite separation for n=%s" % n)
    return sep


def value_for(n, normalisation, digits):
    if normalisation == "container":
        return container_side(n, digits)
    if normalisation == "separation":
        return separation(n, digits)
    raise ValueError("unknown normalisation %r" % (normalisation,))


def _comment(n, normalisation):
    formula = (CONTAINER_LATEX if normalisation == "container"
               else SEPARATION_LATEX)[n]
    return "%s. Optimality is proven by CITE{Melissen}." % formula


def _decimal_prefix_interval(prefix):
    digits = prefix.replace(".", "")
    scale = ZZ(10) ** (len(prefix) - prefix.index(".") - 1)
    lower = QQ(ZZ(digits)) / QQ(scale)
    return lower, lower + QQ(1) / QQ(scale)


def _contains_prefix(value, prefix):
    lower, upper = _decimal_prefix_interval(prefix)
    R = value.parent()
    return (value - R(lower)).lower() >= 0 and (R(upper) - value).lower() >= 0


def _same_ball(left, right, digits):
    R = field(digits)
    return (R(left) - R(right)).contains_zero()


def run_integrity_checks():
    R = field(DIGITS)
    root3 = R(3).sqrt()
    for n in sorted(CONTAINER_TERMS):
        side = container_side(n, DIGITS)
        if not _contains_prefix(side, SOURCE_PREFIX[n]):
            raise ArithmeticError("n=%s side length disagrees with source prefix" % n)

        sep = separation(n, DIGITS)
        if not _same_ball(side, R(2) * root3 + R(2) / R(sep), DIGITS):
            raise ArithmeticError("n=%s conversion from d_n to S_n failed" % n)

        if n in (3, 6, 10, 15):
            k = {3: 2, 6: 3, 10: 4, 15: 5}[n]
            if not _same_ball(side, R(2 * (k - 1)) + R(2) * root3, DIGITS):
                raise ArithmeticError("n=%s triangular-number side formula failed" % n)
            if sep != q(1, k - 1):
                raise ArithmeticError("n=%s triangular-number separation failed" % n)

    higher = {n: container_side(n, DIGITS + 30) for n in CONTAINER_TERMS}
    for n, side in higher.items():
        if not _same_ball(container_side(n, DIGITS), side, DIGITS):
            raise ArithmeticError("n=%s side length changed at higher precision" % n)


class EquilateralTriangleCirclePackings(numberdb.Generator):
    table = TABLE
    parameters = ("n", "normalisation")
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self):
        for n in sorted(CONTAINER_TERMS):
            for normalisation in NORMALISATIONS:
                yield {"n": str(n), "normalisation": normalisation}

    def value(self, params, digits):
        n = ZZ(params["n"])
        normalisation = params["normalisation"]
        return {
            "number": value_for(n, normalisation, digits),
            "comment": _comment(n, normalisation),
        }


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
    generator = EquilateralTriangleCirclePackings()
    run_integrity_checks()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="computed triangle circle packings from exact radicals"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
