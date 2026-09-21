# T1, "One": can it grow?

Read on 2026-09-21 as a growth review. 1 entry; `T1/table.yaml` is 716 bytes as
`/bundle/T1` serves it (the brief's 688 is the same table measured another way
and nothing turns on the difference) — 0.08% of the 1200-entry soft limit,
0.2% of the 320 KB block limit. The question asked was whether the range is the
whole of what the definition promises, or whether the table was stopped early.

**Answer: it is complete, and it is the case the brief names — a table of one
number that is finished. No entry should be added, and no generator should be
written.** The definition is

> The neutral element of multiplication in the ring of integers.

and a monoid has exactly one neutral element: if $e$ and $e'$ both are one then
$e = ee' = e'$. That is a proof rather than a judgement, so the family has one
member, the table holds it, and there is nothing further to enumerate. Three
structural facts say the same thing independently: the table has **no
parameter** at all (`Parameters: ''`, and the single entry is `params: {}`), so
there is no axis to run along; it carries **no generator and no files**; and
its value is **exact**, so the other axis a one-entry table can grow on —
precision — is closed too (§2, §3).

**The one thing worth doing is a single line: `complete` is absent.** The page
says nothing at all about whether one entry is all there is, which is precisely
why this table arrived in a growth queue. Five of the corpus's twelve one-entry
tables declare `complete: yes`, and T8 ("Euler's constant e") carries the
sentence T1 wants verbatim (§4).

One real defect turned up that is not about growth and that the audit does not
see: the definition's link aims at a **row** where the sentence means a
**ring** — `HREF{Integers#1}` under the words "the ring of integers", so a
reader who clicks lands on the row holding 1, the thing they came from (§6).

## 1. How I read it

- **Rendered page:** `curl https://numberdb.org/T1` — **direct, no proxy.**
  Nothing listens on `127.0.0.1:1080` on this runner and `ALL_PROXY` is empty;
  `--socks5-hostname 127.0.0.1:1080` answers exit 7 for every URL, direct HTTPS
  answers 200. `docs/agent-environment.md:1117–1134` records this and counts
  the earlier occurrences, so I have not added another copy. The page sets
  cleanly: no `Math input error`, no eaten `<`, no `argument ()`, no
  `Parameters` block (right, there are none), and the value column is headed
  with the site's default `Number` rather than the fallback word `value`.
- **Document:** `/bundle/T1`, which is the stored YAML, cross-checked against
  `GET /api/table?id=T1`. They agree.
- **Generator:** `/files/T1` — "This table carries no files." The bundle is
  `T1/table.yaml` and `T1/README.txt` and nothing else. §3.
- **Provenance:** `/revisions/T1`. Created 2021-01-14 by bmatschke from the
  data repository, touched again in 2021 twice, then the 2026-08-09 import and
  flattening and the 2026-08-14 rigour migration, whose diff is the whole of
  `rigour details`. **The entry has never changed and there has never been more
  than one.** This table was not stopped early; it was never a range.
- **Audit:** `GET /api/table/T1/audit`. One finding. §6.
- **Search behaviour:** `/api/lookup`, against the live corpus. §5.
- **The corpus around it:** the `/tables?sort_by=entry_count` listing for the
  twelve one-entry tables, then `/api/table?id=…` for each. §4.
- **No Sage was needed,** and running any would have been measuring the wrong
  thing: the entry is the integer 1 and the question is editorial.
- The anonymous API allowance (60 requests an hour) ran out partway through the
  survey above; `X-API-Key` raises it. Both facts are already in
  `agents/lessons/PROPOSALS.md:322–341` and `docs/agent-environment.md:3703`,
  so I have not written them down again.

## 2. The definition names one object, and four ways to grow it all fail

Somebody looking for growth has four places to reach. I worked through each so
the next reader does not have to.

**Other rings.** "The neutral element of multiplication in the ring $R$" for
other $R$ is a family with an index, which is the shape the skill blesses —
"where the members share an index, one table however few". It fails on the
values: every row would read `1`. That is the skill's "counting rather than
choosing" in its purest form, and it is also the small-integer warning —
rows that match everything and identify nothing. It would also need the
definition rewritten away from "the ring of integers", which makes it a
different table rather than more of this one.

