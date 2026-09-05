"""Densities of the densest known lattice sphere packings -- numberdb.org/T148

For each dimension n, the packing density Delta_n and the centre density
delta_n of the densest lattice sphere packing known in R^n, per the table of
densest packings of the Nebe-Sloane Catalogue of Lattices (last revised in
February 2012):

    delta_n = rho^n / sqrt(det L)          rho = sqrt(mu)/2 the packing radius
    Delta_n = V_n delta_n                  V_n = pi^(n/2) / Gamma(n/2 + 1)

under the parameters `n` and `expression` (density or centre).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**Where the values come from.** The catalogue's table gives the centre density
of the record lattice in every dimension n <= 48 in closed form (1/16 sqrt 3,
3^16/2^24, 3^16/(2^20 sqrt 14), ...), and every one of those is the square
root of a rational number. That rational, delta_n^2, is the datum this file
carries, transcribed from the page: for n <= 24 it is 1/det Lambda_n with the
laminated lattice scaled to minimal norm 4 (OEIS A028921), except in
dimensions 11, 12 and 13 where the Coxeter-Todd lattice K_12 and its
laminations K_11 and K_13 are denser (det 972, 729, 972). Beyond n = 48 the
catalogue's table is sporadic and partly approximate, so the table stops
there.

**Exact arithmetic up to the last step.** delta_n is returned as an exact
rational when delta_n^2 is a square (n = 1, 4, 7, 8, 12, 16, 17, 20, 23, 24,
28, 32, 36, 38, 42, 44, 47, 48) and as a ball otherwise; Delta_n is the ball
for pi^floor(n/2) times the exact rational V_n / pi^floor(n/2) times delta_n,
or the exact 1 for n = 1. No division of Python integers occurs anywhere in
this file; every quotient is between Sage rationals.

**These digits are proven.** With the guard below, the widest ball in the
table, relative to its value, has radius 6.7e-119 (measured at 100 digits
over every entry: Delta_46), so 100 digits are supported with room.

**What was checked outside this file** when the table was made, before any
entry was sent: the same 48 rationals parsed by a separate program from the
page's HTML; the page's own decimals; for n <= 26 and n = 30, 31, 32, 36, 48
the determinant and minimal norm of a Gram matrix of the record lattice
(Cartan matrices, the catalogue's GRAM blocks, PARI's qfminim); the OEIS
expansions of Delta_2, Delta_3, Delta_4, Delta_5, Delta_6, Delta_7, Delta_8,
Delta_24, delta_5 and delta_6; the 36 record densities of Table 1 of Cohn's
2017 survey, which come from Table I.1 of Conway and Sloane; the stored
digits of the table of unit-ball volumes and of the table of packing
densities of the classical lattices, which holds the same numbers for n <= 24;
and the symmetry delta_(24-n) = delta_n.
"""

import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField

#: Bits of working precision beyond what the written digits need; the
#: measurement is in the docstring of the table and in its rigour details.
WORKING_GUARD = 64

#: The largest dimension listed: where the catalogue's closed forms end.
TOP = 48

EXPRESSIONS = ('density', 'centre')

#: Determinants of the laminated lattices Lambda_n scaled to minimal norm 4,
#: n = 0, ..., 24: OEIS A028921. delta(Lambda_n) = 1/sqrt(det Lambda_n).
LAMINATED_DET = [1, 4, 12, 32, 64, 128, 192, 256, 256, 512, 768, 1024, 1024,
                 1024, 768, 512, 256, 256, 192, 128, 64, 32, 12, 4, 1]


def _p(base, twice_exponent):
    """base^(twice_exponent/2) squared, i.e. base^twice_exponent, as a
    rational: the page writes 3^13.5 and 2^22.5, and this keeps every
    exponent an integer."""
    return QQ(base) ** ZZ(twice_exponent)


#: delta_n^2 for 1 <= n <= 48, transcribed from the catalogue's table of
#: densest packings: the record lattice's centre density, squared.
DELTA_SQ = {}
for _n in range(1, 25):
    DELTA_SQ[_n] = QQ(1) / LAMINATED_DET[_n]
