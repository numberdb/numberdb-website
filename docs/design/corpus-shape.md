# What a NumberDB table looks like

Measured over all 107 published tables on 2026-08-17, so that advice about new
tables cites the corpus rather than somebody's taste. Written for whoever --
person or program -- is about to make table 108.

The short version: **as many entries as are worth looking up and no more, a
hundred significant digits, one or two integer parameters, and a definition of
one or two sentences that says which convention is meant.** For cheap
approximations that is 500 to 1000 entries; for anything whose entries grow --
polynomials above all -- it is far fewer, and the target is half the soft size
limit rather than the limit. The rest of this note is what that is based on and
where it does not apply.

## Scale

    107 tables, 55,939 entries
    entries per table   min 1, median 502, max 1134
                        19 tables under 10, 31 between 10 and 500, 57 at 500+

Nineteen small tables are not failures. They are the ones where the *whole*
subject is small: five Platonic solids, four rescalings of the Gibbs constant,
one exponent of matrix multiplication. A table should hold what there is.

**How many entries is a question about how expensive the digits are.** Few
numbers known to great precision is as legitimate as many numbers known to a
hundred digits; what is not legitimate is both at once. That trade-off is
enforced rather than merely suggested -- see `numberdb_app/limits.py`, which
counts entries, digits and the size of the serialised block, and holds the
third limit precisely because the first two trade against each other:

| | recommended | soft | hard |
|---|---|---|---|
| entries | 1000 | 1200 | 50,000 |
| digits (approximations only) | 100 | 500 | 10,000 |
| entries block | -- | 320 KB | 4 MB |

A soft limit is a judgement about what makes a good table, and an author who
explains why may pass it -- the table records the reason under `Size
exception`. A hard limit is not a judgement: it is where a paste went wrong, or
where the editor and the diff view stop working.

The digit limits do not apply to exact tables (`Z`, `Q`, `Z[]`, `Q[]`): a
polynomial has no precision to choose, and writing fewer of its coefficients
does not round it, it makes it a different polynomial.

### Tables whose entries grow

The twelve polynomial tables run to n = 50 or 100, not to a thousand, and both
reasons matter.

A table is a reference: somebody meets a value and wants to know what it is.
Nobody meets the 500th Chebyshev polynomial. Beyond the first tens of a family
the entries are not values anyone is looking up, and they bury the ones that
are.

And they get expensive fast. A polynomial of degree n has about n/2 terms with
coefficients of O(n) digits, so it costs O(n²) characters and a table running
to n costs O(n³). Measured on Chebyshev polynomials of the first kind:

| range | table |
|---|---|
| 0..50 | 11 KB |
| 0..100 | 69 KB |
| 0..200 | 472 KB (over the soft block limit) |
| 0..500 | 6.6 MB (over the hard limit) |

The target is **half the soft block limit, about 160 KB**, rather than the
limit itself: a table that only just fits cannot be extended by the next person
without breaching it. For a family indexed by degree that puts the range at
**n = 100 or a little below** --

    chebyshev_T   0..100     69 KB
    hermite       0..100    144 KB
    legendre_P    0..100    164 KB     rational coefficients cost more

-- which is what the existing tables do. Measure the largest entry before
choosing a range.

## Types and parameters

    R 65 · Z 16 · Z[] 8 · Qp 6 · C 4 · Q[] 4 · Q 3 · *R 1

    parameters per table   none 11 · one 50 · two 30 · three 15 · four 1
    parameter types        Z 102 · Symbolic 27 · R 14 · Q 8 · C 5 · Qp 2 · Set 1

Integer parameters dominate, and reach a median of 100 (quartiles 29 and 1450).
Rational parameters use denominators of 10 to 30, at most 55. `Symbolic` is the
variant selector -- `expression` in the Gibbs table, `solid` in the Platonic
ones -- and is how a table holds several related quantities without becoming
several tables.

## Precision

A hundred significant digits, overwhelmingly: 1014 of a 1500-entry sample,
with 96 to 104 accounting for leading zeros and rounding. A hundred digits
identifies a number; a reader who wants more of a cheap value can compute them.

