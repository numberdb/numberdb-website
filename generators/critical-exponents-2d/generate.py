"""Critical exponents of the two-dimensional universality classes -- numberdb.org/T155

The exact rational critical exponents alpha, beta, gamma, delta, nu, eta of
the two-dimensional Ising, 3-state Potts, 4-state Potts, percolation and
self-avoiding-walk universality classes, with the cluster exponents sigma and
tau and the fractal dimension d_f of percolation and the fractal dimension of
the self-avoiding walk: 34 entries with two parameters, `class` and
`exponent`.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**Every value is computed, not transcribed.** Each class has a Coulomb-gas
coupling g (Nienhuis): the q-state Potts classes, percolation being q = 1,
have sqrt(q) = -2 cos(pi g) with 1/2 <= g <= 1, and the self-avoiding walk
is the dilute O(n) model at n = 0, n = -2 cos(pi g) with 1 <= g <= 2. The
scaling dimensions of the thermal and magnetic operators are

    Potts, percolation:   x_T = 3/(2g) - 1,   x_H = (2g - 1)(3 - 2g) / (8g)
    dilute O(n):          x_T = 4/g - 2,      x_H = (3g - 2)(2 - g) / (8g)

(den Nijs 1979, Nienhuis-Riedel-Schick 1980, Pearson 1980, Nienhuis 1982 and
1984), and with d = 2 the exponents are nu = 1/(2 - x_T), alpha = 2 - 2 nu,
beta = nu x_H, gamma = nu (2 - 2 x_H), delta = (2 - x_H)/x_H, eta = 2 x_H,
d_f = 2 - x_H for the percolation cluster and 1/nu for the walk, tau = 1 +
2/d_f, sigma = 1/(nu d_f). Every division is between Sage rationals: under
the named imports below a rational divided by a Python int is refused, the
coercion reaching for a module that only `sage.all` loads.

**What is asserted before a value is returned:** the scaling relations
alpha + 2 beta + gamma = 2, gamma = beta (delta - 1), gamma = nu (2 - eta)
and 2 nu = 2 - alpha on every class; sigma = 1/(beta + gamma) and tau = 2 +
beta/(beta + gamma) for percolation; and that the Ising exponents come out
the same from the Potts branch at q = 2 (g = 3/4) and from the O(n) branch
at n = 1 (g = 4/3), which is the one relation between the two families of
formulas. A class that fails any of these raises rather than returns.

**What was checked outside this file** before any entry was sent: all 30
exponents alpha to eta against the table on Wikipedia's *Universality class*
page; the thermal and magnetic dimensions against the Kac table of the
minimal models, x = 2h with h_{2,1} = 1/2 and h_{1,2} = 1/16 for the Ising
model M(4,3), h_{2,1} = 2/5 and h_{3,3} = 1/15 for the 3-state Potts model
M(6,5), h_{2,1} = 5/8 for percolation and h_{1,3} = 1/3 for the
self-avoiding walk at c = 0, a computation sharing nothing with the Coulomb
gas; the percolation values beta, gamma, nu, eta against the theorem of
Smirnov and Werner and the one-arm exponent 5/48 of Lawler, Schramm and
Werner; d_f = 91/48 against a Monte Carlo measurement of the largest
cluster at p_c = 1/2 on the triangular lattice (1.88 from L = 128 to 2048,
with a control at p = 0.65 returning 2.00); and gamma = 43/32 and nu = 3/4
of the self-avoiding walk against exact enumeration of square-lattice walks
to 16 steps (ratio estimates 1.340 and 0.730, rising, with the ordinary
random walk as a control returning exactly 1 and 1/2).
"""

import sys

import numberdb.sage as numberdb
from sage.rings.rational_field import QQ