**The units $\pm 1$.** A genuine two-member family (the unit group of
$\mathbb{Z}$), but not this definition: $-1$ is not a neutral element of
multiplication. It is already a row of T2, and a table holding 1 and $-1$ would
hold the two most-matched integers there are.

**A second convention.** This is the standard reason a constant table has two
or three rows rather than one, and the corpus uses it: Lévy's constant (T172)
holds $\beta$ and $e^\beta$, the golden ratio (T32) holds three, the
Glaisher-Kinkelin constant (T249) two. There is nothing for T1 to use it on. 1
has no second normalisation; every scaling of it anybody writes down is 1.

**Another type.** 1 as a $p$-adic, as the constant polynomial, as a complex
number. `type` is one value per table, so each of those is a different table,
and each meets the objection of the first paragraph.

None of these is a near miss. I record them because "how far could it go and by
what method" deserves an answer with reasons in it, and because the first one
looks like the blessed shape until you write down what the rows would say.

## 3. No parameter, no generator, no further value — three confirmations

- **No parameter.** `Parameters` is the empty string and the stored entry is
  `params: {}`. This is the cheapest test there is for the growth question and
  it is decisive: a table with no parameter has nothing to enumerate over. The
  contrast is one table away — T2 ("Integers") has parameter `n` of type `Z`
  and `complete: no`, and is the table in this neighbourhood that *could* grow,
  which its own growth review has already settled as a deliberate window of
  examples.
- **No generator.** No `generate.py`, and `/files/T1` says so.
- **`Programs` is a literal.** `numbers = [1]` is not an incantation that
  returns one more value; it is the value. On most tables that would be a
  finding. Here it is right, and it is evidence: there is no Sage call for "the
  next one" because there is no next one. (T5's growth review made the same
  argument from an *empty* `Programs`; T1 makes it from a trivial one.)

## 4. `complete` is absent, and the corpus has the wording four tables away — worth doing

`Data properties` holds `type`, `rigour` and `rigour details`, and no
`complete` and no `complete-note`. Across the twelve tables in the corpus with
exactly one entry:

    complete: yes    T5   Exponent of matrix multiplication complexity
                     T7   Pi
                     T8   Euler's constant e
                     T173 Lochs's constant
                     T189 Viswanath's constant
    (absent)         T0   Zero
                     T1   One
                     T37  Ramanujan's constant
                     T38  Hafner-Sarnak-McCurley constant
                     T39  Twin prime constant
                     T42  42
                     T43  Meissel-Mertens constant

The consequence is not cosmetic. A reader who lands on a one-entry table cannot
tell from the page whether one entry means "this is all there is" or "somebody
started and stopped", and neither can the next growth scan — which is how this
table came to be read today. T7 renders as

> Table is complete: yes (it holds the single number named by the definition;
> the scaled values $a\pi$ are held by rational multiples of $\pi$)

and T8's clause, which is the one T1 wants unchanged, is *it holds the single
number named by the definition*. So:

    complete: yes
    complete-note: it holds the single number named by the definition

At one entry this buys nothing mechanical — the exemption from the entry-count
limit that `numberdb_app/limits.py::claims_completeness` grants is not needed
by a table with one row — and that is the point: it is purely a sentence for a
reader, and the reader currently gets no sentence.

Two notes for whoever does it. The clause finishes the sentence "Table is
complete: …", so it is written as a clause and not a sentence. And the same
line is wanted on the other six tables in the list above: it is one sweep of
seven identical edits rather than seven decisions, and doing it for T1 alone
leaves the question open six more times.

## 5. The entry answers no search by number, and cannot — noting only

The value carries no not-findable dagger, so the site holds it to be
searchable, and it is: it is an exact integer of zero width, which
`search.py`'s scoring gives the maximum. It is nevertheless unreachable, for a
different reason.

