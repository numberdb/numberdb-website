# Design: a schema for tables

Status: proposed
Measured against all 107 resolved tables and the code that renders them,
August 2026.

## Why not a different format

The question that prompted this was whether YAML should be replaced. Three
complaints get attributed to it, and only one of them is really about the
format:

**The `INPUT{}` macros.** Every one of the 107 tables contains at least
`ID: INPUT{id.yaml}`, and thirty put their numbers in a sibling file. That is a
property of storing one table across several files in a git repository, not of
YAML, and it disappears the moment the document is resolved. JSON split across
files would need exactly the same macro.

**The schema's looseness.** Real, and documented below. But JSON, TOML and
anything else would permit the same shapes: what constrains a document is a
schema, not a syntax.

**A 250 KB text box is a poor way to edit 1124 numbers.** True, and the largest
resolved document is 252 KB. This is a fact about the *editing surface* rather
than the format: the answer is a grid for entries and forms for metadata, with
the source as an escape hatch, which is what `user-editing.md` already
proposes.

What YAML earns: 45832 values are already written in it, it diffs legibly line
by line, and a mathematician can read a table file without tooling. Keep it as
the stored and exported form, add the schema below, and put a better editor in
front of it.

## What is actually there

Across the 107 resolved documents.

**The entries section** is `Numbers`, or `Data` in the ten polynomial tables
before normalisation. It is a mapping in 95 tables and a list in 11 (a table
with no parameters, such as `Pi`, is just a list of values).

**Parameters nest one level each**, to a depth of three:

| depth | values |
|---|---|
| 0 (no parameter) | 12 |
| 1 | 19061 |
| 2 | 31463 |
| 3 | 3962 |

**A parameter key holds one value or several.** 54491 keys are a single value;
9738 carry a comma-separated group such as `64, 296`, which `Display
properties: group parameters` explains. Note the space: the stored anchor is
`64,296`, and code that compares the two must normalise, or it silently matches
nothing.

**An entry is a string, a list of strings, or a mapping.** 54300 are a plain
string; 198 are a list, meaning several numbers share one parameter value.

**The mapping form uses nine keys**, in twelve combinations:

| key | uses | what it is |
|---|---|---|
| `number` | 11516 | the value |
| `comment` | 9334 | prose about this entry |
| `param-latex` | 2424 | how to print the parameter |
| `numbers` | 321 | **a container of further entries**, not a value |
| `equals` | 108 | this entry is the same number as another, by reference |
| `proof` | 30 | a citation for the `equals` |
| `both signs` | 25 | both signs of these values occur |
| `url` | 25 | a link for the entry |
| `comments` | 1 | a typo for `comment` |

Two of those deserve emphasis, because both have already caused bugs:

`numbers` is a **container**, sitting beside metadata like `param-latex`, and
the entries inside it are at the same parameter depth as their siblings. Code
that treats a mapping containing `numbers` as terminal collapses three tables
from five hundred entries each to two.

`comments` occurs exactly once, in T91, beside a `number` and a `param-latex`.
It is a typo. It renders anyway, because of the rule below.

## The rule that already makes this extensible

The renderer divides an entry mapping in two. A fixed set of keys is
*structural* -- `number`, `numbers`, `datum`, `data`, `equals`, `polynomial`,
`polynomials` -- and directs the walk. **Everything else is displayed as
information about the entry**, with no list of permitted names anywhere.

That is why `proof`, `both signs`, `url` and even the misspelt `comments` all
work without the renderer knowing about them. The format already has an open
extension point, and it has been used four times without anybody designing it.

A schema should keep that property rather than close it, because the corpus is
mathematics: the next table will want to say something no existing table says,
and a schema that has to be amended before a number can be recorded will be
worked around instead.

## The proposal

**Structural keys are closed.** A document may use `number`, `numbers`,
`equals` and the parameter nesting, and nothing else may change how the
document is walked. New structure is a schema change, deliberately, because it
changes what every reader must implement.

**Annotation keys are open.** Any other key on an entry is prose about that
entry, rendered as such. The schema declares the ones in use -- `comment`,
`param-latex`, `proof`, `url`, `both signs` -- so a form can offer them and a
validator can spell-check against them, and it *warns* rather than *rejects*
on an unknown one. `comments` should produce "did you mean comment?" and still
render.

