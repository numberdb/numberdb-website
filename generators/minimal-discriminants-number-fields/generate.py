"""Minimal discriminants of number fields by degree and signature -- numberdb.org/TBD

For each degree n >= 2 and each number r2 of complex places, 0 <= r2 <= n/2,
the discriminant d_K of the number field K of degree n and signature
(n - 2 r2, r2) whose |d_K| is least. The value is the signed discriminant,
negative exactly when r2 is odd, so that a reader holding -23 finds it as -23.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

**Where the values come from.** Every entry is a theorem from the literature,
cited in its comment, and read here from three independent copies: the papers
(Battistoni 2020 for degrees 8 and 9, the LMFDB's completeness page for which
paper closes which signature), OEIS A343290 with its row and column sequences,
and the LMFDB's list of fields for the signature, which states its own
completeness bound. The polynomial in each comment is PARI's polredabs form,
the LMFDB's defining polynomial; the polynomials were taken from OEIS and the
LMFDB and never from memory, since a quintic written from memory for
signature (3,1) had nfdisc 9584 rather than -4511 (see the batch file).

**What the generator checks before returning a value.** For every row: that
the quoted polynomial is irreducible of degree n, that PARI's nfdisc of it is
the value, that polsturm gives r1 = n - 2 r2 real roots, that the polynomial
is its own polredabs, that polgalois (where PARI has its galdata) gives the
Galois group named in the comment, and that bnfinit followed by bnfcertify
gives the class number named there. And where a complete enumeration is
within reach, the minimum itself is re-derived rather than trusted: for n = 2
no fundamental discriminant of the right sign is smaller (isfundamental); for
n = 3 Hunter's box (as in the table of regulators of cubic fields) lists
every cubic field with smaller |D| and finds none of the signature; for the
totally real rows n = 4 to 8 Sage's enumerate_totallyreal_fields_all, an
implementation of Voight's algorithm sharing no code with the LMFDB, is run
up to the value and must return exactly one field, isomorphic to the quoted
one (the octic run takes about 40 seconds). The other rows -- mixed
signatures of degree 4 and up, and everything in degree 9 -- rest on the
cited papers and the LMFDB's completeness statement, which is what
`rigour: exact` means for a table of records.

**Two rows are left out because they are open.** In degree 9 the signatures
(7,1) and (5,2) have no proven minimum; the table's comment on the open rows
gives the smallest fields known and Odlyzko's unconditional lower bounds.
Degree 1 is left out too: Q has discriminant 1.
"""

import sys
from math import floor, sqrt

import numberdb.sage as numberdb
from sage.libs.pari import pari
from sage.rings.integer_ring import ZZ
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.rational_field import QQ

R = PolynomialRing(QQ, 'x')
x = R.gen()

#: Largest degree listed; every signature of degree 9 but (7,1) and (5,2) is
#: known, and degree 10 has no proven row at all.
TOP = 9

#: The signatures of degree TOP or less whose minimum is not a theorem.
OPEN = {(9, 1), (9, 2)}

