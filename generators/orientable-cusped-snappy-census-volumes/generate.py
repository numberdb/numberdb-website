r"""Volumes of the orientable cusped SnapPea census manifolds -- numberdb.org/T225

    Vol(M), the volume of the complete finite-volume hyperbolic metric
    of curvature -1,

for the orientable cusped hyperbolic 3-manifolds M in the m part of SnapPy's
OrientableCuspedCensus.

Run it with SageMath:

    $ sage -pip install numberdb snappy
    $ sage -python generate.py
    $ sage -python generate.py --publish

The values are computed by SnapPy's verified volume method, which returns Sage
intervals containing the true volumes. The table stores the 301 census names
beginning with m, which is the original SnapPea census through five ideal
tetrahedra.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.real_arb import RealBallField
from snappy import Manifold, OrientableCuspedCensus


WORKING_GUARD = 64
EXPECTED_COUNT = 301


SPECIAL_COMMENTS = {
    "m003": "This manifold has the same volume as $m004$.",
    "m004": (
        "This is the figure-eight knot complement, the row $4_1$ in "
        "HREF{Hyperbolic_volumes_of_the_prime_knots_with_at_most_ten_crossings}"
        "[the table of prime-knot complement volumes]."
    ),
    "m009": "This manifold has the same volume as $m010$.",
    "m010": "This manifold has the same volume as $m009$.",
    "m129": (
        "This is the Whitehead link complement, also named $5^2_1$ in "
        "HREF{Hyperbolic_volumes_of_the_prime_knots_with_at_most_ten_crossings}"
        "[the table of prime-knot complement volumes]."
    ),
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def census_names():
    names = []
    seen = set()
    for manifold in OrientableCuspedCensus:
        name = manifold.name().split("(", 1)[0]
        if not name.startswith("m") or name in seen:
            continue
        seen.add(name)
        names.append(name)
    if len(names) != EXPECTED_COUNT:
        raise ArithmeticError(
            "found %d m-census names, expected %d" % (len(names), EXPECTED_COUNT)
        )
    return names


def homology_tex(manifold):
    text = str(manifold.homology())
    text = text.replace("Z", "\\mathbb{Z}")
    return text


def comment(name):
    manifold = Manifold(name)
    cusp_word = "cusp" if manifold.num_cusps() == 1 else "cusps"
    tetra_word = "tetrahedron" if manifold.num_tetrahedra() == 1 else "tetrahedra"
    pieces = [
        "%d %s" % (manifold.num_cusps(), cusp_word),
        "%d ideal %s" % (manifold.num_tetrahedra(), tetra_word),
        "first homology $%s$" % homology_tex(manifold),
    ]
    special = SPECIAL_COMMENTS.get(name)
    if special:
        pieces.append(special)
    return "; ".join(pieces) + "."


def verified_volume(name, digits):
    bits = numberdb.bits(digits, losing=WORKING_GUARD)
    return Manifold(name).volume(verified=True, bits_prec=bits)


def decimal_enclosure(text, RB):
    mantissa = text.lower().split("e", 1)[0]
    if "." not in mantissa:
        return RB(text)
    places = len(mantissa.split(".", 1)[1])
    radius = RB(10) ** (-places)
    return RB(text).add_error(radius)


def number_from_nested(table, *keys):
    node = table["Numbers"]
    for key in keys:
        node = node[key]
    return node["number"]


def check_identities(digits=100):
    bits = numberdb.bits(digits, losing=WORKING_GUARD)
    RB = RealBallField(bits)
    widest = None
    for name in census_names():
        interval = verified_volume(name, digits)
        approximate = RB(str(Manifold(name).high_precision().volume()))
        difference = RB(interval) - approximate
        if not difference.contains_zero():
            raise ArithmeticError(
                "%s: verified volume does not contain high-precision volume: %s"
                % (name, difference)
            )
        width = interval.absolute_diameter()
        if widest is None or width > widest[0]:
            widest = (width, name, interval)

    knot_table = numberdb.table("T141")
    bianchi_table = numberdb.table("T221")

    m004 = RB(verified_volume("m004", digits))
    figure_eight = decimal_enclosure(number_from_nested(knot_table, "4", "1"), RB)
    if not (m004 - figure_eight).contains_zero():
        raise ArithmeticError("m004 does not overlap the stored figure-eight volume")

    m009 = RB(verified_volume("m009", digits))
    m010 = RB(verified_volume("m010", digits))
    if not (m009 - m010).contains_zero():
        raise ArithmeticError("m009 and m010 do not overlap")
    bianchi_d7 = decimal_enclosure(number_from_nested(bianchi_table, "-7"), RB)
    if not (m009 - 3 * bianchi_d7).contains_zero():
        raise ArithmeticError("m009 is not three times the D=-7 Bianchi covolume")

    m129 = RB(verified_volume("m129", digits))
    bianchi_d4 = decimal_enclosure(number_from_nested(bianchi_table, "-4"), RB)
    if not (m129 - 12 * bianchi_d4).contains_zero():
        raise ArithmeticError("m129 is not twelve times the D=-4 Bianchi covolume")

    print("checked %d m-census manifolds" % EXPECTED_COUNT)
    print("widest verified volume at %s: %s" % (widest[1], widest[2]))
    print("m004 agrees with T141 4_1")
    print("m009 and m010 agree, and m009 = 3 * Bianchi D=-7")
    print("m129 = 12 * Bianchi D=-4")


class OrientableCuspedSnapPeaVolumes(numberdb.Generator):
    table = os.environ.get("NUMBERDB_TABLE") or "T225"
    parameters = ("name",)
    type = "R"
    digits = 100
    rigour = "proven"
    files = ("generate.py",)

    def enumerate(self):
        for name in census_names():
            yield {"name": name}

    def value(self, params, digits):
        name = str(params["name"])
        return {"number": verified_volume(name, digits), "comment": comment(name)}


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
    generator = OrientableCuspedSnapPeaVolumes()
    if os.environ.get("NUMBERDB_CHECK_IDENTITIES") == "1":
        check_identities(generator.digits)
    elif "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="orientable cusped SnapPea census volumes"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
