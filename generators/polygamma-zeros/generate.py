"""Zeros of the polygamma functions -- numberdb.org/TBD

The k-th largest real zero of psi^(n), for even n.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**These digits are proven.** Every value is returned as a ball whose radius
carries the error, and the ball is only formed after psi^(n) has been evaluated
in ball arithmetic at both ends of a rational interval and found to have
strictly opposite signs there. A zero lies between them by the intermediate
value theorem, and the digits written are the ones that enclosure supports.

Unlike the Airy and Bessel tables next door, the *index* is proven too. Those
say they cannot establish that a value is the n-th zero rather than a
neighbour. Here it follows from monotonicity: psi^(n+1) has no real zeros when
n is even -- see `_no_zeros_for_odd_order` below -- so psi^(n) is strictly
monotonic between consecutive poles and has exactly one zero in each gap.
Counting the gaps counts the zeros.
"""

import sys

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.integer import Integer
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


def factorial(n):
    """n! as an exact Sage integer.

    Not `sage.functions.other.factorial`: importing it reaches into the
    symbolic ring, which the narrow imports here deliberately do not
    initialise, and the import fails with a circular-import error rather than
    anything that names the cause.
    """
    return Integer(n).factorial()

#: Working precision in bits for the ball arithmetic, and for the floating
#: search that proposes a bracket. Written down rather than derived: the first
#: must comfortably exceed the digits written, and the second is only a guess
#: that the ball check then has to confirm, so it costs nothing to be generous.
WORKING_BITS = 640

#: Orders and indices. psi^(n) has real zeros only for even n, so the odd
#: orders are not holes in this table -- there is nothing there to list.
ORDERS = 40
ZEROS = 50


def _no_zeros_for_odd_order():
    """Why only even n appears, kept here because the range depends on it.

    psi^(n)(x) = (-1)^(n+1) n! sum_{j>=0} (x+j)^(-n-1). For odd n the exponent
    n+1 is even, so every term has the same sign and the sum cannot vanish.
    For even n the terms alternate with the sign of x+j and zeros appear, one
    between each pair of consecutive poles.
    """


def polygamma(n, x, bits=WORKING_BITS):
    """psi^(n)(x) as a real ball, for rational x that is not a pole.

    Shifted onto the positive axis by psi^(n)(x) = psi^(n)(x+1)
    - (-1)^n n! x^(-n-1), where psi^(n)(y) = (-1)^(n+1) n! zeta(n+1, y) for
    n >= 1 and arb's own digamma for n = 0.

    Two traps, both of which produced a wrong answer here before they were
    understood. `zeta(1, .)` is the pole, so the zeta formula does not reach
    n = 0. And arb takes a power as exp(y log x), so a negative base with a
    negative exponent is a nan -- which then *overlaps every interval*, making
    a check pass while establishing nothing. Hence the reciprocal of a
    positive power below, and hence `_finite` at the end.
    """
    R = RealBallField(bits)
    C = ComplexBallField(bits)
    x = QQ(x)
    if x.denominator() == 1 and x <= 0:
        raise ValueError('psi^(%d) has a pole at %s' % (n, x))
    shift = R(0)
    y = x
    while y <= 0:
        shift -= R((-1) ** n) * factorial(n) / (R(y) ** (n + 1))
        y = y + 1
    if n == 0:
        base = R(y).psi()
    else:
        base = ((-1) ** (n + 1) * factorial(n) * C(n + 1).zeta(C(y))).real()
    return _finite(base + shift)


def _finite(ball):
    """A ball that pins something down, or a refusal.

    A nan ball compares true against everything, so letting one out of here
    turns every later check into a formality.
    """
    if not ball.is_finite():
        raise ArithmeticError('polygamma returned a ball that is not finite')
    return ball


def gap(n, k):
    """The open interval between poles holding the k-th largest zero.

    Returned as ``(low, high)`` with ``None`` for the unbounded side.

    For even n >= 2 every real zero is negative and the k-th largest lies in
    (-k, -k+1). psi itself has one more: it is increasing on (0, infinity)
    from -infinity to +infinity, so it has a zero there too, and that zero --
    1.4616... , the point where Gamma is smallest on the positive reals -- is
    the largest. So n = 0 is offset by one.
    """
    if n == 0:
        if k == 1:
            return (QQ(0), None)
        return (QQ(-(k - 1)), QQ(-(k - 2)))
    return (QQ(-k), QQ(-k + 1))


def _bracket(n, k):
    """A rational interval in which psi^(n) provably changes sign."""
    low, high = gap(n, k)
    if high is None:
        #Walk outwards until the sign changes; psi is negative just above 0.
        a, b = QQ(1), QQ(2)
        while not _opposite(n, a, b):
            b = b * 2
            if b > 2 ** 20:
                raise ArithmeticError('no sign change found above %s' % a)
        return a, b
    #Closed intervals would sit on the poles, so come in from both ends and
    #keep coming in until the signs disagree.
    step = QQ(1) / 4
    while step > QQ(1) / 2 ** 60:
        a, b = low + step, high - step
        if a < b and _opposite(n, a, b):
            return a, b
        step = step / 2
    raise ArithmeticError('no sign change found in (%s, %s)' % (low, high))


def _opposite(n, a, b):
    """Whether psi^(n) has strictly opposite signs at a and b."""
    fa, fb = polygamma(n, a), polygamma(n, b)
    return bool(fa < 0 < fb) or bool(fb < 0 < fa)


def zero(n, k, digits):
    """The k-th largest real zero of psi^(n), as a ball that encloses it.

    Bisection on a bracket whose endpoints have been checked in ball
    arithmetic, so every step preserves a proven sign change and the returned
    ball is an enclosure rather than an estimate.

    Newton was tried first and is not used: it converges much faster, but when
    it wanders -- which it did from k = 13, where the zero sits close to the
    pole -- there is nothing to fall back to, because a widening search around
    a bad guess would have to grow by a factor of 10^40 before it reached the
    root. Bisection cannot wander. The cost is about 350 evaluations an entry
    and it is paid once.
    """
    a, b = _bracket(n, k)
    R = RealBallField(WORKING_BITS)
    rising = bool(polygamma(n, a) < 0)
    target = QQ(10) ** (-(digits + 10))
    while b - a > target:
        middle = (a + b) / 2
        value = polygamma(n, middle)
        if value.contains_zero():
            #The working precision cannot resolve this point. Widening further
            #would be guessing, so stop here and let the enclosure say so.
            break
        if bool(value < 0) == rising:
            a = middle
        else:
            b = middle
    return R(a).union(R(b))


class PolygammaZeros(numberdb.Generator):

    table = 'TBD'
    parameters = ('n', 'k')
    type = 'R'
    digits = 100
    rigour = 'proven'

    def enumerate(self, orders=ORDERS, zeros=ZEROS):
        for n in range(0, orders + 1, 2):
            for k in range(1, zeros + 1):
                yield {'n': n, 'k': k}

    def value(self, params, digits):
        return zero(params['n'], params['k'], digits)


if __name__ == '__main__':
    generator = PolygammaZeros()
    if '--publish' in sys.argv:
        print(generator.publish(message='zeros of the polygamma functions'))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
