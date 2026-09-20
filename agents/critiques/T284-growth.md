# Can T284 grow? "Salem numbers less than 1.3"

Read on 2026-09-20, published, 47 entries in 20125 bytes. The question asked
was whether the range is the whole of what the definition promises or whether
the table was stopped early.

**It was not stopped early. The range *is* the definition, the definition is
full, and no computation adds a row.** The table can only grow by being
redefined, there is exactly one defensible redefinition, and it is capped
0.0247 above the present bound by a limit point of the Salem numbers that this
corpus already holds as a table.

## How I checked

- **Skill** fetched from <https://numberdb.org/skill>. The SOCKS proxy on
  1080 refused connections again; `curl` direct works from this runner, as
  `docs/agent-environment.md` says. Nothing new.
- **Document** `GET /api/table?id=T284`; **page** `GET /T284` (200, renders,
  no `Math input error`, no `argument ()`, no unresolved `CITE{`/`HREF{`).
- **Audit** `GET /api/table/T284/audit` returns `findings: []`, `clean: true`.
  I agree with it, and none of what follows is a thing it could see: the
  audit checks the form of a table, and a range is a judgement about a
  family.
- **Generator** `generators/salem-numbers-less-than-1.3/generate.py`.
- **Sources** Mossinghoff's archived lists (`SalemList.html`, `S4.txt` …
  `S24.txt`, `Known180.gz`) and Sac-Épée, arXiv:2409.11159v3, read from the
  LaTeX source.
- **Sage** two scripts through `agents/sage.sh`; what they checked is stated
  where it is used below.

## 1. The definition promises all of them, and all of them are here

The title and the second sentence of the Definition agree: "Listed are the
small Salem numbers, those less than $1.3$." There is no degree bound and no
search box in that sentence, so the promise is the whole family, and the
table keeps it as well as anybody can:

- **Mossinghoff's list has 47 rows**, and the generator holds all 47. Its
  `SOURCE_ROWS` is a transcription of that page, with `EXPECTED_ROWS = 47`
  asserted. There is no parameter in `enumerate()` to turn up. That is the
  right shape for this table and not a defect: the family is a list, not a
  grid.
- **The low-degree part is certified by an independent source.** Mossinghoff
  also publishes complete lists of Salem numbers of each fixed degree 4 to
  24, up to bounds (3, 2.8, 2.6, 2.4, 2.2, 2, 1.8, φ, φ, 1.5, 1.4) that all
  exceed 1.3. I parsed `S4.txt` … `S24.txt` and compared: they contain
  exactly 29 Salem numbers below 1.3, and those 29 are exactly this table's
  29 entries of degree at most 24, agreeing to 1e-13 (the fixed-degree lists
  carry 14 decimals).
- **The high-degree part is confirmed as far as anybody has looked.**
  `Known180.gz` lists every *known* irreducible non-cyclotomic polynomial of
  degree at most 180 with Mahler measure below 1.3: 8438 of them. Exactly 47
  have one root outside the unit disc, which is what makes the measure a
  Salem number, and those 47 are this table's 47 (same degrees, values
  agreeing to 5e-13 at the 12 decimals that list prints). So no published
  Salem number below 1.3 of any degree up to 180 is missing here.
- **The list has not moved since 1993.** Boyd found 39 in 1977 and 4 more in
  1978; Mossinghoff added the last 4 in 1993. Completeness was certified to
  degree 40 in 1999 and to degree 44 in 2008, and Sac-Épée's 2024 sampling
  search found nothing new below 1.3.

A new row therefore requires somebody to discover a new small Salem number,
which is Lehmer's problem in one of its forms. That is not a range decision,
and the table is right to be 47 rows.

### One sentence in `complete-note` claims more than its source

> "a later random-sampling search rediscovered all 47 and found no others
> below $1.3$"

Sac-Épée searched half-degrees $d = 10$ to $32$, that is Salem degrees 20 to
64 (§2.3). "Found no others below 1.3" reads as unbounded and is bounded.
Smallest fix, and it is worth doing because this is the sentence a reader
holding a number near 1.29 reads to decide whether their number is missing or
is not a Salem number: end it "…and found no others below $1.3$ of degree at
most $64$".

