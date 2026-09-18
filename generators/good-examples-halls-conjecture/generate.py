"""Good examples of Hall's conjecture -- numberdb.org/T278.

    k = y^2 - x^3,  r = sqrt(x) / |k|

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The table stores the 54 examples listed by Wikipedia's Hall's conjecture page:
the integer x, the nearest integer y to x^(3/2), the signed Mordell constant
k = y^2 - x^3, and the Hall ratio r. Wikipedia gives x and a rounded r; y and
k are recomputed exactly from x. Elkies' independent list for x < 10^18 uses
the opposite sign for k, and is checked here after changing that sign.
"""

import os
import sys
from math import isqrt

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.real_arb import RealBallField


TABLE = os.environ.get("NUMBERDB_TABLE", "T278")
DIGITS = 30
WORKING_GUARD = 80


HALL_DATA = (
    (1, 2, "1.41"),
    (2, 5234, "4.26"),
    (3, 8158, "3.76"),
    (4, 93844, "1.03"),
    (5, 367806, "2.93"),
    (6, 421351, "1.05"),
    (7, 720114, "3.77"),
    (8, 939787, "3.16"),
    (9, 28187351, "4.87"),
    (10, 110781386, "1.23"),
    (11, 154319269, "1.08"),
    (12, 384242766, "1.34"),
    (13, 390620082, "1.33"),
    (14, 3790689201, "2.20"),
    (15, 65589428378, "2.19"),
    (16, 952764389446, "1.15"),
    (17, 12438517260105, "1.27"),
    (18, 35495694227489, "1.15"),
    (19, 53197086958290, "1.66"),
    (20, 5853886516781223, "46.60"),
    (21, 12813608766102806, "1.30"),
    (22, 23415546067124892, "1.46"),
    (23, 38115991067861271, "6.50"),
    (24, 322001299796379844, "1.04"),
    (25, 471477085999389882, "1.38"),
    (26, 810574762403977064, "4.66"),
    (27, 9870884617163518770, "1.90"),
    (28, 42532374580189966073, "3.47"),
    (29, 44648329463517920535, "1.79"),
    (30, 51698891432429706382, "1.75"),
    (31, 231411667627225650649, "3.71"),
    (32, 601724682280310364065, "1.88"),
    (33, 4996798823245299750533, "2.17"),
    (34, 5592930378182848874404, "1.38"),
    (35, 14038790674256691230847, "1.27"),
    (36, 77148032713960680268604, "10.18"),
    (37, 180179004295105849668818, "5.65"),
    (38, 372193377967238474960883, "1.33"),
    (39, 664947779818324205678136, "16.53"),
    (40, 2028871373185892500636155, "1.14"),
    (41, 10747835083471081268825856, "1.35"),
    (42, 37223900078734215181946587, "1.87"),
    (43, 69586951610485633367491417, "1.22"),
    (44, 3690445383173227306376634720, "1.51"),
    (45, 133545763574262054617147641349, "1.69"),
    (46, 162921297743817207342396140787, "10.65"),
    (47, 374192690896219210878121645171, "2.97"),
    (48, 401844774500818781164623821177, "1.29"),
    (49, 500859224588646106403669009291, "1.06"),
    (50, 1114592308630995805123571151844, "1.04"),
    (51, 39739590925054773507790363346813, "3.75"),
    (52, 862611143810724763613366116643858, "1.10"),
    (53, 1062521751024771376590062279975859, "1.006"),
    (54, 6078673043126084065007902175846955, "1.03"),
)


