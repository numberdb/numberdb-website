"""Barker polynomials -- numberdb.org/T322 (table wanted: numberdb-data#160)

For a Barker sequence a_0, ..., a_(n-1) normalized by a_0 = a_1 = 1, this
stores

    B_a(x) = sum_(j=0)^(n-1) a_j x^j.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

On the NumberDB build machine, where arguments are not passed through
agents/sage.sh, publish with:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
          agents/sage.sh generate.py

The family convention from numberdb-data#160 is used here: the variable is x,
coefficients run low degree first, and the table is indexed by the sequence's
length and normalized sign word. The sign word uses + for 1 and - for -1.

The values are exact polynomials over ZZ. There is no precision to choose and
no rounding.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ


BARKER_SEQUENCES = (
    (2, "++"),
    (3, "++-"),
    (4, "+++-"),
    (4, "++-+"),
    (5, "+++-+"),
    (7, "+++--+-"),
    (11, "+++---+--+-"),
    (13, "+++++--++-+-+"),
)


RING = PolynomialRing(ZZ, "x")
X = RING.gen()


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def sign_value(sign):
    if sign == "+":
        return ZZ(1)
    if sign == "-":
        return -ZZ(1)
    raise ValueError("unknown Barker sign %r" % (sign,))


def barker_polynomial(signs):
    return sum(sign_value(sign) * X**j for j, sign in enumerate(signs))


def autocorrelation(signs, shift):
    values = [sign_value(sign) for sign in signs]
    return sum(values[j] * values[j + shift]
               for j in range(len(values) - shift))


def autocorrelation_polynomial(signs):
    n = len(signs)
    polynomial = barker_polynomial(signs)
    return polynomial * X**(n - 1) * polynomial(ZZ(1) / X)


def autocorrelation_polynomial_from_coefficients(signs):
    n = len(signs)
    return sum(autocorrelation(signs, abs(k)) * X**(n - 1 + k)
               for k in range(-(n - 1), n))


def is_barker_sequence(signs):
    return all(abs(autocorrelation(signs, shift)) <= 1
               for shift in range(1, len(signs)))


def normalized_words_of_length(n):
    """Brute-force the normalized Barker sign words of length n."""
    if n == 2:
        candidates = ("++",)
    else:
        candidates = (
            "++" + "".join("+" if (mask >> bit) & 1 else "-"
                           for bit in range(n - 2))
            for mask in range(ZZ(2) ** (n - 2))
        )
    return tuple(word for word in candidates if is_barker_sequence(word))


def merit_factor(signs):
    n = ZZ(len(signs))
    energy = sum(autocorrelation(signs, shift) ** 2
                 for shift in range(1, len(signs)))
    return QQ(n * n) / QQ(2 * energy)


def check_identities():
    source = tuple(BARKER_SEQUENCES)
    found = tuple((n, word)
                  for n in range(2, 14)
                  for word in normalized_words_of_length(n))
    if found != source:
        raise AssertionError("brute-force Barker search gave %r" % (found,))

    known_merit_factors = {
        (2, "++"): QQ(2),
        (3, "++-"): QQ(9) / QQ(2),
        (4, "+++-"): QQ(4),
        (4, "++-+"): QQ(4),
        (5, "+++-+"): QQ(25) / QQ(4),
        (7, "+++--+-"): QQ(49) / QQ(6),
        (11, "+++---+--+-"): QQ(121) / QQ(10),
        (13, "+++++--++-+-+"): QQ(169) / QQ(12),
    }

    for n, signs in BARKER_SEQUENCES:
        if len(signs) != n:
            raise AssertionError("length mismatch for %s" % (signs,))
        if not signs.startswith("++"):
            raise AssertionError("normalization failed for %s" % (signs,))
        if not is_barker_sequence(signs):
            raise AssertionError("Barker condition failed for %s" % (signs,))
        if autocorrelation(signs, 0) != n:
            raise AssertionError("c_0 failed for %s" % (signs,))
        if autocorrelation_polynomial(signs) \
                != autocorrelation_polynomial_from_coefficients(signs):
            raise AssertionError("autocorrelation polynomial failed for %s"
                                 % (signs,))
        if merit_factor(signs) != known_merit_factors[(n, signs)]:
            raise AssertionError("merit factor failed for %s" % (signs,))


class BarkerPolynomials(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T322")
    parameters = ("n", "sequence")
    type = "Z[]"
    rigour = "exact"

    def enumerate(self):
        for n, signs in BARKER_SEQUENCES:
            yield {"n": n, "sequence": signs}

    def value(self, params, digits):
        n = ZZ(params["n"])
        signs = str(params["sequence"])
        if len(signs) != n:
            raise ValueError("sequence %s does not have length %s" % (signs, n))
        return barker_polynomial(signs)


def main():
    _key_from_stdin()
    check_identities()
    generator = BarkerPolynomials()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="Barker polynomials for the eight known normalized sequences"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
