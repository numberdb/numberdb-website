"""Kullback-Leibler divergences between probability distributions -- numberdb.org/T343

For probability measures P and Q with P absolutely continuous with respect to
Q, this stores

    D(P || Q) = integral log(dP/dQ) dP,

in nats and in bits, for ordered pairs of named one-dimensional probability
distributions in their SciPy standard forms.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

Values are computed from closed forms in real ball arithmetic. The integrity
check compares finite discrete rows with SciPy's entropy routine, infinite
discrete rows with SciPy probability mass sums, and continuous rows with SciPy
numerical integration under the first distribution.
"""

import math
import os
import sys

import numberdb.sage as numberdb
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


WORKING_GUARD = 128

COMMON_PROBABILITIES = (
    QQ(1) / QQ(2),
    QQ(1) / QQ(3),
    QQ(1) / QQ(4),
    QQ(1) / QQ(5),
    QQ(1) / QQ(10),
    QQ(11) / QQ(100),
)

SMALL_PROBABILITIES = (
    QQ(1) / QQ(2),
    QQ(1) / QQ(3),
    QQ(1) / QQ(4),
    QQ(1) / QQ(10),
)

COMMON_POISSON_MEANS = (
    QQ(1) / QQ(2),
    QQ(1),
    QQ(3) / QQ(2),
    QQ(2),
    QQ(5),
    QQ(10),
)

NORMAL_SCALES = (
    QQ(1),
    QQ(2),
    QQ(1) / QQ(2),
    QQ(3),
)

EXPONENTIAL_SCALES = (
    QQ(1),
    QQ(2),
    QQ(1) / QQ(2),
    QQ(3),
    QQ(10),
)


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


def _q(text):
    return QQ(str(text))


def _format(value):
    return str(value)


def _parse_pair(shape):
    left, right = shape.split(";")
    return left, right


def _parse_rational_pair(shape):
    left, right = _parse_pair(shape)
    return _q(left), _q(right)


def _ordered_distinct_pairs(values):
    for i, first in enumerate(values):
        for second in values[i + 1:]:
            yield first, second
            yield second, first


def _bernoulli_kl_pq(p, q, digits):
    field = _field(digits)
    p_ball = field(p)
    q_ball = field(q)
    one = field(1)
    return (
        p_ball * (p_ball / q_ball).log()
        + (one - p_ball) * ((one - p_ball) / (one - q_ball)).log()
    )


def _bernoulli_kl(shape, digits):
    p, q = _parse_rational_pair(shape)
    return _bernoulli_kl_pq(p, q, digits)


def _binomial_kl(shape, digits):
    n_text, rest = shape.split(",", 1)
    p, q = _parse_rational_pair(rest)
    field = _field(digits)
    return field(int(n_text)) * _bernoulli_kl_pq(p, q, digits)


def _geometric_kl_pq(p, q, digits):
    field = _field(digits)
    p_ball = field(p)
    q_ball = field(q)
    one = field(1)
    return (
        (p_ball / q_ball).log()
        + (one - p_ball) / p_ball
        * ((one - p_ball) / (one - q_ball)).log()
    )


def _geometric_kl(shape, digits):
    p, q = _parse_rational_pair(shape)
    return _geometric_kl_pq(p, q, digits)


def _negative_binomial_kl(shape, digits):
    r_text, rest = shape.split(",", 1)
    p, q = _parse_rational_pair(rest)
    field = _field(digits)
    return field(int(r_text)) * _geometric_kl_pq(p, q, digits)


def _poisson_kl(shape, digits):
    lam, mu = _parse_rational_pair(shape)
    field = _field(digits)
    lam_ball = field(lam)
    mu_ball = field(mu)
    return lam_ball * (lam_ball / mu_ball).log() + mu_ball - lam_ball


def _normal_kl(shape, digits):
    left, right = _parse_pair(shape)
    mu1_text, sigma1_text = left.split(",")
    mu2_text, sigma2_text = right.split(",")
    field = _field(digits)
    mu1 = field(_q(mu1_text))
    sigma1 = field(_q(sigma1_text))
    mu2 = field(_q(mu2_text))
    sigma2 = field(_q(sigma2_text))
    return (
        (sigma2 / sigma1).log()
        + (sigma1 ** 2 + (mu1 - mu2) ** 2) / (2 * sigma2 ** 2)
        - field(QQ(1) / QQ(2))
    )


