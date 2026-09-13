r"""Volumes of the hyperbolic Coxeter simplices -- numberdb.org/T224

This first fill stores the 23 noncompact, rank-4 Coxeter simplices in
hyperbolic 3-space, the Koszul-type tetrahedra of Kozma and Szirmai's table.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The values are computed in ball arithmetic from the Lobachevsky function and
Kellerhals's complete-orthoscheme formula.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.real_arb import RealBallField


WORKING_GUARD = 128
CHECK_GUARD = 160
BOUNDARY_TOLERANCE = "1e-115"


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def fields(bits):
    return RealBallField(bits), ComplexBallField(bits)


def atan_ball(x, RB, CB):
    """atan(x), using a complex logarithm because RealBall has no atan here."""
    x = RB(x)
    return (CB(1, x) / CB(1, -x)).log().imag() / 2


def arccot_ball(x, RB, CB):
    return atan_ball(1 / RB(x), RB, CB)


def lobachevsky(theta, RB, CB):
    """Lobachevsky's Lambda(theta) = Im Li_2(exp(2 i theta)) / 2."""
    theta = RB(theta)
    pi = RB.pi()
    if (theta / pi).contains_integer():
        return RB(0)
    tolerance = RB(BOUNDARY_TOLERANCE)
    for point in (pi / 2, -pi / 2):
        if (theta - point).contains_zero() and RB((theta - point).abs().upper()) < tolerance:
            return RB(0)
    z = (CB(0, 2) * CB(theta)).exp()
    return z.polylog(2).imag() / 2


def orthoscheme(alpha, beta, gamma, RB, CB):
    """Kellerhals's volume formula for a complete hyperbolic orthoscheme."""
    pi = RB.pi()
    alpha = RB(alpha)
    beta = RB(beta)
    gamma = RB(gamma)
    numerator = beta.cos()**2 - alpha.sin()**2 * gamma.sin()**2
    theta = atan_ball(numerator.sqrt() / (alpha.cos() * gamma.cos()), RB, CB)
    return (
        lobachevsky(alpha + theta, RB, CB)
        - lobachevsky(alpha - theta, RB, CB)
        + lobachevsky(gamma + theta, RB, CB)
        - lobachevsky(gamma - theta, RB, CB)
        + lobachevsky(pi / 2 + beta - theta, RB, CB)
        + lobachevsky(pi / 2 - beta - theta, RB, CB)
        + 2 * lobachevsky(pi / 2 - theta, RB, CB)
    ) / 4


def coxeter_orthoscheme(p, q, r, RB, CB):
    pi = RB.pi()
    return orthoscheme(pi / RB(p), pi / RB(q), pi / RB(r), RB, CB)


def values(bits):
    RB, CB = fields(bits)
    pi = RB.pi()
    L3 = lobachevsky(pi / 3, RB, CB)
    L4 = lobachevsky(pi / 4, RB, CB)
    sqrt2 = RB(2).sqrt()
    phi = (RB(1) + RB(5).sqrt()) / 2

    O = lambda p, q, r: coxeter_orthoscheme(p, q, r, RB, CB)
    A = lambda x: atan_ball(x, RB, CB)
    C = lambda x: arccot_ball(x, RB, CB)
    V = {}

    V["[3,3,6]"] = L3 / 8
    V["[3,6,3]"] = L3 / 2
    V["[6,3^{[3]}]"] = 3 * L3 / 2
    V["[3^{[3,3]}]"] = 3 * L3
    V["[3,3^{[3]}]"] = L3 / 4
    V["[6,3,6]"] = 3 * L3 / 4
    V["[4,3,6]"] = 5 * L3 / 16
    V["[4,3^{[3]}]"] = 5 * L3 / 8
    V["[6,3^{1,1}]"] = 5 * L3 / 8
    V["[3^{[]x[]}]"] = 5 * L3 / 4
    V["[(3,6)^{[2]}]"] = 5 * L3 / 2

    V["[3,4,4]"] = L4 / 6
    V["[3,4^{1,1}]"] = L4 / 3
    V["[(3^2,4^2)]"] = 2 * L4 / 3
    V["[4,4,4]"] = L4 / 2
    V["[4^{1,1,1}]"] = L4
    V["[4^{[4]}]"] = 2 * L4

    V["[5,3,6]"] = O(5, 3, 6)
    V["[5,3^{[3]}]"] = 2 * V["[5,3,6]"]
    V["[(3^3,6)]"] = O(3, 3, 6) + O(3, 4, 4) + O(4, 4, 3) + O(3, 6, 3)
    V["[(3,4,3,6)]"] = (
        O(4, 3, 6)
        + orthoscheme(pi / 4, A(sqrt2), C(sqrt2), RB, CB)
        + orthoscheme(C(1 / sqrt2), pi / 2 - A(sqrt2), pi / 3, RB, CB)
        + O(3, 6, 3)
    )
    V["[(3,5,3,6)]"] = (
        O(5, 3, 6)
        + orthoscheme(pi / 5, A(phi), C(phi), RB, CB)
        + orthoscheme(C(1 / phi), pi / 2 - A(phi), pi / 3, RB, CB)
        + O(3, 6, 3)
    )
    V["[(3,4^3)]"] = (
        O(3, 4, 4)
        + O(4, 4, 4)
        + orthoscheme(pi / 3, A(1 / sqrt2), C(1 / sqrt2), RB, CB)
        + orthoscheme(C(sqrt2), pi / 2 - A(1 / sqrt2), pi / 4, RB, CB)
    )
    return V


