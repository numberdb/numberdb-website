# T5, "Exponent of matrix multiplication complexity": can it grow?

Read on 2026-09-21 as a growth review. 1 entry, 2039 bytes of `table.yaml` —
0.08% of the 1200-entry soft limit, 0.6% of the 320 KB block limit. The
question asked was whether the range is the whole of what the definition
promises, or whether the table was stopped early.

**Answer: it is complete, and it is the named-constant case the brief
anticipates. No entry should be added.** The definition names one real number.
There is no index to run — no degree, no order, no argument, no next member —
and the one parameter the definition could plausibly carry (the field) is a
parameter every published theorem is uniform in, so it would produce rows that
are all the same interval (§4). There is no generator and none is possible:
`Programs` is empty because no incantation returns one more value of $\omega$,
and that emptiness is itself the evidence (§3).

That is the predicted answer and it is the right one. The useful part of this
review is the sentence after it:

**T5 is the one table in this corpus whose single entry cannot grow but *must
be narrowed*, and it is four record improvements overdue.** The stored upper
bound is 2.3728596, from Alman–Vassilevska Williams in 2020. Four better bounds
have been published since, the current one being 2.371177 in 2026 (§2). The
table's own `rigour details` says "Sharper upper bounds have been published
since" without saying what they are, and the table's own comment calls 2.3728596
"the most recent bound", which is now a false sentence on a rendered page. For
a family table, "complete" is a state; for this table it is a standing
obligation, and nothing in the document says so.

Two smaller things: the table does not declare `complete` at all, where T7
("Pi"), the corpus's own one-entry named constant, declares `complete: yes`
(§5); and the numbers that a reader actually arrives holding in this subject —
$\log_2 7$, the Coppersmith–Winograd 2.3755 — are in prose, not in rows, and
are not in this table's definition either, so the growth they represent is a
sibling table and not more of T5 (§6).

## 1. How I read it

- **Rendered page:** `curl https://numberdb.org/T5` — **direct, no proxy.**
  `ALL_PROXY` is empty on this runner and nothing listens on `127.0.0.1:1080`;
  `--socks5-hostname 127.0.0.1:1080` answers exit 7 for every URL and direct
  HTTPS answers 200. `docs/agent-environment.md:1117–1134` already records
  this and counts the earlier occurrences, so I have not added another copy.
  The page sets cleanly: the value column is headed `$\omega$` from
  `Display properties: number-header`, not the fallback word `value`; no
  `Math input error`, no eaten `<`, no `argument ()`; there is no `Parameters`
  block, which is right for one unparameterised entry. The value carries the
  `not-findable-mark` dagger linking to `/help#search-precision` — correct, and
  §7.
- **Document:** `numberdb.table('T5')` from `clients/python`, and the same YAML
  from `/bundle/T5`. They agree. `Parameters`, `Formulas`, `Programs`,
  `Similar tables` and `Keywords` are all empty; `Data properties` holds `type`,
  `sources`, `rigour` and `rigour details` and **no `complete` and no
  `complete-note`**.
- **Generator:** the bundle is `T5/table.yaml` and `T5/README.txt` and nothing
  else, and `/files/T5` says "This table carries no files." There is no
  `generate.py`. §3.
- **Provenance:** `/revisions/T5` and `/history/T5`. Created 2021-01-14 by
  bmatschke ("added matrix multiplication complexity exponent"), last touched
  as data 2021-03-05 ("changed data type to R"); then the 2026-08-09 import and
  flattening, and the 2026-08-15 rigour migration, whose diff is the whole of
  `rigour` and `rigour details`. **The value has not been touched in five and a
  half years.**
- **Audit:** `GET /api/table/T5/audit`. Three findings, all the same one. §8.
- **Search behaviour:** `/api/lookup?text=...`, against the live corpus. §6, §7.
- **No Sage was needed.** Nothing here is a computation: the entry is a pair of
  theorems, and the checking to be done is bibliographic. I note that explicitly
  because a growth review that ran Sage on this table would have been measuring
  the wrong thing.

## 2. The entry is four record improvements out of date, and the table says the wrong thing about it — worth doing

What a reader sees, in the comments block on the page:

> Alman and Vassilevska--Williams [1] proved the most recent bound
> $\omega \leq 2.3728596$.

and, under "How they were obtained":

> …the best upper bound published **when the entry was written**. … Sharper
> upper bounds have been published since.

The first sentence is false as printed. The second is true, and is an
admission that the first is false, placed where a reader who has already read
the first will not connect them — and it names no replacement, so a reader who
believes it is left worse off than before: they now know the page is stale and
still do not know the number.

