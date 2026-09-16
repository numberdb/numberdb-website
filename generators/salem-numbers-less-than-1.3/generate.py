"""Salem numbers less than 1.3 -- numberdb.org/T284

This table holds the 47 Salem numbers below 1.3 in Mossinghoff's list of
small Salem numbers. Entries are indexed by the first half of the coefficients
of the reciprocal minimal polynomial.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

Mossinghoff's page prints truncated decimal expansions. This generator uses
the exact reciprocal polynomials, isolates the real root greater than 1 in
interval arithmetic, and checks that the source decimal is a truncation of the
isolated interval.
"""

import os
import re
import sys
from functools import lru_cache

import numberdb.sage as numberdb
from sage.libs.pari import pari
from sage.misc.latex import latex
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ
from sage.rings.real_mpfi import RealIntervalField


TABLE = "T284"
WORKING_GUARD = 192
EXPECTED_ROWS = 47

R = PolynomialRing(QQ, "x")
x = R.gen()


SOURCE_ROWS = """
  1.)  10  1.176280818259917506544070338474  1  1  0 -1 -1 -1
  2.)  18  1.188368147508223588142960958629  1 -1  1 -1  0  0 -1  1 -1  1
  3.)  14  1.200026523987391518902962100414  1  0  0 -1 -1  0  0  1
  4.)  14  1.202616743688604261118295415948  1  0 -1  0  0  0  0 -1
  5.)  10  1.216391661138265091626806311199  1  0  0  0 -1 -1
  6.)  18  1.219720859040311844169606760414  1 -1  0  0  0  0  0  0 -1  1
  7.)  10  1.230391434407224702790177938975  1  0  0 -1  0 -1
  8.)  20  1.232613548593121003962731694807  1 -1  0  0  0 -1  1  0  0 -1  1
  9.)  22  1.235664580389747308105169351531  1  0 -1 -1  0  0  0  1  1  0 -1 -1
 10.)  16  1.236317931803230489899094869802  1 -1  0  0  0  0  0  0 -1
 11.)  26  1.237504821217490608171021829989  1  0 -1  0  0 -1  0  0 -1  0  1  0  0  1
 12.)  12  1.240726423652541392056148161575  1 -1  1 -1  0  0 -1
 13.)  18  1.252775937410113900864582824053  1  0  0  0  0  0 -1 -1 -1 -1
 14.)  20  1.253330650201489757028162788986  1  0 -1  0  0 -1  0  0  0  0  0
 15.)  14  1.255093516763722879173091003232  1  0 -1 -1  0  1  0 -1
 16.)  18  1.256221154391670233067434043309  1 -1  0  0 -1  1  0  0  0 -1
 17.)  24  1.260103540354990920321649852331  1 -1  0  0 -1  1  0 -1  1 -1  0  1 -1
 18.)  22  1.260284236896492963739228435283  1 -1  0 -1  1  0  0  0 -1  1 -1  1
 19.)  10  1.261230961137138851946671503074  1  0 -1  0  0 -1
 20.)  26  1.263038139930169261222022798085  1 -1  0  0  0  0 -1  0  0  0  0  0  0  1
 21.)  14  1.267296442523068692734077407604  1 -1  0  0  0  0 -1  1
 22.)  22  1.276779674019016861136497157605  1 -1 -1  1  0  0  0  0  0 -1  0  1
 23.)   8  1.280638156267757596701902532710  1  0  0 -1 -1
 24.)  26  1.281691371528106310055107748672  1  0  0  0  0  0 -1 -1 -1 -1 -1 -1 -1 -1
 25.)  20  1.282495560639960169561207128806  1 -2  2 -2  2 -2  1  0 -1  1 -1
 26.)  18  1.284616550925536736743131441485  1  0  0  0 -1  0 -1 -1  0 -1
 27.)  26  1.284746821544843035729838140650  1 -2  1  1 -2  1  0  0 -1  1  0 -1  1 -1
 28.)  30  1.285099363651876557117420034512  1  0  0  0  0 -1 -1 -1 -1 -1 -1  0  0  0  0  1
 29.)  30  1.285121520153207532780681369174  1 -2  2 -2  1  0 -1  2 -2  1  0 -1  1 -1  1 -1
 30.)  30  1.285185670752909791356387310393  1 -1  0  0  0  0  0  0 -1  0  0  0 -1  0  0 -1
 31.)  26  1.285196726769853432068127270005  1  0 -1 -1  0  0  0  1  0 -1 -1  0  1  1
 32.)  44  1.285199179205612167312192383918  1 -1  0  0  0  0  0 -1  0  0  0 -1  0  0  0  0  0  0  0  1  0  0  1
 33.)  30  1.285235436228923770828415884707  1  0 -1  0  0 -1 -1  0  0  0  1  0  0  1  0 -1
 34.)  34  1.285409064765363764030309848277  1 -1  0  0 -1  1 -1  0  1 -1  1  0 -1  1 -1  0  1 -1
 35.)  18  1.286395966836277224044411092745  1 -2  2 -2  2 -2  2 -3  3 -3
 36.)  26  1.286730182048201274368747282841  1 -1  0  0 -1  1 -1  0  1 -1  1  0 -1  1
 37.)  24  1.291741425714500483635599066106  1 -1  0  0  0  0 -1  0  0  0  0  0  0
 38.)  20  1.292039106017929461943480560567  1  0 -1  0  0 -1  0  0 -1  0  1
*39.)  40  1.292418657582426546281031229140  1  0  0 -1  0 -1  0 -1  0 -1  0 -1  0  0  1  0  1  0  1  0  1
*40.)  46  1.292900721780102794630870596243  1  0  0  0 -1 -1 -1 -1  0  0  0  0  0  0  0  0  0  0  0  0  0  1  1  1
 41.)  10  1.293485953125454106519909883794  1  0 -1 -1  0  1
 42.)  18  1.295675371944048235295741653561  1 -1  0  0 -1  1 -1  0  1 -1
*43.)  34  1.296210659593309216851783179125  1 -1  0 -1  0  1  0  1 -2  0  0  1  1 -1 -1 -1  1  1
 44.)  22  1.296421365194547218873224266498  1 -1  0  0  0 -1  0  0  0  0  0  1
 45.)  28  1.296821373714950077456125855369  1  0  0  0 -1 -1 -1 -1 -1  0  0  0  1  1  1
*46.)  36  1.298429835475111538327805425740  1  1  0 -1 -2 -2 -1  0  1  1  0 -1 -1  0  1  1  0 -1 -1
 47.)  26  1.299744869472170731620096386139  1 -1 -1  0  2  0 -2 -1  2  2 -2 -2  0  3
"""


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def source_records():
    rows = []
    pattern = re.compile(
        r"^\s*(?P<recent>\*)?\s*(?P<rank>\d+)\.\)\s+"
        r"(?P<degree>\d+)\s+(?P<decimal>\d+\.\d+)\s+"
        r"(?P<coefficients>[-\d\s]+)$"
    )
    for line in SOURCE_ROWS.splitlines():
        if not line.strip():
            continue
        found = pattern.match(line)
        if not found:
            raise ValueError("could not parse source row: %r" % line)
        coefficients = tuple(ZZ(part) for part in found.group("coefficients").split())
        degree = int(found.group("degree"))
        if len(coefficients) != degree // 2 + 1:
            raise ValueError("row %s has wrong half length" % found.group("rank"))
        rows.append({
            "rank": int(found.group("rank")),
            "degree": degree,
            "decimal": found.group("decimal"),
            "coefficients": coefficients,
            "recent": bool(found.group("recent")),
        })
    if len(rows) != EXPECTED_ROWS:
        raise ValueError("found %d source rows, expected %d"
                         % (len(rows), EXPECTED_ROWS))
    return rows


