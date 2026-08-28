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
