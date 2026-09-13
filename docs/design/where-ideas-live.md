# Where table ideas live

Status: accepted 2026-09-13, being implemented.

Ideation and building are already two stages (`two-stage-tables.md`). What was
never decided is what happens to a stage-one result between the two: a batch of
screened proposals is written to a file, and the file is where the design ends.
This note decides where that batch lives, who may act on it, and what happens
to the proposals nobody builds.

## What it costs to have no answer

Measured on 2026-09-13, from the run ledger and the two machines' disks:

* **Ideation is the most expensive stage per run.** Mean $8.30 across six runs,
  against $5.69 for a build, $7.21 for a repair, $4.24 for a critique. A run
  produces five or six proposals, so a screened proposal costs about $1.50
  before anybody tries to build it.
* **119 proposals had been screened**, 89 on the laptop and 30 on the builder,
  in 23 batch files. Roughly 39 have no table resembling them today.
* **None of them was in version control.** `.gitignore:188` excludes
  `BATCH-*.md` as data, correctly -- but nothing else carried them, so each
  batch existed on exactly one disk, one of them an EC2 instance that can be
  terminated. (Fixed first, before this note: `agents/archive-run.sh <file>
  ideas` puts a batch in `numberdb-runs/ideas/`, and all 23 are there.)
* **Only the newest batch is ever read.** `batch_file()` in
  `agents/campaign.sh` is `ls -t agents/table-ideas/BATCH-*.md | head -1`, so a
  campaign that ends mid-batch leaves the rest reachable, and a campaign that
  exhausts one abandons every proposal in every earlier file for ever. On
  2026-09-13 at 17:47 a campaign paid $8.30 for a fresh batch while about
  twenty screened proposals sat unbuilt in older files on the same disk.
* **The screening cannot see itself.** The miner's `already_asked()` searches
  numberdb-data issues, and proposals were written to a gitignored file, so
  "Covolumes of the Bianchi groups" was screened on the laptop on 2026-09-11
  and screened again on the builder on 2026-09-12.

Whole families are stranded, not stragglers: of the five symmetric-function
proposals screened on 2026-09-12 -- Kostka-Foulkes, Macdonald-Kostka,
Hall-Littlewood, the $q,t$-Catalan numbers, Hall polynomials -- **none** was
built, and the next ideation run did not know they existed.

## Three layers, and only one of them is authority

* **What is wanted.** numberdb-data issues, written by anybody, human or
  machine. 88 open today.
* **What is planned.** The queue this note is about: a screened, ranked,
  argued plan. Advisory, expiring, and per-agent.
* **What is true.** The corpus, gated by review. The only authority.

The test the design must pass: **nothing about the queue may make an unqueued
table harder to create.** A person editing through the site, or somebody
else's bot with an API key, must be able to reach a published table without
ever touching a proposal. The queue exists to stop us paying twice to screen
the same idea. That is all it is for, and it is worth about $1.50 a proposal.

So `zeta3-bot` is not privileged, only noisy. Another operator's agent may keep
its own queue, in its own repository, and collaborate through the two things
that are actually shared: the wanted-issues and the corpus.

## What makes concurrency safe is in the database, not in the tracker

These already exist, and they hold for an agent that never heard of our queue:

* **`Table.title` is unique**, so creating a draft *is* the claim: the first
  wins, whoever they are. `numberdb_app/test_proposal_claim.py` pins it.
* **`TableLease`**, twenty minutes, refreshed by each submission
  (`numberdb_app/api.py:1330`): "long enough that a single expensive entry does
  not cost a generator its claim, short enough that a table is not held by a
  dead process for an afternoon."
* **Review.** Nothing reaches the corpus without a person accepting it
  (`guarding-generated-tables.md`).

A label on an issue is not allowed to be load-bearing for correctness. If the
queue and the database ever disagree, the database is right.

## The family is the unit of ideation; the table is the unit of building

