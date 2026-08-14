# How well is a number actually known?

A table says a number has a hundred digits. It does not say whether those
digits are **proven**, **believed on a stated assumption**, **checked by
agreement**, or simply **assumed**. All four appear in this corpus, in roughly
equal measure, and nothing anywhere distinguishes them.

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

**Six scripts do compare two precisions**, and an earlier draft of this note
said flatly that none did. That was wrong: the search looked for a repeated
`mp.dps`, a precision-raising loop or a difference of two values, and the
pattern is none of those --

    prec_factors = [1, 2]
    for prec_factor in prec_factors:
        number = E.lseries().taylor_series(..., prec=prec_factor * RIFprec.prec())[1]
        number_str[prec_factor] = ...blur_real_interval(RIFprec(number))...
    assert len(set(number_str.values())) == 1      # Sanity check

-- all six being elliptic-curve tables, the L-values and the real periods.
Their check is cruder than keeping the agreeing digits and in one way stricter:
they compute at `p` and `2p`, write both, and **fail** if the two written
forms differ, rather than falling back to fewer digits. Failing loudly is a
defensible choice. Those tables are better than the bare `assumed-bound` label
suggests, and their details should say so.

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
- **`assumed-bound`** -- computed in fixed-precision arithmetic, with an error
  bound **asserted by the author and accompanied by a reason**. The value is
  then carried as a ball of that radius, so everything after it is interval
  arithmetic again.

  This level was first drafted as `library`, on the understanding that PARI and
  friends document an accuracy -- typically one ulp -- that could simply be
  trusted. **The documentation does not support that.** In the PARI shipped
  with Sage: of 1271 documented functions, the word "ulp" appears in exactly
  one, and not in this sense. PARI's own header on transcendental functions
  explains at length how precision is *carried* -- from the argument, or from
  `realprecision` -- and says nothing at all about the accuracy of the result.
  Fifty functions mention a guarantee, nineteen an absolute or relative error,
  and sixteen state that the result may be wrong.

  PARI is carefully written and its results are very probably good to an ulp in
  most of these cases. That is a reasonable belief and it is not a citation, so
  the level is named for what the author is doing -- assuming -- rather than
  for where the number came from. *"It was PARI"* is not an answer; *"PARI's
  documentation for this function states X"* is one, and so is *"checked
  against an independent method at 200 digits"*.
- **`heuristic (agreement-checked)`** -- computed twice at different working
  precisions, keeping the digits that agree. Measured rather than assumed, and
  still not a proof.

  Tried on T55, the Airy zeros, and it works with no package change at all:
  take the two results as an interval, `field(low).union(field(high))`. The
  union has real width, so the writer emits only the digits both support and
  the precision check has something to measure. A deliberately inadequate
  guard -- computing at 30 digits for 100 written -- is **accepted** by the
  original point-value method and **refused** by this one, with the message
  naming the shortfall. That is the whole of the argument for it.
- **`heuristic`** -- one computation and a guard chosen by judgement. What the
  29 tables have today.
- **`measured`** -- not computed. The value comes from experiment and the
  stored interval holds the measurements together with their stated
  uncertainties. Four tables: the fine-structure constant, the
  proton-to-electron mass ratio, and the mass and magnetic moment ratios.

Ordered, because the ordering is what lets a change be checked: `exact` >
`proven` > `assumed-bound` > `heuristic (agreement-checked)` > `heuristic`.

**`measured` is deliberately outside that order.** It was added after the audit
found four tables the five levels could not describe, all of them physical
constants that were never computed at all. It is not a sixth degree of
confidence: a well-determined constant can be known to more digits than a
heuristic computation and fewer than a proven one, and asking whether
measurement beats agreement-checking has no answer. So `weakening`, when it
exists, must refuse a change *into or out of* `measured` rather than pretend to
compare it -- the two are different kinds of claim, and a comparison would
invent a fact.

That ordering has one soft spot worth naming: an `assumed-bound` is only as
good as its reason. A cited theorem outranks an agreement check; a bound
asserted because it felt about right does not. The reason is mandatory
precisely because the level cannot be read without it.

### Turning a point value into a ball, deliberately

Where an author does have a reason to believe an error bound, the right move is
not to carry the point value onward but to turn it into a ball at once:

```python
value = numberdb.sage.assume_accurate(
    pari_result, ulps=2,
    because='PARI ellL1 at 38 digits; agrees with the Dokchitser '
            'implementation to 30 digits on this curve')
return value * something_else_rigorous          # error propagates from here
```

Two properties, both deliberate:

- **No default for `ulps`.** A helper that supplies the bound supplies the
  judgement, and the judgement is the whole content of this level.
- **`because` is required**, and is stored with the entry, feeding the table's
  `rigour details`. An assumption nobody wrote down is indistinguishable later
  from an assumption nobody made.

What this buys is real: after the ball exists, every later operation is
interval arithmetic, so the error propagates instead of vanishing at the first
multiplication. The result is rigorous *conditional on one stated assumption*,
which is a far better position than a point value carrying no error at all --
and far better than a general `from_library()` helper, which would invite
wrapping anything at one ulp and moving on.

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
- **`rigour = 'assumed-bound'`** -- accepted only with a reason, and
  `assume_accurate()` is the way to state the bound and carry the value on as
  a ball.
- **`rigour = 'heuristic (agreement-checked)'`** -- the package calls `value()`
  twice, at two working precisions, and writes only the digits that agree. The
  author does not implement this; that is the point of putting it here rather
  than in 43 scripts.
- **`rigour = 'heuristic'`** -- accepted, recorded, and never dressed up as
  anything else.

## The working precision is chosen by the author, and written down

An earlier draft of this note proposed that the package widen the working
precision automatically, retrying an entry until it carried the digits asked
for. That is the wrong default, for a reason that outweighs the convenience:
**the file attached to a table is supposed to be how those numbers were made.**
A generator that silently escalated would not be. Re-running it would not
reproduce the computation that produced the stored values, only a computation
that happened to land in the same place.

The escape from that is to record, per entry, the precision the run finally
used -- and that is a great deal of machinery, in the table and in the wire
format, to buy back a property the code already had before we took it away.

So: **the package refuses, and the author decides.** `publish` measures what
each value pinned down and stops when it falls short, naming the shortfall and
suggesting a starting figure. The author raises the constant and runs again.
Trial and error, with the answer ending up in the file:

```python
GUARD_RATIO = 1.5        # digits computed beyond digits written
SECOND_OPINION = 2.0     # ...and again at this much, so the two can be compared
```

Both converted generators already work this way, and their constants carry the
measurement that justified them.

**One constant, sized for the worst entry, is the right default** -- including
when that is far more than the easy entries need. The easy entries are not the
bottleneck, and a single number in the file is a great deal easier to read,
justify and re-run than a formula. Simplicity beats run-time wherever run-time
does not explode.

Measured, so that "does not explode" is a fact rather than a hope:

| | |
| --- | --- |
| T27, 501 entries, 16-bit guard | 0.08 s |
| ...at 256 bits, sixteen times the guard | 0.08 s |
| ...at 1024 bits | 0.22 s |
| ...at 4096 bits | 2.58 s |
| T55, 1000 Airy zeros at 150 digits | 75 s |
| ...at 200 digits | 123 s |
| ...at 400 digits | 587 s |
| ...at 800 digits | 3542 s |

For T27, generosity is free: sixteen times the guard costs nothing measurable,
and the constant is 256 for that reason. For T55 the cost grows roughly as the
2.4th power of the precision -- doubling it is about five times the work -- so
one constant is still comfortable at 150 against 200 digits, and would not be
if one awkward entry needed 800 while the rest needed 150.

**That ratio is the trigger**, and it is the only thing worth measuring before
reaching for something cleverer. When the worst entry needs several times the
precision of the typical one *and* the table already takes hours, a rule
computed from the parameters earns its place:

```python
def working_digits(self, params, digits):
    return int(1.5 * digits) + 2 * params['d']
```

Deterministic, in the attached file, and it scales with the table. Until then
it is a formula standing in for a number, which is a worse thing to have to
check.

**What tooling can honestly do** is help with the trial rather than replace it:
a development-time pass that reports, per entry, how many digits each one
actually pinned down, so the author can see the shape of the loss and write a
rule that fits it. The output of that is a number typed into the file. Nothing
adaptive survives into a published run.