#: The universality classes, in the order the table lists them, each with
#: its Coulomb-gas branch and coupling g: for the Potts branch
#: sqrt(q) = -2 cos(pi g), for the dilute O(n) branch n = -2 cos(pi g).
CLASSES = ['ising', 'potts3', 'potts4', 'percolation', 'saw']
COUPLING = {
    'ising': ('potts', QQ(3) / QQ(4)),       # q = 2
    'potts3': ('potts', QQ(5) / QQ(6)),      # q = 3
    'potts4': ('potts', QQ(1)),              # q = 4
    'percolation': ('potts', QQ(2) / QQ(3)), # q = 1
    'saw': ('on', QQ(3) / QQ(2)),            # n = 0
}
#: The number of states q of each Potts class, and n of each O(n) class,
#: so that the coupling can be checked against its defining equation.
MODEL = {'ising': 2, 'potts3': 3, 'potts4': 4, 'percolation': 1, 'saw': 0}

#: The six exponents every class has, then the three of percolation and the
#: one of the self-avoiding walk.
EXPONENTS = ['alpha', 'beta', 'gamma', 'delta', 'nu', 'eta']
EXTRA = {'percolation': ['sigma', 'tau', 'df'], 'saw': ['df']}

#: The Ising model is in both branches: q = 2 and n = 1.
ISING_ON_COUPLING = QQ(4) / QQ(3)


def coupling_is_right(branch, g, parameter):
    """sqrt(q) = -2 cos(pi g), or n = -2 cos(pi g), checked at the rational
    g where cos(pi g) is known exactly: 2 cos(pi g) is in {0, +-1, +-sqrt2,
    +-sqrt3, +-2} for the couplings here, so the square of each side is
    compared as a rational."""
    two_cos_squared = {QQ(1) / QQ(2): 0, QQ(2) / QQ(3): 1, QQ(3) / QQ(4): 2, QQ(5) / QQ(6): 3, QQ(1): 4,
                       QQ(4) / QQ(3): 1, QQ(3) / QQ(2): 0, QQ(2): 4}
    if g not in two_cos_squared:
        raise ValueError('cos(pi g) is not tabulated for g = %s' % g)
    if branch == 'potts':
        return two_cos_squared[g] == parameter
    return two_cos_squared[g] == parameter ** 2 and (parameter <= 0) == (g >= QQ(3) / QQ(2))


def dimensions(branch, g):
    """(x_T, x_H) of the thermal and magnetic operators."""
    g = QQ(g)
    if branch == 'potts':
        if not (QQ(1) / QQ(2) <= g <= 1):
            raise ValueError('the critical Potts branch has 1/2 <= g <= 1, not %s' % g)
        x_T = QQ(3) / (2 * g) - 1
        x_H = (2 * g - 1) * (3 - 2 * g) / (8 * g)
    elif branch == 'on':
        if not (1 <= g <= 2):
            raise ValueError('the dilute O(n) branch has 1 <= g <= 2, not %s' % g)
        x_T = QQ(4) / g - 2
        x_H = (3 * g - 2) * (2 - g) / (8 * g)
    else:
        raise ValueError('unknown branch %r' % branch)
    return x_T, x_H


def exponents_from(x_T, x_H, d=2):
    d = QQ(d)
    nu = QQ(1) / (d - x_T)
    values = {
        'nu': nu,
        'alpha': 2 - d * nu,
        'beta': nu * x_H,
        'gamma': nu * (d - 2 * x_H),
        'delta': (d - x_H) / x_H,
        'eta': 2 * x_H - (d - 2),
    }
    df = d - x_H
    values['df'] = df
    values['tau'] = 1 + d / df
    values['sigma'] = QQ(1) / (nu * df)
    return values


def checked(values, cls):
    """The scaling relations, which hold identically in the Coulomb gas but
    would not survive a wrong sign or factor in a formula."""
    a, b, c, dl, nu, eta = (values[k] for k in EXPONENTS)
    relations = [
        ('Rushbrooke', a + 2 * b + c, 2),
        ('Widom', c, b * (dl - 1)),
        ('Fisher', c, nu * (2 - eta)),
        ('Josephson', 2 * nu, 2 - a),
    ]
    if cls == 'percolation':
        relations += [
            ('sigma = 1/(beta + gamma)', values['sigma'], QQ(1) / (b + c)),
            ('tau = 2 + beta/(beta + gamma)', values['tau'], 2 + b / (b + c)),
            ('d_f = 2 - beta/nu', values['df'], 2 - b / nu),
        ]
    for name, left, right in relations:
        if left != right:
            raise ArithmeticError('%s: %s fails, %s != %s' % (cls, name, left, right))
    for name, v in values.items():
        if type(v).__name__ != 'Rational':
            raise TypeError('%s: %s is a %s, not a Sage rational' % (cls, name, type(v).__name__))
    return values