The search box takes a **digit string**, not a value. Measured against the live
corpus:

    text=1      100 results, "We only show the first 100 results";
                five tables (T197 ×96, T61, T11, T93, T329); T1 in none of
                them, stable across three identical requests
    text=42     100 results; T42 is second
    text=1729   25 results; exact 1729 (T256) first, then 0.1728010…,
                1.1728741…, 8796.1729141…

The third line is what the grammar is: `1729` matched values at three different
exponents, so a query is a run of significant digits and not a number. `1` is
therefore a request for every stored value whose significant digits begin with
1 — tens of thousands of them. `search_real_numbers` takes its documented fast
path when more than a page of values lie inside the query ("the order within
that set is arbitrary, which is the deliberate trade"), so the 100 that come
back are 100 equally good answers chosen by nothing, and T1 is not among them.

This is the system working, and the fix is not in T1 — a search that promoted
the table called "One" above every other value beginning with 1 would be a
worse search. I report it under a growth brief because it closes the question
from the other end: **the number in this table cannot be arrived at, so adding
numbers like it could only make other searches worse.** What T1 is, is a
landing page for a name, and it works as one: `neutral element` returns T0 and
T1 as the first two tables, and `one` returns it seventh, behind five tables
about level one cusp forms — the title is one common English word, and the
`Keywords: neutral element` entry is what actually carries it. That is the
right design and it needs nothing.

## 6. The audit's one finding is right in form and should not be acted on as stated — and the real defect is underneath it

    Definition links to another table; a cross-reference belongs in
    Similar tables or a comment

The rule (`audit_table.py:433`) is a flat "no `HREF{` in `Definition`", and the
fault it is aimed at is real: a definition that has grown a relation clause is
one of the two faults the skill's section 4 opens with. **It cannot tell a
relation from a naming, and this is a naming.** The skill is explicit the other
way — "Link the first mention of a thing to what explains it. A table if the
corpus holds one" — and "the ring of integers" is the first and only mention of
an object this corpus holds, as T2. Removing the link would satisfy the audit
and disobey the skill, and would leave the shortest definition in the corpus
pointing at nothing. I would leave it.

What is wrong is the **target**, and the audit does not look at it. The
definition reads `HREF{Integers#1}[integers]`, so the link under the words "the
ring of integers" lands on `/Integers?entry=1` — the row holding the number 1,
which is the row the reader has just come from. The skill: "Link the number,
not the table, when the sentence means one number… Link the whole table when
the sentence means the whole family, which is the commoner case." The sentence
means the ring.

The same anchor is in `Similar tables`, where it is more clearly wrong, because
the relation recorded there is **"contained in"** — a statement about the
table, pointing at one of its rows.

Smallest change: `HREF{Integers}[integers]` in both places, dropping the `#1`.
Two characters each, and it is the same edit on T0, whose definition is the
same sentence with `#0`.

Worth saying that the corpus already states the stronger relation correctly and
in the right place: T2's rows for 0 and 1 carry `equals: Zero` and
`equals: One`, which render on `/Integers`, and that is the `equals` mechanism
the skill describes. Nothing in §6 is a gap in what the corpus knows; it is one
link aimed one level too deep.

## 7. Small things, noted only

- The stored definition has a double space, `ring of  HREF{…}`. HTML collapses
  it, so no reader sees it; only somebody editing the YAML does.
- `Tags: [integer]` drew no audit finding, so the tag reaches more than this
  table, which is what the rule asks. One tag where two is typical, but there
  is no second tag this table wants and inventing one would make a worse way
  through the corpus, not a better one.
- `rigour details` is the corpus's standard sentence for an exact table, which
  is right here and says nothing T1-specific, as it should not.

## 8. What I would do, in order

1. **§4** — `complete: yes` with the T8 clause. One line, and it stops this
   table being queued for a growth review again. The same line on T0, T37, T38,
   T39, T42, T43.
2. **§6** — `HREF{Integers}` in the definition and in `Similar tables`, dropping
   the `#1` anchor. The same on T0.
3. **Nothing else. Do not add an entry, and do not write a generator.**

**I changed nothing.** This is a report.
