"""Bifurcation points of the period-doubling cascade -- numberdb.org/T168.

For f_r(x) = r*x*(1 - x), this generator stores the period-doubling
bifurcation parameters a_n, the superstable parameters s_n, the band-merging
Misiurewicz parameters m_n, and the accumulation point r_infinity, in both the
r-normalisation and the quadratic-polynomial c-normalisation c = -r*(r-2)/4.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The finite rows are computed by Newton iteration at guarded precision and
recomputed at a second precision before the draft is filled. The accumulation
point is transcribed from published decimal expansions and is stored at lower
precision than the finite rows.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.rational_field import QQ
from sage.rings.real_mpfr import RealField


DIGITS = 100
R_INFINITY_DIGITS = 95

# Measured at 100 digits: recomputing the finite rows with 760 and 980 working
# bits gives the same 100 written digits, and the largest defining-equation
# residual is below 1e-180.
WORKING_BITS = numberdb.bits(DIGITS, losing=650)
RR = RealField(WORKING_BITS)

R_INFINITY = (
    "3.569945671870944901842005151386498936763836911514832378107975"
    "5299213628875001367775263210342163"
)

A_SEEDS = {
    1: "3.0",
    2: "3.4494897427831780981972840747058913919659474806567",
    3: "3.5440903595519228536159659866048045405830998454446",
    4: "3.5644072660954325977735575865289824506577347383790",
    5: "3.5687594195438264312982102800253153703569938395808",
    6: "3.5696916098013967142882687062954666071865704082915",
    7: "3.5698912593781204873202712005854493897958251233744",
    8: "3.5699340183739764011848556018871913712192830120006",
    9: "3.5699431760484016363544429761623177495408066656406",
}

S_SEEDS = {
    1: "2.0",
    2: "3.2360679774997896964091736687312762354406183596115",
    3: "3.4985616993277015199989453819445392678868790365444",
    4: "3.5546408627688248653660818519484917918272000141143",
    5: "3.5666673798562685139726311574553680919379540660014",
    6: "3.5692435316371103378082495109127455581766294410483",
    7: "3.5697952937499446205153525296069779756774591767650",
    8: "3.5699134654223485148409735196680118263186321889074",
    9: "3.5699387742333054877934460675629869263611501462433",
}

M_SEEDS = {
    1: "3.6785735104283222651037051293065732008483574921952",
    2: "3.5925721841069786491021528020446585225820627047014",
    3: "3.5748049387592078506132871872648545691516976759616",
    4: "3.5709859403416148051219210346235808742479308140338",
    5: "3.5701684724963757057511275186242231896827701762576",
}

POINTS = (
    tuple("a%d" % n for n in range(1, 10))
    + tuple("s%d" % n for n in range(1, 10))
    + tuple("m%d" % n for n in range(1, 6))
    + ("r-infinity",)
)

_CACHE = {}


def set_working_bits(bits):
    """Use another RealField for agreement checks."""
    global WORKING_BITS, RR, _CACHE
    WORKING_BITS = int(bits)
    RR = RealField(WORKING_BITS)
    _CACHE = {}


def period(point):
    if point[0] in ("a", "s"):
        n = int(point[1:])
        return 2 ** (n - 1)
    if point[0] == "m":
        n = int(point[1:])
        return 2 ** (n - 1)
    return None


def decimal(value, digits):
    return RR(value).str(digits=int(digits))


def c_parameter(r):
    r = RR(r)
    return -r * (r - 2) / 4


def orbit_derivatives(x, r, steps):
    """f_r^steps(x) and derivatives needed for the multiplier equation."""
    y = x
    dx = RR(1)
    dr = RR(0)
    dxx = RR(0)
    dxr = RR(0)
    for _ in range(steps):
        a = 1 - 2 * y
        y_next = r * y * (1 - y)
        dx_next = r * a * dx
        dr_next = y * (1 - y) + r * a * dr
        dxx_next = r * (a * dxx - 2 * dx * dx)
        dxr_next = a * dx + r * (a * dxr - 2 * dr * dx)
        y, dx, dr, dxx, dxr = y_next, dx_next, dr_next, dxx_next, dxr_next
    return y, dx, dr, dxx, dxr


def critical_orbit_with_dr(r, steps):
    y = RR(1) / 2
    dr = RR(0)
    for _ in range(steps):
        dr = y * (1 - y) + r * (1 - 2 * y) * dr
        y = r * y * (1 - y)
    return y, dr


def cycle_seed(r, steps):
    x = RR("0.54321")
    for _ in range(5000 + 20 * steps):
        x = r * x * (1 - x)
    return x


def solve_bifurcation(n, digits=DIGITS):
    """a_n: f_r^p(x)=x and (f_r^p)'(x)=-1, p=2^(n-1)."""
    if n == 1:
        return RR(3)
    p = 2 ** (n - 1)
    r = RR(A_SEEDS[n])
    midpoint = (RR(A_SEEDS[n - 1]) + r) / 2
    x = cycle_seed(midpoint, p)
    target = RR(10) ** (-(int(digits) + 80))
    for _ in range(60):
        y, dx, dr, dxx, dxr = orbit_derivatives(x, r, p)
        f1 = y - x
        f2 = dx + 1
        j11 = dx - 1
        j12 = dr
        j21 = dxx
        j22 = dxr
        det = j11 * j22 - j12 * j21
        step_x = (f1 * j22 - j12 * f2) / det
        step_r = (j11 * f2 - f1 * j21) / det
        x -= step_x
        r -= step_r
        if max(abs(step_x), abs(step_r)) < target:
            break
    y, dx, _, _, _ = orbit_derivatives(x, r, p)
    if abs(y - x) > target or abs(dx + 1) > target:
        raise ArithmeticError("a_%d did not satisfy its equations" % n)
    return r