#: One row per (n, r2). `poly` is the reduced polynomial, coefficients from
#: the constant term up; `label` is the LMFDB label of the field; `galois` is
#: the transitive-group label of the Galois closure with its order and, where
#: it has a standard name, that name; `h` the class number; `next` the |d_K|
#: of the next field of the signature in the LMFDB's list, so that "the only
#: field with this |d_K|" is a fact read off that list; `source` the clause
#: naming who proved the minimum.
# BEGIN-ROWS
ROWS = [
    {'n': 2, 'r2': 0, 'd': 5, 'poly': [-1, -1, 1], 'label': '2.2.5.1',
     'galois': ('2T1', 2, 'C_2'), 'h': 1, 'next': 8,
     'source': 'the discriminant of a quadratic field is a fundamental discriminant, and $5$ is the least positive one',
     'named': r'$K=\mathbb{Q}(\sqrt5)$'},
    {'n': 2, 'r2': 1, 'd': -3, 'poly': [1, -1, 1], 'label': '2.0.3.1',
     'galois': ('2T1', 2, 'C_2'), 'h': 1, 'next': 4,
     'source': 'the discriminant of a quadratic field is a fundamental discriminant, and $-3$ is the negative one of least absolute value',
     'named': r'$K=\mathbb{Q}(\sqrt{-3})=\mathbb{Q}(\zeta_3)$'},
    {'n': 3, 'r2': 0, 'd': 49, 'poly': [1, -2, -1, 1], 'label': '3.3.49.1',
     'galois': ('3T1', 3, 'C_3'), 'h': 1, 'next': 81,
     'source': r"the minimum follows from the list of every cubic field with $|D|\leq 3000$ in HREF{Regulators_of_cubic_fields}[the table of regulators of cubic fields], which rests on Hunter's theorem CITE{Cohen1993}",
     'named': r'$K=\mathbb{Q}(\zeta_7)^+$, the maximal real subfield of the seventh cyclotomic field'},
    {'n': 3, 'r2': 1, 'd': -23, 'poly': [1, 0, -1, 1], 'label': '3.1.23.1',
     'galois': ('3T2', 6, 'S_3'), 'h': 1, 'next': 31,
     'source': r"the minimum follows from the list of every cubic field with $|D|\leq 3000$ in HREF{Regulators_of_cubic_fields}[the table of regulators of cubic fields], which rests on Hunter's theorem CITE{Cohen1993}",
     'named': r'$K=\mathbb{Q}(\rho)$ for the plastic number $\rho$, the real root of $x^3-x-1$'},
    {'n': 4, 'r2': 0, 'd': 725, 'poly': [1, 1, -3, -1, 1], 'label': '4.4.725.1',
     'galois': ('4T3', 8, 'D_4'), 'h': 1, 'next': 1125,
     'source': 'the minimum follows from the complete tables of quartic fields with $|d_K|<10^6$ CITE{BF1989} CITE{BFP1993}'},
    {'n': 4, 'r2': 1, 'd': -275, 'poly': [-1, 2, 0, -1, 1], 'label': '4.2.275.1',
     'galois': ('4T3', 8, 'D_4'), 'h': 1, 'next': 283,
     'source': 'the minimum follows from the complete table of quartic fields with $|d_K|<10^6$ CITE{BFP1993}'},
    {'n': 4, 'r2': 2, 'd': 117, 'poly': [1, 1, -1, -1, 1], 'label': '4.0.117.1',
     'galois': ('4T3', 8, 'D_4'), 'h': 1, 'next': 125,
     'source': 'the minimum follows from the complete table of quartic fields with $|d_K|<10^6$ CITE{BFP1993}'},
    {'n': 5, 'r2': 0, 'd': 14641, 'poly': [-1, 3, 3, -4, -1, 1], 'label': '5.5.14641.1',
     'galois': ('5T1', 5, 'C_5'), 'h': 1, 'next': 24217,
     'source': 'the minimum follows from the complete tables of quintic fields CITE{DyD1991} CITE{SPD1994}',
     'named': r'$K=\mathbb{Q}(\zeta_{11})^+$, the maximal real subfield of the eleventh cyclotomic field, $d_K=11^4$'},
    {'n': 5, 'r2': 1, 'd': -4511, 'poly': [1, 0, -2, -1, 0, 1], 'label': '5.3.4511.1',
     'galois': ('5T5', 120, 'S_5'), 'h': 1, 'next': 4903,
     'source': 'the minimum follows from the complete table of quintic fields CITE{SPD1994}'},
    {'n': 5, 'r2': 2, 'd': 1609, 'poly': [1, 1, -1, -1, 0, 1], 'label': '5.1.1609.1',
     'galois': ('5T5', 120, 'S_5'), 'h': 1, 'next': 1649,
     'source': 'the minimum follows from the complete table of quintic fields CITE{SPD1994}'},
    {'n': 6, 'r2': 0, 'd': 300125, 'poly': [-1, -2, 7, 2, -7, -1, 1], 'label': '6.6.300125.1',
     'galois': ('6T1', 6, 'C_6'), 'h': 1, 'next': 371293,
     'source': 'the minimum was proved by Pohst CITE{Pohst1982}',
     'named': r'$K=\mathbb{Q}(\sqrt5)\cdot\mathbb{Q}(\zeta_7)^+$, the cyclic sextic field of conductor $35$, $d_K=5^3\cdot7^4$'},
    {'n': 6, 'r2': 1, 'd': -92779, 'poly': [1, -2, -1, 3, -2, -1, 1], 'label': '6.4.92779.1',
     'galois': ('6T16', 720, 'S_6'), 'h': 1, 'next': 94363,
     'source': 'the minimum was proved by Pohst CITE{Pohst1982}'},
    {'n': 6, 'r2': 2, 'd': 28037, 'poly': [-1, -2, 0, 3, 0, -2, 1], 'label': '6.2.28037.1',
     'galois': ('6T11', 48, None), 'h': 1, 'next': 29077,
     'source': 'the minimum was proved by Pohst CITE{Pohst1982}'},
    {'n': 6, 'r2': 3, 'd': -9747, 'poly': [1, -3, 4, -2, 1, -1, 1], 'label': '6.0.9747.1',
     'galois': ('6T5', 18, None), 'h': 1, 'next': 10051,
     'source': 'the minimum was proved by Liang and Zassenhaus CITE{LZ1977}, who write the field as $\\mathbb{Q}(\\theta)$ with $\\theta^6-3\\theta^5+4\\theta^4-4\\theta^3+4\\theta^2-2\\theta+1=0$'},
    {'n': 7, 'r2': 0, 'd': 20134393, 'poly': [1, -4, -4, 10, 4, -6, -1, 1], 'label': '7.7.20134393.1',
     'galois': ('7T7', 5040, 'S_7'), 'h': 1, 'next': 25164057,
     'source': 'the minimum was proved by Pohst CITE{Pohst1977}'},
    {'n': 7, 'r2': 1, 'd': -2306599, 'poly': [-1, 1, 3, 1, -1, -3, 0, 1], 'label': '7.5.2306599.1',
     'galois': ('7T7', 5040, 'S_7'), 'h': 1, 'next': 2369207,
     'source': 'the minimum was proved by Diaz y Diaz CITE{DyD1988}'},
    {'n': 7, 'r2': 2, 'd': 612233, 'poly': [-1, -1, 1, -1, 0, 1, -1, 1], 'label': '7.3.612233.1',
     'galois': ('7T7', 5040, 'S_7'), 'h': 1, 'next': 612569,
     'source': 'the minimum was proved by Diaz y Diaz CITE{DyD1984}'},
    {'n': 7, 'r2': 3, 'd': -184607, 'poly': [1, 1, -1, 0, 1, -1, -1, 1], 'label': '7.1.184607.1',
     'galois': ('7T7', 5040, 'S_7'), 'h': 1, 'next': 193327,
     'source': 'the minimum was proved by Diaz y Diaz CITE{DyD1983}'},
    {'n': 8, 'r2': 0, 'd': 282300416, 'poly': [-1, 2, 7, -12, -8, 14, 0, -4, 1], 'label': '8.8.282300416.1',
     'galois': ('8T17', 32, None), 'h': 1, 'next': 309593125,
     'source': 'the minimum was proved by Pohst, Martinet and Diaz y Diaz CITE{PMD1990}',
     'named': r'$d_K=2^{12}\cdot41^3$'},
    {'n': 8, 'r2': 1, 'd': -65106259, 'poly': [1, -2, -4, 4, 7, -1, -5, 0, 1], 'label': '8.6.65106259.1',
     'galois': ('8T50', 40320, 'S_8'), 'h': 1, 'next': 68494627,
     'source': 'the minimum was proved by Battistoni CITE{Battistoni2020}'},
    {'n': 8, 'r2': 2, 'd': 15243125, 'poly': [1, 3, -2, -6, 3, 3, -3, -1, 1], 'label': '8.4.15243125.1',
     'galois': ('8T17', 32, None), 'h': 1, 'next': 15297613,
     'source': 'the minimum was proved by Battistoni CITE{Battistoni2020}'},
    {'n': 8, 'r2': 3, 'd': -4286875, 'poly': [-1, 2, 2, -1, -2, 1, 0, -1, 1], 'label': '8.2.4286875.1',
     'galois': ('8T6', 16, 'D_8'), 'h': 1, 'next': 4296211,
     'source': 'the minimum was proved by Battistoni CITE{Battistoni2019}'},
    {'n': 8, 'r2': 4, 'd': 1257728, 'poly': [1, -2, 3, 0, -4, 4, 0, -2, 1], 'label': '8.0.1257728.1',
     'galois': ('8T17', 32, None), 'h': 1, 'next': 1265625,
     'source': 'the minimum was proved by Diaz y Diaz CITE{DyD1987}',
     'named': r'$d_K=2^8\cdot17^3$'},
    {'n': 9, 'r2': 0, 'd': 9685993193, 'poly': [-1, 5, 3, -20, -2, 24, 0, -9, 0, 1], 'label': '9.9.9685993193.1',
     'galois': ('9T34', 362880, 'S_9'), 'h': 1, 'next': 11779563529,
     'source': 'the minimum was proved by Takeuchi CITE{Takeuchi1999}'},
    {'n': 9, 'r2': 3, 'd': -109880167, 'poly': [-1, -2, 0, 3, 1, -3, 1, 1, -2, 1], 'label': '9.3.109880167.1',
     'galois': ('9T34', 362880, 'S_9'), 'h': 1, 'next': 110852311,
     'source': 'the minimum was proved by Battistoni CITE{Battistoni2020}'},
    {'n': 9, 'r2': 4, 'd': 29510281, 'poly': [1, -3, 6, -8, 7, -3, 0, 2, -2, 1], 'label': '9.1.29510281.1',
     'galois': ('9T34', 362880, 'S_9'), 'h': 1, 'next': 30073129,
     'source': 'the minimum was proved by Battistoni CITE{Battistoni2020}'},
]
# END-ROWS

