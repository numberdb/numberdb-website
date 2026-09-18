"""Petersson norms of level one cusp forms -- numberdb.org/T326.

For each normalised Hecke eigenform f in S_k(SL_2(Z)), this stores the
Petersson norm <f,f>. The eigenforms in each weight are sorted by the embedded
value of a_2, not by Sage's or PARI's raw embedding order.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The values are computed with Sage's petersson_norm method at two working
precisions. PARI's modular-symbol mfpetersson values are used as an
independent check to the stored precision.
"""

from decimal import Decimal
import os
import sys

import numberdb.sage as numberdb
import sage.rings.polynomial.laurent_polynomial_ring
import sage.symbolic.expression
from sage.libs.pari import pari
from sage.misc.verbose import set_verbose
from sage.modular.modform.constructor import CuspForms, Newforms
from sage.rings.complex_mpfr import ComplexField
from sage.rings.integer_ring import ZZ
from sage.rings.qqbar import AA
from sage.rings.real_mpfr import RealField


set_verbose(-2)

MAX_WEIGHT = 40
WORKING_DIGITS = (80, 120)
COMMENT_DIGITS = 80
SAGE_GUARD_BITS = 80
PARI_GUARD_BITS = 80
HECKE_SLUG = "Hecke_polynomials_of_level_one_cusp_forms"
ORDINALS = {
    1: "first",
    2: "second",
    3: "third",
}

_DATA = {}
_PARI_DATA = {}
_COMMENTS = {}
_CHECKED = False


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


def _rows():
    for k in range(12, MAX_WEIGHT + 1, 2):
        dimension = cusp_dimension(k)
        if dimension == 0:
            continue
        for i in range(1, dimension + 1):
            yield ZZ(k), ZZ(i)


def _bits(digits, guard):
    return numberdb.bits(int(digits), losing=int(guard))


def _decimal(value):
    return Decimal(str(value).replace(" ", ""))


def _short_decimal(value):
    return format(_decimal(value), ".16g")


def _ordinal(n):
    return ORDINALS.get(int(n), "%sth" % n)


def _assert_a2_order(k, entries, bits):
    dimension = cusp_dimension(int(k))
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
    for exact_root, embedded_root in zip(roots, got):
        if abs(exact_root - embedded_root) > tolerance:
            raise ArithmeticError(
                "weight %s Sage a_2 order disagrees with Hecke polynomial: "
                "%s against %s" % (k, embedded_root, exact_root))


def _data_for_weight(k, digits):
    key = (int(k), int(digits))
    if key in _DATA:
        return _DATA[key]

    bits = _bits(digits, SAGE_GUARD_BITS)
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
    _assert_a2_order(k, entries, bits)
    for before, after in zip(entries, entries[1:]):
        if _decimal(before["a2"]) == _decimal(after["a2"]):
            raise ArithmeticError("weight %s has repeated a_2 embeddings" % k)

    _DATA[key] = tuple(entries)
    return _DATA[key]


def _petersson_norm_text(k, i, working_digits):
    entry = _data_for_weight(k, working_digits)[int(i) - 1]
    return str(entry["form"].petersson_norm(
        embedding=entry["embedding"],
        prec=entry["bits"]))


def _entry_comment(k, i):
    key = (ZZ(k), ZZ(i))
    if key in _COMMENTS:
        return _COMMENTS[key]
    entry = _data_for_weight(k, COMMENT_DIGITS)[int(i) - 1]
    href = "HREF{%s#%s,2}[$\\chi_{%s,2}$]" % (HECKE_SLUG, k, k)
    if cusp_dimension(int(k)) == 1:
        a2 = entry["form"][2]
        comment = "$a_2=%s$, the root of %s." % (a2, href)
    else:
        comment = (
            "$a_2$ is the %s root of %s in increasing order, with "
            "$a_2\\approx %s$."
            % (_ordinal(i), href, _short_decimal(entry["a2"])))
    _COMMENTS[key] = comment
    return comment


def _set_pari_precision(bits):
    pari("default(realbitprecision, %d)" % int(bits))