def _exponential_kl(shape, digits):
    theta1, theta2 = _parse_rational_pair(shape)
    field = _field(digits)
    first = field(theta1)
    second = field(theta2)
    return (second / first).log() + first / second - 1


def _kl_nats(distribution, shape, digits):
    if distribution == "bernoulli":
        return _bernoulli_kl(shape, digits)
    if distribution == "binomial":
        return _binomial_kl(shape, digits)
    if distribution == "geometric":
        return _geometric_kl(shape, digits)
    if distribution == "negative-binomial":
        return _negative_binomial_kl(shape, digits)
    if distribution == "poisson":
        return _poisson_kl(shape, digits)
    if distribution == "normal":
        return _normal_kl(shape, digits)
    if distribution == "exponential":
        return _exponential_kl(shape, digits)
    raise ValueError("unknown distribution %r" % (distribution,))


def _to_unit(value, unit, digits):
    if unit == "nats":
        return value
    if unit != "bits":
        raise ValueError("unknown unit %r" % (unit,))
    field = _field(digits)
    return field(value) / field(2).log()


def _shape_pair(first, second):
    return "%s;%s" % (_format(first), _format(second))


def _scipy_entropy(pk, qk):
    import scipy.stats as stats

    return stats.entropy(pk, qk)


def _scipy_infinite_sum(p_dist, q_dist, support):
    total = 0.0
    for k in support:
        p = p_dist.pmf(k)
        if p == 0.0:
            continue
        q = q_dist.pmf(k)
        total += p * (math.log(p) - math.log(q))
    return total


def _scipy_geometric(shape):
    import scipy.stats as stats

    p, q = (float(value) for value in _parse_rational_pair(shape))
    p_dist = stats.geom(p)
    q_dist = stats.geom(q)
    high = int(max(p_dist.ppf(1 - 1e-15), q_dist.ppf(1 - 1e-15))) + 20
    return _scipy_infinite_sum(p_dist, q_dist, range(1, high + 1))


def _scipy_negative_binomial(shape):
    import scipy.stats as stats

    r_text, rest = shape.split(",", 1)
    p, q = (float(value) for value in _parse_rational_pair(rest))
    r = int(r_text)
    p_dist = stats.nbinom(r, p)
    q_dist = stats.nbinom(r, q)
    high = int(max(p_dist.ppf(1 - 1e-15), q_dist.ppf(1 - 1e-15))) + 50
    return _scipy_infinite_sum(p_dist, q_dist, range(0, high + 1))


def _scipy_poisson(shape):
    import scipy.stats as stats

    lam, mu = (float(value) for value in _parse_rational_pair(shape))
    p_dist = stats.poisson(lam)
    q_dist = stats.poisson(mu)
    high = int(max(p_dist.ppf(1 - 1e-15), q_dist.ppf(1 - 1e-15))) + 20
    return _scipy_infinite_sum(p_dist, q_dist, range(0, high + 1))


def _scipy_continuous_expectation(distribution, shape):
    import scipy.integrate as integrate
    import scipy.stats as stats

    if distribution == "normal":
        left, right = _parse_pair(shape)
        mu1_text, sigma1_text = left.split(",")
        mu2_text, sigma2_text = right.split(",")
        p_dist = stats.norm(loc=float(_q(mu1_text)), scale=float(_q(sigma1_text)))
        q_dist = stats.norm(loc=float(_q(mu2_text)), scale=float(_q(sigma2_text)))
        low, high = -math.inf, math.inf
    elif distribution == "exponential":
        theta1, theta2 = (float(value) for value in _parse_rational_pair(shape))
        p_dist = stats.expon(scale=theta1)
        q_dist = stats.expon(scale=theta2)
        low, high = 0.0, math.inf
    else:
        raise ValueError("unknown continuous distribution %r" % (distribution,))

    def integrand(x):
        return p_dist.pdf(x) * (p_dist.logpdf(x) - q_dist.logpdf(x))

    value, error = integrate.quad(integrand, low, high, epsabs=1e-11, limit=200)
    if not math.isfinite(value) or error > 1e-6:
        raise ArithmeticError(
            "SciPy integral did not converge for %s %s: value=%r error=%r"
            % (distribution, shape, value, error))
    return value


