"""Values of the linear sieve function F(s) -- numberdb.org/T422

This is the upper function in the dimension-one linear sieve normalisation
where

    sF(s) = 2 exp(gamma)       for 0 < s <= 3,
    sf(s) = 0                  for 0 < s <= 2,
    (sF(s))' = f(s - 1)        for s > 3,
    (sf(s))' = F(s - 1)        for s > 2.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The computation uses the method of steps. On each unit interval it expands
A(s)=sF(s) and B(s)=sf(s) in a Taylor series about the midpoint. The delayed
right hand sides are formed by multiplying the previous interval's series by
the Taylor series of 1/s, and the omitted tail is added to the real ball. This
keeps every returned value as a Sage real ball with its own error bound.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


DIGITS = 100
WORKING_GUARD = 64
ORDER = 240
MAX_ARGUMENT = 10
STEP = 100
HALF = QQ(1) / QQ(2)


def _ball_with_error(value, error):
    """Return ``value`` enlarged by the nonnegative ball ``error``."""
    if not error:
        return value
    return value.add_error(error)


class TaylorStepper:
    """Taylor method of steps for the coupled linear-sieve equations."""

    def __init__(self, digits, order=ORDER, max_argument=MAX_ARGUMENT):
        self.digits = digits
        self.order = order
        self.max_argument = max_argument
        self.R = RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))
        self.half = self.R(HALF)
        self.two_euler = 2 * self.R.euler_constant().exp()
        self.A = []
        self.B = []
        self._build()

    def zero(self):
        return self.R(0)

    def constant(self, value):
        return [value] + [self.zero() for _ in range(self.order - 1)]

    def abs_upper(self, value):
        return self.R(value.abs().upper())

    def sup_norm(self, coeffs):
        total = self.zero()
        power = self.R(1)
        for coeff in coeffs:
            total += self.abs_upper(coeff) * power
            power *= self.half
        return total

    def evaluate(self, coeffs, y):
        y = self.R(y)
        total = self.zero()
        for coeff in reversed(coeffs):
            total = total * y + coeff
        return total

    def reciprocal_coeffs(self, base):
        return [
            self.R(((-1) ** n) * QQ(1) / (base ** (n + 1)))
            for n in range(self.order)
        ]

    def reciprocal_tail(self, base):
        ratio = self.R(HALF / base)
        return self.R(QQ(1) / base) * (ratio ** self.order) / (1 - ratio)

    def truncated_product_tail(self, coeffs, reciprocals):
        absolute_coeffs = [self.abs_upper(coeff) for coeff in coeffs]
        absolute_reciprocals = [self.abs_upper(coeff) for coeff in reciprocals]
        powers = [self.R(1)]
        for _ in range(2 * self.order):
            powers.append(powers[-1] * self.half)

        tail = self.zero()
        for i, coeff in enumerate(absolute_coeffs):
            for j in range(max(0, self.order - i), self.order):
                tail += coeff * absolute_reciprocals[j] * powers[i + j]
        return tail

    def divide_by_delayed_argument(self, coeffs, base):
        """Return a series for ``P(y)/(base + y)`` on ``|y| <= 1/2``."""
        reciprocals = self.reciprocal_coeffs(base)
        out = [self.zero() for _ in range(self.order)]
        for n in range(self.order):
            total = self.zero()
            for i in range(n + 1):
                total += coeffs[i] * reciprocals[n - i]
            out[n] = total

        omitted = (
            self.truncated_product_tail(coeffs, reciprocals)
            + self.sup_norm(coeffs) * self.reciprocal_tail(base)
        )
        out[0] = _ball_with_error(out[0], omitted)
        return out

    def integrate_from_left(self, derivative, left_value):
        integrated = [self.zero() for _ in range(self.order)]
        for n in range(self.order - 1):
            integrated[n + 1] = derivative[n] / self.R(n + 1)
        integrated[0] = left_value - self.evaluate(integrated, -HALF)
        return integrated

    def _build(self):
        for interval in range(self.max_argument + 1):
            if interval <= 2:
                self.A.append(self.constant(self.two_euler))
            else:
                left = self.evaluate(self.A[interval - 1], HALF)
                delayed = self.divide_by_delayed_argument(
                    self.B[interval - 1], QQ(interval) - HALF)
                self.A.append(self.integrate_from_left(delayed, left))

            if interval <= 1:
                self.B.append(self.constant(self.zero()))
            else:
                left = self.evaluate(self.B[interval - 1], HALF)
                delayed = self.divide_by_delayed_argument(
                    self.A[interval - 1], QQ(interval) - HALF)
                self.B.append(self.integrate_from_left(delayed, left))

    def interval_for(self, s):
        if s < 0 or s > self.max_argument:
            raise ValueError("s is outside the computed range")
        whole = s.floor()
        if whole > self.max_argument:
            whole = self.max_argument
        return int(whole)

    def A_at(self, s):
        interval = self.interval_for(s)
        centre = QQ(interval) + HALF
        return self.evaluate(self.A[interval], s - centre)

    def B_at(self, s):
        interval = self.interval_for(s)
        centre = QQ(interval) + HALF
        return self.evaluate(self.B[interval], s - centre)

    def F_at(self, s):
        return self.A_at(s) / self.R(s)

    def f_at(self, s):
        return self.B_at(s) / self.R(s)


_SYSTEMS = {}


def system_for(digits):
    if digits not in _SYSTEMS:
        _SYSTEMS[digits] = TaylorStepper(digits)
    return _SYSTEMS[digits]


def grid_value(n):
    return QQ(n) / QQ(STEP)


class LinearSieveF(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE") or "T422"
    parameters = ("s",)
    type = "R"
    digits = DIGITS
    rigour = "proven"

    def enumerate(self):
        for n in range(STEP, MAX_ARGUMENT * STEP + 1):
            yield {"s": str(grid_value(n))}

    def value(self, params, digits):
        s = QQ(params["s"])
        if s <= 0 or s > MAX_ARGUMENT:
            raise ValueError("s must satisfy 0 < s <= %d" % MAX_ARGUMENT)
        return system_for(digits).F_at(s)


if __name__ == "__main__":
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") == "1":
        os.environ["NUMBERDB_API_KEY"] = sys.stdin.read().strip()
    generator = LinearSieveF()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(generator.publish(message="linear sieve F values"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
