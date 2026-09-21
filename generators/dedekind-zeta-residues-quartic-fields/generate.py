"""Residues of Dedekind zeta functions of quartic fields -- numberdb.org/T365.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

Under this repository's build wrapper:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
        agents/sage.sh generators/dedekind-zeta-residues-quartic-fields/generate.py
"""

import os
import sys
from itertools import permutations

import numberdb.sage as numberdb
from sage.libs.pari import pari
from sage.rings.complex_arb import ComplexBallField
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


BOUND = 5000
EXPECTED_FIELDS = 456
DIGITS = 100
WORKING_GUARD = 192
PARI_DIGITS = 130

GROUPS = (
    ("C4", "4T1"),
    ("V4", "4T2"),
    ("D4", "4T3"),
    ("A4", "4T4"),
    ("S4", "4T5"),
)

QQX = PolynomialRing(QQ, "x")
X = QQX.gen()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def _sage_polynomial(text):
    return QQX(str(text).replace("^", "**"))


def _pari_polynomial(poly):
    return str(poly).replace("^", "**")


def _coeff_key(poly):
    return tuple(poly[i] for i in range(poly.degree() - 1, -1, -1))


def _pari(expr):
    return pari(expr.replace("**", "^"))


def _bnf_data(poly):
    expr = _pari_polynomial(poly)
    data = _pari(
        f"my(b=bnfinit({expr}, 1)); "
        "[bnfcertify(b), b.no, b.tu[1], "
        "vector(length(b.fu), i, lift(b.fu[i]))]"
    )
    return {
        "certified": int(data[0]),
        "class_number": int(data[1]),
        "roots_of_unity": int(data[2]),
        "units": [_sage_polynomial(unit) for unit in data[3]],
    }


def _pari_int(expr):
    return int(_pari(expr))


def _field_discriminant(poly):
    return _pari_int(f"nfdisc({_pari_polynomial(poly)})")


def _signature(poly):
    sign = _pari(f"nfinit({_pari_polynomial(poly)}).sign")
    return int(sign[0]), int(sign[1])


def _field_label(degree, r1, discriminant, index):
    return f"{degree}.{r1}.{abs(discriminant)}.{index}"


def _poly_display(poly, variable="a"):
    text = str(poly).replace("*", "")
    if variable != "x":
        text = text.replace("x", variable)
    return text


def _complex_rows(poly, field):
    ring = PolynomialRing(field, "x")
    roots = ring(poly).roots(multiplicities=False)
    real = []
    complex_positive = []
    for root in roots:
        imag = root.imag()
        if imag.contains_zero():
            real.append(root.real())
        else:
            center = imag.center()
            if center > 0:
                complex_positive.append(root)
    real.sort(key=lambda z: z.center())
    complex_positive.sort(key=lambda z: (z.real().center(), z.imag().center()))
    return real, complex_positive


def _evaluate(poly, z):
    total = z.parent()(0)
    for coefficient in reversed(poly.list()):
        total = total * z + z.parent()(coefficient)
    return total


def _determinant(rows):
    if not rows:
        return None
    n = len(rows)
    total = rows[0][0].parent()(0)
    for perm in permutations(range(n)):
        inversions = sum(
            1
            for i in range(n)
            for j in range(i + 1, n)
            if perm[i] > perm[j]
        )
        term = rows[0][perm[0]]
        for i in range(1, n):
            term *= rows[i][perm[i]]
        total += -term if inversions % 2 else term
    return abs(total)


def _regulator(poly, units, bits):
    field = ComplexBallField(bits)
    real_roots, complex_roots = _complex_rows(poly, field)
    r1, r2 = _signature(poly)
    if len(real_roots) != r1 or len(complex_roots) != r2:
        raise ValueError(
            f"{poly}: roots gave {(len(real_roots), len(complex_roots))}, "
            f"PARI gave {(r1, r2)}"
        )

    rank = r1 + r2 - 1
    if rank == 0:
        return RealBallField(bits)(1)
    rows = []
    for root in real_roots:
        rows.append([_evaluate(unit, field(root)).abs().log() for unit in units])
    for root in complex_roots:
        rows.append([
            2 * _evaluate(unit, root).abs().log()
            for unit in units
        ])
    if len(rows) <= rank:
        chosen = rows
    else:
        chosen = rows[:rank]
    if len(chosen) != rank or any(len(row) != rank for row in chosen):
        raise ValueError(f"{poly}: regulator matrix has shape {len(chosen)}x{len(units)}")
    return _determinant(chosen)


