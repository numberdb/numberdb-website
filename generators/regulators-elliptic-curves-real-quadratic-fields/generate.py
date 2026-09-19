"""Regulators of elliptic curves over real quadratic fields -- numberdb.org/T293.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # preview the changes
    $ sage -python generate.py --publish  # send them

The file reads the pinned ecnf-data commit named below and writes regulators
of positive-rank elliptic curves over the six real quadratic fields of
smallest discriminant, with conductor norm at most 250. It keeps 35
significant digits from ecnf-data's `reg` field, checks the BSD quotient
against the recorded analytic order of Sha, and checks the D=21 rank-2
regulators by recomputing the height-pairing determinant from the recorded
generators and equations.
"""

import os
import re
import sys
from decimal import Decimal, getcontext
from urllib.request import urlopen

import numberdb.sage as numberdb
from sage.misc.sage_eval import sage_eval
from sage.rings.number_field.number_field import NumberField
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ
from sage.rings.real_mpfr import RR
from sage.schemes.elliptic_curves.constructor import EllipticCurve


COMMIT = "10b28418e80392032b106ea00e6c5aa109d28e7b"
BASE = f"https://raw.githubusercontent.com/JohnCremona/ecnf-data/{COMMIT}/RQF"
FIELDS = (5, 8, 12, 13, 17, 21)
CONDUCTOR_NORM_BOUND = 250
DIGITS = 35
BSD_TOLERANCE = Decimal("1e-25")

getcontext().prec = 100


def key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def source_file(kind, D):
    return urlopen(f"{BASE}/{kind}.2.2.{D}.1").read().decode().splitlines()


def key_of(parts):
    return (parts[1], parts[2], parts[3])


def label_of(parts):
    return f"{parts[1]}-{parts[2]}{parts[3]}"


def conductor_norm(parts):
    return int(parts[1].split(".")[0])


def sig_trunc(text, digits=DIGITS):
    sign = ""
    text = text.strip()
    if text.startswith("-"):
        sign, text = "-", text[1:]
    out = []
    count = 0
    started = False
    for char in text:
        if char.isdigit():
            if char != "0" or started:
                started = True
                if count >= digits:
                    continue
                count += 1
            out.append(char)
        else:
            out.append(char)
    result = "".join(out)
    if result.endswith("."):
        result = result[:-1]
    return sign + result


def normalize_latex(text):
    text = text.replace("*w", "w")
    text = text.replace(r"\phi", "w")
    return re.sub(r"(?<![A-Za-z\\])a(?![A-Za-z])", "w", text)


def tamagawa_product(local_data):
    if not local_data or local_data == "[]":
        return 1
    product = 1
    for item in local_data.split(";"):
        if item:
            product *= int(item.split(":")[-1])
    return product


def field_polynomial(D):
    R = PolynomialRing(QQ, "x")
    x = R.gen()
    if D % 4 == 1:
        return x * x - x - QQ(D - 1) / QQ(4)
    return x * x - QQ(D) / QQ(4)


def field(D):
    return NumberField(field_polynomial(D), "w", check=False)


def field_element(K, pair):
    return QQ(pair[0]) + QQ(pair[1]) * K.gen()


def parse_nf_element(K, text):
    a, b = text.split(",")
    return QQ(a) + QQ(b) * K.gen()


def bsd_quotient(row, cp, D):
    r = int(row["rank"])
    torsion_order = Decimal(row["torsion_order"])
    lvalue = Decimal(row["lvalue"])
    omega = Decimal(row["omega"])
    regulator = Decimal(row["reg"])
    numerator = lvalue * torsion_order * torsion_order * Decimal(D).sqrt()
    denominator = (Decimal(2) ** r) * omega * regulator * Decimal(cp)
    return numerator / denominator