# Elkies lists k = x^3 - y^2, opposite to this table's convention.
ELKIES_DATA = (
    (5853886516781223, 1641843),
    (38115991067861271, 30032270),
    (28187351, -1090),
    (810574762403977064, -193234265),
    (5234, -17),
    (720114, -225),
    (8158, -24),
    (939787, 307),
    (367806, 207),
    (3790689201, -28024),
    (65589428378, -117073),
    (53197086958290, -4401169),
    (23415546067124892, 105077952),
    (2, -1),
    (471477085999389882, -497218657),
    (384242766, -14668),
    (390620082, -14857),
    (12813608766102806, -87002345),
    (12438517260105, 2767769),
    (110781386, -8569),
    (35495694227489, 5190544),
    (154319269, -11492),
    (421351, -618),
    (322001299796379844, 548147655),
    (93844, -297),
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


def _nearest_y(x):
    """The nearest integer to x^(3/2), using integer arithmetic only."""
    cube = x ** 3
    y = isqrt(cube)
    if (y + 1) ** 2 - cube < cube - y ** 2:
        y += 1
    return ZZ(y)


def _hall_parts(x):
    x = ZZ(x)
    y = _nearest_y(int(x))
    k = y ** 2 - x ** 3
    return x, y, ZZ(k)


def _source_ratio_parts(text):
    whole, _, fractional = text.partition(".")
    scale = 10 ** len(fractional)
    return int(whole + fractional), scale


def _ratio_rounds_to_source(x, k, source):
    """Check the source's rounded r without computing decimal digits."""
    numerator, scale = _source_ratio_parts(source)
    left = (2 * numerator - 1) ** 2 * int(k) ** 2
    middle = 4 * scale ** 2 * int(x)
    right = (2 * numerator + 1) ** 2 * int(k) ** 2
    return left <= middle < right


def _chowla_t3():
    """The Birch-Chowla-Hall-Schinzel family at t = 3."""
    t = ZZ(3)
    x = t * (t ** 9 + 6 * t ** 6 + 15 * t ** 3 + 12) // ZZ(9)
    k = (3 * t ** 6 + 14 * t ** 3 + 27) // ZZ(108)
    return x, k


def _check_data():
    """Exact checks against the source ratios and Elkies' independent list."""
    global _CHECKED
    if _CHECKED:
        return

    if len(HALL_DATA) != 54:
        raise ArithmeticError("expected 54 Hall examples")
    if [index for index, _x, _ratio in HALL_DATA] != list(range(1, 55)):
        raise ArithmeticError("the source row numbers are not consecutive")

    by_x = {}
    for index, x, source_ratio in HALL_DATA:
        if x in by_x:
            raise ArithmeticError("duplicate x in source list: %s" % x)
        by_x[x] = index
        _x, _y, k = _hall_parts(x)
        if k == 0:
            raise ArithmeticError("row %s has k = 0" % index)
        if not _ratio_rounds_to_source(x, k, source_ratio):
            raise ArithmeticError(
                "row %s with x = %s does not round to source ratio %s" %
                (index, x, source_ratio))

    row20 = _hall_parts(5853886516781223)
    if row20[1] != 447884928428402042307918 or row20[2] != -1641843:
        raise ArithmeticError("Elkies record row does not reproduce")

    row22 = _hall_parts(23415546067124892)
    if row22[2] != 64 * row20[2]:
        raise ArithmeticError("the non-primitive row does not scale k by 64")

    chowla_x, chowla_k = _chowla_t3()
    if _hall_parts(chowla_x)[2] != chowla_k:
        raise ArithmeticError("Chowla's t = 3 example does not reproduce row 3")

    # Wikipedia says Elkies' own table omits its entry 16.
    omitted_by_elkies = 952764389446
    wikipedia_under_bound = {
        x for _index, x, _ratio in HALL_DATA
        if x < 10 ** 18 and x != omitted_by_elkies
    }
    elkies_x = {x for x, _k in ELKIES_DATA}
    if wikipedia_under_bound != elkies_x:
        raise ArithmeticError(
            "Wikipedia and Elkies list different x < 10^18 values: %s / %s" %
            (sorted(wikipedia_under_bound - elkies_x),
             sorted(elkies_x - wikipedia_under_bound)))
    for x, elkies_k in ELKIES_DATA:
        if _hall_parts(x)[2] != -ZZ(elkies_k):
            raise ArithmeticError(
                "Elkies gives k = %s for x = %s, but this convention gives %s" %
                (elkies_k, x, _hall_parts(x)[2]))

    _CHECKED = True


def _ratio(x, k, digits):
    field = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
    return field(x).sqrt() / field(abs(k))


def _entry_comment(x, part):
    if x == 2 and part == "r":
        return "Here $r=\\sqrt{2}$."
    if x == 5853886516781223 and part == "x":
        return "This row has the largest Hall ratio in the source list."
    if x == 23415546067124892 and part == "x":
        return (
            "This non-primitive example is obtained from the Elkies row "
            "$x=5853886516781223$ by multiplying $x$, $y$ and $k$ by "
            "$4$, $8$ and $64$."
        )
    return None


class GoodHallExamples(numberdb.Generator):

    table = TABLE
    parameters = ("x", "part")
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self):
        _check_data()
        for _index, x, _source_ratio in HALL_DATA:
            for part in ("x", "y", "k", "r"):
                yield {"x": str(x), "part": part}

    def value(self, params, digits):
        x, y, k = _hall_parts(int(params["x"]))
        part = params["part"]
        if part == "x":
            number = x
        elif part == "y":
            number = y
        elif part == "k":
            number = k
        elif part == "r":
            source = next(ratio for _i, listed_x, ratio in HALL_DATA
                          if listed_x == int(x))
            if not _ratio_rounds_to_source(x, k, source):
                raise ArithmeticError("r for x = %s no longer matches %s" %
                                      (x, source))
            number = _ratio(x, k, digits)
        else:
            raise ValueError("unknown part %s" % part)

        comment = _entry_comment(int(x), part)
        if comment:
            return {"number": number, "comment": comment}
        return number


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
    generator = GoodHallExamples()
    _check_data()

    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="Hall examples from the Wikipedia list, with y and k "
                    "recomputed exactly from x and r in ball arithmetic"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
