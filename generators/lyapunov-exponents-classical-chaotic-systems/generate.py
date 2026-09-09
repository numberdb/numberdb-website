"""Lyapunov exponents of classical chaotic systems.

This generator stores exact Lyapunov exponents for six standard maps, printed
estimates from Sprott's table of common chaotic systems, and the logarithm of
Viswanath's constant for the random Fibonacci recurrence.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The exact map rows are computed in real ball arithmetic. The Sprott rows are
transcribed decimal estimates; Sprott states that the least significant digit
is only a best estimate. The random Fibonacci row is stored as a deliberately
coarse ball around the logarithm of the published growth constant.
"""

import os
import re
import sys

import numberdb.sage as numberdb
from sage.rings.real_arb import RealBallField


DIGITS = 100
WORKING_GUARD = 64
VISWANATH_LOG = "0.123975598803 +/- 1e-12"


SYSTEMS = (
    "logistic-4",
    "tent-2",
    "doubling-2",
    "gauss",
    "cat",
    "baker",
    "henon-1.4-0.3",
    "chirikov-1",
    "lorenz-10-28-8/3",
    "rossler-0.2-0.2-5.7",
    "ueda-7.5-0.05",
    "sprott-quadratic-2.017",
    "sprott-piecewise-0.6",
    "random-fibonacci",
)


INDICES = {
    "logistic-4": (1,),
    "tent-2": (1,),
    "doubling-2": (1,),
    "gauss": (1,),
    "cat": (1, 2),
    "baker": (1, 2),
    "henon-1.4-0.3": (1, 2),
    "chirikov-1": (1, 2),
    "lorenz-10-28-8/3": (1, 2, 3),
    "rossler-0.2-0.2-5.7": (1, 2, 3),
    "ueda-7.5-0.05": (1, 2, 3),
    "sprott-quadratic-2.017": (1, 2, 3),
    "sprott-piecewise-0.6": (1, 2, 3),
    "random-fibonacci": (1,),
}


SPROTT_VALUES = {
    ("henon-1.4-0.3", 1): "0.41922",
    ("henon-1.4-0.3", 2): "-1.62319",
    ("chirikov-1", 1): "0.10497",
    ("chirikov-1", 2): "-0.10497",
    ("lorenz-10-28-8/3", 1): "0.9056",
    ("lorenz-10-28-8/3", 3): "-14.5723",
    ("rossler-0.2-0.2-5.7", 1): "0.0714",
    ("rossler-0.2-0.2-5.7", 3): "-5.3943",
    ("ueda-7.5-0.05", 1): "0.1034",
    ("ueda-7.5-0.05", 3): "-0.1534",
    ("sprott-quadratic-2.017", 1): "0.0551",
    ("sprott-quadratic-2.017", 3): "-2.0721",
    ("sprott-piecewise-0.6", 1): "0.0362",
    ("sprott-piecewise-0.6", 3): "-0.6362",
}


EXACT_ZERO_ROWS = {
    ("lorenz-10-28-8/3", 2),
    ("rossler-0.2-0.2-5.7", 2),
    ("ueda-7.5-0.05", 2),
    ("sprott-quadratic-2.017", 2),
    ("sprott-piecewise-0.6", 2),
}


def significant_digits(text):
    body = re.sub(r"^[+-]", "", text)
    body = body.split("e")[0].split("E")[0].replace(".", "")
    body = body.lstrip("0")
    return len(body) if body else 1


def field(digits):
    return RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def log2(digits):
    return field(digits)(2).log()


def exact_value(system, index, digits):
    R = field(digits)
    if system in ("logistic-4", "tent-2", "doubling-2"):
        if index != 1:
            raise ValueError("%s has only one exponent" % system)
        return R(2).log()
    if system == "gauss":
        if index != 1:
            raise ValueError("the Gauss map row has only one exponent")
        return R.pi() * R.pi() / (6 * R(2).log())
    if system == "cat":
        eigenvalue = (R(3) + R(5).sqrt()) / 2
        value = eigenvalue.log()
        return value if index == 1 else -value
    if system == "baker":
        value = R(2).log()
        return value if index == 1 else -value
    raise ValueError("%s is not an exact closed-form row" % system)


