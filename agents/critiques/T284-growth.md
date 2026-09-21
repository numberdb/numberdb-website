# Can T284 grow? "Salem numbers less than 1.3", read on 2026-09-20

47 entries, 20,125 bytes: 4% of the entry soft limit and 6% of the block soft
limit. The question asked was whether that is a table stopped early.

**It is not.** The range is exactly what the definition promises, and the
promise is exhausted: in the largest published list of its kind — every known
polynomial of degree at most 180 with Mahler measure below 1.3 — there are
exactly 47 with one root outside the unit circle, and they are these 47. There
is no 48th value to add under this title.

The table can nevertheless grow, once, by moving its bound. There is exactly
one place to move it to, and the material is already cited on the page.

## What was read

- **Skill:** `curl -sS --noproxy '*' https://numberdb.org/skill`, 48,740 bytes,
  fresh. `--socks5-hostname 127.0.0.1:1080` refuses on this builder; that is
  already in `docs/agent-environment.md` and nothing new was learned by it.
- **Page:** `GET /T284`, 200, 65,333 bytes, rendered and read as text.
- **Audit:** `GET /api/table/T284/audit` → `{"findings": [], "clean": true}`.
  I agree; nothing below is something a rule could see.
- **Generator:** `generators/salem-numbers-less-than-1.3/generate.py`.
- **Prior reading:** `agents/critiques/T284.md` and `T284-repaired.md`, and
  the build's own note in `agents/table-ideas/BATCH-2026-09-12T1831.md`, which
  raised the bound question and deferred it: *"Either keep 1.3 as the defining
  bound, or retitle and re-source. Decide before creating the draft."* This
  report is that decision, made with the list read.
- **Sources:** Mossinghoff's archived `SalemList.html` (47 rows), his
  `Known72.html` (2,010 rows) and `Known180.gz` (8,438 rows), his eleven
  complete fixed-degree lists `S4.txt` … `S24.txt` (1,741 rows), and
  Sac-Épée, arXiv:2409.11159 — the TeX source, because this machine has no
  PDF reader.
- **Computation:** one Sage run through `agents/sage.sh`, checking every
  candidate row exactly. Nothing was written to any table.

## 1. The range is the whole of the promise, and the promise is used up

The definition says "Listed are the small Salem numbers, those less than
$1.3$." A reader is entitled to ask whether the 47 are all of them.

Three independent counts say the list is exhausted at its own bound:

| source | what it covers | Salem numbers below 1.3 |
|---|---|---|
| `SalemList.html` | the list the table transcribes | 47 |
| `Known72.html` | all known measures < 1.3, degree ≤ 72 | 47 |
| `Known180.gz` | all known measures < 1.3, degree ≤ 180 | 47 |

The last two are lists of *polynomials*, not of Salem numbers; I counted the
rows whose `Out` column is 1, which is exactly the Salem condition. All three
give the same degree census — 8:1, 10:5, 12:1, 14:4, 16:1, 18:7, 20:4, 22:4,
24:2, 26:7, 28:1, 30:4, 34:2, 36:1, 40:1, 44:1, 46:1 — and it is the census of
the 47 rows on the page. So the place where a 48th small Salem number could
plausibly be hiding, a Salem polynomial of degree between 48 and 180 with
measure below 1.3, has been searched and is empty.

The table also holds *every* row of its source, not a prefix of it: all 47, no
truncation for size. Nothing was stopped early.

## 2. Why 1.3 is a real ceiling, not a round decimal

1.3 looks like the sort of bound somebody picks to keep a table small, and it
is not. Sac-Épée §1.3 gives the reason, and it is worth having on the page:

- The plastic constant $\theta_0 = 1.324717\ldots$, the root of $x^3-x-1$, is
  the smallest Pisot number and the smallest known limit point of the Salem
  numbers. Salem's construction produces a sequence of Salem numbers rising to
  it, so **there are infinitely many Salem numbers below $\theta_0$.**
- Therefore no threshold at or above $\theta_0$ gives a finite table, and any
  threshold below it gives a finite *known* list only. 1.3 is the traditional
  round number safely under the wall.

So the family this table holds is genuinely bounded, and the bound is within
0.019 of a hard mathematical ceiling. Whatever else is done, this table will
never be large. That is the good kind of small: a named, closed list.

## 3. The one available move: 1.3 → 49/37

Reference [1] on the page is Sac-Épée, *Salem numbers less than 49/37* (2025).
$49/37 = 1.3243243\ldots$, chosen to sit just under the plastic constant — it
is the largest published bound short of the wall. Its Table 1 lists the 25
Salem numbers found between 1.3 and 49/37: 15 already known, 10 claimed as new.

I checked all 25 the same way the generator checks the 47 — rebuild the
reciprocal polynomial from the half-list, test irreducibility, test the Salem
root pattern, isolate the real root above 1 in interval arithmetic
(`/tmp/check_extension.py`, run through `agents/sage.sh`):

    all 25 rows check out as Salem numbers in (1.3, 49/37)
    new entries would add about 7308 bytes; largest entry about 424
    degrees: [12,12,14,14,16,16,18,18,20,22,22,22,22,22,24,26,26,28,30,32,32,36,38,40,44]

Every row is irreducible, reciprocal, has exactly one conjugate outside the
unit circle and one inside with the other $d-2$ on it, lies strictly inside
$(1.3,\,49/37)$, and is distinct from all 47 already held. The Salem test was
done exactly, on the trace polynomial $g$ with $f(x)=x^{d/2}g(x+1/x)$, by
counting real roots in $[-2,2]$ and above 2 — no numerical decision anywhere.
*(Sage's `QQbar` route crashes in this image: `abs(root) > 1` on an algebraic
number raises `NameError: name 'RR_1_10' is not defined` from
`sage/rings/qqbar.py`. The trace-polynomial test is better anyway.)*