**Retire the aliases.** `datum`, `data`, `polynomial` and `polynomials` appear
in the renderer's structural set and are used **zero** times across all 107
resolved tables; only `number` (11516), `numbers` (321) and `equals` (108) are. `Data` as the section name
was normalised to `Numbers` in August 2026. Dead alternatives are the cheapest
kind of complexity to remove and the most expensive to keep, because every
future reader must implement all of them.

**Values stay strings.** All 54300 are strings today and must remain so: `3.14`
read as a float is a different number from `3.14` read as text, and
`complete: no` read as YAML 1.1 is a boolean rather than the word. Every reader
in this codebase already uses `BaseLoader`; the schema should say `type:
string` and mean it.

**The identifier is not part of the document.** `ID` was filled in by a macro
pointing at a file whose first line says "Do NOT edit". It belongs to the
table, is allocated on creation, and is neither shown nor accepted from an
editor.


## Addressing a single value

A value's address was `/Best_Sobolev_constant#6,18/11,9/4`. A fragment is never
sent to the server, by the definition of HTTP, so nothing could render one
entry, confirm that it exists, or tell a reader that a citation had gone stale:
the page loaded and the browser scrolled nowhere. For a database whose worth is
that a number has a permanent address, silence is the wrong way to fail.

It now also travels in the query string, which the server does see:

    /T92?entry=6,18/11,9/4     resolvable, validated, citable
    /T92#6,18/11,9/4           kept, so the browser still scrolls

The query string rather than a path segment because 6736 of the identities
contain a "/" -- the parameters are rationals such as 18/11 -- and a
percent-encoded slash inside a path segment is rewritten or rejected by a good
deal of software between here and the reader. Identities are short: the longest
in the corpus is 22 characters.

Canonical on the `T`-number, which is permanent, rather than the slug, which is
not. An entry that no longer exists now says so and still shows the table,
rather than leaving the reader to wonder whether they misread the citation.

## Why the identity has to carry the parameter names

An entry's identity is its parameter values joined by commas, in the order they
nest: `37,48,-216`. Nothing in that says which value is which.

Reordering the `Parameters` declaration is harmless, because the identity
follows the data's nesting rather than the declaration. Restructuring the
nesting is not. With parameters `a` and `b` nested one way, entry `1,2` is
(a=1, b=2); nested the other way, `1,2` still exists and is (a=2, b=1).

    before : {'1,2': value-for-a1-b2, '2,1': value-for-a2-b1}
    after  : {'2,1': value-for-a1-b2, '1,2': value-for-a2-b1}

So the citation does not break. It resolves, reports success, and points at a
different number. That is worse than breaking, and no amount of validation
catches it, because there is nothing invalid to catch.

`a=1,b=2` cannot be confused with `a=2,b=1`. So the named form is the one to
write down, and `?entry=` accepts it now -- in any order, which is the point --
while continuing to accept the positional form, since everything written before
today is in it. An unknown parameter name is refused rather than guessed at.

This is the same argument that decided named records above, arrived at from the
other end: an identity that depends on position is only as stable as the
ordering nobody promised to keep.

## Grouped parameters make a display property load-bearing

Eleven tables declare `Display properties: group parameters`, for instance
`[['N'], ['c4', 'c6']]`, and their entries nest like this:

    Numbers:
      '389':
        '112, -856': ...

One key holds two parameter values. Nothing in the entries says so: the only
way to know that `112, -856` is `c4 = 112, c6 = -856` rather than a single
parameter whose value contains a comma is to read the display properties. A
property that says how a table should *look* decides how its entries are
*parsed*, which means a reader that ignores presentation gets the structure
wrong.

It also explains a bug found earlier: the key is written `112, -856` with a
space and the identity is `112,-856` without one, so anything comparing the two
has to normalise, and the review gate that did not silently matched nothing
across exactly these tables.

Flattening with named parameters removes this entirely:

    - params: {N: 389, c4: 112, c6: -856}

Every parameter is named where it is used, nothing has to be split, and
grouping goes back to being what it claims to be: a statement about how to
arrange the columns. That is a second, independent argument for the named form,
and it is the reason grouping should not survive into the schema as anything
structural.

## The parameter list is fixed once a table exists

