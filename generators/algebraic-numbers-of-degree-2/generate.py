"""Algebraic numbers of degree 2 -- numberdb.org/T35

The roots of every irreducible a2*x^2 + a1*x + a0 with 1 <= a2 <= 5 and
-5 <= a1, a0 <= 5. A port of the table's original `generate.sage`, which
predates the `numberdb` package: it wrote `numbers.yaml` in the data
repository by hand and formatted each root with
`complex_interval_to_sage_string(...).replace('?', '')`.

    $ sage -python generate.py            # verify against what is stored
    $ sage -python generate.py --diff     # what it would write, against it
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**The enumeration is the old one, entry for entry.** A polynomial that factors
is skipped; the roots of one that does not are numbered from 1, ordered by
imaginary part when the discriminant is negative and by real part when it is
positive. That ordering is what the parameter `n` means, so changing it would
renumber every entry and silently move 852 identities.

**What the port changes is how a component is written, and only where the
component is exact.** The old formatter put both halves of a complex number
through one decimal, so the real part of (3 + i*sqrt(3))/2 -- which is exactly
3/2 -- was written as ninety-nine digits of 1.5. A decimal expansion means
plus or minus one unit in the last place however long it is, so that spelling
could not say what was known. Since numberdb 0.1.9 a component that is an
interval landing on a point is written as one, `[3/2, 3/2]`, and a component
declared exact is written as a rational.

Nothing else moves: where both halves are genuine approximations the digits
are the same, and where the whole root is exact -- 2 + i * -1 for x^2-4x+5 --
it was already written exactly and still is.
"""

import sys

import numberdb
from sage.all import ComplexIntervalField, PolynomialRing, RealIntervalField, ZZ

#: The old script's bound, kept so the table holds the same polynomials.
COEFFICIENT_BOUND = 5

#: Its working precision too: 100 decimal digits at 3.4 bits each, with a 30%
#: margin. Written the way the original did rather than through
#: `numberdb.bits`, so that a root computed here is the root computed there.
DIGITS = 100
WORKING_BITS = int(DIGITS * 3.4 * 1.3)

_RING = PolynomialRing(ZZ, 'x')


def polynomials(bound=COEFFICIENT_BOUND):
    """The irreducible quadratics of the table, in the original's order."""
    x = _RING.gen()
    for a2 in range(1, bound + 1):
        for a1 in range(-bound, bound + 1):
            for a0 in range(-bound, bound + 1):
                f = a2 * x ** 2 + a1 * x + a0
                if f.is_irreducible():
                    yield (a2, a1, a0), f


def roots_of(f):
    """The roots, numbered as the table numbers them.

    Complex roots are ordered by imaginary part and real ones by real part,
    which is what makes `n` mean the same thing it has always meant.
    """
    if f.disc() < 0:
        field = ComplexIntervalField(WORKING_BITS)
        found = f.roots(field, multiplicities=False)
        found.sort(key=lambda root: root.imag())
    else:
        field = RealIntervalField(WORKING_BITS)
        found = f.roots(field, multiplicities=False)
        found.sort(key=lambda root: root.real())
    return found


def complex_root(a2, a1, a0, sign):
    """A root of a quadratic with negative discriminant, said exactly where
    it is exact.

    The real part of such a root is -a1/(2*a2), a rational, whatever the
    discriminant does; only sqrt(|disc|)/(2*a2) need be approximated, and
    even that is exact when |disc| is a square. So the halves are declared
    separately rather than both read off an interval.

    Reading exactness off a width instead does not work here, in both
    directions: Sage isolates the roots of x^2-4x+5 as zero-width intervals,
    which would spell the Gaussian integer 2 - i as `[2, 2] + i * [-1, -1]`,
    while it isolates the real part of the roots of x^2-3x+3 as a narrow
    interval that is not zero-width, so exactly 3/2 would stay a hundred
    digits of 1.5. A width is a property of an algorithm; exactness is a
    property of the number, and only the generator knows it.
    """
    from fractions import Fraction

    real = Fraction(-int(a1), 2 * int(a2))
    radicand = ZZ(4 * a2 * a0 - a1 * a1)          # = -disc > 0 here
    #`is_square` and `isqrt`, not `sqrt`: ZZ(3).sqrt() returns the symbolic
    #sqrt(3), whose square *does* equal 3, so a test on that took the exact
    #branch for every discriminant and int() then truncated sqrt(3) to 1 --
    #which wrote the roots of x^2-3x+3 as 3/2 + i * -1/2.
    if radicand.is_square():
        root = radicand.isqrt()
        #A square: the imaginary part is rational too, and the whole root is
        #a Gaussian rational. x^2-4x+5 is this case, and has always been
        #written `2 + i * -1`.
        imaginary = sign * Fraction(int(root), 2 * int(a2))
    else:
        field = RealIntervalField(WORKING_BITS)
        imaginary = numberdb.RealInterval(
            *_interval_endpoints(sign * field(radicand).sqrt()
                                 / field(2 * a2)))
    return numberdb.ComplexInterval(real, imaginary)


def _interval_endpoints(interval):
    """A Sage real interval's endpoints, as exact Fractions."""
    from fractions import Fraction

    def exactly(endpoint):
        #Numerator and denominator taken by hand. `Fraction(sage_rational)`
        #looks like it works: Sage's Rational registers as numbers.Rational,
        #so Fraction reads `.numerator` as an attribute -- and Sage's is a
        #method, so the Fraction ends up holding two bound methods and fails
        #much later, inside the writer, as "conversion from method to Decimal".
        rational = endpoint.exact_rational()
        return Fraction(int(rational.numerator()),
                        int(rational.denominator()))

    return exactly(interval.lower()), exactly(interval.upper())


class QuadraticAlgebraicNumbers(numberdb.Generator):

    table = 'T35'
    parameters = ('a2', 'a1', 'a0', 'n')
    type = 'C'
    digits = DIGITS
    rigour = 'proven'

    def enumerate(self, bound=COEFFICIENT_BOUND):
        for (a2, a1, a0), f in polynomials(bound):
            for n in range(1, f.degree() + 1):
                yield {'a2': a2, 'a1': a1, 'a0': a0, 'n': n}

    def value(self, params, digits):
        x = _RING.gen()
        a2, a1, a0 = params['a2'], params['a1'], params['a0']
        f = a2 * x ** 2 + a1 * x + a0

        if f.disc() < 0:
            #Ordered by imaginary part, as the table numbers them, so n = 1 is
            #the one with the negative imaginary part.
            root = complex_root(a2, a1, a0, -1 if params['n'] == 1 else 1)
        else:
            root = roots_of(f)[params['n'] - 1]

        entry = {'number': root}
        #The golden ratio and its inverse are in the corpus under their own
        #name; the original said so and the table still does.
        if (params['a2'], params['a1'], params['a0']) == (1, -1, -1):
            entry['equals'] = ('HREF{Golden_ratio#phi_inv}' if params['n'] == 1
                               else 'HREF{Golden_ratio#phi}')
        return entry


if __name__ == '__main__':
    generator = QuadraticAlgebraicNumbers()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='regenerated from a Generator: a component that is exact '
                    'is written as one, rather than as a decimal long enough '
                    'to look like it'))
    elif '--diff' in sys.argv:
        import diff_against_stored

        sys.exit(diff_against_stored.main(generator))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
