"""Regulators of quartic fields -- numberdb.org/T364

    R_K = |det(M)|,

where M is any full-rank minor of the logarithmic embedding matrix of the
unit group of a quartic field K, with a complex place weighted by 2.
The table lists every quartic field with |D| <= 5000. Fields sharing a
discriminant D are distinguished by k, the position of PARI's polredabs
defining polynomial in lexicographic order of its coefficient vector.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --check    # also compare the class number formula with lfunrootres
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The digits are proven. PARI's bnfinit supplies the fundamental units and
class number, and bnfcertify is required to prove them. Each unit is rebuilt
exactly in Sage's number field, checked to be an algebraic integer of norm
+-1, and evaluated by Horner's rule at real or complex ball roots of the
reduced polynomial. The logarithms and determinants are arb's. PARI's
floating bnf.reg is used only as a control.
"""

import os
import sys
from math import floor, log10

import numberdb.sage as numberdb
from sage.libs.pari import pari
from sage.rings.complex_arb import ComplexBallField
from sage.rings.integer_ring import ZZ
from sage.rings.number_field.number_field import NumberField
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField
from sage.rings.real_mpfi import RealIntervalField


#: Bits beyond the requested decimal precision. Measured over all 456 entries
#: at 100 digits on 2026-09-20: the worst regulator ball supports more than
#: 130 digits with this guard.
WORKING_GUARD = 128

#: Every quartic field with absolute discriminant at most this bound is listed.
BOUND = 5000

GROUPS = ("C4", "V4", "D4", "A4", "S4")

EXPECTED_SIGNATURES = {
    (4, 0): 20,
    (2, 1): 180,
    (0, 2): 256,
}

LFUN_DIGITS = 70
AGREE_DIGITS = 40

TABLE = os.environ.get("NUMBERDB_TABLE", "T364")

R = PolynomialRing(QQ, "x")

_FIELDS = {}
_DATA = {}


def _read_key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def reduced_polynomial(poly):
    """PARI's polredabs output, as a monic integral Sage polynomial."""
    coefficients = tuple(QQ(c) for c in pari(poly).polredabs().Vecrev())
    if len(coefficients) != 5 or coefficients[-1] != 1:
        raise ArithmeticError("polredabs of %s is not a monic quartic: %s"
                              % (poly, coefficients))
    if any(c.denominator() != 1 for c in coefficients):
        raise ArithmeticError("polredabs of %s is not integral: %s"
                              % (poly, coefficients))
    return R([ZZ(c) for c in coefficients])


def polynomial_key(f):
    """The coefficient vector order that defines k."""
    coefficients = [ZZ(c) for c in f.list()[:-1]]
    return tuple(reversed(coefficients))


