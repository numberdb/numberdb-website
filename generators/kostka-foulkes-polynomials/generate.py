"""Kostka-Foulkes polynomials -- numberdb.org/T259.

    s_lambda = sum_mu K_{lambda,mu}(t) P_mu(x;t)

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The table holds the nonzero coefficients, so lambda and mu have the same size
and lambda dominates mu. Pairs outside that dominance order have coefficient
zero and are not entries.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.combinat.sf.kfpoly import KostkaFoulkesPolynomial

#: Measured before filling the draft: up to size 9 gives 901 entries, the
#: longest value is 182 characters, and the entries block is 75.1 KB. Size 10
#: would be 1719 entries, over the soft entry limit and at 160.8 KB.
MAX_SIZE = 9


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
        yield []
        return
    for part in range(min(total, largest), 0, -1):
        for rest in _partitions(total - part, part):
            yield [part] + rest


def _dominates(lam, mu):
    """Whether lam dominates mu."""
    seen_lam = 0
    seen_mu = 0
    for index in range(max(len(lam), len(mu))):
        seen_lam += lam[index] if index < len(lam) else 0
        seen_mu += mu[index] if index < len(mu) else 0
        if seen_lam < seen_mu:
            return False
    return True


def _format_partition(partition):
    return ",".join(str(part) for part in partition)


def _parse_partition(text):
    return [int(part) for part in text.split(",") if part]


class KostkaFoulkesPolynomials(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T259")
    parameters = ("lambda", "mu")
    type = "Z[]"

    # Exact: Sage returns a polynomial over ZZ['t'] or an exact integer.
    rigour = "exact"

    def enumerate(self, max_size=MAX_SIZE):
        for size in range(1, max_size + 1):
            parts = list(_partitions(size))
            for lam in parts:
                for mu in parts:
                    if _dominates(lam, mu):
                        yield {
                            "lambda": _format_partition(lam),
                            "mu": _format_partition(mu),
                        }

    def value(self, params, digits):
        lam = _parse_partition(params["lambda"])
        mu = _parse_partition(params["mu"])
        return KostkaFoulkesPolynomial(lam, mu)


if __name__ == "__main__":
    _key_from_stdin()
    generator = KostkaFoulkesPolynomials()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="Kostka-Foulkes polynomials for |lambda| <= %d"
                    % (MAX_SIZE,)))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
