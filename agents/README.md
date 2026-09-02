# Agents

Programs that reach the database only through the API, holding a key, rate
limited, named in `produced_by`, unable to publish. The same boundary a human
contributor works across; an agent should not have a private door. See
`docs/design/guarding-generated-tables.md`.

    table-ideas/    stage one: propose tables worth making
    table-build/    stage two: build one proposal, leave it offered for review
    lessons/        what a run met that the skill did not cover

Each stage is a fresh session, one batch at a time. The skill is the memory: if
a run cannot do the work from <https://numberdb.org/skill> alone, the skill is
incomplete, and a long session would hide that behind conversational memory
rather than fixing it. `docs/design/two-stage-tables.md` argues this out.

## The agent account

Stage two writes as **zeta3**, not as a person. GitHub:
<https://github.com/zeta3-bot>.

A separate account is worth the trouble for two reasons: what it wrote is
attributable to it rather than to whoever's key was lying around, and its key
can be revoked without revoking anybody's own access.

**What it may do.** Write to tables through the API, and create up to five
unpublished drafts at a time. That is all, and the limits are the point:

* it may **not** publish. Publishing is board-only and stays a person's act.
* it may **not** review. Marking digits confirmed is board-only.
* its edits are **not** auto-marked reviewed, so every one waits in the queue
  and stays out of search by number until somebody looks.

So "give it API access and review every call" needs no special mode. It is
what an ordinary vouched-for account already does.

**Why it is vouched for rather than having earned it.** Writing through the
API normally needs five reviewed edits. An operated account can never get
them: `accepted_edit_count` will not credit an assistant's revision that its
operator confirmed, and zeta3's operator is its only reviewer. So it is in the
`trusted` group instead -- a grant that is visible in the admin and can be
taken back in one click. `UserProfile.operated_by` records who runs it, and is
what makes the counter see through the second username.

**Its key.** Issued once, stored in a file, never printed and never pasted
anywhere. The client reads it from `NUMBERDB_API_KEY`; keep it in a
mode-600 file and pipe it, so it does not end up in a shell history or a
transcript. If it leaks, revoke it -- `last_used` shows what it did.

**What it must set.** `NUMBERDB_ASSISTED_BY`, so `produced_by` records that an
assistant wrote the revision. That is what the trust counter reads, and
leaving it unset would quietly claim the work was unassisted.

## What a run costs

`agents/runs/COSTS.tsv` gets a line per run, written by `run.sh` from the
result record. The first five, all on Claude:

| stage | runs | turns | cost |
|-------|------|-------|------|
| ideas | 3 | 39-108 | $8.71, $9.86, $10.49 |
| build | 2 | 72-121 | $12.17, $15.70 |

So roughly **$10 for a batch of five screened proposals** and **$14 for one
table built, checked and offered** -- about **$16 a table** once the
proposing is amortised over the batch it produces.

Two things that number does not include, and both are larger than it. A
person still reads every table before it is published, which is the gate and
is not going away. And three of those five runs found a defect in the tooling
rather than producing a table -- the first could not reach the network at all.
That rate should fall, but a run that finds something is not a wasted run.

The transcripts are about a megabyte each and are gitignored; the ledger is
not. Sessions accumulate elsewhere too: this machine's `~/.codex` holds 5.7 GB
and `~/.claude/projects` 172 MB, neither of them written by this pipeline.

## Who an edit is by

Two accounts, and the distinction is about *who decided*, not about which
software typed:

* **zeta3** — the run was autonomous. `agents/run.sh` started it, nobody
  watched it, and it stopped at a draft offered for review. Its revisions say
  which generator produced them and which tool ran it:
  `QuadraticRegulators (numberdb=0.1.0, ...), assisted by claude (agent run ...)`.

* **bmatschke** — the edit was made in a session with a person, whatever tool
  did the typing. Those revisions must still record the assistant, in
  `produced_by`, beginning with the words `assisted by`: a reader is entitled
  to know a program was involved, and `accepted_edit_count` reads that phrase.

The failure to avoid is either one claiming the other's work. An autonomous
run recorded as a person's hides that nobody read it; a person's session
recorded as the bot's hides that somebody chose it.