#: Liang and Zassenhaus's polynomial for the totally complex sextic field,
#: from the review of their paper; the generator checks that it defines the
#: field of the (6,3) row.
LIANG_ZASSENHAUS = [1, -2, 4, -4, 4, -3, 1]

#: Names PARI's polgalois uses, for the groups named in ROWS.
PARI_NAMES = {'C_2': 'S2', 'C_3': 'A3', 'S_3': 'S3', 'D_4': 'D(4)', 'C_5': 'C(5) = 5',
              'S_5': 'S5', 'C_6': 'C(6) = 6 = 3[x]2', 'S_6': 'S6', 'S_7': 'S7', 'S_8': 'S8',
              'D_8': 'D(8)', 'S_9': 'S9'}


def row(n, r2):
    for record in ROWS:
        if record['n'] == n and record['r2'] == r2:
            return record
    raise ValueError('no row for n = %s, r2 = %s' % (n, r2))


def polynomial(record):
    f = R([ZZ(c) for c in record['poly']])
    if f.degree() != record['n'] or f.leading_coefficient() != 1:
        raise ArithmeticError('the polynomial of (%d,%d) is not monic of degree %d: %s'
                              % (record['n'], record['r2'], record['n'], f))
    return f


def check_field(record):
    """PARI's discriminant, signature, reduced form, Galois group and
    certified class number of the quoted polynomial, each compared with the
    row. Returns (galois label, order, name, h, subfield degrees, quadratic
    subfield discriminant or None)."""
    n, r2, d = record['n'], record['r2'], ZZ(record['d'])
    f = polynomial(record)
    g = pari(f)
    if not g.polisirreducible():
        raise ArithmeticError('(%d,%d): %s is reducible' % (n, r2, f))
    if ZZ(g.nfdisc()) != d:
        raise ArithmeticError('(%d,%d): nfdisc(%s) = %s, the row says %s' % (n, r2, f, g.nfdisc(), d))
    if int(g.polsturm()) != n - 2 * r2:
        raise ArithmeticError('(%d,%d): %s has %s real roots, not %d' % (n, r2, f, g.polsturm(), n - 2 * r2))
    if d.sign() != (-1) ** r2:
        raise ArithmeticError('(%d,%d): d = %s has the wrong sign for r2 = %d' % (n, r2, d, r2))
    if g.polredabs() != g:
        raise ArithmeticError('(%d,%d): %s is not its own polredabs, which is %s' % (n, r2, f, g.polredabs()))
    if record['label'] != '%d.%d.%d.1' % (n, n - 2 * r2, abs(d)):
        raise ArithmeticError('(%d,%d): label %s does not say %d.%d.%d.1' % (n, r2, record['label'], n, n - 2 * r2, abs(d)))
    galois = record['galois']
    try:
        pg = g.polgalois()
    except Exception:                                    # noqa: BLE001
        pg = None                                        # PARI without galdata
    if pg is not None:
        order, index, name = int(pg[0]), int(pg[2]), str(pg[3])
        found = ('%dT%d' % (n, index), order, name)
        if galois is None:
            galois = (found[0], order, None)
        elif (found[0], order) != (galois[0], galois[1]) or (galois[2] and PARI_NAMES.get(galois[2]) != name):
            raise ArithmeticError('(%d,%d): polgalois says %s, the row says %s' % (n, r2, found, galois))
    if galois is None:
        raise ArithmeticError('(%d,%d): no Galois group in the row and none from PARI' % (n, r2))
    bnf = g.bnfinit(1)
    if bnf.bnfcertify() != 1:
        raise ArithmeticError('(%d,%d): bnfcertify did not certify %s' % (n, r2, f))
    h = ZZ(bnf.bnf_get_no())
    if record['h'] is not None and h != record['h']:
        raise ArithmeticError('(%d,%d): h = %s, the row says %s' % (n, r2, h, record['h']))
    subfields = g.nfsubfields()
    degrees = sorted(int(s[0].poldegree()) for s in subfields)
    quadratic = [ZZ(s[0].nfdisc()) for s in subfields if int(s[0].poldegree()) == 2]
    if len(quadratic) > 1:
        raise ArithmeticError('(%d,%d): %d quadratic subfields' % (n, r2, len(quadratic)))
    if (n, r2) == (6, 0):
        # the comment names the field as the compositum of Q(sqrt 5) and Q(zeta_7)^+
        proper = sorted(ZZ(s[0].nfdisc()) for s in subfields if 1 < int(s[0].poldegree()) < n)
        if proper != [5, 49]:
            raise ArithmeticError('(6,0): proper subfields have discriminants %s, not [5, 49]' % proper)
    return galois, h, degrees, (quadratic[0] if quadratic else None)


