# T12, "Proton-to-electron mass ratio": can it grow?

Read on 2026-09-21 as a growth review. 2 entries; the `Numbers` block is
**77 bytes** and the whole document 1550 bytes compact — near enough the 1546
the brief quotes, and 0.17% of the 1200-entry soft limit against a corpus
median of 119 entries. The question asked was whether the range is the whole
of what the definition promises, or whether the table was stopped early.

**Answer: it is finished, and it is the "named constant" case the brief
anticipates.** The definition names one quantity — the quotient of the proton
rest mass by the electron rest mass — and the table holds it in the two
conventions it is written in, $\mu$ and $\mu^{-1}$. There is no index to run:
no degree, no order, no argument, no next particle. The two entries are not a
selection from a family; they are one number and its reciprocal, which is
exactly the skill's "where two entries are one object in two conventions, one
table", and the conversion is invertible in the strict sense that rule asks
for. **Nothing should be added.**

The family axis that *could* have grown — other particle mass ratios — is not
this table's. It is **T76, "Mass ratios"**, which already holds 40 ratios over
twelve masses, and which holds this one twice with
`equals: HREF{Proton-to-electron_mass_ratio#mu}` and `#mu_inv` pointing back
here. The corpus settled this question years ago. What it did not do is make
T12 say so, and that is where the four findings below come from: **every one
of them is about the table admitting it is complete, not about making it
bigger.**

## 1. How I read it

- **Rendered page:** `curl https://numberdb.org/T12` — **direct, no proxy.**
  There is no listener on `127.0.0.1:1080` on this runner at all
  (`ss -ltn` finds nothing); direct HTTPS answers 200 for numberdb.org, for
  `physics.nist.gov` and for the skill. `docs/agent-environment.md` already
  records that the `ssh -N -D` tunnel dies without recovering, and the T18
  growth review met the same thing on the same day, so I have not added a
  third copy of the note. The page sets cleanly: no broken mathematics, no
  eaten `<`, no `argument ()`, and the two entry anchors `id="mu"` and
  `id="mu_inv"` both exist — which matters, because T76's two `equals` links
  resolve on them.
- **Document:** `numberdb.table('T12')` through `clients/python`. Two entries,
  `type: R`, `rigour: measured`, `sources: CITE{Bar03}`, **no `complete`, no
  `complete-note`**, and `Formulas`, `Programs`, `Keywords`,
  `Similar tables` and `Display properties` all empty.
- **Provenance:** `/revisions/T12`. Seven revisions: three imports from the
  data repository in February and March **2021** by bmatschke, three 2026
  migrations, and the 2026-08-14 migration that added the `rigour details`
  paragraph. **The numbers have not been touched in five and a half years.**
- **Generator:** there is none, and nothing in `generators/` mentions T12.
  That is correct rather than missing: the skill says `generate.py` is "the
  program that reproduces and extends *this* table", and nothing computes a
  measurement. §5 is about what stands in its place.
- **The neighbours:** T76 and T78 (`Mass ratios`, `Magnetic moment ratios`)
  and T10 (`Fine-structure constant`), fetched whole. T10 is T12's twin in
  every structural respect, down to the `expression` parameter with
  `show-in-parameter-list: no`, the `comment-non-constant` key and the missing
  `complete`.
- **The source:** `https://physics.nist.gov/cgi-bin/cuu/Value?mpsme` and
  `?mesmp`, read directly, and **independently** `scipy.constants` inside the
  server's Sage via `agents/sage.sh` (scipy 1.17.1). The two agree exactly.
  §4.
- **Audit:** `GET /api/table/T12/audit` — `"findings": [], "clean": true`.
  §6 is why I both agree with that and think it is uninformative here.
- **Search:** six lookups through `numberdb.search`, measured not inferred.
  §3.

## 2. Why there is no third entry

The skill's test for a range is "whether anybody will arrive holding one of
them", and its test for a second entry in a constant's table is that the two
forms determine each other. Both are satisfied here and neither admits a
third.

