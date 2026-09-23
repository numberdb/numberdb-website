"""Values of the Jacobi elliptic function sn(u|m) -- numberdb.org/T424.

The table stores real values of the Jacobi elliptic sine with the elliptic
parameter m, not the modulus k. Thus sn(u, k) = sn(u | k^2).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

On the NumberDB build machine, where arguments are not passed through
agents/sage.sh, publish with:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
          agents/sage.sh generate.py

The family convention from numberdb-data#191 is used here: m runs through
1/10, 1/4, 1/2, 3/4 and 9/10, and u runs over the exact two-decimal grid
j/100 for 1 <= j <= 200.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.rational_field import QQ


TABLE = os.environ.get("NUMBERDB_TABLE") or "T424"
DIGITS = 100
WORKING_GUARD = 64
CHECK_GUARD = 192

M_VALUES = (
    QQ(1) / QQ(10),
    QQ(1) / QQ(4),
    QQ(1) / QQ(2),
    QQ(3) / QQ(4),
    QQ(9) / QQ(10),
)


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def _field(digits, guard=WORKING_GUARD):
    return ComplexBallField(numberdb.bits(digits, losing=guard))


def _coerce(field, value):
    parent = getattr(value, "parent", None)
    if callable(parent):
        return field(value)
    try:
        return field(QQ(value))
    except (TypeError, ValueError):
        return field(value)


def _theta_quotients(u, m, digits, guard=WORKING_GUARD):
    field = _field(digits, guard)
    u = _coerce(field, u)
    m = _coerce(field, m)
    elliptic_k = m.elliptic_k()
    complementary_k = (1 - m).elliptic_k()
    tau = field.gen(0) * complementary_k / elliptic_k
    # Sage's ComplexBall.jacobi_theta uses theta(pi*z, tau), so the
    # DLMF theta argument zeta = pi*u/(2*K) is passed as u/(2*K).
    zeta = u / (2 * elliptic_k)

    theta1, theta2, theta3, theta4 = zeta.jacobi_theta(tau)
    _, zero_theta2, zero_theta3, zero_theta4 = field(0).jacobi_theta(tau)
    sn = zero_theta3 / zero_theta2 * theta1 / theta4
    cn = zero_theta4 / zero_theta2 * theta2 / theta4
    dn = zero_theta4 / zero_theta3 * theta3 / theta4
    return sn, cn, dn


def _sn_ball(u, m, digits, guard=WORKING_GUARD):
    value, _, _ = _theta_quotients(u, m, digits, guard)

    if not (value.real().is_finite() and value.imag().is_finite()):
        raise ArithmeticError("sn(%s | %s) produced a non-finite ball: %s"
                              % (u, m, value))
    if not value.imag().contains_zero():
        raise ArithmeticError("sn(%s | %s) came back with non-real part: %s"
                              % (u, m, value.imag()))
    return value.real()


def _overlaps(left, right):
    return (left - right).contains_zero()


def _contains_zero(value):
    return value.contains_zero()


def _asin_ball(value):
    field = value.parent()
    i = field.gen(0)
    return -i * (i * value + (1 - value ** 2).sqrt()).log()


def _check_symmetry():
    for m in M_VALUES:
        field = _field(DIGITS, CHECK_GUARD)
        k = field(m).elliptic_k().real()
        for u in (QQ(1) / QQ(100), QQ(1) / QQ(2), QQ(123) / QQ(100), QQ(2)):
            value = _sn_ball(u, m, DIGITS, CHECK_GUARD)
            odd = _sn_ball(-u, m, DIGITS, CHECK_GUARD)
            if not _contains_zero(value + odd):
                raise AssertionError("oddness failed at u=%s, m=%s" % (u, m))
            reflected = _sn_ball(2 * k - u, m, DIGITS, CHECK_GUARD)
            if not _overlaps(value, reflected):
                raise AssertionError("2K-u symmetry failed at u=%s, m=%s" % (u, m))
            period = _sn_ball(u + 4 * k, m, DIGITS, CHECK_GUARD)
            if not _overlaps(value, period):
                raise AssertionError("4K periodicity failed at u=%s, m=%s" % (u, m))


def _check_quadratic_identities():
    for m in M_VALUES:
        for u in (QQ(1) / QQ(100), QQ(1) / QQ(2), QQ(123) / QQ(100), QQ(2)):
            field = _field(DIGITS, CHECK_GUARD)
            m_ball = field(m)
            sn, cn, dn = _theta_quotients(u, m, DIGITS, CHECK_GUARD)
            sn = sn.real()
            cn = cn.real()
            dn = dn.real()
            if not _contains_zero(sn ** 2 + cn ** 2 - 1):
                raise AssertionError(
                    "sn^2+cn^2 failed at u=%s, m=%s" % (u, m))
            if not _contains_zero(dn ** 2 + m_ball.real() * sn ** 2 - 1):
                raise AssertionError(
                    "dn^2+m sn^2 failed at u=%s, m=%s" % (u, m))


def _check_inverse_integral():
    for m in M_VALUES:
        field = _field(DIGITS, CHECK_GUARD)
        for u in (QQ(1) / QQ(100), QQ(1) / QQ(2), QQ(123) / QQ(100)):
            value = field(_sn_ball(u, m, DIGITS, CHECK_GUARD))
            phi = _asin_ball(value)
            recovered = phi.elliptic_f(field(m))
            if not _contains_zero(recovered.real() - field(u).real()):
                raise AssertionError(
                    "inverse integral failed at u=%s, m=%s" % (u, m))
            if not recovered.imag().contains_zero():
                raise AssertionError(
                    "inverse integral was not real at u=%s, m=%s" % (u, m))


def _check_mpmath():
    try:
        import mpmath
    except ImportError:
        print("mpmath not available; skipped independent mpmath check")
        return
    mpmath.mp.dps = 80
    samples = (
        (QQ(1) / QQ(100), QQ(1) / QQ(2)),
        (QQ(1) / QQ(2), QQ(1) / QQ(2)),
        (QQ(123) / QQ(100), QQ(9) / QQ(10)),
        (QQ(2), QQ(1) / QQ(10)),
    )
    for u, m in samples:
        computed = _sn_ball(u, m, DIGITS, CHECK_GUARD)
        u_mp = mpmath.mpf(str(u.numerator())) / mpmath.mpf(str(u.denominator()))
        m_mp = mpmath.mpf(str(m.numerator())) / mpmath.mpf(str(m.denominator()))
        expected = mpmath.ellipfun("sn", u_mp, m=m_mp)
        expected_ball = _field(DIGITS, CHECK_GUARD)(str(expected)).real()
        expected_ball = expected_ball.add_error(QQ(1) / QQ(10) ** 70)
        if not _overlaps(computed, expected_ball):
            raise AssertionError("mpmath check failed at u=%s, m=%s" % (u, m))


def check_identities():
    _check_symmetry()
    _check_quadratic_identities()
    _check_inverse_integral()
    _check_mpmath()


class JacobiSnValues(numberdb.Generator):

    table = TABLE
    parameters = ("m", "u")
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self):
        for m in M_VALUES:
            for j in range(1, 201):
                yield {"m": str(m), "u": str(QQ(j) / QQ(100))}

    def value(self, params, digits):
        return _sn_ball(QQ(params["u"]), QQ(params["m"]), digits)


def main():
    _key_from_stdin()
    check_identities()
    generator = JacobiSnValues()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message="values of Jacobi sn in ball arithmetic"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