def _entry_comment(field):
    signature = f"$({field['r1']},{field['r2']})$"
    return (
        f"${_poly_display(field['poly'])}=0$; signature {signature}; "
        f"{field['group']}; $h_K={field['class_number']}$; "
        f"$w_K={field['roots_of_unity']}$; LMFDB {field['lmfdb_label']}"
    )


class QuarticDedekindZetaResidues(numberdb.Generator):
    table = "T365"
    parameters = ("D", "k")
    type = "R"
    digits = DIGITS
    rigour = "proven"

    _fields = None
    _by_identity = None

    def fields(self):
        if self._fields is not None:
            return self._fields

        found = {}
        for group_name, group_label in GROUPS:
            for raw in _pari(f'nflist("{group_name}", [1, {BOUND}])'):
                reduced = _sage_polynomial(_pari(f"polredabs({raw})"))
                discriminant = _field_discriminant(reduced)
                if abs(discriminant) > BOUND:
                    continue
                key = str(reduced)
                if key in found and found[key]["group"] != group_label:
                    raise ValueError(f"{reduced}: seen in two Galois groups")
                r1, r2 = _signature(reduced)
                found[key] = {
                    "poly": reduced,
                    "D": discriminant,
                    "group": group_label,
                    "r1": r1,
                    "r2": r2,
                }

        grouped = {}
        for field in found.values():
            grouped.setdefault(field["D"], []).append(field)

        rows = []
        for discriminant in sorted(grouped, key=lambda d: (abs(d), d < 0)):
            fields = sorted(grouped[discriminant], key=lambda row: _coeff_key(row["poly"]))
            for index, field in enumerate(fields, 1):
                bnf = _bnf_data(field["poly"])
                if bnf["certified"] != 1:
                    raise ValueError(f"{field['poly']}: bnfcertify failed")
                field = dict(field)
                field["k"] = index
                field["class_number"] = bnf["class_number"]
                field["roots_of_unity"] = bnf["roots_of_unity"]
                field["units"] = bnf["units"]
                field["lmfdb_label"] = _field_label(4, field["r1"], field["D"], index)
                rows.append(field)

        if len(rows) != EXPECTED_FIELDS:
            raise ValueError(f"expected {EXPECTED_FIELDS} fields, found {len(rows)}")
        counts = {
            (4, 0): sum(1 for row in rows if (row["r1"], row["r2"]) == (4, 0)),
            (2, 1): sum(1 for row in rows if (row["r1"], row["r2"]) == (2, 1)),
            (0, 2): sum(1 for row in rows if (row["r1"], row["r2"]) == (0, 2)),
        }
        if counts != {(4, 0): 20, (2, 1): 180, (0, 2): 256}:
            raise ValueError(f"unexpected signature counts: {counts}")

        self._fields = rows
        self._by_identity = {(row["D"], row["k"]): row for row in rows}
        return rows

    def enumerate(self, bound=BOUND):
        if bound != BOUND:
            raise ValueError(f"this generator is written for bound {BOUND}")
        for field in self.fields():
            yield {"D": field["D"], "k": field["k"]}

    def value(self, params, digits):
        if self._by_identity is None:
            self.fields()
        identity = (int(params["D"]), int(params["k"]))
        field = self._by_identity.get(identity)
        if field is None:
            raise KeyError(f"no quartic field at D,k={identity}")

        bits = numberdb.bits(digits, losing=WORKING_GUARD)
        ball_field = RealBallField(bits)
        regulator = _regulator(field["poly"], field["units"], bits)
        numerator = (
            (ZZ(2) ** field["r1"])
            * ((2 * ball_field.pi()) ** field["r2"])
            * ball_field(field["class_number"])
            * regulator
        )
        denominator = (
            ball_field(field["roots_of_unity"])
            * ball_field(abs(field["D"])).sqrt()
        )
        value = numerator / denominator
        if not value.is_finite():
            raise ValueError(f"{params}: value is not finite")
        return {"number": value, "comment": _entry_comment(field)}

    def residue_control(self, field):
        pari.set_real_precision(PARI_DIGITS)
        expr = _pari_polynomial(field["poly"])
        return _pari(f"polcoef(lfunrootres(lfuncreate({expr}))[1][1][2], -1)")


def fill_draft_once(generator, message):
    """Fill a fresh prose draft without the client's empty upsert probe."""
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


def main():
    _key_from_stdin()
    generator = QuarticDedekindZetaResidues()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="computed quartic Dedekind zeta residues",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