def solve_superstable(n, digits=DIGITS):
    """s_n: f_r^p(1/2)=1/2, p=2^(n-1)."""
    if n == 1:
        return RR(2)
    p = 2 ** (n - 1)
    r = RR(S_SEEDS[n])
    target = RR(10) ** (-(int(digits) + 80))
    for _ in range(60):
        y, dr = critical_orbit_with_dr(r, p)
        step = (y - RR(1) / 2) / dr
        r -= step
        if abs(step) < target:
            break
    y, _ = critical_orbit_with_dr(r, p)
    if abs(y - RR(1) / 2) > target:
        raise ArithmeticError("s_%d did not satisfy its equation" % n)
    return r


def solve_misiurewicz(n, digits=DIGITS):
    """m_n: f^(2^n+1+2^(n-1))(1/2)=f^(2^n+1)(1/2)."""
    p = 2 ** (n - 1)
    preperiod = 2 ** n + 1
    r = RR(M_SEEDS[n])
    target = RR(10) ** (-(int(digits) + 80))
    for _ in range(60):
        y1, dr1 = critical_orbit_with_dr(r, preperiod)
        y2 = y1
        dr2 = dr1
        for _ in range(p):
            dr2 = y2 * (1 - y2) + r * (1 - 2 * y2) * dr2
            y2 = r * y2 * (1 - y2)
        step = (y2 - y1) / (dr2 - dr1)
        r -= step
        if abs(step) < target:
            break
    y1, _ = critical_orbit_with_dr(r, preperiod)
    y2 = y1
    for _ in range(p):
        y2 = r * y2 * (1 - y2)
    if abs(y2 - y1) > target:
        raise ArithmeticError("m_%d did not satisfy its equation" % n)
    return r


#: The rows a theorem gives exactly, and why.
#:
#: A decimal means plus or minus one unit in the last place however long it
#: is, so `3.000000000000000000000000000000` says a number known to *be* 3 is
#: known to thirty places -- which understates it, and understates it exactly
#: where the family is most interesting. The digits cannot decide this: what
#: decides it is the argument, so each row names one.
#:
#:   a1 in r   the nonzero fixed point 1 - 1/r has multiplier 2 - r, which is
#:             -1 at r = 3;
#:   a1 in c   -3(3 - 2)/4;
#:   a2 in c   r = 1 + sqrt(6), so -r(r - 2)/4 = -(1 + sqrt 6)(sqrt 6 - 1)/4
#:             = -(6 - 1)/4, and the surd cancels;
#:   s1 in r   the critical point x = 1/2 is fixed when r/4 = 1/2;
#:   s1 in c   -2(2 - 2)/4;
#:   s2 in c   r = 1 + sqrt(5), so the same cancellation gives -(5 - 1)/4.
#:
#: Each is still checked against the numerical solve every other row uses, so
#: what is written is verified rather than asserted.
EXACT = {
    ("a1", "r"): "3",
    ("a1", "c"): "-3/4",
    ("a2", "c"): "-5/4",
    ("s1", "r"): "2",
    ("s1", "c"): "0",
    ("s2", "c"): "-1",
}

#: Only the `c` rows: an `r` row that is exact already says so in
#: `point_comment`, which is where every other `r` row's remark is.
EXACT_COMMENTS = {
    ("a1", "c"): r"Exactly $-3/4$, from $r=3$ in CITE{formula-conversion}.",
    ("a2", "c"): (r"Exactly $-5/4$: $r=1+\sqrt6$, so "
                  r"$-r(r-2)/4=-(6-1)/4$ and the surd cancels."),
    ("s1", "c"): r"Exactly $0$, from $r=2$ in CITE{formula-conversion}.",
    ("s2", "c"): (r"Exactly $-1$: $r=1+\sqrt5$, so "
                  r"$-r(r-2)/4=-(5-1)/4$ and the surd cancels."),
}