DELTA_SQ[11] = QQ(1) / 972                  # K_11:  1/(18 sqrt 3)
DELTA_SQ[12] = QQ(1) / 729                  # K_12:  1/27
DELTA_SQ[13] = QQ(1) / 972                  # K_13:  1/(18 sqrt 3)
DELTA_SQ.update({
    25: QQ(1) / 2,                          # Lambda_25:  1/sqrt 2
    26: QQ(1) / 3,                          # Lambda_26, T_26:  1/sqrt 3
    27: QQ(1) / 3,                          # B_27:  1/sqrt 3
    28: QQ(4) / 9,                          # B_28:  2/3
    29: QQ(1) / 3,                          # B_29:  1/sqrt 3
    30: _p(3, 27) / _p(2, 44),              # Q_30:  3^13.5 / 2^22
    31: _p(3, 30) / _p(2, 47),              # Q_31:  3^15 / 2^23.5
    32: _p(3, 32) / _p(2, 48),              # Q_32:  3^16 / 2^24
    33: _p(3, 33) / _p(2, 50),              # Q_33:  3^16.5 / 2^25
    34: _p(3, 33) / _p(2, 50),              # Q_34:  3^16.5 / 2^25
    35: QQ(8),                              # B_35:  2 sqrt 2
    36: _p(2, 36) / _p(3, 20),              # KP_36:  2^18 / 3^10
    37: QQ(32),                             # D_37:  4 sqrt 2
    38: QQ(64),                             # D_38:  8
    39: _p(3, 32) / (_p(2, 40) * 14),       # section of P_48p:  3^16 / (2^20 sqrt 14)
    40: _p(3, 34) / _p(2, 45),              # 3^17 / 2^22.5
    41: _p(3, 34) / _p(2, 43),              # 3^17 / 2^21.5
    42: _p(3, 36) / _p(2, 44),              # 3^18 / 2^22
    43: _p(3, 38) / _p(2, 45),              # 3^19 / 2^22.5
    44: _p(3, 40) / _p(2, 46),              # 3^20 / 2^23
    45: _p(3, 42) / _p(2, 47),              # 3^21 / 2^23.5
    46: _p(3, 43) / _p(2, 46),              # 3^21.5 / 2^23
    47: _p(3, 46) / _p(2, 48),              # 3^23 / 2^24
    48: _p(3, 48) / _p(2, 48),              # P_48n, P_48p, P_48q:  3^24 / 2^24
})

#: The record lattice, as a phrase for the entry comment.
LATTICE = {
    1: r'$\Lambda_1=\mathbb{Z}$',
    2: r'$\Lambda_2=A_2$, the hexagonal lattice',
    3: r'$\Lambda_3=A_3=D_3$, the face-centred cubic lattice',
    4: r'$\Lambda_4=D_4$',
    5: r'$\Lambda_5=D_5$',
    6: r'$\Lambda_6=E_6$',
    7: r'$\Lambda_7=E_7$',
    8: r'$\Lambda_8=E_8$',
    11: r'$K_{11}$, a lamination of the Coxeter–Todd lattice $K_{12}$',
    12: r'$K_{12}$, the Coxeter–Todd lattice',
    13: r'$K_{13}$, a lamination of the Coxeter–Todd lattice $K_{12}$',
    16: r'$\Lambda_{16}=BW_{16}$, the Barnes–Wall lattice',
    24: r'$\Lambda_{24}$, the Leech lattice',
    26: r'$\Lambda_{26}$ and $T_{26}$',
    27: r"Bacher's lattice $B_{27}$ CITE{Bacher}",
    28: r"Bacher's lattice $B_{28}$ CITE{Bacher}",
    29: r"Bacher's lattice $B_{29}$ CITE{Bacher}",
    30: r"$Q_{30}$, a section of Quebbemann's lattice $Q_{32}$ CITE{Quebbemann}",
    31: r"$Q_{31}$, a section of Quebbemann's lattice $Q_{32}$ CITE{Quebbemann}",
    32: r"Quebbemann's lattice $Q_{32}$ CITE{Quebbemann}, and others",
    33: r'$Q_{33}$, due to Elkies CITE{Catalogue-density}',
    34: r'$Q_{34}$, due to Elkies CITE{Catalogue-density}',
    35: r'$B_{35}$ CITE{Catalogue-density}',
    36: r'the Kschischang–Pasupathy lattice $KP_{36}$ CITE{KP}',
    37: r'the lattice the catalogue calls $D_{37}$ CITE{Catalogue-density}, which is not the root lattice',
    38: r'the lattice the catalogue calls $D_{38}$ CITE{Catalogue-density}, which is not the root lattice',
    48: r'$P_{48n}$, $P_{48p}$ and $P_{48q}$, even unimodular lattices of minimal norm $6$',
}
for _n in (9, 10, 14, 15, 17, 18, 19, 20, 21, 22, 23, 25):
    LATTICE[_n] = r'$\Lambda_{%d}$' % _n
