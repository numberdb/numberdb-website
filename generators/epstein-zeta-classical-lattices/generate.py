"""Values of the Epstein zeta function of the classical lattices -- numberdb.org/T402.

This fills the first block of the table: every classical lattice from the
T147 indexing with dimension at most 8, every integer or half-integer
satisfying n/2 < s <= n/2 + 3, and the extra Lennard-Jones rows s = 3 and
s = 6 wherever they converge in those dimensions.

Run it in this repository with:

    agents/sage.sh generate.py lattice_data.py
    NUMBERDB_SELF_CHECK=1 agents/sage.sh generate.py lattice_data.py
    cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
        agents/sage.sh generate.py lattice_data.py
"""

import os
import sys

import numberdb.sage as numberdb
from sage.libs.pari.all import pari
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField

import lattice_data


TABLE = os.environ.get("NUMBERDB_TABLE", "T402")
MAX_DIMENSION = 8
WORKING_GUARD = 192
TAIL_GUARD = 20
TAIL_EXTRA_GUARD = 20
MAX_ARGUMENT_CUTOFF = 420

LJ_REFERENCES = {
    ("Z", 3, QQ(3)): "8.4019232",
    ("Z", 3, QQ(6)): "6.2021490",
    ("A", 3, QQ(3)): "14.4539210435",
    ("A", 3, QQ(6)): "12.1318802",
    ("A*", 3, QQ(3)): "12.2533",
    ("A*", 3, QQ(6)): "9.1141833",
}

_COUNT_CACHE = {}
_CALCULATOR_CACHE = {}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _field(digits):
    return RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def _s_values(n):
    values = {QQ(k) / QQ(2) for k in range(n + 1, n + 7)}
    if n <= 5:
        values.add(QQ(3))
    if n <= 11:
        values.add(QQ(6))
    return tuple(sorted(values))


def _lattice_keys(max_dimension=MAX_DIMENSION):
    for family, dimensions in lattice_data.FAMILIES:
        for n in dimensions:
            if n <= max_dimension:
                yield family, int(n)


def _integral_scale(matrix):
    den = ZZ(1)
    for entry in matrix.list():
        den = den.lcm(QQ(entry).denominator())
    return (den * matrix).change_ring(ZZ), den


def _matrix_key(matrix):
    return tuple(
        tuple(ZZ(matrix[i, j]) for j in range(matrix.ncols()))
        for i in range(matrix.nrows())
    )


def _qfrep_counts(matrix, bound):
    bound = int(bound)
    key = (_matrix_key(matrix), bound)
    cached = _COUNT_CACHE.get(key)
    if cached is not None:
        return cached
    raw = pari(matrix).qfrep(bound, 0)
    counts = tuple(2 * ZZ(raw[i]) for i in range(len(raw)))
    _COUNT_CACHE[key] = counts
    return counts


def _ceil_ball(value):
    return ZZ(value.ceil())


def _ceil_sqrt_integer(value):
    value = ZZ(value)
    root = ZZ(1)
    while root * root < value:
        root += 1
    return root


def _split_denominator(dual_scale):
    return _ceil_sqrt_integer(dual_scale)


def _lower_quadratic_bound(matrix):
    inverse = matrix.inverse()
    rho = max(
        sum(abs(QQ(inverse[i, j])) for j in range(matrix.ncols()))
        for i in range(matrix.nrows())
    )
    return QQ(1) / QQ(rho)


def _gamma_upper(R, a, x, label):
    value = R(a).gamma_inc(R(x))
    if not value.is_finite():
        raise ArithmeticError("non-finite incomplete gamma value for %s" % label)
    return value


def _norm_exponential_tail(R, matrix, alpha, cutoff):
    """Bound sum_{Q[x] > cutoff} exp(-alpha Q[x]) / Q[x]."""
    n = matrix.nrows()
    lam = _lower_quadratic_bound(matrix)
    lamR = R(lam)
    alphaR = R(alpha)
    cutoff = QQ(cutoff)
    cutoffR = R(cutoff)

    K = ZZ(0)
    while lam * QQ(K * K) <= cutoff:
        K += 1
    inside_radius = K - 1

    inside_count = (2 * inside_radius + 1) ** n - 1
    inside = R(inside_count) * (-alphaR * cutoffR).exp() / cutoffR

    start = max(K, ZZ(1))
    beta = alphaR * lamR
    p = max(n - 3, 0)

    exact_outer = R(0)
    for k in range(int(start), int(start) + 20):
        shell = (2 * k + 1) ** n - (2 * k - 1) ** n
        qlower = lamR * R(k * k)
        exact_outer += R(shell) * (-beta * R(k * k)).exp() / qlower

    integral_start = ZZ(int(start) + 20)
    coefficient = R(2 * n * (3 ** (n - 1))) / lamR
    lower = R(integral_start)
    shape = QQ(p + 1) / QQ(2)
    integral = (
        R(1)
        / R(2)
        * beta ** (-R(shape))
        * _gamma_upper(R, shape, beta * lower * lower, "tail integral")
    )
    first = lower ** p * (-beta * lower * lower).exp()
    return inside + exact_outer + coefficient * (first + integral)


