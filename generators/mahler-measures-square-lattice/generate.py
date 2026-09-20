"""Mahler measures m_k = m(x + x^-1 + y + y^-1 + k) -- numberdb.org/T282.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The table stores nonnegative integer k, since replacing x and y by -x and
-y gives the same Mahler measure for -k. The values are computed as proven
real enclosures: Jensen's one-variable integral is used for k = 1, 2, 3, the
closed form 4G/pi for k = 4, and the absolutely convergent logarithmic series
for k >= 5. Entry comments list the conductor of the associated elliptic
curve where that curve is nonsingular.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import binomial
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField
from sage.rings.complex_arb import ComplexBallField


TABLE = os.environ.get("NUMBERDB_TABLE", "T282")

# The range was extended from 100 to 112 after a conductor census: among
# k <= 400, this includes every nonsingular row whose associated elliptic
# curve has conductor below 1000.
MAX_K = 112

# Bits beyond the requested digits. At 100 digits, the widest enclosure among
# k = 0..100 has radius below 2e-119 with this guard.
WORKING_GUARD = 96

# Terms are summed until the rigorous geometric tail is smaller than this many
# decimal orders beyond the requested digits.
TAIL_GUARD = 20


CONDUCTORS = {
    1: 15, 2: 24, 3: 21, 5: 15, 6: 120, 7: 231, 8: 24, 9: 195,
    10: 840, 11: 1155, 12: 48, 13: 663, 14: 840, 15: 3135, 16: 15,
    17: 4641, 18: 1848, 19: 6555, 20: 240, 21: 1785, 22: 3432,
    23: 1311, 24: 840, 25: 3045, 26: 17160, 27: 2139, 28: 336,
    29: 4785, 30: 26520, 31: 3255, 32: 42, 33: 35409, 34: 38760,
    35: 42315, 36: 240, 37: 50061, 38: 54264, 39: 58695, 40: 1320,
    41: 22755, 42: 73416, 43: 78819, 44: 2640, 45: 4305, 46: 19320,
    47: 103071, 48: 429, 49: 5565, 50: 2760, 51: 131835, 52: 4368,
    53: 21147, 54: 3480, 55: 165495, 56: 10920, 57: 184281, 58: 21576,
    59: 68145, 60: 1680, 61: 226005, 62: 237336, 63: 83013, 64: 510,
    65: 273585, 66: 286440, 67: 99897, 68: 816, 69: 327405,
    70: 341880, 71: 71355, 72: 7752, 73: 387849, 74: 404040,
    75: 84135, 76: 4560, 77: 16863, 78: 473304, 79: 98355, 80: 1995,
    81: 19635, 82: 550056, 83: 570459, 84: 18480, 85: 22695,
    86: 211560, 87: 657111, 88: 42504, 89: 703545, 90: 242520,
    91: 752115, 92: 12144, 93: 802869, 94: 39480, 95: 285285,
    96: 690, 97: 911121, 98: 134232, 99: 322905, 100: 3120,
    101: 1028685, 102: 151368, 103: 363693, 104: 1560, 105: 1155945,
    106: 1189320, 107: 1223331, 108: 4368, 109: 1293285, 110: 1329240,
    111: 1365855, 112: 609,
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _fields(digits):
    bits = numberdb.bits(digits, losing=WORKING_GUARD)
    return RealBallField(bits), ComplexBallField(bits)


def _integral(C, integrand, a, b):
    value = C.integral(integrand, a, b)
    if not value.imag().contains_zero():
        raise ArithmeticError("the integral came out complex: %s" % value)
    real = value.real()
    if not real.is_finite():
        raise ArithmeticError("the integral did not return a finite ball")
    return real


def _small_k_integral(k, digits):
    """Jensen's formula after a substitution removing the endpoint singularity."""
    if k <= 0 or k >= 4:
        raise ValueError("the transformed integral is for k = 1, 2, 3")
    R, C = _fields(digits)
    kk = R(k)
    root = kk.sqrt()
    pi = R.pi()

    def integrand(t, analytic):
        sine = t.sin()
        cosine = t.cos()
        return (2 * root * cosine * (root * cosine / 2).arcsinh(analytic=analytic)
                / (1 - kk * sine * sine / 4).sqrt(analytic=analytic))

    return _integral(C, integrand, C(0), C(pi / 2)) / pi


def _four_value(digits):
    """m_4 = 4G/pi, with G = L(2, chi_-4) evaluated by arb's Hurwitz zeta."""
    R, _ = _fields(digits)
    catalan = (R(2).zeta(R(QQ(1) / 4)) - R(2).zeta(R(QQ(3) / 4))) / 16
    return 4 * catalan / R.pi()


def _large_k_series(k, digits):
    """log(k) - sum binomial(2n,n)^2/(2n k^(2n)), with a rigorous tail."""
    if k <= 4:
        raise ValueError("the large-k series needs k > 4")
    R, _ = _fields(digits)
    kk = ZZ(k)
    k_ball = R(kk)
    ratio = R(QQ(16) / QQ(kk * kk))
    value = k_ball.log()
    total = R(0)
    target = R(10) ** (-(digits + TAIL_GUARD))

    n = 1
    while True:
        central = ZZ(binomial(2 * n, n))
        total += R(central * central) / (2 * n * k_ball ** (2 * n))
        next_n = n + 1
        tail = ratio ** next_n / (2 * next_n * (1 - ratio))
        if tail < target:
            value -= total
            return value.add_error(tail.upper())
        n = next_n


