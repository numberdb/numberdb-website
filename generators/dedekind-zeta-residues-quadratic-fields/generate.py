"""Residue at s = 1 of the Dedekind zeta function of a quadratic field -- numberdb.org/T128

    kappa_D = lim_{s -> 1} (s - 1) zeta_K(s),    K = Q(sqrt D),

for every fundamental discriminant D with |D| <= 1000, of either sign. Since
zeta_K(s) = zeta(s) L(s, chi_D) and zeta has residue 1, this is the same number
as L(1, chi_D), the Dirichlet L-value of the Kronecker character (D/.) at 1.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**These digits are proven.** Every value is a real ball. It is not obtained by
evaluating anything at the pole: writing L(s, chi_D) as |D|^-s times a sum of
Hurwitz zeta functions and using sum_a chi_D(a) = 0 to cancel the pole gives

    L(1, chi_D) = -(1/|D|) sum_{a=1}^{|D|-1} chi_D(a) psi(a/|D|),

a finite sum of digamma values, which arb evaluates with a rigorous error
bound. The written digits are the ones the resulting ball supports.

**Every value is checked against the class number formula before it is
returned.** h_K comes from Sage's class group computation and, for D > 0, the
fundamental unit from Sage's unit group, both with `proof=True`; neither shares
a line of code with the digamma sum. The two must overlap as balls, and a value
for which they do not is an error rather than an entry. Checked on all 607
discriminants when this was written, with the controls that must fail failing:
kappa_{-4} against pi/3, and h_{-23} = 4 in place of 3.

**Two conventions had to be settled**, and both are stated on the table too.
The parameter is the fundamental discriminant D, not the squarefree d of
Q(sqrt d) -- chi_D is primitive exactly when D is fundamental, and the LMFDB
and OEIS enumerate the fields this way -- so every entry's comment names the
field, because Q(sqrt 3) is D = 12 and nobody arrives holding "12". And the
quantity is the residue of zeta_K itself, not of the completed function
Lambda_K, whose residue differs by Gamma factors and powers of pi.
"""

import sys

import numberdb.sage as numberdb
from sage.arith.misc import is_squarefree, kronecker_symbol
from sage.rings.integer_ring import ZZ
from sage.rings.number_field.number_field import QuadraticField
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField

#: Bits of working precision beyond what the written digits need. Measured
#: over the whole table at 100 digits: the digamma sum has up to 999 terms and
#: the worst entry (D = 937) retains 97.0 digits with no guard, 106.6 with 32
#: bits and 116.3 with 64. The worst entry is the same at every guard, so what
#: is lost is the sum's doing rather than the guard's.
WORKING_GUARD = 64

#: Every fundamental discriminant with |D| up to here is listed: 305 negative
#: and 302 positive, 607 in all. The entries do not grow with D, so the bound
#: is a choice about what somebody looks up rather than about size; a thousand
#: is where the LMFDB's and OEIS's first pages of quadratic fields end.
BOUND = 1000


def is_fundamental_discriminant(D):
    """Whether D is the discriminant of a quadratic field.

    D = 1 mod 4 and squarefree, or D = 4m with m = 2, 3 mod 4 squarefree.
    D = 1 is excluded: it is the discriminant of Q, which is not quadratic.
    Written out rather than imported, so that a reader sees the convention.
    """
    D = ZZ(D)
    if D == 0 or D == 1:
        return False
    if D % 4 == 1:
        return is_squarefree(D)
    if D % 4 == 0:
        m = D // 4
        return m % 4 in (2, 3) and is_squarefree(m)
    return False


def fundamental_discriminants(bound):
    """Fundamental discriminants with |D| <= bound, ordered by |D|, -D first."""
    return [D for D in sorted(range(-bound, bound + 1), key=lambda d: (abs(d), d))
            if is_fundamental_discriminant(D)]


def residue(D, bits):
    """kappa_D = L(1, chi_D) as a real ball, from the digamma sum.

    L(s, chi_D) = |D|^-s sum_{a=1}^{|D|-1} chi_D(a) zeta(s, a/|D|), and near
    s = 1 the Hurwitz zeta function is 1/(s-1) - psi(x) + O(s-1). The poles
    cancel because chi_D sums to zero over a period, and what is left at s = 1
    is -(1/|D|) sum_a chi_D(a) psi(a/|D|). Each psi(a/|D|) is arb's digamma
    of a ball containing the rational a/|D|, so the sum is an enclosure.
    """
    R = RealBallField(bits)
    N = abs(ZZ(D))
    total = R(0)
    for a in range(1, N):
        chi = kronecker_symbol(D, a)
        if chi:
            total += chi * R(QQ(a) / QQ(N)).psi()
    return _finite(-total / R(N))


def _finite(ball):
    """A ball that pins something down, or a refusal.

    A nan ball overlaps every interval, so letting one out of here would turn
    the class number formula check below into a formality.
    """
    if not ball.is_finite():
        raise ArithmeticError('the digamma sum returned a ball that is not finite')
    return ball


