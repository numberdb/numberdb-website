"""Mahler measures of 1 + x_1 + ... + x_{n-1} -- numberdb.org/T283.

    mu_n = log 2 - gamma - int_0^1 (J_0(x)^n - 1)/x dx - int_1^oo J_0(x)^n/x dx

Run it:

    $ pip install numberdb mpmath        # once
    $ python3 generate.py                # check the table against this code
    $ python3 generate.py --publish      # send it, with NUMBERDB_API_KEY set

The table held four values when this was written: n = 3 and 4 from Smyth's
closed forms, n = 5 and 6 from conjectural Rodriguez Villegas eta-integrals.
That range is bibliographic and not a limit of what can be computed: the
Bessel integral above, from Borwein, Straub, Wan and Zudilin, holds for every
n >= 3 and needs no closed form. This generator uses it to carry the table
further.

## Why the integral is taken between the zeros of J_0

`mp.quadosc(..., period=2*pi)` stalls at about sixteen correct digits however
much working precision it is given, because the zeros of J_0 are not spaced by
2*pi: they approach spacing pi. Integrating between consecutive zeros and
accelerating the resulting series instead reaches the working precision: 50
correct digits for n = 3 against Smyth's value.

The acceleration is Richardson and Shanks, and deliberately not Euler-Maclaurin.
`nsum`'s Euler-Maclaurin step treats the summand as a smooth function of k, and
this one is a step function -- the integral over [z_k, z_{k+1}] at k = int(k) --
so the step is meaningless here and it was the whole of the cost: with it, one
value took 825 seconds and 765 MB, and the second run of this generator was
killed by the kernel's OOM killer on a 2 GB build machine; without it, 21
seconds and 14 MB, with the same 42 digits. At the precision used now a value
takes about three minutes per working precision and under 20 MB.

## Why the values are heuristic, and what checks them

A rigorous tail bound from |J_0(x)| <= sqrt(2/(pi x)) gives only
(2/(pi T))^{n/2} * 2/n, so bounding fifty digits at n = 3 would need
T ~ 10^33. Proving these digits needs the asymptotic expansion of the
oscillatory tail integrated term by term, which is a piece of analysis and not
a build step. So the rigour is the table's existing class, agreement-checked,
with two checks that are unusually strong:

  * every value is computed at two working precisions and only the digits both
    support are kept;
  * before anything is published, the method must reproduce the stored values
    at n = 3 and n = 4 -- Cl_2(pi/3)/pi and 7*zeta(3)/(2*pi^2) -- to the
    precision it claims. Those closed forms are independent of this integral,
    so agreement is evidence about the method rather than about arithmetic.

n = 3 to 6 are left alone: their stored values carry fifty digits from closed
forms, and replacing them with forty from quadrature would be a downgrade.
"""

import os
import sys

import mpmath as mp
import numberdb

#: Where the stored range stops, and where this one starts.
FIRST_NEW = 7

#: How far to go. At about six minutes a value for both working precisions,
#: n = 7..20 is under two hours.
UP_TO = 20

#: The two working precisions, and the most digits a value is given. The
#: published value keeps the digits both precisions agree on, less a two-digit
#: margin, and never more than the fifty the closed-form rows carry.
LOW, HIGH = 40, 48
MOST_DIGITS = 50

#: What the method has to reproduce before it is trusted anywhere new.
KNOWN = {
    3: "0.32306594721945051409363651072380639407224184078059",
    4: "0.42627839881750579092352142659616687305800676962964",
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _mu(n, dps):
    """mu_n at one working precision."""
    mp.mp.dps = dps + 15

    #Smooth: J_0(x)^n - 1 ~ -n x^2/4, so the integrand vanishes linearly at 0.
    head = mp.quad(lambda x: (mp.besselj(0, x) ** n - 1) / x, [0, 1])

    zeros = {}

    def zero(k):
        if k not in zeros:
            zeros[k] = mp.besseljzero(0, k)
        return zeros[k]

    first = mp.quad(lambda x: mp.besselj(0, x) ** n / x, [1, zero(1)])

    def between(k):
        k = int(k)
        return mp.quad(lambda x: mp.besselj(0, x) ** n / x,
                       [zero(k), zero(k + 1)])

    #Richardson and Shanks only: see the module docstring for why not
    #Euler-Maclaurin, which cost 40 times the time and 50 times the memory.
    tail = mp.nsum(between, [1, mp.inf], method="r+s")
    return mp.log(2) - mp.euler - head - first - tail


def mu(n):
    """mu_n, as a string of the digits two precisions agree on."""
    low = _mu(n, LOW)
    high = _mu(n, HIGH)
    mp.mp.dps = HIGH + 20
    difference = abs(high - low)
    if difference == 0:
        agreed = LOW
    else:
        agreed = int(-mp.log10(difference / abs(high)))
    #Two digits of margin, because the last agreeing digit is the one most
    #likely to be agreed on by accident.
    keep = max(1, min(MOST_DIGITS, agreed - 2))
    return mp.nstr(high, keep, strip_zeros=False)


def check():
    """Reproduce what is known before computing what is not."""
    for n, stored in sorted(KNOWN.items()):
        got = mu(n)
        digits = len(got.split(".")[-1])
        mp.mp.dps = digits + 10
        if abs(mp.mpf(got) - mp.mpf(stored)) > mp.mpf(10) ** (-digits + 1):
            raise SystemExit(
                "the method does not reproduce mu_%d: %s against %s"
                % (n, got, stored[:len(got)]))
        print("mu_%d reproduced to %d digits" % (n, digits), flush=True)


class ShortWalkMahlerMeasures(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE") or "T283"
    parameters = ("n",)
    type = "R"
    rigour = "heuristic (agreement-checked)"

    def enumerate(self, first=FIRST_NEW, last=UP_TO):
        for n in range(first, last + 1):
            yield {"n": str(n)}

    def value(self, params, digits=None):
        return mu(int(params["n"]))


if __name__ == "__main__":
    _key_from_stdin()
    check()
    generator = ShortWalkMahlerMeasures()
    publishing = (os.environ.get("NUMBERDB_PUBLISH") == "1"
                  or "--publish" in sys.argv)
    #One value per request, because each takes a quarter of an hour or more:
    #a run that dies at n = 19 should leave twelve values in the table rather
    #than nothing. `first` and `last` reach `enumerate` as bounds.
    #
    #`overwrite=False` for the same reason it exists: it adds what is missing
    #and does not recompute -- or touch -- what is stored, so the fifty-digit
    #closed-form rows at n = 3 to 6 cannot be replaced by forty digits of
    #quadrature.
    for n in range(FIRST_NEW, UP_TO + 1):
        if not publishing:
            print(n, generator.value({"n": str(n)}), flush=True)
            continue
        print(n, generator.publish(
            first=n, last=n, overwrite=False,
            message="mu_%d from the Bessel integral of Borwein, Straub, Wan "
                    "and Zudilin, integrated between the zeros of J_0; the "
                    "method reproduces Smyth's closed forms at n = 3 and 4"
                    % (n,)), flush=True)