def agrees_with_the_solve(exact, computed):
    """Whether an exact row matches what the numerical row would have been.

    Half the working precision: the solve carries 650 guard bits beyond the
    hundred digits written, and asking for all of them would be asking the
    check to be tighter than the thing it checks.
    """
    return abs(RR(QQ(exact)) - RR(computed)) < RR(2) ** (-(WORKING_BITS // 2))


def r_value(point, digits=DIGITS):
    key = (point, int(digits), WORKING_BITS)
    if key in _CACHE:
        return _CACHE[key]
    if point == "r-infinity":
        value = RR(R_INFINITY)
    elif point.startswith("a"):
        value = solve_bifurcation(int(point[1:]), digits)
    elif point.startswith("s"):
        value = solve_superstable(int(point[1:]), digits)
    elif point.startswith("m"):
        value = solve_misiurewicz(int(point[1:]), digits)
    else:
        raise ValueError("unknown point %r" % (point,))
    _CACHE[key] = value
    return value


def point_comment(point):
    comments = {
        "a1": r"$a_1=3$, where the nonzero fixed point has multiplier $-1$.",
        "a2": r"$a_2=1+\sqrt6$, the onset of the stable $4$-cycle CITE{OEISA086180}.",
        "a3": (
            r"$a_3$ is the root near $3.54409$ of "
            r"$r^{12}-12r^{11}+48r^{10}-40r^9-193r^8+392r^7+44r^6+8r^5"
            r"-977r^4-604r^3+2108r^2+4913$ CITE{OEISA086181}."
        ),
        "a4": r"$a_4$ is the onset of the stable $16$-cycle CITE{OEISA091517}.",
        "s1": r"$s_1=2$, where the critical point $1/2$ is the nonzero fixed point.",
        "s2": r"$s_2=1+\sqrt5$, where the critical point $1/2$ lies on the $2$-cycle.",
        "m1": (
            r"$m_1$ is Sprott's first Misiurewicz point of the logistic map "
            r"CITE{SprottMisiurewicz}, the root of $r^3-2r^2-4r-8$."
        ),
        "r-infinity": (
            r"$r_\infty$ is the Feigenbaum point, the accumulation point of "
            r"the period-doubling cascade CITE{OEISA098587}."
        ),
    }
    if point in comments:
        return comments[point]
    if point.startswith("a"):
        n = int(point[1:])
        return (r"$a_%d$ is the bifurcation point where the attracting "
                r"period-$%d$ cycle has multiplier $-1$.") % (n, 2 ** (n - 1))
    if point.startswith("s"):
        n = int(point[1:])
        return (r"$s_%d$ is the superstable parameter of the period-$%d$ "
                r"cycle.") % (n, 2 ** (n - 1))
    if point.startswith("m"):
        n = int(point[1:])
        return (r"$m_%d$ is the band-merging Misiurewicz parameter with "
                r"preperiod $%d$ and period $%d$.") % (n, 2 ** n + 1, 2 ** (n - 1))
    return ""


class LogisticPeriodDoublingCascade(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE") or "T168"
    #The key stays `expression`. It is the wrong word -- twenty-two tables
    #use it for three unrelated things, and this axis is the normalisation --
    #but the table was published while it was being fixed, and a key is an
    #entry's address: renaming one leaves every citation resolving, and
    #resolving to a different number. The column *reads* "normalisation",
    #which is the parameter's `title` and `display`, and those are
    #presentation rather than identity.
    parameters = ("point", "expression")
    type = "R"
    digits = DIGITS
    rigour = "heuristic (agreement-checked)"

    def enumerate(self):
        for point in POINTS:
            for expression in ("r", "c"):
                yield {"point": point, "expression": expression}

    def digits_for(self, params):
        if params["point"] == "r-infinity":
            return R_INFINITY_DIGITS
        return self.digits

    def value(self, params, digits):
        point = str(params["point"])
        expression = str(params["expression"])
        if point not in POINTS:
            raise ValueError("point must be one of the listed keys")
        if expression not in ("r", "c"):
            raise ValueError("expression must be r or c")
        wanted = self.digits_for(params)
        r = r_value(point, wanted)
        value = r if expression == "r" else c_parameter(r)

        exact = EXACT.get((point, expression))
        if exact is None:
            entry = {"number": decimal(value, wanted)}
            if wanted != digits:
                entry["digits"] = wanted
        else:
            if not agrees_with_the_solve(exact, value):
                raise ValueError(
                    "%s in %s is written exactly as %s, and the solve does "
                    "not agree" % (point, expression, exact))
            entry = {"number": exact}

        comment = (EXACT_COMMENTS.get((point, expression))
                   or (point_comment(point) if expression == "r" else ""))
        if comment:
            entry["comment"] = comment
        return entry


if __name__ == "__main__":
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") == "1":
        os.environ["NUMBERDB_API_KEY"] = sys.stdin.read().strip()
    generator = LogisticPeriodDoublingCascade()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(generator.publish(
            message="logistic map period-doubling cascade parameters"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
