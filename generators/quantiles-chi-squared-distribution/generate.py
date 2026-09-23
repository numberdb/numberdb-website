"""Quantiles of the chi-squared distribution -- numberdb.org/T453

For each degrees of freedom nu and lower-tail probability p in the table, this
computes the chi-squared quantile chi^2_{nu,p}, where F_nu(chi^2_{nu,p}) = p.

Run it with SageMath:

    $ sage -pip install numberdb
    $ sage -python generate.py
    $ sage -python generate.py --publish
    $ agents/sage.sh generators/quantiles-chi-squared-distribution/generate.py
    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
        agents/sage.sh generators/quantiles-chi-squared-distribution/generate.py

The computation uses bisection with Sage real balls. The returned value is the
final bracketing ball, not a rounded midpoint.
"""

from functools import lru_cache
import os
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


TABLE = os.environ.get("NUMBERDB_TABLE", "T453")
DIGITS = 100
WORKING_GUARD = 128
PROBABILITIES = (
    QQ(1) / QQ(200),
    QQ(1) / QQ(100),
    QQ(1) / QQ(40),
    QQ(1) / QQ(20),
    QQ(1) / QQ(10),
    QQ(1) / QQ(4),
    QQ(1) / QQ(2),
    QQ(3) / QQ(4),
    QQ(9) / QQ(10),
    QQ(19) / QQ(20),
    QQ(39) / QQ(40),
    QQ(99) / QQ(100),
    QQ(199) / QQ(200),
    QQ(999) / QQ(1000),
)
DEGREES_OF_FREEDOM = tuple(range(1, 31)) + (40, 50, 60, 100)


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def _field(digits):
    return RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def _cdf(x, nu, field):
    a = field(QQ(nu) / QQ(2))
    y = field(x) / field(2)
    return a.gamma_inc_lower(y) / a.gamma()


def _assert_initial_bracket(p, nu, field):
    low, high = _initial_bracket(nu)
    if not _cdf(low, nu, field).upper() < p:
        raise ArithmeticError("lower endpoint does not bracket nu=%s p=%s" % (nu, p))
    while not _cdf(high, nu, field).lower() > p:
        high *= QQ(2)
    return low, high


def _initial_bracket(nu):
    return QQ(0), QQ(2 * nu + 30)


@lru_cache(maxsize=None)
def _quantile(nu_text, p_text, digits):
    nu = ZZ(nu_text)
    p = QQ(p_text)
    field = _field(digits)
    low, high = _assert_initial_bracket(p, nu, field)
    target_width = QQ(1) / (QQ(10) ** (digits + 8))

    while high - low > target_width:
        mid = (low + high) / QQ(2)
        value = _cdf(mid, nu, field)
        if value.upper() < p:
            low = mid
        elif value.lower() > p:
            high = mid
        else:
            raise ArithmeticError(
                "cdf(%s) overlaps p=%s before the bracket is narrow enough"
                % (mid, p)
            )

    return field(low).union(field(high))


def _comment(p):
    comments = {
        QQ(1) / QQ(200): "This is the lower cutoff for a central two-sided 1% chi-squared test.",
        QQ(1) / QQ(40): "This is the lower cutoff for a central two-sided 5% chi-squared test.",
        QQ(19) / QQ(20): "This is the one-sided 5% upper critical value.",
        QQ(39) / QQ(40): "This is the upper cutoff for a central two-sided 5% chi-squared test.",
        QQ(99) / QQ(100): "This is the one-sided 1% upper critical value.",
        QQ(199) / QQ(200): "This is the upper cutoff for a central two-sided 1% chi-squared test.",
        QQ(999) / QQ(1000): "This is the one-sided 0.1% upper critical value.",
    }
    return comments.get(p, "")


class ChiSquaredQuantiles(numberdb.Generator):

    table = TABLE
    parameters = ("nu", "p")
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self):
        for nu in DEGREES_OF_FREEDOM:
            for p in PROBABILITIES:
                yield {"nu": str(nu), "p": str(p)}

    def value(self, params, digits):
        nu = ZZ(params["nu"])
        p = QQ(params["p"])
        value = _quantile(str(nu), str(p), digits)
        comment = _comment(p)
        if comment:
            return {"number": value, "comment": comment}
        return value


def _normal_cdf(x, field):
    return (field(1) + (x / field(2).sqrt()).erf()) / field(2)


def _even_survival(x, nu, field):
    y = field(x) / field(2)
    term = field(1)
    total = field(1)
    for j in range(1, ZZ(nu) // ZZ(2)):
        term = term * y / ZZ(j)
        total += term
    return (-y).exp() * total


def _checked_contains_zero(value, label):
    if not value.contains_zero():
        raise AssertionError("%s did not contain zero: %s" % (label, value))
    if not value.is_finite():
        raise AssertionError("%s is not finite: %s" % (label, value))


def _private_checks():
    field = _field(DIGITS)
    values = {}
    generator = ChiSquaredQuantiles()
    for params in generator.enumerate():
        nu = ZZ(params["nu"])
        p = QQ(params["p"])
        raw = generator.value(params, DIGITS)
        value = raw["number"] if isinstance(raw, dict) else raw
        values[(nu, p)] = value
        _checked_contains_zero(_cdf(value, nu, field) - field(p), "cdf bracket %s %s" % (nu, p))

    for p in PROBABILITIES:
        exact = -field(2) * (field(1) - field(p)).log()
        _checked_contains_zero(values[(ZZ(2), p)] - exact, "nu=2 formula %s" % (p,))

    for p in PROBABILITIES:
        target = (field(1) + field(p)) / field(2)
        _checked_contains_zero(
            _normal_cdf(values[(ZZ(1), p)].sqrt(), field) - target,
            "nu=1 normal relation %s" % (p,),
        )

    for nu in DEGREES_OF_FREEDOM:
        previous = None
        for p in PROBABILITIES:
            current = values[(ZZ(nu), p)]
            if previous is not None and not previous.upper() < current.lower():
                raise AssertionError("p monotonicity failed at nu=%s p=%s" % (nu, p))
            previous = current

    for p in PROBABILITIES:
        previous = None
        for nu in DEGREES_OF_FREEDOM:
            current = values[(ZZ(nu), p)]
            if previous is not None and not previous.upper() < current.lower():
                raise AssertionError("nu monotonicity failed at nu=%s p=%s" % (nu, p))
            previous = current

    for nu in DEGREES_OF_FREEDOM:
        if nu % 2:
            continue
        for p in PROBABILITIES:
            survival = _even_survival(values[(ZZ(nu), p)], nu, field)
            _checked_contains_zero(
                survival - field(1 - p),
                "even nu survival formula %s %s" % (nu, p),
            )

    print("private checks passed for %d entries" % (len(values),))


if __name__ == "__main__":
    _key_from_stdin()
    if os.environ.get("NUMBERDB_CHECK_IDENTITIES") == "1":
        _private_checks()
        sys.exit(0)
    generator = ChiSquaredQuantiles()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="chi-squared quantiles"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
