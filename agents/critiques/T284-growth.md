<<<<<<< HEAD
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
=======
# T284 growth: the 47 are everything anybody has found, and the ceiling is a cut in an infinite family

Read on 2026-09-20 (04:4x–05:2x UTC). **The table is complete in the only
sense available to it, and it was not stopped early.** Its definition promises
the Salem numbers below $1.3$; it holds the 47 that are known; the list is a
theorem up to degree $44$; and the searches that went past that degree went a
very long way past it and found nothing. A 48th row is a research result, not
a computation somebody here can run.

There is room above the ceiling rather than below it, and it is real: 25 Salem
numbers between $1.3$ and $49/37$ are published, and I rebuilt and verified
every one of them. Taking them would change the table's subject, not extend
its range, and §3 says what it would cost and what I would want said first.
My recommendation is to leave the range where it is and fix one sentence.

## 1. Why the range stops at 1.3, and why no range can go much further

The bound is not this afternoon's computation and it is not a size target. It
is the largest round number below an obstruction:

* The **plastic number** $\theta_0=1.3247179\ldots$, the real root of
  $x^3-x-1$, is the smallest Pisot number. Salem's construction turns any
  Pisot number into two sequences of Salem numbers converging to it, one from
  below, and Boyd proved every Salem number lies in such a sequence
  (Sac-Épée §1.3, citing Salem 1963 and Boyd 1977).
* So Salem numbers **accumulate at $\theta_0$ from below**: the set below
  $\theta_0$ is infinite. Any table of Salem numbers must cut strictly below
  $1.3247\ldots$, and every threshold is a cut rather than the whole family.

I watched the cut happen. Running Salem's construction on $p(x)=x^3-x-1$, the
Salem factors of $x^kp(x)-p^*(x)$, where $p^*(x)=x^3p(1/x)=1-x^2-x^3$, climb
toward $\theta_0$:

    k=11  degree   8  1.28063815626775759670   T284 row 23
    k=12  degree  10  1.29348595312545410651   T284 row 41, the table's top row
    k=13  degree  12  1.30226880509433446296   first row above the ceiling
    ...
    k=26  degree  28  1.32423131986191797672   last row below 49/37
    k=27  degree  20  1.32435129626712042497   above 49/37
    k=33  degree  34  1.32465047007915778919   still climbing toward 1.32471795...

T284's largest entry is $k=12$ of this one sequence and its ceiling falls in
the gap before $k=13$. That is the honest shape of the range: not "we computed
this far", but "the family is infinite and this is where the literature cuts
it". `complete-note` does not say so, which is finding 1.

Two further facts about the interval, worth having in one place:

* Below $\theta_0$ every irreducible non-cyclotomic integer polynomial is
  reciprocal (Smyth 1971), so below $1.3$ the Salem numbers and the Lehmer
  problem are the same subject. That is why one search serves both.
* Nothing proves the set below $1.3$ is *finite*. Every completeness result I
  read is bounded by degree. Boyd's expectation that the 47 are all of them is
  a conjecture, and the table is right to say `complete: no`.

## 2. Is anything missing below 1.3? Three checks, and no

The table's own note cites Mossinghoff's list and the degree-$44$ theorem. I
checked the row set against everything else that author published and against
the one independent search.

**(a) The certified fixed-degree lists.** Mossinghoff publishes eleven
*complete* lists of Salem numbers of fixed degree up to a bound: degree 4 to
$M=3$, degree 6 to $2.8$, 8 to $2.6$, 10 to $2.4$, 12 to $2.2$, 14 to $2$, 16
to $1.8$, 18 and 20 to the golden ratio, 22 to $1.5$, 24 to $1.4$ (1741 Salem
numbers in all). Filtering them at $1.3$ gives 29 numbers, in degrees
$8,10,12,14,16,18,20,22,24$ with counts $1,5,1,4,1,7,4,4,2$. T284 holds
exactly 29 entries of degree at most 24, with exactly those counts, and every
value agrees to about 13 digits, which is what those files carry: they print
14 decimals, rounded where T284's own source truncates, and five of the 29 are
off in the 14th place, the worst by 7 units. That is the files' precision, not
a disagreement. So the small-degree half of
the table is backed by a completeness result per degree, not only by the
degree-$\leq44$ theorem.

