---
name: numberdb-table
description: Make or update a table of numbers for NumberDB (numberdb.org) with the `numberdb` Python package — choosing the quantity, the convention, the precision and the rigour level, writing a generator, and publishing it. Use when asked to add, extend, correct or verify a NumberDB table, or when working from a "table wanted" issue.
---

# Making a NumberDB table

NumberDB answers one question: *here is a value — has anyone seen it before?*

The values are not only real numbers. A table may hold integers, rationals,
reals, complex numbers, p-adic numbers, or polynomials over Z or Q — and the
database is meant to be able to hold kinds nobody has added yet, which are
shown and cited even where they cannot be searched by their digits. Of the 107
tables today, 65 are real, 16 integer, 12 polynomial, 6 p-adic, 4 complex, 3
rational, and one holds hyperreals.

A table earns its place by making that answer possible and trustworthy. So the
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

## 2. How much to include

**A table is a reference, not a dump.** NumberDB exists so that somebody who
has met a value can find out what it is. That is the test for every entry: is
this a value somebody could plausibly encounter and want to identify? Nobody
meets the 500th Chebyshev polynomial and wonders what it is. A hundred of a
family is a reference; a thousand is a listing of something nobody was looking
for, and it makes the search results worse for everybody by burying the values
that are common.

So: **include what is common, and stop.** Then check what it costs.

See `docs/design/corpus-shape.md` for what the corpus does. Very roughly, and
only as a starting point to think from: 500–1000 entries for cheap
approximations, one or two integer parameters, 100 significant digits.

**Two things move that number down, and they are the usual case.**

*Expensive digits.* Few numbers known to great precision is as legitimate as
many known to a hundred digits; both at once is not.

*Values that grow.* A polynomial of degree n has about n/2 terms with
coefficients of O(n) digits, so it costs O(n²) characters and a table running
to n costs O(n³). Measured on Chebyshev polynomials of the first kind:

    n = 50      570 characters      table 0..50     11 KB
    n = 100    1892                 table 0..100    69 KB
    n = 200    6828                 table 0..200   472 KB   over the soft limit
    n = 500   39674                 table 0..500  6639 KB   over the hard limit

**Aim at half the soft block limit -- about 160 KB -- not at the limit.** A
table that only just fits cannot be extended by the next person without
breaching it, and the limit is there to be a margin rather than a target.

For a family of polynomials indexed by degree, **n up to about 100** is the
house range, and it lands where it should:

    chebyshev_T   0..100     69 KB
    hermite       0..100    144 KB
    legendre_P    0..100    164 KB     rational coefficients cost more

Stop earlier when the coefficients are rational or the family grows faster, and
**measure the largest entry before choosing the range** rather than assuming.
Beyond that, the question is not what fits but what anybody is looking up.

The server enforces three limits (`numberdb_app/limits.py`):

| | recommended | soft | hard |
|---|---|---|---|
| entries | 1000 | 1200 | 50,000 |
| digits | 100 | 500 | 10,000 |
| entries block | — | 320 KB | 4 MB |

A soft limit may be passed by an author who explains why, recorded in the table
as `Size exception`. A hard limit is not a judgement and cannot be passed. The
digit limits do not apply to exact tables. The block limit is the one that
binds for polynomials, and it is a limit on the *whole table*: it admits many
small entries or a few large ones, and refuses both at once.

## 3. Types: what a value is, how it is written, what to return

`type` in Data properties says what the table holds. Seven are searchable by
their digits:

| type | holds | written as |
|---|---|---|
| `Z` | integers | `3`, `-1729` |
| `Q` | rationals | `-3/2` |
| `R` | reals | see below |
| `C` | complex | `0.309... + i * 0.951...` |
| `Qp` | p-adics | `2^4 * 111736... + O(2^167)`, or `Q2:1.110` |
| `Z[]`, `Q[]` | polynomials | `x^2 - x - 1` |