Every entry's identity is its parameter values, so changing the set or the order
of parameters reassigns every identity in the table at once. Nothing breaks
visibly: the anchors still resolve, the cross-references still resolve, the
search results still resolve, and they all point at different numbers.

So an ordinary edit may not do it. `commit_table` refuses, names both lists,
and writes nothing; the editor explains why rather than showing a failure. A
table that genuinely needs different parameters is not stuck -- the refusal can
be overridden deliberately -- but it is an operation, not an edit, and one that
should eventually rewrite the identities and leave redirects behind.

Renaming a parameter is not refused, because the identity is built from the
values rather than the names. It does invalidate citations written in the named
form, which is a smaller and more visible loss: those fail rather than lie.

**98 cross-references name an entry**, across 22 targets, mostly
`Rational_multiples_of_pi` (50) and `Factorial` (30), with five pointing inside
their own table. They were plain fragments, so they had the same defect, and
they are data rather than markup: they are rewritten to the resolvable form as
they render, so no migration of the corpus is needed for them to become
checkable.

## Decisions taken here

**Entries become flat records, with parameters named.** Decided.

    Numbers:
    - params: {p: 2, s: -50}
      number: '2^-1 * 18438155738610754'
      comment: ...

The argument is not flexibility, it is that the nested form is *ambiguous*:
"is this mapping another parameter level, or is it the entry?" is a question
the code answers by sniffing for key names, and getting it wrong has already
produced two bugs in this work -- three tables collapsed from five hundred
entries to two, and a review gate that matched nothing across ten tables. A
record has no such question.

Measured on the corpus: 55493 entries, 7.4 MB nested, 8.6 MB flat with
positional parameters (+16%), 9.0 MB with named ones (+22%).

Named rather than positional, for the extra 6%: it survives somebody reordering
the `Parameters` section, it reads without cross-referencing another part of the
document, and it hands a grid its column headers directly. Positional records
stay correct until the day the parameter list is edited.

One thing the flattening must not lose: a `numbers` container currently lets a
group of entries share metadata, `param-latex` for the whole group. Flattened,
that either repeats on every record or moves up into `Parameters`, where it
arguably belongs, being a property of the parameter rather than of each value.

**Whether `both signs` should be structural.** It is an assertion about the
values rather than prose about them: it says the negatives are there too. No
code reads it -- a search of the whole codebase finds it only in the data --
so today it renders as a note and means nothing to search.

Whether that loses anything is not yet established, and worth checking before
deciding. T4 carries the flag and also stores 1075 rows of which 450 are
negative, so at least some negatives are written out explicitly rather than
implied. If it turns out the flag stands in for values that are *not* stored,
those numbers are unfindable by search and the flag has to become structural,
moving into the closed set. If the negatives are always written out, the flag
is documentation and belongs where it is.

## How big a table may be

Implemented in `numberdb_app/limits.py`, August 2026.

A table is a reference, not a dump. A number found among a million
machine-generated values says nothing about itself, because so does every other
real number in the same equally-spaced grid; one found among forty-five thousand
curated values at a hundred digits is an identification. The limits exist to
protect that, not to save disk, which is why they are editorial and why they
can be argued with.

**Two levels, because one number cannot do both jobs.** The house style is 1000
entries and 100 digits, and enforcing exactly that would flag 26 and 31 of the
107 tables respectively -- every one of them deliberate. A threshold that fires
on a quarter of the corpus teaches everybody to click past it. So the house
style stays advice, and what is enforced sits where the tail actually begins:

| | recommended | needs a reason | refused |
|---|---|---|---|
| entries | 1000 | 1200 | 50000 |
| digits in a value | 100 | 500 | 10000 |
| entries block | -- | 256 KB | 4 MB |

1024 entries and 128 digits are both natural things to reach for -- a table
parametrised in powers of two, a precision chosen to match a machine format --
and both pass with nothing to explain. That gap is the point of having two
levels rather than one.

**Why a hundred digits is the recommendation.** Not storage: digits that are
cheap to compute carry no information. Anybody who wants the thousandth digit of
a value that evaluates in a second can have it, and writing it here adds nothing
a reader could not produce. A hundred is far more than enough to identify a
number, which is what this database is for. Extra digits earn their place when
they were expensive to obtain, and that is exactly what a table is asked to say
when it goes over.

