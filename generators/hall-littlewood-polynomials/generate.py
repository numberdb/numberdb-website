"""Hall-Littlewood polynomials -- numberdb.org/T261.

    P_lambda(x_1, ..., x_n; t), in Macdonald's P normalisation

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

This table stores the complete rectangle 1 <= n <= 4 and |lambda| <= 4.
The largest entry in that rectangle is P_(4) in four variables, at 1080
characters. Extending the same rectangle to n = 5 makes P_(4) 2493
characters, and extending to |lambda| = 5 at n = 4 makes P_(5) 2114
characters.
"""

import os
import sys
from functools import lru_cache
from itertools import permutations

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


TABLE = os.environ.get("NUMBERDB_TABLE", "T261")
MOST_VARIABLES = 4
LARGEST_PARTITION = 4


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _prod(values):
    total = None
    for value in values:
        total = value if total is None else total * value
    return 1 if total is None else total


def _partitions(total, largest=None):
    """Partitions of total, largest part first."""
    if largest is None:
        largest = total
    if total == 0:
        yield []
        return
    for part in range(min(total, largest), 0, -1):
        for rest in _partitions(total - part, part):
            yield [part] + rest


def _format_partition(partition):
    return ",".join(str(part) for part in partition)


def _parse_partition(text):
    return tuple(int(part) for part in str(text).split(",") if part)


@lru_cache(maxsize=None)
def _ring(n):
    names = tuple("x%d" % (i + 1) for i in range(n)) + ("t",)
    return PolynomialRing(ZZ, names)


def _v_lambda(partition, n, t):
    """Macdonald's v_lambda(t), including zero parts after padding to n."""
    counts = {}
    padded = list(partition) + [0] * (n - len(partition))
    for part in padded:
        counts[part] = counts.get(part, 0) + 1

    value = 1
    for multiplicity in counts.values():
        for j in range(1, multiplicity + 1):
            value *= sum(t ** exponent for exponent in range(j))
    return value


@lru_cache(maxsize=None)
def _hall_littlewood(n, partition):
    """Compute P_lambda by Macdonald's symmetrization formula."""
    ring = _ring(n)
    xs = ring.gens()[:n]
    t = ring.gens()[n]
    frac = ring.fraction_field()
    lam = list(partition) + [0] * (n - len(partition))

    total = frac.zero()
    for order in permutations(range(n)):
        term = frac.one()
        for i, exponent in enumerate(lam):
            term *= frac(xs[order[i]]) ** exponent
        for i in range(n):
            for j in range(i + 1, n):
                term *= frac(xs[order[i]] - t * xs[order[j]])
                term /= frac(xs[order[i]] - xs[order[j]])
        total += term

    value = total / frac(_v_lambda(partition, n, t))
    if value.denominator() != 1:
        raise ArithmeticError(
            "Hall-Littlewood denominator did not cancel for n=%s, lambda=%s: %s"
            % (n, _format_partition(partition), value.denominator()))
    return ring(value.numerator())


class HallLittlewoodPolynomials(numberdb.Generator):

    table = TABLE
    parameters = ("n", "lambda")
    type = "Z[]"
    rigour = "exact"

    def enumerate(self, most_variables=MOST_VARIABLES,
                  largest=LARGEST_PARTITION):
        for n in range(1, most_variables + 1):
            for size in range(1, largest + 1):
                for partition in _partitions(size):
                    if len(partition) <= n:
                        yield {
                            "n": str(n),
                            "lambda": _format_partition(partition),
                        }

    def value(self, params, digits):
        n = int(params["n"])
        partition = _parse_partition(params["lambda"])
        return _hall_littlewood(n, partition)


def _values(generator=None):
    generator = generator or HallLittlewoodPolynomials()
    return {
        (int(params["n"]), _parse_partition(params["lambda"])):
        generator.value(params, digits=0)
        for params in generator.enumerate()
    }


def _schur_by_jacobi_trudi(n, partition):
    from itertools import combinations_with_replacement

    ring = _ring(n)
    xs = ring.gens()[:n]

    def homogeneous(degree):
        if degree < 0:
            return ring.zero()
        if degree == 0:
            return ring.one()
        return sum(_prod(combo) for combo in
                   combinations_with_replacement(xs, degree))

    size = len(partition)
    matrix = [
        [homogeneous(partition[i] - i + j) for j in range(size)]
        for i in range(size)
    ]
    return _determinant(matrix, ring)


