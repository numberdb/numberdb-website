"""Zeros of the L-functions of level one cusp forms -- numberdb.org/T324.

For each normalised Hecke eigenform f in S_k(SL_2(Z)), this stores the first
positive ordinates t_n for zeros L(f,k/2+i*t_n)=0 on the critical line. The
eigenforms in each weight are sorted by the embedded value of a_2, not by
Sage's or PARI's raw embedding order.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The zero ordinates are computed with PARI/GP's lfunmf and lfunzeros at two
working precisions. The generator sorts the PARI L-functions by a_2 and checks
that order against the exact T_2 characteristic polynomial from Sage.
"""

from decimal import Decimal
import os
import sys

import numberdb.sage as numberdb
import sage.symbolic.expression
from sage.libs.pari import pari
from sage.modular.modform.constructor import CuspForms
from sage.rings.qqbar import AA
from sage.rings.real_mpfr import RealField


MAX_WEIGHT = 40
ZEROS_PER_FORM = 20
SEARCH_HEIGHT = 80
ZERO_MESH = 16
WORKING_DIGITS = (80, 120)
COMMENT_DIGITS = 80
PARI_GUARD_BITS = 64
HECKE_SLUG = "Hecke_polynomials_of_level_one_cusp_forms"


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def cusp_dimension(k):
    if k < 12 or k % 2:
        return 0
    if k % 12 == 2:
        return k // 12 - 1
    return k // 12


def _bits(digits):
    return numberdb.bits(int(digits), losing=PARI_GUARD_BITS)


def _set_pari_precision(bits):
    pari("default(realbitprecision, %d)" % int(bits))


def _decimal(value):
    return Decimal(str(value).replace(" ", ""))


def _short_decimal(value):
    return format(_decimal(value), ".16g")


def _lfun_list(k):
    mf = pari("mfinit([1,%d],0)" % int(k))
    lfunmf = pari("lfunmf")(mf)
    values = []
    for orbit_index in range(len(lfunmf)):
        orbit = lfunmf[orbit_index]
        for embedding_index in range(len(orbit)):
            ldata = orbit[embedding_index]
            a2 = pari("lfunan")(ldata, 2)[1]
            values.append({
                "orbit": orbit_index + 1,
                "embedding": embedding_index + 1,
                "ldata": ldata,
                "a2": a2,
            })
    return values


def _assert_a2_order(k, entries, bits):
    dimension = cusp_dimension(k)
    if len(entries) != dimension:
        raise ArithmeticError("weight %s has %s embedded forms, expected %s"
                              % (k, len(entries), dimension))

    field = RealField(bits)
    charpoly = CuspForms(1, int(k)).hecke_matrix(2).charpoly()
    roots = sorted(_decimal(field(root))
                   for root in charpoly.roots(ring=AA, multiplicities=False))
    got = [_decimal(entry["a2"]) for entry in entries]
    if len(roots) != len(got):
        raise ArithmeticError("weight %s has %s T_2 roots, expected %s"
                              % (k, len(roots), len(got)))
    tolerance = Decimal(10) ** -50
    for exact_root, pari_root in zip(roots, got):
        if abs(exact_root - pari_root) > tolerance:
            raise ArithmeticError(
                "weight %s PARI a_2 order disagrees with Hecke polynomial: "
                "%s against %s" % (k, pari_root, exact_root))


def _positive_zeros(ldata):
    zeros = pari("lfunzeros")(ldata, SEARCH_HEIGHT, ZERO_MESH)
    positive = [zero for zero in zeros if _decimal(zero) > 0]
    if len(positive) < ZEROS_PER_FORM:
        raise ArithmeticError(
            "only %s positive zeros found up to height %s"
            % (len(positive), SEARCH_HEIGHT))
    return tuple(str(zero) for zero in positive[:ZEROS_PER_FORM])


_DATA = {}


def _data_for_weight(k, digits):
    key = (int(k), int(digits))
    if key in _DATA:
        return _DATA[key]

    bits = _bits(digits)
    _set_pari_precision(bits)
    entries = _lfun_list(k)
    entries.sort(key=lambda entry: _decimal(entry["a2"]))
    _assert_a2_order(k, entries, bits)
    for before, after in zip(entries, entries[1:]):
        if _decimal(before["a2"]) == _decimal(after["a2"]):
            raise ArithmeticError("weight %s has repeated a_2 embeddings" % k)
    for entry in entries:
        entry["zeros"] = _positive_zeros(entry["ldata"])
    _DATA[key] = tuple(entries)
    return _DATA[key]


def _zero_text(k, i, n, working_digits):
    entry = _data_for_weight(k, working_digits)[int(i) - 1]
    return entry["zeros"][int(n) - 1]


def _entry_comment(k, i):
    entry = _data_for_weight(k, COMMENT_DIGITS)[int(i) - 1]
    href = "HREF{%s#%s,2}[$\\chi_{%s,2}$]" % (HECKE_SLUG, k, k)
    if cusp_dimension(k) == 1:
        return "$a_2=%s$, the root of %s." % (
            _short_decimal(entry["a2"]), href)
    return "$a_2$ is root %s of %s in increasing order; $a_2\\approx %s$." % (
        i, href, _short_decimal(entry["a2"]))


class LevelOneCuspFormLZeros(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T324")
    parameters = ("k", "i", "n")
    type = "R"
    digits = 30
    rigour = "heuristic (agreement-checked)"
    files = ("generate.py",)

    def enumerate(self, max_weight=MAX_WEIGHT):
        for k in range(12, max_weight + 1, 2):
            dimension = cusp_dimension(k)
            if dimension == 0:
                continue
            for i in range(1, dimension + 1):
                for n in range(1, ZEROS_PER_FORM + 1):
                    yield {"k": k, "i": i, "n": n}

    def value(self, params, digits):
        k = int(params["k"])
        i = int(params["i"])
        n = int(params["n"])
        return {
            "number": numberdb.agreeing(
                lambda working: _zero_text(k, i, n, working),
                at=WORKING_DIGITS),
            "comment": _entry_comment(k, i),
        }


if __name__ == "__main__":
    _key_from_stdin()
    generator = LevelOneCuspFormLZeros()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message=("level one cusp form L-function zeros for weights up to "
                     "%d, sorted by a_2 and computed at two precisions")
                    % (MAX_WEIGHT,)))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
