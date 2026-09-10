# Stage two: build one proposed table

You are building a table for NumberDB from a proposal. You will leave it as a
draft offered for review. **You will not publish it** -- that is a person's act,
and the reasons are in `docs/design/guarding-generated-tables.md`.

Read <https://numberdb.org/skill> first and follow it. What follows is the
order of work and the mistakes that have actually been made, not a replacement
for it.

## The order of work

**1. Look at the database.** Search for the family and its neighbours. A table
that duplicates one already here, or that cites Wikipedia for something the
corpus holds, is the commonest fault. Read the address of every table you
intend to link to -- `numberdb.table('T119')` and the `url` in the answer --
and never derive a slug from a title. "Power sum symmetric polynomials" is at
`Power_sum_symmetric_polynomials`, and a link written to
`Power_sum_polynomials` points at nothing.

**2. Settle the convention.** Write the definition first, before computing
anything, and make it pin down every choice: the branch, the normalisation, the
indexing, the parameter order, the variable names. The test is whether two
people would build the same table from it. If the proposal left something open
and you cannot settle it from a source, **stop and say so** -- a table whose
definition was guessed is worth less than no table.

**3. Measure before choosing a range.** Compute the family, and look at how
long the longest entry gets written out. Length is what decides these tables,
not the size limits: the Fibonacci polynomials stop at n = 100 where the entry
is 1107 characters, and `h_6` in six variables would be 6969. Aim for a
complete rectangle -- holes in the middle of a table that nothing explains are
worse than a smaller table.

**4. Check every identity before you write it down.** Not after. Recurrences,
generating functions, specialisations, relations to other tables -- each one
verified over the whole range you intend to publish. A suggestion is a
hypothesis: "these are orthogonal polynomials" is plausible and false for the
Fibonacci family, and twenty minutes of checking turned a wrong tag into a true
and more interesting statement.

**5. Verify against something outside the family.** A generator checked against
its own definition proves nothing. Find an independent fact: Cayley's formula
for the Abel polynomials, the Cauchy numbers for the Bernoulli polynomials of
the second kind, Sage's own `SymmetricFunctions` for the symmetric families,
counted set partitions for the Bell coefficients.

**6. Write the generator.** Name the rings you use rather than importing
`sage.all`; import `numberdb.sage` first, because it initialises Sage. Then:

* **Do not divide.** `factorial(n)` in `sage -python` is a Python int, so `/`
  is float division: exact to 2^53 and quietly wrong after. A Bessel polynomial
  built from its closed form was right to n = 15 and wrong from n = 16, in the
  last two digits. Build from a recurrence, or write every division between
  Sage rationals. `c in ZZ` is true of a float, so that check will not save you.
* **Expect the machinery to be missing.** With named imports, power series
  `.log()` and `.inverse()`, `matrix(...).determinant()`, and
  `SymmetricFunctions(...).expand()` all reach for parts of Sage that are not
  initialised. Write the arithmetic out: a determinant over permutations, a
  series product coefficient by coefficient.

**7. Do all of that before the table exists.** A table's history is public and
permanent, so a table should not be built in it: repairing one in public leaves
a revision per mistake. The Fibonacci polynomials took nine revisions, six of
them corrections that could have happened privately; the tables built the other
way took two.

    sage -python agents/table-build/dry_run.py path/to/generate.py

computes every entry, checks the exactness, measures the longest one, and sends
nothing. It needs no table and no key -- the generator is asked for its values
directly. Iterate here: change the range, fix the arithmetic, settle the
definition, and run it again. It exits non-zero while anything is wrong.

**8. Then create the draft, fill it once, and run `verify()`.** Two revisions,
not nine. Check the identities again **on the values read back out of the
database** -- `verify()` compares a table with the generator that made it and
cannot catch a generator wrong in the same way twice.

If something still needs repairing after this, repair it: a wrong table is
worse than an untidy history, and `audit_table` findings are worth acting on
whenever they arrive. The point is not to publish nothing twice, it is to have
done the obvious checking first.

**9. Run `manage.py audit_table T1xx`** and act on what it says. It catches
what a person does not: a CITE naming nothing, a link out to something the
corpus holds, a definition that has grown into four things, a snippet whose
range no longer matches the table, a published table linking to a draft.

