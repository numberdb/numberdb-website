"""Levy's constant -- numberdb.org/T172

The almost-sure growth rate of the denominators of the convergents of the
regular continued fraction, in both of the normalisations in use: the limit
e^beta of q_n^(1/n) itself, and its logarithm beta, which is called the
Khinchin-Levy constant.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Both rows have a closed form, beta = pi^2/(12 log 2), and are computed in real
ball arithmetic from pi and log 2 as balls rather than as rounded constants,
so every stored digit is covered by the enclosure. That is why this table's
rigour is `proven` where T170's is `heuristic (agreement-checked)`: it was one
table, and the weaker word covered rows that did not need it.

Split out of T170, which was "Constants of the regular continued fraction":
a table answers a search by its title, and that title named neither Levy nor
Lochs nor Khinchin.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.real_arb import RealBallField


DIGITS = 100

#: Bits of working precision beyond what the written digits need. Nothing here
#: is ill-conditioned -- pi^2/(12 log 2) and its exponential are ordinary
#: values of ordinary functions -- so the guard is generous because on two
#: entries it costs nothing.
WORKING_GUARD = 64

NORMALISATIONS = ("levy", "khinchin-levy")

COMMENTS = {
    "levy": "Levy's constant, the almost-sure limit of $q_n^{1/n}$"
            " CITE{OEISA086702}.",
    "khinchin-levy": "The Khinchin-Levy constant"
                     " $\\beta=\\log(e^\\beta)=\\pi^2/(12\\log 2)$, the"
                     " almost-sure limit of $\\frac{1}{n}\\log q_n$"
                     " CITE{OEISA100199}.",
}


def closed_form(normalisation, digits):
    R = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
    beta = R.pi() ** 2 / (12 * R(2).log())
    if normalisation == "khinchin-levy":
        return beta
    if normalisation == "levy":
        return beta.exp()
    raise ValueError("unknown normalisation %r" % (normalisation,))


class LevysConstant(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE") or "T172"
    parameters = ("normalisation",)
    type = "R"
    digits = DIGITS

    #Ball arithmetic from pi and log 2 to the result.
    rigour = "proven"

    def enumerate(self):
        for normalisation in NORMALISATIONS:
            yield {"normalisation": normalisation}

    def value(self, params, digits):
        normalisation = str(params["normalisation"])
        if normalisation not in NORMALISATIONS:
            raise ValueError("normalisation must be one of the listed keys")
        return {"number": closed_form(normalisation, digits),
                "comment": COMMENTS[normalisation]}


if __name__ == "__main__":
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") == "1":
        os.environ["NUMBERDB_API_KEY"] = sys.stdin.read().strip()
    generator = LevysConstant()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(generator.publish(message="Levy's constant"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
