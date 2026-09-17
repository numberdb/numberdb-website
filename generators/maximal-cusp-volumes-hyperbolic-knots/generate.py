r"""Maximal cusp volumes of hyperbolic prime knots -- numberdb.org/T316

For every hyperbolic prime knot K = n_k of the Rolfsen table with at most ten
crossings, this draft stores the volume of the maximal cusp of S^3 \ K. The
knot exterior is built from KnotInfo's braid word, not from SnapPy's built-in
Rolfsen name, because the neighboring knot tables use KnotInfo's after-Perko
numbering.

Run it with SageMath and SnapPy:

    $ sage -pip install numberdb snappy   # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The maximal cusp volume is half the area of the maximal horospherical torus in
the one-cusped complement. The values are computed by SnapPy's verified
cusp_areas method and checked against KnotInfo's maximum_cusp_volume column
from the public spreadsheet downloaded on 2026-09-17.
"""

import os
import re
import sys
from decimal import Decimal

import numberdb.sage as numberdb
from numberdb._compare import digits_of
from numberdb._write import to_text
import sage.symbolic.ring  # noqa: F401
from snappy import Link

from knotinfo_prime_knots import (
    KNOTINFO_BRAIDS,
    NAMED,
    TORUS,
    is_alternating,
    names,
    subscript,
)


TABLE = os.environ.get("NUMBERDB_TABLE", "T316")
WORKING_GUARD = 160
GEOMETRIC = "all tetrahedra positively oriented"

