"""Best known packings of equal circles in a circle -- numberdb.org/T394

For each 2 <= n <= 500, this stores two equivalent forms from Packomania's
cci table: the largest minimum distance d_n between n points in the unit disk,
and the enclosing radius R_n = 1 + 2/d_n for n unit circles.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The Packomania source files are copied beside this generator from the
25-Dec-2024 update. The generator checks that the copied radius, distance and
ratio columns agree to the precision stored for the census rows before it
returns any values.
"""

import os
import sys
from decimal import Decimal, localcontext
from pathlib import Path

import numberdb.sage as numberdb
from sage.rings.real_arb import RealBallField


MAX_N = 500
TRANSCRIBED_DIGITS = 9
WORKING_GUARD = 96

DISTANCE_FILE = "packomania-cci-distance-2024-12-25.txt"
RATIO_FILE = "packomania-cci-ratio-2024-12-25.txt"
RADIUS_FILE = "packomania-cci-radius-2024-12-25.txt"

PROVEN_BY = {
    **{n: "Pirl" for n in range(2, 11)},
    11: "Melissen",
    12: "Fodor12",
    13: "Fodor13",
    14: "EkanayakeLaFountain",
    19: "Fodor19",
}

EXACT_N = frozenset([2, 3, 4, 5, 6, 7, 8, 9, 11, 13, 18, 19])

