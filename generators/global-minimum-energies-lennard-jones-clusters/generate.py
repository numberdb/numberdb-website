"""Global minimum energies of Lennard-Jones clusters -- numberdb.org/T446.

For n >= 2, E_n is the minimum energy of the n-atom Lennard-Jones cluster
LJ_n, in units of the pair well depth epsilon, using the Cambridge Cluster
Database convention

    E = sum_{i < j} 4 * ((sigma / r_ij)^12 - (sigma / r_ij)^6).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The rows n = 2, 3, 4 are exact, since all pair distances can be the pair
minimum 2^(1/6) sigma. The remaining rows are transcribed from the Cambridge
Cluster Database table read on 2026-09-23. The integrity check recomputes the
energy from the CCD coordinate archive. Because the published coordinates are
rounded, every recomputed coordinate energy is checked to be within 5e-6 of
the printed value, and the sixth decimal agrees on 125 of the 148 coordinate
rows.
"""

from __future__ import annotations

import hashlib
import html.parser
import io
import os
import sys
import tarfile
import urllib.request
from decimal import Decimal, ROUND_HALF_UP, localcontext

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ


TABLE = os.environ.get("NUMBERDB_TABLE", "T446")

CCD_TABLE_URL = "https://www-wales.ch.cam.ac.uk/~jon/structures/LJ/tables.150.html"
CCD_TAR_URL = "https://www-wales.ch.cam.ac.uk/~jon/structures/LJ/LJ.tar"
CCD_TABLE_SHA256 = "fdcb43c88093bd3601dbdfb761cc61e5758f678fdf71b7d71c2bcdcc7f55c95b"
CCD_TAR_SHA256 = "a5b2aac0000d6d665fb2007dcf24e7d036a05ec16b53d7d18e97d2ccdbd70e8b"

MIN_N = 2
MAX_N = 150
COORDINATE_TOLERANCE = Decimal("0.000005")
SIXTH_DECIMAL_MATCHES = 125
MAX_COORDINATE_DISCREPANCY = Decimal("0.00000134")

