"""Sharp constants in the fractional Sobolev inequality -- numberdb.org/T354

Generate the sharp constants S_{n,s} in the fractional Sobolev inequality.
The table stores the lower-bound direction

    S_{n,s} ||u||_{L^(2n/(n-2s))} <= ||(-Delta)^(s/2) u||_2,

where the Fourier transform is

    uhat(xi) = (2*pi)^(-n/2) int u(x) exp(-i x.xi) dx,

so (-Delta)^(s/2) is the Fourier multiplier |xi|^s and
||(-Delta)^(1/2) u||_2 = ||grad u||_2. The homogeneous space Hdot^s consists
of distributions with |xi|^s uhat(xi) in L^2. Some sources state the
reciprocal square of this constant.

Run it with SageMath:

    $ sage -pip install numberdb
    $ sage -python generate.py
    $ sage -python generate.py --publish

Under the repository's agent runner, pipe the API key on stdin:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 \
        agents/sage.sh generators/sharp-constants-fractional-sobolev-inequality/generate.py

Set NUMBERDB_PUBLISH=preview to preview the write, or NUMBERDB_PUBLISH=1 to
send the entries and attach this file.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


MAX_DIMENSION = 20
MAX_DENOMINATOR = 4
WORKING_GUARD = 96


def configure_key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        numberdb.configure(api_key=token)


def rational_power(base, exponent):
    return (base.parent()(exponent) * base.log()).exp()


def fractional_orders(n, max_denominator=MAX_DENOMINATOR):
    n = ZZ(n)
    orders = set()
    for denominator in range(1, max_denominator + 1):
        for numerator in range(1, n * denominator):
            s = QQ(numerator) / QQ(denominator)
            if s.denominator() <= max_denominator and 2 * s < n:
                orders.add(s)
    return sorted(orders)


def sobolev_constant(field, n, s):
    n = ZZ(n)
    s = QQ(s)
    source_upper_constant = (
        field((n - 2 * s) / 2).gamma()
        / (
            rational_power(field(2), 2 * s)
            * rational_power(field.pi(), s)
            * field((n + 2 * s) / 2).gamma()
        )
        * rational_power(field(n).gamma() / field(QQ(n) / 2).gamma(),
                         QQ(2) * s / n)
    )
    value = source_upper_constant.rsqrt()
    if not value.is_finite():
        raise ArithmeticError("computed a non-finite ball for n=%s, s=%s"
                              % (n, s))
    return value


class FractionalSobolevSharpConstants(numberdb.Generator):
    table = os.environ.get("NUMBERDB_TABLE") or "T354"
    parameters = ("n", "s")
    type = "R"
    digits = 100
    rigour = "proven"

    def enumerate(self):
        for n in range(1, MAX_DIMENSION + 1):
            for s in fractional_orders(n):
                yield {"n": str(n), "s": str(s)}

    def value(self, params, digits):
        field = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
        return sobolev_constant(field, ZZ(params["n"]), QQ(params["s"]))


def main():
    configure_key_from_stdin()
    generator = FractionalSobolevSharpConstants()
    mode = os.environ.get("NUMBERDB_PUBLISH")
    if "--publish" in sys.argv or mode == "1":
        print(generator.publish(message="sharp fractional Sobolev constants"))
        return
    if "--preview" in sys.argv or mode == "preview":
        print(generator.preview())
        return
    report = generator.verify(sample=None)
    print(report)
    sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