Wikipedia's *Computational complexity of matrix multiplication* carries the
timeline. The four bounds published after the stored one:

| year | bound | authors |
|---|---|---|
| 2022 | 2.371866 | Duan, Wu, Zhou |
| 2024 | 2.371552 | Vassilevska Williams, Xu, Xu, Zhou |
| 2024 | 2.371339 | Alman, Duan, Vassilevska Williams, Xu, Xu, Zhou |
| 2026 | 2.371177 | Dupont, Eisenberger, Kozlovskii, Mehrabian, Ruiz, See, Zhou, Alman, Vassilevska Williams, Balog — arXiv:2608.16884 |

Smallest change that fixes it: the entry becomes `[2, 2.371177]`, `sources`
and `References` gain the 2026 paper, and `comment-non-trivial-bounds` loses
the words "the most recent" in favour of naming the year — "Alman and
Vassilevska Williams [1] proved $\omega \leq 2.3728596$ in 2020, and the bound
has been improved four times since; the best published is
$\omega \leq 2.371177$ [new ref]." The last sentence of `rigour details` then
becomes "the best upper bound published in 2026" and the apology drops out.

**Two cautions for whoever does it, neither of which I could resolve from
here.** First, I read this from Wikipedia and not from the papers, and
Wikipedia's *other* article on the subject — the one T5 links as `Wiki` —
still says 2.371339 "as of September 2025". The two pages disagree, which is
exactly the failure mode this entry is already in. The bound should be taken
from arXiv:2608.16884 itself before it is written into a row. Second, whoever
changes it should decide whether a bound six months old is something this
corpus wants to chase at all, or whether the honest entry is the *durable*
one — `[2, 2.375478]`, Coppersmith–Winograd, which stood for twenty years —
with the current record in a comment. I think chasing is right, because the
interval is the whole content of the entry and a stale interval is a wrong
one, but it is a judgement and it belongs to a person.

This is a repair finding rather than a growth finding, and I am reporting it
under a growth brief because it *is* the growth answer: the only axis this
table has is the width of its one interval, and that axis has moved four times
while the table stood still.

## 3. There is no generator, and that is the proof of completeness

`Programs` is `{}` and the bundle carries no `generate.py`. On most tables that
is a gap. Here it is the finding: the skill says `Programs` holds "the standard
incantation for a reader who wants one more value", and for $\omega$ there is
no such incantation in Sage or anywhere else, because one more value does not
exist and the one value that does is not computable — it is the subject of an
open problem. A table whose generator cannot be written *because the family has
one member and that member is unknown* is finished by construction.

I checked that this is not merely an omission by asking what such a program
would say. `RBF(2)` is not $\omega$. There is no `matrix_multiplication_exponent()`.
The nearest honest program is a literal, and a literal that will be wrong again
in two years is worse than nothing. **Leave `Programs` empty.** This is the one
place where T7's repair — which added a `Programs` line — should *not* be
copied across.

## 4. The only parameter the definition could carry would make identical rows

The definition says "field operations" and never says over which field. That is
the single place where somebody looking for growth would reach: index the table
by the field, or by its characteristic, and $\omega_p$ for $p = 0, 2, 3, 5,
\dots$ is a family with an index, which is the shape the skill blesses
("where the members share an index, one table however few").

It does not work here, and it is worth writing down why so that the next
reader does not spend the afternoon on it:

- Every bound in the timeline in §2 is proved by the laser method over an
  arbitrary field. There is no published row where the bound over one field
  differs from the bound over another.
- The lower bound 2 is the trivial counting bound and is the same everywhere.
- So every row of such a table would read `[2, 2.371177]`, identically, for as
  many characteristics as somebody chose to list. That is the skill's "counting
  rather than choosing" in its purest form: a bound on the index admits
  $\omega_{101}$ and nobody has ever met $\omega_{101}$.
- The standard references state that the exponent depends on the field only
  through its characteristic (Bürgisser–Clausen–Shokrollahi, *Algebraic
  Complexity Theory*, ch. 15). I did not verify that from the source, and it
  does not change the conclusion either way: if it is true the rows collapse
  further, and if it is false nobody has published a separation to put in them.

The smallest useful change this suggests is not a parameter but a clause: the
definition could say "over any field", which is what the theorems prove and
what Wikipedia's own statement of the definition says. That is a one-phrase
edit to the `Definition`, it makes the table's silence deliberate rather than
accidental, and it forecloses the question for the next reader. Worth doing,
but small.