def hunter_cubics(bound):
    """The discriminants of every cubic field with |D| <= bound, with
    multiplicity, from Hunter's box (Cohen, Thm 6.4.2): a generator of trace
    0 or 1 with T2 <= 1/3 + (2/sqrt 3)(bound/3)^(1/2)."""
    t2 = 1.0 / 3 + (2 / sqrt(3)) * sqrt(bound / 3.0)
    a1_max = int(floor((1 + t2) / 2)) + 1
    a0_max = int(floor((t2 / 3) ** 1.5)) + 1
    found = {}
    for a2 in (0, -1):
        for a1 in range(-a1_max, a1_max + 1):
            for a0 in range(-a0_max, a0_max + 1):
                if a0 == 0:
                    continue
                g = pari(x ** 3 + a2 * x ** 2 + a1 * x + a0)
                if not g.polisirreducible():
                    continue
                D = ZZ(g.nfdisc())
                if abs(D) <= bound:
                    found.setdefault(D, set()).add(str(g.polredabs()))
    return found


def check_minimal(record):
    """Re-derive the minimum where a complete enumeration is cheap; return
    a phrase saying how, or None where the row rests on the literature."""
    n, r2, d = record['n'], record['r2'], ZZ(record['d'])
    f = polynomial(record)
    if n == 2:
        # isfundamental(1) is true of the discriminant of Q, which is not a quadratic field
        for t in range(-abs(d) + 1, abs(d)):
            if t not in (0, 1) and pari(t).isfundamental() and ZZ(t).sign() == d.sign():
                raise ArithmeticError('(2,%d): %d is a fundamental discriminant smaller than %s' % (r2, t, d))
        return 'no fundamental discriminant of that sign is smaller'
    if n == 3:
        found = hunter_cubics(abs(d))
        smaller = [D for D in found if abs(D) < abs(d) and D.sign() == d.sign()]
        if smaller:
            raise ArithmeticError('(3,%d): Hunter\'s box finds cubic fields of discriminant %s' % (r2, smaller))
        if found.get(d) != {str(pari(f))}:
            raise ArithmeticError('(3,%d): Hunter\'s box finds %s at D = %s' % (r2, found.get(d), d))
        return "Hunter's box finds no cubic field of that sign with smaller $|D|$"
    if r2 == 0 and n <= 8:
        from sage.rings.number_field.totallyreal_rel import enumerate_totallyreal_fields_all
        fields = enumerate_totallyreal_fields_all(n, int(d))
        if len(fields) != 1 or ZZ(fields[0][0]) != d:
            raise ArithmeticError('(%d,0): enumerate_totallyreal_fields_all(%d, %s) returned %s' % (n, n, d, fields))
        if pari.nfisisom(pari(R(fields[0][1])), pari(f)) == 0:
            raise ArithmeticError('(%d,0): the enumerated field %s is not the quoted one %s' % (n, fields[0][1], f))
        return 'Sage\'s enumeration of totally real fields up to that discriminant returns this field alone'
    if (n, r2) == (6, 3):
        if pari.nfisisom(pari(R(LIANG_ZASSENHAUS)), pari(f)) == 0:
            raise ArithmeticError("(6,3): Liang and Zassenhaus's polynomial does not define the quoted field")
    return None


