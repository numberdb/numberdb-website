"""Entropy constants of lattice models -- numberdb.org/T153

For a lattice model whose configurations on a finite region of a lattice
with N vertices are counted by Z_N, the entropy constant is
kappa = lim Z_N^(1/N), the number of configurations per site, and the
entropy per site is h = ln kappa. The table holds kappa and h for the
hard-core lattice gas at activity 1 (independent sets: hard squares, hard
hexagons, and the model on the honeycomb lattice and on the line), the ice
model on the square lattice (Eulerian orientations), the dimer model
(perfect matchings) on the square, triangular and honeycomb lattices, and
spanning trees on the square, triangular, honeycomb, kagome, diced,
(3,12^2), (4,8^2), union-jack and simple cubic lattices: 17 rows, 34
entries, with three parameters, `model`, `lattice` and `expression`.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**Three kinds of entry.** Twenty-eight entries are computed here in ball
arithmetic at 100 digits: the closed forms (the golden ratio, (4/3)^(3/2),
Catalan's constant and L(2, chi_-3) through arb's Hurwitz zeta function,
and the spanning-tree constants that Shrock and Wu express through them),
the two one-dimensional integrals that remain after one angle of a
Kasteleyn or Laplacian double integral is integrated in closed form (dimers
on the triangular lattice, spanning trees on (4,8^2)), evaluated with arb's
rigorous integrator, and the hard-hexagon constant, which is Baxter's exact
solution evaluated at activity 1: the root x of -x H(x)^5 / G(x)^5 = 1 is
enclosed by bisection and the Rogers-Ramanujan products are evaluated on
that enclosure with explicit tail bounds. Two entries are heuristic: the
simple-cubic spanning-tree constant is a double integral with a square-root
singularity at one corner, evaluated by nested tanh-sinh quadrature at two
working precisions, keeping the digits both agree on. Four entries are
transcribed: the hard-square and honeycomb hard-core constants are Baxter's
corner-transfer-matrix values, written with the digits Baxter states, and
their logarithms are computed from those intervals.

**What was checked outside this file** before any entry was sent: every
closed form against the OEIS entry that holds it, to every digit listed
there; the hard-hexagon value against Baxter's 55 digits, against the
density rho(1) Baxter gives beside it, and against the degree-24 polynomial
of Joyce as transcribed by MathWorld, which vanishes on the enclosure; the
triangular dimer integral against OEIS A247548; the (4,8^2) integral
against Shrock and Wu's 0.786684(1), with the same reduction applied to
the square lattice as a control returning 4G/pi; the simple-cubic
spanning-tree constant against the closed-walk series ln 6 - sum
W_2m/(2m 36^m) summed to 1.6 million terms and extrapolated, which agrees
with the quadrature to 22 digits and shows that the value 1.6741481(1)
printed by Shrock and Wu is wrong in the fourth decimal.
"""

import sys

import numberdb.sage as numberdb
from numberdb._compare import digits_of
from numberdb._write import to_text
from sage.rings.complex_arb import ComplexBallField
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField
from sage.rings.real_mpfr import RealField

#: Bits of working precision beyond what the written digits need, for the
#: closed forms and the arb integrals. Measured at 100 digits: the widest
#: ball relative to its value is the union-jack spanning-tree constant,
#: exp(2 z_(4,8^2)), at 4.2e-118.
WORKING_GUARD = 64

#: The hard-hexagon row encloses the root x to 10^-(digits+20) and carries
#: tail bounds on a dozen products; measured at 100 digits, the enclosure
#: of kappa has radius 8.2e-120 with this guard, and the enclosure at 30
#: digits contains it.
HARD_HEXAGON_GUARD = 220

#: Decimal working precisions of the two quadratures of the simple-cubic
#: spanning-tree integral; the digits they agree on are written.
SIMPLE_CUBIC_AT = (40, 55)

