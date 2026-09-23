"""Values of the odd Mathieu functions se_n(z,q) -- numberdb.org/T438

This table stores the DLMF-normalised odd Mathieu functions
se_n(z,q), with z recorded by the rational parameter z/pi.

Run it with SageMath:

    $ sage -pip install numberdb mpmath          # once
    $ sage -python generate.py                   # check the table
    $ sage -python generate.py --publish         # fill the draft, with NUMBERDB_API_KEY set

For this repository's unattended build wrapper:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 agents/sage.sh generate.py

The computation uses the sine Fourier basis.  In that basis
-d^2/dz^2 + 2q cos(2z) is a tridiagonal matrix with off-diagonal entries q;
the k=1 sine row has the extra diagonal contribution -q from sin(-z)=-sin(z).
The eigenvector is normalised so that the sum of the squared sine
coefficients is 1, which gives integral_0^(2*pi) se_n(x,q)^2 dx = pi.
"""

import os
import sys
from fractions import Fraction
from functools import lru_cache

import mpmath
import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ


Q_VALUES = ("1", "2", "5", "10")
Z_STEPS = range(19)
Z_DENOMINATOR = QQ(36)

# The measured pair.  Across the full proposed grid, comparing 60 digits with
# 26 sine terms against 90 digits with 34 sine terms left at least 43 common
# significant digits.  The table writes 30.
WORKING_DIGITS = (60, 90)
TERMS = {60: 26, 90: 34}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _rational(text):
    value = Fraction(str(text))
    return QQ(value.numerator) / QQ(value.denominator)


def _mpq(text):
    value = Fraction(str(text))
    return mpmath.mpf(value.numerator) / value.denominator


def _basis(n, terms):
    start = 1 if n % 2 else 2
    return tuple(start + 2 * i for i in range(terms))


def _eigen_index(n):
    return (n - 1) // 2 if n % 2 else n // 2 - 1


@lru_cache(maxsize=None)
def _coefficients(n, q_text, working_digits):
    """Sine coefficients for se_n(z,q), at one working precision."""
    terms = TERMS[int(working_digits)]
    mpmath.mp.dps = int(working_digits)
    q = _mpq(q_text)
    ks = _basis(int(n), terms)
    matrix = mpmath.matrix(terms)

    for row, k in enumerate(ks):
        matrix[row, row] = mpmath.mpf(k * k)
    if int(n) % 2:
        matrix[0, 0] -= q
    for row in range(terms - 1):
        matrix[row, row + 1] = q
        matrix[row + 1, row] = q

    _values, vectors = mpmath.eigsy(matrix)
    index = _eigen_index(int(n))
    coeffs = [vectors[row, index] for row in range(terms)]
    norm = mpmath.sqrt(mpmath.fsum(c * c for c in coeffs))
    coeffs = [c / norm for c in coeffs]
    if coeffs[index] < 0:
        coeffs = [-c for c in coeffs]
    return ks, tuple(coeffs)


def _is_exact_zero(n, z_text):
    z = _rational(z_text)
    return z == 0 or (int(n) % 2 == 0 and z == QQ(1) / QQ(2))


def _se_text(n, q_text, z_text, working_digits):
    """A decimal string for one Mathieu se value."""
    if _is_exact_zero(n, z_text):
        return "0"
    mpmath.mp.dps = int(working_digits)
    ks, coeffs = _coefficients(int(n), str(q_text), int(working_digits))
    z = mpmath.pi * _mpq(z_text)
    value = mpmath.fsum(
        coefficient * mpmath.sin(k * z)
        for k, coefficient in zip(ks, coeffs)
    )
    return mpmath.nstr(value, int(working_digits), strip_zeros=False)


def _control_zero_q():
    """Check the q=0 convention against sin(nz)."""
    mpmath.mp.dps = 50
    for n in range(1, 7):
        for step in Z_STEPS:
            z_text = str(QQ(step) / Z_DENOMINATOR)
            got = mpmath.mpf(_se_text(n, "0", z_text, 60))
            want = mpmath.sin(n * mpmath.pi * _mpq(z_text))
            if abs(got - want) > mpmath.mpf("1e-45"):
                raise ArithmeticError(
                    "q=0 control failed for n=%d, z=%s: %s != %s"
                    % (n, z_text, got, want)
                )


class MathieuOddValues(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE") or "T438"
    parameters = ("n", "q", "z")
    type = "R"
    digits = 30
    rigour = "heuristic (agreement-checked)"
    files = ("generate.py",)

    def enumerate(self):
        for n in range(1, 7):
            for q in Q_VALUES:
                for step in Z_STEPS:
                    yield {
                        "n": n,
                        "q": q,
                        "z": str(QQ(step) / Z_DENOMINATOR),
                    }

    def value(self, params, digits):
        n = int(params["n"])
        q_text = str(params["q"])
        z_text = str(params["z"])
        if _is_exact_zero(n, z_text):
            return ZZ(0)
        return numberdb.agreeing(
            lambda working: _se_text(n, q_text, z_text, working),
            at=WORKING_DIGITS,
        )


if __name__ == "__main__":
    _key_from_stdin()
    _control_zero_q()
    generator = MathieuOddValues()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="odd Mathieu function values from Fourier sine matrices"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