def poly_latex(f):
    terms = []
    coefficients = [ZZ(c) for c in f.list()]
    for i in range(len(coefficients) - 1, -1, -1):
        c = coefficients[i]
        if c == 0:
            continue
        power = '' if i == 0 else ('x' if i == 1 else 'x^%d' % i)
        magnitude = abs(c)
        body = ('' if magnitude == 1 and i > 0 else str(magnitude)) + power
        terms.append(('-' if c < 0 else ('+' if terms else '')) + body)
    return ''.join(terms)


def galois_text(galois):
    label, order, name = galois
    if name in ('D_4', 'D_8'):
        return 'Galois group the dihedral group of order %d (%s)' % (order, label)
    if name:
        return 'Galois group $%s$ (%s)' % (name, label)
    return 'Galois group %s, of order %d' % (label, order)


def squarefree_kernel(delta):
    """m with Q(sqrt m) the quadratic field of discriminant delta."""
    delta = ZZ(delta)
    return delta if delta % 4 == 1 else delta // 4


def comment(record, galois, h, degrees, quadratic):
    n, r2 = record['n'], record['r2']
    f = polynomial(record)
    parts = ['$%s=0$' % poly_latex(f), galois_text(galois), '$h_K=%s$' % h, 'LMFDB %s' % record['label']]
    if quadratic is not None and n > 2:
        parts.append(r'quadratic subfield $\mathbb{Q}(\sqrt{%s})$' % squarefree_kernel(quadratic))
    if record.get('named'):
        parts.append(record['named'])
    parts.append(record['source'])
    if record['next'] is not None:
        parts.append('the next field of signature $(%d,%d)$ has $|d_K|=%d$' % (n - 2 * r2, r2, record['next']))
    return '; '.join(parts)


class MinimalDiscriminants(numberdb.Generator):

    table = 'TBD'
    parameters = ('n', 'r2')
    type = 'Z'
    rigour = 'exact'

    def enumerate(self):
        for n in range(2, TOP + 1):
            for r2 in range(0, n // 2 + 1):
                if (n, r2) in OPEN:
                    continue
                yield {'n': n, 'r2': r2}

    def value(self, params, digits):
        n, r2 = int(params['n']), int(params['r2'])
        record = row(n, r2)
        galois, h, degrees, quadratic = check_field(record)
        check_minimal(record)
        return {'number': ZZ(record['d']),
                'comment': comment(record, galois, h, degrees, quadratic)}


if __name__ == '__main__':
    generator = MinimalDiscriminants()
    if '--publish' in sys.argv:
        print(generator.publish(
            message='minimal discriminants of number fields of degree 2 to 9 by signature, the 26 '
                    'signatures whose minimum is a theorem; each polynomial checked with nfdisc, '
                    'polsturm, polredabs, polgalois and bnfcertify, and the minimum re-derived for '
                    'the quadratic, cubic and totally real rows to degree 8'))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
