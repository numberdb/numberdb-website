r"""Cumulants $\kappa_n$ of the Tracy–Widom distributions -- numberdb.org/T444

This generator reproduces the first four cumulants of the Tracy–Widom
distributions for beta = 1, 2 and 4. Bornemann prints the mean, variance,
skewness and excess kurtosis; this file stores the first two directly and
converts the last two to raw cumulants.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

For this repository's build environment, use:

    $ agents/sage.sh generate.py
    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
        agents/sage.sh generate.py

The optional convention check uses a direct Painlevé-II integration:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 \
        TW_CONVENTION_CHECK=1 agents/sage.sh generate.py
"""

from decimal import Decimal, ROUND_HALF_UP, getcontext
import os
import sys

import numberdb.sage as numberdb


TABLE = "T444"
DIGITS = 14

getcontext().prec = 80

SOURCE_STATS = {
    1: {
        "mean": "-1.2065335745820",
        "variance": "1.607781034581",
        "skewness": "0.29346452408",
        "excess": "0.1652429384",
    },
    2: {
        "mean": "-1.771086807411",
        "variance": "0.8131947928329",
        "skewness": "0.224084203610",
        "excess": "0.0934480876",
    },
    4: {
        "mean": "-2.306884893241",
        "variance": "0.5177237207726",
        "skewness": "0.16550949435",
        "excess": "0.0491951565",
    },
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _significant_digits(text):
    digits = [char for char in text if char.isdigit()]
    while digits and digits[0] == "0":
        digits.pop(0)
    return len(digits)


def _format_significant(value, digits):
    if not value:
        return "0"
    adjusted = value.adjusted()
    places = digits - adjusted - 1
    quantum = Decimal(1).scaleb(-places)
    return format(value.quantize(quantum, rounding=ROUND_HALF_UP), "f")


def _cumulants():
    out = {}
    for beta, stats in SOURCE_STATS.items():
        mean = stats["mean"].strip()
        variance = stats["variance"]
        v = Decimal(variance)
        skewness = Decimal(stats["skewness"])
        excess = Decimal(stats["excess"])
        kappa3 = _format_significant(skewness * v.sqrt() ** 3, 10)
        kappa4 = _format_significant(excess * v ** 2, 9)
        out[(beta, 1)] = (mean, _significant_digits(mean))
        out[(beta, 2)] = (variance, _significant_digits(variance))
        out[(beta, 3)] = (kappa3, _significant_digits(kappa3))
        out[(beta, 4)] = (kappa4, _significant_digits(kappa4))
    return out


CUMULANTS = _cumulants()


class TracyWidomCumulants(numberdb.Generator):
    table = TABLE
    parameters = ("beta", "n")
    type = "R"
    digits = DIGITS
    rigour = "measured"

    def enumerate(self):
        for beta in (1, 2, 4):
            for n in range(1, 5):
                yield {"beta": beta, "n": n}

    def value(self, params, digits):
        text, known_digits = CUMULANTS[(int(params["beta"]), int(params["n"]))]
        return {"number": text, "digits": known_digits}


def _rk4_step(rhs, x, y, h):
    k1 = rhs(x, y)
    y2 = [yi + h * ki / 2 for yi, ki in zip(y, k1)]
    k2 = rhs(x + h / 2, y2)
    y3 = [yi + h * ki / 2 for yi, ki in zip(y, k2)]
    k3 = rhs(x + h / 2, y3)
    y4 = [yi + h * ki for yi, ki in zip(y, k3)]
    k4 = rhs(x + h, y4)
    return [
        yi + h * (a + 2 * b + 2 * c + d) / 6
        for yi, a, b, c, d in zip(y, k1, k2, k3, k4)
    ]


def _painleve_gse_mean_variance(step_text="0.00125"):
    from mpmath import mp

    mp.dps = 50
    x_max = mp.mpf("10")
    x_min = mp.mpf("-12")
    h = -mp.mpf(step_text)

    def rhs(x, y):
        q, qp, u, i, j = y
        return [qp, x * q + 2 * q ** 3, -q, -q ** 2, -i]

    x = x_max
    y = [mp.airyai(x), mp.airyai(x, 1), mp.mpf("0"), mp.mpf("0"), mp.mpf("0")]
    samples = []
    steps = int((x_max - x_min) / abs(h))
    for index in range(steps + 1):
        q, _qp, u, i, j = y
        f2_sqrt = mp.exp(-j / 2)
        gse_density = f2_sqrt * (
            i * mp.cosh(u / 2) - q * mp.sinh(u / 2)
        ) / 2
        samples.append((x, gse_density))
        if index < steps:
            y = _rk4_step(rhs, x, y, h)
            x += h

    samples.sort(key=lambda row: row[0])
    dx = abs(h)
    moments = []
    for power in range(3):
        total = mp.mpf("0")
        for index, (x, density) in enumerate(samples):
            weight = 4 if index % 2 else 2
            if index == 0 or index == len(samples) - 1:
                weight = 1
            scaled_x = x / mp.sqrt(2)
            total += weight * scaled_x ** power * density
        moments.append(total * dx / 3)

    mass, first, second = moments
    mean = first / mass
    variance = second / mass - mean ** 2
    return mass, mean, variance


def check_convention():
    from mpmath import mp

    mass, mean, variance = _painleve_gse_mean_variance()
    source_mean = mp.mpf(SOURCE_STATS[4]["mean"])
    source_variance = mp.mpf(SOURCE_STATS[4]["variance"])
    print("Painlevé-II GSE mass:", mp.nstr(mass, 16))
    print("Painlevé-II GSE mean:", mp.nstr(mean, 16))
    print("Painlevé-II GSE variance:", mp.nstr(variance, 16))
    if abs(mean - source_mean) > mp.mpf("2e-6"):
        raise ArithmeticError("GSE mean does not match Bornemann's scaling")
    if abs(variance - source_variance) > mp.mpf("2e-6"):
        raise ArithmeticError("GSE variance does not match Bornemann's scaling")


if __name__ == "__main__":
    _key_from_stdin()
    if os.environ.get("TW_CONVENTION_CHECK") == "1":
        check_convention()

    generator = TracyWidomCumulants()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="filled Tracy-Widom cumulants"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