EXACT_COMMENTS = {
    (2, "separation"): "$d_2=2$.",
    (2, "container"): "$R_2=2$.",
    (3, "separation"): "$d_3=\\sqrt{3}$.",
    (3, "container"): "$R_3=1+2/\\sqrt{3}$.",
    (4, "separation"): "$d_4=\\sqrt{2}$.",
    (4, "container"): "$R_4=1+\\sqrt{2}$.",
    (5, "separation"): "$d_5=2\\sin(\\pi/5)$.",
    (5, "container"): "$R_5=1+\\csc(\\pi/5)$.",
    (6, "separation"): "$d_6=1$.",
    (6, "container"): "$R_6=3$.",
    (7, "separation"): "$d_7=1$.",
    (7, "container"): "$R_7=3$.",
    (8, "separation"): "$d_8=2\\sin(\\pi/7)$.",
    (8, "container"): "$R_8=1+\\csc(\\pi/7)$.",
    (9, "separation"): "$d_9=2\\sin(\\pi/8)$.",
    (9, "container"): "$R_9=1+\\csc(\\pi/8)$.",
    (11, "separation"): "$d_{11}=2\\sin(\\pi/9)$.",
    (11, "container"): "$R_{11}=1+\\csc(\\pi/9)$.",
    (13, "separation"): "$d_{13}=(\\sqrt{5}-1)/2$.",
    (13, "container"): "$R_{13}=2+\\sqrt{5}$.",
    (18, "separation"): "$d_{18}=2\\sin(\\pi/12)$.",
    (18, "container"): "$R_{18}=1+\\csc(\\pi/12)$.",
    (19, "separation"): "$d_{19}=2\\sin(\\pi/12)$.",
    (19, "container"): "$R_{19}=1+\\csc(\\pi/12)$.",
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _read_column(name):
    path = Path(__file__).resolve().parent / name
    out = {}
    with path.open(encoding="utf8") as handle:
        for line in handle:
            parts = line.split()
            if len(parts) < 2:
                continue
            n = int(parts[0])
            if 2 <= n <= MAX_N:
                out[n] = parts[1]
    missing = [n for n in range(2, MAX_N + 1) if n not in out]
    if missing:
        raise ValueError("%s is missing n=%s" % (name, missing[:5]))
    return out


def _plain_decimal(value, count):
    count = int(count)
    if value.is_zero():
        return "0"
    exponent = value.adjusted()
    with localcontext() as context:
        context.prec = count + 8
        quantised = value.quantize(Decimal(1).scaleb(exponent - count + 1))
    if -7 < exponent < count:
        return format(quantised, "f")
    mantissa, _, power = format(quantised, "e").partition("e")
    return "%se%d" % (mantissa, int(power))


def _round_sig(text, digits=TRANSCRIBED_DIGITS):
    with localcontext() as context:
        context.prec = digits + 8
        value = Decimal(text)
    return _plain_decimal(value, digits)


def _round_decimal(value, digits=TRANSCRIBED_DIGITS):
    with localcontext() as context:
        context.prec = digits + 8
        value = +value
    return _plain_decimal(value, digits)


def _check_source_consistency(distance, ratio, radius):
    with localcontext() as context:
        context.prec = 80
        for n in range(2, MAX_N + 1):
            d = Decimal(distance[n])
            r = Decimal(radius[n])
            R = Decimal(ratio[n])
            if _round_decimal(Decimal(1) / r) != _round_sig(ratio[n]):
                raise ValueError("radius and ratio disagree at n=%d" % (n,))
            if _round_decimal(Decimal(2) * r / (Decimal(1) - r)) != _round_sig(distance[n]):
                raise ValueError("radius and distance disagree at n=%d" % (n,))
            if _round_decimal(Decimal(1) + Decimal(2) / d) != _round_sig(ratio[n]):
                raise ValueError("distance and ratio disagree at n=%d" % (n,))


def _data():
    distance = _read_column(DISTANCE_FILE)
    ratio = _read_column(RATIO_FILE)
    radius = _read_column(RADIUS_FILE)
    _check_source_consistency(distance, ratio, radius)
    return distance, ratio


DISTANCE, RATIO = _data()


def _field(digits):
    return RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def _exact_distance(n, digits):
    field = _field(digits)
    if n == 2:
        return 2
    if n == 3:
        return field(3).sqrt()
    if n == 4:
        return field(2).sqrt()
    if n == 5:
        return 2 * (field.pi() / 5).sin()
    if n in (6, 7):
        return 1
    if n == 8:
        return 2 * (field.pi() / 7).sin()
    if n == 9:
        return 2 * (field.pi() / 8).sin()
    if n == 11:
        return 2 * (field.pi() / 9).sin()
    if n == 13:
        return (field(5).sqrt() - 1) / 2
    if n in (18, 19):
        return 2 * (field.pi() / 12).sin()
    raise KeyError(n)


def _exact_value(n, normalisation, digits):
    d = _exact_distance(n, digits)
    if normalisation == "separation":
        return d
    if n == 2:
        return 2
    if n in (6, 7):
        return 3
    field = _field(digits)
    return field(1) + field(2) / field(d)


def _proof_sentence(n):
    key = PROVEN_BY.get(n)
    if key:
        return "Optimality is proven by CITE{%s}." % (key,)
    return "Packomania CITE{Packomania} lists this as the best packing known; optimality is open."


def _comment(n, normalisation):
    pieces = []
    exact = EXACT_COMMENTS.get((n, normalisation))
    if exact:
        pieces.append(exact)
    pieces.append(_proof_sentence(n))
    return " ".join(pieces)


def _source_value(n, normalisation):
    if normalisation == "separation":
        return _round_sig(DISTANCE[n])
    return _round_sig(RATIO[n])


class BestKnownPackingsEqualCirclesInCircle(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T394")
    parameters = ("n", "normalisation")
    type = "R"
    digits = 100
    rigour = "heuristic (agreement-checked)"
    files = (__file__, DISTANCE_FILE, RATIO_FILE, RADIUS_FILE)

    def enumerate(self, max_n=MAX_N):
        for n in range(2, max_n + 1):
            yield {"n": n, "normalisation": "separation"}
            yield {"n": n, "normalisation": "container"}

    def digits_for(self, params):
        n = int(params["n"])
        if n in EXACT_N:
            return self.digits
        return TRANSCRIBED_DIGITS

    def value(self, params, digits):
        n = int(params["n"])
        normalisation = params["normalisation"]
        if n in EXACT_N:
            number = _exact_value(n, normalisation, digits)
            return {"number": number, "comment": _comment(n, normalisation)}
        return {
            "number": _source_value(n, normalisation),
            "digits": TRANSCRIBED_DIGITS,
            "comment": _comment(n, normalisation),
        }


if __name__ == "__main__":
    _key_from_stdin()
    generator = BestKnownPackingsEqualCirclesInCircle()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="imported Packomania cci values through n=500"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