_CACHE = {}


def exponents_of(cls):
    if cls in _CACHE:
        return _CACHE[cls]
    if cls not in COUPLING:
        raise ValueError('no such universality class here: %r' % cls)
    branch, g = COUPLING[cls]
    if not coupling_is_right(branch, g, MODEL[cls]):
        raise ArithmeticError('%s: g = %s does not solve the defining equation of the %s branch' % (cls, g, branch))
    values = checked(exponents_from(*dimensions(branch, g)), cls)
    if cls == 'saw':
        #For the walk the fractal dimension is 1/nu, the two-leg operator
        #being the thermal one, and it must agree with 2 - x_T.
        values['df'] = QQ(1) / values['nu']
        if values['df'] != 2 - dimensions(branch, g)[0]:
            raise ArithmeticError('saw: 1/nu = %s is not 2 - x_T' % values['df'])
    if cls == 'ising':
        again = checked(exponents_from(*dimensions('on', ISING_ON_COUPLING)), 'ising')
        for k in EXPONENTS:
            if again[k] != values[k]:
                raise ArithmeticError('ising: %s is %s from the Potts branch and %s from the O(n) branch'
                                      % (k, values[k], again[k]))
    _CACHE[cls] = values
    return values


#: Entry comments: a caveat about a particular value, and nothing that the
#: document already says for every row at once.
COMMENT = {
    ('ising', 'alpha'): r'The specific heat diverges logarithmically, $C\propto-\ln|t|$ CITE{Onsager}.',
    ('percolation', 'alpha'): r'The existence of $\alpha$ is open; the value follows from $\nu=\frac43$ by '
                              r'$2-\alpha=2\nu$ CITE{SmirnovWerner}.',
    ('percolation', 'df'): r'$d_f=2-\frac{5}{48}$, the fractal dimension of the incipient infinite cluster; '
                           r'$\frac{5}{48}$ is the one-arm exponent CITE{LSW}.',
    ('saw', 'df'): r'$d_f=\frac1\nu$, the fractal dimension of the walk and of the trace of $\mathrm{SLE}_{8/3}$ '
                   r'CITE{LSW2004} CITE{Beffara}.',
    ('potts4', 'alpha'): r'With multiplicative logarithmic corrections, as every 4-state Potts exponent '
                         r'CITE{SalasSokal}.',
}


class CriticalExponents2D(numberdb.Generator):

    table = 'T155'
    parameters = ('class', 'exponent')
    type = 'Q'
    rigour = 'exact'

    def enumerate(self):
        for cls in CLASSES:
            for exponent in EXPONENTS + EXTRA.get(cls, []):
                yield {'class': cls, 'exponent': exponent}

    def value(self, params, digits):
        cls, exponent = params['class'], params['exponent']
        if exponent not in EXPONENTS + EXTRA.get(cls, []):
            raise ValueError('the table has no %s for the class %s' % (exponent, cls))
        number = exponents_of(cls)[exponent]
        entry = {'number': number}
        if (cls, exponent) in COMMENT:
            entry['comment'] = COMMENT[(cls, exponent)]
        return entry


if __name__ == '__main__':
    generator = CriticalExponents2D()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='exact critical exponents alpha, beta, gamma, delta, nu, eta of the two-dimensional Ising, '
                    '3-state Potts, 4-state Potts, percolation and self-avoiding-walk classes, with sigma, tau '
                    'and d_f of percolation and d_f of the walk, 34 rationals from the Coulomb-gas coupling of '
                    'each class with the scaling relations asserted'))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
