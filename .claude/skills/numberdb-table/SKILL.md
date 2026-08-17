---
name: numberdb-table
description: Make or update a table of numbers for NumberDB (numberdb.org) with the `numberdb` Python package — choosing the quantity, the convention, the precision and the rigour level, writing a generator, and publishing it. Use when asked to add, extend, correct or verify a NumberDB table, or when working from a "table wanted" issue.
---

# Making a NumberDB table

NumberDB answers one question: *here is a number — is it already known?* A
table earns its place by making that answer possible and trustworthy. So the
work is not "compute some values"; it is "compute values somebody else can
check, indexed so they can be found, and labelled with how well they are
known".

Install: `pip install numberdb`, or `sage -pip install numberdb` inside
SageMath. In Sage use `import numberdb.sage as numberdb`, which returns Sage
objects.

## 1. Decide what the table says before computing anything

Write these down first. Every one of them has gone wrong in this corpus, and
none was caught by a test.

- **Which quantity, exactly.** Not "the AGM" but "the AGM, taking at each step
  the square root nearer to the new arithmetic mean". Over the p-adics the
  other choice gives a different limit, and the table that failed to say so
  could not be reproduced from its own definition.
- **Which normalisation, branch, and indexing.** `elliptic_k` takes the
  parameter *m*, not the modulus *k*; the two differ from the second entry
  onwards. "The nth zero" needs a statement of where counting starts.
- **What the parameters are, and what constraint they actually satisfy.** One
  table said `k = 1 mod p` while 702 of its 856 entries were not. State the
  constraint the entries meet, and if the values extend beyond the obvious
  domain, say by what extension.
- **What each value will be**: an exact integer, rational or polynomial, or an
  approximation. Exact values are stronger and shorter — return them exactly
  rather than as a hundred digits of an integer.

## 2. Size

See `docs/design/corpus-shape.md` for the measurements. In brief: **500–1000
entries, 100 significant digits, one or two integer parameters.**

How many entries is a question about how expensive the digits are. Few numbers
at great precision is as legitimate as many at a hundred; both at once is not.
The server enforces this with three limits (`numberdb_app/limits.py`):

| | recommended | soft | hard |
|---|---|---|---|
| entries | 1000 | 1200 | 50,000 |
| digits | 100 | 500 | 10,000 |
| entries block | — | 320 KB | 4 MB |

Soft limits may be passed by an author who explains why, recorded in the table
as `Size exception`. Digit limits do not apply to exact tables.

## 3. Write a generator

```python
import sys
import numberdb.sage as numberdb
from sage.all import QQ, ComplexBallField

WORKING_GUARD = 64          # bits beyond what the digits need, measured

class CompleteEllipticK(numberdb.Generator):
    table = 'T25'           # omit when creating a new table
    parameters = ('m',)
    type = 'R'              # Z, Q, R, C, Qp, Z[], Q[]
    digits = 100
    rigour = 'proven'

    def enumerate(self, denominator=50):
        for b in range(1, denominator + 1):
            for a in range(0, denominator + 1):
                m = QQ(a) / QQ(b)
                if m >= 1 or m.denominator() != b:
                    continue
                yield {'m': str(m)}

    def value(self, params, digits):
        field = ComplexBallField(numberdb.bits(digits, losing=WORKING_GUARD))
        value = field(QQ(params['m'])).elliptic_k()
        assert value.imag().contains_zero()
        return value.real()

if __name__ == '__main__':
    generator = CompleteEllipticK()
    if '--publish' in sys.argv:
        print(generator.publish(message='recomputed in ball arithmetic'))
    else:
        report = generator.verify()
        print(report)
        sys.exit(0 if report.ok else 1)
```

- `verify()` recomputes and compares against the stored table. Needs no key,
  writes nothing. `verify(sample=None)` checks every entry.
- `preview()` computes and compares and sends nothing — the right thing to run
  unattended.
- `publish()` writes. Needs `NUMBERDB_API_KEY`.
- `numberdb.bits(digits, losing=n)` converts decimal digits to bits and adds a
  guard. State the guard as a constant with the measurement behind it: how many
  digits the worst entry actually retained. Do not tune it until the run stops
  complaining.