**10. Offer it for review** and stop. Say what you did, what you checked, and
what you decided that the proposal did not settle.

## Run the checks rather than re-writing them

`agents/table-build/check.py` holds what this work needs repeatedly. Use it
instead of writing your own, which is how it stays as good as the day it caught
something:

    exactness(values)        every coefficient is an exact Sage number.
                             Catches the float class mechanically: a Bessel
                             polynomial built by dividing Python ints reports
                             "coefficient 1.0 is a float", where `c in ZZ` says
                             nothing is wrong.
    measure(values)          entries, longest written entry, block size --
                             so the range is chosen from data.
    agrees_with(values, f)   compare against a computation sharing no code.
    names_its_rings(path)    the generator does not import sage.all, and does
                             import numberdb.sage.
    stored(tid)              the table read back, to check identities on what
                             was published rather than on what was computed.

## Three rules that are not checks

These are where a run is weaker than a careful person, so they are stated
rather than left to judgement.

**When two computations disagree, neither is right until you know why.** Do not
pick the one that looks better and move on. The Bessel polynomials came from a
closed form and from a recurrence, and they differed from n = 16; the cause was
float division, and taking either at face value would have published wrong
digits. Chase it to a cause you can name.

**A measurement needs a control that returns an answer you already know.** The
first attempt at an orthogonality check used Simpson's rule on a singular
weight and reported -0.023 for a pairing that is exactly zero -- and its
control silently returned zero for everything through a coercion error, so it
agreed with the wrong answer while looking like agreement. Run the control
first, and check it gives the known answer, before believing anything else the
method says.

**Declining is a good outcome.** A run that builds nothing and explains why is
worth more than one that guessed a convention. Four families were looked at and
left this week -- Mahler, Bateman, Boole, the Stirling polynomials -- because
each has more than one convention in circulation and there was no independent
value to check a choice against. Say what you found, what the choices are, and
what would settle it. A table whose definition was guessed is worth less than
no table, and is harder to remove than to never add.

## Two limits you will meet

**Six variables.** Matching polynomials that differ only in variable names
needs a key found by trying permutations, so more than six is refused. The
partial Bell polynomials stop at n = 7 because B(8,2) has seven variables.

