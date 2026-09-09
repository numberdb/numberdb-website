"""Periodic windows of the logistic map.

For f_r(x) = r*x*(1 - x), this generator stores, by superstable kneading word,
the window onset, superstable parameter, first period-doubling point, and
topological entropy for the primitive windows through period 8, excluding the
main period-doubling cascade.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.rational_field import QQ
from sage.rings.real_mpfr import RealField


DIGITS = 100

# Measured at 100 digits: recomputing all endpoint and entropy rows at 760 and
# 980 guard bits gives the same 100 written digits. The defining-equation
# residuals are below 1e-180 away from the two harmonic onsets, where the value
# is copied from the parent's period-doubling endpoint because the multiplier
# +1 continuation is singular.
WORKING_GUARD = 760
WORKING_BITS = numberdb.bits(DIGITS, losing=WORKING_GUARD)
RR = RealField(WORKING_BITS)

WINDOW_DATA = (
    ("RLC", 3, "3.83187405528331556841036277549610655579782785260369463047889"),
    ("RLLC", 4, "3.96027012722115260157125779850142054454978143186380426963011"),
    ("RLRRC", 5, "3.73891491297068499308521289037628945123011655080787136700626"),
    ("RLLRC", 5, "3.90570646983129035482040709205270692520123591507403554654039"),
    ("RLLLC", 5, "3.99026704697370151827752638855431798336598982156607813701226"),
    ("RLRRRC", 6, "3.62755752951552320337487410201744167984471413668637428601269"),
    ("RLLRLC", 6, "3.84456879219443297290078487624558310353185746845492078015162"),
    ("RLLRRC", 6, "3.93753644475455110456195058197103873365215915515224038284069"),
    ("RLLLRC", 6, "3.97776642226547291402054545126087675864272268564042588450143"),
    ("RLLLLC", 6, "3.99758311825456726610019472081786309367501729922294434876419"),
    ("RLRRRRC", 7, "3.70176915353795611419331084301300604849413321574933283184849"),
    ("RLRRLRC", 7, "3.77421418890091323212739972204104818206084012028500672645025"),
    ("RLLRLRC", 7, "3.88604587818782201152249198516686183130618919773650386210825"),
    ("RLLRRRC", 7, "3.92219340330970002847241358035937377280274034284494160144631"),
    ("RLLRRLC", 7, "3.95103216476130619789149231869205357950097805625282226150577"),
    ("RLLLRLC", 7, "3.96897685695553797149529480553910894603778370379935112154288"),
    ("RLLLRRC", 7, "3.98474761881553890777227690756145467967695741149867955409540"),
    ("RLLLLRC", 7, "3.99453780911119719041722057353600587626551227740194151958958"),
    ("RLLLLLC", 7, "3.99939706096209841119149570748595344287447837974184760843867"),
    ("RLRRRRRC", 8, "3.66219250368657675340876010432325910893615015663642213835629"),
    ("RLRRLRRC", 8, "3.80077094387466976937368109454104253124347270335887952260225"),
    ("RLLRLRRC", 8, "3.87054098436375722318755269464027944382282435049289399007371"),
    ("RLLRLRLC", 8, "3.89946895097060233416934344787695205856357586340214333515350"),
    ("RLLRRRLC", 8, "3.91204662107512651104763023851459235523482847662900300073974"),
    ("RLLRRRRC", 8, "3.93047299573214484064402135589651638257113463053635152580303"),
    ("RLLRRLRC", 8, "3.94421349573255098808610901732878288595325948829461131171778"),
    ("RLLLRLLC", 8, "3.96093369754758146637114229913583917292042387207979678535427"),
    ("RLLLRLRC", 8, "3.97372425567498033782288399372111449028970594265243660107476"),
    ("RLLLRRRC", 8, "3.98140895441526149539552930197501172904253702383791585384259"),
    ("RLLLRRLC", 8, "3.98774549537007548382140455558237811663416743658051704703934"),
    ("RLLLLRLC", 8, "3.99251952328433189778669097627568608641243470578643252758917"),
    ("RLLLLRRC", 8, "3.99621959590116485491127851415714485231231646692996928535121"),
    ("RLLLLLRC", 8, "3.99864163620644360240349251525825508554511035102421802984503"),
    ("RLLLLLLC", 8, "3.99984936201385107048028702522067059113459005561707696664198"),
)

WINDOWS = tuple(row[0] for row in WINDOW_DATA)
PERIOD = {word: period for word, period, _seed in WINDOW_DATA}
SUPERSTABLE_SEEDS = {word: seed for word, _period, seed in WINDOW_DATA}

#: What the table holds for each window, in the order it is shown.
#:
#: The three parameter values are held in both normalisations, because a
#: reader who works in $z^2+c$ should not have to convert: c was in the entry
#: comments, which is not a place a value can be searched for or cited.
#:
#: One parameter with seven values rather than a `normalisation` parameter
#: beside a `quantity` one, as T168 has: T168's grid is a rectangle and this
#: is not. The topological entropy has no normalisation -- it is a property of
#: the map, the same number whichever coordinate names it -- and a
#: normalisation parameter would have to claim either that it has both or
#: that it has one.
QUANTITIES = (
    "onset", "onset-c",
    "superstable", "superstable-c",
    "doubling", "doubling-c",
    "entropy",
)

#: The `r` row each `c` row converts.
BASE_OF = {q: q[:-2] for q in QUANTITIES if q.endswith("-c")}

#: The one row a theorem gives exactly. The period-3 window opens at
#: r = 1 + 2 sqrt 2, so c = -r(r-2)/4 = -(1 + 2 sqrt 2)(2 sqrt 2 - 1)/4
#: = -(8 - 1)/4 and the surd cancels. A decimal would say a number known to be
#: -7/4 is known to a hundred places. Checked against the solve below.
EXACT = {
    ("RLC", "onset-c"): "-7/4",
}

HARMONIC_ONSETS = {
    "RLLRLC": "RLC",
    "RLLLRLLC": "RLLC",
}

ENTROPY_POLYNOMIALS = {
    "RLC": "x^2 - x - 1",
    "RLLC": "x^3 - x^2 - x - 1",
    "RLRRC": "x^4 - x^3 - x^2 + x - 1",
    "RLLRC": "x^4 - x^3 - x^2 - x + 1",
    "RLLLC": "x^4 - x^3 - x^2 - x - 1",
    "RLRRRC": "x^4 - x^2 - 1",
    "RLLRLC": "x^2 - x - 1",
    "RLLRRC": "x^5 - x^4 - x^3 - x^2 + x - 1",
    "RLLLRC": "x^4 - 2*x^3 + x^2 - 2*x + 1",
    "RLLLLC": "x^5 - x^4 - x^3 - x^2 - x - 1",
    "RLRRRRC": "x^3 - x^2 - 1",
    "RLRRLRC": "x^6 - x^5 - x^4 + x^3 - x^2 - x + 1",
    "RLLRLRC": "x^6 - x^5 - x^4 - x^3 + x^2 + x - 1",
    "RLLRRRC": "x^3 - 2*x^2 + x - 1",
    "RLLRRLC": "x^6 - x^5 - x^4 - x^3 + x^2 - x - 1",
    "RLLLRLC": "x^6 - x^5 - x^4 - x^3 - x^2 + x + 1",
    "RLLLRRC": "x^6 - x^5 - x^4 - x^3 - x^2 + x - 1",
    "RLLLLRC": "x^6 - x^5 - x^4 - x^3 - x^2 - x + 1",
    "RLLLLLC": "x^6 - x^5 - x^4 - x^3 - x^2 - x - 1",
    "RLRRRRRC": "x^6 - x^4 - x^2 - 1",
    "RLRRLRRC": "x^7 - x^6 - x^5 + x^4 - x^3 - x^2 + x - 1",
    "RLLRLRRC": "x^5 - x^4 - 2*x^2 + x - 1",
    "RLLRLRLC": "x^7 - x^6 - x^5 - x^4 + x^3 + x^2 - x - 1",
    "RLLRRRLC": "x^6 - x^4 - 2*x^3 - x^2 - 2*x - 1",
    "RLLRRRRC": "x^7 - x^6 - x^5 - x^4 + x^3 - x^2 + x - 1",
    "RLLRRLRC": "x^7 - x^6 - x^5 - x^4 + x^3 - x^2 - x + 1",
    "RLLLRLLC": "x^3 - x^2 - x - 1",
    "RLLLRLRC": "x^7 - x^6 - x^5 - x^4 - x^3 + x^2 + x - 1",
    "RLLLRRRC": "x^7 - x^6 - x^5 - x^4 - x^3 + x^2 - x + 1",
    "RLLLRRLC": "x^6 - 2*x^5 + x^4 - 2*x^3 + x^2 - 1",
    "RLLLLRLC": "x^7 - x^6 - x^5 - x^4 - x^3 - x^2 + x + 1",
    "RLLLLRRC": "x^5 - x^4 - 2*x^3 + x - 1",
    "RLLLLLRC": "x^6 - 2*x^5 + x^4 - 2*x^3 + x^2 - 2*x + 1",
    "RLLLLLLC": "x^7 - x^6 - x^5 - x^4 - x^3 - x^2 - x - 1",
}

SPECIAL_ENDPOINT_COMMENTS = {
    ("RLC", "onset"): r"$r_{\mathrm{on}}=1+2\sqrt2$ CITE{OEISA086178}",
    ("RLC", "superstable"): (
        r"$r_W$ is the root near $3.83187$ of "
        r"$r^6-6r^5+4r^4+24r^3-16r^2-32r-64$"
    ),
    ("RLC", "doubling"): (
        r"$r_{\mathrm{pd}}$ is the root near $3.84150$ of "
        r"$r^6-6r^5+4r^4+24r^3-14r^2-36r-81$ CITE{OEISA086179}"
    ),
    ("RLRRC", "onset"): (
        r"$r_{\mathrm{on}}$ is the first period-$5$ onset listed in "
        r"OEIS A118452 CITE{OEISA118452}"
    ),
    ("RLRRRC", "onset"): (
        r"$r_{\mathrm{on}}$ is the first period-$6$ onset listed in "
        r"OEIS A118453 CITE{OEISA118453}"
    ),
    ("RLRRRRC", "onset"): (
        r"$r_{\mathrm{on}}$ is the first period-$7$ onset listed in "
        r"OEIS A118746 CITE{OEISA118746}"
    ),
}

_CACHE = {}


def set_working_bits(bits):
    """Use another RealField for agreement checks."""
    global WORKING_GUARD, WORKING_BITS, RR, _CACHE
    WORKING_GUARD = max(0, int(bits) - numberdb.bits(DIGITS, losing=0))
    WORKING_BITS = int(bits)
    RR = RealField(WORKING_BITS)
    _CACHE = {}


def decimal(value, digits=DIGITS):
    return RR(value).str(digits=int(digits))


def f_value(r, x):
    return r * x * (1 - x)


def c_parameter(r):
    r = RR(r)
    return -r * (r - 2) / 4


def critical_orbit_with_dr(r, steps):
    y = RR(1) / RR(2)
    dr = RR(0)
    for _ in range(steps):
        dr = y * (1 - y) + r * (1 - 2 * y) * dr
        y = f_value(r, y)
    return y, dr


def orbit_derivatives(x, r, steps):
    """f_r^steps(x) and derivatives for the multiplier equation."""
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


def superstable_parameter(word, digits=DIGITS):
    key = ("superstable", word, WORKING_BITS)
    if key in _CACHE:
        return _CACHE[key]
    p = PERIOD[word]
    r = RR(SUPERSTABLE_SEEDS[word])
    target = RR(10) ** (-(int(digits) + 90))
    for _ in range(80):
        y, dr = critical_orbit_with_dr(r, p)
        step = (y - RR(1) / RR(2)) / dr
        r -= step
        if abs(step) < target:
            break
    y, _ = critical_orbit_with_dr(r, p)
    if abs(y - RR(1) / RR(2)) > target:
        raise ArithmeticError("%s: superstable equation not solved" % word)
    _CACHE[key] = r
    return r


def solve_multiplier(word, target_mu, digits=DIGITS):
    key = ("multiplier", word, int(target_mu), WORKING_BITS)
    if key in _CACHE:
        return _CACHE[key]
    p = PERIOD[word]
    r = superstable_parameter(word, digits)
    x = RR(1) / RR(2)
    target = RR(10) ** (-(int(digits) + 90))
    for j in range(1, 81):
        mu = RR(target_mu) * RR(j) / RR(80)
        for _ in range(40):
            y, dx, dr, dxx, dxr = orbit_derivatives(x, r, p)
            f1 = y - x
            f2 = dx - mu
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
    if abs(y - x) > target or abs(dx - RR(target_mu)) > target:
        raise ArithmeticError("%s: multiplier %s equation not solved" % (
            word, target_mu))
    _CACHE[key] = r
    return r


def onset_parameter(word, digits=DIGITS):
    parent = HARMONIC_ONSETS.get(word)
    if parent:
        return doubling_parameter(parent, digits)
    return solve_multiplier(word, RR(1), digits)


def doubling_parameter(word, digits=DIGITS):
    return solve_multiplier(word, RR(-1), digits)


def partition_matrix(word, digits=DIGITS):
    p = PERIOD[word]
    r = superstable_parameter(word, digits)
    c = RR(1) / RR(2)
    orbit = [c]
    y = c
    for _ in range(1, p):
        y = f_value(r, y)
        orbit.append(y)
    points = sorted([RR(0), RR(1)] + orbit)
    unique = []
    tolerance = RR(10) ** (-(int(digits) + 20))
    for point in points:
        if not unique or abs(point - unique[-1]) > tolerance:
            unique.append(point)
    n = len(unique) - 1
    matrix = [[0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        a, b = unique[i], unique[i + 1]
        image_a = f_value(r, a)
        image_b = f_value(r, b)
        lo = min(image_a, image_b)
        hi = max(image_a, image_b)
        for j in range(n):
            midpoint = (unique[j] + unique[j + 1]) / 2
            if lo < midpoint < hi:
                matrix[i][j] = 1
    return matrix


def matmul(left, right):
    n = len(left)
    return [[sum(left[i][k] * right[k][j] for k in range(n))
             for j in range(n)] for i in range(n)]


def charpoly_coeffs(matrix):
    """Characteristic polynomial coefficients, high degree first."""
    n = len(matrix)
    b = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
    coeffs = [1]
    for k in range(1, n + 1):
        ab = matmul(matrix, b)
        trace = sum(ab[i][i] for i in range(n))
        if trace % k:
            raise ArithmeticError("nonintegral characteristic coefficient")
        c = -trace // k
        coeffs.append(c)
        b = [[ab[i][j] + (c if i == j else 0) for j in range(n)]
             for i in range(n)]
    return coeffs


def poly_eval(coeffs, value):
    out = RR(0)
    for coefficient in coeffs:
        out = out * value + RR(coefficient)
    return out


def perron_root(coeffs, digits=DIGITS):
    lo = RR(1) + RR(10) ** (-(int(digits) + 10))
    hi = RR(2)
    flo = poly_eval(coeffs, lo)
    fhi = poly_eval(coeffs, hi)
    if flo * fhi > 0:
        raise ArithmeticError("Perron root is not bracketed")
    for _ in range(6 * int(digits)):
        mid = (lo + hi) / 2
        fmid = poly_eval(coeffs, mid)
        if flo * fmid <= 0:
            hi = mid
            fhi = fmid
        else:
            lo = mid
            flo = fmid
    return (lo + hi) / 2


def entropy_parameter(word, digits=DIGITS):
    key = ("entropy", word, WORKING_BITS)
    if key in _CACHE:
        return _CACHE[key]
    matrix = partition_matrix(word, digits)
    root = perron_root(charpoly_coeffs(matrix), digits)
    value = root.log()
    _CACHE[key] = value
    return value


def r_value(word, expression, digits=DIGITS):
    if expression == "onset":
        return onset_parameter(word, digits)
    if expression == "superstable":
        return superstable_parameter(word, digits)
    if expression == "doubling":
        return doubling_parameter(word, digits)
    if expression == "entropy":
        return entropy_parameter(word, digits)
    raise ValueError("unknown expression %r" % (expression,))


def endpoint_comment(word, expression, value):
    parts = ["period $%d$" % PERIOD[word]]
    special = SPECIAL_ENDPOINT_COMMENTS.get((word, expression))
    if special:
        parts.append(special)
    parent = HARMONIC_ONSETS.get(word)
    if expression == "onset" and parent:
        parts.append(
            r"$r_{\mathrm{on}}$ is the first period-doubling point of "
            r"$\mathtt{%s}$" % parent
        )
    return "; ".join(parts) + "."


def normalisation_comment(word, base):
    """The remark on a `c` row: which `r` row it converts."""
    symbol = {"onset": r"r_{\mathrm{on}}",
              "superstable": "r_W",
              "doubling": r"r_{\mathrm{pd}}"}[base]
    return (r"period $%d$; the same window's $%s$ in the $z\mapsto z^2+c$ "
            r"normalisation CITE{formula-conversion}."
            % (PERIOD[word], symbol))


def entropy_comment(word):
    polynomial = ENTROPY_POLYNOMIALS[word]
    pieces = [
        "period $%d$" % PERIOD[word],
        r"if $\lambda$ is the Perron root then $\lambda$ satisfies $%s$" % polynomial,
        r"$h_{\mathrm{top}}=\log\lambda$",
    ]
    if word == "RLC":
        pieces.append(
            r"$\lambda$ is HREF{Golden_ratio#phi}[the golden ratio $\varphi$]")
    if word == "RLRRRC":
        pieces.append(r"$h_{\mathrm{top}}$ is half the entropy of $\mathtt{RLC}$")
    if word in HARMONIC_ONSETS:
        pieces.append(r"the entropy equals that of $\mathtt{%s}$" %
                      HARMONIC_ONSETS[word])
    return "; ".join(pieces) + "."


class LogisticPeriodicWindows(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE") or "T169"
    parameters = ("W", "quantity")
    type = "R"
    digits = DIGITS
    rigour = "heuristic (agreement-checked)"

    def enumerate(self):
        for word in WINDOWS:
            for quantity in QUANTITIES:
                yield {"W": word, "quantity": quantity}

    def value(self, params, digits):
        word = str(params["W"])
        quantity = str(params["quantity"])
        if word not in WINDOWS:
            raise ValueError("W must be one of the listed kneading words")
        if quantity not in QUANTITIES:
            raise ValueError("quantity must be one of %s" %
                             ", ".join(QUANTITIES))

        base = BASE_OF.get(quantity, quantity)
        value = r_value(word, base, digits)
        if quantity in BASE_OF:
            value = c_parameter(value)
            comment = normalisation_comment(word, base)
        elif quantity == "entropy":
            comment = entropy_comment(word)
        else:
            comment = endpoint_comment(word, quantity, value)

        exact = EXACT.get((word, quantity))
        if exact is None:
            return {"number": decimal(value, digits), "comment": comment}
        if abs(RR(QQ(exact)) - RR(value)) >= RR(2) ** (-(WORKING_BITS // 2)):
            raise ValueError(
                "%s in %s is written exactly as %s, and the solve does not "
                "agree" % (word, quantity, exact))
        return {"number": exact, "comment": comment}


if __name__ == "__main__":
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") == "1":
        os.environ["NUMBERDB_API_KEY"] = sys.stdin.read().strip()
    generator = LogisticPeriodicWindows()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(generator.publish(
            message="logistic-map periodic windows through period 8"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