def field_data(D):
    """(h, w, eps) for K = Q(sqrt D): class number, roots of unity, fundamental unit.

    `w` is None for D > 0 and `eps` is None for D < 0. For D > 0, `eps` is the
    pair (a, b) of integers with eps = (a + b sqrt d)/2 > 1, d the squarefree
    part of D (d = D or D/4) -- the unit of the maximal order, so eps_5 is the
    golden ratio and not 2 + sqrt 5. `K.units()` may return any of eps, -eps,
    1/eps, -1/eps; the one whose real embedding exceeds 1 is chosen.
    """
    D = ZZ(D)
    K = QuadraticField(D, 'w')
    h = ZZ(K.class_number(proof=True))
    if D < 0:
        w = 6 if D == -3 else (4 if D == -4 else 2)
        return h, w, None
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
    #c0 + c1 sqrt D = c0 + c1 (D/d)^(1/2) sqrt d, and D/d is 1 or 4.
    b_over_two = c1 * ZZ(D // d).sqrt()
    a, b = 2 * c0, 2 * b_over_two
    if a.denominator() != 1 or b.denominator() != 1:
        raise ArithmeticError('unit coordinates are not half-integral for D = %s' % D)
    return h, None, (ZZ(a), ZZ(b))


def squarefree_part(D):
    """d with Q(sqrt D) = Q(sqrt d): D itself, or D/4."""
    D = ZZ(D)
    return D if D % 4 == 1 else D // 4


def class_number_formula(D, h, w, eps, bits):
    """kappa_D from Dirichlet's class number formula, as a ball.

    2 pi h / (w sqrt|D|) for D < 0 and 2 h log(eps) / sqrt D for D > 0, with
    eps = (a + b sqrt d)/2. Shares nothing with `residue` but the name of D.
    """
    R = RealBallField(bits)
    D = ZZ(D)
    if D < 0:
        return 2 * R.pi() * h / (w * R(-D).sqrt())
    a, b = eps
    d = squarefree_part(D)
    log_eps = ((R(a) + R(b) * R(d).sqrt()) / 2).log()
    return 2 * h * log_eps / R(D).sqrt()


def field_name(D):
    d = squarefree_part(D)
    if d == -1:
        return r'\mathbb{Q}(i)'
    return r'\mathbb{Q}(\sqrt{%d})' % d


def unit_latex(D, eps):
    """(a + b sqrt d)/2 written the way a person would."""
    a, b = eps
    d = squarefree_part(D)
    root = r'\sqrt{%d}' % d
    if a % 2 == 0 and b % 2 == 0:
        a, b = a // 2, b // 2
        return '%d+%s%s' % (a, '' if b == 1 else str(b), root)
    return '(%d+%s%s)/2' % (a, '' if b == 1 else str(b), root)


def comment(D, h, w, eps):
    """The identification a reader wants under the value.

    The field, since D = 12 is Q(sqrt 3) and nobody arrives holding "12"; the
    class number; and what the class number formula makes of them. For D < 0
    that is a closed form short enough to print. For D > 0 it is 2 h log(eps)
    / sqrt D, the same shape on every entry, so the entry gives eps and the
    formula on the table gives the rest -- the comments are counted in the
    size of the entries block, and 302 copies of one formula are not worth
    what they cost there.
    """
    D = ZZ(D)
    if D < 0:
        multiple = QQ(2 * h) / QQ(w)
        if D == -4:
            closed = r'\pi/4'
        elif multiple == 1:
            closed = r'\pi/\sqrt{%d}' % (-D)
        elif multiple.denominator() == 1:
            closed = r'%d\pi/\sqrt{%d}' % (multiple, -D)
        elif multiple.numerator() == 1:
            closed = r'\pi/(%d\sqrt{%d})' % (multiple.denominator(), -D)
        else:
            closed = r'%d\pi/(%d\sqrt{%d})' % (multiple.numerator(),
                                                multiple.denominator(), -D)
        roots = '' if w == 2 else ', $w_K=%d$' % w
        return '$%s$: $h_K=%d$%s, $\\kappa_D=%s$' % (field_name(D), h, roots, closed)
    return '$%s$: $h_K=%d$, $\\varepsilon_K=%s$' % (field_name(D), h, unit_latex(D, eps))


class DedekindZetaResidues(numberdb.Generator):

    table = 'T128'
    parameters = ('D',)
    type = 'R'
    digits = 100
    rigour = 'proven'

    def enumerate(self, bound=BOUND):
        for D in fundamental_discriminants(bound):
            yield {'D': int(D)}

    def value(self, params, digits):
        D = ZZ(params['D'])
        bits = numberdb.bits(digits, losing=WORKING_GUARD)
        kappa = residue(D, bits)
        h, w, eps = field_data(D)
        check = class_number_formula(D, h, w, eps, bits)
        if not (check.is_finite() and kappa.overlaps(check)):
            raise ArithmeticError(
                'D = %s: the digamma sum gives %s and the class number formula '
                '%s; neither is right until the disagreement has a cause'
                % (D, kappa, check))
        entry = {'number': kappa, 'comment': comment(D, h, w, eps)}
        if D == -4:
            #pi/4 is in the corpus already, as a = 1/4 of the rational
            #multiples of pi; say so rather than hold the digits twice unlinked.
            entry['equals'] = r'HREF{Rational_multiples_of_pi#1/4}[$\pi/4$]'
        return entry


if __name__ == '__main__':
    generator = DedekindZetaResidues()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='residues of Dedekind zeta functions of quadratic fields, '
                    'from the digamma sum, each checked against the class '
                    'number formula'))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