def _monomial_symmetric(n, partition):
    ring = _ring(n)
    xs = ring.gens()[:n]
    exponents = list(partition) + [0] * (n - len(partition))
    return sum(
        _prod(x ** exponent for x, exponent in zip(xs, arrangement))
        for arrangement in sorted(set(permutations(exponents)))
    )


def _determinant(rows, ring):
    size = len(rows)
    total = ring.zero()
    for order in permutations(range(size)):
        sign = 1
        for i in range(size):
            for j in range(i + 1, size):
                if order[i] > order[j]:
                    sign = -sign
        term = ring.one()
        for i, j in enumerate(order):
            term *= rows[i][j]
        total += sign * term
    return total


def _specialize_t(polynomial, value):
    ring = polynomial.parent()
    images = list(ring.gens())
    images[-1] = ZZ(value)
    return polynomial(*images)


def _integer_polynomial_from_univariate(poly, target):
    t = target.gens()[-1]
    if not hasattr(poly, "dict"):
        poly = poly.parent()(poly)
    out = target.zero()
    for exponent, coefficient in poly.dict().items():
        power = exponent[0] if isinstance(exponent, tuple) else exponent
        if coefficient.denominator() != 1:
            raise ArithmeticError("nonintegral Hall-Littlewood coefficient")
        out += ZZ(coefficient) * (t ** power)
    return out


def _from_sage_expansion(expanded, target):
    xs = target.gens()[:-1]
    out = target.zero()
    for exponents, coefficient in expanded.dict().items():
        if coefficient.denominator() != 1:
            raise ArithmeticError("Sage returned a rational function coefficient")
        coeff = _integer_polynomial_from_univariate(
            coefficient.numerator(), target)
        out += coeff * _prod(x ** exponent
                             for x, exponent in zip(xs, exponents))
    return out


def _sage_hall_littlewood(n, partition):
    import sage.rings.polynomial.laurent_polynomial_ring  # noqa: F401
    from sage.combinat.sf.sf import SymmetricFunctions
    from sage.rings.rational_field import QQ

    base = PolynomialRing(QQ, "t")
    basis = SymmetricFunctions(base.fraction_field()).hall_littlewood().P()
    names = ["x%d" % (i + 1) for i in range(n)]
    expanded = basis[list(partition)].expand(n, alphabet=names)
    return _from_sage_expansion(expanded, _ring(n))


def _kostka_foulkes(lam, mu, target):
    from sage.combinat.sf.kfpoly import KostkaFoulkesPolynomial

    source = KostkaFoulkesPolynomial(list(lam), list(mu))
    if not hasattr(source, "dict"):
        return target(source)
    t = target.gens()[-1]
    out = target.zero()
    for exponent, coefficient in source.dict().items():
        power = exponent[0] if isinstance(exponent, tuple) else exponent
        out += ZZ(coefficient) * (t ** power)
    return out


def identity_complaints():
    """Return identity-check complaints for the stored range."""
    values = _values()
    complaints = []
    by_size = {}
    for key, value in values.items():
        n, partition = key
        by_size.setdefault((n, sum(partition)), {})[partition] = value

        sage_value = _sage_hall_littlewood(n, partition)
        if value != sage_value:
            complaints.append(
                "Sage disagrees at n=%s, lambda=%s" %
                (n, _format_partition(partition)))

        if _specialize_t(value, 0) != _schur_by_jacobi_trudi(n, partition):
            complaints.append(
                "Schur specialization fails at n=%s, lambda=%s" %
                (n, _format_partition(partition)))

        if _specialize_t(value, 1) != _monomial_symmetric(n, partition):
            complaints.append(
                "monomial specialization fails at n=%s, lambda=%s" %
                (n, _format_partition(partition)))

    for (n, _size), p_values in by_size.items():
        for lam in p_values:
            ring = _ring(n)
            reconstructed = ring.zero()
            for mu, p_mu in p_values.items():
                reconstructed += _kostka_foulkes(lam, mu, ring) * p_mu
            if reconstructed != _schur_by_jacobi_trudi(n, lam):
                complaints.append(
                    "Kostka-Foulkes transition fails at n=%s, lambda=%s" %
                    (n, _format_partition(lam)))
    return complaints


if __name__ == "__main__":
    _key_from_stdin()
    generator = HallLittlewoodPolynomials()

    if "--check-identities" in sys.argv:
        failures = identity_complaints()
        for failure in failures:
            print(failure)
        if not failures:
            print("all Hall-Littlewood identities checked")
        sys.exit(1 if failures else 0)

    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(generator.publish(
            message="Hall-Littlewood polynomials by Macdonald symmetrization"))
    else:
        report = generator.verify()
        print(report)
        if not report.ok:
            sys.exit(1)
