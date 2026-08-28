# Making tables in two stages

Status: proposed, with the prompts written

Stage one proposes tables. Stage two builds one. They are separate because the
questions are different: the first is about mathematics worth recording, the
second about doing it correctly, and an agent doing both at once tends to
propose what it already knows how to build.

Neither publishes. A table becomes public when a person reviews it, for the
reasons in `guarding-generated-tables.md`.

## What each stage is

**Stage one** reads the corpus and the open issues, and writes a batch of
proposals: a coherent group of families, each with what it is, why a reader
might meet one of its members, what has to be decided before it can be built,
and roughly how big it would be. It writes no code and touches no table.

Its hardest instruction is what *not* to propose. numberdb-data#128 makes the
case against itself -- "Monomials. Trivial but maybe should be included?" -- and
a table of monomials would match everything and tell nobody anything. The test
is the use case: would a number that fell out of somebody's calculation turn
out to be one of these?

**Stage two** takes one proposal and does what the last few days have been:
search the database first, measure before choosing a range, check every
identity before writing it down and again on the values read back, reference
tables that exist here rather than encyclopedias, run `audit_table`, and leave
the table as a draft offered for review.

## Should the automation enhance itself?

**It should propose lessons, not apply them.**

The skill is the accumulated lessons, and an agent that finds one inconvenient
can soften it. The failure would be silent: the skill still exists, still reads
sensibly, and has quietly lost the line that prevented an error. "Measure the
largest entry before choosing a range" is exactly the sort of instruction an
agent in a hurry would relax.

There is already a guard, and it is the right one to build on: 36 tests assert
that specific lessons are present in the skill, by the sentence that carries
them. Deleting "readability, not size" fails CI. So the rule is:

> A new lesson lands as a diff to the skill **and** a test that asserts it,
> in the same commit, accepted by a person.

Stage two therefore ends by writing what it had to decide that the skill did
not cover, and what went wrong, to `agents/lessons/PROPOSALS.md`. That file is
input to a person, not to the next run.

This is not caution for its own sake. Six lessons appeared in the last week --
`factorial` returning a Python int so that `/` is float division; narrow
imports failing where `sage.all` is absent and vice versa; a slug guessed
rather than read; entry comments stored and never displayed; the six-variable
limit on the search key; drafts answering a public search. Every one of them
was found by something failing loudly, not by an agent noticing it was about
to be wrong. An agent editing its own instructions from a run in which nothing
failed would be editing from no evidence.

## One long session, or one per batch?

**One per batch, fresh.**

The skill is the memory. If an agent cannot do the work from the skill alone,
the skill is incomplete -- and a long session hides exactly that, because the
agent remembers being told something in conversation that was never written
down. A fresh session is the test of whether the skill is sufficient, run every
time.

It also bounds the damage. A batch that goes wrong goes wrong on its own, and
the drafts it left can be dropped without unpicking a week of context.

The cost is real: each run re-reads the corpus and re-learns the shape of the
work, and that is slower. It is worth it, on the same argument as everything
else here -- the expensive check is the one that catches the error the cheap
one misses.

## Is stage two as good as a person doing it?

No, and it is worth being exact about the gap rather than hoping.

Of the things that actually caught an error while these tables were being
made, four are now mechanical, three are stated as rules, and one is not
reproducible at all:

    caught by                                    now
    ------------------------------------------   ----------------------------
    float coefficients passing `c in ZZ`         check.exactness
    a generator importing sage.all               check.names_its_rings
    a range chosen before measuring              check.measure
    a slug guessed, a definition grown to four   audit_table
      things, a link to something we hold
    two computations disagreeing                 a rule in the prompt
    a measurement without a working control      a rule in the prompt
    guessing a convention rather than declining  a rule in the prompt
    somebody asking "is that actually true?"     nothing

The last line is the real one. Several of the best findings this week came from
Benjamin pushing back -- that multivariate polynomials are supported, that
entry comments were never displayed, that six variables is already a lot. No
prompt reproduces someone who knows the project asking whether a claim is true.

That is an argument for the review step rather than against the automation. The
run leaves a draft; a person reads it before it becomes public; and the run is
told to make that reading easy by saying what it decided and what it could not
check. It is also an argument for the adversarial pass sketched in
`guarding-generated-tables.md` -- a second agent whose only job is to attack
the table, propose an experiment that would fail if a claim were false, and run
it. That is the nearest mechanical thing to being asked whether it is true, and
it is the obvious next piece to build.