A batch is a family: tables that share machinery, share a tag, and
cross-reference each other. That coherence is most of why the batches have been
good, and it is what a flat list of proposals would throw away. The hyperbolic
family survived only because one campaign happened to get through it -- T219,
T222, T223, T224, T225, all pointing at each other as designed.

So the queue has two levels:

* **One issue per family** in numberdb-data, labelled `proposal`: the summary,
  the conventions the tables share, the tag they need, a checklist of the
  tables, and which `table wanted` issues it draws on. About eight issues, not
  forty, so the tracker stays readable beside the human requests.
* **The full screening report** stays in `numberdb-runs/ideas/`, where the
  batch files now are, linked from the issue. Long machine prose belongs where
  machine prose lives; the issue is an index and a place to argue.

Overlap is by reference and is many-to-many: a family says which wanted-issues
it draws on, each table says which it answers, and a `table wanted` closes when
the tables answering it are published -- possibly from two different families.
That is already the true shape; today it is invisible.

The build order follows from the family being real: **finish the family you are
in before opening another.** Today that happens only by accident of file
mtimes, and breaks exactly when a campaign ends mid-family.

## A proposal is a claim about a date

Every proposal asserts something about the world when it was screened: nothing
here holds this, no issue asks for it, these sources name it, these numbers
check out. All of it rots. The corpus grows; sources move; the house style
moves weekly. The measurement above is the rot made visible -- of the laptop's
89 proposals only about 19 have no table like them today.

Therefore:

* Every family carries **`screened: <date>`** and the checks that were run.
* A build **re-runs the cheap half of the screen before building**:
  `already_here`, `already_asked`, `api/lookup` on the sample values, and does
  the tag exist. Seconds of work against a $5.69 build.
* A family older than **six weeks** is re-screened in full or closed with a
  comment saying what changed. A closed family is not a loss; it is the corpus
  telling us what it learned.
* The queue stays **shallow on purpose**: eight to fifteen open proposals,
  refilled on demand. A hundred-deep backlog of month-old screening is a
  liability that looks like an asset.

## Two agents, one subject

Three cases, and only one is hard.

1. **Same table, same intent.** The title claim settles it: the loser moves to
   the next proposal. This works today, across worktrees that cannot see each
   other.
2. **Same numbers, different titles.** The real hazard, and we have met it:
   T219 and T225 were nearly the same table, and a reader spotted it, not a
   check. Prose cannot catch this; digits can. A draft's values go through
   `api/lookup`, and whatever tables already hold them are reported. This
   belongs in the audit, which is now reachable over the API, so a build sees
   it before offering and a reviewer sees it too. It is the one check here that
   protects against agents who ignore the queue entirely, which is why it is
   worth more than the queue.
3. **Same subject, different design** -- one table with a parameter against one
   table per value of it. Editorial, and it belongs to review. What the family
   issue buys is that the argument is written down before the money is spent.

## The jobs

Ideation and building have nothing in common operationally: ideation needs
network and reading, no Sage, no SnapPy, about thirteen minutes; a build needs
the heavy image and about forty. One ideation run feeds five or six builds. Run
together in one loop, every build machine occasionally stops to pay for
screening, and a failed screening kills a campaign.

* **The ideas job** tops the queue up when fewer than eight proposals are open,
  and writes a family issue plus the archived report.
* **The build job** takes the highest-ranked unbuilt table of the family it is
  already in, else of the newest family with work left, re-screens it cheaply,
  claims it by creating the draft, builds, and ticks the box.

Several build jobs can then run on different machines against one queue, which
is the point: the claim is the draft, so they cannot collide even when the
queue is stale.

## What this does not do

* **No proposal table in the database.** A T-number is issued when a draft is
  created, which is early enough; a second identifier before that would have to
  be reconciled with the first, and the tracker already gives us one.
* **No automatic closing of `table wanted` issues.** A person decides when a
  request has been answered.
* **No gate.** Building a table that is in no family stays exactly as easy as
  it is today.
