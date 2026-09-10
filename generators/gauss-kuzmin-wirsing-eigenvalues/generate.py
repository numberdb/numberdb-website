"""Eigenvalues of the Gauss-Kuzmin-Wirsing operator -- numberdb.org/T174

The Gauss-Kuzmin-Wirsing transfer operator for the Gauss continued-fraction
map has real eigenvalues lambda_n ordered by decreasing absolute value, with
lambda_1 = 1. This generator stores the certified eigenvalues lambda_2, ...,
lambda_50 from Nisoli's K = 1024 spectral data.

Signed, as the source gives them. They alternate -- lambda_2 = -0.30366...,
lambda_3 = +0.10088..., and in general the sign is (-1)^(n+1) -- and the
source certifies the sign in a column of its own. Storing |lambda_n| threw
that away and could not be undone from the table: a reader cannot see an
alternation in a column of positive numbers. The one place the magnitude is
the conventional quantity is lambda_2, whose absolute value is what the
literature calls the Gauss-Kuzmin-Wirsing constant, and the entry comment for
that row says so.

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
from sage.rings.integer_ring import ZZ
from sage.rings.real_arb import RealBallField


DIGITS = 90
WORKING_GUARD = 256
DATA_FILE = "gkw_spectral_coefficients_K1024.tsv"
#: The leading eigenvalue is stored too, and it is stored as the integer.
#:
#: lambda_1 = 1 is a theorem: the operator preserves the Gauss measure, whose
#: density 1/((1+x) log 2) is the eigenfunction. The source's row for j = 1 is
#: 0.999...9, which is the Galerkin computation getting it right, and a
#: decimal of a hundred nines would say a number known to *be* 1 is known to a
#: hundred places. So the row is `1` and the source row is used to check it.
FIRST_STORED = 1
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
    if int(n) == 1:
        return (
            "Exactly $1$: the operator preserves the Gauss measure, whose "
            "density $\\frac{1}{(1+x)\\log2}$ is the eigenfunction "
            "CITE{comment-leading}."
        )
    if int(n) == 2:
        return (
            "The Gauss-Kuzmin-Wirsing constant is $|\\lambda_2|$, and the "
            "literature quotes it positive CITE{OEISA038517} "
            "CITE{MathWorldGKW}; the eigenvalue itself is negative."
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
        if n == 1:
            #Checked against the source rather than taken from it: the row is
            #a theorem, and the certified enclosure is what says the
            #computation agrees with the theorem.
            enclosure = eigenvalue(n, digits)
            if not enclosure.contains_exact(ZZ(1)):
                raise ValueError(
                    "the source's leading eigenvalue does not enclose 1")
            out = {"number": ZZ(1)}
        else:
            out = {"number": eigenvalue(n, digits)}
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
