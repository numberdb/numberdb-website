"""Hall polynomials -- numberdb.org/T263.

    g^lambda_{mu,nu}(q)

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The table stores the nonzero non-edge Hall polynomials with |lambda| <= 8 and
both lower partitions nonempty. The edge cases with one lower partition empty
are the identity constants stated in the table formulas.
"""

import itertools
import os
import sys
from functools import lru_cache

import numberdb.sage as numberdb

# Sage's Hall-Littlewood multiplication reaches this module lazily in a way
# that fails under named imports unless it is initialised first.
import sage.rings.polynomial.laurent_polynomial_ring  # noqa: F401,E402

from sage.combinat.sf.sf import SymmetricFunctions  # noqa: E402
from sage.rings.integer_ring import ZZ  # noqa: E402
from sage.rings.rational_field import QQ  # noqa: E402
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing  # noqa: E402


TABLE = os.environ.get("NUMBERDB_TABLE", "T263")

# Measured before filling the draft: up to size 8, with both lower partitions
# nonempty, gives 1197 entries. The longest value is 128 characters and the
# entries block is about 80 KB. Size 9 would give 2527 entries, past the soft
# entry limit of 1200.
MAX_SIZE = 8
DIRECT_CHECK_SIZE = 4

T_RING = PolynomialRing(QQ, "t")
P_BASIS = SymmetricFunctions(T_RING.fraction_field()).hall_littlewood().P()
POLY = PolynomialRing(ZZ, "q")
Q = POLY.gen()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _partitions(total, largest=None):
    """Partitions of total, largest part first."""
    if largest is None:
        largest = total
    if total == 0:
        yield ()
        return
    for part in range(min(total, largest), 0, -1):
        for rest in _partitions(total - part, part):
            yield (part,) + rest


def _format_partition(partition):
    return ",".join(str(part) for part in partition)


def _parse_partition(text):
    return tuple(int(part) for part in str(text).split(",") if part)


def _n_stat(partition):
    return sum(index * part for index, part in enumerate(partition))


def _coerce_t_polynomial(value):
    if not hasattr(value, "dict"):
        return T_RING(value)
    try:
        return T_RING(value)
    except TypeError:
        numerator = value.numerator()
        denominator = value.denominator()
        if denominator != 1:
            raise ArithmeticError("non-polynomial Hall-Littlewood coefficient %s" %
                                  (value,))
        return T_RING(numerator)


def _hall_from_structure_constant(lam, mu, nu, coefficient):
    coefficient = _coerce_t_polynomial(coefficient)
    shift = _n_stat(lam) - _n_stat(mu) - _n_stat(nu)
    out = POLY.zero()
    for exponent, c in coefficient.dict().items():
        power = exponent[0] if isinstance(exponent, tuple) else exponent
        q_power = shift - power
        if q_power < 0:
            raise ArithmeticError(
                "%s,%s,%s gives negative q exponent in %s" %
                (lam, mu, nu, coefficient))
        if c.denominator() != 1:
            raise ArithmeticError(
                "%s,%s,%s gives nonintegral coefficient in %s" %
                (lam, mu, nu, coefficient))
        out += ZZ(c) * (Q ** q_power)
    return out


@lru_cache(maxsize=None)
def _hall_product(mu, nu):
    """Nonzero Hall polynomials in P_mu P_nu, keyed by lambda."""
    product = P_BASIS(list(mu)) * P_BASIS(list(nu))
    values = {}
    for lam in product.support():
        lam = tuple(int(part) for part in lam)
        value = _hall_from_structure_constant(
            lam, mu, nu, product.coefficient(list(lam)))
        if value != 0:
            values[lam] = value
    return values


def _hall_polynomial(lam, mu, nu):
    if sum(lam) != sum(mu) + sum(nu):
        return POLY.zero()
    return _hall_product(tuple(mu), tuple(nu)).get(tuple(lam), POLY.zero())


class HallPolynomials(numberdb.Generator):

    table = TABLE
    parameters = ("lambda", "mu", "nu")
    type = "Z[]"
    rigour = "exact"

    def enumerate(self, max_size=MAX_SIZE):
        for total in range(2, max_size + 1):
            for mu_size in range(1, total):
                nu_size = total - mu_size
                for mu in _partitions(mu_size):
                    for nu in _partitions(nu_size):
                        for lam in sorted(_hall_product(mu, nu), reverse=True):
                            yield {
                                "lambda": _format_partition(lam),
                                "mu": _format_partition(mu),
                                "nu": _format_partition(nu),
                            }

    def value(self, params, digits):
        lam = _parse_partition(params["lambda"])
        mu = _parse_partition(params["mu"])
        nu = _parse_partition(params["nu"])
        return _hall_polynomial(lam, mu, nu)


def _group_moduli(partition, p):
    return tuple(p ** part for part in partition)


