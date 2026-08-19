# Guarding tables that a program made

Written after two tables were made with an assistant and needed six rounds of
correction. The question is what can be checked automatically, and what a
critique loop would add on top.

## What the corrections actually were

Worth listing before designing anything, because the answer is not what it
feels like from inside the work.

| what was wrong | mechanically checkable? |
|---|---|
| Wikipedia cited for the Chebyshev polynomials, which the database holds | **yes** -- compare link titles against table titles |
| Definition holding a definition plus three other things | **yes**, approximately -- length, and phrases like "note that" |
| A `Programs` snippet whose range no longer matched the table | **yes** -- parse the range, count the entries |
| `HREF{Roots_or_unity}`, one character wrong | **yes** -- resolve every target |
| A tag no other table uses | **yes** |
| U and V used and never defined | partly -- a symbol in a formula and nowhere else |
| The range being 150 when 100 reads better | no -- that is taste, and it was Benjamin's call |
| "Tag them as orthogonal polynomials" being false | no -- that took a measurement |

So most of it is mechanical, and `manage.py audit_table` now does that part.
Run over the whole corpus the first time, it found a broken cross-reference
that had been published for years, two external links to tables the database
holds, and fifteen stale snippet ranges.

## The layer above: what a critique could add

The two rows at the bottom of that table are the interesting ones, and they are
different from each other.

**Taste** -- is this range sensible, does this definition read well, is this
comment worth having -- is what a reviewer is for. A model can draft an opinion
about it. It cannot settle it, and a loop that acted on its own opinion would
be optimising prose nobody asked it to touch.

**Mathematical claims** are the ones worth attacking, because they are the ones
that are wrong in ways nothing else catches. "These are orthogonal polynomials"
is the example: plausible, standard-sounding, false. What settled it was not an
opinion but an experiment -- Favard's condition, then a quadrature with a
control.

So the useful shape is not "an LLM checks the table". It is **an LLM proposes
experiments, and the experiments are run**:

    claim in the table  ->  a check that would fail if it were false
                        ->  run it  ->  a finding with evidence

That keeps the model doing what it is good at -- reading prose, noticing what
is asserted, thinking of a way to test it -- and keeps the verdict with
arithmetic. It is also how the sweep already works, and the sweep has never
once been wrong about a value; the four times it disagreed with the corpus, the
checker was at fault, which is exactly why the verdicts have to be reproducible.

## The repair loop, and why it should not close

A critique that proposes fixes is useful. A loop that applies them is not, and
the reason is specific rather than squeamish.

Every mistake in the list above is one where the *wrong* version looked fine.
A repair loop is a machine for producing plausible text, judged by another
machine for plausibility. Run it twice and the table is prose nobody wrote and
nobody checked, in a database whose whole claim is that its numbers can be
traced to something.

So: **critique produces findings, repair produces a diff, and both stop.** The
draft lifecycle already has the right shape for this -- a table is proposed,
filled, offered, reviewed, published -- and a proposed repair is another thing
to offer, not another thing to do.

The one exception worth allowing is repairs that are *verifiable*: a link that
404s and has a working replacement, a snippet range that disagrees with a count.
Those have a right answer that a test can state, and the test is the guard.

## What to build, in order

1. **`audit_table` in the deploy check and the sweep service.** It costs
   nothing and it has already earned its place.
2. **The claim-to-experiment step, offline.** Take a table's Comments and
   Formulas, ask for each assertion a check that would fail if it were false,
   run those, report. Start with the tables whose rigour is weakest.
3. **A critique of prose, as a suggestion on the table's discussion**, where a
   person sees it beside the table and nobody has to trust it.
4. **Repairs only where a test can state the right answer**, and even then
   through the review queue.

Nothing here needs a large model. The claim-to-experiment step is the only part
that benefits from a good one, and it is also the part whose output is checked
by arithmetic rather than believed.