def _pari_entries_for_weight(k, digits):
    key = (int(k), int(digits))
    if key in _PARI_DATA:
        return _PARI_DATA[key]

    bits = _bits(digits, PARI_GUARD_BITS)
    _set_pari_precision(bits)
    mf = pari("mfinit([1,%d],0)" % int(k))
    eigenbasis = pari("mfeigenbasis")(mf)
    entries = []

    for orbit_index in range(len(eigenbasis)):
        form = eigenbasis[orbit_index]
        a2 = pari("mfcoefs")(form, 2)[2]
        symbols = pari("mfsymbol")(mf, form)
        petersson = pari("mfpetersson")(symbols)

        try:
            nf = pari("nfinit")(pari("component")(a2, 1))
            embedded_a2 = pari("nfeltembed")(nf, a2)
        except Exception:                           # noqa: BLE001
            entries.append({
                "orbit": orbit_index + 1,
                "embedding": 0,
                "a2": pari("real")(a2),
                "norm": petersson,
            })
            continue

        for embedding_index in range(len(embedded_a2)):
            entries.append({
                "orbit": orbit_index + 1,
                "embedding": embedding_index + 1,
                "a2": pari("real")(embedded_a2[embedding_index]),
                "norm": petersson[embedding_index, embedding_index],
            })

    entries.sort(key=lambda entry: _decimal(entry["a2"]))
    dimension = cusp_dimension(int(k))
    if len(entries) != dimension:
        raise ArithmeticError("PARI weight %s has %s entries, expected %s"
                              % (k, len(entries), dimension))
    _PARI_DATA[key] = tuple(entries)
    return _PARI_DATA[key]


def _check_against_pari():
    for k in range(12, MAX_WEIGHT + 1, 2):
        dimension = cusp_dimension(k)
        if dimension == 0:
            continue
        sage_entries = _data_for_weight(k, WORKING_DIGITS[-1])
        pari_entries = _pari_entries_for_weight(k, WORKING_DIGITS[-1])
        tolerance = Decimal(10) ** -40
        for i, (sage_entry, pari_entry) in enumerate(zip(sage_entries, pari_entries),
                                                     start=1):
            sage_a2 = _decimal(sage_entry["a2"])
            pari_a2 = _decimal(pari_entry["a2"])
            if abs(sage_a2 - pari_a2) > tolerance:
                raise ArithmeticError(
                    "weight %s entry %s has different a_2 order: %s against %s"
                    % (k, i, sage_a2, pari_a2))

            sage_norm = _decimal(sage_entry["form"].petersson_norm(
                embedding=sage_entry["embedding"],
                prec=sage_entry["bits"]))
            pari_norm = _decimal(pari_entry["norm"])
            scale = max(abs(sage_norm), abs(pari_norm), Decimal(1))
            if abs(sage_norm - pari_norm) > tolerance * scale:
                raise ArithmeticError(
                    "weight %s entry %s has different Petersson norms: "
                    "%s against %s" % (k, i, sage_norm, pari_norm))


def _check_global():
    global _CHECKED
    if _CHECKED:
        return
    rows = list(_rows())
    if len(rows) != 24:
        raise ArithmeticError("got %s rows, expected 24" % len(rows))
    _check_against_pari()
    _CHECKED = True


class LevelOneCuspFormPeterssonNorms(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T326")
    parameters = ("k", "i")
    type = "R"
    digits = 30
    rigour = "heuristic (agreement-checked)"
    files = ("generate.py",)

    def enumerate(self, max_weight=MAX_WEIGHT):
        if int(max_weight) != MAX_WEIGHT:
            raise ValueError("this draft covers weights up to %s" % MAX_WEIGHT)
        _check_global()
        for k, i in _rows():
            yield {"k": k, "i": i}

    def value(self, params, digits):
        k = ZZ(params["k"])
        i = ZZ(params["i"])
        if (k, i) not in set(_rows()):
            raise ValueError("row outside this table: k=%s, i=%s" % (k, i))
        return {
            "number": numberdb.agreeing(
                lambda working: _petersson_norm_text(k, i, working),
                at=WORKING_DIGITS),
            "comment": _entry_comment(k, i),
        }


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
        attach(table, name, body, run=run, message=message,
               rigour=generator.rigour)

    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = LevelOneCuspFormPeterssonNorms()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message=("Petersson norms for level one cusp forms with weights "
                     "up to %d, sorted by a_2 and checked against PARI")
                    % (MAX_WEIGHT,)))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
