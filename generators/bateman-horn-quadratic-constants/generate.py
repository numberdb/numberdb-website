"""Bateman-Horn constants of monic quadratic polynomials -- numberdb.org/T166.

For a monic irreducible quadratic f(x) with integer coefficients and no fixed
prime divisor, this computes

    C(f) = product_p (1 - N_f(p)/p) / (1 - 1/p),

where N_f(p) is the number of roots of f modulo p.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The table stores C(f), not the C(f)/2 that appears in the asymptotic for one
quadratic polynomial. The computation is the Belabas-Cohen PARI/GP algorithm
for Hardy-Littlewood constants of quadratic polynomials, embedded here so the
generator is self-contained. It is agreement-checked, not proven: PARI returns
high-precision real numbers, not intervals carrying the truncation error.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import kronecker_symbol
from sage.libs.pari import pari
from sage.rings.integer_ring import ZZ

#: Decimal digits written to the table. PARI is run with extra guard digits.
DIGITS = 100
PARI_PRECISION = DIGITS + 40

#: The finite-prime cutoff used by the Belabas-Cohen script. Larger values give
#: the same 100 digits on the rows checked before the draft was filled.
FINITE_CUTOFF = 50

FAMILIES = ('x^2+a', 'x^2+x+a')

_PARI_READY = False
_VALUES = {}


PARI_DEFINITIONS = (
    r"""ZetaDN(P, s) = zeta(s) * prod(j = 1, #P, 1 - P[j]^(-s))""",
    r"""LchiN(L, Ebad, s) =
{ my([P, E] = Ebad);
  lfun(L, s) * prod(j = 1, #P, subst(E[j], 'x, P[j]^(-s)));
}""",
    r"""LchiNinit(D, P) =
{ my(Ebad = [], Pbad = []);
  for (j = 1, #P,
    my(p = P[j], s = kronecker(D, p));
    if (s, Ebad = concat(Ebad, 1 - s*'x);
           Pbad = concat(Pbad, p)));
  return ([Pbad, Ebad]);
}""",
    r"""Oddpart(n) = n >> valuation(n,2)""",
    r"""HLW2(D, N) =
{ my(B = getlocalbitprec(), lim, S1, S2, L, P, v, Ebad);
  localbitprec(32); lim = ceil(B*log(2)/log(N/2));
  localbitprec(B + lim + exponent(lim));
  L = lfuninit(D, [1/2, lim, 0]);
  v = vector(lim);
  forfactored(X = 1, lim,
    my([n] = X, S = 0);
    fordivfactored(X, Y,
      my([d] = Y);
      if (d % 2, S += moebius(Y) << (n/d)));
    v[n] = S / (2*n);
  );
  P = setunion(factor(abs(D))[,1]~, primes([2, N]));
  Ebad = LchiNinit(D, P);
  S1 = sum(n = 1, lim, v[n] * log(LchiN(L, Ebad, n)));
  S2 = sum(n = 2, lim, (v[n] - if (n%2 == 0, v[n/2]))
                       * log(ZetaDN(P, n)));
  return (S1 + S2);
}""",
    r"""HardyLittlewood2(A, N = 50) =
{ my(D = poldisc(A), S, P);
  if (poldegree(A) != 2, error("polynomial of degree != 2"));
  my([a, b, c] = Vec(A));
  if (issquare(D) || gcd([2 * a, a + b, c]) > 1, return (0));
  N = max(N, 3);
  S = if ((a + b) % 2, 1., 2.);
  P = factor(Oddpart(a))[,1];
  for (j = 1, #P,
    my(p = P[j]);
    S *= if (b % p, (p - 1) / (p - 2), p / (p - 1))
  );
  my([D0, f] = coredisc(D, 1));
  P = factor(Oddpart(f))[,1];
  S /= prod(j = 1, #P,
    my(p = P[j]);
    1 - kronecker(D0, p) / (p - 1);
  );
  S *= prodeuler(p = 3, N, 1 - kronecker(D0, p) / (p - 1));
  return (S * exp(-HLW2(D0, N)));
}""",
)


def load_pari():
    """Load the GP functions once into the PARI session."""
    global _PARI_READY
    if not _PARI_READY:
        for definition in PARI_DEFINITIONS:
            pari(definition)
        _PARI_READY = True


def polynomial_text(b, c):
    """The parameter spelling in NumberDB."""
    b = ZZ(b)
    c = ZZ(c)
    text = 'x^2'
    if b == 1:
        text += '+x'
    elif b == -1:
        text += '-x'
    elif b:
        text += '%+dx' % b
    if c:
        text += '%+d' % c
    return text