#: The rows, in the order the table lists them.
ROWS = [
    ('hard-core', 'line'), ('hard-core', 'square'), ('hard-core', 'triangular'), ('hard-core', 'honeycomb'),
    ('ice', 'square'),
    ('dimer', 'square'), ('dimer', 'triangular'), ('dimer', 'honeycomb'),
    ('spanning-tree', 'square'), ('spanning-tree', 'triangular'), ('spanning-tree', 'honeycomb'),
    ('spanning-tree', 'kagome'), ('spanning-tree', 'D-3-6-3-6'), ('spanning-tree', '3-12-12'),
    ('spanning-tree', '4-8-8'), ('spanning-tree', 'D-4-8-8'), ('spanning-tree', 'sc'),
]

#: Baxter's corner-transfer-matrix values (Annals of Combinatorics 3, 1999),
#: as printed: 43 decimals for hard squares, which he believes correct to
#: the last place; 38 for the honeycomb lattice, of which "the last two or
#: three digits should be treated with caution", so 35 are kept.
BAXTER_SQUARE = '1.5030480824753322643220663294755536893857810'
BAXTER_HONEYCOMB = '1.54644070878756141848902270530472278'

#: Liang's rigorous bounds on the hard-square constant (arXiv:2507.04007,
#: eq. 27), which prove Baxter's first 25 decimals: the two agree through
#: ...20663 and part in the 26th place, and the paper prints them with a
#: space before "four non-exact digits".
LIANG_BOUNDS = ('1.50304808247533226432206632947', '1.50304808247533226432206633030')

GOLDEN = 'Golden_ratio'
REGULATORS = 'Regulators_of_real_quadratic_fields'
L_VALUES = 'Values_of_Dirichlet_L-functions_at_positive_integers'

_CACHE = {}


def fields(bits):
    return RealBallField(bits), ComplexBallField(bits)


def catalan(RBF):
    """G = L(2, chi_-4) = (zeta(2, 1/4) - zeta(2, 3/4)) / 16, Hurwitz zeta in arb."""
    return (RBF(2).zeta(RBF(QQ(1) / 4)) - RBF(2).zeta(RBF(QQ(3) / 4))) / 16


def l_chi_minus_3(RBF):
    """L(2, chi_-3) = (zeta(2, 1/3) - zeta(2, 2/3)) / 9."""
    return (RBF(2).zeta(RBF(QQ(1) / 3)) - RBF(2).zeta(RBF(QQ(2) / 3))) / 9


def z_triangular(RBF):
    """Spanning trees on the triangular lattice, Shrock and Wu (2.19):
    (3 sqrt 3 / pi) sum over n coprime to 6 of chi_-3(n) / n^2 = (15 sqrt 3 / (4 pi)) L(2, chi_-3)."""
    return 15 * RBF(3).sqrt() / (4 * RBF.pi()) * l_chi_minus_3(RBF)


def integral(CBF, integrand, a, b):
    """arb's rigorous integral of an analytic integrand over [a, b], real part."""
    value = CBF.integral(integrand, a, b)
    if not value.imag().contains_zero():
        raise ArithmeticError('the integral came out complex: %s' % value)
    return value.real()


def dimer_triangular_entropy(bits):
    """Per site. Fendley, Moessner and Sondhi's Kasteleyn integral
    (1/(16 pi^2)) int int ln(6 + 2 cos u + 2 cos v + 2 cos(u+v)) du dv; the v
    integral is (2 pi) ln((A + sqrt(A^2 - B^2))/2) with A = 6 + 2 cos u,
    B = 4 cos(u/2), and A^2 - B^2 >= 16 on the path."""
    RBF, CBF = fields(bits)
    pi = RBF.pi()

    def f(u, analytic):
        A = 6 + 2 * u.cos()
        B = 4 * (u / 2).cos()
        return ((A + (A * A - B * B).sqrt(analytic=analytic)) / 2).log(analytic=analytic)

    return integral(CBF, f, -pi, pi) / (8 * pi)


def z_4_8_8(bits):
    """Spanning trees on (4,8^2), Shrock and Wu (4.11):
    (1/4) ln 2 + (1/(4 pi)) int_0^pi ln(7 - 3 cos t + 4 sin(t/2) sqrt(5 - cos t)) dt."""
    RBF, CBF = fields(bits)
    pi = RBF.pi()

    def f(t, analytic):
        c = t.cos()
        return (7 - 3 * c + 4 * (t / 2).sin() * (5 - c).sqrt(analytic=analytic)).log(analytic=analytic)

    return RBF(2).log() / 4 + integral(CBF, f, CBF(0), pi) / (4 * pi)