for _n in range(39, 48):
    LATTICE[_n] = r'a section of $P_{48p}$'

#: Where the record is proven: 'lattice' for the densest lattice packing of
#: its dimension, 'all' for the densest packing of any kind, with the
#: reference keys of the table document.
OPTIMAL_LATTICE = {1: None, 2: 'Lagrange', 3: 'Gauss', 4: 'KZ', 5: 'KZ',
                   6: 'Blichfeldt', 7: 'Blichfeldt', 8: 'Blichfeldt', 9: 'DSvW',
                   24: 'CohnKumar'}
OPTIMAL_ALL = {1: None, 2: 'ThueFejesToth', 3: 'Hales', 8: 'Viazovska', 24: 'CKMRV'}

#: Dimensions in which a nonlattice packing denser than every lattice
#: packing known is known: (name, delta^2 exact or None, the source's
#: decimal centre density where no closed form is given, reference key).
#: The catalogue's table of February 2012 names P_10c, P_11a, P_13a, B_18,
#: B_20, R_22, B*_27, B*_28, B*_29, T_30 and T_44 to T_47; the antipode
#: packings of Chen, Hu, Li, Wang and Wu (2025) are denser than B_20 and
#: T_44, T_45, T_47 and beat the laminated lattices in dimensions 19, 21
#: and 23, where the 2012 table listed no nonlattice packing.
NONLATTICE = {
    10: (r'P_{10c}', _p(5, 2) / _p(2, 14), None, 'Catalogue-density'),
    11: (r'P_{11a}', _p(9, 2) / _p(2, 16), None, 'Catalogue-density'),
    13: (r'P_{13a}', _p(9, 2) / _p(2, 16), None, 'Catalogue-density'),
    18: (r'B_{18}', _p(3, 18) / _p(4, 18), None, 'BierbrauerEdel'),
    19: (r'A_{19}', _p(13, 19) / (_p(3, 18) * _p(5, 21)), None, 'Antipode2025'),
    20: (r'A_{20}', _p(3, 40) / (_p(2, 20) * _p(5, 21)), None, 'Antipode2025'),
    21: (r'A_{21}', _p(43, 21) / (_p(2, 82) * _p(3, 23)), None, 'Antipode2025'),
    22: (r'R_{22}', None, '0.33254', 'Antipode'),
    23: (r'A_{23}', _p(23, 23) / (_p(2, 68) * _p(3, 24)), None, 'Antipode2025'),
    27: (r'B_{27}^{*}', QQ(1) / 2, None, 'VardyDoubling'),
    28: (r'B_{28}^{*}', QQ(1), None, 'VardyDoubling'),
    29: (r'B_{29}^{*}', QQ(1) / 2, None, 'VardyDoubling'),
    30: (r'T_{30}', QQ(1), None, 'VardyDoubling'),
    44: (r'A_{44}', _p(157, 44) / (_p(2, 44) * _p(5, 43) * _p(11, 46)), None, 'Antipode2025'),
    45: (r'A_{45}', _p(23, 45) / _p(2, 183), None, 'Antipode2025'),
    46: (r'T_{46}', _p(13, 46) / _p(3, 93), None, 'Antipode'),
    47: (r'A_{47}', _p(47, 47) / _p(2, 236), None, 'Antipode2025'),
}

#: The nonlattice packings the catalogue's 2012 table names where a denser
#: one is known now, for the entry comment: (name, delta^2, key).
NONLATTICE_2012 = {
    20: (r'B_{20}', _p(7, 20) / _p(2, 62), 'Vardy20'),
    44: (r'T_{44}', _p(17, 44) / (_p(2, 86) * _p(3, 48)), 'Antipode'),
    45: (r'T_{45}', _p(17, 45) / (_p(2, 88) * _p(3, 48)), 'Antipode'),
    47: (r'T_{47}', _p(35, 47) / (_p(2, 140) * _p(3, 48)), 'Antipode'),
}