## 4. Rigour: say how well the digits are known

One value per table, in `rigour`. The first five are ordered, weakest last.

| level | means |
|---|---|
| `exact` | an integer, rational or polynomial. No precision to choose. |
| `proven` | interval or ball arithmetic throughout, so the digits follow from the width of the result. |
| `assumed-bound` | fixed precision with an error bound you assert *and justify*. |
| `heuristic (agreement-checked)` | computed at two or more precisions, keeping the digits they agree on. |
| `heuristic` | one computation and a guard chosen by judgement. |
| `measured` | not computed at all — an experimental value. Not on the scale. |

**`proven` is enforced, in one direction**: a value carrying no error of its
own is refused. That refusal exists because of the commonest mistake in this
field:

```python
RealIntervalField(prec)(some_float_function(x))   # width zero: claims exactness
```

Wrapping a fixed-precision result in an interval field does not make it an
enclosure. Check with `arb`/ball arithmetic (`ComplexBallField`,
`RealBallField`) rather than `RealIntervalField` around a float — arb
implements a great deal (`elliptic_k`, `barnes_g`, `zeta`, `zetaderiv`, `agm`,
`airy_ai`, `bessel_J`, Hurwitz `zeta(s, a)`, `sin_integral`, …).

Ball arithmetic also disposes of the argument-rounding problem: `CBF(QQ(1)/3)`
is a ball *containing* 1/3, so an argument you cannot represent is inside the
bound rather than outside the claim.

When you cannot bound it, say so — a weaker level honestly stated is a
contribution, a false `proven` is not:

```python
numberdb.agreeing(lambda working: compute(params, working), at=(150, 200))
numberdb.assume_accurate(value, ulps=2, because='PARI ellL1 at 38 digits; ...')
```

`agreeing` takes decimal digits, not bits, and does not escalate on its own:
the file attached to a table is meant to say how the numbers were made.
`assume_accurate` requires `because` — checked against documentation, most
libraries state no accuracy at all.

## 5. What the refusals mean

The package stops rather than guesses. Each of these has caught a real error:

- **"N digits were asked for and this value carries M"** — the working
  precision was too low, or a field was built in digits where Sage counts bits
  (a factor of ~3.3). Raise the guard; do not lower `digits` silently.
- **"rigour is 'proven', and this value carries no error of its own"** — see
  above. Compute in ball arithmetic, or state the weaker level.
- **"the table holds X and this run produced Y"** — a real disagreement.
  Investigate before passing `correcting=True`; a table once held 200 digits of
  which the last three were wrong, and it was found exactly here.
- **"the table holds N digits and this run produced M"** — you are about to
  shorten stored values. `lowering=True` only if the stored precision was never
  justified.

## 6. Metadata

Every table has: **Title**, **Definition**, **Tags** (two is typical),
**Links**, **Data properties** (`type`, `rigour`). Definitions run to one or
two sentences; use `$...$` for mathematics and `CITE{}` for references.

Link to sources that will still be there: Wikipedia, LMFDB, OEIS, MathWorld,
mpmath, or a paper.

**`Programs` and `generate.py` answer different questions.** `Programs` is the
standard incantation in Sage, PARI or mpmath for a reader who wants one more
value. `generate.py` is the program that reproduces and extends *this* table,
attached to it. A table wants both where both apply.

## 7. Publishing, and what happens next

- Publishing needs the owner's API key. Do not ask for it, and do not put a key
  in a file you commit.
- Values are held out of search by number until a board member reviews them.
  That is deliberate: a reader looking at a table can see an entry is
  unreviewed, and somebody typing digits into a search box cannot.
- Correcting values that are already public is a human decision. Show the
  measured discrepancy — in units of the last place — and ask.

## 8. Check the work

- `verify(sample=None)` after publishing.
- `manage.py sweep_arb` (server-side) recomputes stored values from
  independent definitions and reports anything the site's own parsers would
  read as a different number.
- If your recomputation disagrees with a stored value, suspect your
  recomputation first. In this corpus every disagreement after the first two
  was the checker's fault: a Teichmüller limit that collapses at p = 2, an
  exponential series that does not converge where the Artin–Hasse exponential
  is defined, a dodecahedron's inradius out by a factor of √5.