RECORDS = source_records()
RECORD_BY_KEY = {
    ",".join(str(c) for c in record["coefficients"]): record
    for record in RECORDS
}


def _decimal_lower(text):
    whole, fractional = text.split(".", 1)
    scale = ZZ(10) ** len(fractional)
    return QQ(ZZ(whole) * scale + ZZ(fractional)) / QQ(scale)


def source_truncation_interval(text):
    lower = _decimal_lower(text)
    return lower, lower + QQ(1) / QQ(10) ** len(text.split(".", 1)[1])


def coefficient_key(coefficients):
    return ",".join(str(c) for c in coefficients)


def polynomial_from_half(coefficients):
    degree = 2 * (len(coefficients) - 1)
    polynomial = R(0)
    for i, coefficient in enumerate(coefficients):
        polynomial += QQ(coefficient) * x ** (degree - i)
    for i, coefficient in enumerate(coefficients[:-1]):
        polynomial += QQ(coefficient) * x ** i
    return polynomial


@lru_cache(None)
def polynomial_from_key(key):
    coefficients = tuple(ZZ(part) for part in key.split(","))
    return polynomial_from_half(coefficients)


def _check_polynomial(record):
    coefficients = record["coefficients"]
    polynomial = polynomial_from_half(coefficients)
    degree = record["degree"]
    if polynomial.degree() != degree:
        raise ArithmeticError("%s has degree %d, expected %d"
                              % (coefficient_key(coefficients),
                                 polynomial.degree(), degree))
    for i in range(degree + 1):
        if polynomial[i] != polynomial[degree - i]:
            raise ArithmeticError("%s is not reciprocal"
                                  % coefficient_key(coefficients))
    if not pari(str(polynomial)).polisirreducible():
        raise ArithmeticError("%s is not irreducible"
                              % coefficient_key(coefficients))
    return polynomial


