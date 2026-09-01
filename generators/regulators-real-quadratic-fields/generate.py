"""Regulators of real quadratic fields -- numberdb.org/T131

    R_K = log eps_K,    K = Q(sqrt D),

for every fundamental discriminant D with 1 < D <= 1000, where eps_K > 1 is
the fundamental unit of the ring of integers of K -- of the maximal order, so
eps_5 is the golden ratio (1 + sqrt 5)/2 and not 2 + sqrt 5, which is its cube.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**These digits are proven.** The unit is taken exactly from Sage's unit group
with proof=True, as a pair of integers (a, b) with eps_K = (a + b sqrt d)/2 and
d the squarefree part of D; then a, b and sqrt d are real balls and the
logarithm is arb's, so the written digits are the ones the ball supports.
`K.regulator()` is not used: it is a 53-bit float that documents no accuracy.

**Every unit is checked before its logarithm is taken**, against a computation
sharing no code with Sage's unit group: the continued fraction of sqrt d,
which gives the smallest unit of the order Z[sqrt d] by integer arithmetic
alone. That unit must be eps_K itself or, when eps_K has half-integral
coordinates, eps_K^3 -- and a^2 - d b^2 must be +-4. A unit failing either is
an error rather than an entry.

Outside the generator, when this was written, all 302 units were also compared
with OEIS A014000 / A014046 / A014077 (the coordinates and the norm of the
fundamental unit, taken there from Cohen's tables), eight regulators with the
values on their LMFDB pages, and every regulator with the residue table T128
through the class number formula kappa_D = 2 h_K R_K / sqrt D, with the
controls that must fail failing.

**Two conventions had to be settled**, and both are stated on the table. The
unit is that of the maximal order, normalised to exceed 1 (Sage may return
-eps, 1/eps or -1/eps), and the regulator is log eps_K with no factor 2 -- the
LMFDB convention, and the one under which the class number formula reads
kappa_D = 2 h_K R_K / sqrt D.
"""

import sys

import numberdb.sage as numberdb
from sage.arith.misc import is_squarefree
from sage.rings.integer_ring import ZZ
from sage.rings.number_field.number_field import QuadraticField
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField

#: Bits of working precision beyond what the written digits need. Measured
#: over the whole table at 100 digits: the worst ball (D = 889, the largest
#: unit in range) has radius 5.5e-118 with this guard, which supports 117
#: digits; the guard costs nothing and the margin is what it buys.
WORKING_GUARD = 64

#: Every real fundamental discriminant up to here is listed: 302 of them, the
#: same enumeration as the residue table T128. The entries do not grow with D
#: (the longest unit in range has 20-digit coordinates), so the bound is a
#: choice about what somebody looks up rather than about size.
BOUND = 1000


def is_fundamental_discriminant(D):
    """D = 1 mod 4 squarefree, or D = 4m with m = 2, 3 mod 4 squarefree; not 1."""
    D = ZZ(D)
    if D == 0 or D == 1:
        return False
    if D % 4 == 1:
        return is_squarefree(D)
    if D % 4 == 0:
        m = D // 4
        return m % 4 in (2, 3) and is_squarefree(m)
    return False


def real_fundamental_discriminants(bound):
    return [ZZ(D) for D in range(2, bound + 1) if is_fundamental_discriminant(D)]


def squarefree_part(D):
    """d with Q(sqrt D) = Q(sqrt d): D itself, or D/4."""
    D = ZZ(D)
    return D if D % 4 == 1 else D // 4


