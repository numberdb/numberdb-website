r"""Chern-Simons invariants of hyperbolic knot complements -- numberdb.org/T313

For every hyperbolic prime knot K = n_k of the Rolfsen table with at most ten
crossings, this draft stores the signed representative of
CS(S^3 \ K) in (-1/4, 1/4), and its 2*pi^2 multiple, for the knot as KnotInfo
draws it and for the mirror image of each chiral hyperbolic knot.

Run it with SageMath and SnapPy:

    $ sage -pip install numberdb snappy   # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The CS values are the Chern-Simons invariant normalised by 2*pi^2, matching
SnapPy's chern_simons() and KnotInfo's Chern-Simons invariant column. They are
defined modulo 1/2; this table uses the representative printed by KnotInfo and
returned by SnapPy, lying in (-1/4, 1/4). The second normalisation is the
unnormalised value 2*pi^2 CS, the imaginary part convention of SnapPy's complex
volume, computed from the printed CS value as an interval so it carries no more
precision than the source.

The exterior is built from KnotInfo's braid word, not from SnapPy's manifold
name, for the same reason as the neighboring knot tables: SnapPy's built-in
Rolfsen names use pre-Perko numbering for part of the ten-crossing table. Each
SnapPy value is checked against KnotInfo's printed value before the entry is
returned. The mirror entry is checked by computing the mirror exterior and by
the congruence CS(S^3 \ bar K) = -CS(S^3 \ K) mod 1/2.
"""

import os
import re
import sys
from decimal import Decimal

import numberdb.sage as numberdb
from numberdb._compare import digits_of
from numberdb._write import to_text
import sage.symbolic.ring  # noqa: F401
from sage.rings.real_arb import RealBallField
from snappy import Link

from knotinfo_prime_knots import (
    AMPHICHIRAL,
    KNOTINFO_BRAIDS,
    NAMED,
    TORUS,
    is_alternating,
    names,
    subscript,
)


TABLE = os.environ.get("NUMBERDB_TABLE", "T313")
WORKING_GUARD = 64