def parse_polynomial(text):
    """Return (b, c) for the two families this table enumerates."""
    text = str(text).replace(' ', '')
    for a in range(-30, 31):
        if polynomial_text(0, a) == text:
            return ZZ(0), ZZ(a)
    for a in range(1, 42, 2):
        if polynomial_text(1, a) == text:
            return ZZ(1), ZZ(a)
    raise ValueError('not a polynomial in this table: %s' % text)


def discriminant(b, c):
    """The polynomial discriminant of x^2 + b*x + c."""
    return ZZ(b) ** 2 - 4 * ZZ(c)


def fixed_prime_divisor(b, c):
    """Whether x^2 + b*x + c has a prime dividing every integer value."""
    b = ZZ(b)
    c = ZZ(c)
    return ZZ(2).gcd(1 + b).gcd(c) > 1


def in_domain(b, c):
    """Whether this monic quadratic has a Bateman-Horn constant listed here."""
    delta = discriminant(b, c)
    return not delta.is_square() and not fixed_prime_divisor(b, c)


def pari_expression(b, c):
    """The polynomial as a PARI expression."""
    b = ZZ(b)
    c = ZZ(c)
    parts = ['x^2']
    if b == 1:
        parts.append('+x')
    elif b == -1:
        parts.append('-x')
    elif b:
        parts.append('%+d*x' % b)
    if c:
        parts.append('%+d' % c)
    return ''.join(parts)


def bateman_horn_constant(b, c, digits=DIGITS, cutoff=FINITE_CUTOFF):
    """C(x^2 + b*x + c), as a PARI real."""
    b = ZZ(b)
    c = ZZ(c)
    if not in_domain(b, c):
        raise ValueError('%s is outside the table domain' % polynomial_text(b, c))
    key = (int(b), int(c), int(digits), int(cutoff))
    if key not in _VALUES:
        load_pari()
        pari('default(realprecision, %d)' % (int(digits) + 40))
        _VALUES[key] = pari('HardyLittlewood2(%s, %d)' % (
            pari_expression(b, c), int(cutoff)))
    return _VALUES[key]


def decimal(value, digits):
    """A PARI real as NumberDB's plain decimal text."""
    text = str(pari('Strprintf("%%.%dg", %s)' % (int(digits), value)))
    return text.replace('E', 'e')


def root_count_mod_prime(b, c, p):
    """The number of roots of x^2 + b*x + c modulo p, checked directly."""
    b = ZZ(b)
    c = ZZ(c)
    p = ZZ(p)
    return ZZ(sum(1 for x in range(int(p)) if (x * x + b * x + c) % p == 0))


def root_count_identity_holds(b, c, bound=97):
    """Check N_f(p) = 1 + Kronecker(Delta, p) for small primes."""
    delta = discriminant(b, c)
    p = ZZ(2)
    while p <= bound:
        if root_count_mod_prime(b, c, p) != 1 + kronecker_symbol(delta, p):
            return False
        p = p.next_prime()
    return True


def entry_comment(b, c):
    """A short row note naming the discriminant and notable external rows."""
    b = ZZ(b)
    c = ZZ(c)
    delta = discriminant(b, c)
    if not root_count_identity_holds(b, c):
        raise ArithmeticError('%s failed the root-count check' % polynomial_text(b, c))
    facts = [r'The discriminant is $\Delta=%s$' % delta]
    if b == 0 and c == 1:
        facts.append(
            r"primes of the form $n^2+1$ are Landau's fourth problem "
            r'CITE{WikiLandau}')
        facts.append(
            r'OEIS A199401 gives this normalization, A331941 gives half of '
            r'it, and A206709 counts such primes CITE{OEISCountsX2Plus1}')
    if b == 1 and c == 41:
        facts.append(
            r'OEIS A221712 gives half of this normalization, and OEIS '
            r'A331940 lists $41$ as a record addend '
            r'CITE{OEISRecordQuadratics}')
    return '; '.join(facts) + '.'


class BatemanHornQuadraticConstants(numberdb.Generator):

    table = os.environ.get('NUMBERDB_TABLE', 'T166')
    parameters = ('f',)
    type = 'R'
    digits = DIGITS
    rigour = 'heuristic (agreement-checked)'

    def enumerate(self):
        for a in range(-30, 31):
            if in_domain(0, a):
                yield {'f': polynomial_text(0, a)}
        for a in range(1, 42, 2):
            if in_domain(1, a):
                yield {'f': polynomial_text(1, a)}

    def value(self, params, digits):
        b, c = parse_polynomial(params['f'])
        return {
            'number': decimal(bateman_horn_constant(b, c, digits), digits),
            'comment': entry_comment(b, c),
        }


if __name__ == '__main__':
    generator = BatemanHornQuadraticConstants()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='Bateman-Horn constants of monic quadratic polynomials in '
                    'the checked ranges'))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
