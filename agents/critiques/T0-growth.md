# T0, "Zero": can it grow?

Read on 2026-09-21 as a growth review. 1 entry; `T0/table.yaml` is 661 bytes as
`/bundle/T0` serves it (the brief's 633 is the same table measured another way,
and nothing turns on the difference) — 0.08% of the 1200-entry soft limit, 0.2%
of the 320 KB block limit. The question asked was whether the range is the whole
of what the definition promises, or whether the table was stopped early.

**Answer: it is complete, and it is the case the brief names — a named constant
with one entry, finished. No entry should be added, and no generator should be
written.** The definition is

> The neutral element of addition in the ring of integers.

and a monoid has exactly one neutral element: if $z$ and $z'$ both are one then
$z = z + z' = z'$. That is a proof and not a judgement, so the family has one
member, the table holds it, and there is nothing to enumerate. Three structural
facts say the same independently: the table has **no parameter** (`Parameters:
''`, and the single entry is `params: {}`), so there is no axis to run along; it
carries **no generator and no files** (`/files/T0`: "This table carries no
files"; the bundle is `table.yaml` and `README.txt` and nothing else); and the
value is **exact**, so precision — the other axis a one-entry table can grow on
— is closed too.

**This table is T1's twin, and the repair that T1 got four hours ago was not
applied here.** T1 ("One") was read under the same brief this morning
(`agents/critiques/T1-growth.md`), and at 2026-09-21 21:25 zeta3 edited it,
comment "repair growth critique": it now carries `complete: yes` with the T8
clause, and its definition links `HREF{Integers}` with no anchor. T0 carries
neither change, and it was named in that critique's own list of what to sweep.
Both findings below are therefore already settled decisions with a worked
example one table away; nobody has to re-decide them.

| | T1, after 21:25 today | T0, now |
|---|---|---|
| `complete` | `yes` | absent |
| `complete-note` | it holds the single number named by the definition | absent |
| definition link | `HREF{Integers}[integers]` | `HREF{Integers#0}[integers]` |
| `Similar tables` | `HREF{Integers}[integers]` | `HREF{Integers#0}[integers]` |

## How I read it

- **Rendered page:** `curl https://numberdb.org/T0` — **direct, no proxy.**
  Nothing listens on `127.0.0.1:1080` on this runner and `ALL_PROXY` is empty;
  `--socks5-hostname 127.0.0.1:1080` answers exit 7 for every URL, direct HTTPS
  answers 200. `docs/agent-environment.md:1117–1134` records this and counts the
  earlier occurrences, so I have not added another copy. The page sets cleanly:
  no `Math input error`, no eaten `<`, no `argument ()`, no `Parameters` block
  (right — there are none), the value column's header cell is empty and the
  section is headed with the site's default `Number` rather than the fallback
  word `value`, and the entry renders as `0`.
- **Document:** `/bundle/T0`, the stored YAML, cross-checked against
  `GET /api/table?id=T0`. They agree.
- **Provenance:** `/revisions/T0`. Created 2021-01-14 by bmatschke from the data
  repository, touched twice more in 2021, then the 2026-08-09 import and
  flattening and the two 2026-08 rigour migrations, the last of which added the
  whole of `rigour details`. **The entry has never changed and there has never
  been more than one.** This table was not stopped early; it was never a range.
- **Audit:** `GET /api/table/T0/audit` with the key — there is no database on
  this runner, which is the fallback the brief names. One finding. §3.
- **Search behaviour:** `/api/lookup` against the live corpus, plus
  `numberdb_app/search.py`. §4, and it is where I had to correct myself.
- **The corpus around it:** `/api/table?id=…` for the ten one-entry tables named
  in the T1 review, to see which still lack `complete`. §2.
- **No Sage was needed.** The entry is the integer 0 and the question is
  editorial; a Sage run would have measured the wrong thing.

## 1. Four ways to grow it, and each fails on the values

The routes are the same four T1's review worked through, and they fail the same
way, so I state them briefly and add what is different for 0.

**Other rings.** "The neutral element of addition in the ring $R$" is a family
with an index, which is the shape the skill blesses — "where the members share
an index, one table however few". It fails on the values: **every row would read
`0`.** That is the skill's "counting rather than choosing" in its purest form,
and it would need the definition rewritten away from "the ring of integers",
which makes it a different table rather than more of this one.

**A second convention.** This is the usual reason a constant table has two or
three rows — Lévy's constant (T172) holds $\beta$ and $e^\beta$, the golden
ratio (T32) three. There is nothing here to use it on, and 0 is the strongest
case of that in the corpus: $a \cdot 0 = 0$ for every $a$, so there is no
companion table of scaled values to point at either. T7's `complete-note` names
`rational multiples of $\pi$` as where the near misses went; T0 has no near
misses to send anywhere, and its clause should be T8's shorter one unchanged.

**Another type.** 0 as a $p$-adic, as the zero polynomial, as a complex number.
`type` is one value per table, so each is a different table, and each meets the
objection of the first paragraph.

**Negative zero, or zero in other conventions.** There is no second $0$ in
$\mathbb{Z}$. (The nearest real thing, the signed zeros of floating point, is a
fact about a representation and not about a number.)

**One route T1 does not have, and it argues against growth rather than for
it.** 0 is not a rare value: it is a legitimate *entry* of many tables here.
`/api/lookup?text=0` returns a capped hundred exact zeros drawn from at least
twelve tables — T33 (19 of them), T36 (16), T27 (7), T15, T331, T28, T136,
T376, T29, T22, T134, T210. So any table of "zeros of things" that T0 could be
grown into would duplicate rows the corpus already holds in their proper
families, and would push those rows further down an already-capped result set.
The corpus's mechanism for the relation that does exist is already in place and
correct: T2's row for $n=0$ carries `equals: HREF{Zero}`.

## 2. `complete` is absent — the one thing worth doing, and it is one line

`Data properties` holds `type`, `rigour` and `rigour details`, and no `complete`
and no `complete-note`. The page therefore says nothing at all about whether one
entry is all there is, which is exactly why this table arrived in a growth
queue — a reader, and the next scan, cannot tell "this is all there is" from
"somebody started and stopped".

Read today, the one-entry tables stand at:

    complete: yes    T1   One                     (added 2026-09-21 21:25)
                     T5   Exponent of matrix multiplication complexity
                     T7   Pi
                     T8   Euler's constant e
                     T173 Lochs's constant
                     T189 Viswanath's constant
    (absent)         T0   Zero
                     T37  Ramanujan's constant
                     T38  Hafner-Sarnak-McCurley constant
                     T39  Twin prime constant
                     T42  42
                     T43  Meissel-Mertens constant

Smallest change, which is T8's and now T1's wording verbatim:

    complete: yes
    complete-note: it holds the single number named by the definition

Two notes for whoever does it. The clause finishes the rendered sentence "Table
is complete: …", so it is written as a clause and not a sentence. And at one
entry this buys nothing mechanical — the exemption from the entry-count limit
that `numberdb_app/limits.py::claims_completeness` grants is not needed by a
table with one row. That is the point: it is purely a sentence for a reader, and
the reader currently gets no sentence.

## 3. The audit's one finding is right in form and should not be acted on as stated — the real defect is underneath it

    Definition links to another table; a cross-reference belongs in
    Similar tables or a comment

The rule (`audit_table.py:433`) is a flat "no `HREF{` in `Definition`", and the
fault it aims at is real: a definition that has grown a relation clause is one
of the two faults the skill's section 4 opens with. **It cannot tell a relation
from a naming, and this is a naming.** The skill is explicit the other way —
"Link the first mention of a thing to what explains it. A table if the corpus
holds one" — and "the ring of integers" is the first and only mention of an
object this corpus holds, as T2. Removing the link would satisfy the audit and
disobey the skill. I would leave it, as the T1 repair did: T1's definition still
contains `HREF{`, and still draws this finding.

What is wrong is the **target**, and the audit does not look at it. The stored
text is `HREF{Integers#0}[integers]`, which renders as `href="Integers?entry=0"`
— so the link under the words "the ring of integers" lands on the row of T2
holding the number 0, which is the row the reader has just come from. The
skill: "Link the number, not the table, when the sentence means one number…
Link the whole table when the sentence means the whole family, which is the
commoner case." The sentence means the ring.

The same anchor sits in `Similar tables`, where it is more clearly wrong,
because the relation recorded there is **"contained in"** — a statement about
the whole table, pointing at one of its rows. And the other end of that same
relation is already stored correctly: T2's entry for $n=0$ reads
`equals: HREF{Zero}`, the table and no anchor.

Smallest change: `HREF{Integers}[integers]` in both places, dropping the `#0`.
Two characters each, and it is the edit already made on T1.

## 4. The reader arriving with the number: measured, and it is thinner than it first looks

I first read this as good news and it is not, so the correction is worth having
in writing.

    /api/lookup?text=0                100 results, capped; T0's own entry at
                                      rank 28; tables: [T0]
                                      stable across three identical requests
    /api/lookup?text=zero             0 results; 20 tables, T0 fourteenth,
                                      behind thirteen "Zeros of …" tables
    /api/lookup?text=neutral element  tables: T0, T1, T335, T338, T41, T118
    /api/lookup?text=zero element     tables: T0 first
    /api/lookup?text=additive identity   nothing at all

The `tables: [T0]` on the first line is **not** the name being found. A bare
integer is answered by `search_metadata`'s `_table_by_number`, which reads the
term as a table's own number and returns `T0` because this table is table zero
(`search.py:662–670`; confirmed — `text=376` returns only T376, `text=29` only
T29, `text=7` only Pi). It is a coincidence of numbering, it would answer the
same if the table held anything at all, and a contributor checking "is my number
searchable?" by typing it would be misled by it. §5 proposes that as a lesson.

What is left is honest and mostly fine. T0's own entry *does* appear among the
hundred number results, where T1's does not — "0" is the significant-digit
string of nothing but exact zeros, so the set it selects is small enough that
this table is inside it — but the placement is the documented arbitrary fast
path, so it is stable rather than earned, and I would not lean on it. The name
works: "zero element" lands T0 first, "neutral element" first of six. The
`Keywords` entry carrying that is doing real work, since "neutral element" is
not in the title.

**One gap, cheap to close: `additive identity` reaches nothing in the corpus.**
That is the commonest English name for what this table holds, and neither the
title, the keyword nor the definition contains either word. The skill's rule is
exactly this case — "If the title does not contain that word, put it in
`Keywords`, which is the same weight". Smallest change: add `additive identity`
to `Keywords` (and, by the same argument, `multiplicative identity` to T1).
Worth doing, and not urgent.

The other half — that a reader who arrives holding a plain `0` from a
calculation wants to know what they have — is a question T0 cannot answer and
should not try to: 0 is the value that matches everything, which is the skill's
small-integer warning, and it is one more reason not to grow this table.

## 5. For the lessons, and for the environment

- **Lesson proposed:** `agents/lessons/proposals/20260921T215138Z-critique.md`,
  on the table-number branch of the search box making a findability check a
  false positive. It is reachable by anybody with a laptop and a browser.
- **Nothing new for `docs/agent-environment.md`.** The dead SOCKS proxy and the
  working direct `curl` are already recorded there at lines 1117–1134, with a
  count of how often it has been rediscovered; I have not added a fifth copy.
- The lesson the T1 review proposed — a parameterless table needs `complete:
  yes`, and the skill explains `complete` only for a range that stops somewhere
  — is already filed at `agents/lessons/proposals/20260921T211050Z-critique.md`
  and T0 is the second table it fits. I have not re-proposed it; T0 is evidence
  for it, not a new case.

## 6. Small things, noted only

- The stored definition has a double space, `ring of  HREF{…}`, exactly as T1's
  did. HTML collapses it; only somebody editing the YAML sees it.
- `Programs` is `numbers = [0]`, a literal rather than an incantation for one
  more value. On most tables that is a finding. Here it is right, and it is
  evidence: there is no call for "the next one" because there is no next one.
- `Tags: [integer]`, one where two is typical. It drew no audit finding, so the
  tag reaches more than this table, which is what the rule asks. T2 next door
  carries `ring` and `Abelian group`; neither is true of a number, and inventing
  a tag to make two would make a worse way through the corpus.
- `rigour details` is the corpus's standard sentence for an exact table, which
  is right here and says nothing T0-specific, as it should not.

## 7. What I would do, in order

1. **§2** — `complete: yes` with the T8 clause. One line, it stops this table
   being queued for a growth review again, and it is the repair T1 already got.
2. **§3** — `HREF{Integers}` in the definition and in `Similar tables`, dropping
   the `#0` anchor. The same edit T1 already got.
3. **§4** — add `additive identity` to `Keywords`. Cheap, and it is the one
   name a reader might type that reaches nothing today.
4. **Nothing else. Do not add an entry, and do not write a generator.**

Items 1 and 2 are the same sweep across T37, T38, T39, T42 and T43 that the T1
review asked for; doing them for T0 alone leaves the question open five more
times.

**I changed nothing.** This is a report.
