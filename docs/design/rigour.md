# How well is a number actually known?

A table says a number has a hundred digits. It does not say whether those
digits are **proven**, **guaranteed by a library**, **believed on the strength
of a check**, or **assumed**. All four appear in this corpus, in roughly equal
measure, and nothing anywhere distinguishes them.

This note proposes that they be distinguished, says where the distinction
should live, and is deliberately written before any code.

## What the corpus actually contains

Measured over the 80 generator scripts in the data repository:

| | |
| --- | --- |
| rigorous only -- RIF/RBF/CIF/CBF throughout | 21 |
| both rigorous and inexact arithmetic in one script | 38 |
| inexact only -- RR/CC/float/`.n()` | 5 |
| neither: exact values, or no arithmetic at all | 16 |

So **43 of 80 touch arithmetic that carries no error bound**, and 29 of them
end by wrapping a point value in an interval field. The archetype, from the
Airy zeros:

```python
mpmath.mp.dps = prec10 * 1.5                  # 150 digits, no error bound
RIFprec = RealIntervalField(prec10 * 3.4 * 2)
number = mpmath.mp.airyaizero(n, derivative=0)
real_interval_to_sage_string(RIFprec(number), max_digits=prec10)   # writes 100
```

`RIFprec(number)` of an mpmath float is an interval of **zero width**. The
shared helper truncates Sage's `?`-notation to `max_digits`, which is sound for
a genuine interval -- Sage's `?` reflects real uncertainty -- and is pure
truncation of an unbounded value for a point. The `* 1.5` is the entire error
control, in 11 scripts. One uses `* 2`. Nothing checks either.

To be clear about what is *not* there: no script computes at two precisions and
keeps the digits that agree. There is no repeated `mp.dps`, no
precision-raising loop, no difference of two computed values, no interval
union. That technique is a good idea for the future rather than a practice to
preserve.

**The precision check in the client package is silently inert on exactly these
tables.** It measures the digits of the written string, and a zero-width
interval yields as many as are asked for. It has never fired for any of the 29
and never will. Any adaptive-precision scheme built on it would inherit the
same blindness, and would be worse than nothing: it would bless assumed digits
as measured ones.

## Four levels, and what each one means

- **`exact`** -- an integer, a rational, a polynomial. No precision to discuss.
- **`proven`** -- interval or ball arithmetic end to end (RIF, RBF, CIF, CBF,
  arb). The written digits follow from the width of the result. Trustworthy up
  to the correctness of arb and Sage.
- **`library`** -- computed in fixed-precision arithmetic by a routine whose
  documentation guarantees an accuracy, typically to within an ulp. PARI/GP
  states this for many functions. The claim is per function, not per library,
  so *"it was PARI"* is not itself an answer.
- **`heuristic (agreement-checked)`** -- computed twice at different working
  precisions, keeping the digits that agree. Measured rather than assumed, and
  still not a proof.
- **`heuristic`** -- one computation and a guard chosen by judgement. What the
  29 tables have today.

Ordered, because the ordering is what lets a change be checked: `exact` >
`proven` > `library` > `heuristic (agreement-checked)` > `heuristic`.

### Promoting a library result into rigorous arithmetic

Where a routine's accuracy is documented, the right move is not to carry the
point value onward but to turn it into a ball immediately:

```python
value = numberdb.sage.from_library(pari_result, ulps=1)   # a genuine RBF/RIF
return value * something_else_rigorous                    # error propagates
```

One ulp of stated accuracy becomes one ulp of radius, and every later operation
is interval arithmetic again. The result is rigorous *conditional on one
documented claim*, which is a far better position than a point value that
silently loses its error at the first multiplication. The entry is still
recorded as `library` -- the assumption is real and should be visible -- but
the arithmetic downstream of it is sound.

This is the single highest-value piece of the whole proposal: it converts
category 3 into category 2 mechanically, wherever the documentation supports
it.

## Where the level lives

**On the entry, defaulting from the table.** Not on the table alone.

The corpus settles this. Pólya's random walk constants carries

