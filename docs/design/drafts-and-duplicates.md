# Drafts, and two people making the same table

Written while working out how an assistant could draft a table without a person
having to create it first. Most of what was needed turned out to exist.

## What already works

A table can be created unpublished, and a draft:

- **keeps the T-number it was given.** Publishing flips a flag and changes
  nothing else. The alternative -- a temporary number that becomes a T-number
  -- is the one that goes wrong, because a generator carries the identifier of
  the table it fills and is written while the table is still being set up.
- **is invisible.** Not in the listing, not in search by number, not readable
  by a stranger. Its author and the board can see it, the latter so that an
  abandoned one can be found.
- **costs a number when abandoned.** Accepted deliberately: a gap in the
  numbering is an honest record that something was started and not finished.

Added while writing this note: **a draft's address follows its title.** The
slug of a published table is frozen because every link anybody has written
points at it -- but nobody can have linked to a draft, so the reason for the
rule is the reason for the exception. It freezes at publication, when the
address starts to mattering.

## What is still missing

**Creating a draft through the API is board-only**, like creating any table.
That is right for published tables and probably wrong for drafts: the reasoning
behind the restriction is that a table is "a permanent T-number, a title in
every listing, a namespace whose parameter order can never be changed, and
prose that no reviewer wrote", and a draft is none of those things until
somebody publishes it. A loop that makes three hundred drafts is still a mess,
but it is a mess in a place nobody can see, and one that can be cleaned up.

The rate limit and a cap on unpublished drafts per account would do what the
board-only rule is doing now, with less friction for the case we actually want:
an assistant proposing a table, a person deciding whether it should exist.

## Two people, one subject

The question this note exists for. A draft can sit for months, and meanwhile
somebody else -- or somebody else's assistant -- starts the same table.

**Sometimes that is correct.** T103 and T104 are the Hermite polynomials in the
physicists' and the probabilists' conventions: the same objects, held twice,
deliberately, because the two conventions are both used and a reader arriving
with a number needs whichever they have. Duplicate *subjects* are not the
problem. Accidental duplicate *work* is.

**So the fix is visibility, not prevention.** The reason to hide a draft's
content -- its numbers are unreviewed and may be wrong -- is not a reason to
hide its existence. A list of drafts in progress, showing the title, the
subject, who is working on it and since when, visible to anyone signed in,
lets somebody about to start a table find out that it is already being made.
This is what the OEIS does with draft sequences, for exactly this reason.

That leaves the numbers invisible, which is the part that matters: an
unreviewed value must not answer a search by number, because a reader looking
at a table can see that it is a draft and a reader typing digits cannot.

**Staleness should be shown, not enforced.** An automatic expiry deletes
somebody's work on a timer, and the timer will always be wrong for somebody.
Showing the age in the list is enough for a person to ask, and the board can
already see and close an abandoned draft. If it becomes a real problem, a
prompt to the author before the board acts is the next step, not a cron job.

## What was built, 2026-08-18

1. **A drafts listing at `/drafts`**, for anybody signed in: number, title,
   who started it, when, and when it last changed. Existence only -- the title
   links through to the table for its author and the board, and for everybody
   else it is a name and a date. The values stay out of search, which is the
   part that matters: a reader looking at a table can see it is a draft, and a
   reader typing digits cannot.

2. **Draft creation through the API**, with `X-Draft: yes`, open to any account
   that may write with a program and capped at five drafts in flight. The cap
   is on drafts *held*, not drafts made: publish one and the allowance comes
   back. The board is not capped. A refusal says how many are held and why the
   limit exists, and every successful creation reports `drafts_held` and
   `drafts_remaining` so a caller need not be refused to find out.

   `X-Draft` is explicit rather than inferred, because creating a table and
   proposing one are different acts with different consequences.

Still to do: a note on the "table wanted" issue when a draft claims it, so the
two coordination points do not drift apart.

Publishing stays a person's act, and should. It is the moment a T-number
becomes permanent and a table starts answering searches.