def _real_roots_greater_than_one(polynomial, bits):
    field = RealIntervalField(bits)
    roots = []
    for root, multiplicity in polynomial.roots(field):
        if multiplicity != 1:
            raise ArithmeticError("multiple real root in %s" % polynomial)
        if root.lower() > 1:
            roots.append(root)
    roots.sort(key=lambda root: root.lower())
    return roots


def salem_root_interval(polynomial, digits):
    roots = _real_roots_greater_than_one(
        polynomial, numberdb.bits(digits, losing=WORKING_GUARD))
    if len(roots) != 1:
        raise ArithmeticError("%s has %d real roots greater than 1"
                              % (polynomial, len(roots)))
    return roots[0]


def check_source_truncation(root, source_decimal):
    lower, upper = source_truncation_interval(source_decimal)
    if not (root.lower() >= lower and root.upper() < upper):
        raise ArithmeticError(
            "root interval %s is not inside source truncation [%s, %s)"
            % (root, lower, upper))


def polynomial_latex(polynomial):
    return latex(polynomial)


def entry_comment(record, polynomial):
    comment = ("degree $%d$; minimal polynomial $%s$"
               % (record["degree"], polynomial_latex(polynomial)))
    if record["rank"] == 1:
        comment += "; this is Lehmer's number"
    if record["degree"] > 44:
        comment += ("; this is the one known small Salem number in "
                    "Mossinghoff's list with degree greater than $44$")
    elif record["recent"]:
        comment += "; Mossinghoff marks this row as a recent discovery"
    return comment + "."


class SalemNumbersLessThan13(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE") or TABLE
    parameters = ("coefficients",)
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self):
        for record in RECORDS:
            yield {"coefficients": coefficient_key(record["coefficients"])}

    def value(self, params, digits):
        key = str(params["coefficients"])
        record = RECORD_BY_KEY[key]
        polynomial = _check_polynomial(record)
        root = salem_root_interval(polynomial, digits)
        check_source_truncation(root, record["decimal"])
        return {"number": root, "comment": entry_comment(record, polynomial)}


def main():
    _key_from_stdin()
    generator = SalemNumbersLessThan13()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="computed Salem roots from exact polynomials"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