def read_rows():
    rows = []
    for D in FIELDS:
        curves = {}
        for line in source_file("curves", D):
            parts = line.split()
            curves[key_of(parts)] = {
                "ideal": normalize_latex(parts[4]),
                "ainvs": parts[6],
                "equation": normalize_latex(parts[10]),
            }
        local = {}
        for line in source_file("local_data", D):
            parts = line.split()
            local[key_of(parts)] = parts[4] if len(parts) > 4 else ""
        for line in source_file("mwdata", D):
            parts = line.split()
            if conductor_norm(parts) > CONDUCTOR_NORM_BOUND:
                continue
            if parts[4] == "?" or int(parts[4]) <= 0:
                continue
            curve = curves[key_of(parts)]
            row = {
                "D": D,
                "label": label_of(parts),
                "rank": parts[4],
                "rank_bounds": parts[5],
                "analytic_rank": parts[6],
                "ngens": parts[7],
                "gens": parts[8],
                "heights": parts[9],
                "reg": parts[10],
                "torsion_order": parts[11],
                "torsion_structure": parts[12],
                "torsion_gens": parts[13],
                "omega": parts[14],
                "lvalue": parts[15],
                "sha": parts[16],
                "ideal": curve["ideal"],
                "ainvs": curve["ainvs"],
                "equation": curve["equation"],
                "cp": tamagawa_product(local[key_of(parts)]),
            }
            check_source_row(row)
            rows.append(row)
    check_rank_two_determinants(rows)
    return rows


def check_source_row(row):
    rank = int(row["rank"])
    if rank == 1:
        height = row["heights"].strip()[1:-1]
        if sig_trunc(height, DIGITS) != sig_trunc(row["reg"], DIGITS):
            raise ValueError(f'{row["D"]} {row["label"]}: rank-1 height disagrees with reg')
    quotient = bsd_quotient(row, row["cp"], row["D"])
    sha = Decimal(row["sha"])
    if abs(quotient - sha) > BSD_TOLERANCE:
        raise ValueError(
            f'{row["D"]} {row["label"]}: BSD quotient {quotient} != Sha {sha}'
        )


def check_rank_two_determinants(rows):
    by_D = {}
    for row in rows:
        if int(row["rank"]) == 2:
            by_D.setdefault(row["D"], []).append(row)
    for D, rank_two_rows in by_D.items():
        K = field(D)
        for row in rank_two_rows:
            ainvs = [parse_nf_element(K, part) for part in row["ainvs"].split(";")]
            E = EllipticCurve(K, ainvs)
            gens = sage_eval(row["gens"], locals={"QQ": QQ})
            points = [
                E([field_element(K, coordinate) for coordinate in point])
                for point in gens
            ]
            determinant = RR(E.height_pairing_matrix(points).det())
            source = RR(row["reg"])
            relative = abs(determinant - source) / max(abs(source), RR("1e-99"))
            if relative > RR("1e-10"):
                raise ValueError(
                    f'{D} {row["label"]}: rank-2 determinant {determinant} '
                    f"disagrees with source {source}"
                )


class RealQuadraticEllipticRegulators(numberdb.Generator):
    table = "T293"
    parameters = ("D", "label")
    type = "R"
    digits = DIGITS
    rigour = "heuristic"

    def __init__(self):
        self.rows = read_rows()

    def enumerate(self):
        for row in self.rows:
            yield {"D": str(row["D"]), "label": row["label"]}

    def value(self, params, digits):
        D = int(params["D"])
        label = params["label"]
        for row in self.rows:
            if row["D"] == D and row["label"] == label:
                field_label = f"2.2.{D}.1-{label}"
                return {
                    "number": sig_trunc(row["reg"], digits),
                    "comment": (
                        f"LMFDB curve {field_label} has conductor ideal "
                        f'${row["ideal"]}$, rank ${row["rank"]}$, and equation '
                        f'${row["equation"]}$.'
                    ),
                }
        raise KeyError(params)


if __name__ == "__main__":
    key_from_stdin()
    generator = RealQuadraticEllipticRegulators()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            overwrite=False,
            message="refresh rank-2-aware generator for conductor norm <= 250",
        ))
    else:
        print(generator.preview(overwrite=False))