class HardHexagons(object):
    """Baxter's solution of the hard-hexagon model for 0 < z < z_c, in the
    parametrisation x in (-1, 0):

        z = -x H(x)^5 / G(x)^5,
        kappa = H(x)^3 Q(x^5)^2 / G(x)^2 * prod (1-x^{6n-4})(1-x^{6n-3})^2(1-x^{6n-2})
                                                 / ((1-x^{6n-5})(1-x^{6n-1})(1-x^{6n})^2),

    with G(x) = prod 1/((1-x^{5n-4})(1-x^{5n-1})), H(x) = prod 1/((1-x^{5n-3})(1-x^{5n-2}))
    the Rogers-Ramanujan products and Q(x) = prod (1-x^n). Every product is
    truncated where the omitted factors lie within the working precision of
    1 and multiplied by a ball enclosing the omitted tail, so kappa(X) on an
    enclosure X of the root of z(x) = 1 is an enclosure of kappa(1)."""

    def __init__(self, bits):
        self.RBF = RealBallField(bits)
        self.RR = RealField(bits)
        self.bits = bits

    def tail(self, x_abs, M):
        """A ball around 1 enclosing prod_{m > M} (1 - x^m) over any set of
        exponents m > M, for |x| <= 1/2: |ln(1 - y)| <= 2|y| there."""
        if not x_abs <= 0.5:
            raise ValueError('the tail bound needs |x| <= 1/2; got %s' % x_abs)
        return self.RBF(1).add_error(4 * x_abs ** (M + 1) / (1 - x_abs))

    def terms(self, x):
        xa = self.RR(x.abs().upper())
        return int((self.bits + 40) * self.RR(2).log() / (1 / xa).log()) + 5

    def qprod(self, x, exponent, N):
        p = self.RBF(1)
        for n in range(1, N + 1):
            p *= 1 - x ** exponent(n)
        return p * self.tail(x.abs().upper(), exponent(N))

    def G(self, x):
        N = self.terms(x)
        return 1 / (self.qprod(x, lambda n: 5 * n - 4, N) * self.qprod(x, lambda n: 5 * n - 1, N))

    def H(self, x):
        N = self.terms(x)
        return 1 / (self.qprod(x, lambda n: 5 * n - 3, N) * self.qprod(x, lambda n: 5 * n - 2, N))

    def Q(self, x):
        return self.qprod(x, lambda n: n, self.terms(x))

    def z(self, x):
        return -x * self.H(x) ** 5 / self.G(x) ** 5

    def kappa(self, x):
        N = self.terms(x)
        num = (self.qprod(x, lambda n: 6 * n - 4, N) * self.qprod(x, lambda n: 6 * n - 3, N) ** 2
               * self.qprod(x, lambda n: 6 * n - 2, N))
        den = (self.qprod(x, lambda n: 6 * n - 5, N) * self.qprod(x, lambda n: 6 * n - 1, N)
               * self.qprod(x, lambda n: 6 * n, N) ** 2)
        return self.H(x) ** 3 * self.Q(x ** 5) ** 2 / self.G(x) ** 2 * num / den

    def root(self, delta):
        """An enclosure of width 2 delta of the x in (-1/2, -1/20) with z(x) = 1:
        bisection on thin balls, then a sign change of z - 1 across the ends."""
        RBF, RR = self.RBF, self.RR
        lo, hi = RR(-0.5), RR(-0.05)
        if not (self.z(RBF(lo)) > 1 and self.z(RBF(hi)) < 1):
            raise ArithmeticError('z(x) - 1 does not change sign on the bracket')
        while hi - lo > delta / 4:
            mid = (lo + hi) / 2
            v = self.z(RBF(mid)) - 1
            if v.contains_zero():
                raise ArithmeticError('the sign of z(x) - 1 could not be decided at x = %s' % mid)
            if v > 0:
                lo = mid          # z grows with -x, so a value above 1 puts the root nearer 0
            else:
                hi = mid
        x0 = (lo + hi) / 2
        below, above = self.z(RBF(x0 - delta)) - 1, self.z(RBF(x0 + delta)) - 1
        if below.contains_zero() or above.contains_zero() or bool(below > 0) == bool(above > 0):
            raise ArithmeticError('no sign change of z(x) - 1 across x0 +/- delta')
        return RBF(x0).add_error(delta)

    def constant(self, digits):
        X = self.root(self.RR(10) ** (-(digits + 20)))
        kappa = self.kappa(X)
        if not (1 < kappa < 2):
            raise ArithmeticError('the hard-hexagon constant came out as %s' % kappa)
        return kappa