def fundamental_unit(D):
    """(a, b) integers with eps_K = (a + b sqrt d)/2 > 1, from Sage's unit group.

    `K.units()` may return any of eps, -eps, 1/eps, -1/eps; the one whose real
    embedding exceeds 1 is chosen. The coordinates come back in the power
    basis (1, sqrt D) and are rewritten over sqrt d, so that eps_5 reads
    (1 + sqrt 5)/2 and eps_8 reads (2 + 2 sqrt 2)/2 = 1 + sqrt 2.
    """
    D = ZZ(D)
    K = QuadraticField(D, 'w')
    units = K.units(proof=True)
    if len(units) != 1:
        raise ArithmeticError('expected one fundamental unit for D = %s' % D)
    u = units[0]
    R = RealBallField(64)
    chosen = None
    for candidate in (u, -u, 1 / u, -1 / u):
        c0, c1 = candidate.vector()                   # coordinates in (1, sqrt D)
        if R(c0) + R(c1) * R(D).sqrt() > 1:
            chosen = (QQ(c0), QQ(c1))
    if chosen is None:
        raise ArithmeticError('no conjugate of the unit exceeds 1 for D = %s' % D)
    c0, c1 = chosen
    d = squarefree_part(D)
    a, b = 2 * c0, 2 * c1 * ZZ(D // d).sqrt()          # D/d is 1 or 4
    if a.denominator() != 1 or b.denominator() != 1:
        raise ArithmeticError('unit coordinates are not half-integral for D = %s' % D)
    return ZZ(a), ZZ(b)


def pell_unit(d):
    """The smallest unit x + y sqrt d > 1 of Z[sqrt d], as (x, y).

    From the continued fraction of sqrt d: the convergents p/q are run through
    until p^2 - d q^2 = +-1, which the first one in a period does. Integer
    arithmetic only; shares nothing with `fundamental_unit`.
    """
    d = ZZ(d)
    a0 = d.isqrt()
    m, q, a = ZZ(0), ZZ(1), a0
    p_prev, p = ZZ(1), a0
    q_prev, q_cur = ZZ(0), ZZ(1)
    while p * p - d * q_cur * q_cur not in (1, -1):
        m = q * a - m
        q = (d - m * m) // q
        a = (a0 + m) // q
        p_prev, p = p, a * p + p_prev
        q_prev, q_cur = q_cur, a * q_cur + q_prev
    return p, q_cur


def checked_unit(D):
    """(a, b, d, norm) for eps_K, or a refusal naming both computations.

    eps_K generates the units of O_K and x + y sqrt d those of Z[sqrt d], an
    order of index 1 or 2 in O_K, so the unit index divides 3: the Pell unit
    is eps_K, or eps_K^3 when eps_K has half-integral coordinates.
    """
    D = ZZ(D)
    a, b = fundamental_unit(D)
    d = squarefree_part(D)
    norm = (a * a - d * b * b) / QQ(4)
    if norm not in (1, -1):
        raise ArithmeticError('D = %s: (%s + %s sqrt %s)/2 has norm %s, not a unit'
                              % (D, a, b, d, norm))
    x, y = pell_unit(d)
    #((a + b s)/2)^3 with s = sqrt d, s^2 = d.
    cube = ((a ** 3 + 3 * a * b * b * d) / QQ(8), (3 * a * a * b + b ** 3 * d) / QQ(8))
    if (a, b) != (2 * x, 2 * y) and cube != (x, y):
        raise ArithmeticError(
            'D = %s: the unit group gives (%s + %s sqrt %s)/2 and the continued '
            'fraction of sqrt %s gives %s + %s sqrt %s; neither is right until '
            'the disagreement has a cause' % (D, a, b, d, d, x, y, d))
    return a, b, d, ZZ(norm)


def regulator(a, b, d, bits):
    """log((a + b sqrt d)/2) as a real ball."""
    R = RealBallField(bits)
    return _finite(((R(a) + R(b) * R(d).sqrt()) / 2).log())


def _finite(ball):
    if not ball.is_finite():
        raise ArithmeticError('the logarithm returned a ball that is not finite')
    return ball


def unit_latex(a, b, d):
    """(a + b sqrt d)/2 written the way a person would."""
    root = r'\sqrt{%d}' % d
    if a % 2 == 0 and b % 2 == 0:
        a, b = a // 2, b // 2
        return '%d+%s%s' % (a, '' if b == 1 else str(b), root)
    return '(%d+%s%s)/2' % (a, '' if b == 1 else str(b), root)


#: Closed forms a reader would recognise, for the entries that have one.
NAMED = {
    5: r'$R_K=\log\varphi$, the logarithm of the golden ratio',
    8: r'$R_K=\log(1+\sqrt{2})=\operatorname{arsinh}(1)$',
    12: r'$R_K=\log(2+\sqrt{3})=\operatorname{arcosh}(2)$',
}


def comment(D, a, b, d, norm):
    """The field, since D = 12 is Q(sqrt 3); the unit exactly; its norm."""
    text = r'$\mathbb{Q}(\sqrt{%d})$: $\varepsilon_K=%s$, $N(\varepsilon_K)=%s$' % (
        d, unit_latex(a, b, d), '-1' if norm == -1 else '1')
    if int(D) in NAMED:
        text += '; ' + NAMED[int(D)]
    return text


class QuadraticRegulators(numberdb.Generator):

    table = 'T131'
    parameters = ('D',)
    type = 'R'
    digits = 100
    rigour = 'proven'

    def enumerate(self, bound=BOUND):
        for D in real_fundamental_discriminants(bound):
            yield {'D': int(D)}

    def value(self, params, digits):
        D = ZZ(params['D'])
        if not (D > 1 and is_fundamental_discriminant(D)):
            raise ValueError('D must be a real fundamental discriminant, not %s' % D)
        a, b, d, norm = checked_unit(D)
        bits = numberdb.bits(digits, losing=WORKING_GUARD)
        return {'number': regulator(a, b, d, bits),
                'comment': comment(D, a, b, d, norm)}


if __name__ == '__main__':
    generator = QuadraticRegulators()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='regulators of real quadratic fields with D <= %d: log of '
                    'the fundamental unit of the maximal order in ball '
                    'arithmetic, each unit checked against the continued '
                    'fraction of sqrt d' % BOUND))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