def _scipy_expected(params):
    distribution = params["distribution"]
    shape = params["shape"]
    unit = params["unit"]

    if distribution == "bernoulli":
        p, q = (float(value) for value in _parse_rational_pair(shape))
        expected = _scipy_entropy([1 - p, p], [1 - q, q])
    elif distribution == "binomial":
        import scipy.stats as stats

        n_text, rest = shape.split(",", 1)
        p, q = (float(value) for value in _parse_rational_pair(rest))
        n = int(n_text)
        support = range(n + 1)
        expected = _scipy_entropy(
            [stats.binom.pmf(k, n, p) for k in support],
            [stats.binom.pmf(k, n, q) for k in support],
        )
    elif distribution == "geometric":
        expected = _scipy_geometric(shape)
    elif distribution == "negative-binomial":
        expected = _scipy_negative_binomial(shape)
    elif distribution == "poisson":
        expected = _scipy_poisson(shape)
    elif distribution in ("normal", "exponential"):
        expected = _scipy_continuous_expectation(distribution, shape)
    else:
        raise ValueError("unknown distribution %r" % (distribution,))

    if unit == "bits":
        expected /= math.log(2)
    return expected


def _midpoint(value):
    return float((value.lower() + value.upper()) / 2)


class KullbackLeiblerDivergences(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T343")
    parameters = ("distribution", "shape", "unit")
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self):
        for p, q in _ordered_distinct_pairs(COMMON_PROBABILITIES):
            shape = _shape_pair(p, q)
            for unit in ("nats", "bits"):
                yield {"distribution": "bernoulli", "shape": shape, "unit": unit}

        for n in range(2, 11):
            for p, q in _ordered_distinct_pairs(SMALL_PROBABILITIES):
                shape = "%d,%s" % (n, _shape_pair(p, q))
                for unit in ("nats", "bits"):
                    yield {"distribution": "binomial", "shape": shape, "unit": unit}

        for p, q in _ordered_distinct_pairs(COMMON_PROBABILITIES):
            shape = _shape_pair(p, q)
            for unit in ("nats", "bits"):
                yield {"distribution": "geometric", "shape": shape, "unit": unit}

        for r in range(2, 11):
            for p, q in _ordered_distinct_pairs(SMALL_PROBABILITIES):
                shape = "%d,%s" % (r, _shape_pair(p, q))
                for unit in ("nats", "bits"):
                    yield {"distribution": "negative-binomial", "shape": shape, "unit": unit}

        for lam, mu in _ordered_distinct_pairs(COMMON_POISSON_MEANS):
            shape = _shape_pair(lam, mu)
            for unit in ("nats", "bits"):
                yield {"distribution": "poisson", "shape": shape, "unit": unit}

        for sigma1, sigma2 in _ordered_distinct_pairs(NORMAL_SCALES):
            shape = "0,%s;0,%s" % (_format(sigma1), _format(sigma2))
            for unit in ("nats", "bits"):
                yield {"distribution": "normal", "shape": shape, "unit": unit}

        for theta1, theta2 in _ordered_distinct_pairs(EXPONENTIAL_SCALES):
            shape = _shape_pair(theta1, theta2)
            for unit in ("nats", "bits"):
                yield {"distribution": "exponential", "shape": shape, "unit": unit}

    def value(self, params, digits):
        distribution = str(params["distribution"])
        shape = str(params["shape"])
        unit = str(params["unit"])
        return _to_unit(_kl_nats(distribution, shape, digits), unit, digits)


def run_integrity_checks():
    generator = KullbackLeiblerDivergences()
    largest = (0.0, None, None, None)
    for params in generator.enumerate():
        value = generator.value(params, 50)
        got = _midpoint(value)
        expected = _scipy_expected(params)
        difference = abs(got - expected)
        if difference > largest[0]:
            largest = (difference, dict(params), got, expected)
        if difference > 5e-8:
            raise ArithmeticError(
                "SciPy check failed for %s: %.17g here, %.17g independently"
                % (params, got, expected))
    print("largest SciPy difference %.3g at %s" % (largest[0], largest[1]))


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
    generator = KullbackLeiblerDivergences()
    run_integrity_checks()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="KL divergence values of probability distributions"))
    elif os.environ.get("NUMBERDB_API_KEY"):
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
    else:
        print("integrity checks passed; NUMBERDB_API_KEY is not set, so verify() was skipped")
