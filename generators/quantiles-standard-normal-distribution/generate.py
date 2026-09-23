"""Quantiles of the standard normal distribution -- numberdb.org/T452

For each lower-tail probability p in the table, this computes the standard
normal quantile z_p, where Phi(z_p) = p.

Run it with SageMath:

    $ sage -pip install numberdb
    $ sage -python generate.py
    $ sage -python generate.py --publish
    $ agents/sage.sh generators/quantiles-standard-normal-distribution/generate.py
    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
        agents/sage.sh generators/quantiles-standard-normal-distribution/generate.py

The computation uses bisection with Sage real balls.  The returned value is the
final bracketing ball, not a rounded midpoint.
"""

from functools import lru_cache
import os
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


TABLE = os.environ.get("NUMBERDB_TABLE", "T452")
DIGITS = 100
WORKING_GUARD = 128
BRACKET = (QQ(-10), QQ(10))


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


def _cdf(x, field):
    z = field(x)
    return (field(1) + (z / field(2).sqrt()).erf()) / field(2)


def _probabilities():
    values = {QQ(k) / QQ(1000) for k in range(1, 1000)}
    values.update(
        [
            QQ(1) / QQ(10000),
            QQ(1) / QQ(2000),
            QQ(1) / QQ(400),
            QQ(399) / QQ(400),
            QQ(1999) / QQ(2000),
            QQ(9999) / QQ(10000),
        ]
    )
    for p in sorted(values):
        yield p


def _assert_initial_bracket(p, field):
    low, high = BRACKET
    if not _cdf(low, field).upper() < p:
        raise ArithmeticError("lower endpoint does not bracket p=%s" % (p,))
    if not _cdf(high, field).lower() > p:
        raise ArithmeticError("upper endpoint does not bracket p=%s" % (p,))


@lru_cache(maxsize=None)
def _quantile(p_text, digits):
    p = QQ(p_text)
    if p == QQ(1) / QQ(2):
        return ZZ(0)

    field = _field(digits)
    _assert_initial_bracket(p, field)

    low, high = BRACKET
    target_width = QQ(1) / (QQ(10) ** (digits + 6))
    while high - low > target_width:
        mid = (low + high) / QQ(2)
        value = _cdf(mid, field)
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
    common = {
        QQ(1) / QQ(2): "The median of the standard normal distribution is exactly zero.",
        QQ(19) / QQ(20): "This is the one-sided 5% upper critical value.",
        QQ(39) / QQ(40): "This is the positive cutoff for a two-sided 5% normal test.",
        QQ(99) / QQ(100): "This is the one-sided 1% upper critical value.",
        QQ(199) / QQ(200): "This is the positive cutoff for a two-sided 1% normal test.",
        QQ(999) / QQ(1000): "This is the one-sided 0.1% upper critical value.",
    }
    return common.get(p, "")


class StandardNormalQuantiles(numberdb.Generator):

    table = TABLE
    parameters = ("p",)
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self):
        for p in _probabilities():
            yield {"p": str(p)}

    def value(self, params, digits):
        p = QQ(params["p"])
        value = _quantile(str(p), digits)
        comment = _comment(p)
        if comment:
            return {"number": value, "comment": comment}
        return value


if __name__ == "__main__":
    _key_from_stdin()
    generator = StandardNormalQuantiles()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="standard normal quantiles"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