More than that is for values that were expensive to obtain, and then the count
should come down to match -- which is what the block limit expresses. Four
tables write more than 500 digits and each is one of those cases.

## The metadata, and what is not optional

    Title              107        Comments            82
    Links              107        Programs            45
    Tags               107        Formulas            43
    Data properties    107        References          29
    Definition         106        Keywords            13
    Display properties  99        Similar tables       3
    Parameters          96

Definitions run to a median of 195 characters -- one or two sentences. 46 of
107 titles carry LaTeX; 102 tables use `$...$` in their prose, 52 use `CITE{}`
for a reference and 7 use `HREF{}`.

Links are how a reader checks the table against something outside it, and they
should go to sources that will still be there: Wikipedia (85 tables), LMFDB
(13), mpmath (9), MathWorld (7), OEIS (5), or a paper.

**The definition must fix the convention.** This is the one place where the
corpus is not a good model for what to do next. T52 defined the p-adic
arithmetic-geometric mean by its iteration and never said which square root,
and over Q_p the two choices give different limits -- so the table could not be
reproduced from what it said, and reading it the natural way gave a different
number for every entry at every odd prime. T45's stated parameter constraint
excluded two thirds of its own entries. Both are fixed; neither was found by a
test, because neither is the kind of thing a test can see. A definition that
does not pin the branch, the normalisation and the indexing is incomplete even
when every digit in the table is right.

## `Programs` and `generate.py` are different things

Both exist, and a table wants both where both apply.

**`Programs`** is for daily use: the standard incantation in Sage, PARI or
mpmath that produces these numbers, so a reader who wants one more value knows
what to type. 45 tables have one, all Sage.

**`generate.py`** is for reproducibility: the program that produced *this
table*, attached to it, which recomputes and republishes it and can extend it.
Fifteen tables carry one; 91 attachments are the older `generate.sage` scripts,
kept as history and never run by the server.

A one-line `Programs` entry does not make a table reproducible, and a
`generate.py` does not tell a reader how to get the next value in one line.

## Entries

    params 4776 · number 4771 · comment 535 · equals 60
    both signs 59 · url 59 · proof 30

`equals` links an entry to the table that holds the same number under its own
name -- the entry for the volume of the 2-ball says `HREF{Pi}` rather than
repeating it -- and `comment` carries whatever a reader needs to know about
that value in particular.

## Style

Concise, exact, and checkable. A table is a reference: it says what the numbers
are, how they are indexed, where they came from and how well they are known,
and it says each of those once. Prose that could be a link should be a link;
prose that could be a formula should be a formula; a claim that could be wrong
should be one somebody can check without asking the author.

## What making tables 108 and 109 taught

The Fibonacci and Lucas polynomials were the first tables made with the skill
rather than by hand, and they needed six rounds of correction. Four of those
were the skill's fault and are now lines in it.

**A definition is not a place to put everything true about the table.** Both
definitions grew to hold a definition, an alternative indexing, the value at
x = 1 and a pointer to the companion table. The sections for those already
existed and the skill never said which was which.

**Reference the database before the encyclopedia.** The Chebyshev polynomials
were cited as a Wikipedia article by a table whose own database holds them as
T99. A reader following a reference should land on the numbers.

**Readability binds before the size limit.** The range was first set at n = 150
because that fitted every limit comfortably. It came down to 100 because
F_150 is 2248 characters and nobody reads that.

**Notation has to be defined where it is used.** A comment said the values are
the Lucas sequences U_n(x,-1) and V_n(x,-1) without saying what U and V are.

And two that were not the skill's fault but are worth keeping:

**A suggestion is a hypothesis.** Tagging these as orthogonal polynomials was
a reasonable idea and false -- Favard's condition fails, and what holds instead
is an indefinite pairing on the imaginary axis. Checking took twenty minutes
and the table now says something true and interesting instead of something
plausible.

**A measurement needs a control that returns a known answer.** The first
version of that check used Simpson's rule on a singular weight and reported
-0.023 for a pairing that is exactly zero -- and its control, the Chebyshev
family, silently returned zero for everything through a coercion error, so it
agreed with the wrong answer while looking like agreement.
