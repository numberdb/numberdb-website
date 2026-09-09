"""Densities of primes with a given primitive root -- numberdb.org/T165

For an integer a that is not -1 and is not a perfect square, this computes
Artin's density delta(a), the conjectural natural density of primes p for
which a is a primitive root modulo p under the generalized Riemann hypothesis.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The values are exact rational multiples of Artin's constant

    A = product_q (1 - 1/(q*(q - 1))),

where q runs over primes. PARI's prodeulerrat evaluates A quickly by zeta
expansion, but it does not return a ball or interval; the table is therefore
heuristic (agreement-checked), not proven. The rational correction factors are
computed exactly from Hooley's formula.
"""

import os
import sys
from math import gcd

import numberdb.sage as numberdb
from sage.libs.pari import pari
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ

#: The table contains every admissible integer a in [-BOUND, BOUND].
BOUND = 50

#: Decimal digits written to the table. PARI is run with extra guard digits.
DIGITS = 100
PARI_PRECISION = DIGITS + 40

_ARTIN = None


def prime_factors(n):
    """The prime divisors of n, as Sage integers."""
    return [p for p, _ in ZZ(abs(n)).factor()]


def exponent_gcd(n):
    """The gcd of the exponents in the factorisation of |n|."""
    out = 0
    for _, exponent in ZZ(abs(n)).factor():
        out = int(exponent) if out == 0 else gcd(out, int(exponent))
    return out or 1


def is_rational_square(a):
    """Whether the integer a is a square in Q."""
    a = ZZ(a)
    return a >= 0 and a.is_square()


def in_domain(a):
    """Whether a is one of the table's parameters."""
    a = ZZ(a)
    return a != -1 and not is_rational_square(a)


