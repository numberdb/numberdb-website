"""Eigenvalues of the Gauss-Kuzmin-Wirsing operator -- numberdb.org/T174

The Gauss-Kuzmin-Wirsing transfer operator for the Gauss continued-fraction
map has real eigenvalues lambda_n ordered by decreasing absolute value, with
lambda_1 = 1. This generator stores the magnitudes of the certified
eigenvalues lambda_2, ..., lambda_50 from Nisoli's K = 1024 spectral data.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The attached TSV file gives centres and rigorous eigenvalue enclosure radii.
Each row is returned as a real ball whose radius includes the corresponding
enclosure radius, and the table asks for 90 digits, the precision certified
for all 50 eigenvalues in the source.
"""

import csv
import os
import sys

import numberdb.sage as numberdb
from sage.rings.real_arb import RealBallField


DIGITS = 90
WORKING_GUARD = 256
DATA_FILE = "gkw_spectral_coefficients_K1024.tsv"
FIRST_STORED = 2
LAST_STORED = 50


def field(digits):
    return RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def data_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), DATA_FILE)


def source_rows():
    with open(data_path(), encoding="utf8") as handle:
        usable = [line for line in handle if not line.startswith("#")]
    rows = {}
    for row in csv.DictReader(usable, delimiter="\t"):
        if not row:
            continue
        rows[int(row["j"])] = row
    return rows


_ROWS = None


def row_for(n):
    global _ROWS
    if _ROWS is None:
        _ROWS = source_rows()
    try:
        return _ROWS[int(n)]
    except KeyError as exc:
        raise ValueError("no certified source row for n = %s" % n) from exc


def eigenvalue(n, digits):
    row = row_for(n)
    R = field(digits)
    return R(row["lambda_j"]).add_error(R(row["eval_encl"]))


def entry_comment(n):
    if int(n) == 2:
        return (
            "$|\\lambda_2|$ is the Gauss-Kuzmin-Wirsing constant "
            "CITE{OEISA038517} "
            "CITE{MathWorldGKW}."
        )
    return ""


class GaussKuzminWirsingEigenvalues(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE") or "T174"
    parameters = ("n",)
    type = "R"
    digits = DIGITS
    rigour = "proven"
    files = ("generate.py", DATA_FILE)

    def enumerate(self):
        for n in range(FIRST_STORED, LAST_STORED + 1):
            yield {"n": n}

    def value(self, params, digits):
        n = int(params["n"])
        if n < FIRST_STORED or n > LAST_STORED:
            raise ValueError("n must satisfy %d <= n <= %d" %
                             (FIRST_STORED, LAST_STORED))
        out = {"number": abs(eigenvalue(n, digits))}
        comment = entry_comment(n)
        if comment:
            out["comment"] = comment
        return out


if __name__ == "__main__":
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") == "1":
        os.environ["NUMBERDB_API_KEY"] = sys.stdin.read().strip()
    generator = GaussKuzminWirsingEigenvalues()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(generator.publish(message="certified GKW eigenvalues"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
