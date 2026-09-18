"""Degrees of irreducible characters of sporadic simple groups -- numberdb.org/T255

This generator reads CTblLib 1.3.11 and stores the exact degrees chi_i(1) of
the nontrivial irreducible complex characters of the 26 sporadic simple
groups. The ordering is CTblLib's ordering for each ordinary character table,
and chi_1 is omitted because it is the trivial character of degree 1.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

Set CTBLLIB_TARBALL to a local copy of ctbllib-1.3.11.tar.gz to avoid
downloading the public archive again.
"""

import io
import os
import re
import sys
import tarfile
import urllib.request
from functools import lru_cache

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ


TABLE = "T255"
CTBLLIB_URL = (
    "https://www.math.rwth-aachen.de/~Thomas.Breuer/ctbllib/"
    "ctbllib-1.3.11.tar.gz"
)
OEIS_MONSTER_URL = "https://oeis.org/A001379/b001379.txt"

GROUPS = (
    ("M11", "M11", "ctomathi.tbl"),
    ("M12", "M12", "ctomathi.tbl"),
    ("M22", "M22", "ctomathi.tbl"),
    ("M23", "M23", "ctomathi.tbl"),
    ("M24", "M24", "ctomathi.tbl"),
    ("J1", "J1", "ctoconja.tbl"),
    ("J2", "J2", "ctoconja.tbl"),
    ("J3", "J3", "ctoconja.tbl"),
    ("J4", "J4", "ctoconja.tbl"),
    ("Co3", "Co3", "ctoconja.tbl"),
    ("Co2", "Co2", "ctoconja.tbl"),
    ("Co1", "Co1", "ctoconja.tbl"),
    ("Fi22", "Fi22", "ctofisc1.tbl"),
    ("Fi23", "Fi23", "ctofisc2.tbl"),
    ("Fi24", "F3+", "ctofisc2.tbl"),
    ("HS", "HS", "ctospora.tbl"),
    ("McL", "McL", "ctospora.tbl"),
    ("He", "He", "ctospora.tbl"),
    ("Ru", "Ru", "ctospora.tbl"),
    ("Suz", "Suz", "ctospora.tbl"),
    ("ON", "ON", "ctospora.tbl"),
    ("HN", "HN", "ctospora.tbl"),
    ("Ly", "Ly", "ctospora.tbl"),
    ("Th", "Th", "ctospora.tbl"),
    ("B", "B", "ctomonst.tbl"),
    ("M", "M", "ctomonst.tbl"),
)