**The parameters are the family's domain, not your range.** `$s$ a negative
odd integer`, not `$s\in\{-1,-3,-5\}$`; `$D$ a fundamental discriminant,
$D>1$`, not `$1<D\leq 1000$`. What you actually computed goes in
`Data properties` as `complete: no` with a `complete-note` saying which part
is finished. The note is read *inside* a sentence -- "Table is complete: no
(...)" -- so write a clause that finishes it: "it holds every real
fundamental discriminant with $D\leq 1000$". Otherwise extending the table
later means editing the definition of the family.

**If the table repeats another's values, declare it.** `Data properties:
repeats: HREF{Other_table}` says that where the two hold the same number,
that table states it first, and search then answers with the original instead
of twice. Only where this table repeats that one's computation: the
Gauss-Kronrod table stores the nodes of the embedded Gauss rule, which are the
Gauss-Legendre nodes. Where two tables agree because of a theorem -- Hermite's
constant in dimension 8 is the Hermite number of $E_8$ -- both should answer,
and declaring it would throw away the more interesting fact. See
docs/design/same-construction.md.

**An identifier goes in its field, not in the sentence.** A reference carries
`arxiv:`, `doi:`, `zbl:` or `mr:` beside its `bib`, and the page renders each
as a link to the paper. Ending the bib with "..., 567-615, arXiv:hep-lat/9607030"
puts the number where a reader can see it and not click it, and can only use it
by retyping. Nine tables did it in three days, fifty-two references between
them. `audit_table` refuses it now.

**Tags: prefer an existing one, and say so when none fits.** The tag list is a
way through the corpus. It is also unfinished, so if this table shares a
subject with two or more others and there is no tag for it, write that down in
your report -- naming the tables -- rather than settling for "physics". A tag
is proposed by the batch that needs it, since one table alone cannot show that
three would use it. `audit_table` refuses a tag that reaches only this table.

**One table per named object; the connection goes elsewhere.** T20 and T21
are the zeros of the Bessel functions of the first and second kind, T22 and
T23 their extrema, T25, T26 and T59 the three complete elliptic integrals.
Several named objects are several tables; one object at a sequence of index
values is one table; one object in two conventions is one table. That the
objects belong together is said in `Similar tables` (the relation, in words),
in `HREF` at first mention, in `equals` where two entries are the same
number, and in shared `Tags` -- not by putting them in one table, which is
the one place the relation cannot be written down.

**A value that is exactly a rational is written exactly.** Not
`3.000000000000000000000000000000`: a decimal means plus or minus one unit in
the last place however long it is, so that spelling says a number known to be
3 is known to thirty places. The exactly-known members of a family are usually
its most interesting rows -- the logistic map's $r=3$ and $r=2$, and the
$c=-3/4$, $-5/4$, $-1$ that go with them.

**Decide it from the definition, never from the digits.** A run of zeros is
evidence and not proof: 3.000000000000000000 may be 3, or 3 + 10^-40 rounded,
and no number of zeros separates them. $r=3$ is exact because the fixed point
loses stability where $|f'|=1$, which is an argument. Where there is no such
argument the zeros mean the opposite thing -- a rounding presented as sixty
significant places -- and the fix is fewer digits, or a ball. `dry_run.py`
reports the run of zeros and leaves the reading to you.

**Entries are shown in the order the document writes them**, so
`enumerate` decides what a reader sees first. For an index that runs over the
negative numbers as well, that is not the order of $\mathbb Z$: T165 led with
$a=-50$ and put $a=2$ -- Artin's own constant, the row anybody arrives wanting
-- halfway down. Enumerate by $|a|$, positive before negative, so the small
cases are at the top and $a$ and $-a$ are next to each other, which is what a
reader compares. Sorting does this without a special case where the two are
not a pair, as at $|a|=4$, where $4$ is a square and $-4$ is not.

**A value's display is a label, not a formula.** It is printed on every row
that value indexes, so a conversion rule put there is repeated once per row:
T168 carries `$c=-r(r-2)/4$` on all twenty-four of its $c$ rows, where `$c$`
was wanted and the formula belongs in `Formulas`. The same for a closed form
that the entry's comment already gives -- T167's Ramanujan row was labelled
`$15/\pi^2$, ...` and its comment says the identity in the sentence that
names it.

**Do not name a parameter by its key in prose.** T169's definition said "the
periodic-window quantity named by the parameter `expression`", which tells a
reader nothing: `expression` is how the document addresses a column, not a
word anybody outside it knows. Name the quantities, or use the parameter's
`display` symbol.

**And prefer a specific key to `expression`.** Twenty-two tables use that one
name for three unrelated things -- which form of a constant, which quantity of
an object, which length is normalised to 1. For a new table say which:
`quantity`, `form`, `normalisation`. The existing ones stay as they are,
because a key appears in entry addresses and renaming one breaks citations.

**The first line of the generator's docstring names the table**, as
`... -- numberdb.org/T164`. It is not decoration: the campaign reads it to
know which table to critique, and the cost ledger reads it to know what the
run was about. A generator that omitted it sent a critique and a repair at
the wrong table, which had been finished an hour earlier.

**Link the number, not the table, when the sentence means one number.**
A link may name an entry, `HREF{Feigenbaum_constants#delta}[$\delta$]` rather
than `HREF{Feigenbaum_constants}`, and the address after the `#` is the
entry's identity -- its parameter values as a citation writes them, so
`HREF{Golden_ratio#phi}` and `HREF{slug#Z,1,density}`. T169 sent a reader to
a table of six Feigenbaum constants where it meant $\delta$, and to three
golden-ratio rows where it meant $\varphi$. Read the keys out of `Numbers`
rather than inventing them.

**Cite what you already declared.** If `Links` holds the Wikipedia article for
the object, put `CITE{Wiki}` at its first mention in the definition. The
reference is there; the reader should not have to scroll for it.

**Write the symbol, not its position.** "The first factor", "the latter", "as
above" all make a reader count back through a formula and be wrong. Name it:
`$B_{2m}$ is in ...`. And **link a table the first time you name it, once per
section** -- the corpus holding the thing you are talking about is the most
useful sentence in a comment, and the fourth link to it in the same paragraph
is noise.

**Never "below" or "above" either.** The document is written with Comments
before Formulas; the page draws Formulas *first*, whatever order you wrote
them in, so "the class number formula below" sends a reader past it into the
Programs and back. Four tables said it before anyone noticed. `CITE` the
formula's label instead -- it renders as the formula's number -- or name the
formula itself: "by Siegel's formula $\zeta_K(-1)=\frac{1}{60}\sum\ldots$".
Both stay right if the page order ever changes. `audit_table` now refuses
this.

**A formula states a relation, not who checked it.** "Checked on every
entry", "both were computed and agree", "checked in ball arithmetic on every
rule here" are facts about your run. In a Formulas section they read as an
apology -- *we did not prove this, we looked* -- and the field for them
already exists: `rigour details`, under "How they were obtained". Put what
you verified there, once, and let the formula be a formula. `audit_table`
refuses this too.

**Write in sentences, not in dashes.** A `--` in a definition or a comment is
a parenthesis the reader has to hold open, and the renderer makes no
typographic substitution, so it reaches the page as two hyphens: in a field
full of minus signs that reads as mathematics. Say it with a comma, a colon
or a full stop. "converges uniformly for continuous $f$, which is Bernstein's
proof of the Weierstrass approximation theorem"; "each entry comment says
which argument makes it exact. In $c$ the surd cancels: $r=1+\sqrt6$ gives
$-r(r-2)/4=-(6-1)/4$."

The em dashes a reader does see, in the parameter list and in `Similar
tables`, are the site's own: it sets one between a parameter and its title,
and between a table and the relation glossing it. Those are punctuation the
page supplies, not something an author writes. A hyphen inside a word or a
key is a third thing again and is right as it is: period-doubling, `onset-c`.

**Write sentences, not notes to yourself.** Everything a reader sees is read
as English -- a comment, a formula's gloss, a data property. Five tables said
"every rule with $n\leq 30$ is here, nodes and weights, both halves", which is
four fragments stapled together: a reader cannot tell whether both halves of
every rule are listed, or both halves of something else, or whether "nodes and
weights" is a second thing the table holds. It says "it holds every rule with
$n\leq 30$, where $n$ is the number of nodes; each rule is listed in full,
every node with its weight, and both halves of the symmetric set."

The register is an encyclopedia's: precise, unhurried, and answering the
question a reader actually has. Name what a symbol indexes the first time the
field uses it, and use the table's own word for it -- if the parameter is
titled "number of nodes", write nodes, not points. Telegraphic is not concise;
it is unfinished.

**A comment states a fact.** Not how useful a search hit would be, not how
distinctive the value is, not what a reader should conclude -- those are
remarks about this website, and they read as apology. Where a value looks
surprising, the fact is the explanation: "the value is $x$ because
$j(\zeta_3)=0$" earns its place, and "this is the one entry that identifies
nothing on its own" does not. Write the first and stop.

**Entry comments are shown**, as a line under the value. Use one for a name a
reader would recognise -- 35 of the 996 small graphs have one -- and for a
caveat about a particular value.

## When you meet something new

Write it down, in whichever of two files it belongs to. Do not edit the skill
yourself: a person accepts a lesson, with a test that asserts it, in one
commit.

The skill is published at <https://numberdb.org/skill>, for somebody who has
Python and perhaps Sage and wants to contribute a table. **Could that person,
on their own laptop, hit what you hit?**

* Yes -- `agents/lessons/PROPOSALS.md`: what you had to decide that the skill
  did not cover, what went wrong, and what the skill should say.
* No, it is about this deployment -- containers, ssh, the proxy, the wrapper
  scripts, your own permissions, a bug in the site -- `docs/agent-environment.md`.
  Still worth writing down; just not a lesson about making tables.

A skill that carries somebody else's docker problem teaches the wrong thing to
everybody who reads it.