def signature(f):
    r1 = ZZ(pari(f).polsturm())
    return int(r1), int((4 - r1) // 2)


def quartic_fields(bound=BOUND):
    """{D: [f_1, f_2, ...]} for quartic fields with |D| <= bound."""
    if bound in _FIELDS:
        return _FIELDS[bound]

    found = {}
    for group in GROUPS:
        for f in pari('nflist("%s", [1, %d])' % (group, bound)):
            g = pari(f)
            D = ZZ(g.nfdisc())
            if abs(D) > bound:
                raise ArithmeticError("nflist returned %s with discriminant %s"
                                      % (f, D))
            reduced = reduced_polynomial(g)
            found.setdefault(D, set()).add(tuple(ZZ(c) for c in reduced.list()[:-1]))

    table = {
        D: [R(list(coefficients) + [1])
            for coefficients in sorted(polys, key=lambda c: tuple(reversed(c)))]
        for D, polys in found.items()
    }

    if bound == BOUND:
        counts = {}
        for polynomials in table.values():
            for f in polynomials:
                counts[signature(f)] = counts.get(signature(f), 0) + 1
        if counts != EXPECTED_SIGNATURES:
            raise ArithmeticError("nflist found signature counts %s, expected %s"
                                  % (counts, EXPECTED_SIGNATURES))
    _FIELDS[bound] = table
    return table


def field_data(f):
    """Certified arithmetic data for the field of f."""
    key = str(f)
    if key in _DATA:
        return _DATA[key]

    bnf = pari(f).bnfinit(1)
    if bnf.bnfcertify() != 1:
        raise ArithmeticError("bnfcertify did not certify the field of %s" % f)

    K = NumberField(f, "a")
    units = []
    for u in bnf.bnf_get_fu():
        coefficients = [QQ(c) for c in u.lift().Vecrev()]
        units.append(K(R(coefficients)))

    r1, r2 = signature(f)
    rank = r1 + r2 - 1
    if len(units) != rank:
        raise ArithmeticError("expected %d fundamental units for %s, got %d"
                              % (rank, f, len(units)))

    for unit in units:
        if unit.norm() not in (1, -1):
            raise ArithmeticError("%s has norm %s in the field of %s"
                                  % (unit, unit.norm(), f))
        if not unit.is_integral():
            raise ArithmeticError("%s is not integral in the field of %s"
                                  % (unit, f))

    h = ZZ(bnf.bnf_get_no())
    w = ZZ(bnf.bnf_get_tu()[0])
    reg_float = str(bnf.bnf_get_reg())
    data = (K, h, w, units, reg_float)
    _DATA[key] = data
    return data


def real_roots(f, bits):
    RIF = RealIntervalField(bits)
    RB = RealBallField(bits)
    return [RB(root) for root in f.roots(RIF, multiplicities=False)]


def complex_place_roots(f, bits):
    CBF = ComplexBallField(bits)
    roots = f.roots(CBF, multiplicities=False)
    roots = [root for root in roots if not root.imag().contains_zero()]
    chosen = []
    for root in roots:
        if root.imag().lower() > 0:
            chosen.append(root)
    if len(chosen) * 2 != len(roots):
        raise ArithmeticError("could not pair the complex roots of %s" % f)
    return chosen


def embed(unit, root):
    """Evaluate a unit at an embedding, by Horner's rule in balls."""
    field = root.parent()
    value = field(0)
    for coefficient in reversed(unit.polynomial().list()):
        value = value * root + field(QQ(coefficient))
    return value


def determinant(rows):
    """The determinant for sizes 1, 2 and 3, without asking Sage for matrices."""
    if len(rows) == 1:
        return rows[0][0]
    if len(rows) == 2:
        return rows[0][0] * rows[1][1] - rows[0][1] * rows[1][0]
    if len(rows) == 3:
        return (
            rows[0][0] * (rows[1][1] * rows[2][2] - rows[1][2] * rows[2][1])
            - rows[0][1] * (rows[1][0] * rows[2][2] - rows[1][2] * rows[2][0])
            + rows[0][2] * (rows[1][0] * rows[2][1] - rows[1][1] * rows[2][0])
        )
    raise ArithmeticError("quartic fields have unit rank at most 3, not %d"
                          % len(rows))


def _finite(ball):
    if not ball.is_finite():
        raise ArithmeticError("the computation returned a non-finite ball")
    return ball


def supported_digits(ball):
    """A conservative decimal digit count from a real ball's relative radius."""
    radius = float(ball.rad())
    centre = float(ball.center())
    if radius == 0.0:
        return 10 ** 9
    scale = max(1.0, abs(centre))
    return max(0, int(floor(-log10(radius / scale))))


def regulator(f, units, bits):
    """The regulator from the logarithmic embedding, as a real ball."""
    rows = []
    for root in real_roots(f, bits):
        rows.append([embed(unit, root).abs().log() for unit in units])
    for root in complex_place_roots(f, bits):
        rows.append([2 * embed(unit, root).abs().log() for unit in units])
    rank = len(units)
    if len(rows) != rank + 1:
        raise ArithmeticError("expected %d logarithmic rows for %s, got %d"
                              % (rank + 1, f, len(rows)))
    return _finite(determinant(rows[:rank]).abs())


def galois_label(f):
    index = ZZ(pari(f).polgalois()[2])
    labels = {
        1: r"$C_4$ (4T1)",
        2: r"$C_2\times C_2$ (4T2)",
        3: r"$D_4$ (4T3)",
        4: r"$A_4$ (4T4)",
        5: r"$S_4$ (4T5)",
    }
    try:
        return labels[int(index)]
    except KeyError as exc:
        raise ArithmeticError("unexpected quartic Galois group index %s for %s"
                              % (index, f)) from exc


def lmfdb_label(D, k, f):
    r1, _r2 = signature(f)
    return "4.%d.%d.%d" % (r1, abs(ZZ(D)), k)


def poly_latex(poly, var="a"):
    coefficients = [QQ(c) for c in poly.list()]
    d = ZZ(1)
    for c in coefficients:
        d = d.lcm(c.denominator())
    numerators = [ZZ(c * d) for c in coefficients]
    terms = []
    for i in range(len(numerators) - 1, -1, -1):
        n = numerators[i]
        if n == 0:
            continue
        power = "" if i == 0 else (var if i == 1 else "%s^%d" % (var, i))
        magnitude = abs(n)
        body = ("" if magnitude == 1 and i > 0 else str(magnitude)) + power
        terms.append(("-" if n < 0 else ("+" if terms else "")) + body)
    text = "".join(terms) or "0"
    return text if d == 1 else r"\tfrac{1}{%d}(%s)" % (d, text)


def named_field(D, f):
    if D == 125:
        return r"$K=\mathbb{Q}(\zeta_5)$"
    if D == 144:
        return r"$K=\mathbb{Q}(\zeta_{12})$"
    if D == 256:
        return r"$K=\mathbb{Q}(\zeta_8)$"
    if D == 2304 and str(f) == "x^4 + 9":
        return r"$K=\mathbb{Q}(\zeta_{12},\sqrt{3})$"
    return None


def comment(D, k, f, h, w):
    r1, r2 = signature(f)
    parts = [
        "$%s=0$" % poly_latex(f),
        r"signature $(%d,%d)$" % (r1, r2),
        galois_label(f),
        r"$h_K=%d$" % h,
        r"$w_K=%d$" % w,
        "LMFDB %s" % lmfdb_label(D, k, f),
    ]
    name = named_field(int(D), f)
    if name:
        parts.append(name)
    return "; ".join(parts)


def residue_from_class_number_formula(D, h, w, signature_pair, reg):
    r1, r2 = signature_pair
    RB = reg.parent()
    numerator = (RB(2) ** r1) * ((2 * RB.pi()) ** r2) * h * reg
    return _finite(numerator / (w * RB(abs(ZZ(D))).sqrt()))


def residue_lfun(f, digits=LFUN_DIGITS):
    pari.set_real_precision(digits)
    answer = pari("lfunrootres(lfuncreate(%s))" % f)
    series = answer[0][0][1]
    return RealBallField(numberdb.bits(digits))(str(pari.polcoef(series, -1)))


def check_independent(bound=BOUND, digits=100):
    fields = quartic_fields(bound)
    bits = numberdb.bits(digits, losing=WORKING_GUARD)
    tolerance = RealBallField(64)(10) ** (-AGREE_DIGITS)
    checked = 0
    worst_supported = None
    worst_at = None
    for D in sorted(fields, key=lambda d: (abs(d), d < 0, d)):
        for k, f in enumerate(fields[D], 1):
            _K, h, w, units, reg_float = field_data(f)
            reg = regulator(f, units, bits)
            kappa = residue_from_class_number_formula(D, h, w, signature(f), reg)
            check = residue_lfun(f)
            if not (kappa - check).abs() < tolerance:
                raise ArithmeticError(
                    "D = %s, k = %s: class number formula gives %s, "
                    "lfunrootres gives %s" % (D, k, kappa, check)
                )
            control = RealBallField(80)(reg_float)
            if not (reg - control).abs() < RealBallField(64)(10) ** (-12):
                raise ArithmeticError(
                    "D = %s, k = %s: ball regulator %s does not agree with "
                    "PARI bnf.reg %s" % (D, k, reg, reg_float)
                )
            supported = supported_digits(reg)
            if worst_supported is None or supported < worst_supported:
                worst_supported = supported
                worst_at = (D, k)
            checked += 1
    return checked, worst_supported, worst_at


class QuarticRegulators(numberdb.Generator):
    table = TABLE
    parameters = ("D", "k")
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self, bound=BOUND):
        fields = quartic_fields(bound)
        for D in sorted(fields, key=lambda d: (abs(d), d < 0, d)):
            for k in range(1, len(fields[D]) + 1):
                yield {"D": int(D), "k": k}

    def value(self, params, digits):
        D, k = ZZ(params["D"]), ZZ(params["k"])
        fields = quartic_fields()
        if D not in fields or not 1 <= k <= len(fields[D]):
            raise ValueError("no quartic field with D = %s, k = %s and |D| <= %d"
                             % (D, k, BOUND))
        f = fields[D][k - 1]
        _K, h, w, units, _reg_float = field_data(f)
        bits = numberdb.bits(digits, losing=WORKING_GUARD)
        return {
            "number": regulator(f, units, bits),
            "comment": comment(D, k, f, h, w),
        }


if __name__ == "__main__":
    _read_key_from_stdin()
    generator = QuarticRegulators()
    if "--check" in sys.argv:
        checked, supported, where = check_independent()
        print("checked %d fields against lfunrootres and bnf.reg" % checked)
        print("worst regulator ball supports %s digits at D=%s, k=%s"
              % (supported, where[0], where[1]))
    elif "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(generator.publish(
            message=("regulators of the quartic fields with |D| <= %d from "
                     "units certified by bnfcertify and evaluated in ball "
                     "arithmetic" % BOUND)))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
