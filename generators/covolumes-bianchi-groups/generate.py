r"""Covolumes of the Bianchi groups -- numberdb.org/T221

    Vol(PSL_2(O_K) \ H^3),

where K is the imaginary quadratic field of fundamental discriminant D < 0.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The values are computed from Humbert's formula

    Vol = |D|^(3/2) L(2, chi_D) / 24.

The generator evaluates the Dirichlet L-value with arb's Hurwitz zeta
function. The private identity check compares every row with the finite
Clausen sum

    Vol = |D|/24 sum_{a=1}^{|D|-1} chi_D(a) Cl_2(2*pi*a/|D|),

computed with arb's complex polylogarithm.
"""

import os
import sys
from math import gcd, isqrt

import numberdb.sage as numberdb
from sage.arith.misc import fundamental_discriminant, kronecker_symbol
from sage.rings.complex_arb import ComplexBallField
from sage.rings.real_arb import RealBallField


BOUND = 1000
EXPECTED_DISCRIMINANTS = 305
WORKING_GUARD = 96
CHECK_GUARD = 128


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def discriminants(bound=BOUND):
    found = [
        D for D in range(-3, -bound - 1, -1)
        if fundamental_discriminant(D) == D
    ]
    found.sort(key=abs)
    if bound == BOUND and len(found) != EXPECTED_DISCRIMINANTS:
        raise ArithmeticError(
            "found %d negative fundamental discriminants, expected %d"
            % (len(found), EXPECTED_DISCRIMINANTS)
        )
    return found


def squarefree_d(D):
    if D % 4 == 0:
        return -D // 4
    return -D


def class_number(D):
    """Class number of the imaginary quadratic field of discriminant D.

    For fundamental D < 0 this is the number of reduced primitive positive
    definite binary quadratic forms of discriminant D.
    """
    if D >= 0:
        raise ValueError("D must be negative")
    count = 0
    limit = isqrt((-D) // 3) + 2
    for a in range(1, limit + 1):
        for b in range(-a, a + 1):
            numerator = b * b - D
            denominator = 4 * a
            if numerator % denominator:
                continue
            c = numerator // denominator
            if a > c:
                continue
            if (abs(b) == a or a == c) and b < 0:
                continue
            if gcd(gcd(a, abs(b)), c) != 1:
                continue
            count += 1
    return count


def volume_hurwitz(D, bits):
    q = -int(D)
    RB = RealBallField(bits)
    s = RB(2)
    total = RB(0)
    for a in range(1, q + 1):
        chi = kronecker_symbol(D, a)
        if chi:
            total += RB(chi) * s.zeta(RB(a) / RB(q))
    L_value = total / (RB(q) * RB(q))
    return RB(q) * RB(q).sqrt() * L_value / RB(24)


def cl2(t, CB):
    z = (CB(0, 1) * CB(t.parent().pi()) * CB(t)).exp()
    return z.polylog(2).imag()


def volume_clausen(D, bits):
    q = -int(D)
    RB = RealBallField(bits)
    CB = ComplexBallField(bits)
    total = RB(0)
    for a in range(1, q):
        chi = kronecker_symbol(D, a)
        if chi:
            total += RB(chi) * cl2(RB(2) * RB(a) / RB(q), CB)
    return RB(q) * total / RB(24)


def decimal_enclosure(text, RB):
    """The NumberDB plain-decimal interval for a stored real string."""
    mantissa = text.lower().split("e", 1)[0]
    if "." not in mantissa:
        return RB(text)
    places = len(mantissa.split(".", 1)[1])
    radius = RB(10) ** (-places)
    return RB(text).add_error(radius)


def entry_comment(D):
    h = class_number(D)
    cusp_word = "cusp" if h == 1 else "cusps"
    return (
        "$K=\\mathbb{Q}(\\sqrt{-%d})$; class number $h_K=%d$, so the "
        "Bianchi orbifold has %d %s."
        % (squarefree_d(D), h, h, cusp_word)
    )


def check_identities(digits=100):
    from sage.libs.pari import pari

    bits = numberdb.bits(digits, losing=CHECK_GUARD)
    widest = None
    for D in discriminants():
        hurwitz = volume_hurwitz(D, bits)
        clausen = volume_clausen(D, bits)
        difference = hurwitz - clausen
        if not difference.contains_zero():
            raise ArithmeticError(
                "Hurwitz and Clausen computations disagree at D=%d: %s"
                % (D, difference)
            )
        width = difference.diameter()
        if widest is None or width > widest[0]:
            widest = (width, D, difference)

        h = class_number(D)
        expected_h = int(pari.qfbclassno(D))
        if h != expected_h:
            raise ArithmeticError(
                "class number mismatch at D=%d: %d here, %d from PARI"
                % (D, h, expected_h)
            )

    bits = numberdb.bits(digits, losing=CHECK_GUARD)
    RB = RealBallField(bits)
    figure_eight = volume_hurwitz(-3, bits) * RB(12)
    catalan_over_three = volume_hurwitz(-4, bits) * RB(3)
    knot_table = numberdb.table("T141")
    figure_eight_stored = decimal_enclosure(
        knot_table["Numbers"]["4"]["1"]["number"], RB)
    if not (figure_eight - figure_eight_stored).contains_zero():
        raise ArithmeticError(
            "12 * Vol(D=-3) does not overlap the stored figure-eight volume")

    clausen_table = numberdb.table("T175")
    catalan_stored = decimal_enclosure(
        clausen_table["Numbers"]["2"]["1/2"]["number"], RB)
    if not (catalan_over_three - catalan_stored).contains_zero():
        raise ArithmeticError(
            "3 * Vol(D=-4) does not overlap the stored Catalan constant")

    print("checked %d discriminants" % EXPECTED_DISCRIMINANTS)
    print("widest Hurwitz-Clausen difference at D=%d: %s" % (widest[1], widest[2]))
    print("12 * Vol(D=-3) = %s" % figure_eight)
    print("3 * Vol(D=-4) = %s" % catalan_over_three)


class BianchiCovolumes(numberdb.Generator):
    table = os.environ.get("NUMBERDB_TABLE") or "T221"
    parameters = ("D",)
    type = "R"
    digits = 100
    rigour = "proven"
    files = ("generate.py",)

    def enumerate(self):
        for D in discriminants():
            yield {"D": str(D)}

    def value(self, params, digits):
        D = int(params["D"])
        bits = numberdb.bits(digits, losing=WORKING_GUARD)
        return {"number": volume_hurwitz(D, bits), "comment": entry_comment(D)}


def fill_draft_once(generator, message):
    """Fill a fresh draft without the empty upsert probe."""
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
    generator = BianchiCovolumes()
    if os.environ.get("NUMBERDB_CHECK_IDENTITIES") == "1":
        check_identities(generator.digits)
    elif "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="Bianchi group covolumes from Humbert's formula"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