def mahler_measure(k, digits=100):
    k = int(k)
    if k < 0:
        k = -k
    if k == 0:
        return ZZ(0)
    if k < 4:
        return _small_k_integral(k, digits)
    if k == 4:
        return _four_value(digits)
    return _large_k_series(k, digits)


def _direct_jensen_integral(k, digits):
    """Independent one-dimensional Jensen integral, used as a check."""
    R, C = _fields(digits)
    kk = R(k)
    pi = R.pi()
    if k == 0:
        return R(0)
    if k < 4:
        return _small_power_series(k, digits)
    if k == 4:
        def integrand(t, analytic):
            return 4 * t.cos().arcsinh(analytic=analytic)
        return _integral(C, integrand, C(0), C(pi / 2)) / pi

    def integrand(t, analytic):
        return ((kk + 2 * t.cos()) / 2).arccosh(analytic=analytic)

    return _integral(C, integrand, C(0), C(pi)) / pi


def _small_power_series(k, digits):
    """Small-k power series from expanding the transformed Jensen integral."""
    if not 0 <= k < 4:
        raise ValueError("the small-k series is used for 0 <= k < 4")
    if k == 0:
        return ZZ(0)
    R, _ = _fields(digits)
    kk = ZZ(k)
    total = R(0)
    target = R(10) ** (-(digits + TAIL_GUARD))

    # The summand is indexed by j from the asinh expansion and ell from the
    # binomial expansion of (1 - k sin(t)^2/4)^(-1/2). Summing by total degree
    # gives a reliable stopping test for k = 1, 2, 3, where the series is
    # absolutely convergent.
    consecutive_small = 0
    n = 0
    while True:
        diagonal = R(0)
        for j in range(n + 1):
            ell = n - j
            b = j + 1
            integral_over_pi = (
                QQ(binomial(2 * ell, ell) * binomial(2 * b, b))
                / (2 * QQ(4) ** (ell + b) * QQ(binomial(ell + b, ell))))
            coefficient = (
                QQ((-1) ** j)
                * QQ(binomial(2 * j, j) * binomial(2 * ell, ell))
                * integral_over_pi
                / (QQ(16) ** (j + ell) * QQ(2 * j + 1)))
            diagonal += R(coefficient) * R(kk) ** (n + 1)
        total += diagonal
        if diagonal.abs() < target:
            consecutive_small += 1
            if consecutive_small >= 6:
                return total.add_error((6 * target).upper())
        else:
            consecutive_small = 0
        n += 1
        if n > 1000:
            raise ArithmeticError("small-k power series did not converge")


def _overlap_or_raise(label, left, right):
    R = left.parent()
    if not left.is_finite() or not right.is_finite():
        raise ArithmeticError("%s produced a non-finite comparison" % label)
    if not left.overlaps(R(right)):
        raise ArithmeticError("%s: %s does not overlap %s" % (label, left, right))


def run_integrity_checks():
    """Check every row against a computation that does not share the main path."""
    for k in range(MAX_K + 1):
        computed = mahler_measure(k, 100)
        if k == 0:
            if computed != 0:
                raise ArithmeticError("k=0 should be exact zero")
            continue
        independent = _direct_jensen_integral(k, 100)
        _overlap_or_raise("k=%d" % k, computed, independent)

    # The formulas should also agree with the public table that already holds
    # the k = 4 value as the square-lattice spanning-tree entropy.
    _overlap_or_raise("k=4 Catalan check", _four_value(100),
                      _direct_jensen_integral(4, 100))


def _entry_comment(k):
    if k == 0:
        return ("Here $x+x^{-1}+y+y^{-1}=x^{-1}y^{-1}(x+y)(xy+1)$, "
                "so the Mahler measure is zero.")
    if k == 1:
        return ("Rogers and Zudilin proved an identity relating this value "
                "to the $L$-series of a conductor 15 elliptic curve.")
    if k == 4:
        return ("This is $4G/\\pi$, the "
                "HREF{Entropy_constants_of_lattice_models#spanning-tree,square,entropy}"
                "[square-lattice spanning-tree entropy].")
    if k in CONDUCTORS:
        return ("The associated curve $E_k$ has conductor "
                "$%d$." % CONDUCTORS[k])
    return ""


class SquareLatticeMahlerMeasures(numberdb.Generator):
    """Generator for T282, the table of $m_k$."""

    table = TABLE
    parameters = ("k",)
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self, max_k=MAX_K):
        for k in range(max_k + 1):
            yield {"k": str(k)}

    def value(self, params, digits):
        k = int(params["k"])
        entry = {"number": mahler_measure(k, digits)}
        comment = _entry_comment(k)
        if comment:
            entry["comment"] = comment
        return entry


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
    generator = SquareLatticeMahlerMeasures()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="Mahler measures for x+x^-1+y+y^-1+k, k = 0..%d" % MAX_K))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
