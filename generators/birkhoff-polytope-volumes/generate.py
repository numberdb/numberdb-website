"""Volumes of the Birkhoff polytopes -- numberdb.org/T236

For n = 1, ..., 10 this stores three exact rational normalisations of the
volume of the Birkhoff polytope B_n: relative, normalised, and Euclidean.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The normalised volume rows are transcribed from OEIS A037302. The relative
volume is the leading coefficient of the Ehrhart polynomial, obtained by
dividing the normalised volume by ((n - 1)^2)!. The Euclidean volume is
n^(n - 1) times the relative volume, because the zero-margin lattice has
Euclidean covolume n^(n - 1).
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.rational_field import QQ
from math import factorial


UP_TO_N = 10

NORMALISED_VOLUMES = {
    1: 1,
    2: 1,
    3: 3,
    4: 352,
    5: 4718075,
    6: 14666561365176,
    7: 17832560768358341943028,
    8: 12816077964079346687829905128694016,
    9: 7658969897501574748537755050756794492337074203099,
    10: 5091038988117504946842559205930853037841762820367901333706255223000,
}

EUCLIDEAN_NUMERATORS = {
    1: 1,
    2: 2,
    3: 9,
    4: 176,
    5: 23590375,
    6: 9700106723,
    7: 77436678274508929033,
    8: 5562533838576105333259507434329,
    9: 559498129702796022246895686372766052475496691,
    10: 727291284016786420977508457990121862548823260052557333386607889,
}

OEIS_EUCLIDEAN_DENOMINATORS = {
    1: 1,
    2: 1,
    3: 8,
    4: 2835,
    5: 167382319104,
    6: 1319281996032000000,
    7: 13730296368223523839986892800000000,
    8: 125890362600954779500814809426933398033089280000000000,
    9: 9269262340995263649896514671280698429605195132920241960610847715334553600000000000000,
    10: 828160860106766855125676318796872729344622463533089422677980721388055739956270293750883504892820848640000000,
}

CORRECTED_EUCLIDEAN_DENOMINATORS = dict(OEIS_EUCLIDEAN_DENOMINATORS)
CORRECTED_EUCLIDEAN_DENOMINATORS[9] = (
    215330276631180889478121101750832506606140689157723348094523801600000000000000
)

BECK_PIXTON_RELATIVE = {
    1: (1, 1),
    2: (1, 1),
    3: (1, 8),
    4: (11, 11340),
    5: (188723, 836911595520),
    6: (9700106723, 10258736801144832000000),
    7: (225762910421308831, 4709491654300668677115504230400000000),
    8: (5562533838576105333259507434329,
        264011225709317517739692779219312229551889249730560000000000),
    9: (559498129702796022246895686372766052475496691,
        9269262340995263649896514671280698429605195132920241960610847715334553600000000000000),
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def dimension(n):
    return (n - 1) ** 2


def relative_volume(n):
    return QQ(NORMALISED_VOLUMES[n]) / QQ(factorial(dimension(n)))


def normalised_volume(n):
    return QQ(NORMALISED_VOLUMES[n])


def euclidean_volume(n):
    return QQ(n) ** (n - 1) * relative_volume(n)


def source_checks():
    complaints = []
    for n in range(1, UP_TO_N + 1):
        oeis_pair = (
            QQ(EUCLIDEAN_NUMERATORS[n]) / QQ(OEIS_EUCLIDEAN_DENOMINATORS[n])
        )
        if n == 9:
            if oeis_pair != relative_volume(n):
                complaints.append(
                    "n=9: OEIS denominator no longer records the relative "
                    "volume exception")
            continue
        if euclidean_volume(n) != oeis_pair:
            complaints.append("n=%d: Euclidean volume disagrees with OEIS" % n)
    expected_nine = (
        QQ(EUCLIDEAN_NUMERATORS[9]) / QQ(CORRECTED_EUCLIDEAN_DENOMINATORS[9])
    )
    if euclidean_volume(9) != expected_nine:
        complaints.append("n=9: corrected Euclidean denominator is wrong")
    for n, (num, den) in BECK_PIXTON_RELATIVE.items():
        expected = QQ(num) / QQ(den)
        if relative_volume(n) != expected:
            complaints.append(
                "n=%d: relative volume disagrees with Beck-Pixton" % n)
    return complaints


class BirkhoffPolytopeVolumes(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T236")
    parameters = ("n", "normalisation")
    type = "Q"
    rigour = "exact"

    def enumerate(self, up_to_n=UP_TO_N):
        for n in range(1, up_to_n + 1):
            yield {"n": str(n), "normalisation": "relative"}
            yield {"n": str(n), "normalisation": "normalised"}
            yield {"n": str(n), "normalisation": "euclidean"}

    def value(self, params, digits):
        n = int(params["n"])
        normalisation = params["normalisation"]
        if normalisation == "relative":
            return {
                "number": relative_volume(n),
                "param-latex": r"$\operatorname{vol}_{\mathrm{rel}}(B_%d)$" % n,
            }
        if normalisation == "normalised":
            return {
                "number": normalised_volume(n),
                "param-latex": r"$\operatorname{Vol}(B_%d)$" % n,
            }
        if normalisation == "euclidean":
            return {
                "number": euclidean_volume(n),
                "param-latex": r"$\operatorname{vol}_{\mathrm{Euc}}(B_%d)$" % n,
            }
        raise ValueError("unknown normalisation %r" % (normalisation,))


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
    generator = BirkhoffPolytopeVolumes()
    complaints = source_checks()
    if complaints:
        for complaint in complaints:
            print(complaint)
        sys.exit(1)
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="Birkhoff polytope volumes"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
