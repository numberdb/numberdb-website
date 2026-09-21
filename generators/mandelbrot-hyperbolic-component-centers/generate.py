"""Centers of the hyperbolic components of the Mandelbrot set -- numberdb.org/T392.

Let f_c(z) = z^2 + c, set F_0(c) = 0 and F_{n+1}(c) = F_n(c)^2 + c.
This generator fills T392 with the roots of the exact-period Gleason
polynomial

    G_n(c) = F_n(c) / prod_{d|n, d<n} G_d(c),

for 1 <= n <= 9. The roots are sorted by increasing real part, with ties by
increasing imaginary part.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import divisors, moebius
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.complex_roots import complex_roots
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing

TABLE = os.environ.get("NUMBERDB_TABLE", "T392")
MAX_PERIOD = 9
DIGITS = 100
ROOT_MIN_PREC = 800

C_RING = PolynomialRing(ZZ, "c")
c = C_RING.gen()

T168_SLUG = "Bifurcation_points_of_the_period-doubling_cascade_of_the_logistic_map"
T169_SLUG = "Periodic_windows_of_the_logistic_map_by_kneading_word"

EQUALS = {
    (1, 1): (
        r"HREF{%s#s1,c}[$s_1$ in the $c$ normalisation]" % T168_SLUG
    ),
    (2, 1): (
        r"HREF{%s#s2,c}[$s_2$ in the $c$ normalisation]" % T168_SLUG
    ),
    (3, 1): (
        r"HREF{%s#RLC,superstable-c}[$c_W$ for $\mathtt{RLC}$]" % T169_SLUG
    ),
    (4, 1): (
        r"HREF{%s#RLLC,superstable-c}[$c_W$ for $\mathtt{RLLC}$]" % T169_SLUG
    ),
    (4, 2): (
        r"HREF{%s#s3,c}[$s_3$ in the $c$ normalisation]" % T168_SLUG
    ),
    (5, 1): (
        r"HREF{%s#RLLLC,superstable-c}[$c_W$ for $\mathtt{RLLLC}$]" % T169_SLUG
    ),
    (5, 2): (
        r"HREF{%s#RLLRC,superstable-c}[$c_W$ for $\mathtt{RLLRC}$]" % T169_SLUG
    ),
    (5, 3): (
        r"HREF{%s#RLRRC,superstable-c}[$c_W$ for $\mathtt{RLRRC}$]" % T169_SLUG
    ),
    (6, 1): (
        r"HREF{%s#RLLLLC,superstable-c}[$c_W$ for $\mathtt{RLLLLC}$]" % T169_SLUG
    ),
    (6, 2): (
        r"HREF{%s#RLLLRC,superstable-c}[$c_W$ for $\mathtt{RLLLRC}$]" % T169_SLUG
    ),
    (6, 3): (
        r"HREF{%s#RLLRRC,superstable-c}[$c_W$ for $\mathtt{RLLRRC}$]" % T169_SLUG
    ),
    (6, 4): (
        r"HREF{%s#RLLRLC,superstable-c}[$c_W$ for $\mathtt{RLLRLC}$]" % T169_SLUG
    ),
    (6, 5): (
        r"HREF{%s#RLRRRC,superstable-c}[$c_W$ for $\mathtt{RLRRRC}$]" % T169_SLUG
    ),
    (7, 1): (
        r"HREF{%s#RLLLLLC,superstable-c}[$c_W$ for $\mathtt{RLLLLLC}$]" % T169_SLUG
    ),
    (7, 2): (
        r"HREF{%s#RLLLLRC,superstable-c}[$c_W$ for $\mathtt{RLLLLRC}$]" % T169_SLUG
    ),
    (7, 3): (
        r"HREF{%s#RLLLRRC,superstable-c}[$c_W$ for $\mathtt{RLLLRRC}$]" % T169_SLUG
    ),
    (7, 4): (
        r"HREF{%s#RLLLRLC,superstable-c}[$c_W$ for $\mathtt{RLLLRLC}$]" % T169_SLUG
    ),
    (7, 5): (
        r"HREF{%s#RLLRRLC,superstable-c}[$c_W$ for $\mathtt{RLLRRLC}$]" % T169_SLUG
    ),
    (7, 6): (
        r"HREF{%s#RLLRRRC,superstable-c}[$c_W$ for $\mathtt{RLLRRRC}$]" % T169_SLUG
    ),
    (7, 7): (
        r"HREF{%s#RLLRLRC,superstable-c}[$c_W$ for $\mathtt{RLLRLRC}$]" % T169_SLUG
    ),
    (7, 10): (
        r"HREF{%s#RLRRLRC,superstable-c}[$c_W$ for $\mathtt{RLRRLRC}$]" % T169_SLUG
    ),
    (7, 11): (
        r"HREF{%s#RLRRRRC,superstable-c}[$c_W$ for $\mathtt{RLRRRRC}$]" % T169_SLUG
    ),
    (8, 1): (
        r"HREF{%s#RLLLLLLC,superstable-c}[$c_W$ for $\mathtt{RLLLLLLC}$]" % T169_SLUG
    ),
    (8, 2): (
        r"HREF{%s#RLLLLLRC,superstable-c}[$c_W$ for $\mathtt{RLLLLLRC}$]" % T169_SLUG
    ),
    (8, 3): (
        r"HREF{%s#RLLLLRRC,superstable-c}[$c_W$ for $\mathtt{RLLLLRRC}$]" % T169_SLUG
    ),
    (8, 4): (
        r"HREF{%s#RLLLLRLC,superstable-c}[$c_W$ for $\mathtt{RLLLLRLC}$]" % T169_SLUG
    ),
    (8, 5): (
        r"HREF{%s#RLLLRRLC,superstable-c}[$c_W$ for $\mathtt{RLLLRRLC}$]" % T169_SLUG
    ),
    (8, 6): (
        r"HREF{%s#RLLLRRRC,superstable-c}[$c_W$ for $\mathtt{RLLLRRRC}$]" % T169_SLUG
    ),
    (8, 7): (
        r"HREF{%s#RLLLRLRC,superstable-c}[$c_W$ for $\mathtt{RLLLRLRC}$]" % T169_SLUG
    ),
    (8, 8): (
        r"HREF{%s#RLLLRLLC,superstable-c}[$c_W$ for $\mathtt{RLLLRLLC}$]" % T169_SLUG
    ),
    (8, 9): (
        r"HREF{%s#RLLRRLRC,superstable-c}[$c_W$ for $\mathtt{RLLRRLRC}$]" % T169_SLUG
    ),
    (8, 10): (
        r"HREF{%s#RLLRRRRC,superstable-c}[$c_W$ for $\mathtt{RLLRRRRC}$]" % T169_SLUG
    ),
    (8, 11): (
        r"HREF{%s#RLLRRRLC,superstable-c}[$c_W$ for $\mathtt{RLLRRRLC}$]" % T169_SLUG
    ),
    (8, 12): (
        r"HREF{%s#RLLRLRLC,superstable-c}[$c_W$ for $\mathtt{RLLRLRLC}$]" % T169_SLUG
    ),
    (8, 13): (
        r"HREF{%s#RLLRLRRC,superstable-c}[$c_W$ for $\mathtt{RLLRLRRC}$]" % T169_SLUG
    ),
    (8, 18): (
        r"HREF{%s#RLRRLRRC,superstable-c}[$c_W$ for $\mathtt{RLRRLRRC}$]" % T169_SLUG
    ),
    (8, 21): (
        r"HREF{%s#RLRRRRRC,superstable-c}[$c_W$ for $\mathtt{RLRRRRRC}$]" % T169_SLUG
    ),
    (8, 24): (
        r"HREF{%s#s4,c}[$s_4$ in the $c$ normalisation]" % T168_SLUG
    ),
}

_ITERATE_CACHE = {}
_GLEASON_CACHE = {}
_CENTER_CACHE = {}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def critical_iterate(n):
    """Return F_n(c)=f_c^n(0)."""
    n = int(n)
    if n not in _ITERATE_CACHE:
        value = C_RING(0)
        for _ in range(n):
            value = value * value + c
        _ITERATE_CACHE[n] = value
    return _ITERATE_CACHE[n]


def gleason_polynomial(n):
    """Return the exact-period Gleason polynomial G_n(c)."""
    n = int(n)
    if n in _GLEASON_CACHE:
        return _GLEASON_CACHE[n]

    polynomial = critical_iterate(n)
    for d in sorted(divisors(n)):
        if d == n:
            continue
        quotient, remainder = polynomial.quo_rem(gleason_polynomial(d))
        if remainder:
            raise ArithmeticError("G_%d does not divide F_%d exactly" % (d, n))
        polynomial = quotient
    if polynomial.leading_coefficient() < 0:
        polynomial = -polynomial
    _GLEASON_CACHE[n] = polynomial
    return polynomial


def expected_degree(n):
    return sum(ZZ(moebius(n // d)) * ZZ(2) ** (d - 1) for d in divisors(n))


def _interval_sort_key(root):
    return (root.real().center(), root.imag().center())


def _interval_contains_zero(interval):
    contains_zero = getattr(interval, "contains_zero", None)
    if contains_zero is not None:
        return bool(contains_zero())
    return interval.lower() <= 0 <= interval.upper()


def _imaginary_part_contains_zero(root):
    return _interval_contains_zero(root.imag())


def _is_negative_interval(interval):
    return interval.upper() < 0


def _is_positive_interval(interval):
    return interval.lower() > 0


def _intervals_overlap(first, second):
    return not (first.upper() < second.lower() or second.upper() < first.lower())


def _conjugate_imaginary_intervals(first, second):
    return _interval_contains_zero(first.imag() + second.imag())


def _absolute_diameter(value):
    if value is None:
        return ZZ(0)
    diameter = getattr(value, "absolute_diameter", None)
    if diameter is None:
        return ZZ(0)
    return abs(diameter())


def _real_projection_clusters(roots):
    clusters = []
    current = []
    current_upper = None
    for root in roots:
        real = root.real()
        if not current:
            current = [root]
            current_upper = real.upper()
            continue
        if real.lower() <= current_upper:
            current.append(root)
            if real.upper() > current_upper:
                current_upper = real.upper()
        else:
            clusters.append(current)
            current = [root]
            current_upper = real.upper()
    if current:
        clusters.append(current)
    return clusters


def _check_real_projection_order(period, roots):
    """Prove no non-conjugate roots share a real part."""
    for cluster in _real_projection_clusters(roots):
        if len(cluster) == 1:
            continue
        if len(cluster) != 2:
            raise ArithmeticError(
                "period %d has %d roots with overlapping real intervals" % (
                    period, len(cluster))
            )
        first, second = cluster
        first_imag = first.imag()
        second_imag = second.imag()
        opposite_signs = (
            _is_negative_interval(first_imag) and _is_positive_interval(second_imag)
        ) or (
            _is_positive_interval(first_imag) and _is_negative_interval(second_imag)
        )
        if not opposite_signs or not _conjugate_imaginary_intervals(first, second):
            raise ArithmeticError(
                "period %d has a non-conjugate real-part tie" % period
            )


def centers(period):
    """Return the sorted centers for one exact period."""
    period = int(period)
    if period in _CENTER_CACHE:
        return _CENTER_CACHE[period]

    polynomial = gleason_polynomial(period)
    isolated = complex_roots(polynomial, min_prec=ROOT_MIN_PREC)
    roots = [root for root, multiplicity in isolated]
    if any(multiplicity != 1 for _root, multiplicity in isolated):
        raise ArithmeticError("period %d has a multiple root" % period)
    roots = sorted(roots, key=_interval_sort_key)
    if len(roots) != polynomial.degree():
        raise ArithmeticError("period %d root count mismatch" % period)
    _check_real_projection_order(period, roots)

    real_count = polynomial.number_of_real_roots()
    isolated_real_count = sum(
        1 for root in roots if _imaginary_part_contains_zero(root)
    )
    if isolated_real_count != real_count:
        raise ArithmeticError(
            "period %d has %d certified real roots, expected %d" % (
                period, isolated_real_count, real_count)
        )

    records = []
    for index, root in enumerate(roots, start=1):
        root_is_real = _imaginary_part_contains_zero(root)
        if period == 1:
            value = ZZ(0)
        elif period == 2:
            value = ZZ(-1)
        elif root_is_real:
            value = root.real()
        else:
            value = root
        record = {"number": value}
        equals = EQUALS.get((period, index))
        if equals:
            record["equals"] = equals
        records.append(record)

    _CENTER_CACHE[period] = records
    return records


class MandelbrotHyperbolicComponentCenters(numberdb.Generator):
    """Generator for T392, centers of Mandelbrot hyperbolic components."""

    table = TABLE
    parameters = ("n", "i")
    type = "C"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self):
        for period in range(1, MAX_PERIOD + 1):
            for index in range(1, len(centers(period)) + 1):
                yield {"n": str(period), "i": str(index)}

    def value(self, params, digits):
        period = ZZ(params["n"])
        index = ZZ(params["i"])
        return centers(period)[int(index) - 1]


def run_integrity_checks():
    fingerprints = {
        1: c,
        2: c + 1,
        3: c ** 3 + 2 * c ** 2 + c + 1,
        4: c ** 6 + 3 * c ** 5 + 3 * c ** 4 + 3 * c ** 3 + 2 * c ** 2 + 1,
    }
    for period, expected in fingerprints.items():
        if gleason_polynomial(period) != expected:
            raise ArithmeticError("G_%d does not match the convention fingerprint" % period)

    total = 0
    real_counts = []
    worst_diameter = ZZ(0)
    worst_at = None
    for period in range(1, MAX_PERIOD + 1):
        polynomial = gleason_polynomial(period)
        if polynomial.degree() != expected_degree(period):
            raise ArithmeticError("G_%d has degree %d, expected %d" % (
                period, polynomial.degree(), expected_degree(period)))
        real_counts.append(int(polynomial.number_of_real_roots()))

        for index, record in enumerate(centers(period), start=1):
            total += 1
            value = record["number"]
            real = value.real() if hasattr(value, "real") else value
            imag = value.imag() if hasattr(value, "imag") else None
            diameter = max(_absolute_diameter(real), _absolute_diameter(imag))
            if diameter > worst_diameter:
                worst_diameter = diameter
                worst_at = (period, index)

    expected_reals = [1, 1, 1, 2, 3, 5, 9, 16, 28]
    if real_counts != expected_reals:
        raise ArithmeticError("real root counts %s, expected %s" % (
            real_counts, expected_reals))

    print("integrity checks passed for %d centers through period %d" % (
        total, MAX_PERIOD))
    print("real root counts: %s" % ",".join(str(n) for n in real_counts))
    print("worst root diameter is %s at n=%s, i=%s" % (
        worst_diameter, worst_at[0], worst_at[1]))
    print("no non-conjugate real-part ties occur through n=%d" % MAX_PERIOD)


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


if __name__ == "__main__":
    _key_from_stdin()
    generator = MandelbrotHyperbolicComponentCenters()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="fill Mandelbrot hyperbolic component centers",
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
