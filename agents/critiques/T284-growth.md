# Can T284 grow? — "Salem numbers less than 1.3", read 2026-09-20

**Answer: no, and it should not. The table is finished at 47 entries.** Its
range is exactly what its definition promises, the shortfall against the soft
limits is not a shortfall, and the one direction in which the range could be
widened runs into a wall 0.025 away. There is real growth available in this
subject, but it belongs in a *different* table, and §4 says which one and how
big it is.

## How it was read

- **Skill**: fetched from <https://numberdb.org/skill>, 48740 bytes, and read
  on ranges (§3, "Hold the numbers that turn up", the limits table, "include
  what is common, and stop") and on where a range is recorded (§4, the
  `complete` / `complete-note` rule).
- The SOCKS proxy on 127.0.0.1:1080 is down — `curl` gets "Failed to
  connect", `ALL_PROXY` is empty and `NUMBERDB_REMOTE=local`. The site answers
  directly from this runner. `docs/agent-environment.md` already records both
  halves of this; nothing new to add.
- **Table**: `GET /api/table?id=T284` with the key, and `GET /T284`, which now
  answers 200 — it is published, no longer the draft the September critique
  read. 47 entries, 15470 bytes of entries block, no `Math input error` or
  `argument ()` in the rendering.
- **Audit**: `GET /api/table/T284/audit` → `{"findings": [], "clean": true}`.
  I agree, and it is silent on everything below: the audit has no notion of
  how far a range *could* go.
- **Generator**: `generators/salem-numbers-less-than-1.3/generate.py`. Its 47
  source rows are transcribed from Mossinghoff's page into `SOURCE_ROWS`; it
  rebuilds each reciprocal polynomial, checks irreducibility, isolates the
  root in interval arithmetic and checks the source decimal is a truncation.
- **Sources**: Sac-Épée, arXiv:2409.11159v3, §1.3, §3.2 and §4; Mossinghoff's
  archived `Lehmer/lists/` index and the eleven `S4.txt`…`S24.txt` fixed-degree
  lists behind it. Corpus context from T222, T286, T301 through `api/lookup`.
- **Not rechecked**: the 47 values. `verify` and the build already did that.

## 1. The range *is* the definition, and it is exhausted

The Definition ends "Listed are the small Salem numbers, those less than
$1.3$." There is no truncation anywhere in the table: no degree cap, no
sampling, no "computed so far". The generator enumerates a hard-coded list of
47 rows and asserts `EXPECTED_ROWS = 47` — it is a transcription, not a search
with a budget, and running it longer produces nothing.

A 48th entry would be a mathematical discovery, not a longer run. Two
independent efforts have looked for one and failed:

- Mossinghoff, Rhin and Wu (2008) certify the list complete for degree at most
  44, after Flammang, Grandcolas and Rhin (1999) got degree 40. The single
  degree-46 row is the only entry outside a proof.
- Sac-Épée's integer-programming search, sampling root separators uniformly,
  "found all known Salem numbers less than 1.3, but no new numbers less than
  this value" (§3.2), and found them repeatedly.

Both facts are already in `complete-note`, correctly, and it is the sentence a
reader holding a number near 1.29 needs. Nothing to do.

47 entries in 20 KB against soft limits of 1200 and 320 KB is not a table that
stopped early. It is a table whose subject is 47 numbers long. The skill's own
words for this case: "include what is common, and stop."

## 2. The bound cannot be raised to a round number — the plastic constant is a wall

The obvious growth move is to raise 1.3. It is blocked twice over, and the
table already says so in `comment-bound`, which I checked against the source
and found accurate.