The `Known180` fact above is the stronger version of the same claim and costs
one clause: every known polynomial of degree at most 180 with Mahler measure
below 1.3 whose measure is a Salem number is in this table. If it is added,
Mossinghoff's list page is already in `Links` and no new reference is needed.

## 2. The ceiling: the plastic constant, and it is T286's first row

`comment-bound` already says the important thing, and says it well: the
plastic constant is the smallest known limit point of the Salem numbers, and
Salem's construction puts infinitely many Salem numbers below it. That is
what caps this table forever.

Made concrete. $\rho = 1.324717957244746\ldots$ is the real root of
$x^3-x-1$. I ran Salem's construction on it: factor $z^nP(z)\pm P^*(z)$ for
$P=z^3-z-1$, keep the irreducible factors that are Salem polynomials, and
collect their Salem roots. For $n\leq 89$ that gives

- **14** Salem numbers in $(1.3,\,49/37]$, and
- **63** in $(49/37,\,\rho)$,

and the roots increase to $\rho$, so the second count grows without bound as
$n$ does. From this one Pisot number alone. So:

| bound $B$ | "Salem numbers less than $B$" |
|---|---|
| $B < \rho$ | conjecturally finite, and a table |
| $B \geq \rho$ | infinite, and not a table |

The entire headroom this table can ever have is the interval
$(1.3,\ 1.3247179\ldots)$, of width 0.0247, and the count diverges at its
right end.

**T286 holds $\rho$ and this table does not link it.** The corpus has
"Pisot numbers less than the golden ratio" at
`Pisot_numbers_less_than_the_golden_ratio`, whose entry `1` is the plastic
constant, with a comment naming it the smallest Pisot number. T286's
`Similar tables` links T284; T284's does not link back, and `comment-bound`
names the plastic constant in plain text. Worth doing, small, and it belongs
to the growth question because that entry is the boundary of this table's
range: make the first mention
`HREF{Pisot_numbers_less_than_the_golden_ratio#1}[the plastic constant]`, and
add T286 to `Similar tables` with the relation stated — its first entry is
the smallest known limit point of the Salem numbers, which is why this table
stops where it does.

T286 is also the instructive contrast, and it is why "stopped early" is the
wrong reading here. T286 holds 79 of an infinite family accumulating at
$\varphi$, and could because Dufresnoy and Pisot *classified* the Pisot
numbers in $(1,\varphi)$: there is a formula, an increasing order, and a
place to stop for a stated reason. Nothing of that kind exists for the Salem
numbers below $\rho$. Boyd's theorem says every Salem number arises from
Salem's construction on some Pisot number, but that is not an enumeration in
increasing order, and the sources are lists rather than families. T284
cannot grow the way T286 grew.

## 3. The one extension that exists: $B = 49/37$

Sac-Épée (arXiv:2409.11159, 2024/25) is the only published list that reaches
past 1.3 while staying below $\rho$. His threshold $49/37 = 1.324324\ldots$
is chosen exactly for that, and it covers 98.4% of the remaining interval:
$\rho - 49/37 = 3.94\cdot 10^{-4}$. His table lists **25** Salem numbers in
$(1.3,\,49/37)$, ten of them new.

**I checked all 25 in Sage**, from the printed half-coefficient lists alone:
each rebuilds an irreducible reciprocal polynomial of the printed degree with
exactly one real root greater than 1, one in $(0,1)$ and every other root on
the unit circle; each Salem root is strictly inside $(1.3,\,49/37)$; the 25
are distinct and in the printed order; and each printed decimal is correct to
its 12 places. Degrees run 12 to 44. So the values are sound, whatever is
true of the list's completeness.

What an extended table would look like:

- **72 entries, about 31 KB.** I built the entry comments in the generator's
  own format and measured: the 25 add roughly 7.3 KB of key, value and
  comment, so the stored block goes from 20125 to about 31 KB. A tenth of
  the soft limit, and the largest entry is no larger than the degree-46 row
  already here.