def _primal_tail(R, matrix, s, split, bound):
    cutoff = QQ(bound)
    x = R.pi() * R(split) * R(cutoff)
    if not x > R(s - 1):
        return R(1)
    geom = R(1) / (R(1) - R(s - 1) / x)
    coefficient = R(split) ** (R(s) - 1) * geom / R.pi()
    alpha = R.pi() * R(split)
    return coefficient * _norm_exponential_tail(R, matrix, alpha, cutoff)


def _dual_tail(R, matrix, scale, s, split, bound):
    actual = QQ(bound) / QQ(scale)
    a = QQ(matrix.nrows()) / QQ(2) - QQ(s)
    coefficient = R(split) ** (1 - R(a)) / R.pi()
    alpha = R.pi() / R(split)
    return coefficient * _norm_exponential_tail(R, matrix / QQ(scale), alpha, actual)


def _entry_cutoff(R, G, dual_matrix, dual_scale, s, split, det, digits):
    factor = R.pi() ** R(s) / R(s).gamma()
    det_factor = R(1) / R(det).sqrt()
    target = R(10) ** (-(digits + TAIL_GUARD))
    argument = 80
    while argument <= MAX_ARGUMENT_CUTOFF:
        primal_bound = _ceil_ball(R(argument) / (R.pi() * R(split)))
        dual_bound = _ceil_ball(R(argument) * R(split) * R(dual_scale) / R.pi())
        tail = (
            _primal_tail(R, G, s, split, primal_bound)
            + det_factor * _dual_tail(R, dual_matrix, dual_scale, s, split, dual_bound)
        )
        if factor * tail < target:
            return primal_bound, dual_bound, factor * tail, argument
        argument += 20
    raise ArithmeticError("no tail cutoff found for s=%s" % (s,))


def _minimal_norm(matrix):
    found = pari(matrix).qfminim(None, None, 0)
    return QQ(ZZ(found[1]))


def _overlap_or_raise(label, left, right):
    parent = left.parent()
    right = parent(right)
    if not left.is_finite() or not right.is_finite():
        raise ArithmeticError("%s produced a non-finite comparison" % label)
    if not left.overlaps(right):
        raise ArithmeticError("%s: %s does not overlap %s" % (label, left, right))


class _EpsteinCalculator:
    def __init__(self, family, n, digits):
        self.family = family
        self.n = int(n)
        self.digits = digits
        self.R = _field(digits)
        self.G, _ = lattice_data.gram(family, n)
        self.det = QQ(self.G.det())
        self.dual_matrix, self.dual_scale = _integral_scale(self.G.inverse())
        self.split = QQ(1) / QQ(_split_denominator(self.dual_scale))
        self.requirements = {}
        self.max_primal = ZZ(0)
        self.max_dual = ZZ(0)

        for s in _s_values(self.n):
            primal, dual, error, argument = _entry_cutoff(
                self.R,
                self.G,
                self.dual_matrix,
                self.dual_scale,
                s,
                self.split,
                self.det,
                digits,
            )
            self.requirements[s] = (primal, dual, error, argument)
            self.max_primal = max(self.max_primal, primal)
            self.max_dual = max(self.max_dual, dual)

        self.primal_counts = _qfrep_counts(self.G, self.max_primal)
        self.dual_counts = _qfrep_counts(self.dual_matrix, self.max_dual)

    def _sum_primal(self, s, bound):
        total = self.R(0)
        for index, count in enumerate(self.primal_counts[: int(bound)], start=1):
            if not count:
                continue
            q = QQ(index)
            x = self.R.pi() * self.R(q) * self.R(self.split)
            total += (
                self.R(count)
                * (self.R.pi() * self.R(q)) ** (-self.R(s))
                * _gamma_upper(self.R, s, x, "primal %s_%s s=%s q=%s" %
                               (self.family, self.n, s, q))
            )
        return total

    def _sum_dual(self, s, bound):
        total = self.R(0)
        a = QQ(self.n) / QQ(2) - QQ(s)
        for index, count in enumerate(self.dual_counts[: int(bound)], start=1):
            if not count:
                continue
            q = QQ(index) / QQ(self.dual_scale)
            x = self.R.pi() * self.R(q) / self.R(self.split)
            total += (
                self.R(count)
                * (self.R.pi() * self.R(q)) ** (-self.R(a))
                * _gamma_upper(self.R, a, x, "dual %s_%s s=%s q=%s" %
                               (self.family, self.n, s, q))
            )
        return total

    def value(self, s):
        s = QQ(s)
        primal_bound, dual_bound, error, _argument = self.requirements[s]
        half_dimension = QQ(self.n) / QQ(2)
        det_factor = self.R(1) / self.R(self.det).sqrt()
        integral = (
            self._sum_primal(s, primal_bound)
            + det_factor * self._sum_dual(s, dual_bound)
            + det_factor
            * self.R(self.split) ** (self.R(s) - self.R(half_dimension))
            / (self.R(s) - self.R(half_dimension))
            - self.R(self.split) ** self.R(s) / self.R(s)
        )
        value = self.R.pi() ** self.R(s) * integral / self.R(s).gamma()
        return value.add_error(error.upper())