A type outside that set is allowed but is *shown and cited rather than found*:
it must also carry a `type name` (T41's four hyperreals are `*R`, "hyperreals").
A misspelling is a typo; a new symbol with a name beside it is somebody
deciding something.

**A real is stored as an interval that contains it**, in one of four forms, and
the first is the one the corpus is written in:

    3.14                 the interval [3.13, 3.15] -- the last digit may be
                         off by one. `12e2` means [1100, 1300].
    [2, 2.3728596]       endpoints, exactly
    3.14 +/- 2e-2        centre and radius, exactly: [3.12, 3.16]
    1p31415              p-notation: 0.31415e1 with the last digit uncertain

A string with no `.` and no `e` is an **exact integer**, not an approximation.
This convention is the whole reason a hundred digits means something: `3.14`
*is* an interval, so a table never has to say separately how far to trust it.

**What `value()` should return**, and what each return means:

| return | recorded as | rigour it can support |
|---|---|---|
| `int`, `ZZ(n)` | exact integer | `exact` |
| `Fraction`, `QQ(a)/b` | exact rational | `exact` |
| `RealBallField(prec)(x)` (arb) | interval, from the ball | `proven` |
| `ComplexBallField(prec)(x)` | complex interval | `proven` |
| `RealIntervalField(prec)` element of nonzero width | interval | `proven` |
| a Sage polynomial | polynomial | `exact` |
| a `Qp` element | p-adic, with its own `O(p^n)` | `proven` |
| a string | taken verbatim | not `proven` |
| a `float` | **refused** — it does not say how precise it is | — |

Prefer **balls** (`RealBallField`, `ComplexBallField`) for anything
transcendental: arb carries the error through every step, so the digits written
are the digits the result supports. `RealIntervalField` is fine when the whole
computation is interval arithmetic (MPFI), and is a trap when it merely wraps a
fixed-precision result — see below.

An entry may also say it is deliberately less precise than the table's
`digits`, by returning `{'number': x, 'digits': 8}`.

## 4. Write a generator

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

**Open the file with the commands to run it.** The generator is attached to the
table and downloaded from it, by somebody who has neither this repository nor a
way to guess:

```
Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set
```

Then say what the file does and, where it matters, what was decided and why: a
working precision that was measured, a convention that had to be chosen, an
error bound and where it comes from.

## 5. Rigour: say how well the digits are known

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

## 6. What the refusals mean

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

## 7. Metadata

Every table has: **Title**, **Definition**, **Tags** (two is typical),
**Links**, **Data properties** (`type`, `rigour`). Definitions run to one or
two sentences; use `$...$` for mathematics and `CITE{}` for references.

Link to sources that will still be there: Wikipedia, LMFDB, OEIS, MathWorld,
mpmath, or a paper.

**`Programs` and `generate.py` answer different questions.** `Programs` is the
standard incantation in Sage, PARI or mpmath for a reader who wants one more
value. `generate.py` is the program that reproduces and extends *this* table,
attached to it. A table wants both where both apply.

## 8. Publishing, and what happens next

- Publishing needs the owner's API key. Do not ask for it, and do not put a key
  in a file you commit.
- Values are held out of search by number until a board member reviews them.
  That is deliberate: a reader looking at a table can see an entry is
  unreviewed, and somebody typing digits into a search box cannot.
- Correcting values that are already public is a human decision. Show the
  measured discrepancy — in units of the last place — and ask.

## 9. Check the work

- `verify(sample=None)` after publishing.
- `manage.py sweep_arb` (server-side) recomputes stored values from
  independent definitions and reports anything the site's own parsers would
  read as a different number.
- If your recomputation disagrees with a stored value, suspect your
  recomputation first. In this corpus every disagreement after the first two
  was the checker's fault: a Teichmüller limit that collapses at p = 2, an
  exponential series that does not converge where the Artin–Hasse exponential
  is defined, a dodecahedron's inradius out by a factor of √5.
