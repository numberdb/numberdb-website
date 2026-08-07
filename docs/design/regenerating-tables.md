# Design: code that can recompute a table

Status: decided, largely unbuilt
August 2026

## The goal

For most tables there should be a program that can regenerate the entries, kept
as a reference for how the numbers were obtained. Not every table can have one
— some rest on measurements, on other databases, or on a computation nobody
will repeat — and that is fine, and worth saying explicitly rather than leaving
as an apparent gap. But a table whose numbers cannot be traced to anything is a
table a reader has to take on faith, and this database is for numbers that can
be checked.

82 tables already carry a `generate.sage`. They are the starting point, not the
finished thing.

## Why the current arrangement has to change

The scripts write files into the data repository:

| what | count |
|---|---|
| scripts writing `numbers.yaml` | 67 |
| scripts writing `polynomials.yaml` | 11 |
| scripts writing `table.yaml` | **0** |
| tables reading entries back through `INPUT{}` | 80 |
| tables with both a script and that macro | 78 |

So the split between `table.yaml` and `numbers.yaml` is not a convenience for
handling large files: it is the seam between the part a person writes and the
part a program writes. That arrangement worked when the repository was where
tables were decided. It does not survive the repository becoming a mirror,
because a script writing a file that the site then has to import is a second
way for data to get in, and the whole point of the move was to have one.

## The decision

**Scripts submit through the write API rather than writing files.** A
regeneration becomes a proposal like any other: attributed, rate-limited,
size-checked, landing in the review queue if its author has no track record,
and recorded as machine-produced so a reviewer can triage it.

This removes the seam honestly, rather than by inlining it and leaving 78
scripts writing files nothing reads. It also means the export can write one
self-contained file per table, which is what it already does.

**The shared machinery belongs in the `numberdb` package.** Every script
repeats the same handful of operations: turn a Sage real interval into the
string form the database stores, assemble entries under their parameters, write
the result out. Today that lives in `utils/utils.py` in the website repository
and is imported by scripts in the *data* repository, which is a dependency
pointing the wrong way. In the package it is installable, versioned, documented
and testable, and a contributor writing a new generator gets it with
`pip install numberdb`.

What the package should carry:

* the canonical string form for each kind of value, so two generators do not
  round the same number differently;
* a way to build entries as records with named parameters, which is the form
  the database now stores;
* submission, so a script ends with a call rather than with a file.

## Order of work

1. Write support in the package: submit and create, and the canonical value
   and entry types.
2. Rewrite the generators against it, table by table. They can be checked
   against the entries already stored: a generator that reproduces the table
   is demonstrably the code that made it.
3. Only then may the export drop the entries macro, since until a table's
   script is migrated the macro is still that script's output.

## The backlog item this creates

**Most tables should have a generator, and a table should say whether it has
one.** Three states worth distinguishing, because they mean different things to
a reader:

* a generator exists and reproduces the entries;
* a generator exists that needs data from elsewhere — a measurement, another
  database — so it documents the derivation without being self-contained;
* no generator, because the numbers came from somewhere that cannot be re-run.

The third is legitimate and should be recorded as a fact about the table rather
than left looking like an omission. The first is the one worth aiming at, and
worth checking: a generator that no longer reproduces its table has found
either a bug or a correction, and either way somebody should look.

## A new table must contain a number

Decided, August 2026.

Creating a table requires at least one entry — one is enough, more is fine. A
table with none is not a small table, it is a different kind of thing: a draft.

The workflow this settles is the one the generator interface implies. A person
writes the prose on the site — title, definition, parameters, references, tags
— and enters **one value by hand**; the program adds the rest. So the ordering
that makes sense (prose by a person, numbers by a program) survives, and the
step that worried us — "what if the script never runs?" — leaves a small, true,
publishable table rather than an empty shell holding a permanent identifier.

Public drafts are not allowed. A published draft carries a T-number, appears in
the listings and answers nothing, and is indistinguishable from a table
somebody abandoned.

## Open: do drafts share the T-number space?

Private drafts are wanted eventually. The question is whether a draft carries an
identifier of its own that becomes a T-number on publication, or whether there
is one permanent identifier from the moment anything is created.