def epstein_zeta(family, n, s, digits=100):
    key = (family, int(n), int(digits))
    calculator = _CALCULATOR_CACHE.get(key)
    if calculator is None:
        calculator = _EpsteinCalculator(family, n, digits)
        _CALCULATOR_CACHE[key] = calculator
    return calculator.value(QQ(s))


def _dirichlet_beta(R, s):
    ss = R(s)
    return (ss.zeta(R(QQ(1) / QQ(4))) - ss.zeta(R(QQ(3) / QQ(4)))) / (
        R(4) ** ss
    )


def _dirichlet_l_minus_three(R, s):
    ss = R(s)
    return (ss.zeta(R(QQ(1) / QQ(3))) - ss.zeta(R(QQ(2) / QQ(3)))) / (
        R(3) ** ss
    )


def _zeta_square_lattice(s, digits):
    R = _field(digits)
    return R(4) * R(s).zeta() * _dirichlet_beta(R, s)


def _zeta_hexagonal_lattice(s, digits):
    R = _field(digits)
    return (
        R(6)
        * R(2) ** (-R(s))
        * R(s).zeta()
        * _dirichlet_l_minus_three(R, s)
    )


def _zeta_e8(s, digits):
    R = _field(digits)
    return R(240) * R(2) ** (-R(s)) * R(s).zeta() * R(s - 3).zeta()


def _lj_scaled_value(family, n, s, digits):
    G, _scale = lattice_data.gram(family, n)
    mu = _minimal_norm(G)
    return _field(digits)(mu) ** _field(digits)(s) * epstein_zeta(
        family, n, s, digits
    )


def run_integrity_checks(digits=100):
    for s in _s_values(2):
        _overlap_or_raise(
            "Z2 closed form s=%s" % s,
            epstein_zeta("Z", 2, s, digits),
            _zeta_square_lattice(s, digits),
        )
        _overlap_or_raise(
            "A2 closed form s=%s" % s,
            epstein_zeta("A", 2, s, digits),
            _zeta_hexagonal_lattice(s, digits),
        )

    for s in _s_values(8):
        _overlap_or_raise(
            "E8 closed form s=%s" % s,
            epstein_zeta("E", 8, s, digits),
            _zeta_e8(s, digits),
        )

    for key, decimal in LJ_REFERENCES.items():
        family, n, s = key
        computed = _lj_scaled_value(family, n, s, digits)
        expected = _field(digits)(decimal)
        tolerance = _field(digits)(10) ** (-(len(decimal.split(".")[1]) - 1))
        _overlap_or_raise(
            "Lennard-Jones %s_%s s=%s" % (family, n, s),
            computed,
            expected.add_error(tolerance),
        )

    print("self-check passed: closed forms and Lennard-Jones constants")


class EpsteinZetaClassicalLattices(numberdb.Generator):
    """Generator for T402, the Epstein zeta values of classical lattices."""

    table = TABLE
    parameters = ("family", "n", "s")
    type = "R"
    digits = 100
    rigour = "proven"
    files = ("generate.py", "lattice_data.py")

    def enumerate(self):
        for family, n in _lattice_keys():
            for s in _s_values(n):
                yield {"family": family, "n": str(n), "s": str(s)}

    def value(self, params, digits):
        return epstein_zeta(params["family"], int(params["n"]), QQ(params["s"]), digits)


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
        message="Epstein zeta values for classical lattices through dimension %d"
        % MAX_DIMENSION,
        produced_by=_producer(
            generator,
            assisted_by=os.environ.get("NUMBERDB_ASSISTED_BY", "codex-cli"),
        ),
        upsert=False,
        run=run,
        rigour=generator.rigour,
    )

    stored = []
    for name, body in sorted(_source_files(generator).items()):
        attach(table, name, body, run=run, message=message, rigour=generator.rigour)
        stored.append(name)

    return {
        "tid": answer.get("tid", table),
        "revision": answer.get("revision"),
        "entries": len(entries),
        "files": stored,
    }


def main():
    _key_from_stdin()
    generator = EpsteinZetaClassicalLattices()
    if os.environ.get("NUMBERDB_SELF_CHECK") == "1":
        run_integrity_checks(generator.digits)
        return
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(
            fill_draft_once(
                generator,
                message=(
                    "Epstein zeta values for classical lattices through "
                    "dimension %d" % MAX_DIMENSION
                ),
            )
        )
        return
    if os.environ.get("NUMBERDB_PUBLISH") == "preview" or "--preview" in sys.argv:
        print(generator.preview())
        return
    report = generator.verify(sample=None)
    print(report)
    sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
