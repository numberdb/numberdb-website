"""Zeros of the derivative zeta'(s) of the Riemann zeta function -- numberdb.org/T387

The table stores the non-real zeros of zeta'(s) with positive imaginary
part, ordered by increasing imaginary part. Candidates are found by Newton
iteration from two fixed seed grids. Each stored value is then certified by a
Krawczyk step in complex ball arithmetic.

Run it with SageMath:

    $ sage -pip install numberdb
    $ sage -python generate.py
    $ sage -python generate.py --publish

Under the repository's agent runner, pipe the API key on stdin:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 \
        agents/sage.sh generators/zeta-derivative-zeros/generate.py

Set NUMBERDB_PUBLISH=preview to preview the write, or NUMBERDB_PUBLISH=1 to
send the entries and attach this file.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField


TABLE = os.environ.get("NUMBERDB_TABLE", "T387")
DIGITS = 30
HEIGHT = 200
WORKING_GUARD = 160
CERTIFY_RADIUS = "1e-24"
NEWTON_TOLERANCE = "1e-45"
RESIDUAL_TOLERANCE = "1e-35"
SAME_ROOT_TOLERANCE = "1e-25"
EXPECTED_ROOTS = 58

OEIS_FIRST_REAL = "2.4631618694543212858743950533063291449207931345673"
OEIS_FIRST_IMAG = "23.2983204927628579020109616265978470505957639"

PRIMARY_REAL_SEEDS = ("0.2", "0.5", "0.8", "1", "1.5", "2", "2.5", "3", "4", "5", "7")
OFFSET_REAL_SEEDS = ("0.35", "0.65", "0.95", "1.25", "1.75", "2.25", "2.75", "3.5", "4.5", "6", "9")


def configure_key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        numberdb.configure(api_key=token)


def decimal_string(numerator, denominator):
    quotient, remainder = divmod(numerator, denominator)
    if remainder == 0:
        return str(quotient)
    if denominator == 2:
        return "%d.5" % quotient
    if denominator == 4:
        return "%d.%s" % (quotient, {1: "25", 2: "5", 3: "75"}[remainder])
    raise ValueError("unsupported seed denominator")


def primary_heights():
    return [decimal_string(j, 2) for j in range(1, 2 * HEIGHT + 1)]


def offset_heights():
    return [decimal_string(j, 4) for j in range(1, 4 * HEIGHT) if j % 2 == 1]


def field(digits=DIGITS):
    return ComplexBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def real_field(complex_field):
    return complex_field._real_field()


def real(complex_field, text):
    return real_field(complex_field)(text)


def upper_as_ball(parent, value):
    return real_field(parent)(str(value.upper()))


def radius_as_ball(parent, value):
    return real_field(parent)(str(value.rad()))


def finite_small(z, threshold):
    return (
        z.real().is_finite()
        and z.imag().is_finite()
        and radius_as_ball(z.parent(), z) < real(z.parent(), threshold)
    )


def ball_abs_upper(z):
    return real_field(z.parent())(str(z.abs().upper()))


def newton_from_seed(seed_real, seed_imag, complex_field):
    z = complex_field(real(complex_field, seed_real), real(complex_field, seed_imag))
    for _ in range(20):
        f = z.zetaderiv(1)
        df = z.zetaderiv(2)
        if not (df.real().is_finite() and df.imag().is_finite()):
            return None
        if ball_abs_upper(df) == 0:
            return None
        step = f / df
        z = z - step
        if not finite_small(z, "1e-35"):
            return None
        if ball_abs_upper(step) < real(complex_field, NEWTON_TOLERANCE):
            break

    if ball_abs_upper(z.zetaderiv(1)) > real(complex_field, RESIDUAL_TOLERANCE):
        return None
    if z.imag().lower() <= 0 or z.imag().upper() > HEIGHT:
        return None
    if z.real().lower() < -10 or z.real().upper() > 20:
        return None
    return z


def same_root(a, b):
    return ball_abs_upper(a - b) < real(a.parent(), SAME_ROOT_TOLERANCE)


def locate_from_grid(real_seeds, heights, complex_field):
    roots = []
    for seed_imag in heights:
        for seed_real in real_seeds:
            root = newton_from_seed(seed_real, seed_imag, complex_field)
            if root is None:
                continue
            if any(same_root(root, old) for old in roots):
                continue
            roots.append(root)
    roots.sort(key=lambda z: (z.imag().center(), z.real().center()))
    return roots


def require_same_roots(primary, offset):
    if len(primary) != len(offset):
        raise ArithmeticError(
            "primary grid found %d roots, offset grid found %d"
            % (len(primary), len(offset))
        )
    for n, (one, two) in enumerate(zip(primary, offset), 1):
        if not same_root(one, two):
            raise ArithmeticError("seed grids disagree at root %d" % n)


def refine_center(candidate, digits):
    complex_field = field(digits)
    z = complex_field(candidate)
    for _ in range(8):
        z = z - z.zetaderiv(1) / z.zetaderiv(2)
    return z


def with_radius(center, radius):
    complex_field = center.parent()
    r = real(complex_field, radius)
    return (
        center.union(complex_field(center.real() + r, center.imag()))
        .union(complex_field(center.real() - r, center.imag()))
        .union(complex_field(center.real(), center.imag() + r))
        .union(complex_field(center.real(), center.imag() - r))
    )


def subset_interior(inner, outer):
    return (
        inner.real().lower() > outer.real().lower()
        and inner.real().upper() < outer.real().upper()
        and inner.imag().lower() > outer.imag().lower()
        and inner.imag().upper() < outer.imag().upper()
    )


def contains_zero(value):
    return (
        value.real().lower() <= 0
        and value.real().upper() >= 0
        and value.imag().lower() <= 0
        and value.imag().upper() >= 0
    )


def certify(candidate, digits):
    center = refine_center(candidate, digits)
    box = with_radius(center, CERTIFY_RADIUS)
    derivative_at_center = center.zetaderiv(2)
    derivative_on_box = box.zetaderiv(2)
    inverse_derivative = 1 / derivative_at_center
    image = (
        center
        - inverse_derivative * center.zetaderiv(1)
        + (1 - inverse_derivative * derivative_on_box) * (box - center)
    )
    if not subset_interior(image, box):
        raise ArithmeticError("Krawczyk image is not inside the zero box")
    if not contains_zero(image.zetaderiv(1)):
        raise ArithmeticError("certified zero ball does not evaluate over zero")
    return image


def check_first_root(root):
    complex_field = root.parent()
    first = complex_field(real(complex_field, OEIS_FIRST_REAL), real(complex_field, OEIS_FIRST_IMAG))
    if not same_root(root, first):
        raise ArithmeticError("first root does not agree with OEIS A356216/A356092")


class RiemannZetaDerivativeZeros(numberdb.Generator):
    table = TABLE
    parameters = ("n",)
    type = "C"
    digits = DIGITS
    rigour = "proven"

    def __init__(self):
        super().__init__()
        self._roots = None

    def roots(self):
        if self._roots is None:
            complex_field = field(self.digits)
            primary = locate_from_grid(PRIMARY_REAL_SEEDS, primary_heights(), complex_field)
            offset = locate_from_grid(OFFSET_REAL_SEEDS, offset_heights(), complex_field)
            require_same_roots(primary, offset)
            if len(primary) != EXPECTED_ROOTS:
                raise ArithmeticError("expected %d roots, found %d" % (EXPECTED_ROOTS, len(primary)))
            check_first_root(primary[0])
            self._roots = primary
        return self._roots

    def enumerate(self):
        for n, _root in enumerate(self.roots(), 1):
            yield {"n": str(n)}

    def value(self, params, digits):
        n = int(params["n"])
        root = self.roots()[n - 1]
        number = certify(root, digits)
        if n == 1:
            return {
                "number": number,
                "comment": "The real and imaginary parts agree with OEIS A356216 and A356092.",
            }
        return number


def main():
    configure_key_from_stdin()
    generator = RiemannZetaDerivativeZeros()
    mode = os.environ.get("NUMBERDB_PUBLISH")
    if "--publish" in sys.argv or mode == "1":
        print(generator.publish(message="certified zeros of zeta prime up to height 200"))
        return
    if "--preview" in sys.argv or mode == "preview":
        print(generator.preview())
        return
    report = generator.verify(sample=None)
    print(report)
    sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
