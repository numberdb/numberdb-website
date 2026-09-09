"""Khinchin's means of the partial quotients -- numberdb.org/T170

For almost every real number the power mean of order $p<1$ of the partial
quotients of its regular continued fraction expansion has a limit that does
not depend on the number. This generator stores that limit for the orders the
table lists; the order 0 is Khinchin's constant.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The rows use the zeta-series expansion of the Gauss-Kuzmin distribution,
computed twice with different precision and truncation, and what is stored is
what the two agree on. Agreement is evidence and not a proof, which is what
the table's rigour says.

This was the Khinchin part of T170 when T170 was "Constants of the regular
continued fraction"; Levy's constant and Lochs's constant were in it too and
are now numberdb.org/T172 and numberdb.org/T173, because a table answers a
search by its title and that title named none of the three.
"""

import os
import sys

import numberdb.sage as numberdb
from mpmath import mp


DIGITS = 100

# Measured at 100 digits: the rows computed at 150 and 210 working decimal
# digits agree in their first 105 significant digits. The corresponding series
# truncations use 680 and 920 grouped zeta terms.
AGREEMENT_DIGITS = (150, 210)
TERM_MULTIPLIER = 4
TERM_GUARD = 80

CONSTANTS = (
    "K0",
    "K-1",
    "K-2",
    "K-3",
    "K-4",
    "K-5",
    "K-6",
    "K-7",
    "K-8",
    "K-9",
    "K-10",
    "K1/2",
    "K-1/2",
)

OEIS_FOR_K = {
    "K0": "OEISA002210",
    "K-1": "OEISA087491",
    "K-2": "OEISA087492",
    "K-3": "OEISA087493",
    "K-4": "OEISA087494",
    "K-5": "OEISA087495",
    "K-6": "OEISA087496",
    "K-7": "OEISA087497",
    "K-8": "OEISA087498",
    "K-9": "OEISA087499",
    "K-10": "OEISA087500",
}

_CACHE = {}


def terms_for(working_digits):
    return TERM_MULTIPLIER * int(working_digits) + TERM_GUARD


def p_of(constant):
    if constant == "K0":
        return None
    if constant == "K1/2":
        return mp.mpf(1) / mp.mpf(2)
    if constant == "K-1/2":
        return -mp.mpf(1) / mp.mpf(2)
    if constant.startswith("K"):
        return mp.mpf(int(constant[1:]))
    raise ValueError("%s is not a Khinchin mean row" % constant)


def signed_binomials(p, nmax):
    """Return (-1)^i binomial(p, i), for 0 <= i <= nmax."""
    coeffs = [mp.mpf(1)]
    p = mp.mpf(p)
    for i in range(nmax):
        coeffs.append(coeffs[-1] * (i - p) / (i + 1))
    return coeffs


def coefficients_by_exponent(p, nmax):
    """Coefficients of zeta(n-p)-1 after grouping by n = 2j+i."""
    signed = signed_binomials(p, nmax)
    coefficients = [mp.mpf(0)] * (nmax + 1)
    for n in range(2, nmax + 1):
        total = mp.mpf(0)
        for j in range(1, n // 2 + 1):
            total += signed[n - 2 * j] / j
        coefficients[n] = total
    return coefficients


def moment_by_zeta(p, working_digits):
    """The p-th moment of the partial quotient distribution, for p != 0."""
    key = ("moment", str(p), int(working_digits))
    if key in _CACHE:
        return _CACHE[key]

    mp.dps = int(working_digits) + 20
    p = mp.mpf(p)
    nmax = terms_for(working_digits)
    coefficients = coefficients_by_exponent(p, nmax)
    total = mp.mpf(0)
    for n in range(2, nmax + 1):
        total += coefficients[n] * (mp.zeta(n - p) - 1)
    value = total / mp.log(2)
    _CACHE[key] = value
    return value


def log_k0_by_zeta(working_digits):
    """log(K_0), using the Bailey-Borwein-Crandall zeta series."""
    key = ("log-k0", int(working_digits))
    if key in _CACHE:
        return _CACHE[key]

    mp.dps = int(working_digits) + 20
    nmax = terms_for(working_digits) // 2
    total = mp.mpf(0)
    alternating_harmonic = mp.mpf(0)
    for k in range(1, 2 * nmax):
        alternating_harmonic += (1 if k % 2 else -1) / mp.mpf(k)
        if k % 2 == 1:
            n = (k + 1) // 2
            total += (mp.zeta(2 * n) - 1) * alternating_harmonic / n
    value = total / mp.log(2)
    _CACHE[key] = value
    return value


def khinchin_mean_decimal(constant, working_digits):
    key = ("decimal", constant, int(working_digits))
    if key in _CACHE:
        return _CACHE[key]

    mp.dps = int(working_digits) + 20
    p = p_of(constant)
    if p is None:
        value = mp.exp(log_k0_by_zeta(working_digits))
    else:
        value = moment_by_zeta(p, working_digits) ** (1 / p)
    text = mp.nstr(value, int(working_digits) + 5)
    _CACHE[key] = text
    return text


def khinchin_mean(constant):
    return numberdb.agreeing(
        lambda working: khinchin_mean_decimal(constant, working),
        at=AGREEMENT_DIGITS,
    )


def entry_comment(constant):
    if constant in OEIS_FOR_K:
        if constant == "K0":
            return "Khinchin's constant, the geometric mean of the partial quotients CITE{%s}." % OEIS_FOR_K[constant]
        if constant == "K-1":
            return "The Khinchin harmonic mean CITE{%s} CITE{MathWorldHarmonic}." % OEIS_FOR_K[constant]
        return "The Khinchin mean of order $%s$ CITE{%s}." % (
            constant[1:], OEIS_FOR_K[constant])
    if constant == "K1/2":
        return "The Khinchin mean of order $1/2$."
    if constant == "K-1/2":
        return "The Khinchin mean of order $-1/2$."
    return ""


class KhinchinMeans(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T170")
    parameters = ("constant",)
    type = "R"
    digits = DIGITS
    rigour = "heuristic (agreement-checked)"

    def enumerate(self):
        for constant in CONSTANTS:
            yield {"constant": constant}

    def value(self, params, digits):
        constant = str(params["constant"])
        if constant not in CONSTANTS:
            raise ValueError("constant must be one of the listed keys")
        return {"number": khinchin_mean(constant),
                "comment": entry_comment(constant)}


if __name__ == "__main__":
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") == "1":
        os.environ["NUMBERDB_API_KEY"] = sys.stdin.read().strip()
    generator = KhinchinMeans()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(generator.publish(message="Khinchin's means"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