- **The completeness note would have three clauses, all citable.** Complete
  below $49/37$ for degree at most 24, by Mossinghoff's fixed-degree lists —
  I checked that those lists give exactly Sac-Épée's 16 rows of degree at
  most 24 in the window, so the two sources agree where they overlap.
  Complete below 1.3 for degree at most 44, by Mossinghoff, Rhin and Wu.
  Everything else — degrees 26 to 64 in the window — from one sampling
  search, uncertified, and degrees above 64 unsearched in the window at all.
- **It must be this table, retitled.** A separate table of the numbers
  between 1.3 and $49/37$ would be one family cut at an arbitrary point and
  split across two pages; the skill's reasons for two tables (two
  conventions, two parameterisations, two costs of storage) none of them
  apply.
- **The cost is the title.** "Small Salem number" *means* less than 1.3 in
  the literature — Sac-Épée §1.3 says so, and `comment-bound` says so. A
  title reading "Salem numbers less than $49/37$" names one preprint's
  threshold instead of a named object. `Keywords` already carries "small
  Salem number" and is weighted with the title, so search survives; the
  Definition would have to keep the sentence that 1.3 is what "small" means.
- **The generator's source check would have to change.** Mossinghoff's
  `SalemList.html` truncates its decimals, and `check_source_truncation`
  depends on that. Sac-Épée rounds, and so do the fixed-degree `S*.txt`
  files, whose format note says so explicitly. My first run of the check
  failed on the degree-38 row for exactly this reason: the root is
  1.30647353753260…, printed as 1.306473537533. Ten of the 25 are rounded up.
  A source-decimal check on those rows has to allow a half-unit in the last
  place.

**Is there a reader this would serve?** One, demonstrably. The smallest of
the 25, $1.3022688050943344\ldots$, is already in the corpus: it is T222's
row `[12,3]`, the growth rate of the Coxeter triangle group
$\Delta(2,3,12)$, and its minimal polynomial there is the one Sac-Épée's
coefficients give. It sits 0.0023 above this table's cutoff. Somebody who
computes that growth rate and asks whether it is a Salem number gets T222,
which does not say, and not T284, which is the table that would. It is the
only T222 value in $(1.3,\rho)$; T223's smallest value is 1.3509…, well
outside. For the other 24 I found no occurrence elsewhere in the corpus.

**My reading.** One reader served, 25 verified values, 11 KB, against the
loss of a title that names a literature object and the mixing of a
33-year-stable certified core with a one-preprint extension. I would take it
— the table's own `comment-bound` already argues that 1.3 is traditional and
$\rho$ is the real boundary, and a table that says so and then stops at the
traditional bound is arguing against itself — but this is a change to what
the table *is*, not to how far a computation ran, and it is the owner's call
rather than a repair. If it is not taken, nothing here is wrong: the table is
complete against its own definition and should be left alone.

## What would not be growth

Three neighbouring families turned up while reading, and none of them is this
table getting longer:

- **Small Mahler measures.** `Known180.gz` has 8438 polynomials with measure
  below 1.3, of which only the 47 have Salem measures. The other 8391
  measures are a genuine family and a genuine table, but 8438 entries is past
  both the recommended 1000 and the soft 1200, so it would need a range
  decision of its own before it is a table at all.
- **Salem numbers by degree.** Mossinghoff's `S4.txt` … `S24.txt` are 1741
  rows of complete fixed-degree lists up to bounds between 1.4 and 3. A table
  of the smallest Salem number of each degree is a different and much
  smaller idea. Either is a sibling, not an extension.
- **More digits.** The values are roots of exact polynomials, so any
  precision is available and 100 is the house number. Nobody arrives holding
  300 digits of a Salem number. Leave it.

## What reads well

The two things I checked hardest and found sound: the 47 are exactly the
known family, confirmed against two Mossinghoff sources the table does not
cite and one it does; and the range is not a size target but a named object,
with `comment-bound` giving the mathematical reason for the bound rather than
a count. That paragraph is the model of what the skill asks a completeness
argument to be, and it is the reason this table reads as finished rather than
as abandoned partway.

Nothing in this report is a reason to run the generator again.
