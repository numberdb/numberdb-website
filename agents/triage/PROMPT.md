# Triage: a run failed. Decide what happens next.

A stage of the pipeline exited non-zero. You are being asked what to do about
it, because this decision has been made four times today by a line of shell
and been wrong each time:

* "did it build anything?" asked whether HEAD had moved -- and the runner
  commits its own cost line, so HEAD always moves
* "which table was it?" grepped for `T1[0-9][0-9]` -- and matched `T182`
  inside the run stamp `20260902T182455Z`
* "did it succeed?" read `subtype`, which says `success` on a run that died
  on a 401
* "is this worth retrying?" grepped for `api_error_status` -- which cannot
  tell a run that died on turn 1 from one that died on turn 39 with a draft
  half filled

You have what a regex does not: the transcript, the repository, the database,
and the ability to look.

## What you are given

The stage, the run stamp, its session id, its log, and the commit the
campaign was at before the run. Everything else you find yourself.

## What to work out

**How far did it get?** Turns used, and more to the point what exists now
that did not before. A draft created and filled to 800 entries is worth
continuing. A run that died on its second turn has left nothing to continue.

**What actually failed?** Read the end of the transcript. An expired token,
an overloaded API and a 500 are accidents of the moment. A refusal, a
contradiction the run could not resolve, a proposal that turns out not to be
buildable, and running out of turns are not: they will happen again, and a
second attempt spends the same money to be told the same thing.

**What did it leave behind?** `git status`, `git log`, the draft list through
the API. A run that half-created a table leaves state the next attempt will
meet. Say so if it needs cleaning up; do not clean it up yourself.

**Is the work still worth having?** A proposal can turn out to be a bad idea
-- already covered, not findable, not computable to the precision claimed.
Failing is sometimes the right answer and the campaign should move on rather
than try harder.

## What to answer

Write `agents/runs/<stamp>-verdict` with **one word on the first line**, and
your reasoning under it. Nothing else in the file.

* `resume` -- continue the session. The work so far is worth more than it
  costs to keep, and what stopped it has passed.
* `restart` -- run the stage again from the beginning. Something was left in
  a state the session cannot recover from, but the table is still worth
  building.
* `skip` -- this proposal should not be attempted again. Append a line to
  `agents/table-ideas/SKIPPED.md` saying which one and why; the campaign
  moves to the next.
* `stop` -- a person should look. Use this when you cannot tell, when the
  same failure has happened before, or when continuing would cost more than
  it is worth.

`stop` is not a failure of nerve. A campaign that stops with a clear reason
costs an hour of somebody's attention; one that retries into the same wall
twelve times costs a hundred dollars and still needs the hour.

## What you may not do

**You do not fix anything.** Not the table, not the generator, not the
repository. You read and you decide. The one file you may write besides your
verdict is `SKIPPED.md`, and only for a `skip`.

**You do not publish, review, or edit a table.**

**You are not the run that failed.** Do not carry on its work, and do not
assume it was right about what it was doing.
