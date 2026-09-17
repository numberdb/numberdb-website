# Agents

Programs that reach the database only through the API, holding a key, rate
limited, named in `produced_by`, unable to publish. The same boundary a human
contributor works across; an agent should not have a private door. See
`docs/design/guarding-generated-tables.md`.

    table-ideas/    stage one: propose tables worth making
    table-build/    stage two: build one proposal, leave it offered for review
    lessons/        what a run met that the skill did not cover

Two jobs, not one loop:

    agents/propose-batch.sh   screen a family and put it in the queue
    agents/campaign.sh        work through what is waiting, item by item

and four kinds of work, which `agents/work.py` picks between:

    proposal   a screened family in the queue        -> build a new table
    demand     an `enhancement` issue, or a sentence -> critique file, repair
    growth     a table small for its subject         -> ask, then grow it
    sweep      a table nobody has ever read          -> critique, repair

They share one pipeline because they share one shape: a list of claims about
one table, and an agent that checks each claim and acts. `growth` and `sweep`
exist because nobody files an issue for them -- 126 hand-made tables had never
been read, and the median table built since T240 uses a tenth of the room it
is allowed.

The queue is the `proposal` issues in numberdb-data, one per family, each with
a checklist of its tables; `agents/queue.py` speaks it. A campaign tops the
queue up when it runs low and otherwise never stops to screen. Why it is there
and not in a file: `docs/design/where-ideas-live.md`.

Each stage is a fresh session, one batch at a time. The skill is the memory: if
a run cannot do the work from <https://numberdb.org/skill> alone, the skill is
incomplete, and a long session would hide that behind conversational memory
rather than fixing it. `docs/design/two-stage-tables.md` argues this out.

## Which engine runs which stage

Two harnesses run these prompts: Claude Code and the Codex CLI. Either can run
any stage, and the campaign takes one engine per *kind of work* rather than one
per campaign:

    NUMBERDB_WRITER   builds and repairs
    NUMBERDB_CRITIC   reads the finished table and triages a failed run
    NUMBERDB_MINER    proposes the batch
    NUMBERDB_AGENT    what any of the three falls back to (default: claude)

So the four pairings are two variables:

    agents/campaign.sh                                   # claude throughout
    NUMBERDB_WRITER=codex agents/campaign.sh             # codex writes, claude reads
    NUMBERDB_CRITIC=codex agents/campaign.sh             # claude writes, codex reads
    NUMBERDB_AGENT=codex agents/campaign.sh              # codex throughout

The immediate reason is a weekly quota: when one vendor's is spent the campaign
should carry on rather than stop. The better reason is that a critique is worth
more from a reader that did not write the table, and that is truer still when
it is not the same model -- which of the four is actually best is a question
this makes askable, and the answer is in `agents/runs/COSTS.tsv` and in what
the critiques catch.

**Codex is told its model and effort** rather than taking them from
`~/.codex/config.toml`, so a run is reproducible and the ledger records what
answered: `NUMBERDB_CODEX_MODEL` (default `gpt-5.5`) and
`NUMBERDB_CODEX_EFFORT` (default `xhigh`). It runs under `workspace-write`
with the network open, which is the nearest thing codex has to the deny list
the claude branch carries; the guards that actually hold are elsewhere anyway
-- `scripts/ship.sh` refuses an agent run whatever started it, and zeta3
cannot publish from any harness.

**What every row says, whichever engine wrote it: a cost in USD.** Tokens do
not compare -- a cached input token on Fable 5.1 costs a fortieth of a fresh
one, the two harnesses cache differently, and one counts a whole `exec` as a
turn where the other counts a message. So `agents/ledger.py` prices every run
at list API rates from `agents/model-rates.tsv`, and `agents/spend.py` adds it
up by engine, model, stage or day. Claude reports its own `costUSD` per model
at list basis and that is what is used; the rate table reproduces it to the
cent on a real build, and exists for the engine that reports no price at all.

    python3 agents/spend.py --since 20260906

**What the ledger can say about each.** Claude reports a cost in dollars and
the model that answered; codex reports neither, but prints `turn.completed`
with token counts, so its rows carry the model it was told to use and the
tokens it spent, and leave the cost column empty rather than inventing a rate.

**The `turns` column does not mean the same thing on both.** Claude counts one
per assistant message -- a build is 84 of them. Codex counts one per `exec`,
so a critique that made 119 tool calls is recorded as 1. Compare tokens across
engines, not turns.

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