ROWS = [
    ("[3,3,6]", r"$\overline{V}_3$", "0.0422892336"),
    ("[3,6,3]", r"$\overline{Y}_3$", "0.1691569344"),
    ("[6,3^{[3]}]", r"$\overline{VP}_3$", "0.5074708032"),
    ("[3^{[3,3]}]", r"$\widehat{PP}_3$", "1.0149416064"),
    ("[3,3^{[3]}]", r"$\overline{P}_3$", "0.0845784672"),
    ("[6,3,6]", r"$\overline{Z}_3$", "0.2537354016"),
    ("[4,3,6]", r"$\overline{BV}_3$", "0.1057230840"),
    ("[4,3^{[3]}]", r"$\overline{BP}_3$", "0.2114461680"),
    ("[6,3^{1,1}]", r"$\overline{DV}_3$", "0.2114461680"),
    ("[3^{[]x[]}]", r"$\overline{DP}_3$", "0.4228923360"),
    ("[(3,6)^{[2]}]", r"$\widehat{VV}_3$", "0.8457846720"),
    ("[3,4,4]", r"$\overline{R}_3$", "0.0763304662"),
    ("[3,4^{1,1}]", r"$\overline{O}_3$", "0.1526609324"),
    ("[(3^2,4^2)]", r"$\widehat{BR}_3$", "0.3053218647"),
    ("[4,4,4]", r"$\overline{N}_3$", "0.2289913985"),
    ("[4^{1,1,1}]", r"$\overline{M}_3$", "0.4579827971"),
    ("[4^{[4]}]", r"$\widehat{RR}_3$", "0.9159655942"),
    ("[5,3,6]", r"$\overline{HV}_3$", "0.1715016613"),
    ("[5,3^{[3]}]", r"$\overline{HP}_3$", "0.3430033226"),
    ("[(3^3,6)]", r"$\widehat{AV}_3$", "0.3641071004"),
    ("[(3,4,3,6)]", r"$\widehat{BV}_3$", "0.5258402692"),
    ("[(3,5,3,6)]", r"$\widehat{HV}_3$", "0.6729858045"),
    ("[(3,4^3)]", r"$\widehat{CR}_3$", "0.5562821156"),
]


VOLUME_COMMENTS = {
    "[3,3,6]": r"$\Lambda(\pi/3)/8$",
    "[3,6,3]": (
        r"$\Lambda(\pi/3)/2$, which is the covolume of "
        r"$\mathrm{PSL}_2(\mathbb{Z}[\omega])$ in "
        r"HREF{Covolumes_of_the_Bianchi_groups#-3}[the Bianchi covolume table]"
    ),
    "[6,3^{[3]}]": r"$3\Lambda(\pi/3)/2$",
    "[3^{[3,3]}]": r"$3\Lambda(\pi/3)=\mathrm{Cl}_2(\pi/3)$",
    "[3,3^{[3]}]": r"$\Lambda(\pi/3)/4$",
    "[6,3,6]": r"$3\Lambda(\pi/3)/4$",
    "[4,3,6]": r"$5\Lambda(\pi/3)/16$",
    "[4,3^{[3]}]": r"$5\Lambda(\pi/3)/8$",
    "[6,3^{1,1}]": r"$5\Lambda(\pi/3)/8$",
    "[3^{[]x[]}]": r"$5\Lambda(\pi/3)/4$",
    "[(3,6)^{[2]}]": r"$5\Lambda(\pi/3)/2$",
    "[3,4,4]": r"$\Lambda(\pi/4)/6$",
    "[3,4^{1,1}]": r"$\Lambda(\pi/4)/3$",
    "[(3^2,4^2)]": (
        r"$2\Lambda(\pi/4)/3$, which is the covolume of "
        r"$\mathrm{PSL}_2(\mathbb{Z}[i])$ in "
        r"HREF{Covolumes_of_the_Bianchi_groups#-4}[the Bianchi covolume table]"
    ),
    "[4,4,4]": r"$\Lambda(\pi/4)/2$",
    "[4^{1,1,1}]": r"$\Lambda(\pi/4)$",
    "[4^{[4]}]": (
        r"$2\Lambda(\pi/4)$, which is "
        r"HREF{Values_of_the_Clausen_functions_at_rational_multiples_of#2,1/2}"
        r"[Catalan's constant $G$]"
    ),
}