EXACT_ENERGIES = {
    2: ZZ(-1),
    3: ZZ(-3),
    4: ZZ(-6),
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _read_source(filename, url, expected_hash, binary=False):
    beside = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(beside, filename)
    if os.path.exists(path):
        with open(path, "rb") as handle:
            body = handle.read()
    else:
        request = urllib.request.Request(url, headers={"User-Agent": "numberdb-build"})
        with urllib.request.urlopen(request, timeout=60) as answer:
            body = answer.read()
    digest = hashlib.sha256(body).hexdigest()
    if digest != expected_hash:
        raise RuntimeError(
            "%s has sha256 %s, not the source snapshot %s"
            % (filename, digest, expected_hash)
        )
    return body if binary else body.decode("iso-8859-1")


def _table_html():
    return _read_source("tables.150.html", CCD_TABLE_URL, CCD_TABLE_SHA256)


def _tar_bytes():
    return _read_source("LJ.tar", CCD_TAR_URL, CCD_TAR_SHA256, binary=True)


class _Rows(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self._row = None
        self._cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        if tag in ("td", "th") and self._row is not None:
            self._cell = ""

    def handle_data(self, data):
        if self._cell is not None:
            self._cell += data

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None:
            text = " ".join(self._cell.replace("\xa0", " ").split())
            self._row.append(text)
            self._cell = None
        if tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None


def source_rows():
    """The CCD global-minimum rows, not the later icosahedral-minima table."""
    parser = _Rows()
    parser.feed(_table_html())
    rows = {}
    for row in parser.rows:
        for offset in (0, 5):
            if offset + 3 >= len(row) or not row[offset].isdigit():
                continue
            n = int(row[offset])
            energy = row[offset + 2]
            if not (MIN_N <= n <= MAX_N) or not energy.startswith("-"):
                continue
            rows.setdefault(n, {
                "energy": energy,
                "point_group": row[offset + 1],
                "reference": row[offset + 3],
            })
    expected = set(range(MIN_N, MAX_N + 1))
    if set(rows) != expected:
        missing = sorted(expected - set(rows))
        extra = sorted(set(rows) - expected)
        raise RuntimeError("unexpected CCD row set, missing %s extra %s" % (missing, extra))
    return rows


def _point_group_latex(text):
    text = text.strip()
    replacements = {
        "Dinfty h": r"$D_{\infty h}$",
        "D3h": r"$D_{3h}$",
        "D5h": r"$D_{5h}$",
        "C1": r"$C_1$",
        "C2": r"$C_2$",
        "C2v": r"$C_{2v}$",
        "C3v": r"$C_{3v}$",
        "C5v": r"$C_{5v}$",
        "Cs": r"$C_s$",
        "Ih": r"$I_h$",
        "Oh": r"$O_h$",
        "Td": r"$T_d$",
    }
    return replacements.get(text, text)


def _coordinates_from_tar(tar, n):
    if n == 2:
        with localcontext() as context:
            context.prec = 80
            r = Decimal(2) ** (Decimal(1) / Decimal(6))
        return [(Decimal(0), Decimal(0), Decimal(0)), (r, Decimal(0), Decimal(0))]

    with tar.extractfile(str(n)) as handle:
        tokens = handle.read().decode("ascii").split()
    if len(tokens) == 3 * n + 1 and Decimal(tokens[0]) == 0:
        tokens = tokens[1:]
    if len(tokens) != 3 * n:
        raise RuntimeError("point file %d has %d coordinates" % (n, len(tokens)))
    values = [Decimal(token) for token in tokens]
    return [tuple(values[i:i + 3]) for i in range(0, len(values), 3)]


def lennard_jones_energy(points):
    with localcontext() as context:
        context.prec = 80
        total = Decimal(0)
        one = Decimal(1)
        four = Decimal(4)
        for i, left in enumerate(points):
            for right in points[i + 1:]:
                r2 = sum((left[k] - right[k]) ** 2 for k in range(3))
                inv6 = one / (r2 ** 3)
                total += four * (inv6 * inv6 - inv6)
        return +total


def _rounded(value, decimals):
    quantum = Decimal(1).scaleb(-decimals)
    return value.quantize(quantum, rounding=ROUND_HALF_UP)


def _rounded_text(value, decimals):
    return format(_rounded(value, decimals), "f")


def _round_source(text, decimals):
    return _rounded_text(Decimal(text), decimals)


def run_integrity_checks():
    rows = source_rows()
    if len(rows) != MAX_N - MIN_N + 1:
        raise RuntimeError("expected 149 rows, found %d" % len(rows))

    tar_bytes = _tar_bytes()
    sixth_matches = 0
    largest_discrepancy = Decimal(0)
    with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as tar:
        names = set(tar.getnames())
        missing = [str(n) for n in range(3, MAX_N + 1) if str(n) not in names]
        if missing:
            raise RuntimeError("coordinate archive is missing %s" % ", ".join(missing))
        for n in range(MIN_N, MAX_N + 1):
            printed = rows[n]["energy"]
            if n in EXACT_ENERGIES:
                if Decimal(printed) != Decimal(str(EXACT_ENERGIES[n])):
                    raise RuntimeError("exact row n=%d disagrees with the source" % n)
                if n == 2:
                    continue
            computed = lennard_jones_energy(_coordinates_from_tar(tar, n))
            discrepancy = abs(computed - Decimal(printed))
            largest_discrepancy = max(largest_discrepancy, discrepancy)
            if discrepancy >= COORDINATE_TOLERANCE:
                raise RuntimeError(
                    "coordinate check failed at n=%d: %s from coordinates, %s in source"
                    % (n, computed, printed)
                )
            if _rounded_text(computed, 6) == printed:
                sixth_matches += 1

    if sixth_matches != SIXTH_DECIMAL_MATCHES:
        raise RuntimeError(
            "expected %d sixth-decimal matches, found %d"
            % (SIXTH_DECIMAL_MATCHES, sixth_matches)
        )
    if largest_discrepancy >= MAX_COORDINATE_DISCREPANCY:
        raise RuntimeError("largest coordinate discrepancy was %s" % largest_discrepancy)


def _comment(n, row):
    if n in EXACT_ENERGIES:
        return (
            r"$E_%d=%s$. Optimality follows from the pair potential lower bound."
            % (n, EXACT_ENERGIES[n])
        )
    point_group = _point_group_latex(row["point_group"])
    reference = row["reference"].strip()
    if reference:
        first = "The CCD lists point group %s and first reference %s." % (
            point_group, reference
        )
    else:
        first = "The CCD lists point group %s." % point_group
    return first + " A proof of global optimality is not cited in the source table."


class LennardJonesClusterGlobalMinimumEnergies(numberdb.Generator):
    table = TABLE
    parameters = ("n",)
    type = "R"
    digits = 6
    rigour = "heuristic (agreement-checked)"
    files = ("generate.py", "tables.150.html")

    def enumerate(self):
        for n in range(MIN_N, MAX_N + 1):
            yield {"n": str(n)}

    def value(self, params, digits):
        n = int(params["n"])
        row = source_rows()[n]
        number = EXACT_ENERGIES.get(n, row["energy"])
        return {"number": number, "comment": _comment(n, row)}


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

        written = to_text(value, entry.get("digits", wanted), generator.format)
        _check_precision(table, identity, written, entry.get("digits", wanted), lowering=False)

        record = dict(entry)
        record.pop("digits", None)
        entries.add(**params, **record, digits=entry.get("digits", wanted))

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
    generator = LennardJonesClusterGlobalMinimumEnergies()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="Lennard-Jones cluster global minimum energies for 2 <= n <= 150",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
