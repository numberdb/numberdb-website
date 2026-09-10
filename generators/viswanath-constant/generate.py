"""Viswanath's constant -- numberdb.org/T189

    V = lim |t_n|^(1/n),   t_1 = t_2 = 1,  t_n = +-t_{n-1} +- t_{n-2}

with the four signs independent and equally likely. The limit exists and is
the same for almost every sequence of signs.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

This generator computes nothing. V is the Lyapunov exponent of a product of
random matrices and there is no series for it: Viswanath's own method needs a
fractal measure on the Stern-Brocot tree, Bai's a cycle expansion, and
Oliveira and de Figueiredo's an interval computation of both. OEIS marks the
expansion `hard` and holds fourteen significant digits, and three further
digits proposed in 2017 were withdrawn in 2018 as doubtful.

So the value is transcribed, and this file exists to say so in the place a
reader looks for how a number was made -- and to be the thing that would
change if somebody recomputed it. A generator that returned a hundred digits
of its own would be claiming to have done what the literature has not.
"""

import os
import sys

import numberdb.sage as numberdb


#: OEIS A078416, fourteen significant digits. Written as it is quoted, so the
#: last digit is the uncertain one under this database's decimal convention.
VISWANATH = "1.1319882487943"


class ViswanathConstant(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE") or "T189"
    parameters = ()
    type = "R"

    #Transcribed, not computed here, and not an enclosure: an interval
    #computation of V exists in the literature and this does not reproduce it.
    rigour = "heuristic"

    def enumerate(self):
        yield {}

    def value(self, params, digits):
        #`digits` says how well this is known, which is fourteen places and
        #not the hundred the table asks of a computed value. Without it the
        #client refuses the entry, and it is right to: a value returned to a
        #hundred digits claims a hundred.
        return {"number": VISWANATH, "digits": 14}


if __name__ == "__main__":
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") == "1":
        os.environ["NUMBERDB_API_KEY"] = sys.stdin.read().strip()
    generator = ViswanathConstant()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(generator.publish(message="Viswanath's constant, transcribed"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