## What Sage documents for the elliptic-curve tables

Fourteen tables are `assumed-bound`, all of them elliptic-curve quantities
widened by a hand-chosen four ulps. The question worth asking of each is
whether anything states an accuracy, and the answer differs by quantity.

**L-values: yes, and it is usable.** `E.lseries().at1()` and `deriv_at1()`
return a *pair* -- the value and, in Sage's own words, "a bound on the error in
the approximation". It is a series-truncation bound following Cohen's
algorithm, so it shrinks with the number of terms rather than with the working
precision. Measured on curve 37a:

| terms | error bound | proven digits | time |
| --- | --- | --- | --- |
| 100 | 1.5e-45 | 45 | 0.0 s |
| 1000 | 1.9e-118 | **118** | 0.0 s |

So a hundred proven digits costs a thousand terms and no measurable time, and
those tables could be **`proven`** rather than assumed. Two limits: `at1` is
`L(E,1)` and `deriv_at1` is `L'(E,1)` assuming `L(E,1) = 0`, so this covers
rank 0 and rank 1 and nothing higher; and past a thousand terms the bound stops
improving, because it becomes limited by the working precision instead. The
rank 2 and rank 3 tables have only `taylor_series`, which documents a precision
in bits and no accuracy at all.

**Regulators: no.** `regulator(precision=...)` documents bits, not accuracy.
The word "rigorous" does appear in the elliptic-curve code, but about a
different thing -- whether the generators found are provably the full
Mordell-Weil basis. That is a question about *which lattice*, not about the
digits of its determinant, and conflating the two would be a false claim of
the most misleading kind.

**Real periods: no.** `period_lattice().real_period(prec=...)` documents bits,
and the period lattice offers no interval or ball variant at all.

So of the fourteen, the rank 0 and rank 1 L-value tables have a documented,
citable, cheap bound and should be recomputed as `proven`; the rest keep their
four ulps, and their `rigour details` should say that Sage documents no
accuracy for the quantity in question rather than leaving a reader to wonder
whether anybody looked.

## What mpmath documents, since half the corpus depends on it

The same question asked of PARI, asked of mpmath 1.4.1:

- its low-level arithmetic documents **correct rounding** (`libmp/libmpf.py`),
  and it is candid where it is not -- one integer routine documents being "1
  ulp wrong with high probability";
- `airyaizero` and `besseljzero` say **nothing at all** about accuracy, and
  neither do `mp`, `mpf`, `workprec` or `workdps`;
- it ships a **rigorous interval mode**, `mpmath.iv`, which returns genuine
  intervals for `pi`, `exp` and `gamma` -- and raises `AttributeError` for
  `zeta`, `airyaizero` and `besseljzero`, whose implementations call context
  methods the interval context does not have. Sage's `RealBallField` does not
  expose Airy or Bessel at all.

So mpmath is careful and says so where it can, and the functions this corpus
leans on carry no claim. Those tables cannot be made `proven` with what is
installed, short of wrapping arb's `arb_hypgeom_airy_zero` ourselves. They can
be made agreement-checked today.

**And the padding trap, which is worse than the point-interval one.**
`mpmath.nstr(z, 100)` prints a hundred digits of a value computed to thirty.
The extra seventy are the decimal expansion of a binary approximation:
deterministic, reproducible, and wrong. Measured on the first Airy zero,
computing at 30 digits and at 300 gives answers that diverge at the 40th, so
**61 of the 100 digits would be published** with nothing anywhere noticing --
not the writer, which was asked for a hundred, and not the check, which counts
the digits it was given. Returning a string instead of an interval does not
help: the string is padded too.

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

1. `assume_accurate()` and the refusal of unmarked point values. Small, and it
   stops the corpus growing more of the problem.
2. `rigour` on entries and tables, with the table-level default. A migration
   that marks the 29 known tables `heuristic` and the 21 rigorous ones
   `proven`, leaving the rest to inspection.
3. The site shows it, next to `reliability`.
4. `heuristic (agreement-checked)` in the package, so 43 generators do not
   each hand-roll it. Not adaptive precision: see above. A development-time
   report of what each entry pinned down would help the author choose, and
   what they choose goes in the file.
5. `weakening`, once anything can be weakened.