**What that would cost.** 47 → 72 entries, 20,125 → about 27,400 bytes. Six
percent of the entry limit, nine percent of the block limit. The largest new
entry is about 424 bytes, in line with the degree-46 row already there. Size
is not an argument against it in either direction.

**How complete it would be** — and this is the part worth saying precisely,
because the extended table's `complete-note` almost writes itself:

- For **degree at most 24** the extension is *certified complete*. Mossinghoff
  publishes complete lists of Salem numbers of each fixed degree up to a bound
  $M$, and every one of those bounds exceeds 49/37 (degree 4 up to 3, …,
  degree 22 up to 1.5, degree 24 up to 1.4). I counted the members of those
  eleven lists lying in $(1.3,\,49/37)$: 2, 2, 2, 2, 1, 5, 1 for degrees 12,
  14, 16, 18, 20, 22, 24 and none below degree 12 — **15**, matching
  Sac-Épée's 15 non-new rows value for value. The same lists independently
  reproduce the 29 members of the current table with degree at most 24.
- Below 1.3, complete to degree 44 (Mossinghoff–Rhin–Wu), as now.
- The 10 rows of degree 26 to 44 rest on one random-sampling search in a
  preprint. Their *values* do not: I verified each exactly, so nothing
  unproven enters the table's numbers. Only the claim "there are no others"
  weakens, and it is already weak.

## 4. If somebody does it, five things that will bite

Ranked by how much damage each does if missed.

**1. The generator no longer reproduces the table. Fix this first.**
`agents/critiques/T284-repaired.md` records that the repair pass rewrote nine
entry comments through the API: five Coxeter-triangle rows, four
Mossinghoff-discovery rows. Those nine now read as sentences — *"This Salem
number has degree $10$, with minimal polynomial … It is Lehmer's number and
the growth rate of the Coxeter triangle group $\Delta(2,3,7)$."* — while
`entry_comment()` in the generator still produces the old fragment form
*"degree $10$; minimal polynomial …; this is Lehmer's number."*. On the live
page 9 comments are sentences and 38 are the generator's fragments. **A
`generate.py --publish` run to add rows would silently revert all nine**,
undoing findings 1 and 3 of the last critique. Port the repaired prose into
`entry_comment()` before adding a single row.

**2. Sac-Épée's decimals are rounded; Mossinghoff's are truncated.** The
generator's `check_source_truncation()` would reject 11 of the 25 new rows —
not because anything is wrong, but because the paper rounds at the twelfth
decimal while `SalemList.html` says in its own footer "Salem numbers are
truncated, not rounded". The paper states it follows Mossinghoff's
presentation; on this point it does not. All 11 pass once the check allows a
nearest-value reading, and all 25 then agree with the computed root. The
generator needs the convention recorded per source, not assumed.

**3. It is a retitle, so it is a person's decision.** The bound is in the
title, and the title is the claim. The address survives: `editing.py:480`
freezes the slug at publication, so a published T284 keeps
`/Salem_numbers_less_than_1_3` — the 48 `HREF{Salem_numbers_less_than_1_3}`
links from T301 (one per row, plus the similar-table link) keep working. The
cost is cosmetic and permanent: the address would say 1.3 forever while the
page said 49/37.

**4. T301 has to move in lockstep.** "Minimal polynomials of the Salem numbers
less than 1.3" holds the same 47 rows under the same coefficient keys and
links to this table row by row. Extending one and not the other leaves two
tables of the same family disagreeing about what the family is.

**5. Keep the 47 visible in the note.** "The 47 small Salem numbers" is the
phrase the literature uses and the thing most readers arrive holding. If the
table grows to 72, the `complete-note` should still say which 47 are the
classical list below 1.3 — otherwise a reader checking the table against
Mossinghoff counts 72 and thinks one of them is wrong.

## 5. What I would do

**Extend it, as one operation with T301 — but it is a retitle and therefore a
person's call, and leaving it alone is defensible.**

For: a reader who computes 1.3082710855… today gets "No match in database",
and the answer exists, is published, and is exactly verifiable. After the
move, the table's range would end where the mathematics ends rather than at a
round decimal, and it would be, for degrees up to 24, a *certified complete*
statement — which the present table is only for degrees up to 44 *and* below
1.3. 25 more rows, 7 KB, no limit approached.

Against: the 47 below 1.3 are a canonical object with a canonical name, and
the ten degree-26-to-44 additions come from one unrefereed preprint's search.
A table that stops at the standard bound is never wrong about what it is.

**Do not** reach for the other lists on that site as growth. Mossinghoff's
eleven fixed-degree lists hold 1,741 Salem numbers up to bounds as high as 3 —
past the entry soft limit, and bounded by degree rather than by value. That is
a different family under a different criterion, exactly the mixing the build's
idea note warned against, and if anybody wants it, it is a new table.

## What reads well, since I went looking

The two things I checked hardest and could not fault:

- **The completeness note is the best I have read in this corpus.** It says
  what is held (47, Mossinghoff's list), what is proved (complete to degree
  44), which row lies outside the proof (the degree-46 one), and what a later
  search found (all 47 again, nothing new). Every clause of it survived being
  checked against three of Mossinghoff's lists and the preprint. The skill
  asks the note to say what the table *does* cover; this one does, and names
  its evidence.
- **The generator earns its `proven`.** It treats the source decimals as a
  check and not as data, rebuilds each polynomial exactly, and refuses a row
  that is reducible or has the wrong root pattern. That is why the extension
  is cheap: the hard part is already written, and the 25 new rows go through
  the same gate I put them through by hand.