def hard_hexagon_constant(digits):
    key = ('hh', digits)
    if key not in _CACHE:
        bits = numberdb.bits(digits, losing=HARD_HEXAGON_GUARD)
        _CACHE[key] = HardHexagons(bits).constant(digits)
    return _CACHE[key]


def simple_cubic_entropy(working, exponentiate=False):
    """z_sc = (1/pi^2) int_0^pi int_0^pi arccosh(3 - cos a - cos b) da db, the
    Laplacian integral ln 6 + (2 pi)^-3 int ln(1 - (cos t1 + cos t2 + cos t3)/3)
    after the t3 integration; nested tanh-sinh quadrature in mpmath at
    `working` decimal digits. Returns a string carrying that many digits."""
    import mpmath
    key = ('sc', working)
    if key not in _CACHE:
        saved = mpmath.mp.dps
        try:
            mpmath.mp.dps = working + 10
            f = lambda a, b: mpmath.acosh(3 - mpmath.cos(a) - mpmath.cos(b))       # noqa: E731
            value = mpmath.quad(lambda a: mpmath.quad(lambda b: f(a, b), [0, mpmath.pi]),
                                [0, mpmath.pi]) / mpmath.pi ** 2
            _CACHE[key] = (mpmath.nstr(value, working), mpmath.nstr(mpmath.exp(value), working))
        finally:
            mpmath.mp.dps = saved
    return _CACHE[key][1 if exponentiate else 0]


def transcribed(RBF, text):
    """A ball containing the interval a written decimal denotes: the last
    digit may be off by one."""
    places = len(text.split('.')[1])
    return RBF(RealField(RBF.precision())(text)).add_error(RBF(10) ** (-places))


