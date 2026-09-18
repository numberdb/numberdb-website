"""Complementary Shapiro polynomials Q_n -- numberdb.org/T320 (table wanted: numberdb-data#160)

    P_0 = Q_0 = 1,
    P_(n+1) = P_n + x^(2^n) Q_n,
    Q_(n+1) = P_n - x^(2^n) Q_n.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

On the NumberDB build machine, where arguments are not passed through
agents/sage.sh, publish with:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
          agents/sage.sh generate.py

The family convention from numberdb-data#160 is used here: the variable is x,
coefficients run low degree first, and the table is indexed by the construction
parameter n, so Q_n has degree 2^n - 1.

The values are exact polynomials over ZZ. There is no precision to choose and
no rounding; writing fewer coefficients would make a different polynomial.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


UP_TO = 7


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


def shapiro_pair(n):
    """Return the pair (P_n, Q_n) from the defining recurrence."""
    p = RING.one()
    q = RING.one()
    for k in range(int(n)):
        p, q = p + X ** (2 ** k) * q, p - X ** (2 ** k) * q
    return p, q


def complementary_shapiro_polynomial(n):
    return shapiro_pair(n)[1]


def rudin_shapiro_sign(j):
    """The Golay-Rudin-Shapiro coefficient a_j."""
    return ZZ(1) if (int(j) & (int(j) >> 1)).bit_count() % 2 == 0 else ZZ(-1)


def rudin_shapiro_polynomial(n):
    """Return P_n from the direct coefficient definition."""
    return sum(rudin_shapiro_sign(j) * X ** j for j in range(2 ** int(n)))


def complementary_from_direct_p(n):
    """Return Q_n from Q_n(x)=(-1)^n x^(2^n-1) P_n(-1/x)."""
    n = int(n)
    degree = 2 ** n - 1
    terms = []
    for j in range(degree + 1):
        sign = ZZ(1) if (n + j) % 2 == 0 else ZZ(-1)
        terms.append(sign * rudin_shapiro_sign(j) * X ** (degree - j))
    return sum(terms, RING.zero())


def reverse_polynomial(polynomial, degree):
    """Return x^degree f(1/x), without leaving ZZ[x]."""
    return sum(polynomial[i] * X ** (degree - i) for i in range(degree + 1))


def autocorrelation(polynomial, length, shift):
    """Aperiodic autocorrelation of the coefficient vector at shift."""
    return sum(polynomial[j] * polynomial[j + shift]
               for j in range(length - shift))


def check_identities(up_to=UP_TO):
    printed_examples = {
        1: 1 - X,
        2: 1 + X - X**2 + X**3,
        3: 1 + X + X**2 - X**3 - X**4 - X**5 + X**6 - X**7,
    }
    values = {n: shapiro_pair(n) for n in range(up_to + 1)}
    for n, expected in printed_examples.items():
        if n <= up_to and values[n][1] != expected:
            raise AssertionError("printed example failed at n=%s" % (n,))

    for n, (p, q) in values.items():
        degree = 2 ** n - 1
        length = degree + 1
        if q.degree() != degree:
            raise AssertionError("degree check failed at n=%s" % (n,))
        if q[0] != 1:
            raise AssertionError("constant coefficient check failed at n=%s"
                                 % (n,))
        for j in range(length):
            if q[j] not in (-1, 1):
                raise AssertionError("coefficient check failed at n=%s, j=%s"
                                     % (n, j))
        if p != rudin_shapiro_polynomial(n):
            raise AssertionError("direct P coefficient check failed at n=%s"
                                 % (n,))
        if q != complementary_from_direct_p(n):
            raise AssertionError("direct Q coefficient check failed at n=%s"
                                 % (n,))

        norm = (p * reverse_polynomial(p, degree)
                + q * reverse_polynomial(q, degree))
        if norm != ZZ(2) ** (n + 1) * X ** degree:
            raise AssertionError("complementary norm check failed at n=%s"
                                 % (n,))
        if autocorrelation(p, length, 0) + autocorrelation(q, length, 0) \
                != ZZ(2) ** (n + 1):
            raise AssertionError("autocorrelation c_0 failed at n=%s" % (n,))
        for shift in range(1, length):
            if autocorrelation(p, length, shift) \
                    + autocorrelation(q, length, shift) != 0:
                raise AssertionError(
                    "autocorrelation check failed at n=%s, shift=%s"
                    % (n, shift))

        at_one = ZZ(0) if n % 2 else ZZ(2) ** (n // 2)
        if q(ZZ(1)) != at_one:
            raise AssertionError("Q_n(1) check failed at n=%s" % (n,))
        at_minus_one = (ZZ(1) if n == 0
                        else (-ZZ(1) if n % 2 == 0 else ZZ(1))
                        * ZZ(2) ** ((n + 1) // 2))
        if q(-ZZ(1)) != at_minus_one:
            raise AssertionError("Q_n(-1) check failed at n=%s" % (n,))

    for n in range(1, up_to):
        q = values[n][1]
        next_q = values[n + 1][1]
        if next_q != q(X**2) + X * q(-X**2):
            raise AssertionError("one-polynomial recurrence failed at n=%s"
                                 % (n,))


class ComplementaryShapiroPolynomials(numberdb.Generator):

    table = "T320"
    parameters = ("n",)
    type = "Z[]"
    rigour = "exact"

    def enumerate(self, up_to=UP_TO):
        for n in range(up_to + 1):
            yield {"n": n}

    def value(self, params, digits):
        return complementary_shapiro_polynomial(ZZ(params["n"]))


def main():
    _key_from_stdin()
    check_identities()
    generator = ComplementaryShapiroPolynomials()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message=("Complementary Shapiro polynomials Q_n for 0 <= n <= %d"
                     % (UP_TO,))))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