def _zero(moduli):
    return tuple(0 for _ in moduli)


def _add(moduli, left, right):
    return tuple((a + b) % modulus
                 for a, b, modulus in zip(left, right, moduli))


def _scale(moduli, scalar, element):
    return tuple((scalar * value) % modulus
                 for value, modulus in zip(element, moduli))


@lru_cache(maxsize=None)
def _group_elements(lam, p):
    moduli = _group_moduli(lam, p)
    return tuple(itertools.product(*(range(modulus) for modulus in moduli)))


def _cyclic_span(moduli, element):
    seen = []
    current = _zero(moduli)
    while current not in seen:
        seen.append(current)
        current = _add(moduli, current, element)
    return tuple(seen)


def _subgroup_with(moduli, subgroup, element):
    span = _cyclic_span(moduli, element)
    return frozenset(_add(moduli, h, s) for h in subgroup for s in span)


@lru_cache(maxsize=None)
def _subgroups(lam, p):
    moduli = _group_moduli(lam, p)
    elements = _group_elements(lam, p)
    trivial = frozenset([_zero(moduli)])
    seen = {trivial}
    queue = [trivial]
    for subgroup in queue:
        for element in elements:
            if element in subgroup:
                continue
            generated = _subgroup_with(moduli, subgroup, element)
            if generated not in seen:
                seen.add(generated)
                queue.append(generated)
    return tuple(seen)


def _log_power(value, p):
    power = 0
    while value > 1:
        if value % p:
            raise ArithmeticError("%d is not a power of %d" % (value, p))
        value //= p
        power += 1
    return power


def _partition_from_image_sizes(sizes, p):
    conjugate = []
    for before, after in zip(sizes, sizes[1:]):
        if before % after:
            raise ArithmeticError("image sizes are not nested: %s" % (sizes,))
        conjugate.append(_log_power(before // after, p))

    parts = []
    for index, height in enumerate(conjugate):
        next_height = conjugate[index + 1] if index + 1 < len(conjugate) else 0
        parts.extend([index + 1] * (height - next_height))
    return tuple(reversed(parts))


def _subgroup_type(lam, p, subgroup):
    moduli = _group_moduli(lam, p)
    sizes = []
    power = 1
    while True:
        image = frozenset(_scale(moduli, power, element) for element in subgroup)
        sizes.append(len(image))
        if len(image) == 1:
            break
        power *= p
    return _partition_from_image_sizes(sizes, p)


def _sum_sets(moduli, left, right):
    return frozenset(_add(moduli, a, b) for a in left for b in right)


def _quotient_type(lam, p, subgroup):
    moduli = _group_moduli(lam, p)
    group = _group_elements(lam, p)
    sizes = []
    power = 1
    while True:
        image = frozenset(_scale(moduli, power, element) for element in group)
        image_plus_subgroup = _sum_sets(moduli, image, subgroup)
        sizes.append(len(image_plus_subgroup) // len(subgroup))
        if sizes[-1] == 1:
            break
        power *= p
    return _partition_from_image_sizes(sizes, p)


@lru_cache(maxsize=None)
def _direct_count(lam, mu, nu, p):
    total = ZZ(0)
    for subgroup in _subgroups(lam, p):
        if _subgroup_type(lam, p, subgroup) != nu:
            continue
        if _quotient_type(lam, p, subgroup) != mu:
            continue
        total += 1
    return total


def run_integrity_checks():
    generator = HallPolynomials()
    rows = list(generator.enumerate())
    if len(rows) != 1197:
        raise AssertionError("expected 1197 rows, got %d" % (len(rows),))

    checked_direct = 0
    for params in rows:
        lam = _parse_partition(params["lambda"])
        mu = _parse_partition(params["mu"])
        nu = _parse_partition(params["nu"])
        value = _hall_polynomial(lam, mu, nu)

        if value != _hall_polynomial(lam, nu, mu):
            raise AssertionError("%s,%s,%s violates symmetry" %
                                 (lam, mu, nu))

        if sum(lam) <= DIRECT_CHECK_SIZE:
            for p in (2, 3):
                if value(q=ZZ(p)) != _direct_count(lam, mu, nu, p):
                    raise AssertionError(
                        "%s,%s,%s at p=%d disagrees with direct count" %
                        (lam, mu, nu, p))
                checked_direct += 1

    for size in range(1, MAX_SIZE + 1):
        for lam in _partitions(size):
            if _hall_polynomial(lam, lam, ()) != 1:
                raise AssertionError("%s: quotient edge is not 1" % (lam,))
            if _hall_polynomial(lam, (), lam) != 1:
                raise AssertionError("%s: submodule edge is not 1" % (lam,))

    print("integrity checks passed for %d rows and %d direct counts" %
          (len(rows), checked_direct))


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
    generator = HallPolynomials()
    run_integrity_checks()

    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="exact Hall polynomials from Hall-Littlewood products"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