**The third limit is the balance between the first two.** Few numbers known
deeply is as legitimate as many numbers known to a hundred digits; both at once
is not. 1000 entries at 100 digits is about 100 KB, 200 entries at 1000 digits
about 200 KB, and both together a megabyte. 256 KB admits either and refuses the
pair. Nothing in the corpus exceeds it: the largest block is 236 KB.

**Completeness exempts the entry count, with no reason required.** Truncating a
complete table does not make it smaller, it makes it wrong, and a reader told a
table is complete who finds it cut off at a round number has been misled about
the mathematics. Six tables claim completeness today. It does not exempt the
digits or the block, because which rows exist is mathematics while how much is
written per row is a choice.

**Exact types are exempt from the digit limit entirely.** T96 writes 54342
digits in a single entry. Those are the coefficients of a modular polynomial for
the j-invariant, and writing fewer would not round the value, it would produce a
different polynomial. `Z`, `Q`, `Z[]` and `Q[]` therefore skip the digit check;
`R`, `C` and `Qp` do not, a p-adic having a precision like anything else.

What still governs an exact table is the block limit, and it does the editorial
work by itself. A very long polynomial is usually not interesting enough to
record, which is why T96 holds twelve of them and not two hundred; at 129 KB it
has room for one or two more before the next one has to argue for its size. That
is a better rule than "polynomials must be short", because it lets a table grow
freely while its entries are small and pushes back precisely when they are not.

**Hard limits are a different kind of statement.** A soft limit is a judgement
about what makes a good table and can be overridden by somebody who explains
themselves. A hard limit is not a judgement: it is where a paste went wrong, or
where the editor and the diff stop working, and no reason makes that workable. A
table that large wants to be several tables, or a program.

**Machine writers do not get the warning, they get the refusal.** A person over a
soft limit is told and their edit is saved, because they have judgement to
exercise and the review queue is where reasons get weighed. The API and bulk
proposals pass `strict=True`, which refuses an unexplained breach instead: a
warning shown to nobody is not a limit, and a script has no judgement to
exercise. This is the main thing standing between programmatic editing and a
corpus full of unconsidered rows.

## How a complex value is written

`a + i * b`, with the `i` before the digits. All 1847 complex values in the
corpus are written this way; Sage's own `b*I` appears in none of them.

The order is the substantive part. An imaginary part can run to a hundred
digits or more, so anywhere a value is shown abbreviated -- a search result, a
table cell, a wrapped line -- a reader sees its beginning and not its end. With
`i` in front, the beginning says which part this is. Written `b*I`, the marker
is the one character guaranteed to be cut off, and a long real part and a long
imaginary part become indistinguishable.

A negative imaginary part keeps its sign in `b`: `2 + i * -1`, never
`2 - i * 1`. The separator is therefore always `+`, and nothing has to be read
twice to establish what is being subtracted. There is no `- i * ` anywhere in
the corpus.

Worth stating because the derived column in the database holds Sage's spelling,
so anybody checking the convention against `NumberComplex.exact_text` rather
than against the documents will conclude the opposite -- as happened while this
was being written.

## A parameter whose values are names

25 tables have entry identities that are not numbers, and the split matters:

| kind | tables | examples |
|---|---|---|
| values select which quantity is meant | 15 | `a_n` vs `a_n/n!` (T15, T33); `phi` vs `phi_inv` (T32); `unit-R`, `unit-r`, `unit-s` (T17); `S`, `eps`, `1/eps` (T41); `c4`, `c6` (T87) |
| values are names from a finite set | 8 | `Co1`, `M11` (sporadic groups, T77); `Z2xZ2` (torsion subgroups, T91); `cube`, `icosahedron` (T85/T86); `koch-curve` (T100); `m_W`, `m_Z` (T76) |
| values are free symbols | 2 | `a`, `b` for α and β (T105, T106) |

The schema already has a name for the first two: `type: Symbolic`, declared 27
times. So this is not a gap to fill with a new type, it is an existing type left
under-specified -- `Symbolic` says only "not a number", and a reader cannot tell
`Co1` (a member of a fixed list) from `a_n/n!` (a normalisation of the entry
above) from `a` (a free variable standing for infinitely many values).