```yaml
reliability: no error bounds specified for $d \geq 4$ (help needed)
```

-- a table whose rigour varies *by parameter*, written as prose because there
was nowhere else to put it. A single table-level field cannot express it, and
that is not an exotic case: it is what happens whenever a family gets harder
further along, which is most families.

So:

- **`Data properties: rigour`** states the table's level. This is what almost
  every table needs and the only thing most readers will look at.
- An **entry may override it**, and the override is stored only where it
  differs. Most tables store one word and nothing per entry.
- **`Data properties: rigour details`** is optional prose: what blocks a proof,
  which routine is being trusted, what the guard was. The existing
  `reliability` field stays for everything else it already says.

The table-level statement is then a claim about the weakest entry, and the site
can check it rather than take it on faith.

## Two numbers, not one: written digits and proven digits

The hardest case is a number known rigorously to twenty digits and
heuristically to a hundred. Storing twenty throws away work that was done.
Storing a hundred and calling the whole thing heuristic throws away the fact
that twenty of them are certain.

So an entry carries both: the value as written, and **how far it is proven**.

```yaml
- params: {n: '17'}
  number: '1.234567890123456789012345678901…'    # 100 digits written
  rigour: heuristic (agreement-checked)
  proven_digits: 20                               # the first 20 follow from a bound
```

`proven_digits` is absent when it equals the written length, which is the
common case. Fully heuristic values have `proven_digits: 0`.

This is also what search should eventually use. A search by number that matches
on digits 30 to 40 of a value proven only to 20 is matching on belief, and the
machinery for holding weakly-known values out of search by number already
exists.

## A run may raise the level, never quietly lower it

If rigour is per entry, then a generator that recomputes part of a table can
change it -- and replacing a proven value with a heuristic one is exactly the
kind of silent loss the write path already refuses elsewhere.

It should refuse this the same way, and in the same shape as the arguments that
already exist:

```
publish(..., weakening=True)     # allow entries to be stored at a lower rigour
```

`overwrite`, `correcting`, `lowering`, `removing`, `restating` and now
`weakening`: each defaults to the conservative answer and names, in the
refusal, the argument that permits it. Lowering the *number* of digits and
lowering the *quality* of the digits are the same kind of act and deserve the
same treatment.

## What the package does with this

- **`rigour = 'proven'`** (the default for approximate types) -- a zero-width
  value of approximate type is refused, with a message that explains the
  point-interval trap outright, because it is otherwise invisible.
- **`rigour = 'library'`** -- accepted, and `from_library()` is offered for
  turning the point into a ball at the stated accuracy.
- **`rigour = 'heuristic (agreement-checked)'`** -- the package calls `value()`
  twice, at two working precisions, and writes only the digits that agree. The
  author does not implement this; that is the point of putting it here rather
  than in 43 scripts.
- **`rigour = 'heuristic'`** -- accepted, recorded, and never dressed up as
  anything else.

Adaptive precision -- widening until the result carries the digits asked for --
then makes sense for the first and third, where there is something real to
measure, and is refused for the others, where there is not.

## What this does not do

Agreement between two precisions bounds **rounding** error, not **method**
error. Two runs of a wrong algorithm agree perfectly and are both wrong; so do
two runs of a library function with a bug. `proven` inherits the correctness of
arb and Sage. `library` inherits a documentation claim, which is a statement
about intent as much as about code.

None of this makes a number true. It makes the basis for believing it explicit,
which is the most a database of numbers can honestly offer -- and considerably
more than "100 digits, no further comment".

## Order of work

1. `from_library()` and the refusal of unmarked point values. Small, and it
   stops the corpus growing more of the problem.
2. `rigour` on entries and tables, with the table-level default. A migration
   that marks the 29 known tables `heuristic` and the 21 rigorous ones
   `proven`, leaving the rest to inspection.
3. The site shows it, next to `reliability`.
4. `heuristic (agreement-checked)` in the package, and adaptive precision
   gated on the level.
5. `weakening`, once anything can be weakened.