#: Where the corpus already holds the value: the same lattice's row in the
#: table of packing densities of the classical lattices (family, n, in its
#: identity order), and the quadratic irrationals 1/sqrt 2 and 1/sqrt 3 in
#: the table of algebraic numbers of degree 2 (addresses read off the
#: stored documents).
CLASSICAL = 'Packing_densities_and_Hermite_numbers_of_the_classical_lattices'
CLASSICAL_ROW = {1: 'Z,1', 2: 'A,2', 3: 'A,3', 4: 'D,4', 5: 'D,5', 6: 'E,6',
                 7: 'E,7', 8: 'E,8', 12: 'K,12'}
for _n in (9, 10, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24):
    CLASSICAL_ROW[_n] = 'Lambda,%d' % _n
QUADRATIC = {25: 'HREF{Algebraic_numbers_of_degree_2#2,0,-1,2}',
             26: 'HREF{Algebraic_numbers_of_degree_2#3,0,-1,2}',
             27: 'HREF{Algebraic_numbers_of_degree_2#3,0,-1,2}',
             29: 'HREF{Algebraic_numbers_of_degree_2#3,0,-1,2}'}


def ball_volume_over_pi_power(n):
    """V_n / pi^floor(n/2) as an exact rational: 1/k! for n = 2k and
    2^(2k+1) k! / (2k+1)! for n = 2k+1."""
    n = int(n)
    k = n // 2
    kf = ZZ(1)
    for i in range(2, k + 1):
        kf *= i
    if n % 2 == 0:
        return QQ(1) / kf
    nf = ZZ(1)
    for i in range(2, n + 1):
        nf *= i
    return QQ(2) ** (2 * k + 1) * QQ(kf) / QQ(nf)


def sqrt_exact_or_ball(r, RBF):
    r = QQ(r)
    if r.is_square():
        return r.sqrt()
    return RBF(r).sqrt()


def density_from_centre(n, delta, RBF):
    """Delta = V_n delta, with V_n / pi^floor(n/2) exact."""
    n = int(n)
    c = ball_volume_over_pi_power(n)
    k = n // 2
    if k == 0:
        return c * delta                            # n = 1: V_1 = 2, exact
    return RBF(c) * RBF.pi() ** k * delta


def compute(n, bits):
    n = int(n)
    if n not in DELTA_SQ:
        raise ValueError('no record listed for n = %d' % n)
    RBF = RealBallField(bits)
    delta_sq = DELTA_SQ[n]
    if delta_sq <= 0:
        raise ArithmeticError('n = %d: delta^2 is not positive' % n)
    delta = sqrt_exact_or_ball(delta_sq, RBF)
    density = density_from_centre(n, delta, RBF)
    for name, value in (('density', density), ('centre', delta)):
        if hasattr(value, 'is_finite') and not value.is_finite():
            raise ArithmeticError('n = %d: %s is not a finite ball' % (n, name))
    return {'density': density, 'centre': delta, 'delta_sq': delta_sq}


# ---------------------------------------------------------------- comments

def latex_rational(r):
    r = QQ(r)
    if r.denominator() == 1:
        return str(r.numerator())
    return r'\frac{%d}{%d}' % (r.numerator(), r.denominator())


