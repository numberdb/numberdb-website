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
