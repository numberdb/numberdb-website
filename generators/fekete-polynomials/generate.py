"""Fekete polynomials f_p(x) -- numberdb.org/T318 (table wanted: numberdb-data#160)

For an odd prime p,

    f_p(x) = sum_{a=0}^{p-1} (a | p) x^a,

where (a | p) is the Legendre symbol. Thus the constant term is 0, and the
remaining coefficients are +1 for the nonzero quadratic residues modulo p and
-1 for the nonresidues.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

On the NumberDB build machine, where arguments are not passed through
agents/sage.sh, publish with:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
          agents/sage.sh generate.py

The family convention from numberdb-data#160 is used here: the variable is x,
coefficients run low degree first, and the polynomial is indexed by p rather
than by the degree p - 1. The associated Legendre sequence of length p is a
different object: it has u_0 = 1, while this polynomial has constant term 0.

The values are exact polynomials over ZZ. There is no precision to choose and
no rounding; writing fewer coefficients would make a different polynomial.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import kronecker_symbol, prime_range
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


UP_TO = 101


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


def fekete_polynomial(p):
    """Return f_p(x) from Sage's Kronecker symbol, equal to Legendre for p."""
    return sum(ZZ(kronecker_symbol(a, p)) * X**a for a in range(p))


def residue_polynomial(p):
    """Return f_p(x) from the set of nonzero quadratic residues modulo p."""
    residues = {ZZ(a * a % p) for a in range(1, p)}
    return sum(_residue_coefficient(a, residues) * X**a for a in range(p))


def _residue_coefficient(a, residues):
    if a == 0:
        return ZZ(0)
    return ZZ(1) if ZZ(a) in residues else ZZ(-1)


def euler_symbol(a, p):
    """Legendre symbol from Euler's criterion, written without Sage's symbol."""
    if a % p == 0:
        return ZZ(0)
    residue = pow(int(a), int((p - 1) // 2), int(p))
    if residue == 1:
        return ZZ(1)
    if residue == p - 1:
        return ZZ(-1)
    raise ValueError("Euler criterion returned %s modulo %s" % (residue, p))


def check_identities(up_to=UP_TO):
    for p in prime_range(3, up_to + 1):
        value = fekete_polynomial(p)
        if value != residue_polynomial(p):
            raise AssertionError("residue-set check failed at p=%s" % (p,))
        for a in range(p):
            if kronecker_symbol(a, p) != euler_symbol(a, p):
                raise AssertionError("Euler criterion failed at p=%s, a=%s"
                                     % (p, a))
        if value(1) != 0:
            raise AssertionError("f_p(1) check failed at p=%s" % (p,))


class FeketePolynomials(numberdb.Generator):

    table = "T318"
    parameters = ("p",)
    type = "Z[]"
    rigour = "exact"

    def enumerate(self, up_to=UP_TO):
        for p in prime_range(3, up_to + 1):
            yield {"p": p}

    def value(self, params, digits):
        return fekete_polynomial(ZZ(params["p"]))


def main():
    _key_from_stdin()
    check_identities()
    generator = FeketePolynomials()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="Fekete polynomials for odd primes p <= %d" % (UP_TO,)))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