class Row(object):
    """One row: its entropy h and its constant kappa as balls, an interval, or
    a string, and its comments."""

    def __init__(self, model, lattice):
        if (model, lattice) not in ROWS:
            raise ValueError('no row for %s on %s' % (model, lattice))
        self.model, self.lattice = model, lattice

    def values(self, digits):
        """(kappa, h), each a ball, a real interval, or a decimal string."""
        bits = numberdb.bits(digits, losing=WORKING_GUARD)
        RBF, CBF = fields(bits)
        key = (self.model, self.lattice)
        if key == ('hard-core', 'line'):
            phi = (1 + RBF(5).sqrt()) / 2
            return phi, phi.log()
        if key == ('hard-core', 'square'):
            lo, hi = LIANG_BOUNDS
            ball = transcribed(RBF, BAXTER_SQUARE)
            if not (RBF(RealField(bits)(lo)) < ball < RBF(RealField(bits)(hi))):
                raise ValueError("Baxter's hard-square value is outside Liang's bounds")
            return BAXTER_SQUARE, ball.log()
        if key == ('hard-core', 'triangular'):
            kappa = hard_hexagon_constant(digits)
            return kappa, kappa.log()
        if key == ('hard-core', 'honeycomb'):
            return BAXTER_HONEYCOMB, transcribed(RBF, BAXTER_HONEYCOMB).log()
        if key == ('ice', 'square'):
            kappa = (RBF(4) / 3) ** (QQ(3) / 2)
            return kappa, kappa.log()
        if key == ('dimer', 'square'):
            h = catalan(RBF) / RBF.pi()
        elif key == ('dimer', 'triangular'):
            h = dimer_triangular_entropy(bits)
        elif key == ('dimer', 'honeycomb'):
            h = 3 * RBF(3).sqrt() / (8 * RBF.pi()) * l_chi_minus_3(RBF)
        elif key == ('spanning-tree', 'square'):
            h = 4 * catalan(RBF) / RBF.pi()
        elif key == ('spanning-tree', 'triangular'):
            h = z_triangular(RBF)
        elif key == ('spanning-tree', 'honeycomb'):
            h = z_triangular(RBF) / 2
        elif key in (('spanning-tree', 'kagome'), ('spanning-tree', 'D-3-6-3-6')):
            h = (z_triangular(RBF) + RBF(6).log()) / 3
        elif key == ('spanning-tree', '3-12-12'):
            h = (z_triangular(RBF) + RBF(15).log()) / 6
        elif key == ('spanning-tree', '4-8-8'):
            h = z_4_8_8(bits)
        elif key == ('spanning-tree', 'D-4-8-8'):
            h = 2 * z_4_8_8(bits)
        elif key == ('spanning-tree', 'sc'):
            h = numberdb.agreeing(lambda w: simple_cubic_entropy(w), at=SIMPLE_CUBIC_AT)
            kappa = numberdb.agreeing(lambda w: simple_cubic_entropy(w, exponentiate=True), at=SIMPLE_CUBIC_AT)
            return kappa, h
        else:
            raise ValueError('no computation for %s on %s' % key)
        if not (0 < h < 3):
            raise ArithmeticError('%s on %s: entropy %s is not a finite ball in (0, 3)' % (self.model, self.lattice, h))
        return h.exp(), h

    def comments(self):
        return COMMENT[(self.model, self.lattice)]

    def entry(self, expression, digits):
        kappa, h = self.values(digits)
        number = kappa if expression == 'kappa' else h
        entry = {'number': number, 'comment': self.comments()[0 if expression == 'kappa' else 1]}
        claimed = digits_of(to_text(number, digits))
        if claimed < digits:
            entry['digits'] = claimed
        if (self.model, self.lattice) == ('hard-core', 'line'):
            entry['equals'] = ('HREF{%s#phi}' % GOLDEN if expression == 'kappa'
                               else 'HREF{%s#5}' % REGULATORS)
        return entry


