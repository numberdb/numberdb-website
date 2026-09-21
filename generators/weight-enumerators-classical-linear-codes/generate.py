"""Weight enumerators of the classical linear codes -- numberdb.org/T388.

This generator fills the table of dehomogenised Hamming weight enumerators

    W_C(x) = sum_i A_i x^i,

where A_i counts codewords of Hamming weight i. The entry keys are
`family,a,b`; the meaning of a and b is family-specific and is documented in
the table.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import itertools
import os
import sys
from functools import lru_cache

import numberdb.sage as numberdb
from sage.arith.misc import binomial
from sage.rings.finite_rings.finite_field_constructor import GF
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


TABLE = os.environ.get("NUMBERDB_TABLE", "T388")

R = PolynomialRing(ZZ, "x")
x = R.gen()
RQ = PolynomialRing(QQ, "x")
xq = RQ.gen()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _int_power(base, exponent):
    return int(ZZ(base) ** ZZ(exponent))


def _dimension_rm(r, m):
    return sum(int(binomial(m, i)) for i in range(r + 1))


def _poly_from_counts(counts):
    total = R.zero()
    for weight, count in enumerate(counts):
        if count:
            total += ZZ(count) * x ** weight
    return R(total)


def _counts_from_poly(poly, n):
    poly = R(poly)
    return [int(poly[i]) for i in range(n + 1)]


def _integer_polynomial(poly):
    poly = RQ(poly)
    coeffs = []
    for coefficient in poly.list():
        if coefficient.denominator() != 1:
            raise ArithmeticError("nonintegral coefficient %s in %s" %
                                  (coefficient, poly))
        coeffs.append(ZZ(coefficient))
    return R(coeffs)


def _macwilliams_from_counts(counts, q):
    """Weight enumerator of the dual code from the original distribution."""
    n = len(counts) - 1
    size = sum(counts)
    total = RQ.zero()
    for weight, count in enumerate(counts):
        if not count:
            continue
        total += (
            QQ(count)
            * (1 + QQ(q - 1) * xq) ** (n - weight)
            * (1 - xq) ** weight
        )
    return _integer_polynomial(total / QQ(size))


def _simplex_counts(q, m):
    n = (q ** m - 1) // (q - 1)
    counts = [0] * (n + 1)
    counts[0] = 1
    counts[q ** (m - 1)] = q ** m - 1
    return counts


def _simplex_poly(q, m):
    return _poly_from_counts(_simplex_counts(q, m))


def _hamming_poly(q, m):
    return _macwilliams_from_counts(_simplex_counts(q, m), q)


def _bit_positions(m):
    return list(range(1 << m))


def _monomial_masks(r, m):
    masks = []
    positions = _bit_positions(m)
    for degree in range(r + 1):
        for subset in itertools.combinations(range(m), degree):
            mask = 0
            for column, point in enumerate(positions):
                value = 1
                for bit in subset:
                    value &= (point >> bit) & 1
                if value:
                    mask |= 1 << column
            masks.append(mask)
    return masks


def _binary_span_counts(rows, n):
    counts = [0] * (n + 1)
    word = 0
    previous = 0
    for index in range(1 << len(rows)):
        gray = index ^ (index >> 1)
        if index:
            changed = gray ^ previous
            word ^= rows[changed.bit_length() - 1]
        counts[word.bit_count()] += 1
        previous = gray
    return counts


@lru_cache(maxsize=None)
def _reed_muller_poly(r, m):
    n = 1 << m
    if r < 0:
        return R.one()
    if r >= m:
        return R((1 + x) ** n)
    dual_r = m - r - 1
    if r > dual_r:
        dual_counts = _counts_from_poly(_reed_muller_poly(dual_r, m), n)
        return _macwilliams_from_counts(dual_counts, 2)
    return _poly_from_counts(_binary_span_counts(_monomial_masks(r, m), n))


GOLAY_COUNTS = {
    (2, 23): {
        0: 1, 7: 253, 8: 506, 11: 1288, 12: 1288, 15: 506, 16: 253, 23: 1,
    },
    (2, 24): {
        0: 1, 8: 759, 12: 2576, 16: 759, 24: 1,
    },
    (3, 11): {
        0: 1, 5: 132, 6: 132, 8: 330, 9: 110, 11: 24,
    },
    (3, 12): {
        0: 1, 6: 264, 9: 440, 12: 24,
    },
}


def _golay_poly(q, n):
    counts = [0] * (n + 1)
    for weight, count in GOLAY_COUNTS[(q, n)].items():
        counts[weight] = count
    return _poly_from_counts(counts)


def _multiplicative_order(q, n):
    value = q % n
    order = 1
    while value != 1:
        value = (value * q) % n
        order += 1
    return order


def _base_polynomial_ring(q):
    field = GF(q)
    return PolynomialRing(field, "z")


def _minimal_polynomial_in_base(beta_power, ring):
    return ring(beta_power.minpoly().list())


def _lcm_polynomials(polynomials, ring):
    value = ring.one()
    for polynomial in polynomials:
        value = value.lcm(ring(polynomial))
    return value.monic()


@lru_cache(maxsize=None)
def _root_data(q, n):
    extension_degree = _multiplicative_order(q, n)
    extension = GF(q ** extension_degree, "a")
    alpha = extension.gen()
    beta = alpha ** ((q ** extension_degree - 1) // n)
    if beta.multiplicative_order() != n:
        raise ArithmeticError("failed to choose an nth root for q=%d n=%d" %
                              (q, n))
    return beta, _base_polynomial_ring(q)


def _generator_from_roots(q, n, exponents):
    beta, ring = _root_data(q, n)
    return _lcm_polynomials(
        [_minimal_polynomial_in_base(beta ** exponent, ring)
         for exponent in sorted(set(exponents))],
        ring,
    )


def _quadratic_residue_generator(q, n):
    residues = sorted({(i * i) % n for i in range(1, n)})
    return _generator_from_roots(q, n, tuple(residues))


def _bch_generator(n, delta):
    return _generator_from_roots(2, n, tuple(range(1, delta)))


def _cyclic_code_counts(q, n, generator):
    degree = generator.degree()
    k = n - degree
    if q ** k > 70000:
        raise ArithmeticError("refusing to enumerate %d^%d codewords" % (q, k))

    rows = []
    coefficients = [int(c) for c in generator.list()]
    for shift in range(k):
        row = [0] * n
        for offset, coefficient in enumerate(coefficients):
            row[shift + offset] = coefficient
        rows.append(row)

    if q == 2:
        bit_rows = []
        for row in rows:
            mask = 0
            for index, coefficient in enumerate(row):
                if coefficient:
                    mask |= 1 << index
            bit_rows.append(mask)
        return _binary_span_counts(bit_rows, n)

    counts = [0] * (n + 1)
    for message in itertools.product(range(q), repeat=k):
        word = [0] * n
        for scalar, row in zip(message, rows):
            if scalar == 0:
                continue
            for index, coefficient in enumerate(row):
                word[index] = (word[index] + scalar * coefficient) % q
        counts[sum(1 for coefficient in word if coefficient)] += 1
    return counts


@lru_cache(maxsize=None)
def _quadratic_residue_poly(q, n):
    return _poly_from_counts(
        _cyclic_code_counts(q, n, _quadratic_residue_generator(q, n)))


@lru_cache(maxsize=None)
def _bch_poly(n, delta):
    return _poly_from_counts(_cyclic_code_counts(2, n, _bch_generator(n, delta)))


def _min_distance(poly):
    poly = R(poly)
    for weight in range(1, poly.degree() + 1):
        if poly[weight]:
            return weight
    return 0


def _sum_coefficients(poly):
    return int(R(poly)(1))


def _dimension_from_size(size, q):
    k = 0
    value = 1
    while value < size:
        value *= q
        k += 1
    if value != size:
        raise ArithmeticError("size %d is not a power of %d" % (size, q))
    return k


def _comment(label, q, n, k, d, extra=None):
    sentence = "%s code with parameters $[%d,%d,%d]_%d$." % (
        label, n, k, d, q)
    if extra:
        sentence += " " + extra
    return sentence


def _spec(family, a, b, q, n, label, poly_func, extra_comment=None):
    poly = poly_func()
    size = _sum_coefficients(poly)
    k = _dimension_from_size(size, q)
    d = _min_distance(poly)
    return {
        "family": family,
        "a": int(a),
        "b": int(b),
        "q": int(q),
        "n": int(n),
        "k": int(k),
        "d": int(d),
        "label": label,
        "extra_comment": extra_comment,
    }


def _all_specs():
    specs = []
    hamming_ranges = {2: 6, 3: 4, 4: 3}
    for q, max_m in hamming_ranges.items():
        for m in range(2, max_m + 1):
            n = (q ** m - 1) // (q - 1)
            specs.append(_spec(
                "simplex", q, m, q, n, "$q$-ary simplex",
                lambda q=q, m=m: _simplex_poly(q, m)))
            specs.append(_spec(
                "hamming", q, m, q, n, "$q$-ary Hamming",
                lambda q=q, m=m: _hamming_poly(q, m),
                "It is the dual of the simplex row with the same $q$ and $m$."))

    for q, n in ((3, 11), (3, 12), (2, 23), (2, 24)):
        extra = None
        if (q, n) in ((2, 23), (3, 11)):
            extra = "This is the perfect Golay code."
        else:
            extra = "This is the extended Golay code."
        specs.append(_spec(
            "golay", q, n, q, n, "Golay",
            lambda q=q, n=n: _golay_poly(q, n), extra))

    for m in range(2, 6):
        for r in range(0, m + 1):
            n = 1 << m
            specs.append(_spec(
                "rm", r, m, 2, n, "binary Reed-Muller",
                lambda r=r, m=m: _reed_muller_poly(r, m)))

    for q, n in ((2, 7), (3, 11), (3, 13), (2, 17), (2, 23), (2, 31)):
        specs.append(_spec(
            "qr", q, n, q, n, "quadratic-residue",
            lambda q=q, n=n: _quadratic_residue_poly(q, n)))

    for n, delta in ((15, 3), (15, 5), (15, 7), (31, 7), (31, 11)):
        specs.append(_spec(
            "bch", n, delta, 2, n, "binary primitive narrow-sense BCH",
            lambda n=n, delta=delta: _bch_poly(n, delta),
            "The designed distance is $\\delta=%d$." % delta))

    return sorted(specs, key=lambda spec: (
        spec["n"], spec["k"], spec["family"], spec["a"], spec["b"]))


@lru_cache(maxsize=None)
def _specs_by_key():
    specs = {}
    for spec in _all_specs():
        key = (spec["family"], spec["a"], spec["b"])
        if key in specs:
            raise ArithmeticError("duplicate key %r" % (key,))
        specs[key] = spec
    return specs


def _value_for(family, a, b):
    family, a, b = str(family), int(a), int(b)
    if family == "simplex":
        return _simplex_poly(a, b)
    if family == "hamming":
        return _hamming_poly(a, b)
    if family == "golay":
        return _golay_poly(a, b)
    if family == "rm":
        return _reed_muller_poly(a, b)
    if family == "qr":
        return _quadratic_residue_poly(a, b)
    if family == "bch":
        return _bch_poly(a, b)
    raise KeyError((family, a, b))


def _record_for(params):
    family = params["family"]
    a = int(params["a"])
    b = int(params["b"])
    spec = _specs_by_key()[(family, a, b)]
    polynomial = _value_for(family, a, b)
    comment = _comment(
        spec["label"], spec["q"], spec["n"], spec["k"], spec["d"],
        spec["extra_comment"])
    return {"number": polynomial, "comment": comment}


class ClassicalCodeWeightEnumerators(numberdb.Generator):
    """Generator for T388, weight enumerators of classical linear codes."""

    table = TABLE
    parameters = ("family", "a", "b")
    type = "Z[]"
    rigour = "exact"

    def enumerate(self):
        for spec in _all_specs():
            yield {
                "family": spec["family"],
                "a": str(spec["a"]),
                "b": str(spec["b"]),
            }

    def value(self, params, digits):
        return _record_for(params)


def _check_basic_invariants():
    for spec in _all_specs():
        poly = _value_for(spec["family"], spec["a"], spec["b"])
        if poly[0] != 1:
            raise ArithmeticError("constant term failed for %r" % (spec,))
        if poly.degree() > spec["n"]:
            raise ArithmeticError("degree failed for %r" % (spec,))
        if _sum_coefficients(poly) != spec["q"] ** spec["k"]:
            raise ArithmeticError("size failed for %r" % (spec,))
        if _min_distance(poly) != spec["d"]:
            raise ArithmeticError("minimum distance failed for %r" % (spec,))


def _check_hamming_simplex_duality():
    for q in (2, 3, 4):
        for m in range(2, 7):
            if q == 4 and m > 4:
                continue
            simplex_counts = _counts_from_poly(_simplex_poly(q, m),
                                               (q ** m - 1) // (q - 1))
            if _macwilliams_from_counts(simplex_counts, q) != _hamming_poly(q, m):
                raise ArithmeticError("Hamming duality failed at q=%d m=%d" %
                                      (q, m))


def _check_reed_muller_duality():
    for m in range(2, 6):
        n = 1 << m
        for r in range(0, m):
            left = _reed_muller_poly(r, m)
            dual = _reed_muller_poly(m - r - 1, m)
            dual_counts = _counts_from_poly(dual, n)
            if _macwilliams_from_counts(dual_counts, 2) != left:
                raise ArithmeticError("RM duality failed at r=%d m=%d" % (r, m))


def _check_golay_against_qr():
    if _golay_poly(2, 23) != _quadratic_residue_poly(2, 23):
        raise ArithmeticError("binary Golay did not match QR(2,23)")
    if _golay_poly(3, 11) != _quadratic_residue_poly(3, 11):
        raise ArithmeticError("ternary Golay did not match QR(3,11)")


def _check_cyclic_roots():
    for q, n in ((2, 7), (3, 11), (3, 13), (2, 17), (2, 23), (2, 31)):
        beta, _ring = _root_data(q, n)
        generator = _quadratic_residue_generator(q, n)
        residues = sorted({(i * i) % n for i in range(1, n)})
        for exponent in residues:
            if generator(beta ** exponent) != 0:
                raise ArithmeticError("QR root check failed q=%d n=%d i=%d" %
                                      (q, n, exponent))

    for n, delta in ((15, 3), (15, 5), (15, 7), (31, 7), (31, 11)):
        beta, _ring = _root_data(2, n)
        generator = _bch_generator(n, delta)
        for exponent in range(1, delta):
            if generator(beta ** exponent) != 0:
                raise ArithmeticError("BCH root check failed n=%d delta=%d i=%d" %
                                      (n, delta, exponent))
        if _min_distance(_bch_poly(n, delta)) < delta:
            raise ArithmeticError("BCH bound failed n=%d delta=%d" % (n, delta))


def run_integrity_checks():
    _check_basic_invariants()
    _check_hamming_simplex_duality()
    _check_reed_muller_duality()
    _check_golay_against_qr()
    _check_cyclic_roots()


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
    generator = ClassicalCodeWeightEnumerators()
    run_integrity_checks()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message="exact classical linear-code weight enumerators"))
    elif os.environ.get("NUMBERDB_API_KEY"):
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
    else:
        print("identity checks passed; NUMBERDB_API_KEY is not set, so verify() was skipped")
