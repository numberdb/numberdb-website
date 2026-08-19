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

## Where the pieces go

The constraint that decides most of this: **the model cannot run on the
server.** numberdb.org is a 1 GB machine already running Sage and Postgres, and
the review queue was killing workers last week for want of a few hundred
megabytes. So the split is not a matter of taste:

    on the server, in this repository        outside, where the model runs
    ---------------------------------        -----------------------------
    audit_table      deterministic           reads tables through the API
    sweep_arb        recomputation           proposes experiments
    the sandbox      runs proposed code      decides what is worth checking
    review queue     a person decides        posts findings, proposes drafts
    the API          the seam between them

Everything whose verdict has to be reproducible lives on the left, in version
control, runnable by anybody. Everything that involves a model lives on the
right and reaches the database only through the API -- which means it holds a
key, is rate limited, is named in `produced_by`, and cannot publish. That is
the same boundary a human contributor works across, which is the point: an
agent should not have a private door.

### On the server

1. **`audit_table` in the deploy and on a timer.** It is written; what is left
   is wiring. `scripts/ship.sh` should run it after a deploy the way it already
   runs the search check, and `scripts/systemd/numberdb-audit.timer` should run
   `--all --links` nightly, since a link that has rotted is not something a
   commit will tell you about.

2. **`audit_table --json`.** Findings for a machine as well as a person: table,
   check, severity, message. The sweep already writes JSONL and the shape is
   worth copying, including the checkpoint, since `--links` is slow.

3. **A discussion endpoint.** `/discuss/T61` exists as a page and has no API,
   so an outside agent has nowhere to put a finding. `POST /api/table/<tid>/
   discussion` with a key, rate limited like everything else. This is the piece
   that makes the loop useful rather than clever: a finding appears beside the
   table, attributed, where a person sees it in the ordinary course of looking.

4. **A checking endpoint, or not.** The sandbox in `workers/` runs untrusted
   expressions for advanced search: prefork, rlimits, no network, killed after
   one evaluation. It could run an agent's proposed experiment too. I would not
   do this yet -- it lets an outside agent spend server CPU on code the server
   did not write, and the same sandbox runs perfectly well on the machine the
   agent is on. Revisit if a finding ever needs the server's data to check.

### Outside

5. **`agents/claim-check/`** in this repository, because it encodes the
   conventions and should be versioned with them, and because a person should
   be able to read what the thing does. It:

       fetches a table with the numberdb package
       lists the claims in its Comments and Formulas
       for each, asks the model for a Sage snippet that FAILS if the claim
           is false, and a one-line statement of what failure would mean
       runs each snippet under workers/sandbox.py
       reports: claim, snippet, output, verdict

   The prompt is a file in that directory, not a string in the code. Every
   claim it fails should be reproducible by pasting the snippet into Sage, and
   a finding that cannot be reproduced that way is a bug in the tool.

6. **The critique of prose** is the same program with a different prompt and no
   experiments: it reads a table and says what a careful reader would ask.
   Output goes to the discussion, marked as a suggestion. Nothing acts on it.

### What stays a person's

Publishing. Applying a repair that no test can state the right answer for.
Deciding whether a table should exist. The lifecycle already has the shapes for
these -- draft, offer, review -- and the loop above adds a fourth thing to
offer rather than a fourth thing to do.

## What to build, in order

1. Wire `audit_table` into `ship.sh` and a nightly timer. An afternoon.
2. `audit_table --json`, and the discussion API endpoint. These are what turn
   an outside agent from a thing that prints to a thing that contributes.
3. `agents/claim-check/`, starting with the tables whose rigour is weakest --
   `heuristic` and `assumed-bound` -- because those are where an unchecked
   claim is most likely and least likely to have been noticed.
4. The prose critique, once the claim checker has been wrong a few times and
   the failure modes are known.

Nothing here needs a large model. The claim-to-experiment step is the only part
that benefits from a good one, and it is also the part whose output is checked
by arithmetic rather than believed.
