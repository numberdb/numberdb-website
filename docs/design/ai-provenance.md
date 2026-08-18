# Who made this table, when part of it was made by an AI

Decided and implemented on 2026-08-18, before the first AI-assisted table was
submitted, because the answer is easier to agree on in the abstract than with a
finished table waiting. What follows is the reasoning; the last section records
what was built.

## The distinction that matters

Two different things get called "how this table was made", and conflating them
is what makes the question feel hard.

**What ran** is deterministic and already recorded: the generator is attached
to the table, and it says what was computed and how. What it does *not* record
is the versions of the software underneath -- Sage, arb, PARI, mpmath -- which
is a real gap, because "verify() disagrees" is only useful if something says
what the first run was. `Generator.environment()` exists for exactly this and
reports Python, Sage and the package version. It is deliberately minimal and
`publish` never calls it: what else is installed on somebody's machine is their
business.

**What was decided** is not deterministic and is not in the code. Which
convention, which range, which parameterisation, how the definition is worded.
A generator records the decision but not the reasoning, and reasoning is where
an AI's involvement actually bears on whether a reader should trust the table.

Only the second needs a new convention.

## Authorship: the person, and only the person

The author of a submission is the human whose key published it. Not a
co-author arrangement, and not the model.

This is the settled position in scientific publishing (ICMJE, Nature, COPE) and
the reasoning transfers exactly: authorship is accountability, and a model can
neither take responsibility for a wrong value nor agree to the licence the
data is published under. Somebody has to answer for T93's tails being wrong.
That is the person who published it.

So: **author = the person. AI involvement = a disclosed method.**

## Where the disclosure goes

`TableRevision.produced_by` already exists, is per-revision, and is already
shown in the blame view, the revision history, the file history and the review
queue. Its own comment says why: *"Reviewers triage generated edits
differently, and readers are entitled to know, which is why Wikipedia flags bot
edits."*

Today it holds `api`, or a script name, or the generator's class name. The
proposal is a convention for what to put there, and a `publish(...)` parameter
that sets it:

    generator.publish(assisted_by='claude-opus-5')

which records, say, `T25 generator, assisted by claude-opus-5 (numberdb 0.1.2)`.

Per revision rather than per table, because a table's history will mix: a
person may correct by hand a table an assistant created, and the history should
show which was which.

## When to disclose

A rule of "disclose any use" becomes noise -- everyone's editor completes lines
-- and cannot be checked. A rule of "disclose when it matters" is too vague to
follow. The line proposed:

**Disclose when the AI made a decision a reader would otherwise attribute to a
person.** Concretely, disclose if it chose the convention, the range or the
parameterisation; wrote the definition a reader relies on; or wrote the
generator. Do not disclose for renaming variables, formatting, running the
tests, or fixing a typo.

That is the same line the database already draws elsewhere: the *table* is a
claim, the *edit* is an act, and it is claims that need provenance.

## The edge case nobody asked about: the trust ladder

`accepted_edit_count` grants API write access once a person's edits have been
reviewed, and `is_trusted` opens publishing on that basis. The counter exists to
measure *a person's* judgement, and it was designed against gaming: it counts
reviews rather than approvals, because "a script can farm" approval.

An assistant producing fifty tables that their operator then reviews farms it
just as effectively, and more politely. Two possible answers:

1. Revisions whose `produced_by` names a model do not count toward
   `accepted_edit_count`.
2. They count only when the reviewer is not the author.

The second is better -- it keeps the ladder meaningful without penalising
somebody who uses a tool and gets genuinely reviewed -- and it is close to what
the review system already implies. Board members are exempt either way, being
trusted by definition, so this does not bite today. It will bite the first
outside contributor who arrives with an agent.

## Other cases worth deciding once

- **Model names age.** `claude-opus-5` will not mean in two years what it means
  now. Record it as reported anyway: it is a provenance note, not a promise.
- **Chains of tools.** An assistant may call others. Record what the publisher
  knows; do not demand a call graph.
- **AI wrote the checker, not the table.** No disclosure needed on the table:
  a check is either right or wrong, and the sweep re-runs it independently.
- **Table suggested by a "table wanted" issue.** Cite the issue in the table,
  under References. That is provenance of the idea, and it is owed to whoever
  asked for it, AI or no AI.
- **Nothing enforces honesty here.** True, and consistent: `rigour = heuristic`
  is also the author's word. The machine checks what it can -- `proven` is
  refused for a value carrying no error -- and the rest is stated, attributed,
  and revisable.
- **The licence.** Contributions to numberdb-data are covered by a CLA. A
  person can agree to it for work an assistant helped produce, but whether the
  CLA's wording needs a sentence about that is a legal question, not a
  technical one, and is worth asking someone qualified.

## What this costs to implement

Small. `publish(assisted_by=...)` passing an `X-Produced-By` header the API
already reads; a sentence in the skill; the trust-ladder change; and
`environment()` called by `publish` when the author asks for it, so the software
versions stop being the gap they currently are.

## What was built

- **`publish()` records the software versions.** `Generator.environment()` was
  never called by anything, so no table said which Sage produced it -- and
  `verify()` disagreeing in a year is only informative if something recorded
  the first run. The package and Sage versions now go into `produced_by`. Still
  no package list: what else is installed is nobody's business.

- **`NUMBERDB_ASSISTED_BY` names the tool that ran the publish**, read from the
  environment at publish time. Not written into the generator, and the reason
  decided it: a file saying `claude-opus-5` keeps saying it after another tool
  edits and republishes it, so a hard-coded name records who wrote the file
  rather than who submitted the run, and quietly credits one tool with
  another's work. `publish(assisted_by=...)` overrides for a caller that knows
  better. Unset means a person ran it.

  Recorded as `Zeta (numberdb=0.1.2, python=3.12.5, sage=10.9), assisted by
  claude-opus-5`, in the field the blame view, the revision history, the file
  history and the review queue already show.

- **The trust ladder counts people.** `accepted_edit_count` now ignores an
  assisted revision that its own author reviewed. Tables gained `reviewed_by`
  for this -- who confirmed the digits was not recorded at all, which is worth
  fixing on its own, since a review is a claim and claims have claimants.
  Reviews predating the field count as before: they were the board's.

- **Documented in three places** because there are three audiences: the skill
  (an assistant about to publish), the package README (somebody writing a
  generator), and the API reference (somebody writing their own client).

Nine tests. The open question left is the licence: whether numberdb-data's CLA
needs a sentence about assisted contributions is a legal question, not a
technical one.