## 5. `complete` is absent, and the corpus has the precedent one table away — worth doing

T5's `Data properties` has no `complete` key. Compare the other single-entry
named constants among the seed tables:

    T1  One                                    1 entry    complete: (absent)
    T5  Exponent of matrix multiplication      1 entry    complete: (absent)
    T7  Pi                                     1 entry    complete: yes
    T8  Euler's constant e                     1 entry    complete: yes   (repaired 2026-09-21)

T7 and T8 say it; T1 and T5 do not. The consequence is not cosmetic. A reader
who lands on a one-entry table cannot tell from the page whether one entry
means "this is all there is" or "somebody started and stopped" — and neither
can the next growth scan, which is why this table was queued for one. Saying it
costs one line and retires the question permanently.

The clause finishes the sentence "complete: …", so the shape wanted is

    complete: yes, $\omega$ is a single constant and the entry is the interval
      between the trivial lower bound and the best published upper bound

which is true, is the sentence a reader wants, and — usefully — makes the
maintenance obligation in §2 a visible part of the table's own claim rather
than a footnote in `rigour details`.

One caveat on the wording. `complete: yes` means "every member of the family is
here", not "the digits are as good as they get". Those are different axes and
T5 is `yes` on the first and permanently `no` on the second. The clause above
says both without confusing them; a bare `complete: yes` would invite the
reading that the *value* is settled, which is precisely the open problem.

## 6. The numbers a reader arrives holding are in prose, and they are not this table's — a sibling table, not growth

The skill: "A value belongs in a row, not in a comment. A number written into a
comment answers no search, carries no type, and cannot be cited."

T5's comments carry $\log_2(7) \leq 2.8074$ and $2.3728596$. Neither is in a
row. I checked what that costs, against the live corpus:

    /api/lookup?text=2.807354922   →  T339, Shannon entropies of discrete
                                       probability distributions
    /api/lookup?text=2.3755        →  (nothing relevant)
    /api/lookup?text=Coppersmith   →  no tables
    /api/lookup?text=Strassen      →  T5 only

So a reader who arrives holding 2.807354922 — which is what you get if you
evaluate Strassen's exponent, the single most-computed number in this subject —
lands on **Shannon entropies**, because $\log_2 7$ is also the entropy of a
uniform distribution on seven outcomes. T5 is not offered. And a reader holding
the Coppersmith–Winograd 2.3755, the exponent that stood for twenty years and
appears in a thousand paper abstracts, finds nothing at all in NumberDB.

**This is not a fault in T5 and cannot be fixed inside T5.** $\log_2 7$ is not a
value of $\omega$; it is a bound on it. Putting it in a row of a table whose
`Definition` says "$\omega$ is the smallest real number such that…" would make
the value column hold two different things — one interval of ignorance and a
list of exact algorithm exponents — which is the two-tables-one-title fault the
brief warns about, with the value column falling back on the word `value` to
prove it.

The growth here is a **sibling table**, and by the skill's own test it is a
legitimate one. "Does the parameter name *what the number is of*, or *which
quantity is taken of it*?" — "the exponent achieved by Strassen's algorithm"
names what the number is of, the same shape as "one Hausdorff dimension for
each of forty named sets". Roughly:

- **Title** something like "Exponents of fast matrix multiplication algorithms".
- **Parameter** the algorithm, keyed specifically (not `expression`), displayed
  by author and year.
- **~16 rows**, Strassen 1969 through Dupont et al. 2026, the timeline in §2
  plus the eight earlier ones. Perhaps 1 KB. Nowhere near any limit.
- **Values**: exact where the algorithm gives one — $\log_2 7$ for Strassen,
  $\log_4 48 = 2 + \log_4 3$ for the 2025 AlphaEvolve/Dumas–Pernet–Sedoglavic
  $4\times4$ algorithm — and the published decimal bound where it does not,
  which is most of the laser-method row. That mixture is the table's one real
  design problem and should be settled before it is built, not after: an exact
  $\log_2 7$ and a rounded 2.3755 are not the same kind of thing, and a `rigour
  details` note has to say which rows are which.
- It would carry `repeats:` nothing, and T5 would gain a `Similar tables`
  entry pointing at it with the relation named.

**I am flagging this, not proposing it.** It is outside the brief — I was asked
whether T5 can grow, and the answer to that is no — and it is a table somebody
should decide to want. I record it because the question "how far could it go and
by what method" has, for this table, an answer that is not about this table, and
leaving that out would make the report read as though the subject were
exhausted. It is not; only T5 is.