def decimal_enclosure(text, RB):
    mantissa = text.lower().split("e", 1)[0]
    if "." not in mantissa:
        return RB(text)
    places = len(mantissa.split(".", 1)[1])
    return RB(text).add_error(RB(10) ** (-places))


def entry_comment(diagram, witt, _source_decimal):
    intro = "Kozma and Szirmai write this simplex as %s." % (witt,)
    if diagram not in VOLUME_COMMENTS:
        return intro
    return "%s Its volume is %s." % (intro, VOLUME_COMMENTS[diagram])


def check_identities(digits=100):
    bits = numberdb.bits(digits, losing=CHECK_GUARD)
    RB, _ = fields(bits)
    computed = values(bits)
    for diagram, _, source in ROWS:
        if not (computed[diagram] - decimal_enclosure(source, RB)).contains_zero():
            raise ArithmeticError(
                "%s does not overlap source decimal %s: %s"
                % (diagram, source, computed[diagram])
            )

    clausen = numberdb.table("T175")
    cl2_pi_over_3 = decimal_enclosure(clausen["Numbers"]["2"]["1/3"]["number"], RB)
    catalan = decimal_enclosure(clausen["Numbers"]["2"]["1/2"]["number"], RB)
    if not (computed["[3^{[3,3]}]"] - cl2_pi_over_3).contains_zero():
        raise ArithmeticError("regular ideal tetrahedron does not match T175")
    if not (computed["[4^{[4]}]"] - catalan).contains_zero():
        raise ArithmeticError("ideal octahedral value does not match T175")

    bianchi = numberdb.table("T221")
    d3 = decimal_enclosure(bianchi["Numbers"]["-3"]["number"], RB)
    d4 = decimal_enclosure(bianchi["Numbers"]["-4"]["number"], RB)
    if not (computed["[3,3,6]"] * RB(4) - d3).contains_zero():
        raise ArithmeticError("[3,3,6] is not one quarter of T221 D=-3")
    if not (computed["[3,4,4]"] * RB(4) - d4).contains_zero():
        raise ArithmeticError("[3,4,4] is not one quarter of T221 D=-4")
    if not (computed["[3,6,3]"] - d3).contains_zero():
        raise ArithmeticError("[3,6,3] is not T221 D=-3")
    if not (computed["[(3^2,4^2)]"] - d4).contains_zero():
        raise ArithmeticError("[(3^2,4^2)] is not T221 D=-4")

    print("checked %d source decimals" % len(ROWS))
    print("[3^{[3,3]}] matches T175 Cl_2(pi/3)")
    print("[4^{[4]}] matches T175 Catalan's constant")
    print("[3,3,6] and [3,4,4] match quarters of T221")
    print("[3,6,3] and [(3^2,4^2)] match T221 covolumes")


class HyperbolicCoxeterSimplexVolumes(numberdb.Generator):
    table = os.environ.get("NUMBERDB_TABLE") or "T224"
    parameters = ("n", "diagram")
    type = "R"
    digits = 100
    rigour = "proven"
    files = ("generate.py",)

    def enumerate(self):
        for diagram, _, _ in ROWS:
            yield {"n": "3", "diagram": diagram}

    def value(self, params, digits):
        bits = numberdb.bits(digits, losing=WORKING_GUARD)
        diagram = params["diagram"]
        by_diagram = values(bits)
        witt = dict((diagram, witt) for diagram, witt, _ in ROWS)[diagram]
        source = dict((diagram, source) for diagram, _, source in ROWS)[diagram]
        return {
            "number": by_diagram[diagram],
            "comment": entry_comment(diagram, witt, source),
        }


def fill_draft_once(generator, message):
    """Fill a fresh draft without the empty upsert probe."""
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

    files = _source_files(generator)
    stored = []
    for name, body in sorted(files.items()):
        attach(table, name, body, run=run, message=message,
               rigour=generator.rigour)
        stored.append(name)

    return {
        "tid": answer.get("tid", table),
        "revision": answer.get("revision"),
        "entries": len(entries),
        "files": stored,
    }


if __name__ == "__main__":
    _key_from_stdin()
    generator = HyperbolicCoxeterSimplexVolumes()
    if os.environ.get("NUMBERDB_CHECK_IDENTITIES") == "1":
        check_identities(generator.digits)
    elif "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="noncompact hyperbolic Coxeter simplex volumes"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