# Values from KnotInfo's chern_simons_invariant column, fetched on
# 2026-09-17. These are the signed representatives in (-1/4, 1/4).
KNOTINFO_CS = {
    (4, 1): "0",
    (5, 2): "-0.153204133",
    (6, 1): "0.155977017",
    (6, 2): "-0.202492498",
    (6, 3): "0",
    (7, 2): "-0.055153535",
    (7, 3): "0.187220178",
    (7, 4): "0.021726694",
    (7, 5): "0.120555869",
    (7, 6): "0.182283191",
    (7, 7): "0.1329856",
    (8, 1): "0.222133121",
    (8, 2): "0.212918515",
    (8, 3): "0",
    (8, 4): "-0.181952812",
    (8, 5): "0.182078283",
    (8, 6): "-0.072534896",
    (8, 7): "0.131958556",
    (8, 8): "-0.117099372",
    (8, 9): "0",
    (8, 10): "0.157052315",
    (8, 11): "0.019309343",
    (8, 12): "0",
    (8, 13): "-0.192783664",
    (8, 14): "-0.05199305",
    (8, 15): "-0.018424716",
    (8, 16): "0.151381673",
    (8, 17): "0",
    (8, 18): "0",
    (8, 20): "0.103363447",
    (8, 21): "-0.241804603",
    (9, 2): "-0.007707448",
    (9, 3): "0.116481613",
    (9, 4): "-0.207615097",
    (9, 5): "0.100298381",
    (9, 6): "0.024287061",
    (9, 7): "0.219457098",
    (9, 8): "0.097141668",
    (9, 9): "-0.01776427",
    (9, 10): "-0.089574066",
    (9, 11): "-0.063062742",
    (9, 12): "-0.172870946",
    (9, 13): "-0.197081974",
    (9, 14): "0.006939989",
    (9, 15): "0.197391343",
    (9, 16): "-0.057237415",
    (9, 17): "0.035265127",
    (9, 18): "-0.166289356",
    (9, 19): "0.247414919",
    (9, 20): "0.007626177",
    (9, 21): "0.120109098",
    (9, 22): "-0.010955728",
    (9, 23): "-0.24233192",
    (9, 24): "-0.121749639",
    (9, 25): "-0.219499139",
    (9, 26): "-0.173837793",
    (9, 27): "-0.196169915",
    (9, 28): "0.195408234",
    (9, 29): "-0.029441592",
    (9, 30): "0.158418513",
    (9, 31): "0.134608909",
    (9, 32): "-0.212531774",
    (9, 33): "0.14069143",
    (9, 34): "0.167756984",
    (9, 35): "0.109912886",
    (9, 36): "-0.056326575",
    (9, 37): "-0.199700696",
    (9, 38): "-0.164704133",
    (9, 39): "0.184473921",
    (9, 40): "0.202815317",
    (9, 41): "0.05",
    (9, 42): "0.103415652",
    (9, 43): "-0.218003228",
    (9, 44): "0.023833924",
    (9, 45): "-0.101005115",
    (9, 46): "-0.14504796",
    (9, 47): "-0.08516805",
    (9, 48): "-0.102810873",
    (9, 49): "0.066236",
    (10, 1): "-0.242222319",
    (10, 2): "0.16966684",
    (10, 3): "0.072170674",
    (10, 4): "-0.126209321",
    (10, 5): "0.193205657",
    (10, 6): "-0.173623346",
    (10, 7): "0.116340907",
    (10, 8): "0.10630991",
    (10, 9): "-0.088973251",
    (10, 10): "0.222320933",
    (10, 11): "-0.219389223",
    (10, 12): "0.031490227",
    (10, 13): "0.139343184",
    (10, 14): "-0.194044237",
    (10, 15): "0.229298725",
    (10, 16): "-0.101238697",
    (10, 17): "0",
    (10, 18): "-0.181673094",
    (10, 19): "0.183855815",
    (10, 20): "0.000141354",
    (10, 21): "-0.06463226",
    (10, 22): "0.096051141",
    (10, 23): "-0.09053022",
    (10, 24): "0.134075911",
    (10, 25): "-0.190643197",
    (10, 26): "0.214239473",
    (10, 27): "0.023328145",
    (10, 28): "0.219341461",
    (10, 29): "-0.179148898",
    (10, 30): "0.123862719",
    (10, 31): "-0.080975515",
    (10, 32): "0.136232538",
    (10, 33): "0",
    (10, 34): "-0.179187486",
    (10, 35): "-0.091648377",
    (10, 36): "0.033820488",
    (10, 37): "0",
    (10, 38): "0.053142588",
    (10, 39): "-0.152342696",
    (10, 40): "-0.009943898",
    (10, 41): "-0.111474841",
    (10, 42): "-0.054167761",
    (10, 43): "0",
    (10, 44): "-0.166712665",
    (10, 45): "0",
    (10, 46): "0.117601502",
    (10, 47): "0.23382412",
    (10, 48): "-0.030368616",
    (10, 49): "-0.142813363",
    (10, 50): "-0.110994882",
    (10, 51): "-0.052808895",
    (10, 52): "0.169102971",
    (10, 53): "0.164530375",
    (10, 54): "0.226255147",
    (10, 55): "0.070960601",
    (10, 56): "-0.20671678",
    (10, 57): "0.034925503",
    (10, 58): "0.069592985",
    (10, 59): "-0.135970795",
    (10, 60): "-0.199702174",
    (10, 61): "0.10728773",
    (10, 62): "-0.243566962",
    (10, 63): "0.097962685",
    (10, 64): "-0.142858798",
    (10, 65): "-0.022363657",
    (10, 66): "-0.196684628",
    (10, 67): "0.091195441",
    (10, 68): "0.185277564",
    (10, 69): "-0.013618542",
    (10, 70): "0.181592128",
    (10, 71): "-0.002720688",
    (10, 72): "-0.241280314",
    (10, 73): "-0.060830498",
    (10, 74): "0.203041242",
    (10, 75): "-0.155784059",
    (10, 76): "0.223370687",
    (10, 77): "0.09400538",
    (10, 78): "-0.08862306",
    (10, 79): "0",
    (10, 80): "-0.16443507",
    (10, 81): "0",
    (10, 82): "-0.104004668",
    (10, 83): "-0.039387087",
    (10, 84): "-0.06436061",
    (10, 85): "0.239779044",
    (10, 86): "0.183147375",
    (10, 87): "0.076759058",
    (10, 88): "0",
    (10, 89): "-0.073918755",
    (10, 90): "0.146644036",
    (10, 91): "-0.010769866",
    (10, 92): "-0.179635306",
    (10, 93): "-0.227496792",
    (10, 94): "-0.122288498",
    (10, 95): "-0.044751139",
    (10, 96): "-0.188546503",
    (10, 97): "0.109616979",
    (10, 98): "-0.144138872",
    (10, 99): "0",
    (10, 100): "-0.24647666",
    (10, 101): "0.095028752",
    (10, 102): "0.117069293",
    (10, 103): "0.002156507",
    (10, 104): "-0.009383138",
    (10, 105): "-0.171725261",
    (10, 106): "-0.12604575",
    (10, 107): "-0.035682646",
    (10, 108): "-0.241341556",
    (10, 109): "0",
    (10, 110): "-0.13807251",
    (10, 111): "-0.117089254",
    (10, 112): "0.11772367",
    (10, 113): "-0.046145975",
    (10, 114): "-0.142409299",
    (10, 115): "0",
    (10, 116): "0.126086904",
    (10, 117): "0.018788434",
    (10, 118): "0",
    (10, 119): "-0.149213537",
    (10, 120): "0.15938382",
    (10, 121): "0.030415577",
    (10, 122): "-0.096862024",
    (10, 123): "0",
    (10, 125): "-0.072814255",
    (10, 126): "0.230410569",
    (10, 127): "0.124073851",
    (10, 128): "0.220275737",
    (10, 129): "0.191263345",
    (10, 130): "-0.021262717",
    (10, 131): "-0.084977695",
    (10, 132): "0.186748986",
    (10, 133): "-0.211510648",
    (10, 134): "0.067235354",
    (10, 135): "-0.20077754",
    (10, 136): "0.24729063",
    (10, 137): "-0.147855661",
    (10, 138): "0.060735926",
    (10, 139): "-0.228927561",
    (10, 140): "-0.103360013",
    (10, 141): "-0.175623698",
    (10, 142): "0.161733527",
    (10, 143): "-0.224020127",
    (10, 144): "0.071725956",
    (10, 145): "0.22844721",
    (10, 146): "-0.173581855",
    (10, 147): "0.119232019",
    (10, 148): "-0.214138314",
    (10, 149): "0.076427941",
    (10, 150): "0.140030728",
    (10, 151): "0.241018368",
    (10, 152): "0.240454021",
    (10, 153): "0.226641032",
    (10, 154): "0.240380161",
    (10, 155): "0.177006746",
    (10, 156): "0.186162912",
    (10, 157): "-0.062900125",
    (10, 158): "-0.082871522",
    (10, 159): "0.198702064",
    (10, 160): "0.212926331",
    (10, 161): "-0.190989852",
    (10, 162): "-0.124019328",
    (10, 163): "-0.230670258",
    (10, 164): "0.231024036",
    (10, 165): "0.098889515",
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
    keys = [key for key in names() if key in KNOTINFO_CS]
    if len(keys) != 243:
        raise ArithmeticError("expected 243 hyperbolic knots, got %d" % len(keys))
    if set(keys) != set(KNOTINFO_BRAIDS) - set(TORUS):
        raise ArithmeticError("the Chern-Simons source and braid table name different hyperbolic knots")
    return keys


def _decimal_places(text):
    found = re.search(r"\.(\d+)$", text)
    return len(found.group(1)) if found else 0


def _decimal(text):
    return Decimal(str(text))


def _tolerance(text):
    places = _decimal_places(text)
    if places == 0:
        return Decimal("5e-8")
    return Decimal(5) * (Decimal(10) ** Decimal(-places))


def _negated(text):
    if text == "0":
        return "0"
    return text[1:] if text.startswith("-") else "-" + text


def _source_text(n, k, image):
    text = KNOTINFO_CS[(n, k)]
    return text if image == "K" else _negated(text)


def _source_ball(text, bits):
    field = RealBallField(bits)
    value = field(text)
    places = _decimal_places(text)
    if places:
        value = value.add_error(field(10) ** (-places))
    return value


def _scaled_text(text):
    if text == "0":
        return "0"
    source_digits = digits_of(text)
    digits = max(1, source_digits - 1)
    bits = numberdb.bits(digits + 3, losing=WORKING_GUARD)
    field = RealBallField(bits)
    value = _source_ball(text, bits) * 2 * field.pi() ** 2
    return to_text(value, digits=digits)


def _is_close_to_source(computed, expected):
    return abs(_decimal(computed) - _decimal(expected)) <= _tolerance(expected)


def _snap_cs_for_braid(n, k, mirror=False):
    strands, word = KNOTINFO_BRAIDS[(n, k)]
    link = Link(braid_closure=[int(letter) for letter in word])
    if mirror:
        link = link.mirror()
    value, accuracy = link.exterior().high_precision().chern_simons(accuracy=True)
    if accuracy < 20:
        raise ArithmeticError("%d_%d: SnapPy estimates only %d digits of Chern-Simons accuracy" % (n, k, accuracy))
    return str(value)


def _check_one(n, k):
    expected = KNOTINFO_CS[(n, k)]
    computed = _snap_cs_for_braid(n, k)
    if not _is_close_to_source(computed, expected):
        raise ArithmeticError(
            "%d_%d: SnapPy gives %s, KnotInfo gives %s"
            % (n, k, computed, expected)
        )
    if (n, k) in AMPHICHIRAL:
        return
    mirror_expected = _negated(expected)
    mirror_computed = _snap_cs_for_braid(n, k, mirror=True)
    if not _is_close_to_source(mirror_computed, mirror_expected):
        raise ArithmeticError(
            "%d_%d mirror: SnapPy gives %s, expected %s by sign reversal"
            % (n, k, mirror_computed, mirror_expected)
        )


def _entry_comment(n, k, image):
    name = subscript(n, k)
    if (n, k) in NAMED:
        name += ", " + NAMED[(n, k)]
    if image == "mirror":
        name = "mirror image of " + name
    parts = [name]
    parts.append("alternating" if is_alternating(n, k) else "non-alternating")
    if (n, k) in AMPHICHIRAL:
        parts.append("amphichiral")
    return "; ".join(parts)


class ChernSimonsKnotComplements(numberdb.Generator):

    table = TABLE
    parameters = ("n", "k", "knot", "normalisation")
    type = "R"
    digits = 9
    rigour = "heuristic (agreement-checked)"
    files = ("generate.py", "knotinfo_prime_knots.py")

    _checked = set()

    def enumerate(self):
        for n, k in hyperbolic_names():
            for image in ("K", "mirror"):
                if image == "mirror" and (n, k) in AMPHICHIRAL:
                    continue
                for normalisation in ("cs", "two-pi-squared-cs"):
                    yield {"n": int(n), "k": int(k), "knot": image, "normalisation": normalisation}

    def _ensure_checked(self, n, k):
        key = (n, k)
        if key not in self._checked:
            _check_one(n, k)
            self._checked.add(key)

    def value(self, params, digits):
        n, k = int(params["n"]), int(params["k"])
        image = params["knot"]
        normalisation = params["normalisation"]
        if (n, k) not in KNOTINFO_CS:
            raise ValueError("%d_%d is not a hyperbolic prime knot with at most ten crossings" % (n, k))
        if image not in ("K", "mirror"):
            raise ValueError("knot is 'K' or 'mirror', not %r" % image)
        if image == "mirror" and (n, k) in AMPHICHIRAL:
            raise ValueError("%d_%d is amphichiral and has one entry" % (n, k))
        if normalisation not in ("cs", "two-pi-squared-cs"):
            raise ValueError("normalisation is not recognised: %r" % normalisation)

        self._ensure_checked(n, k)
        text = _source_text(n, k, image)
        if normalisation == "two-pi-squared-cs":
            text = _scaled_text(text)
        number = 0 if text == "0" else text
        entry = {"number": number, "comment": _entry_comment(n, k, image)}
        if isinstance(number, str):
            entry["digits"] = digits_of(number)
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

    for name, body in sorted(_source_files(generator).items()):
        attach(table, name, body, run=run, message=message, rigour=generator.rigour)

    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = ChernSimonsKnotComplements()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="Chern-Simons invariants of the 243 hyperbolic prime knots with at most ten crossings and the mirror images of the chiral ones, checked against KnotInfo and SnapPy"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