## 7. The one entry answers no search by number, by design — noting only

The rendered value carries a dagger: *"This number will not be found in the
search."* That is `search.py:_identifiable`, which drops values whose relative
width exceeds `NUMBERDB_MAX_RELATIVE_WIDTH` (1e-5). T5's interval has relative
width about 0.17, four orders of magnitude over.

I confirmed the effect and confirmed it is not a bug, with a control:

    text=2.3728596    →  0 results        (T5's own upper endpoint)
    text=2.2          →  100 results, T5 not among them  (inside T5's interval)
    text=2.685452001  →  T170, Khinchin's means          (control: lookup works)

So T5 answers exactly zero numeric searches, now and permanently — narrowing the
bound to 2.371177 will not change that, since the interval stays 0.17 wide until
somebody proves $\omega = 2$.

This is the system working. The dagger says so on the page, and a search that
returned T5 for any number between 2 and 2.37 would bury every real hit in the
range. I note it because it settles the second axis a one-entry table can grow
on — precision — in the same way §4 settles the first: **T5 is a word-search
landing page, and it is a good one.** `matrix multiplication exponent` returns
it first, `omega` returns it fifth, `Strassen` returns it and nothing else. No
`Keywords` are needed; the title already carries every word somebody would type.

## 8. The audit's three findings are one finding, and it is right but not actionable here

    Tags: "complexity" reaches only this table
    Tags: "algorithms" reaches only this table
    Tags: "matrix multiplication" reaches only this table

All three are correct — I checked `/tags`, and none of the three appears in the
listing's first fifty by entry count, consistent with each holding one table of
one entry. And the rule behind them is right: the skill says "a tag with one
table on it is not a way through the corpus", and propose a new one only when
three or more tables would carry it.

But the fix the finding implies — retag T5 — is the wrong move, and I disagree
with acting on it as stated. There is nothing to retag T5 *to*: I searched for
`tensor rank`, `Coppersmith`, `galactic` and found no tables, and the nearest
algorithmic neighbours in the corpus (T274 and T288, cuckoo hashing thresholds)
are about a different thing. Stripping the tags would leave a table with no way
in but its title.

What the three findings actually say, taken together, is a fact about the
corpus and not about T5: **NumberDB holds one complexity-theory table, and this
is it.** Three dead-end tags on a one-entry table is the shape that makes. The
finding is worth keeping open, and the thing that closes it is §6 or something
like it — two or three more tables in the subject — not an edit here.

## 9. Small things, noted only

- **`comment-trivial-algorithm` proves the wrong half.** "The trivial matrix
  multiplication algorithm runs in $O(n^3)$, which proves $2 \leq \omega \leq
  3$." The trivial algorithm proves $\omega \leq 3$. The $2 \leq \omega$ half
  comes from the counting bound — an algorithm has to read $2n^2$ entries — and
  the comment attributes both to one cause. A reader who trusts it has a wrong
  proof of the lower bound. One clause fixes it: "…runs in $O(n^3)$, which
  proves $\omega \leq 3$; reading the $2n^2$ entries of the input gives
  $\omega \geq 2$." Small, but it is the only mathematical claim on the page
  that is not right, and `rigour: proven` invites a reader to take it at face
  value.
- **The `Wiki` link is the less useful of the two.** `Wiki` points at *Matrix
  multiplication algorithm* and `WikiCC` at the `#Computational_complexity`
  anchor of *Matrix multiplication*. I checked: both resolve, the anchor is
  still there. But the article that holds the timeline of bounds — the thing a
  reader of this table wants and the thing §2 is about — is a third one,
  *Computational complexity of matrix multiplication*. Adding it, or swapping
  it for `Wiki`, would put the maintenance source one click from the entry.
- **No `Similar tables`.** Correct as things stand; there is no table in the
  corpus this one relates to. It becomes a finding only if §6 is built.

## 10. What I would do, in order

1. **§2** — narrow the interval to the current published bound, from the paper
   and not from Wikipedia, and delete the words "the most recent" and the
   apology in `rigour details`. This is the whole of the table's growth.
2. **§5** — `complete: yes, <clause>`, matching T7 and T8. One line, and it
   stops this table being queued for a growth review again.
3. **§9, first bullet** — the $2 \leq \omega$ attribution.
4. **§4** — "over any field" in the definition.
5. **§9, second bullet** — the third Wikipedia link.

Findings 6 and 8 are not edits to T5 and should not be treated as ones.

**I changed nothing.** This is a report.