The proposal is to make `Symbolic` carry its values:

    Parameters:
      G:
        type: Symbolic
        values: [M11, M12, Co1, Co2, Co3, B, ...]

An enumeration is checkable, gives a grid its dropdown, gives search something
to match, and turns a typo into an error instead of a new entry. Where the
values genuinely cannot be listed -- the free symbols of T105 and T106 -- that
should be said outright rather than inferred from the absence of a list.

**One wart to fix while here.** T63 has identities like `26.212618669873*`: a
merit value with a marker glued to it. Whatever the star means, it is a footnote
living inside an identity, so it is part of every citation and every anchor, and
it will be there forever. It belongs on the entry as an annotation key.

## A row that is a family, not a number

T106 (Jacobi polynomials) is the case that shows what flattening is for. Its
parameters are (α, β, n) and its α keys are `a`, `-1/2`, `0`, `1/2`, `1`, `3/2`
-- a free symbol sitting in the same slot as numbers. Under `a/a` there is an
entry whose entire content is

    equals: HREF{Gegenbauer_polynomials}

with no value at all. The actual mathematics -- α=β gives the Gegenbauer
polynomials with parameter α+1/2 -- is stated in a prose comment, while T105
(Gegenbauer), T101 (Legendre) and T98/T99 (Chebyshev) all exist as their own
tables.

Flattening does not create a problem here, it surfaces one. Flattened, that row
is a record with parameters and no number, which is exactly the signal that it
does not belong in the entries block. There are **7** such rows in the whole
corpus, out of 55504, so this is a cleanup and not a migration.

**A family relation is a map between parameter spaces, not a pointer.** `equals`
points at one entry; it cannot express "for every α, this table's (α,α,n) is
that table's (α+1/2,n)", which covers infinitely many special cases. That wants
to be declared once at table level:

    Related tables:
    - table: T105
      when:  {alpha: t, beta: t}
      gives: {lambda: t + 1/2}
      proof: CITE{...}

One statement, in principle checkable by evaluating both sides at a few values,
and it frees the entries block to hold only values -- which is what makes the
flattened form unambiguous in the first place. The prose comments stay; they are
how a reader understands it, and this is how a machine does.

## Attachments: the code and files a table came with

85 of the 109 tables carry files the website has never shown: 82 `generate.sage`
scripts, plus `.txt`, `.new`, `.html` and three `.sobj`. 159 files, 1.2 MB, the
largest 477 KB. Four fifths of the corpus has provenance that no reader can see.

**Not a git repository.** Git's good idea is the content-addressed blob, and
`TableRevision` already has that. What git adds beyond it is a *repository*, and
that is where it stops fitting: our unit of change is one table and git's is the
whole tree, so a shared commit welds unrelated edits together and a
commit-per-table makes a repo lock that every editor contends for. It would also
reintroduce a second thing that could claim to be the truth, which is the
decision this whole design turns on. Efficiency is not the objection -- 11 MB of
data against an 11 MB `.git`, git would cope easily. Authority is.

**A manifest per revision, complete rather than incremental.** Each revision
names the full set of `{filename: blob digest}`, exactly as `content` is a whole
snapshot rather than a diff. Then "which `generate.sage` does this revision
mean?" is answered by reading that revision alone. The alternative -- walking
back through parents for the most recent version of a name -- is ambiguous
precisely where it matters, because a merge has two parents and "the latest in
the non-future history" is not single-valued across them.

Blobs are shared by digest, so an unchanged 477 KB `.sobj` across fifty
revisions costs 477 KB once, and an older revision's attachments stay reachable
for as long as the revision does. `?rev=` gives a permanently citable address
for the exact file that produced the numbers.

Merging manifests reuses `merge.py` unchanged: both sides touched a name, that
is a conflict; one side did, take it; a name deleted on one side and modified on
the other is a conflict, as everywhere else.

**Code is shown, payload is not diffed.** The `.sage` files are source and want
highlighting and diffs. The `.sobj` files are computed binary and want a
download link and nothing else; a diff view that tries to render a pickle is a
bug waiting to happen.

**Nothing is executed.** Displaying `generate.sage` is safe, running it is
arbitrary code execution, and several of the existing scripts run for hours or
days regardless. The evaluator sandbox exists for short expressions and is not
the same feature.
