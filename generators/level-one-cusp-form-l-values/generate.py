"""Special values of the L-functions of level one cusp forms -- numberdb.org/T323.

For each normalised Hecke eigenform f in S_k(SL_2(Z)), this stores the
critical values L(f,s) in arithmetic normalisation. The eigenforms in each
weight are sorted by the embedded value of a_2, not by Sage's or PARI's raw
embedding order.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The values are computed with Sage's Newforms L-series at two working
precisions, using a fresh L-series object for each value. PARI's lfunmf values
were used as an independent check to the stored precision.
"""

from decimal import Decimal
import os
import sys

import numberdb.sage as numberdb
from sage.misc.verbose import set_verbose
from sage.modular.modform.constructor import Newforms
from sage.rings.complex_mpfr import ComplexField


set_verbose(-2)

MAX_WEIGHT = 40
WORKING_DIGITS = (80, 120)
COMMENT_DIGITS = 80
SAGE_GUARD_BITS = 64
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


def _decimal(value):
    return Decimal(str(value).replace(" ", ""))


_DATA = {}


def _data_for_weight(k, digits):
    key = (int(k), int(digits))
    if key in _DATA:
        return _DATA[key]

    bits = numberdb.bits(int(digits), losing=SAGE_GUARD_BITS)
    complex_field = ComplexField(bits)
    forms = Newforms(1, int(k), names="a")

    entries = []
    for orbit_index, form in enumerate(forms):
        a2 = form[2]
        for embedding_index, embedding in enumerate(a2.parent().embeddings(complex_field)):
            embedded_a2 = embedding(a2).real()
            entries.append({
                "orbit": orbit_index + 1,
                "embedding": embedding_index,
                "form": form,
                "bits": bits,
                "a2": embedded_a2,
            })

    entries.sort(key=lambda entry: _decimal(entry["a2"]))
    if len(entries) != cusp_dimension(k):
        raise ArithmeticError("weight %s has %s embedded forms, expected %s"
                              % (k, len(entries), cusp_dimension(k)))
    for before, after in zip(entries, entries[1:]):
        if _decimal(before["a2"]) == _decimal(after["a2"]):
            raise ArithmeticError("weight %s has repeated a_2 embeddings" % k)

    _DATA[key] = tuple(entries)
    return _DATA[key]


def _lvalue_text(k, i, s, working_digits):
    entry = _data_for_weight(k, working_digits)[int(i) - 1]
    lseries = entry["form"].lseries(
        embedding=entry["embedding"], prec=entry["bits"])
    return str(lseries(int(s)))


def _short_decimal(value):
    return format(_decimal(value), ".16g")


def _entry_comment(k, i):
    entry = _data_for_weight(k, COMMENT_DIGITS)[int(i) - 1]
    href = "HREF{%s#%s,2}[$\\chi_{%s,2}$]" % (HECKE_SLUG, k, k)
    if cusp_dimension(k) == 1:
        return "$a_2=%s$, the root of %s." % (
            _short_decimal(entry["a2"]), href)
    return "$a_2$ is root %s of %s in increasing order; $a_2\\approx %s$." % (
        i, href, _short_decimal(entry["a2"]))


class LevelOneCuspFormLValues(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T323")
    parameters = ("k", "i", "s")
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
                for s in range(1, k):
                    if k % 4 == 2 and s == k // 2:
                        continue
                    yield {"k": k, "i": i, "s": s}

    def value(self, params, digits):
        k = int(params["k"])
        i = int(params["i"])
        s = int(params["s"])
        return {
            "number": numberdb.agreeing(
                lambda working: _lvalue_text(k, i, s, working),
                at=WORKING_DIGITS),
            "comment": _entry_comment(k, i),
        }


if __name__ == "__main__":
    _key_from_stdin()
    generator = LevelOneCuspFormLValues()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message=("level one cusp form L-values for weights up to %d, "
                     "sorted by a_2 and computed at two precisions")
                    % (MAX_WEIGHT,)))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