**(b) The degree-180 list.** `Known180.gz` holds 8438 known irreducible
non-cyclotomic polynomials of degree at most 180 with Mahler measure below
$1.3$, with a column counting roots outside the unit circle. Exactly **47** of
the 8438 have one root outside, which is what makes them Salem; the degree
multiset of those 47 is identical to T284's. 7388 of the 8438 have degree
greater than 46 and not one of them is Salem — the degree-48 and degree-52
polynomials found by Rhin, Mossinghoff and Wu in 2008, which one might expect
to be the next Salem numbers, have 2 and 3 roots outside the circle. People
have searched to degree 180 for small measure; the Salem numbers stop at 46.

**(c) The one independent search.** Sac-Épée's integer-programming search
sampled degrees up to 64, rediscovered all 47 repeatedly, and found no
others (§3.2, §4). That is the only check here that is independent of
Mossinghoff: (a) and (b) are different files by the same author, and I should
not call them independent evidence.

## 3. The growth that exists: 25 numbers between 1.3 and 49/37

Sac-Épée's table (arXiv:2409.11159v3 §3.2) lists 25 Salem numbers in
$(1.3,\,49/37)$, 15 of degree at most 24 that were already known and 10 new
ones of degrees 26 to 44. I rebuilt all 25 from their coefficient halves and
checked each in interval arithmetic: **all 25 are irreducible reciprocal
polynomials with exactly one root outside the unit circle, and all 25 roots
lie strictly between $1.3$ and $49/37$.** The 15 of degree $\leq24$ match
Mossinghoff's certified fixed-degree lists exactly. So the material is sound
and the work is transcription.

What taking it would mean:

* **72 entries, about 24 KB of entries block** (the 47 cost 15.5 KB; the 25
  new rows average degree 24 and would cost about 8.5 KB). 6% of the entry
  limit and 7% of the block limit. Size is not what decides this.
* **The title changes**, and with it what search reaches. "Small Salem number"
  is a term of art meaning $\tau<1.3$; a table called "Salem numbers less than
  $49/37$" is named after one paper's cut, 3 parts in $10^4$ below $\theta_0$,
  and the next member of the plastic sequence misses it by $2.7\times10^{-5}$.
  A reader holding $1.3244$ would be outside a table that looks like it should
  hold them.
* **The completeness note becomes three-tier**: proved complete for degree
  $\leq44$ below $1.3$; proved complete for degree $\leq24$ throughout the new
  range, by the fixed-degree lists; a sampling search to degree 64 and nothing
  at all above that. Writable, but it is three sentences where there is now
  one.
* **T301 moves with it.** The minimal-polynomial table is keyed by the
  same coefficient halves, row for row, and a ceiling raised in one table and
  not the other leaves two tables that no longer line up.
* **The generator needs one real change**, not just more rows: see finding 2.

I would not do it. The gain is 25 real numbers a reader could plausibly hold;
the cost is a table named after a threshold with no standing, whose most
interesting region — the approach to $\theta_0$ — is exactly where nobody can
say what is missing. If the corpus wants those numbers, the better shape is
in finding 3.

## Findings, ranked

### 1. `complete-note` says how much is here but not why the range ends where it does. Worth doing, small.

The note reads: "it holds the 47 known Salem numbers below $1.3$ in
Mossinghoff's list. The list is proved complete for degree at most $44$. The
one degree-$46$ entry lies outside that range, and a later random-sampling
search rediscovered all 47 and found no others below $1.3$."

Every clause is true and it is a good note. What it does not answer is the
question a reader asks *next*: why $1.3$, and what is just above it. As
written, $1.3$ reads like a round number somebody chose, and the skill asks
that the sentence carrying the range be the argument for it.

Fix: one clause, in `Comments` rather than in the note, which is already
long. For example: "Salem numbers below $1.3$ are called small. The bound
cannot be raised far: the Salem numbers accumulate from below at the plastic
number $1.3247\ldots$, the smallest Pisot number CITE{SacEpee}, so there are
infinitely many below it." That also tells the reader with $1.31$ in their
hand that their number is probably a Salem number and is not here, which is
the most useful thing the table can say to them.

### 2. The generator's source check is written for truncated decimals, and the only source of new rows rounds. Worth doing if and only if the range moves.