$\mu$ is what the molecular-spectroscopy and varying-constants literature
writes; $\mu^{-1}=m_{\rm e}/m_{\rm p}$ is what NIST's own table calls the
*electron-proton mass ratio* and publishes as a separate line. A reader
arrives holding either, so both belong, and $x\mapsto1/x$ is as invertible as
a conversion gets. There is no third convention in use: nobody records
$\ln\mu$ or $\sqrt\mu$, and a row for one would be the "counting rather than
choosing" the skill warns about.

Two other ways this table might have been thought unfinished, and why neither
is growth:

- **Other mass ratios.** This is T76's subject, it is done there, and moving
  it here would break the one rule the corpus is most consistent about: *a
  title is what a search reaches*. "Proton-to-electron mass ratio" answers
  somebody typing that phrase; putting $m_\mu/m_{\rm e}$ under it makes the
  muon ratio unfindable by name. T76 and T12 are the right shape, and the
  `equals` marker is the machinery that lets the same value sit in both
  without either pretending to be the other's copy.
- **Historical measurements, one entry per experiment.** T10's reliability
  note gestures at this — "all measurements … in the years 2014-2020" — but
  T10 still holds two entries, not twelve. Nobody arrives holding the 1998
  adjustment's value of $\mu$; they arrive holding today's. A row per
  adjustment would be a listing of something nobody is looking for, which is
  the failure mode the skill spends a page on.

I also checked what a reader actually gets. `numberdb.search` on
`1836.152673426` (the current CODATA value, which is what a modern library
hands back) returns **both** tables, T76 first and T12 second; on
`5.446170214889e-4`, likewise; on the coarse `1836.15`, T12 first. A reader
holding either number is served in one screen. This is the one thing that had
to work and it does.

## 3. Nothing points from here to T76 — worth doing

T76 names T12 twice, in the only way the data model has. **T12 names T76
nowhere**: `Similar tables` is the empty string, `Comments` holds one sentence
about $\mu$ possibly varying, and the word "mass ratios" never appears.

A reader who lands on T12 holding $m_{\rm n}/m_{\rm e}$ — an easy mistake, the
numbers are 1838.68 and 1836.15 — is told nothing and leaves. A reader who
wants to know whether this database has the muon ratio has to find T76 by
guessing its title.

**Smallest change:** one line in `Similar tables` naming T76 and the relation,
e.g. *"HREF{T76}[Mass ratios] — the other ratios of particle rest masses;
$\mu$ and $\mu^{-1}$ appear there too, as $m_{\rm p}/m_{\rm e}$ and
$m_{\rm e}/m_{\rm p}$."* A second line to T10 is defensible — $\alpha$ and
$\mu$ are the two dimensionless constants the varying-constants literature
studies together, and T12's own `comment-non-constant` is T10's sentence with
the symbol changed — but it is weaker, and I would take it or leave it.

## 4. The digits are CODATA 2018, and CODATA 2022 is out — worth doing, not urgent

This is the only axis on which T12 can move at all, and it moves by
maintenance rather than by growth.

The stored intervals are not arbitrary. CODATA 2018 gives
$\mu = 1836.15267343(11)$ with relative standard uncertainty $6.0\times
10^{-11}$, and five of those, rounded **up**, is $5.5085\times10^{-7}
\to 5.51\times10^{-7}$ — the stored radius exactly. The same arithmetic on
$\mu^{-1}$ gives $1.6339\times10^{-13} \to 1.64\times10^{-13}$, also exactly
the stored radius. So T12 is CODATA 2018 widened to five sigma and written out
in `+/-` form, which is the convention its own `reliability` note declares.
T76 stores the same adjustment in the concise `(11)` form and says so —
`sources: CITE{NIST} (based on CODATA 2018)`.

CODATA 2022 has been out since May 2024. From NIST directly and from
`scipy.constants` in the server's Sage, which agree to every digit:

