"""Division polynomials psi_n of y^2 = x^3 + A*x + B -- numberdb.org/T344.

The table stores the full division polynomial psi_n in Z[x,y,A,B]. For even n
this includes the factor psi_2 = 2*y, rather than the x-only quotient
psi_n/psi_2.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

On the NumberDB build machine, where arguments are not passed through
agents/sage.sh, publish with:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
          agents/sage.sh generate.py

The recurrence is evaluated in the coordinate ring of the universal short
Weierstrass curve. Internally a polynomial is represented as u + y*v with
u,v in Z[x,A,B], so reducing by y^2 = x^3 + A*x + B is explicit and does not
depend on Sage quotient-ring machinery.

The values are exact polynomials over ZZ. There is no precision to choose and
no rounding.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.libs.pari import pari
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing


#: Measured before filling T344: n = 1..7 gives seven entries, psi_7 is 1109
#: characters written out, and the entries block is 2.3 KB. The next entry,
#: psi_8, is 2043 characters, past the range where a polynomial entry stays
#: readily readable.
UP_TO = 7

_BASE = PolynomialRing(ZZ, names=("x", "A", "B"))
_x, _A, _B = _BASE.gens()
_CURVE_POLYNOMIAL = _x**3 + _A * _x + _B

_OUT = PolynomialRing(ZZ, names=("x", "y", "A", "B"))
_ox, _oy, _oA, _oB = _OUT.gens()

_UNIVARIATE = PolynomialRing(ZZ, "x")
_ux = _UNIVARIATE.gen()

_ZERO = _BASE.zero()
_PSI = {}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def _pair(u=0, v=0):
    """Represent u + y*v in the coordinate ring."""
    return _BASE(u), _BASE(v)


def _sub(left, right):
    return left[0] - right[0], left[1] - right[1]


def _mul(left, right):
    """Multiply in Z[x,A,B,y] / (y^2 - x^3 - A*x - B)."""
    return (
        left[0] * right[0] + _CURVE_POLYNOMIAL * left[1] * right[1],
        left[0] * right[1] + left[1] * right[0],
    )


def _pow_pair(value, exponent):
    result = _pair(1, 0)
    while exponent:
        if exponent & 1:
            result = _mul(result, value)
        value = _mul(value, value)
        exponent >>= 1
    return result


def _half_coeff(coeff):
    coeff = ZZ(coeff)
    if coeff % ZZ(2) != 0:
        raise ArithmeticError("coefficient %s is not divisible by 2" % (coeff,))
    return coeff // ZZ(2)


def _halve(poly):
    return _BASE({exps: _half_coeff(coeff)
                  for exps, coeff in poly.dict().items()})


def _divide_by_curve_polynomial(poly):
    quotient, remainder = poly.quo_rem(_CURVE_POLYNOMIAL)
    if remainder != 0:
        raise ArithmeticError("polynomial is not divisible by y^2")
    return quotient


def _divide_by_psi2(value):
    """Divide u + y*v by 2*y in the coordinate ring."""
    return (
        _halve(value[1]),
        _halve(_divide_by_curve_polynomial(value[0])),
    )


def _initial_values():
    return {
        0: _pair(0, 0),
        1: _pair(1, 0),
        2: _pair(0, 2),
        3: _pair(3 * _x**4 + 6 * _A * _x**2 + 12 * _B * _x - _A**2, 0),
        4: _pair(
            0,
            4 * (_x**6 + 5 * _A * _x**4 + 20 * _B * _x**3
                 - 5 * _A**2 * _x**2 - 4 * _A * _B * _x
                 - _A**3 - 8 * _B**2),
        ),
    }


def division_polynomial_pair(n):
    """Return psi_n as (u, v), representing u + y*v."""
    if not _PSI:
        _PSI.update(_initial_values())
    if n in _PSI:
        return _PSI[n]

    if n % 2:
        m = (n - 1) // 2
        value = _sub(
            _mul(division_polynomial_pair(m + 2),
                 _pow_pair(division_polynomial_pair(m), 3)),
            _mul(division_polynomial_pair(m - 1),
                 _pow_pair(division_polynomial_pair(m + 1), 3)),
        )
    else:
        m = n // 2
        bracket = _sub(
            _mul(division_polynomial_pair(m + 2),
                 _pow_pair(division_polynomial_pair(m - 1), 2)),
            _mul(division_polynomial_pair(m - 2),
                 _pow_pair(division_polynomial_pair(m + 1), 2)),
        )
        value = _divide_by_psi2(_mul(division_polynomial_pair(m), bracket))

    _PSI[n] = value
    return value


def _embed_base(poly):
    """Embed a polynomial in x,A,B into the output ring x,y,A,B."""
    result = _OUT.zero()
    for (x_exp, a_exp, b_exp), coeff in poly.dict().items():
        term = _OUT(coeff)
        if x_exp:
            term *= _ox**x_exp
        if a_exp:
            term *= _oA**a_exp
        if b_exp:
            term *= _oB**b_exp
        result += term
    return result


def division_polynomial(n):
    """Return psi_n as an element of Z[x,y,A,B]."""
    u, v = division_polynomial_pair(n)
    return _embed_base(u) + _oy * _embed_base(v)


def _specialise(poly, a, b):
    return _UNIVARIATE(poly.subs({_x: _ux, _A: ZZ(a), _B: ZZ(b)}))


def _pari_division_polynomial(a, b, n):
    curve = pari("ellinit([0,0,0,%s,%s])" % (a, b))
    return _UNIVARIATE(str(pari("elldivpol")(curve, int(n))))


def _pari_convention(pair, a, b, n):
    u, v = pair
    if n % 2:
        return _specialise(u, a, b)
    curve_polynomial = _ux**3 + ZZ(a) * _ux + ZZ(b)
    return 2 * curve_polynomial * _specialise(v, a, b)


def check_identities(up_to=UP_TO):
    """Check degrees, leading coefficients and PARI/GP specialisations."""
    samples = [(-1, 0), (0, 1), (-7, 10), (2, 3), (-3, 5)]
    for a, b in samples:
        if 4 * ZZ(a)**3 + 27 * ZZ(b)**2 == 0:
            raise AssertionError("singular sample curve")
        for n in range(1, up_to + 1):
            pair = division_polynomial_pair(n)
            ours = _pari_convention(pair, a, b, n)
            theirs = _pari_division_polynomial(a, b, n)
            if ours != theirs:
                raise AssertionError(
                    "PARI comparison failed at A=%s, B=%s, n=%s"
                    % (a, b, n))

    for n in range(1, up_to + 1):
        u, v = division_polynomial_pair(n)
        poly = u if n % 2 else v
        expected_degree = ((n * n - 1) // 2 if n % 2
                           else (n * n - 4) // 2)
        if poly.degree(_x) != expected_degree:
            raise AssertionError("degree check failed at n=%s" % (n,))
        leading = poly.coefficient({_x: expected_degree})
        if leading != n:
            raise AssertionError("leading coefficient check failed at n=%s"
                                 % (n,))


class ShortWeierstrassDivisionPolynomials(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T344")
    parameters = ("n",)
    type = "Z[]"
    rigour = "exact"

    def enumerate(self, up_to=UP_TO):
        for n in range(1, up_to + 1):
            yield {"n": str(n)}

    def value(self, params, digits):
        return division_polynomial(int(ZZ(params["n"])))


def main():
    _key_from_stdin()
    check_identities()
    generator = ShortWeierstrassDivisionPolynomials()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="division polynomials for y^2=x^3+A*x+B, n = 1..%d"
                    % (UP_TO,)))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
