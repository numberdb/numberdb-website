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