def core_and_exponent(a):
    """Return a0, h with a = a0^h and h maximal.

    For negative a only odd exponents are possible. Thus -64 is (-4)^3, not
    a sixth power.
    """
    a = ZZ(a)
    if not in_domain(a):
        raise ValueError('%s is outside the Artin-density domain' % a)

    h = exponent_gcd(a)
    if a < 0:
        while h % 2 == 0:
            h //= 2

    base = ZZ(1)
    for p, exponent in ZZ(abs(a)).factor():
        base *= p ** ZZ(exponent // h)
    if a < 0:
        base = -base
    return base, ZZ(h)


def squarefree_part(n):
    """The signed squarefree part of n."""
    n = ZZ(n)
    sign = -1 if n < 0 else 1
    out = ZZ(1)
    for p, exponent in ZZ(abs(n)).factor():
        if int(exponent) % 2:
            out *= p
    return ZZ(sign) * out


def quadratic_discriminant(a):
    """The discriminant of Q(sqrt(a))."""
    base, _ = core_and_exponent(a)
    d = squarefree_part(base)
    return d if int(d) % 4 == 1 else 4 * d


def moebius_squarefree(n):
    """The Moebius value of a positive squarefree integer."""
    return ZZ(-1) ** len(prime_factors(n))


def artin_multiplier(h):
    """A(h) / A, where A is Artin's constant."""
    out = QQ(1)
    for q in prime_factors(h):
        out *= QQ(q * (q - 2)) / QQ(q * q - q - 1)
    return out


def entanglement_factor(d, h):
    """Hooley's correction factor attached to the quadratic subfield."""
    d = ZZ(d)
    h = ZZ(h)
    if int(d) % 4 != 1:
        return QQ(1)

    product = QQ(1)
    for q in prime_factors(d):
        if h % q == 0:
            product *= QQ(1) / QQ(q - 2)
        else:
            product *= QQ(1) / QQ(q * q - q - 1)
    return QQ(1) - QQ(moebius_squarefree(abs(d))) * product


def density_multiplier(a):
    """The exact rational r(a) for delta(a) = r(a) A."""
    _, h = core_and_exponent(a)
    d = quadratic_discriminant(a)
    return artin_multiplier(h) * entanglement_factor(d, h)


def artin_constant():
    """Artin's constant as a PARI real."""
    global _ARTIN
    if _ARTIN is None:
        pari('default(realprecision, %d)' % PARI_PRECISION)
        _ARTIN = pari('prodeulerrat(1 - 1/(p*(p - 1)))')
    return _ARTIN


def density(a):
    """Hooley's Artin density for a."""
    return pari(str(density_multiplier(a))) * artin_constant()


def decimal(value, digits):
    """A PARI real as NumberDB's plain decimal text."""
    text = str(pari('Strprintf("%%.%dg", %s)' % (int(digits), value)))
    return text.replace('E', 'e')


def tex_integer(n):
    """An integer in TeX, parenthesised when needed as a power base."""
    n = ZZ(n)
    return '(%s)' % n if n < 0 else str(n)


def tex_rational(value):
    """A rational in short TeX form."""
    value = QQ(value)
    if value.denominator() == 1:
        return str(value.numerator())
    return r'\frac{%s}{%s}' % (value.numerator(), value.denominator())


def multiplier_text(value):
    """The entry comment's multiple of Artin's constant."""
    value = QQ(value)
    if value == 1:
        return 'A'
    return '%sA' % tex_rational(value)


def entry_comment(a):
    """A short comment naming the rational multiple and the correction data."""
    a = ZZ(a)
    base, h = core_and_exponent(a)
    d = quadratic_discriminant(a)
    multiple = density_multiplier(a)

    if multiple == 1:
        lead = r"This is Artin's constant $A$"
    else:
        lead = (r"This is $%s$, where $A$ is Artin's constant"
                % multiplier_text(multiple))

    facts = []
    if a == 2:
        facts.append(
            r'the primes for which $2$ is a primitive root form OEIS A001122 '
            r'CITE{OEISPrimitiveRoot2}')
    if h != 1:
        facts.append(r'$%s=%s^%s$' % (a, tex_integer(base), h))
    facts.append(r'the quadratic-field discriminant is $d=%s$' % d)

    if len(facts) == 1:
        tail = facts[0]
    else:
        tail = '%s and %s' % (', '.join(facts[:-1]), facts[-1])
    return '%s; %s.' % (lead, tail)


class ArtinPrimitiveRootDensities(numberdb.Generator):

    table = os.environ.get('NUMBERDB_TABLE', 'T165')
    parameters = ('a',)
    type = 'R'
    digits = DIGITS
    rigour = 'heuristic (agreement-checked)'

    def enumerate(self, bound=BOUND):
        #By |a|, positive before negative, and not in the order of ZZ. Entries
        #are shown in the order the document writes them, so -1000 led the
        #table and 2 -- Artin's own constant, and the row anybody arrives
        #wanting -- was halfway down. Small bases are the interesting ones and
        #belong at the top, and a and -a belong next to each other because
        #their densities are what a reader compares.
        #
        #The two are not paired everywhere: 4 is a square and -4 is not, so
        #|a| = 4 contributes one row. Sorting handles that without a special
        #case.
        for a in sorted(range(-bound, bound + 1), key=lambda a: (abs(a), -a)):
            if in_domain(a):
                yield {'a': str(a)}

    def value(self, params, digits):
        a = ZZ(params['a'])
        return {
            'number': decimal(density(a), digits),
            'comment': entry_comment(a),
        }


if __name__ == '__main__':
    #The environment as well as the argument: `agents/sage.sh` runs a script
    #with no arguments, so `--publish` cannot be given through it, and this
    #generator silently verified ten sampled rows where a rewrite was meant.
    #The other generators here already read both.
    if os.environ.get('NUMBERDB_KEY_FROM_STDIN') == '1':
        os.environ['NUMBERDB_API_KEY'] = sys.stdin.read().strip()
    generator = ArtinPrimitiveRootDensities()
    if '--publish' in sys.argv or os.environ.get('NUMBERDB_PUBLISH') == '1':
        print(generator.publish(
            message='Artin primitive-root densities for small integer bases'))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
