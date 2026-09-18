# What made this revision, and which version of it

`docs/design/ai-provenance.md` settled *who answers* for a table: the account
whose key published it, with the tool disclosed in `produced_by`. This note
settles the question that one left open -- **what ran, exactly** -- because the
answer turned out to be unrecoverable in practice.

## What the record said before this

Every revision in the database, grouped by how it described itself:

    268  data-repository history   bmatschke   21-01-14..23-03-01
    265  api  assisted by codex-cli            zeta3   26-09-07..26-09-18
    237  rigour-audit              bmatschke   26-08-13..26-08-17
    121  api  api                              bmatschke   26-09-10..26-09-18
     87  api  assisted by Claude Opus 5        bmatschke
     76  api  codex-cli                        zeta3
     43  api  assisted by codex                zeta3
     42  api  assisted by claude-opus-5        bmatschke
     37  api  assisted by an assistant         bmatschke
     ... 60 more shapes, most of them one revision each

Four faults, and each of them loses something different:

1. **Eight spellings of one fact.** `assisted by codex-cli`, `codex-cli`,
   `codex`, `codex-gpt-5`, `assisted by codex`, `codex-cli table-build`,
   `zeta3 table build script`, `assisted by an assistant`. Nothing can be
   counted, grouped or filtered.
2. **No version of anything.** A table built on 2026-08-30 and one built on
   2026-09-17 say the same words, though the prompt that steered them changed
   33 times in between. "Rebuild it the way T219 was built" was not answerable.
3. **The run id joins to nothing.** `TableRevision.run` is set only by package
   publishes and holds `ChernSimonsKnotComplements-1789`, while the cost ledger
   keys on the run stamp `20260918T072306Z`. The two records of the same event
   could not be put side by side -- which is also why 36 runs and $174 of
   spend sit unattributed to any table.
4. **A person's own assistance went unrecorded.** An interactive session --
   Claude Code or Codex CLI with somebody typing -- wrote `api`, the same as a
   hand-typed curl. By the disclosure rule in `ai-provenance.md` those edits
   *should* disclose: the assistant chose conventions, ranges and wording.

## The shape of the fix

**One row per run, and revisions point at it.** `AgentRun` holds what ran;
`TableRevision.agent_run` is a foreign key to it. `produced_by` stays as the
one-line rendering, because the blame view, the history, the file history and
the review queue already show it and a reader wants a sentence, not a join.

A run is not only a machine's: an interactive session is a run too, with a
model, a session id and a person at the keyboard. Making it the same object is
what lets one question -- "what made this?" -- have one answer everywhere:

| what happened | author | AgentRun |
|---|---|---|
| campaign stage on the builder | `zeta3` | pipeline `table-build`, engine `codex`, model, prompt version, campaign |
| Claude Code session, person typing | `bmatschke` | pipeline `interactive`, engine `claude-code`, model, session |
| person edits the web form | the person | none |
| person's own script through the API | the person | pipeline `script`, named by them |
| an old hand edit in numberdb-data | `bmatschke` | pipeline `data-repository`, with the commit |

## Versioning: the manifest is the scope

A digest of *what* -- that is the question the scope answers, and it cannot be
answered globally, because the pipelines differ: the one that builds a table
from a proposal is not the one that will build a tag's table, and neither is
the critique-and-repair loop. So **each pipeline declares its own scope**, in a
manifest that lives beside it and is versioned with it:

    # agents/pipelines/table-build.yaml
    name: table-build
    major: 2
    files:
      - agents/table-build/PROMPT.md
      - agents/table-build/check.py
      - agents/run.sh
      - agents/queue.py
      - agents/work.py
      - .claude/skills/numberdb-table/SKILL.md

The recorded label is

    table-build@2.7+9f3ac1d2

  * **name** -- which pipeline. Short, and the same string as the directory.
  * **major** -- declared by hand in the manifest, bumped when the *shape*
    changes: a new stage, a different way of choosing work. "One pipeline, four
    sources of work" was such a change; a reworded paragraph is not.
  * **minor** -- not declared. It is the position of this digest among the
    distinct digests that manifest has had, in commit order, computed from git
    by `agents/pipeline.py`. A number nobody types cannot drift from the truth.
  * **digest** -- sha256 over `(path, contents)` for the manifest's files, in
    manifest order, first eight hex digits. This is the authority; the version
    is a name for it.

Three properties follow, and they are the reason for the arrangement:

  * the scope is **auditable**, because it is a file in the repository rather
    than a convention in somebody's head;
  * the label is **checkable** -- a recorded digest that does not match the
    version's digest is a detectable lie, so the label is a claim the machine
    can test;
  * the history is **reconstructible**: walking the commits that touch a
    manifest's files gives every version that ever existed, including the ones
    that existed before this note was written.

**A campaign runs from pushed commits only.** A version that names
`agents@d3fce7a` is provenance only if somebody else can resolve it, and when
this was written the builder was 383 commits ahead of origin: every sha it had
recorded named a commit that existed on one disk. `run.sh` now refuses to start
when `HEAD` is not on the remote.

## Backfilling: three sources, and honesty about which

The record is worth having for the past too, and the material exists.
`AgentRun.source` says where each row came from, and it is never guessed
silently:

  * **`run`** -- written by the run itself, first-hand. Everything from now on.
  * **`ledger`** -- reconstructed from `agents/runs/COSTS.tsv`, which carries
    the run stamp, stage, engine, model, prompt version, harness session,
    campaign, batch, turns, tokens and cost per model. 579 runs across two
    machines, 2026-08-30 to now, of which 292 name their table outright.
  * **`inferred`** -- reconstructed from the revision itself: its `produced_by`
    string, its timestamp and its author, matched against the ledger by table
    and time window. Weaker, and labelled so.

The hand-made past is a fourth case and a different kind of record: 268
revisions from 2021-01-14 to 2023-03-01 are one person editing YAML in
numberdb-data when that repository was the source of truth. Their messages
already name the commit -- *"from the data repository, fc072a35"* -- so they
get an `AgentRun` with pipeline `data-repository`, no model, and the commit as
the version. Not because a person is a pipeline, but because "what made this"
should answer for every revision in the table, and the answer there is *a
person, by hand, at that commit*.

## What a submitter may declare

Through the API, on any write:

    X-Run-Id:      20260918T072306Z      the run this belongs to
    X-Pipeline:    table-build@2.7+9f3ac1d2
    X-Engine:      codex-cli             or claude-code, or a script's name
    X-Model:       gpt-5.5
    X-Session:     01a0b365-...          the harness session, when there is one

All optional; a write that declares none is a person at a keyboard, which is
what the absence honestly means. None of it is verifiable, exactly as
`rigour: heuristic` is not verifiable -- the machine checks what it can (a
digest against its version) and the rest is stated, attributed and revisable.