**Mathematically.** The plastic constant $\rho = 1.3247179\ldots$, the smallest
Pisot number, is a limit point of the Salem numbers: Salem's construction turns
any Pisot number into two sequences of Salem numbers converging to it, so there
are *infinitely many* Salem numbers below $\rho$ (Sac-Épée §1.3). A table
titled "Salem numbers less than $B$" is therefore a finite object only for
$B < \rho$. At $B = \rho$ or above it is not a table at all — it is an infinite
set with no natural truncation, and the truncation you would invent ("the first
$N$") is exactly the "counting rather than choosing" the skill warns against.

**By name.** 1.3 is not a size cutoff, it is a definition: "Salem numbers less
than 1.3 are referred to as small in the literature" (§1.3). The title names a
class people use. Move the bound and the title stops naming anything, which is
the one thing §4 says a title must do.

So the entire room for growth is the interval $[1.3, \rho)$, which is
0.025 wide. §3 measures what is in it.

## 3. What is in that interval: 25 numbers, no completeness, and one reader

Sac-Épée's paper is the state of the art there, and it tabulates 25 Salem
numbers in $[1.3, 49/37)$ — $49/37 = 1.324324\ldots$, chosen as a rational just
below $\rho$. Ten are new in that paper (degrees 26 to 44); the other fifteen
were known, the ones up to degree 24 from Hare–Mossinghoff (2014) and
Mossinghoff's fixed-degree lists.

Adopting them would take the table from 47 to 72 — still a tenth of the soft
limit, so size is no objection. The objections are the two that matter:

- **The completeness statement collapses.** For the part below 1.3 the table
  can say "proved complete for degree at most 44". For the part above it can
  say nothing at all. Sac-Épée is explicit in §4: "this algorithmic approach
  does not guarantee the exhaustiveness of the table it provides." A
  `complete-note` that is a proof on one side of 1.3 and a shrug on the other
  is worse than either, because a reader holding 1.31 cannot tell which half
  of the sentence applies to them.
- **Almost nobody arrives holding one.** I checked this rather than assuming
  it. Of the 25, exactly one is a number this corpus already sees a reader
  carrying: $1.3022688\ldots$, degree 12, which is T222's `[12,3]` — the growth
  rate of the Coxeter triangle group $\Delta(2,3,12)$, the next one after the
  five already in T284. The sequence $\Delta(2,3,r)$ converges to $\rho$
  itself, which is T222's `[inf,3]`, so extending the bound to $49/37$ buys
  one more Coxeter growth rate and then runs out of them for the same reason
  the whole range runs out. The other 24 are hits from a random search.

**Verdict: do not.** One useful number is not worth trading a proof for a
shrug. If somebody wants $\Delta(2,3,12)$ findable, it is findable — it is
already in T222 with its label on it.

## 4. The growth in this subject is a sibling table, and it is proven

This is the part worth acting on. The same page T284 already cites links
"More Salem Numbers": **complete** lists of Salem numbers of each fixed even
degree, up to a degree-dependent bound $M$. I fetched all eleven and counted
them.

| degree | $M$ | rows | rows $< 1.3$ | rows $< 1.4$ | rows $< \varphi$ |
|---|---|---|---|---|---|
| 4 | 3 | 8 | 0 | 0 | 0 |
| 6 | 2.8 | 34 | 0 | 0 | 4 |
| 8 | 2.6 | 104 | 1 | 2 | 7 |
| 10 | 2.4 | 223 | 5 | 8 | 17 |
| 12 | 2.2 | 314 | 1 | 5 | 24 |
| 14 | 2 | 390 | 4 | 12 | 50 |
| 16 | 1.8 | 231 | 1 | 9 | 68 |
| 18 | $\varphi$ | 141 | 7 | 18 | 141 |
| 20 | $\varphi$ | 191 | 4 | 21 | 191 |
| 22 | 1.5 | 89 | 4 | 27 | 89 |
| 24 | 1.4 | 16 | 2 | 16 | 16 |
| **total** | | **1741** | **29** | **118** | |

Two checks that this is the same data seen from a different angle, both of
which passed:

- The 29 rows of degree at most 24 below 1.3 in these lists are **exactly** the
  29 rows of T284 with degree at most 24 — same degrees, same values, and
  matching by reconstructed half-coefficient list, not by value.
- Of the 53 distinct growth rates below $\varphi$ in T222, ten carry an
  $\infty$ label (those are Pisot, not Salem), and of the remaining 43 **all
  but one** appear in the degree-$\le 20$ lists. The exception is `[12,11]`,
  $1.6119226\ldots$, whose degree exceeds 20.

That second check is the argument the skill asks for — "whether anybody will
arrive holding one of them" — answered with a count rather than a hope. So:

**Recommended shape: "Salem numbers of degree at most 20 less than the golden
ratio."** 502 entries. Uniform bound, because $M = \varphi$ is the binding one
and every smaller degree is certified further. Proven complete, so
`rigour: proven` and a `complete-note` that is a statement rather than an
apology. Measured size: about 70 KB of bare entries at 100 digits, about 151 KB
with an entry comment of the current length on every row — under the skill's
160 KB target, and 502 lands inside the recommended 500–1000. Degree at most
20 is also Boyd's own range (*Small Salem numbers*, Duke 1977), so the title
names something.

Two smaller variants, if 502 is too much appetite:

- **"…of degree at most 24 less than 1.4"**: 118 entries, ~35 KB. The largest
  uniform bound valid across all eleven lists. Safe, small, and the weakest
  reader-service case of the three.
- **The whole of the fixed-degree lists**: 1741 entries, ~237 KB bare and
  ~518 KB with comments. This breaks the 1200-entry soft limit and the 320 KB
  block limit at once, *and* its bound is ragged — a different $M$ per degree —
  which the skill calls a sign of two tables rather than one unfinished. Don't.

Overlap to settle before building: 23 of T284's 47 rows have degree at most 20,
all of them below $1.3 < \varphi$, so a degree-$\le 20$ table would repeat
them. That is what `repeats` in `Data properties` is for, and the two tables
would want each other in `Similar tables`. It is not a reason against; T284 and
T301 already share an index this way.

## 5. Two things to fix first, whichever way it goes

Neither is a growth argument; both are obstacles the next person will hit.

**The generator has drifted from the published table.** The repairs recorded in
`agents/critiques/T284-repaired.md` were made through the API, not through
`generate.py`. The generator still emits `"degree $10$; minimal polynomial …;
this is Lehmer's number."` and the stale `"Mossinghoff marks this row as a
recent discovery"`; the live table has `"This Salem number has degree $10$,
with minimal polynomial … It is Lehmer's number and the growth rate of the
Coxeter triangle group …"` and the corrected discovery attribution. Running
`generate.py --publish` today would regress every comment the repair fixed.
Anyone extending this table — or building the sibling in §4 from the same
code — should reconcile `entry_comment` with the live text *before* running
anything. Smallest fix: port the repaired wording into `entry_comment` and
re-verify.

**The source-truncation check does not transfer.** `check_source_truncation`
asserts the root lies in `[d, d + 10^-30)` for the decimal `d` printed by
`SalemList.html` — correct there, because that page truncates at 30 places.
The fixed-degree `S*.txt` files are a different animal: they print 14 places,
they *round* rather than truncate, and they are not even accurate to 14. Over
the 29 rows I could compare against T284's exact values, the largest
disagreement is $7.0\times10^{-14}$ — e.g. degree 24 prints
`1.29174142571457` where the root is $1.2917414257145004\ldots$. About 13
digits are trustworthy, not 14. Copying the existing check across would fail on
roughly half the rows and, worse, a builder who loosened it to make it pass
without measuring first would not know where to stop loosening. The honest
check against those files is agreement to $10^{-12}$, with the polynomial —
not the decimal — as the thing being transcribed. This is written up as a
lesson proposal.

## What I checked hardest, and what I did not

Hardest: that $\rho$ really is a wall and not just where one author stopped
(Sac-Épée §1.3, read in full, and it is consistent with T222's `[inf,3]` row
being $\rho$ itself); that the fixed-degree lists are the same objects as
T284's rows and not a differently-normalised source (matched by reconstructed
polynomial, 29 of 29); and that a degree-$\le 20$ table would hold numbers
readers arrive with (42 of T222's 43 non-$\infty$ growth rates below $\varphi$).

Not checked: whether Mossinghoff's completeness claim for the fixed-degree
lists traces to a published proof. The index page asserts it plainly, and the
method is presumably Boyd's interval algorithm (*Pisot and Salem numbers in
intervals of the real line*, Math. Comp. 32 (1978)), which is in T284's
neighbourhood already — but I did not read the paper, and nobody should write
`rigour: proven` on the strength of my guess. That is the first thing to settle
if §4 is acted on.

Also not checked: the 502 entries themselves. The count comes from the source
files; the values would have to be recomputed from the polynomials, which is
what the existing generator's machinery already does well.