def latex_sqrt_of_rational(r):
    """sqrt(r) for a positive rational r as (t/q) sqrt(s), s squarefree."""
    r = QQ(r)
    p, q = r.numerator(), r.denominator()
    m = ZZ(p * q)
    s = m.squarefree_part()
    t = ZZ((m // s).sqrt())
    coefficient = QQ(t) / q
    if s == 1:
        return latex_rational(coefficient)
    root = r'\sqrt{%d}' % s
    if coefficient == 1:
        return root
    if coefficient.denominator() == 1:
        return '%d%s' % (coefficient.numerator(), root)
    return r'\frac{%s%s}{%d}' % ('' if coefficient.numerator() == 1 else coefficient.numerator(),
                                  root, coefficient.denominator())


#: Above this size of numerator or denominator a closed form is written as a
#: product of prime powers rather than as a reduced fraction: 3^16/2^24 is
#: the page's form and 43046721/16777216 says nothing to a reader.
LARGE = 10 ** 4


def latex_prime_powers(delta_sq):
    """sqrt(delta_sq) as a fraction of prime powers, an odd exponent e
    written as p^{e/2} and the primes of exponent 1 gathered under one root,
    the page's 3^{13.5}/2^{22} becoming 3^{27/2}/2^{22} and its
    3^16/(2^20 sqrt 14) keeping its sqrt 14."""
    r = QQ(delta_sq)
    up, down = [], []
    for p, e in ZZ(r.numerator()).factor():
        up.append((p, e))
    for p, e in ZZ(r.denominator()).factor():
        down.append((p, e))

    def render(factors):
        parts = []
        root = ZZ(1)
        for p, e in factors:
            if e == 2:
                parts.append(str(p))
            elif e % 2 == 0:
                parts.append(r'%d^{%d}' % (p, e // 2))
            elif e == 1:
                root *= p
            else:
                parts.append(r'%d^{%d/2}' % (p, e))
        text = r'\cdot '.join(parts)
        if root != 1:
            text += (r'\,' if text else '') + r'\sqrt{%d}' % root
        return text or '1'

    top = render(up)
    if not down:
        return top
    return r'\frac{%s}{%s}' % (top, render(down))


def latex_centre(delta_sq):
    """The closed form of a centre density: (t/q) sqrt(s) where that is
    short, prime powers where it is not."""
    r = QQ(delta_sq)
    p, q = r.numerator(), r.denominator()
    m = ZZ(p * q)
    s = m.squarefree_part()
    t = ZZ((m // s).sqrt())
    coefficient = QQ(t) / q
    if coefficient.numerator() < LARGE and coefficient.denominator() < LARGE:
        return latex_sqrt_of_rational(r)
    return latex_prime_powers(r)


def latex_ball_volume(n):
    """V_n in closed form: pi^k/k! for n = 2k, 2^(k+1) pi^k/(2k+1)!! for n = 2k+1."""
    n = int(n)
    k = n // 2
    if n % 2 == 0:
        return r'\frac{\pi^{%d}}{%d!}' % (k, k)
    return r'\frac{2^{%d}\pi^{%d}}{%d!!}' % (k + 1, k, n)


def latex_density(n, delta_sq):
    """Delta = c pi^k sqrt(delta_sq) with c = V_n / pi^k, as a closed form:
    the reduced fraction for n <= 24, which is what the table of the
    classical lattices writes for the same numbers, and V_n times delta_n
    beyond, where the reduced fraction has twenty digits."""
    n = int(n)
    k = n // 2
    c = ball_volume_over_pi_power(n)
    r = QQ(delta_sq)
    p, q = r.numerator(), r.denominator()
    m = ZZ(p * q)
    s = m.squarefree_part()
    t = ZZ((m // s).sqrt())
    coefficient = c * QQ(t) / q
    if n > 24:
        return r'%s\cdot %s' % (latex_ball_volume(n), latex_centre(r))
    pi_power = '' if k == 0 else (r'\pi' if k == 1 else r'\pi^{%d}' % k)
    root = '' if s == 1 else r'\sqrt{%d}' % s
    head = root + (r'\,' if root and pi_power else '') + pi_power
    if not head:
        return latex_rational(coefficient)
    if coefficient == 1:
        return head
    if coefficient.denominator() == 1:
        return '%d%s' % (coefficient.numerator(), head)
    num = '' if coefficient.numerator() == 1 else str(coefficient.numerator())
    return r'\frac{%s%s}{%d}' % (num, head, coefficient.denominator())


def truncated_decimal(ball, significant):
    """The first `significant` digits of a positive ball, truncated, as a
    string with a trailing ellipsis; the digits are those every point of the
    ball shares."""
    RBF = ball.parent()
    magnitude = int((ball.mid().log10()).floor())      # value in [10^m, 10^(m+1))
    k = significant - magnitude - 1
    scaled = ball * RBF(10) ** k
    lo = ZZ(scaled.lower().floor())
    hi = ZZ(scaled.upper().floor())
    if lo != hi:
        raise ArithmeticError('the ball does not fix %d digits' % significant)
    digits = str(lo)
    if magnitude < -4:
        return digits[0] + '.' + digits[1:] + r'\ldots\cdot 10^{%d}' % magnitude
    if k <= 0:
        return digits + '0' * (-k) + r'\ldots'
    if len(digits) <= k:
        digits = '0' * (k - len(digits) + 1) + digits
    return digits[:-k] + '.' + digits[-k:] + r'\ldots'


def status_note(n):
    n = int(n)
    if n in OPTIMAL_ALL:
        who = OPTIMAL_ALL[n]
        return 'the densest packing of any kind in dimension %d' % n + (' CITE{%s}' % who if who else '')
    if n in OPTIMAL_LATTICE:
        return 'the densest lattice packing in dimension %d CITE{%s}' % (n, OPTIMAL_LATTICE[n])
    return None


def nonlattice_note(n, bits):
    n = int(n)
    if n not in NONLATTICE:
        return None
    name, delta_sq, decimal, key = NONLATTICE[n]
    RBF = RealBallField(bits)
    if delta_sq is None:
        return (r'the nonlattice packing $%s$ CITE{%s} is denser, with centre density $%s$ CITE{Catalogue-density}'
                % (name, key, decimal))
    centre = latex_centre(delta_sq)
    density = truncated_decimal(density_from_centre(n, RBF(delta_sq).sqrt(), RBF), 7)
    if key == 'Antipode2025':
        what = 'the antipode packing of dimension %d CITE{%s}' % (n, key)
    else:
        what = 'the nonlattice packing $%s$ CITE{%s}' % (name, key)
    note = '%s is denser, with centre density $%s$ and density $%s$' % (what, centre, density)
    if n in NONLATTICE_2012:
        old_name, old_sq, old_key = NONLATTICE_2012[n]
        note += r', as is $%s$ CITE{%s} with centre density $%s$' % (old_name, old_key, latex_centre(old_sq))
    return note


def comment(n, expression, values, bits):
    n = int(n)
    delta_sq = values['delta_sq']
    parts = []
    if expression == 'density':
        parts.append(r'$\Delta_{%d}=%s$, the density of %s' % (n, latex_density(n, delta_sq), LATTICE[n]))
        status = status_note(n)
        if status:
            parts.append(status)
        note = nonlattice_note(n, bits)
        if note:
            parts.append(note)
    else:
        parts.append(r'$\delta_{%d}=%s$, the centre density of %s' % (n, latex_centre(delta_sq), LATTICE[n]))
        if n <= 24 and n not in (11, 12, 13):
            parts.append(r'$\det\Lambda_{%d}=%d$ at minimal norm $4$' % (n, LAMINATED_DET[n]))
        elif n in (11, 12, 13):
            parts.append(r'$\det K_{%d}=%d$ at minimal norm $4$' % (n, 1 / delta_sq))
    return '; '.join(parts)


def equals_link(n, expression, value):
    n = int(n)
    if n in CLASSICAL_ROW:
        return 'HREF{%s#%s,%s}' % (CLASSICAL, CLASSICAL_ROW[n], expression)
    if expression == 'centre' and n in QUADRATIC:
        return QUADRATIC[n]
    if value == 1 and not hasattr(value, 'rad'):
        return 'HREF{One}'
    return None


class DensestLatticePackings(numberdb.Generator):

    table = 'T148'
    parameters = ('n', 'expression')
    type = 'R'
    digits = 100
    rigour = 'proven'

    def enumerate(self, top=TOP):
        for n in range(1, top + 1):
            for expression in EXPRESSIONS:
                yield {'n': n, 'expression': expression}

    def value(self, params, digits):
        n, expression = int(params['n']), params['expression']
        if expression not in EXPRESSIONS:
            raise ValueError('expression is one of %s, not %r' % (', '.join(EXPRESSIONS), expression))
        bits = numberdb.bits(digits, losing=WORKING_GUARD)
        values = cached(n, bits)
        entry = {'number': values[expression],
                 'comment': comment(n, expression, values, bits)}
        link = equals_link(n, expression, values[expression])
        if link:
            entry['equals'] = link
        return entry


_cache = {}


def cached(n, bits):
    key = (int(n), int(bits))
    if key not in _cache:
        _cache[key] = compute(n, bits)
    return _cache[key]


if __name__ == '__main__':
    generator = DensestLatticePackings()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='density and centre density of the densest lattice packing known in '
                    'each dimension n <= %d, from the exact centre densities of the '
                    "catalogue's table: exact rationals where rational, balls otherwise" % TOP))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
