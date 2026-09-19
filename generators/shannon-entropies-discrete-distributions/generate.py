"""Shannon entropies of discrete probability distributions -- numberdb.org/T339

For a discrete random variable X with probability mass function p, this stores

    H(X) = - sum_x p(x) log(p(x)),

in nats and in bits, for named discrete distributions in their standard
forms.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

Values are computed in real ball arithmetic. Infinite sums are truncated only
after a proved positive tail bound is smaller than the guard required for the
stored digits, and that tail bound is added to the returned ball.
"""

import math
import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import binomial
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


WORKING_GUARD = 128
TAIL_GUARD_DIGITS = 12

COMMON_PROBABILITIES = (
    QQ(1) / 2,
    QQ(1) / 3,
    QQ(1) / 4,
    QQ(1) / 5,
    QQ(1) / 10,
    QQ(11) / 100,
)

SMALL_PROBABILITIES = (
    QQ(1) / 2,
    QQ(1) / 3,
    QQ(1) / 4,
    QQ(1) / 10,
)

HYPERGEOMETRIC_SHAPES = (
    (10, 2, 2),
    (10, 2, 5),
    (10, 2, 8),
    (10, 5, 2),
    (10, 5, 5),
    (10, 5, 8),
    (20, 2, 2),
    (20, 2, 5),
    (20, 2, 10),
    (20, 5, 2),
    (20, 5, 5),
    (20, 5, 10),
    (20, 10, 2),
    (20, 10, 5),
    (20, 10, 10),
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


def _target(field, digits):
    return field(QQ(1) / QQ(10) ** (digits + TAIL_GUARD_DIGITS))


def _ordered_probabilities():
    grid = {
        QQ(a) / QQ(b)
        for b in range(2, 13)
        for a in range(1, b)
        if QQ(a) / QQ(b) <= QQ(1) / QQ(2)
    }
    grid.update(QQ(k) / QQ(100) for k in range(1, 51))
    seen = set()
    ordered = []
    for value in COMMON_PROBABILITIES:
        if value in grid and value not in seen:
            ordered.append(value)
            seen.add(value)
    for value in sorted(grid, key=lambda x: (x.denominator(), x.numerator())):
        if value not in seen:
            ordered.append(value)
            seen.add(value)
    return tuple(ordered)


def _ordered_common_probability_grid():
    grid = set(COMMON_PROBABILITIES)
    grid.update(QQ(k) / QQ(100) for k in range(1, 51))
    seen = set()
    ordered = []
    for value in COMMON_PROBABILITIES:
        if value not in seen:
            ordered.append(value)
            seen.add(value)
    for value in sorted(grid, key=lambda x: (x.denominator(), x.numerator())):
        if value not in seen:
            ordered.append(value)
            seen.add(value)
    return tuple(ordered)


def _half_integer_grid():
    return tuple(QQ(k) / QQ(2) for k in range(1, 21)) + tuple(QQ(k) for k in range(11, 21))


def _entropy_term(probability):
    if probability == 0:
        return probability
    return -probability * probability.log()


def _finite_entropy(probabilities, digits):
    field = _field(digits)
    total = field(0)
    for probability in probabilities:
        p = field(probability)
        if not p.contains_zero():
            total += _entropy_term(p)
    return total


def _finite_entropy_from_balls(probabilities, digits):
    field = _field(digits)
    total = field(0)
    for probability in probabilities:
        p = field(probability)
        if not p.contains_zero():
            total += _entropy_term(p)
    return total


def _bernoulli_entropy(shape, digits):
    p = _q(shape)
    return _finite_entropy((p, 1 - p), digits)


def _binomial_entropy(shape, digits):
    n_text, p_text = shape.split(",")
    n = int(n_text)
    p = _q(p_text)
    q = 1 - p
    probabilities = [
        QQ(binomial(n, k)) * p ** k * q ** (n - k)
        for k in range(n + 1)
    ]
    return _finite_entropy(probabilities, digits)


def _geometric_entropy(shape, digits):
    field = _field(digits)
    p = field(_q(shape))
    q = 1 - p
    return -p.log() - q * q.log() / p


def _negative_binomial_tail_bound(field, p_start, k_start, r, p, alpha):
    q = 1 - p
    one = field(1)
    a = field(alpha)
    denominator = one - a
    k = field(k_start)
    a_log = field(r) * (-field(p).log())
    b_log = -field(q).log()
    return p_start * (
        (a_log + k * b_log) / denominator
        + b_log * a / (denominator ** 2)
    )


def _negative_binomial_entropy(shape, digits):
    r_text, p_text = shape.split(",")
    r = int(r_text)
    p = _q(p_text)
    q = 1 - p
    field = _field(digits)
    target = _target(field, digits)
    alpha = (1 + q) / 2

    total = field(0)
    probability = field(p) ** r
    k = 0
    while True:
        total += _entropy_term(probability)
        next_probability = probability * field(q) * field(k + r) / field(k + 1)
        k_start = k + 1
        ratio_bound = q * QQ(k_start + r) / QQ(k_start + 1)
        if ratio_bound <= alpha:
            tail = _negative_binomial_tail_bound(
                field, next_probability, k_start, r, p, alpha)
            if tail.upper() < target.lower():
                return total.add_error(tail.upper())
        probability = next_probability
        k += 1


def _poisson_tail_bound(field, p_start, k_start, lam, alpha):
    one = field(1)
    a = field(alpha)
    denominator = one - a
    k = field(k_start)
    lam_ball = field(lam)
    abs_log_lam = lam_ball.log().abs()
    sum_one = one / denominator
    sum_j = a / (denominator ** 2)
    sum_j2 = a * (one + a) / (denominator ** 3)
    sum_k = k * sum_one + sum_j
    sum_k2 = (k ** 2) * sum_one + 2 * k * sum_j + sum_j2
    return p_start * (lam_ball * sum_one + abs_log_lam * sum_k + sum_k2)


def _poisson_entropy(shape, digits):
    lam = _q(shape)
    field = _field(digits)
    target = _target(field, digits)
    alpha = QQ(1) / QQ(2)

    total = field(0)
    probability = (-field(lam)).exp()
    k = 0
    while True:
        total += _entropy_term(probability)
        next_probability = probability * field(lam) / field(k + 1)
        k_start = k + 1
        if QQ(lam) / QQ(k_start + 1) <= alpha:
            tail = _poisson_tail_bound(
                field, next_probability, k_start, lam, alpha)
            if tail.upper() < target.lower():
                return total.add_error(tail.upper())
        probability = next_probability
        k += 1


def _uniform_entropy(shape, digits):
    field = _field(digits)
    return field(int(shape)).log()


def _hypergeometric_entropy(shape, digits):
    population_text, successes_text, draws_text = shape.split(",")
    population = int(population_text)
    successes = int(successes_text)
    draws = int(draws_text)
    denominator = QQ(binomial(population, draws))
    low = max(0, draws - (population - successes))
    high = min(draws, successes)
    probabilities = []
    for k in range(low, high + 1):
        probabilities.append(
            QQ(binomial(successes, k))
            * QQ(binomial(population - successes, draws - k))
            / denominator)
    return _finite_entropy(probabilities, digits)


def _logarithmic_tail_bound(field, p_power, n_plus_one, c, p):
    p_ball = field(p)
    one_minus_p = field(1 - p)
    a = field(10)
    b = -p_ball.log()
    geometric_tail = p_power / one_minus_p
    return c * (a * geometric_tail / field(n_plus_one)
                + (b + 1) * geometric_tail)


def _logarithmic_entropy(shape, digits):
    p = _q(shape)
    field = _field(digits)
    target = _target(field, digits)
    p_ball = field(p)
    c = -1 / (1 - p_ball).log()

    total = field(0)
    p_power = p_ball
    k = 1
    while True:
        probability = c * p_power / field(k)
        total += _entropy_term(probability)
        next_power = p_power * p_ball
        tail = _logarithmic_tail_bound(field, next_power, k + 1, c, p)
        if tail.upper() < target.lower():
            return total.add_error(tail.upper())
        p_power = next_power
        k += 1


def _zipf_entropy(shape, digits):
    s_text, n_text = shape.split(",")
    exponent = int(s_text)
    size = int(n_text)
    normalisation = sum(QQ(1) / QQ(k) ** exponent for k in range(1, size + 1))
    probabilities = [
        (QQ(1) / QQ(k) ** exponent) / normalisation
        for k in range(1, size + 1)
    ]
    return _finite_entropy(probabilities, digits)


def _benford_entropy(digits):
    field = _field(digits)
    log10 = field(10).log()
    probabilities = [
        (1 + field(QQ(1) / QQ(d))).log() / log10
        for d in range(1, 10)
    ]
    return _finite_entropy_from_balls(probabilities, digits)


def _entropy_nats(distribution, shape, digits):
    if distribution == "bernoulli":
        return _bernoulli_entropy(shape, digits)
    if distribution == "binomial":
        return _binomial_entropy(shape, digits)
    if distribution == "geometric":
        return _geometric_entropy(shape, digits)
    if distribution == "negative-binomial":
        return _negative_binomial_entropy(shape, digits)
    if distribution == "poisson":
        return _poisson_entropy(shape, digits)
    if distribution == "discrete-uniform":
        return _uniform_entropy(shape, digits)
    if distribution == "hypergeometric":
        return _hypergeometric_entropy(shape, digits)
    if distribution == "logarithmic":
        return _logarithmic_entropy(shape, digits)
    if distribution == "zipf":
        return _zipf_entropy(shape, digits)
    if distribution == "benford":
        return _benford_entropy(digits)
    raise ValueError("unknown distribution %r" % (distribution,))


def _to_unit(value, unit, digits):
    if unit == "nats":
        return value
    if unit != "bits":
        raise ValueError("unknown unit %r" % (unit,))
    field = _field(digits)
    return field(value) / field(2).log()


def _power_of_two(n):
    return n > 0 and (n & (n - 1)) == 0


def _skip_entry(distribution, shape, unit):
    if unit != "bits":
        return False
    if distribution == "bernoulli" and shape == "1/2":
        return True
    if distribution == "geometric" and shape == "1/2":
        return True
    if distribution == "discrete-uniform" and _power_of_two(int(shape)):
        return True
    if distribution == "binomial" and shape == "2,1/2":
        return True
    return False


def _comment(distribution, shape, unit):
    if unit != "nats":
        return ""
    if distribution == "bernoulli" and shape == "1/2":
        return "In bits this entropy is exactly $1$."
    if distribution == "geometric" and shape == "1/2":
        return "In bits this entropy is exactly $2$."
    if distribution == "discrete-uniform":
        n = int(shape)
        if _power_of_two(n):
            return "In bits this entropy is exactly $%d$." % (n.bit_length() - 1)
    if distribution == "binomial" and shape == "2,1/2":
        return "In bits this entropy is exactly $3/2$."
    return ""


def _format_probability(value):
    return str(value)


def _scipy_expected(params):
    import scipy.stats as stats

    distribution = params["distribution"]
    shape = params["shape"]
    unit = params["unit"]
    if distribution == "bernoulli":
        expected = stats.bernoulli(float(_q(shape))).entropy()
    elif distribution == "binomial":
        n_text, p_text = shape.split(",")
        expected = stats.binom(int(n_text), float(_q(p_text))).entropy()
    elif distribution == "geometric":
        expected = stats.geom(float(_q(shape))).entropy()
    elif distribution == "negative-binomial":
        r_text, p_text = shape.split(",")
        expected = stats.nbinom(int(r_text), float(_q(p_text))).entropy()
    elif distribution == "poisson":
        expected = stats.poisson(float(_q(shape))).entropy()
    elif distribution == "discrete-uniform":
        expected = math.log(int(shape))
    elif distribution == "hypergeometric":
        population_text, successes_text, draws_text = shape.split(",")
        expected = stats.hypergeom(
            int(population_text), int(successes_text), int(draws_text)).entropy()
    elif distribution == "logarithmic":
        expected = stats.logser(float(_q(shape))).entropy()
    elif distribution == "zipf":
        s_text, n_text = shape.split(",")
        if hasattr(stats, "zipfian"):
            expected = stats.zipfian(int(s_text), int(n_text)).entropy()
        else:
            weights = [k ** (-int(s_text)) for k in range(1, int(n_text) + 1)]
            total = sum(weights)
            expected = -sum((w / total) * math.log(w / total) for w in weights)
    elif distribution == "benford":
        probabilities = [math.log10(1 + 1 / d) for d in range(1, 10)]
        expected = -sum(p * math.log(p) for p in probabilities)
    else:
        raise ValueError("unknown distribution %r" % (distribution,))
    if unit == "bits":
        expected /= math.log(2)
    return expected


def _midpoint(value):
    if isinstance(value, dict):
        value = value["number"]
    return float((value.lower() + value.upper()) / 2)


class ShannonEntropies(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T339")
    parameters = ("distribution", "shape", "unit")
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self):
        for p in _ordered_probabilities():
            shape = _format_probability(p)
            for unit in ("nats", "bits"):
                if not _skip_entry("bernoulli", shape, unit):
                    yield {"distribution": "bernoulli", "shape": shape, "unit": unit}

        for n in range(2, 21):
            for p in SMALL_PROBABILITIES:
                shape = "%d,%s" % (n, p)
                for unit in ("nats", "bits"):
                    if not _skip_entry("binomial", shape, unit):
                        yield {"distribution": "binomial", "shape": shape, "unit": unit}

        for p in _ordered_common_probability_grid():
            shape = _format_probability(p)
            for unit in ("nats", "bits"):
                if not _skip_entry("geometric", shape, unit):
                    yield {"distribution": "geometric", "shape": shape, "unit": unit}

        for r in range(2, 11):
            for p in SMALL_PROBABILITIES:
                shape = "%d,%s" % (r, p)
                for unit in ("nats", "bits"):
                    yield {"distribution": "negative-binomial", "shape": shape, "unit": unit}

        for lam in _half_integer_grid():
            shape = _format_probability(lam)
            for unit in ("nats", "bits"):
                yield {"distribution": "poisson", "shape": shape, "unit": unit}

        for n in range(2, 31):
            shape = str(n)
            for unit in ("nats", "bits"):
                if not _skip_entry("discrete-uniform", shape, unit):
                    yield {"distribution": "discrete-uniform", "shape": shape, "unit": unit}

        for population, successes, draws in HYPERGEOMETRIC_SHAPES:
            shape = "%d,%d,%d" % (population, successes, draws)
            for unit in ("nats", "bits"):
                yield {"distribution": "hypergeometric", "shape": shape, "unit": unit}

        for p in _ordered_common_probability_grid():
            shape = _format_probability(p)
            for unit in ("nats", "bits"):
                yield {"distribution": "logarithmic", "shape": shape, "unit": unit}

        for exponent in (1, 2, 3):
            for size in (10, 100):
                shape = "%d,%d" % (exponent, size)
                for unit in ("nats", "bits"):
                    yield {"distribution": "zipf", "shape": shape, "unit": unit}

        for unit in ("nats", "bits"):
            yield {"distribution": "benford", "shape": "-", "unit": unit}

    def value(self, params, digits):
        distribution = str(params["distribution"])
        shape = str(params["shape"])
        unit = str(params["unit"])
        value = _to_unit(_entropy_nats(distribution, shape, digits), unit, digits)
        comment = _comment(distribution, shape, unit)
        if comment:
            return {"number": value, "comment": comment}
        return value


def run_integrity_checks():
    generator = ShannonEntropies()
    largest = (0.0, None, None, None)
    for params in generator.enumerate():
        value = generator.value(params, 50)
        got = _midpoint(value)
        expected = _scipy_expected(params)
        difference = abs(got - expected)
        if difference > largest[0]:
            largest = (difference, dict(params), got, expected)
        if difference > 5e-9:
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
    generator = ShannonEntropies()
    run_integrity_checks()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="Shannon entropy values of discrete distributions"))
    elif os.environ.get("NUMBERDB_API_KEY"):
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
    else:
        print("integrity checks passed; NUMBERDB_API_KEY is not set, so verify() was skipped")