| | stored (CODATA 2018, 5σ) | CODATA 2022, 5σ |
|---|---|---|
| $\mu$ | 1836.152673430 ± 5.51e-7 | 1836.152673426 ± 1.60e-7 |
| $\mu^{-1}$ | 0.000544617021488 ± 1.64e-13 | 0.0005446170214889 ± 4.70e-14 |

**Nothing here is wrong.** The new centres lie well inside the stored
intervals — the shifts are 4e-9 and 9e-16 against radii of 5.5e-7 and
1.6e-13 — so this is not a correction and there is no reader being misled.
The gain from updating is 3.4× on $\mu$ and 3.5× on $\mu^{-1}$, which is about
half a significant digit. That is why I rank it below §3 and §5: do it when
somebody is in the file anyway, not as an errand of its own.

What makes it *hard* to do, and is the real finding here, is §5.

## 5. The cited source cannot be where the digits came from — worth doing

`sources: CITE{Bar03}` is John D. Barrow, *The Constants of Nature*, 2003, a
popular book. The `reliability` note says the interval "is chosen to contain
the measurement up to five measurement uncertainties **that are displayed in**
[Bar03]".

It cannot have been. §4 shows the radius is five times CODATA 2018's relative
uncertainty of $6.0\times10^{-11}$, and **CODATA 2018 was published in May
2019, sixteen years after the book**. Barrow gives $\mu$ to a handful of
figures, as a trade book does; he does not display a relative uncertainty at
$10^{-11}$.

This matters for growth in the plainest way: **the table's stated source is
one that never gets revised.** Nobody reading T12 can tell which adjustment
the digits are, or whether a newer one exists, or where to go to check — which
is precisely why §4 sat undone for five and a half years while T76, which
cites NIST and names its adjustment, is at least legible about being out of
date.

**Smallest change:** give T12 the sourcing T76 and T78 already have — a `NIST`
link to `https://physics.nist.gov/cuu/Constants/index.html`, `sources:
CITE{NIST} (based on CODATA 2018)`, and a `reliability` note that says five
times the *standard uncertainty NIST publishes*. Keep `Bar03` in `References`,
cited from a comment, where a popular account of why this ratio matters is
worth having; it is a reference, not a source of digits. If §4 is done at the
same time, "CODATA 2018" becomes "CODATA 2022" and the two changes are one
edit.

A one-line `Programs` entry would follow naturally and is worth having on its
own — the skill wants "the standard incantation for a reader who wants one
more value", and here it is exact:

```python
from scipy.constants import physical_constants
physical_constants['proton-electron mass ratio']   # (1836.152673426, '', 3.2e-08)
```

I ran that through `agents/sage.sh`; the output above is verbatim. scipy also
exposes `_physical_constants_2018` alongside `_2022`, so the whole maintenance
path — check the adjustment, widen by five, compare against what is stored —
is three lines and reproducible by the reader on their own laptop.

## 6. No `complete` key, and this is the one I would do first

T12 never says it is finished. `Data properties` has no `complete` and no
`complete-note`, so the page simply does not carry the line.

That is not how this corpus reads. I sampled 30 tables across the range:
**25 carry `complete`**, most with a note. The five that do not are
T10, T12, T42, T76 and T78 — the oldest physics and seed tables, which is to
say the ones nobody has been back to. It is not a field anybody has to
remember, either: `NEW_TABLE_TEMPLATE` in `numberdb_app/editing.py` starts
every table created since with `complete: no` already written in. T12 predates
that by five years. T18 is the model, and its note is exactly the sentence T12
wants:

> complete: **yes** (it holds Broadhurst's six constants for the
> period-doubling fixed point, together with the positive convention
> $|\alpha|$ for the second Feigenbaum constant)

The brief says "a named constant with one entry is finished, and saying so is
a good answer". The table should be the thing that says so. A reader who finds
two entries and no statement cannot distinguish "this is the whole of it" from
"somebody got bored", and this review exists only because that distinction was
not written down.

**Smallest change:** `complete: yes`, with a note along the lines of