# KnotInfo's maximum_cusp_volume column from knotinfo_data_complete.xls,
# downloaded from https://knotinfo.org/homelinks/database_download.php on
# 2026-09-17. These are source checks only; the returned value is recomputed.
KNOTINFO_CUSP_VOLUMES = {
    (4, 1): "1.732050808",
    (5, 2): "1.973463516",
    (6, 1): "1.995452053",
    (6, 2): "2.882878368",
    (6, 3): "4.038066621",
    (7, 2): "1.998817633",
    (7, 3): "2.878339426",
    (7, 4): "3.538856255",
    (7, 5): "3.955453152",
    (7, 6): "4.447334995",
    (7, 7): "5.065554809",
    (8, 1): "1.999600977",
    (8, 2): "2.761873097",
    (8, 3): "3.546273373",
    (8, 4): "3.387434632",
    (8, 5): "4.570601651",
    (8, 6): "4.337088545",
    (8, 7): "3.830256465",
    (8, 8): "4.551728668",
    (8, 9): "5.181939455",
    (8, 10): "4.948574966",
    (8, 11): "5.00654735",
    (8, 12): "5.515651234",
    (8, 13): "4.95806026",
    (8, 14): "5.634795116",
    (8, 15): "6.219558884",
    (8, 16): "7.177619132",
    (8, 17): "7.250949677",
    (8, 18): "9.447477653",
    (8, 20): "2.677039848",
    (8, 21): "4.447880759",
    (9, 2): "1.999839617",
    (9, 3): "2.748613225",
    (9, 4): "3.376157636",
    (9, 5): "3.287842269",
    (9, 6): "3.737575388",
    (9, 7): "4.474972758",
    (9, 8): "4.584342628",
    (9, 9): "4.894706735",
    (9, 10): "5.556537628",
    (9, 11): "4.165777482",
    (9, 12): "4.816076403",
    (9, 13): "5.596681118",
    (9, 14): "4.768949766",
    (9, 15): "5.673391283",
    (9, 16): "5.901832692",
    (9, 17): "5.524447659",
    (9, 18): "5.583841432",
    (9, 19): "5.729655566",
    (9, 20): "5.3050394",
    (9, 21): "5.555841057",
    (9, 22): "5.609469989",
    (9, 23): "6.102772577",
    (9, 24): "6.35406353",
    (9, 25): "6.303897392",
    (9, 26): "5.911153234",
    (9, 27): "6.322088326",
    (9, 28): "7.113471366",
    (9, 29): "7.371436642",
    (9, 30): "6.919683872",
    (9, 31): "7.023806062",
    (9, 32): "6.996782896",
    (9, 33): "7.245595794",
    (9, 34): "8.681728495",
    (9, 35): "4.899510723",
    (9, 36): "4.907322585",
    (9, 37): "6.361299164",
    (9, 38): "7.847565034",
    (9, 39): "7.598767957",
    (9, 40): "10.81009997",
    (9, 41): "8.351372733",
    (9, 42): "2.363032105",
    (9, 43): "3.152719797",
    (9, 44): "4.099116088",
    (9, 45): "5.000385784",
    (9, 46): "3.274382056",
    (9, 47): "6.687008193",
    (9, 48): "6.153200536",
    (9, 49): "6.518814123",
    (10, 1): "1.999926941",
    (10, 2): "2.709581775",
    (10, 3): "3.277219664",
    (10, 4): "3.225693026",
    (10, 5): "3.678635289",
    (10, 6): "4.098806795",
    (10, 7): "4.679421627",
    (10, 8): "3.648369342",
    (10, 9): "4.749775952",
    (10, 10): "4.651176322",
    (10, 11): "5.381979852",
    (10, 12): "5.183587653",
    (10, 13): "5.379858945",
    (10, 14): "5.708017332",
    (10, 15): "4.272185956",
    (10, 16): "5.35321704",
    (10, 17): "5.814171397",
    (10, 18): "5.353107525",
    (10, 19): "5.973447458",
    (10, 20): "4.536286994",
    (10, 21): "5.411595954",
    (10, 22): "5.576825054",
    (10, 23): "6.113160452",
    (10, 24): "5.840201012",
    (10, 25): "6.671022863",
    (10, 26): "7.095615378",
    (10, 27): "6.87455807",
    (10, 28): "5.363038387",
    (10, 29): "5.983160174",
    (10, 30): "6.123354288",
    (10, 31): "5.822226437",
    (10, 32): "6.305726698",
    (10, 33): "7.563921173",
    (10, 34): "4.599796391",
    (10, 35): "5.589741902",
    (10, 36): "5.602789911",
    (10, 37): "6.056148413",
    (10, 38): "6.049708804",
    (10, 39): "6.189752936",
    (10, 40): "7.277054996",
    (10, 41): "6.648860842",
    (10, 42): "7.45713276",
    (10, 43): "7.306365877",
    (10, 44): "7.30023023",
    (10, 45): "7.965675353",
    (10, 46): "4.465801628",
    (10, 47): "4.803282777",
    (10, 48): "5.984339607",
    (10, 49): "6.133250882",
    (10, 50): "6.098304198",
    (10, 51): "7.128128785",
    (10, 52): "6.85900825",
    (10, 53): "7.124075976",
    (10, 54): "4.919713854",
    (10, 55): "6.390615963",
    (10, 56): "6.172513863",
    (10, 57): "7.346979109",
    (10, 58): "6.730189329",
    (10, 59): "7.150058199",
    (10, 60): "7.828634646",
    (10, 61): "4.95193178",
    (10, 62): "5.150367684",
    (10, 63): "6.265340369",
    (10, 64): "6.213795342",
    (10, 65): "6.488605407",
    (10, 66): "7.331200823",
    (10, 67): "6.319027518",
    (10, 68): "5.6884191",
    (10, 69): "7.948534176",
    (10, 70): "6.537062028",
    (10, 71): "7.407701996",
    (10, 72): "7.013902616",
    (10, 73): "7.733838532",
    (10, 74): "6.522540375",
    (10, 75): "7.916875286",
    (10, 76): "6.517226766",
    (10, 77): "6.937138542",
    (10, 78): "7.194155784",
    (10, 79): "7.869607006",
    (10, 80): "7.326246082",
    (10, 81): "8.41004779",
    (10, 82): "7.253722675",
    (10, 83): "8.527786165",
    (10, 84): "7.442272741",
    (10, 85): "7.030087649",
    (10, 86): "8.801783345",
    (10, 87): "7.007688983",
    (10, 88): "8.543810679",
    (10, 89): "8.45285303",
    (10, 90): "7.669041933",
    (10, 91): "7.946395173",
    (10, 92): "7.452590049",
    (10, 93): "7.133013745",
    (10, 94): "7.3756905",
    (10, 95): "7.668547313",
    (10, 96): "8.017805403",
    (10, 97): "7.584367235",
    (10, 98): "8.552705969",
    (10, 99): "8.783716014",
    (10, 100): "7.88977197",
    (10, 101): "7.226122906",
    (10, 102): "7.550001548",
    (10, 103): "8.598367373",
    (10, 104): "8.910944384",
    (10, 105): "7.951634207",
    (10, 106): "8.525792212",
    (10, 107): "8.070343563",
    (10, 108): "8.014761916",
    (10, 109): "9.380627866",
    (10, 110): "8.688655226",
    (10, 111): "7.774540093",
    (10, 112): "9.478196833",
    (10, 113): "8.410847311",
    (10, 114): "9.80578387",
    (10, 115): "9.955525405",
    (10, 116): "9.936883453",
    (10, 117): "9.15165626",
    (10, 118): "9.66045165",
    (10, 119): "8.960135477",
    (10, 120): "9.469486194",
    (10, 121): "9.985170995",
    (10, 122): "10.81134277",
    (10, 123): "12.44949142",
    (10, 125): "2.972314905",
    (10, 126): "4.072219312",
    (10, 127): "4.903063669",
    (10, 128): "2.991091718",
    (10, 129): "5.001494343",
    (10, 130): "3.552387185",
    (10, 131): "5.515098866",
    (10, 132): "2.277288304",
    (10, 133): "3.948708643",
    (10, 134): "4.0431083",
    (10, 135): "5.683604687",
    (10, 136): "4.502434614",
    (10, 137): "4.95465117",
    (10, 138): "5.840999596",
    (10, 139): "3.713631446",
    (10, 140): "3.782482864",
    (10, 141): "4.890544111",
    (10, 142): "3.800881906",
    (10, 143): "5.292677066",
    (10, 144): "6.425854001",
    (10, 145): "3.213554034",
    (10, 146): "5.82366979",
    (10, 147): "5.050485524",
    (10, 148): "6.209884945",
    (10, 149): "7.196160266",
    (10, 150): "5.72952087",
    (10, 151): "6.997312337",
    (10, 152): "5.923815149",
    (10, 153): "5.148123856",
    (10, 154): "5.974363241",
    (10, 155): "6.488128446",
    (10, 156): "6.143681484",
    (10, 157): "8.394390627",
    (10, 158): "7.264142254",
    (10, 159): "7.778262251",
    (10, 160): "5.482489159",
    (10, 161): "3.438911764",
    (10, 162): "6.894366887",
    (10, 163): "7.887024343",
    (10, 164): "7.768581067",
    (10, 165): "6.566098629",
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def hyperbolic_names():
    keys = [key for key in names() if key in KNOTINFO_CUSP_VOLUMES]
    if len(keys) != 243:
        raise ArithmeticError("expected 243 hyperbolic knots, got %d" % len(keys))
    if set(keys) != set(KNOTINFO_BRAIDS) - set(TORUS):
        raise ArithmeticError("the cusp-volume source and braid table name different hyperbolic knots")
    return keys


def _decimal_places(text):
    found = re.search(r"\.(\d+)$", text)
    return len(found.group(1)) if found else 0


def _source_interval(text):
    centre = Decimal(text)
    places = _decimal_places(text)
    radius = Decimal(5) * (Decimal(10) ** Decimal(-places if places else -8))
    return centre - radius, centre + radius


def _source_contains(computed_text, source_text):
    value = Decimal(computed_text)
    low, high = _source_interval(source_text)
    return low <= value <= high


def _exterior(n, k):
    strands, word = KNOTINFO_BRAIDS[(n, k)]
    manifold = Link(braid_closure=[int(letter) for letter in word]).exterior()
    for _attempt in range(50):
        if manifold.solution_type() == GEOMETRIC:
            return manifold
        manifold.randomize()
    raise ArithmeticError("%d_%d: no geometric triangulation found" % (n, k))


def _maximal_cusp_volume(n, k, digits):
    bits = numberdb.bits(digits, losing=WORKING_GUARD)
    try:
        areas = _exterior(n, k).cusp_areas(verified=True, bits_prec=bits)
    except Exception as error:
        raise ArithmeticError("%d_%d: verified cusp area failed: %s" % (n, k, error))
    if len(areas) != 1:
        raise ArithmeticError("%d_%d has %d cusps" % (n, k, len(areas)))
    return areas[0] / 2


def _entry_comment(n, k):
    parts = [subscript(n, k)]
    if (n, k) in NAMED:
        parts.append(NAMED[(n, k)])
    parts.append("alternating" if is_alternating(n, k) else "non-alternating")
    return "; ".join(parts)


class MaximalCuspVolumes(numberdb.Generator):

    table = TABLE
    parameters = ("n", "k")
    type = "R"
    digits = 100
    rigour = "proven"
    files = ("generate.py", "knotinfo_prime_knots.py")

    def enumerate(self):
        for n, k in hyperbolic_names():
            yield {"n": int(n), "k": int(k)}

    def value(self, params, digits):
        n, k = int(params["n"]), int(params["k"])
        if (n, k) not in KNOTINFO_CUSP_VOLUMES:
            raise ValueError("%d_%d is not a hyperbolic prime knot with at most ten crossings" % (n, k))
        value = _maximal_cusp_volume(n, k, digits)
        source = KNOTINFO_CUSP_VOLUMES[(n, k)]
        computed = to_text(value, digits=digits_of(source))
        if not _source_contains(computed, source):
            raise ArithmeticError(
                "%d_%d: SnapPy gives %s, KnotInfo gives %s"
                % (n, k, computed, source)
            )
        return {"number": value, "comment": _entry_comment(n, k)}


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
        asked = generator.digits_for(params)
        entry = generator._entry(params, asked)
        wanted = entry.get("digits", asked)
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
    generator = MaximalCuspVolumes()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="maximal cusp volumes of the 243 hyperbolic prime knots with at most ten crossings, checked against KnotInfo"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