**Recommendation: one permanent identifier, allocated at creation.** A draft is
then a table that is not published yet, and publishing changes a flag rather
than a name.

The argument is the workflow above. A generator carries the identifier of the
table it fills — `tid = 'T93'` — and it is written while the table is still
being set up. If publication renumbers, every such script has to be edited at
exactly the moment somebody is thinking about something else, and a script that
is not edited goes on writing to an identifier that no longer means what it did.
That is the class of failure this project keeps finding: not a crash, a quiet
wrong target.

What the separate-space argument buys is density — every T-number would name a
table that really was published, with no gaps left by abandoned drafts. That is
worth less than it sounds. Numbers are not scarce, a gap is an honest record
that something was started and not finished, and no citation is harmed by one.
Renumbering, by contrast, can only be got wrong.

The cost to accept: a T-number may exist privately for a while, so a citation
written early resolves to nothing until the table is published. That is the
same as citing a table that does not exist yet, and it becomes correct rather
than becoming wrong.

Nothing decided here is binding yet — with public drafts disallowed and an
entry required, drafts do not exist at all — so this can be settled when they
are built.


## Sending values as they are computed

A generator of expensive values must be able to send each as it is found. One
that computes everything first loses everything when it dies at entry 900, and
some of these tables take hours per entry.

Two things make that work without wrecking the history.

**Upsert.** Entries arriving are merged into the stored ones by identity, so a
submission of one entry leaves the other thousand alone. Replacing stays the
default: one means "here is the table", the other "here is another value", and
each is wrong as a default for the other.

**A run is one revision that grows.** Every revision holds the complete
document, so a revision per entry would be a thousand copies of a table that is
236 KB at its largest — 230 MB and a thousand one-line diffs for a single
regeneration. Submissions carrying the same run amend their revision instead:
content, digest and rows move on; date and position in the history stay.

### What the lock covers, and what it does not

Writes to one table are serialised, because two submissions adding *different*
entries are not in conflict and the document merge — which compares the entries
list whole — could not tell. Before the lock, one of them was refused; in the
variant where a request merged against one moment and passed a base from
another, the earlier entry was silently overwritten.

The lock covers the **write**, never a caller's computation. A generator that
spends three hours on one entry holds nothing during those hours; it takes the
lock only to store the result. What the deadline has to cover is one rebuild of
the table's rows:

| table | entries | one write |
|---|---|---|
| T62 | 723 | 1.8s |
| T69 | 1124 | 3.0s |
| T94 | 1135 | 2.5s |

`NUMBERDB_WRITE_LOCK_WAIT` is 15 seconds by default. Past it a writer is told
to come back rather than left holding a connection, and a run resending one
entry costs nothing.

### The cost that does scale

Each submission rebuilds the whole table's rows, so streaming N entries one at
a time costs O(N²): about 16 minutes of rebuild for a thousand entries, and
proportionally more for a table of long values.

For a generator that takes hours per entry this is noise. For a fast one it is
the dominant cost, and the answer today is `batch=` — send a hundred at a time
and pay a hundredth of it. The real fix is to rebuild only the rows that
changed, which is worth doing when a fast generator needs it and not before.


### Two runs on the same table at once

A run amends its own revision only while that revision is still the head. So if
two people generate into the same table at the same time, neither can amend:
their submissions interleave, and six of them become seven revisions.

Nothing about that is *wrong*. Every revision holds exactly what it held, and
an entry is attributed to whoever last changed it — checked with two
interleaved runs, where the odd entries come back as Alice's and the even ones
as the other author's. The "latest revision" always matches its own entries,
because attribution is per entry rather than per revision.

What breaks is readability, and the storage that goes with it: a thousand
entries each would be two thousand revisions, each holding the whole document.
Two mitigations, in order of how much they help:

* `batch=` — a run sending a hundred at a time makes interleaving rare and
  divides the revisions by a hundred. This is the answer for anything that is
  not genuinely hours per entry.
* the history groups a run into one line, positioned at its latest part, with
  the parts available underneath. Two acts read as two lines whether they
  produced two revisions or two thousand.

The storage cost is real and unmitigated in the worst case. Rebuilding only the
rows that changed, and storing a revision as a diff when it belongs to a run,
are both available if a table ever needs them; neither is worth building before
something does.