> it holds $\mu$ and its reciprocal $\mu^{-1}$, which are the two forms this
> ratio is published in; the ratios of the other particle rest masses are in
> HREF{T76}[Mass ratios]

I checked that `HREF{}` survives in a `complete-note` rather than printing
raw: `numberdb_app/views.py:1177` folds the note into the `complete` line, and
T296's note renders `HREF{T295}[the singular moduli $k_r$]` as a live anchor
on the page. So the note can carry the §3 link too, and a reader meets it
without scrolling.

## 7. The audit is clean, and it is structurally blind here

`GET /api/table/T12/audit` returns `{"findings": [], "clean": true}`. I agree
with every check it ran, and I want to record one it could not run.

`_values_also_in_another_table` (`audit_table.py:688`) — the check that
catches two tables holding the same numbers — opens with

```python
rows = list(Number.objects.filter(table=table)...)
if len(rows) < self.ENOUGH:      # ENOUGH = 3
    return
```

T12 has two indexed values. **The check returns before sampling anything.**
And if it had run, it would have fired at the maximum: 2 of 2 distinctive
values are also in T76, which is 100% against a threshold of "at least three,
and at least half". Its own message — *"if these are the same numbers, one of
the two tables should not exist, and if they are not, say how they differ in
Similar tables"* — is §3, almost word for word.

I do not think the floor is wrong. Three is there so the check does not shout
about small cases where one shared value proves nothing, and raising it is a
different kind of change. But it means **`clean: true` on a two-entry table is
the absence of evidence and not evidence of absence**, and a table this small
gets its overlap read by a person or not at all. That is worth knowing the
next time a two-entry table passes an audit.

The one other check that might have had an opinion — the grid check, on a
parameter whose values are a handful of names — also bails, because each of
`mu` and `mu_inv` carries a single entry. Here the silence is *right*: this is
the good kind, one number in two conventions, and the skill blesses it
explicitly. The `expression` parameter with `show-in-parameter-list: no` and
symbols for values is the correct rendering of it, and the page shows
`$\mu$:` and `$\mu^{-1}$:` as labels rather than a `value` column, which is
the tell the brief says to look for. It is not there.

## 8. Noted only because I noticed

- T12 displays $\mu^{-1}$ as `0.000544617021488`; T76 displays the entry it
  declares `equals` to it as `5.44617021487(33)e-4`. The last shown digit
  differs. Nothing is wrong — T12's radius is 1.64e-13 and the disagreement is
  1e-15, so each interval contains the other's centre and both contain CODATA
  2022 — but a reader who follows the `equals` link sees two numbers that do
  not look identical. It resolves itself if §4 is done, since both would then
  be restated from the same adjustment.
- The two tables index the same measurement at **different confidence
  levels**. `data_pipeline/build.py:401` reads a stored `(11)` as a ball of
  **one** standard uncertainty, with a comment in the file saying the 68%
  that implies "is not good"; T12's `+/-` form spells out **five**. So T76's
  $m_{\rm p}/m_{\rm e}$ is indexed as ±1.1e-7 and T12's $\mu$ as ±5.51e-7 —
  the same number, searchable through two windows differing by a factor of
  five. Both matched every query I tried, so no reader is losing a hit today.
  It is a corpus-wide question about the `(nn)` form rather than a T12 defect,
  and I raise it here only because T12 is where the two conventions touch.

## 9. What I would change, in order

1. **`complete: yes` with a note** (§6). The table's whole situation is that
   it is finished and does not say so. One field and one sentence.
2. **`Similar tables` → T76** (§3), which the note in (1) can carry by itself.
3. **Re-source to NIST/CODATA** (§5), and add the two-line `Programs` snippet.
   This is what makes (4) possible for the next person.
4. **Update the digits to CODATA 2022** (§4). Half a significant digit, no
   correction, best done inside (3).

None of these adds an entry, and none should. **The range is the whole of what
the definition promises.** I did not change the table.
