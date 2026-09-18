"""Merit factors of the Legendre sequences -- numberdb.org/T321 (table wanted: numberdb-data#160)

For an odd prime p, the Legendre sequence u^(p) has length p, with u_0 = 1
and u_j = (j | p) for 1 <= j < p. Its aperiodic autocorrelations are

    c_k = sum_{j=0}^{p-1-k} u_j u_{j+k},

with c_0 = p. This table stores the exact aperiodic merit factor

    F_p = p^2 / (2 sum_{k=1}^{p-1} c_k^2).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

On the NumberDB build machine, where arguments are not passed through
agents/sage.sh, publish with:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
          agents/sage.sh generate.py

The family convention from numberdb-data#160 is used here: coefficient and
sequence indices run low degree first, the Legendre sequence has u_0 = 1, and
the merit factor is aperiodic. The periodic merit factor and the merit factors
of cyclically rotated Legendre sequences are different quantities.

The values are exact rational numbers. There is no precision to choose and no
rounding.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import kronecker_symbol, prime_range
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ


UP_TO = 997

KNOWN_VALUES = {
    3: QQ(9) / QQ(2),
    5: QQ(5) / QQ(4),
    7: QQ(7) / QQ(2),
    11: QQ(11) / QQ(6),
    13: QQ(169) / QQ(124),
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def legendre_sequence(p):
    """The length-p Legendre sequence, with u_0 = 1."""
    p = ZZ(p)
    return [ZZ(1)] + [ZZ(kronecker_symbol(j, p)) for j in range(1, p)]


def autocorrelations(sequence):
    """The positive-shift aperiodic autocorrelations of sequence."""
    n = len(sequence)
    out = []
    for k in range(1, n):
        out.append(sum(sequence[j] * sequence[j + k]
                       for j in range(n - k)))
    return out


def merit_factor_from_sequence(sequence):
    n = ZZ(len(sequence))
    energy = sum(c * c for c in autocorrelations(sequence))
    return QQ(n * n) / QQ(2 * energy)


def legendre_merit_factor(p):
    return merit_factor_from_sequence(legendre_sequence(p))


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


def euler_legendre_sequence(p):
    """The same sequence, built without Sage's kronecker_symbol."""
    return [ZZ(1)] + [euler_symbol(j, p) for j in range(1, p)]


def l4_denominator_from_pairs(sequence):
    """Return ||U||_4^4 - n^2 from all ordered coefficient pairs.

    This computes the coefficients of U(x)U(1/x) by pair differences instead
    of by the positive-shift autocorrelation loop used by the generator.
    """
    n = len(sequence)
    offset = n - 1
    coefficients = [ZZ(0) for _ in range(2 * n - 1)]
    for i, left in enumerate(sequence):
        for j, right in enumerate(sequence):
            coefficients[i - j + offset] += left * right
    l4_fourth = sum(c * c for c in coefficients)
    return l4_fourth - ZZ(n * n)


def check_identities(up_to=UP_TO):
    for p in prime_range(3, up_to + 1):
        value = legendre_merit_factor(p)
        if p in KNOWN_VALUES and value != KNOWN_VALUES[p]:
            raise AssertionError("known value failed at p=%s" % (p,))

        euler_value = merit_factor_from_sequence(euler_legendre_sequence(p))
        if value != euler_value:
            raise AssertionError("Euler criterion check failed at p=%s" % (p,))

        sequence = legendre_sequence(p)
        denominator = QQ(p * p) / value
        if denominator != l4_denominator_from_pairs(sequence):
            raise AssertionError("L4 identity failed at p=%s" % (p,))


class LegendreSequenceMeritFactors(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T321")
    parameters = ("p",)
    type = "Q"
    rigour = "exact"

    def enumerate(self, up_to=UP_TO):
        for p in prime_range(3, up_to + 1):
            yield {"p": p}

    def value(self, params, digits):
        return legendre_merit_factor(ZZ(params["p"]))


def main():
    _key_from_stdin()
    check_identities()
    generator = LegendreSequenceMeritFactors()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="Legendre sequence merit factors for odd primes p <= %d"
            % (UP_TO,)))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
