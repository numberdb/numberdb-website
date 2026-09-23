"""The Markoff number asymptotic density constant -- numberdb.org/T432.

Let M(x) be the number of Markoff numbers less than x. Zagier proved

    M(x) = C log(3x)^2 + O(log x (log log x)^2).

This generator stores the 72 fractional digits of C recorded in OEIS A261613.
It does not prove the tail bound for those digits, so the table's rigour is
`assumed-bound`. The integrity check below compares the leading digits with a
fresh finite partial sum of Zagier's rapidly convergent series and checks that
the Markoff-triple counts match the family issue's controls.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set
"""

import math
import os
import sys
from collections import deque

import numberdb.sage as numberdb


TABLE = os.environ.get("NUMBERDB_TABLE", "T432")
DIGITS = 72

OEIS_FRACTIONAL_DIGITS = (
    "180717104711806478057792649049167621476305627670882734805388896650560768"
)
VALUE = "0." + OEIS_FRACTIONAL_DIGITS

# Controls copied from numberdb-data issue #193. Matching these checks that the
# independent partial-sum code is enumerating the same normalized Markoff tree.
TRIPLE_COUNT_CONTROLS = {
    10**2: 7,
    10**3: 13,
    10**4: 21,
    10**5: 31,
    10**6: 40,
    10**7: 56,
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def markoff_triples(limit):
    """Normalized Markoff triples with largest entry at most limit."""
    start = (1, 1, 1)
    seen = {start}
    queue = deque([start])
    triples = []

    while queue:
        triple = queue.popleft()
        if triple[2] <= limit:
            triples.append(triple)

        for index in range(3):
            values = list(triple)
            other = [i for i in range(3) if i != index]
            values[index] = 3 * values[other[0]] * values[other[1]] - values[index]
            child = tuple(sorted(values))
            if child not in seen and child[2] <= limit:
                seen.add(child)
                queue.append(child)

    return sorted(triples, key=lambda t: (t[2], t[1], t[0]))


def zagier_partial_sum(limit):
    """Finite partial sum of Zagier's series, using triples with r <= limit."""
    total = 0.0
    for p, q, r in markoff_triples(limit):
        fp = math.acosh(3 * p / 2)
        fq = math.acosh(3 * q / 2)
        fr = math.acosh(3 * r / 2)
        weight = 0.5 if (p, q, r) in ((1, 1, 1), (1, 1, 2)) else 1.0
        total += weight * (fp + fq - fr) / (fp * fq * fr)
    return 3 * total / (math.pi * math.pi)


def run_integrity_checks():
    """Independent checks for the source transcription and the stated formula."""
    if len(OEIS_FRACTIONAL_DIGITS) != DIGITS:
        raise ArithmeticError("OEIS digit string does not have 72 digits")

    for limit, expected in TRIPLE_COUNT_CONTROLS.items():
        found = len(markoff_triples(limit))
        if found != expected:
            raise ArithmeticError(
                "Markoff triple count for r <= %s is %s, expected %s"
                % (limit, found, expected)
            )

    partial = zagier_partial_sum(10**7)
    if format(partial, ".16f") != VALUE[:18]:
        raise ArithmeticError(
            "Zagier partial sum check failed: %.18f vs %s"
            % (partial, VALUE)
        )


class MarkoffNumberAsymptoticDensityConstant(numberdb.Generator):

    table = TABLE
    parameters = ()
    type = "R"
    digits = DIGITS
    rigour = "assumed-bound"

    def enumerate(self):
        yield {}

    def value(self, params, digits):
        if params:
            raise ValueError("this table has no parameters")
        if digits != DIGITS:
            raise ValueError("the source transcription has exactly 72 digits")
        return VALUE


if __name__ == "__main__":
    _key_from_stdin()
    run_integrity_checks()
    generator = MarkoffNumberAsymptoticDensityConstant()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="Markoff density constant from OEIS A261613"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