`check_source_truncation` demands that the isolated root lie in
$[d,\,d+10^{-k})$ for the printed decimal $d$. That is right for Mossinghoff,
whose page says "Salem numbers are truncated, not rounded". Sac-Épée's table
rounds: of his 25 rows, all 25 agree with my recomputation as roundings and
only 14 as truncations. Transcribing his rows into the generator unchanged
would make 11 of the 25 raise `ArithmeticError` with a message saying the root
is not inside the source interval, which reads like a wrong value and is not.

Fix, if the rows are ever taken: check against a half-unit interval for that
source, and record which convention each source uses beside its rows. Nothing
to do while the table's range is unchanged; noted here because it is the trap
waiting at the front of that work.

### 3. Where the appetite for more Salem numbers should go: a table indexed by degree. Noted, for somebody else's decision.

The eleven certified fixed-degree lists are 1741 Salem numbers, each list
complete up to a stated bound. That is a different table from this one — the
range is bounded by *degree*, with a theorem behind each row's presence, and
no cut through an accumulating family. Degrees 4 to 14 alone are 1073
entries, which lands inside the soft limit without a size exception; the whole
thing at 1741 would need one. The interesting design question is that the
bound $M$ varies with the degree (3 down to 1.4), so the range is ragged by
construction and the completeness note would have to carry the table of
bounds. It is a good table and it is not this table's growth.

### 4. Noted only

* **The brief's "20125 bytes" is 19805 as the API returns the document
  today**, of which the entries block is 15.5 KB. Nothing has changed the
  table since the critique of it was acted on; the difference is what the
  figure counts.
* **The degree-$46$ row is the one entry outside every completeness
  statement**, and `complete-note` already says so. Worth keeping exactly as
  it is: it is the row most likely to be joined by a neighbour if anybody ever
  searches degree 48 to 180 for Salem polynomials specifically rather than for
  small measure generally.
* **`audit_table` (via `GET /api/table/T284/audit`) returns
  `findings: [], clean: true`.** I agree with it here. It has nothing to say
  about range, which is the whole subject of this report: a table that holds
  three members of a thousand-member family and one that holds all 47 of 47
  look the same to it.

## What I checked hardest, and it was fine

* **That the 47 are all the Salem numbers anybody has published below 1.3.**
  Three ways, in §2. The strongest is the root-count column of the degree-180
  list: 8438 small-measure polynomials, 47 of them Salem, degrees matching
  T284 row for row.
* **That the 25 rows above the ceiling are really Salem numbers in the
  window.** Not taken from the paper's word: each polynomial rebuilt from its
  coefficient half, checked reciprocal and irreducible, and passed through the
  trace polynomial $Q$ with $P(x)=x^dQ(x+1/x)$, where the Salem condition is
  that every root of $Q$ is real with exactly one above $2$ and the rest
  inside $(-2,2)$. Root counts by Sturm sequence, so the counts are exact.
* **That Sac-Épée's list has no visible gap.** Salem's construction on the
  plastic number produces 14 Salem numbers in $(1.3,\,49/37)$ — more than half
  the window's known content is the tail of this single sequence — and all 14
  are in his table. The same construction on $x^4-x^3-1$, the next Pisot
  number, produces nothing in the window and stops below $1.3$ at $1.28063\ldots$,
  which is T284's degree-8 row. This is a probe and not a proof: Boyd's theorem
  says every Salem number comes from *some* Pisot number, and I tried two.

## How this was read

* The rendered page (`https://numberdb.org/T284`) and the document
  (`GET /api/table?id=T284`), and the generator at
  `generators/salem-numbers-less-than-1.3/generate.py`.
* Sac-Épée, *Salem numbers less than 49/37*, arXiv:2409.11159v3, read in full
  from the arXiv HTML rather than from memory — §1.3 for the history of the
  47 and the certifications, §2 for the method, §3.2 for the table and the
  degree range searched, §4 for what the author does and does not claim.
* Mossinghoff's lists, from the Internet Archive copy the table already links:
  `SalemList.html` (the 47), `Known180.gz` (8438 rows with a root-count
  column) and `S4.txt`–`S24.txt` (the eleven certified fixed-degree lists).
  The site itself is gone; `web.archive.org` answers directly from this
  runner.
* Sage, through `agents/sage.sh`, three runs: verification of the 25 candidate
  rows, Salem's construction on two Pisot numbers to degree 90, and the
  truncation-versus-rounding test. Scripts in `/tmp/t284growth*.py`.
* Nothing was written to the table, and nothing was published.
>>>>>>> origin/campaign/w3
