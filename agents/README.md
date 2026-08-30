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