def entry_comment(system, index):
    comments = {
        ("logistic-4", 1): (
            r"$\lambda_1=\log 2$ for the logistic map at $r=4$ "
            r"CITE{WikiLogistic} CITE{SprottCommon}."
        ),
        ("tent-2", 1): (
            r"$\lambda_1=\log 2$ for the full tent map "
            r"$x\mapsto 2\min(x,1-x)$ CITE{WikiTent}."
        ),
        ("doubling-2", 1): (
            r"$\lambda_1=\log 2$ for the doubling map "
            r"$x\mapsto 2x\bmod 1$ CITE{WikiDyadic}."
        ),
        ("gauss", 1): (
            r"$\lambda_1=\pi^2/(6\log2)$ for the continued-fraction Gauss "
            r"map CITE{WikiContinuedFraction}; this is twice the "
            r"Khinchin-Levy constant in "
            r"HREF{T170}[the table of regular continued-fraction constants]."
        ),
        ("cat", 1): (
            r"The expanding eigenvalue of Arnold's cat-map matrix is "
            r"$(3+\sqrt5)/2$ CITE{WikiCatMap}."
        ),
        ("cat", 2): (
            r"The contracting eigenvalue of Arnold's cat-map matrix is "
            r"$(3-\sqrt5)/2$, so $\lambda_2=-\lambda_1$."
        ),
        ("baker", 1): (
            r"The baker's map expands one coordinate by $2$ "
            r"CITE{WikiBakerMap}."
        ),
        ("baker", 2): (
            r"The baker's map contracts the other coordinate by $1/2$; the "
            r"folded and unfolded versions have the same Lyapunov spectrum."
        ),
        ("henon-1.4-0.3", 1): (
            r"Sprott lists the Henon map at $a=1.4$, $b=0.3$ "
            r"CITE{SprottCommon}."
        ),
        ("henon-1.4-0.3", 2): (
            r"For the Henon map at $a=1.4$, $b=0.3$, the exponent sum is "
            r"$\log 0.3$."
        ),
        ("chirikov-1", 1): (
            r"Sprott lists the Chirikov standard map at $k=1$ "
            r"CITE{SprottCommon}."
        ),
        ("chirikov-1", 2): (
            r"The Chirikov standard map is area-preserving, so "
            r"$\lambda_2=-\lambda_1$."
        ),
        ("lorenz-10-28-8/3", 1): (
            r"Sprott lists the Lorenz system at "
            r"$(\sigma,\rho,\beta)=(10,28,8/3)$ CITE{SprottCommon}."
        ),
        ("lorenz-10-28-8/3", 2): (
            r"An autonomous flow has a zero exponent in the flow direction."
        ),
        ("lorenz-10-28-8/3", 3): (
            r"For the Lorenz system at $(10,28,8/3)$, the divergence gives "
            r"$\lambda_1+\lambda_2+\lambda_3=-41/3$."
        ),
        ("rossler-0.2-0.2-5.7", 1): (
            r"Sprott lists the Rossler system at $a=b=0.2$, $c=5.7$ "
            r"CITE{SprottCommon}."
        ),
        ("rossler-0.2-0.2-5.7", 2): (
            r"An autonomous flow has a zero exponent in the flow direction."
        ),
        ("rossler-0.2-0.2-5.7", 3): (
            r"Sprott gives the negative Rossler exponent with four significant "
            r"digits CITE{SprottCommon}."
        ),
        ("ueda-7.5-0.05", 1): (
            r"Sprott lists the Ueda oscillator at $B=7.5$, $k=0.05$ "
            r"CITE{SprottCommon}."
        ),
        ("ueda-7.5-0.05", 2): (
            r"An autonomous flow has a zero exponent in the flow direction."
        ),
        ("ueda-7.5-0.05", 3): (
            r"For the Ueda oscillator in Sprott's normalisation, "
            r"$\lambda_1+\lambda_2+\lambda_3=-k=-0.05$."
        ),
        ("sprott-quadratic-2.017", 1): (
            r"Sprott lists the simplest quadratic flow at $A=2.017$ "
            r"CITE{SprottCommon}."
        ),
        ("sprott-quadratic-2.017", 2): (
            r"An autonomous flow has a zero exponent in the flow direction."
        ),
        ("sprott-quadratic-2.017", 3): (
            r"For Sprott's simplest quadratic flow, the divergence gives "
            r"$\lambda_1+\lambda_2+\lambda_3=-A$."
        ),
        ("sprott-piecewise-0.6", 1): (
            r"Sprott lists the simplest piecewise-linear flow at $A=0.6$ "
            r"CITE{SprottCommon}."
        ),
        ("sprott-piecewise-0.6", 2): (
            r"An autonomous flow has a zero exponent in the flow direction."
        ),
        ("sprott-piecewise-0.6", 3): (
            r"For the piecewise-linear flow, the divergence gives "
            r"$\lambda_1+\lambda_2+\lambda_3=-A$ away from the switching "
            r"surface."
        ),
        ("random-fibonacci", 1): (
            r"This is $\log V$, where "
            r"$V=1.1319882487943\ldots$ is Viswanath's constant "
            r"CITE{OEISA078416} CITE{Viswanath}."
        ),
    }
    return comments[(system, index)]


class ClassicalChaoticLyapunovExponents(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T171")
    parameters = ("system", "i")
    type = "R"
    digits = DIGITS
    rigour = "heuristic"

    def enumerate(self):
        for system in SYSTEMS:
            for index in INDICES[system]:
                yield {"system": system, "i": index}

    def digits_for(self, params):
        key = (str(params["system"]), int(params["i"]))
        if key in SPROTT_VALUES:
            return significant_digits(SPROTT_VALUES[key])
        if key == ("random-fibonacci", 1):
            return 12
        return self.digits

    def value(self, params, digits):
        system = str(params["system"])
        index = int(params["i"])
        if system not in SYSTEMS:
            raise ValueError("system must be one of the listed keys")
        if index not in INDICES[system]:
            raise ValueError("i is not valid for %s" % system)

        key = (system, index)
        if key in SPROTT_VALUES:
            number = SPROTT_VALUES[key]
        elif key in EXACT_ZERO_ROWS:
            number = 0
        elif key == ("random-fibonacci", 1):
            number = VISWANATH_LOG
        else:
            number = exact_value(system, index, digits)
        return {"number": number, "comment": entry_comment(system, index)}


if __name__ == "__main__":
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") == "1":
        os.environ["NUMBERDB_API_KEY"] = sys.stdin.read().strip()
    generator = ClassicalChaoticLyapunovExponents()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(generator.publish(
            message="Lyapunov exponents of classical chaotic systems"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