EXPECTED_CHARACTER_COUNTS = {
    "M11": 10,
    "M12": 15,
    "M22": 12,
    "M23": 17,
    "M24": 26,
    "J1": 15,
    "J2": 21,
    "J3": 21,
    "J4": 62,
    "Co3": 42,
    "Co2": 60,
    "Co1": 101,
    "Fi22": 65,
    "Fi23": 98,
    "Fi24": 108,
    "HS": 24,
    "McL": 24,
    "He": 33,
    "Ru": 36,
    "Suz": 43,
    "ON": 30,
    "HN": 54,
    "Ly": 53,
    "Th": 48,
    "B": 184,
    "M": 194,
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _download(url):
    request = urllib.request.Request(
        url, headers={"User-Agent": "numberdb-sporadic-character-degrees"})
    with urllib.request.urlopen(request, timeout=120) as answer:
        return answer.read()


def _archive_bytes():
    path = os.environ.get("CTBLLIB_TARBALL")
    if path:
        with open(path, "rb") as handle:
            return handle.read()

    cache = "/tmp/ctbllib-1.3.11.tar.gz"
    if os.path.exists(cache):
        with open(cache, "rb") as handle:
            return handle.read()

    data = _download(CTBLLIB_URL)
    try:
        with open(cache, "wb") as handle:
            handle.write(data)
    except OSError:
        pass
    return data


def _ordinary_sources():
    wanted = sorted({filename for _, _, filename in GROUPS})
    source = {}
    with tarfile.open(fileobj=io.BytesIO(_archive_bytes()), mode="r:gz") as archive:
        for filename in wanted:
            member = "ctbllib-1.3.11/data/" + filename
            source[filename] = archive.extractfile(member).read().decode(
                "utf8", "replace")
    return source


def _split_top_level(text):
    parts = []
    start = 0
    bracket_depth = 0
    paren_depth = 0
    in_string = False
    escaped = False

    for index, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "[":
            bracket_depth += 1
        elif char == "]":
            bracket_depth -= 1
        elif char == "(":
            paren_depth += 1
        elif char == ")":
            paren_depth -= 1
        elif char == "," and bracket_depth == 0 and paren_depth == 0:
            parts.append(text[start:index].strip())
            start = index + 1

    parts.append(text[start:].strip())
    return parts


def _list_elements(text):
    text = text.strip()
    if not (text.startswith("[") and text.endswith("]")):
        raise ValueError("expected a GAP list, got %r" % text[:40])
    return _split_top_level(text[1:-1])


def _extract_mot_call(source, name):
    needle = 'MOT("%s"' % name
    start = source.find(needle)
    if start < 0:
        raise KeyError("CTblLib table %s was not found" % name)

    open_paren = source.find("(", start)
    depth = 0
    in_string = False
    escaped = False

    for index in range(open_paren, len(source)):
        char = source[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return source[open_paren + 1:index]

    raise ValueError("unterminated MOT record for %s" % name)


def _degree_from_row(row, degrees):
    row = row.strip()
    if row.startswith("[GALOIS"):
        found = re.match(r"\[GALOIS,\s*\[(\d+)", row)
        if not found:
            raise ValueError("could not read GALOIS row %r" % row[:80])
        return degrees[int(found.group(1)) - 1]

    if not row.startswith("["):
        raise ValueError("expected a character row, got %r" % row[:80])
    first = _split_top_level(row[1:-1])[0]
    if not re.fullmatch(r"\d+", first):
        raise ValueError("character degree is not an integer: %r" % first[:80])
    return int(first)


def _parse_degrees(characters):
    degrees = []
    for row in _list_elements(characters):
        degrees.append(_degree_from_row(row, degrees))
    return tuple(degrees)


@lru_cache(maxsize=1)
def character_degrees():
    sources = _ordinary_sources()
    out = {}
    counts = {}
    for key, ctbl_name, filename in GROUPS:
        arguments = _split_top_level(_extract_mot_call(sources[filename], ctbl_name))
        centralizers = _list_elements(arguments[2])
        degrees = _parse_degrees(arguments[4])
        if len(degrees) != len(centralizers):
            raise ValueError("%s has %d degrees and %d classes" % (
                key, len(degrees), len(centralizers)))
        if len(degrees) != EXPECTED_CHARACTER_COUNTS[key]:
            raise ValueError("%s has %d characters, expected %d" % (
                key, len(degrees), EXPECTED_CHARACTER_COUNTS[key]))
        out[key] = degrees
        counts[key] = len(centralizers)
    return out, counts


def stored_sporadic_orders():
    table = numberdb.table("T77")
    return {
        group: int(entry["number"] if isinstance(entry, dict) else entry)
        for group, entry in table["Numbers"].items()
    }


def monster_degrees_from_oeis():
    text = _download(OEIS_MONSTER_URL).decode("utf8", "replace")
    values = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        _, value = line.split(None, 1)
        values.append(int(value))
    return tuple(values)


def run_integrity_checks():
    degrees, counts = character_degrees()
    if sum(counts.values()) != 1396:
        raise ValueError("expected 1396 irreducible characters")
    if sum(len(rows) - 1 for rows in degrees.values()) != 1370:
        raise ValueError("expected 1370 nontrivial character degrees")

    orders = stored_sporadic_orders()
    for group, rows in degrees.items():
        total = sum(degree * degree for degree in rows)
        if total != orders[group]:
            raise ValueError("%s: sum of squares is %s, order is %s" % (
                group, total, orders[group]))

    oeis_monster = monster_degrees_from_oeis()
    if tuple(degrees["M"]) != oeis_monster[:len(degrees["M"])]:
        raise ValueError("Monster degrees disagree with OEIS A001379")

    return True


class SporadicCharacterDegrees(numberdb.Generator):

    table = TABLE
    parameters = ("G", "chi")
    type = "Z"
    rigour = "exact"

    def enumerate(self):
        degrees, _ = character_degrees()
        for group, _, _ in GROUPS:
            for index in range(2, len(degrees[group]) + 1):
                yield {"G": group, "chi": str(index)}

    def value(self, params, digits):
        degrees, _ = character_degrees()
        return ZZ(degrees[str(params["G"])][int(params["chi"]) - 1])


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
        produced_by=_producer(generator),
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
    generator = SporadicCharacterDegrees()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        run_integrity_checks()
        print(fill_draft_once(
            generator,
            message="sporadic irreducible character degrees from CTblLib"))
    else:
        run_integrity_checks()
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
