"""Volumes of closed hyperbolic 3-manifolds in the Hodgson-Weeks census -- numberdb.org/T219

    Vol(M), the volume of the complete hyperbolic metric of curvature -1,

for the orientable closed hyperbolic 3-manifolds M of the Hodgson-Weeks
census, which SnapPy distributes as OrientableClosedCensus. The two rows are
the Weeks manifold and the Meyerhoff manifold.

The names are the census's own, not SnapPy's: m003(-3,1) is the Dehn filling
with coefficients (-3,1) on the cusped census manifold m003, and m003 is a
SnapPea census name. SnapPy is the program that distributes and looks them
up, and its own documentation calls them SnapPea census manifolds.

Run it with SageMath:

    $ sage -pip install numberdb
    $ sage -python generate.py
    $ sage -python generate.py --publish

The triangulation data were extracted from SnapPy 3.3.2. The verification does
not import SnapPy: it proves, in arb ball arithmetic, that each extracted
filled ideal triangulation has a nearby solution of the rectangular gluing
equations with all shape parameters in the upper half plane.
"""

import os
import sys

import numberdb.sage as numberdb
from closed_census_data import CLOSED_CENSUS_VOLUME_LT_ONE
from sage.rings.complex_arb import ComplexBallField
from sage.rings.real_arb import RealBallField


WORKING_GUARD = 64
VOLUME_BOUND = "1"

COMMON_NAMES = {
    "m003(-3,1)": "Weeks manifold, also called the Fomenko-Matveev-Weeks manifold",
    "m003(-2,3)": "Meyerhoff manifold",
}

ALIASES = {
    "m003(-2,3)": "SnapPy also identifies $m004(5,1)$ with this census entry",
}


class NotCertified(ArithmeticError):
    pass


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def records():
    return list(CLOSED_CENSUS_VOLUME_LT_ONE)


def record_for(name):
    for record in records():
        if record["name"] == name:
            return record
    raise ValueError("%s is not in the volume < %s part of the closed census"
                     % (name, VOLUME_BOUND))


def log_residuals(equations, z, CB):
    one = CB(1)
    out = []
    for A, B, c in equations:
        prod = CB(c)
        for a, b, zi in zip(A, B, z):
            if a:
                prod *= zi ** int(a)
            if b:
                prod *= (one - zi) ** int(b)
        out.append(prod.log())
    return out


def jacobian(equations, z, CB):
    one = CB(1)
    inv = [one / zi for zi in z]
    inv1 = [one / (one - zi) for zi in z]
    rows = []
    for A, B, c in equations:
        rows.append([CB(int(a)) * inv[i] - CB(int(b)) * inv1[i]
                     for i, (a, b) in enumerate(zip(A, B))])
    return rows


def midpoint(ball, CB):
    return CB(ball.mid())


def inverse_of_midpoints(J, CB):
    n = len(J)
    M = [[midpoint(J[i][j], CB) for j in range(n)]
         + [CB(1 if i == j else 0) for j in range(n)]
         for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(M[r][col].mid()))
        if abs(M[pivot][col].mid()) == 0:
            raise NotCertified("the Jacobian of the chosen equations is singular")
        M[col], M[pivot] = M[pivot], M[col]
        p = M[col][col]
        M[col] = [midpoint(x / p, CB) for x in M[col]]
        for r in range(n):
            if r != col and M[r][col] != 0:
                factor = M[r][col]
                M[r] = [midpoint(x - factor * y, CB)
                        for x, y in zip(M[r], M[col])]
    return [row[n:] for row in M]


def matmul_vec(C, v):
    zero = C[0][0].parent()(0)
    return [sum((C[i][j] * v[j] for j in range(len(v))), zero)
            for i in range(len(C))]


def contained_in_interior(k, x, RB):
    for kk, xx in ((k.real(), x.real()), (k.imag(), x.imag())):
        distance = (RB(kk.mid()) - RB(xx.mid())).abs() + RB(kk.rad())
        if not bool(distance < RB(xx.rad())):
            return False
    return True


def krawczyk(system, z0, first, C, X, CB):
    n = len(z0)
    JX = jacobian(system, X, CB)
    CJ = [[sum((C[i][l] * JX[l][j] for l in range(n)), CB(0))
           for j in range(n)] for i in range(n)]
    delta = [X[j] - z0[j] for j in range(n)]
    return [first[i]
            + sum(((CB(1 if i == j else 0) - CJ[i][j]) * delta[j]
                   for j in range(n)), CB(0))
            for i in range(n)]


def bloch_wigner(z, CB):
    one = CB(1)
    return (one - z).arg() * z.abs().log() + z.polylog(2).imag()