#: (comment on kappa, comment on h) for each row.
COMMENT = {
    ('hard-core', 'line'): (
        r'$\kappa=\varphi=\frac{1+\sqrt5}{2}$, the HREF{%s}[golden ratio]: the path on $n$ vertices has '
        r'$F_{n+2}$ independent sets, and the one-dimensional hard-core gas is the golden-mean shift.' % GOLDEN,
        r'$h=\ln\varphi$, the topological entropy of the golden-mean shift and the '
        r'HREF{%s#5}[regulator of $\mathbb{Q}(\sqrt5)$].' % REGULATORS),
    ('hard-core', 'square'): (
        r'The hard-square entropy constant, OEIS A085850 CITE{OEIShs}: not known in closed form; the $43$ decimals '
        r"are Baxter's corner-transfer-matrix value CITE{Baxter99}, and the first $25$ are proved by the bounds "
        r'$1.50304808247533226432206632947<\kappa<1.50304808247533226432206633030$ of Liang CITE{Liang}.',
        r"$h=\ln\kappa$ from Baxter's $43$ decimals CITE{Baxter99}, OEIS A379041 CITE{OEIShsh}; the topological "
        r'entropy of the two-dimensional golden-mean shift, the standard $\mathbb{Z}^2$ shift of finite type '
        r'whose entropy has no known closed form.'),
    ('hard-core', 'triangular'): (
        r"The hard-hexagon entropy constant, OEIS A085851 CITE{OEIShh}, from Baxter's exact solution "
        r'CITE{Baxter80} evaluated at activity $z=1$; an algebraic number of degree $24$ CITE{Joyce}, the root '
        r'of the polynomial CITE{formula-hard-hexagon}. Baxter gives $55$ decimals CITE{Baxter99}; the last '
        r'digit listed in A085851 is one too small.',
        r'$h=\ln\kappa$ from the exact solution; Metcalf and Yang conjectured $h=\frac13$, which '
        r'Baxter and Tsang refuted before Baxter solved the model CITE{Baxter99}.'),
    ('hard-core', 'honeycomb'): (
        r"Baxter's corner-transfer-matrix value CITE{Baxter99}, printed there to $38$ decimals of which "
        r'"the last two or three digits should be treated with caution", so $35$ are kept.',
        r"$h=\ln\kappa$ from the $35$ decimals kept of Baxter's value CITE{Baxter99}."),
    ('ice', 'square'): (
        r"$\kappa=\left(\frac43\right)^{3/2}=\frac{8\sqrt3}{9}$, Lieb's square ice constant CITE{Lieb}, "
        r'OEIS A118273 CITE{OEISice}; the growth rate of the proper $3$-colourings of the square lattice.',
        r'$h=\frac32\ln\frac43$, the residual entropy of square ice per vertex in units of '
        r"Boltzmann's constant CITE{Lieb}."),
    ('dimer', 'square'): (
        r"$\kappa=e^{G/\pi}$ with $G$ Catalan's constant CITE{Kasteleyn} CITE{TemperleyFisher}, OEIS A097469 "
        r'CITE{OEISdimer}; the number of domino tilings per cell of the board, that is per vertex of the lattice. '
        r'Per dimer the constant is $\kappa^2=e^{2G/\pi}=1.7916228\ldots$, OEIS A130834 CITE{OEISdimer2}.',
        r'$h=G/\pi$ CITE{Kasteleyn}, OEIS A143233 CITE{OEISdimerh}; $G=L(2,\chi_{-4})$ is in the '
        r'HREF{%s}[table of Dirichlet $L$-values].' % L_VALUES),
    ('dimer', 'triangular'): (
        r'$\kappa=e^{h}$ with $h$ the Kasteleyn integral CITE{formula-dimer-triangular} of Fendley, Moessner '
        r'and Sondhi CITE{FMS}; per dimer the constant is $\kappa^2=2.3565273\ldots$, OEIS A247548 CITE{OEISdimertri}.',
        r'$h=\frac{1}{16\pi^2}\int_{-\pi}^{\pi}\!\int_{-\pi}^{\pi}\ln\left(6+2\cos u+2\cos v+2\cos(u+v)\right)du\,dv$ '
        r'CITE{FMS}, who give $0.4286$.'),
    ('dimer', 'honeycomb'): (
        r'$\kappa=e^{h}$; the number of lozenge tilings per vertex of the honeycomb lattice CITE{Kasteleyn63}.',
        r'$h=\frac{3\sqrt3}{8\pi}L(2,\chi_{-3})=\frac12 m(1+x+y)$, half the Mahler measure of $1+x+y$ '
        r'CITE{Smyth}, and one tenth of the spanning-tree constant of the triangular lattice; $L(2,\chi_{-3})$ '
        r'is in the HREF{%s}[table of Dirichlet $L$-values].' % L_VALUES),
    ('spanning-tree', 'square'): (
        r'$\kappa=e^{4G/\pi}$, OEIS A229728 CITE{OEISste}: spanning trees per vertex of the square lattice.',
        r'$z_{\mathrm{sq}}=\frac{4G}{\pi}=\frac4\pi\left(1-\frac1{3^2}+\frac1{5^2}-\cdots\right)$ CITE{Wu77} '
        r'CITE{ShrockWu}, OEIS A218387 CITE{OEISst}; the Mahler measure of $4+x+x^{-1}+y+y^{-1}$ CITE{Guttmann}.'),
    ('spanning-tree', 'triangular'): (
        r'$\kappa=e^{z_{\mathrm{tri}}}$.',
        r'$z_{\mathrm{tri}}=\frac{3\sqrt3}{\pi}\left(1-\frac1{5^2}+\frac1{7^2}-\frac1{11^2}+\frac1{13^2}-\cdots\right)'
        r'=\frac{15\sqrt3}{4\pi}L(2,\chi_{-3})$ CITE{Wu77} CITE{ShrockWu}, OEIS A245725 CITE{OEISsttri}.'),
    ('spanning-tree', 'honeycomb'): (
        r'$\kappa=e^{z_{\mathrm{hc}}}$.',
        r'$z_{\mathrm{hc}}=\frac12 z_{\mathrm{tri}}$ CITE{ShrockWu}, by the duality CITE{formula-duality}, '
        r'OEIS A245737 CITE{OEISsthc}.'),
    ('spanning-tree', 'kagome'): (
        r'$\kappa=e^{z_{\mathrm{kag}}}$.',
        r'$z_{\mathrm{kag}}=\frac13\left(z_{\mathrm{tri}}+\ln 6\right)$ CITE{ShrockWu}, OEIS A245739 CITE{OEISstkag}.'),
    ('spanning-tree', 'D-3-6-3-6'): (
        r'$\kappa=e^{z_{\mathrm{kag}}}$: the diced lattice is the planar dual of the kagome lattice and has the '
        r'same vertex density, so the two share their constant CITE{ShrockWu}.',
        r'$z_{\mathrm{diced}}=z_{\mathrm{kag}}$ CITE{ShrockWu}, by the duality CITE{formula-duality}.'),
    ('spanning-tree', '3-12-12'): (
        r'$\kappa=e^{z}$ with $z=\frac16\left(z_{\mathrm{tri}}+\ln 15\right)$ CITE{ShrockWu}.',
        r'$z=\frac16\left(z_{\mathrm{tri}}+\ln 15\right)$ CITE{ShrockWu}, who give $0.7205633$.'),
    ('spanning-tree', '4-8-8'): (
        r'$\kappa=e^{z}$ with $z$ the integral CITE{formula-spanning-4-8-8} of Shrock and Wu CITE{ShrockWu}.',
        r'$z=\frac14\ln2+\frac1{4\pi}\int_0^{\pi}\ln\left(7-3\cos\theta+4\sin\frac\theta2\sqrt{5-\cos\theta}\right)d\theta$ '
        r'CITE{ShrockWu}, who give $0.786684(1)$.'),
    ('spanning-tree', 'D-4-8-8'): (
        r'$\kappa=e^{z}$ with $z$ twice the constant of $(4,8^2)$, its planar dual CITE{ShrockWu}.',
        r'$z_{\mathrm{UJ}}=2z_{(4,8^2)}$ CITE{ShrockWu}, by the duality CITE{formula-duality}; they give $1.573368(2)$.'),
    ('spanning-tree', 'sc'): (
        r'$\kappa=e^{z_{\mathrm{sc}}}$, spanning trees per vertex of the simple cubic lattice.',
        r'$z_{\mathrm{sc}}=\frac1{\pi^2}\int_0^{\pi}\!\int_0^{\pi}\operatorname{arccosh}(3-\cos\theta_1-\cos\theta_2)\,'
        r'd\theta_1\,d\theta_2$ CITE{formula-spanning-cubic}; the value $1.6741481(1)$ printed by Shrock and Wu '
        r'CITE{ShrockWu} differs from it in the fourth decimal, and the closed-walk series '
        r'$\ln 6-\sum_{m\geq1}W_{2m}/(2m\cdot 36^m)$ gives $1.6733893029701967322834\ldots$.'),
}


class EntropyConstants(numberdb.Generator):

    table = 'T153'
    parameters = ('model', 'lattice', 'expression')
    type = 'R'
    digits = 100
    rigour = 'heuristic'

    def enumerate(self):
        for model, lattice in ROWS:
            for expression in ('kappa', 'entropy'):
                yield {'model': model, 'lattice': lattice, 'expression': expression}

    def value(self, params, digits):
        row = Row(params['model'], params['lattice'])
        if params['expression'] not in ('kappa', 'entropy'):
            raise ValueError('expression must be kappa or entropy, not %r' % params['expression'])
        return row.entry(params['expression'], digits)


if __name__ == '__main__':
    generator = EntropyConstants()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='entropy constants kappa and h = ln kappa per site of the hard-core, ice, dimer '
                    'and spanning-tree models on lattices: closed forms and integrals in ball '
                    'arithmetic at 100 digits, the hard-hexagon constant from Baxter\'s exact '
                    'solution, the simple-cubic spanning-tree constant by quadrature at two '
                    'precisions, and Baxter\'s hard-square and honeycomb values transcribed'))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
