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

**Look for the entry that identifies nothing.** A family can be distinctive
and still contain one value that is not: the Hilbert class polynomial of
Delta = -3 is `x`, because j vanishes there, and `x` already answers a search
in ten other tables. One such entry is not a reason against the table -- it is
the true value and a hole where the most famous case should be is worse -- but
it is a reason to say so in its comment, so that a reader who arrives at it by
searching sees immediately why the hit means nothing. Check the shortest and
the most common-looking entries in your range before you fill, with
`numberdb.search_number` or `/api/lookup`, and write the comment then rather
than after somebody notices.

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