def certify(record, bits, newton_steps=6, refinements=4):
    CB = ComplexBallField(bits)
    RB = RealBallField(bits)
    rect = record["rect"]
    log = record["log"]
    shapes = record["shapes"]
    n = len(shapes)
    if len(rect) != n + 1 or len(log) != n + 1:
        raise NotCertified("expected %d edge rows and one filling row, got %d"
                           % (n, len(rect)))

    edges = rect[:n]
    filling = rect[-1]
    for i in range(n):
        if sum(A[i] for A, B, c in edges) != 0:
            raise NotCertified("the edge equations do not multiply to 1 in z_%d" % i)
        if sum(B[i] for A, B, c in edges) != 0:
            raise NotCertified("the edge equations do not multiply to 1 in 1-z_%d" % i)
    sign = 1
    for A, B, c in edges:
        sign *= int(c)
    if sign != 1:
        raise NotCertified("the edge equations multiply to -1")

    system = edges[:-1] + [filling]
    try:
        z0 = [CB(RB(str(re).replace(" ", "")), RB(str(im).replace(" ", "")))
              for re, im in shapes]
    except (ValueError, TypeError) as trouble:
        raise NotCertified("a starting shape is not a number: %s" % trouble)

    for _ in range(newton_steps):
        f = log_residuals(system, z0, CB)
        C = inverse_of_midpoints(jacobian(system, z0, CB), CB)
        z0 = [midpoint(z0[i] - v, CB)
              for i, v in enumerate(matmul_vec(C, f))]

    f0 = log_residuals(system, z0, CB)
    C = inverse_of_midpoints(jacobian(system, z0, CB), CB)
    first = [z0[i] - v for i, v in enumerate(matmul_vec(C, f0))]

    X = None
    exponent = bits - 8
    while exponent > 8:
        radius = RB(2) ** (-exponent)
        box = [z.add_error(radius) for z in z0]
        K = krawczyk(system, z0, first, C, box, CB)
        if all(contained_in_interior(k, x, RB) for k, x in zip(K, box)):
            X = K
            break
        exponent -= 12
    if X is None:
        raise NotCertified("no box around the approximate solution passed the Krawczyk test")

    for _ in range(refinements):
        K = krawczyk(system, z0, first, C, X, CB)
        if all(contained_in_interior(k, x, RB) for k, x in zip(K, X)):
            X = K
        else:
            break

    for i, x in enumerate(X):
        if not bool(x.imag() > 0):
            raise NotCertified("shape %d is not certified to have positive imaginary part: %s"
                               % (i, x))

    one = CB(1)
    logs = []
    for x in X:
        logs.extend([x.log(), (one / (one - x)).log(), ((x - one) / x).log()])
    two_pi_i = CB(0, 2) * CB.pi()
    for r, row in enumerate(log):
        total = sum((CB(int(e)) * l for e, l in zip(row, logs) if e), CB(0))
        if not (total - two_pi_i).contains_zero():
            raise NotCertified("logarithmic equation %d misses 2*pi*i: %s" % (r, total))
        if not (bool(total.real().rad() < 0.1)
                and bool(total.imag().rad() < 0.1)):
            raise NotCertified("logarithmic equation %d is not pinned: %s" % (r, total))

    volume = sum((bloch_wigner(x, CB) for x in X), RB(0))
    if not volume.is_finite():
        raise NotCertified("the volume ball is not finite")
    return volume, X, exponent


def comment(record):
    name = record["name"]
    parts = [COMMON_NAMES[name]]
    parts.append("first homology $%s$" % record["homology"].replace("Z", "\\mathbb{Z}"))
    filling = record["filling"][0]
    parts.append("Dehn filling coefficients $(%d,%d)$ on $%s$"
                 % (filling[0], filling[1], name.split("(", 1)[0]))
    if name in ALIASES:
        parts.append(ALIASES[name])
    if name == "m003(-3,1)":
        parts.append("the smallest closed orientable hyperbolic 3-manifold")
    if name == "m003(-2,3)":
        parts.append("the second smallest closed orientable hyperbolic 3-manifold")
    return "; ".join(parts) + "."


class ClosedHodgsonWeeksVolumes(numberdb.Generator):
    table = "T219"
    parameters = ("name",)
    type = "R"
    digits = 100
    rigour = "proven"
    files = ("generate.py", "closed_census_data.py")

    def enumerate(self):
        for record in records():
            yield {"name": record["name"]}

    def value(self, params, digits):
        record = record_for(str(params["name"]))
        bits = numberdb.bits(digits, losing=WORKING_GUARD)
        volume, shapes, exponent = certify(record, bits)
        return {"number": volume, "comment": comment(record)}


def fill_draft_once(generator, message):
    """Fill a fresh draft without the empty upsert probe.

    The ordinary Generator.publish() path first sends an empty upsert as a
    writeability check. A draft created with no Numbers section currently
    rejects that harmless probe while rebuilding its search rows. This table
    has two entries, so sending the complete non-empty block once keeps the
    intended revision history and still uses the package's entry formatting.
    """
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
    generator = ClosedHodgsonWeeksVolumes()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="closed Hodgson-Weeks census volumes below 1, certified in ball arithmetic"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
