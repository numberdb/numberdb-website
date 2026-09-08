"""Mertens constants of primes in arithmetic progressions -- numberdb.org/T164

For q >= 3 and gcd(a, q) = 1, this computes the three constants

    sum_{p <= x, p = a mod q} 1/p = log(log x)/phi(q) + M(q,a) + o(1),
    B(q,a) = sum_{p = a mod q} (log(1 - 1/p) + 1/p),
    prod_{p <= x, p = a mod q} (1 - 1/p) ~ C(q,a) / log(x)^(1/phi(q)).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The computation follows Languasco and Zaccagnini's formulas with cutoff
X = 9600 and truncations K = M = 26. The constants are not marked proven here:
the omitted tails are those bounded in their papers, and this generator writes
95 significant digits checked against their published 100-decimal-place
matrices before the draft was filled.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.arith.misc import euler_phi, prime_divisors, prime_range
from sage.modular.dirichlet import DirichletGroup
from sage.rings.complex_arb import ComplexBallField
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField

#: The table contains every reduced residue class modulo q through this bound.
BOUND = 30

#: Languasco-Zaccagnini's cutoff for the accelerated Euler products.
CUTOFF = 9600

#: Truncations from the 100-digit computations in the cited papers.
K_TRUNCATION = 26
M_TRUNCATION = 26

#: Terms with n >= this have |log L_X(chi,n)| < 10^-130 by the paper's
#: elementary tail bound, far below the 95 digits written here.
TAIL_LOG_SKIP_AT = 34

#: The Meissel-Mertens constant M is computed from gamma - sum P(m)/m.
MEISSEL_TRUNCATION = 430
ZETA_LOG_SKIP_AT = 520

#: Bits of working precision beyond the requested 95 digits. Measured in the
#: dry run: every stored decimal was stable against the published matrices.
WORKING_GUARD = 260

CONSTANTS = ('M', 'B', 'C')
PRIMES = tuple(prime_range(2, CUTOFF + 1))

_CHARACTERS = {}
_ENCLOSED = {}
_L_VALUE = {}
_L_TAIL_LOG = {}
_PRIME_ZETA = {}
_MEISSEL_MERTENS = {}
_BY_MODULUS = {}


def mu(n):
    """The Moebius function, without importing more Sage machinery."""
    n = ZZ(n)
    factors = n.factor()
    if any(e > 1 for _, e in factors):
        return ZZ(0)
    return ZZ(-1) ** len(factors)


def characters(q):
    """Dirichlet characters modulo q, cached by modulus."""
    q = ZZ(q)
    if q not in _CHARACTERS:
        _CHARACTERS[q] = tuple(DirichletGroup(q))
    return _CHARACTERS[q]


def character_key(chi):
    """A stable key for a Sage Dirichlet character."""
    return (int(chi.modulus()), int(chi.conrey_number()))


def enclose(value, bits):
    """A cyclotomic value enclosed as a complex ball."""
    key = (repr(value), bits)
    if key in _ENCLOSED:
        return _ENCLOSED[key]
    C = ComplexBallField(bits)
    parent = value.parent()
    if parent is QQ or parent is ZZ:
        out = C(value)
    else:
        order = parent.gen().multiplicative_order()
        zeta = (2 * C.pi() * C(0, 1) / order).exp()
        out = value.polynomial()(zeta)
    _ENCLOSED[key] = out
    return out


def l_value(chi, s, bits):
    """L(s, chi) for a character modulo q as a complex ball."""
    q = ZZ(chi.modulus())
    s = ZZ(s)
    key = (character_key(chi), int(s), bits)
    if key in _L_VALUE:
        return _L_VALUE[key]

    C = ComplexBallField(bits)
    R = RealBallField(bits)
    if chi.is_trivial():
        if s == 1:
            raise ArithmeticError('the principal L-function has a pole at s = 1')
        value = C(s).zeta()
        for p in prime_divisors(q):
            value *= 1 - C(1) / C(p) ** s
        _L_VALUE[key] = value
        return value

    total = C(0)
    for a in range(1, int(q) + 1):
        c = chi(a)
        if c == 0:
            continue
        x = QQ(a) / q
        if s == 1:
            total += enclose(c, bits) * C(R(x).psi())
        else:
            total += enclose(c, bits) * C(s).zeta(C(x))
    value = -total / q if s == 1 else total / C(q) ** s
    _L_VALUE[key] = value
    return value


def l_tail_log(chi, s, bits):
    """log L_X(chi,s), where L_X is the Euler product over primes p > CUTOFF."""
    s = ZZ(s)
    C = ComplexBallField(bits)
    if s >= TAIL_LOG_SKIP_AT:
        return C(0)
    key = (character_key(chi), int(s), bits)
    if key in _L_TAIL_LOG:
        return _L_TAIL_LOG[key]
    tail = l_value(chi, s, bits)
    for p in PRIMES:
        c = chi(p)
        if c != 0:
            tail *= 1 - enclose(c, bits) / C(p) ** s
    value = tail.log()
    if not (value.real().is_finite() and value.imag().is_finite()):
        raise ArithmeticError('log L_%d(chi, %s) is not finite for %s'
                              % (CUTOFF, s, chi))
    _L_TAIL_LOG[key] = value
    return value


def prime_zeta(s, bits):
    """P(s) = sum_p p^-s by Moebius inversion from log zeta."""
    s = ZZ(s)
    key = (int(s), bits)
    if key in _PRIME_ZETA:
        return _PRIME_ZETA[key]
    C = ComplexBallField(bits)
    R = RealBallField(bits)
    total = C(0)
    k = ZZ(1)
    while k * s < ZETA_LOG_SKIP_AT:
        muk = mu(k)
        if muk:
            total += C(QQ(muk) / QQ(k)) * C(k * s).zeta().log()
        k += 1
    if not total.imag().contains_zero():
        raise ArithmeticError('P(%s) has nonzero imaginary part %s'
                              % (s, total.imag()))
    value = R(total.real())
    _PRIME_ZETA[key] = value
    return value


def meissel_mertens(bits):
    """The classical Meissel-Mertens constant M."""
    if bits in _MEISSEL_MERTENS:
        return _MEISSEL_MERTENS[bits]
    R = RealBallField(bits)
    total = R.euler_constant()
    for m in range(2, MEISSEL_TRUNCATION + 1):
        total -= prime_zeta(m, bits) / m
    _MEISSEL_MERTENS[bits] = total
    return total


def tail_prime_sum(chi, m, bits):
    """sum_{p > X} chi(p) / p^m by Moebius inversion."""
    C = ComplexBallField(bits)
    total = C(0)
    for k in range(1, K_TRUNCATION + 1):
        n = ZZ(k * m)
        if n >= TAIL_LOG_SKIP_AT:
            break
        muk = mu(k)
        if muk:
            total += C(QQ(muk) / QQ(k)) * l_tail_log(chi ** k, n, bits)
    return total


def tail_for_M(chi, bits):
    """The tail of sum_p chi(p)/p after the cutoff."""
    return tail_prime_sum(chi, 1, bits)


def tail_for_C(chi, bits):
    """The tail contribution sum_m m^-1 sum_{p > X} chi(p)/p^m."""
    C = ComplexBallField(bits)
    total = C(0)
    for m in range(1, M_TRUNCATION + 1):
        total += tail_prime_sum(chi, m, bits) / m
    return total


def real_part(value, label):
    """Return a real ball after checking that the imaginary part vanishes."""
    if not value.imag().contains_zero():
        raise ArithmeticError('%s has nonzero imaginary part %s'
                              % (label, value.imag()))
    return value.real()


def constants_for_modulus(q, digits):
    """All M(q,a), B(q,a), C(q,a) for a fixed modulus q."""
    q = ZZ(q)
    bits = numberdb.bits(digits, losing=WORKING_GUARD)
    key = (int(q), bits)
    if key in _BY_MODULUS:
        return _BY_MODULUS[key]

    chars = characters(q)
    nontrivial = [chi for chi in chars if not chi.is_trivial()]
    units = [ZZ(a) for a in range(1, int(q) + 1) if ZZ(a).gcd(q) == 1]
    phi = ZZ(euler_phi(q))
    C = ComplexBallField(bits)
    R = RealBallField(bits)

    class_recip = {a: QQ(0) for a in units}
    class_log = {a: R(0) for a in units}
    coprime_recip = QQ(0)
    base_finite_log = -R.euler_constant()
    for p in PRIMES:
        p = ZZ(p)
        log_factor = (1 - R(QQ(1) / p)).log()
        base_finite_log -= log_factor
        if p.gcd(q) == 1:
            coprime_recip += QQ(1) / p
        residue = p % q
        if residue in class_recip:
            class_recip[residue] += QQ(1) / p
            class_log[residue] += log_factor

    M_base = C(meissel_mertens(bits))
    for p in prime_divisors(q):
        M_base -= C(QQ(1) / p)
    M_base -= C(coprime_recip)

    M_tails = {chi: tail_for_M(chi, bits) for chi in nontrivial}
    C_tails = {chi: tail_for_C(chi, bits) for chi in nontrivial}

    values = {}
    for a in units:
        M_value = C(phi * class_recip[a]) + M_base
        log_C_value = C(base_finite_log + phi * class_log[a])
        for chi in nontrivial:
            coefficient = enclose(chi(a), bits).conjugate()
            M_value += coefficient * M_tails[chi]
            log_C_value -= coefficient * C_tails[chi]
        M_value = real_part(M_value / phi, 'M(%s,%s)' % (q, a))
        log_C_value = real_part(log_C_value / phi, 'log C(%s,%s)' % (q, a))
        values[(int(a), 'M')] = M_value
        values[(int(a), 'C')] = log_C_value.exp()
        values[(int(a), 'B')] = M_value + log_C_value

    _BY_MODULUS[key] = values
    return values


class MertensProgressionConstants(numberdb.Generator):

    table = os.environ.get('NUMBERDB_TABLE', 'T164')
    parameters = ('q', 'a', 'constant')
    type = 'R'
    digits = 95
    rigour = 'heuristic (agreement-checked)'

    def enumerate(self, bound=BOUND):
        for q in range(3, bound + 1):
            for a in range(1, q + 1):
                if ZZ(a).gcd(ZZ(q)) != 1:
                    continue
                for constant in CONSTANTS:
                    yield {'q': q, 'a': a, 'constant': constant}

    def value(self, params, digits):
        q = ZZ(params['q'])
        a = ZZ(params['a'])
        constant = str(params['constant'])
        if constant not in CONSTANTS:
            raise ValueError('unknown constant %r' % constant)
        if q < 3 or a < 1 or a > q or a.gcd(q) != 1:
            raise ValueError('expected q >= 3 and gcd(a,q) = 1')
        return constants_for_modulus(q, digits)[(int(a), constant)]


if __name__ == '__main__':
    generator = MertensProgressionConstants()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='Mertens constants M(q,a), B(q,a) and C(q,a) for reduced '
                    'residue classes modulo q <= 30, computed from the '
                    'Languasco-Zaccagnini accelerated formulas and checked '
                    'against their published matrices'))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
