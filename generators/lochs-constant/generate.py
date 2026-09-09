"""Lochs's constant -- numberdb.org/T173

    L = 6 log 2 log 10 / pi^2

the constant of Lochs's theorem: for almost every real number the first n
decimal digits determine, asymptotically, Ln terms of the regular continued
fraction expansion.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The table has no parameters: it holds one number, as numberdb.org/T7 holds pi.
What would go in an entry's comment is in the table's Comments instead, where
a search can reach it -- the text index gives weight to a table's Comments and
none at all to an entry's.

Split out of T170, which was "Constants of the regular continued fraction":
a table answers a search by its title, and that title named neither Lochs nor
Levy nor Khinchin.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.real_arb import RealBallField


DIGITS = 100

#: Bits of working precision beyond what the written digits need. See the note
#: in the Levy generator: nothing here is ill-conditioned, and on one entry a
#: generous guard costs nothing.
WORKING_GUARD = 64


def lochs(digits):
    R = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
    return 6 * R(2).log() * R(10).log() / R.pi() ** 2


class LochssConstant(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE") or "T173"
    parameters = ()
    type = "R"
    digits = DIGITS

    #Ball arithmetic from pi, log 2 and log 10 to the result.
    rigour = "proven"

    def enumerate(self):
        yield {}

    def value(self, params, digits):
        return lochs(digits)


if __name__ == "__main__":
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") == "1":
        os.environ["NUMBERDB_API_KEY"] = sys.stdin.read().strip()
    generator = LochssConstant()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(generator.publish(message="Lochs's constant"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
