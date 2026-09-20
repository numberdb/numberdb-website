# T293, *Regulators of elliptic curves over real quadratic fields* — can it grow?

Read on 2026-09-20 as a reader: the rendered page at `https://numberdb.org/T293`,
the live document from `GET /api/table?id=T293`, `GET /api/table/T293/audit`,
the four tables `Similar tables` points at, and the pinned `ecnf-data` commit
`10b28418e80392032b106ea00e6c5aa109d28e7b` recounted from scratch. Nothing was
changed.

**The brief said 32 entries in 13825 bytes. That is stale by a wide margin.**
The live table holds **1171 entries** in a **279,665-byte** entries block. It is
not a tenth of the soft limits; it is 98% of the 1200-entry soft limit and 87%
of the 320 KB block limit.

## The answer

**It cannot grow, and it should not.** Every axis the definition leaves open
costs hundreds of entries the first step you take along it:

| step | entries it would add |
|---|---|
| conductor norm 250 → 255 (the next round value) | +42, total 1213, over the soft limit |
| a seventh field, $D=24$, at $N\leq250$ | +577 |
| the cheapest seventh field, $D=29$, at $N\leq250$ | +285 |
| far enough to reach a rank-2 curve over $D=5$ ($N\leq1831$) | total 17,643 |

The table's own stopping argument checks out exactly. Recounting the pinned
source: $N\leq250$ gives **1171**, $N\leq255$ gives **1213**, the first rank-2
curve among the six fields is over $D=21$ at conductor norm **235**, and
$\{5,8,12,13,17,21\}$ are indeed the six real quadratic fields of smallest
discriminant. Three numeric claims, three matches. The audit is clean, the page
renders with no maths faults, the value column is headed `$R_{E/K}$` rather
than the word `value`, and the parameter block states the family (`positive
fundamental discriminant`) rather than this run's six values, which is what the
skill asks. I checked those hardest and found nothing to report.

So "how far could it go" has an answer that is not about T293 at all. What the
family has left to give lives in two places, and neither of them is a longer
T293.

---

## 1. The two halves of the BSD formula are cut on different rules, and only a quarter of the rows pair up — worth doing

`Similar tables` offers *Special $L$-values of elliptic curves over real
quadratic fields* as "the $L^*(E/K,1)$ side of the Birch and Swinnerton-Dyer
formula". Formula (1) on this page is that formula, with $R_{E/K}$ and
$L^*(E/K,1)$ both in it. A reader who wants to use (1) needs one row from each
table.

They can do that for **309 of the 1171 rows**. T293 covers six fields at
$N\leq250$; the $L$-values table covers five fields at $N\leq150$. Every row
over $D=21$, and every row over the other five fields with conductor norm
between 151 and 250, has no counterpart.

The fix is not on this page, and the direction is the opposite of "extend
T293": the $L$-values table holds 572 entries in 111 KB and has most of a table
of room. Recounting isogeny classes in the same pinned source (my count
reproduces its 572 exactly, so the rule is the one stated):

* five fields, $N\leq250$: **1141** classes
* six fields, $N\leq200$: **1058** classes
* six fields, $N\leq250$: 1433 classes, over the soft limit

So either of the first two brings the companion into step within the limits,
and the second is the one that adds $D=21$. Alternatively T293 itself could be
recut to five fields at $N\leq250$ (823 rows, and room to spare) — but that
drops $D=21$, which is where its only rank-2 rows are, so I would not.

This is a proposal for whoever owns the pair, not an edit to T293.

## 2. Rank is the axis this range rule cannot reach at all; that is a sibling table — worth doing

**1163 of the 1171 rows are rank 1.** Eight are rank 2, all over $D=21$. There
are no others, and the reason is arithmetic rather than choice: under a bound
on the conductor norm, the first rank-2 curve appears at norm 235 over $D=21$,
478 over $D=17$, 637 over $D=13$, 814 over $D=12$, 1031 over $D=8$ and **1831**
over $D=5$. A range that reached rank 2 in every one of its six fields would
carry 17,643 rows, fifteen times the soft limit. No conductor-norm bound will
ever do it.

Selecting on rank instead does it immediately. In the pinned source, over these
same six fields, there are **exactly 1330 curves of rank 2** — and none of rank
3 or above, so that is the whole of what the source has. At the 239 bytes an
entry this table averages (flat across conductor norm, measured: 235 bytes at
norms under 100, 240 at norms near 250), 1330 entries is about 318 KB, which is
at the block limit; the first 1199 of them by conductor norm reach $N\leq4672$
and cost about 287 KB, which is the same shape as T293 today.

The corpus already splits this subject that way: the three tables T293 links
over $\mathbb{Q}$ are rank 1, rank 2 and rank 3 separately, at 1007, 955 and
1061 entries. A *Regulators of rank-2 elliptic curves over real quadratic
fields* is the natural continuation of T293, it is nearly complete relative to
its source rather than truncated by a limit, and creating it is a person's act,
not a generator's.

## 3. Say what the shape of the range is, where a reader can see it — worth doing, small

Per field, the table holds 17, 63, 253, 195, 295 and 348 rows for
$D=5,8,12,13,17,21$. A reader working over $\mathbb{Q}(\sqrt5)$ — the first
real quadratic field anybody meets — sees seventeen rows and a table claiming
six fields, and has no way to tell whether their curve is absent because the
range stops short or because there is nothing there.

Comment (7) holds the explanation and does not finish it:

> In the pinned ecnf-data source, the smallest conductor norms among
> positive-rank curves over $D=5$ and $D=8$ are $199$ and $103$.

Two faults, both small. It pairs its numbers by position, which is the thing
the skill asks authors not to do: the reader has to match 199 to $D=5$ and 103
to $D=8$ by counting. And it stops one clause before the point. Smallest
change:

> In the pinned ecnf-data source, the smallest conductor norm among
> positive-rank curves is $199$ over $D=5$ and $103$ over $D=8$, so the bound
> of $250$ leaves $17$ rows over $D=5$ and $348$ over $D=21$.

That sentence is what somebody holding a regulator over $\mathbb{Q}(\sqrt5)$
came to the page to read.

## 4. The repository copy of the table is behind the live one — worth doing

`generators/regulators-elliptic-curves-real-quadratic-fields/` is where the
next person to extend this table starts, and it would walk them backwards:

* `table.yaml`'s `complete-note` is the short form, without the rank-2 and
  soft-limit clauses the live note carries.
* `table.yaml` still glosses the $L$-values table as "for the same ecnf-data
  **curves**"; the live document says "for elliptic curves from the same
  ecnf-data source". The live wording is the true one — as §1 measures, only
  309 of 1171 rows are shared — and republishing from the checked-in YAML would
  put the false claim back.
* `curve_data.py` is 660 KB of records that `generate.py` does not import (it
  fetches from the pinned commit at run time), and its docstring says the table
  uses "$D$ in {5, 8, 12, 13, 17}" — five fields, not six. It is a stale copy
  that disagrees with the table it sits beside.

## 5. Noted only

**Rebalancing to equal depth per field.** Somebody will propose it, so here are
the numbers: 195 curves in each of the six fields (total 1170, the same size)
needs conductor-norm bounds of 655, 361, 213, 244, 188 and 153 for
$D=5,8,12,13,17,21$. I do not recommend it. "Conductor norm at most 250" is a
rule a reader can apply to their own curve; "the first 195 per field" is a
count, and the skill's own advice is to let the mathematics choose the range
rather than the count. The present bound is the more defensible of the two,
and finding 3 is what it needs instead.

**$N\leq250$ is round, not extremal.** $N\leq254$ gives 1195, still inside the
soft limit. Twenty-four rows is not worth a revision, and 250 is the better
number to print.

**Do not trim the entry comments to make room.** They hold the conductor ideal,
the rank and the Weierstrass equation, none of which is anywhere else in the
row, and they are about 155 of the 239 bytes an entry. Dropping them would take
the block from 279 KB to roughly 98 KB and buy nothing, because what binds here
is entries (1171 of 1200), not bytes.

**The completeness note explains itself in the site's own terms.** It ends
"above the $1200$-entry soft limit", which is a fact about NumberDB's
configuration rather than about elliptic curves, and a reader checking whether
their curve belongs here does not know what it means. The mathematical half of
the clause — that the range reaches the first rank-2 curves — is the half that
serves them. Low priority, and arguable: the clause was added deliberately, and
a stated reason for a range is what the skill asks for.

---

## Counts, so the next reader need not redo them

Live table: 1171 entries, 279,665 bytes (YAML), against soft limits of 1200 and
320 KB. Per field: $D=5$ 17, $D=8$ 63, $D=12$ 253, $D=13$ 195, $D=17$ 295,
$D=21$ 348. By rank: 1163 of rank 1, 8 of rank 2.

Pinned `ecnf-data` at `10b28418e80392032b106ea00e6c5aa109d28e7b`, six fields,
positive rank: 37,573 curves in all, of which 1171 at $N\leq250$, 1195 at
$N\leq254$, 1213 at $N\leq255$, 1639 at $N\leq300$, 3577 at $N\leq500$. Rank 2:
1330 curves, none of rank 3 or more. The commit holds **130** real quadratic
fields; the table uses six.

Companions: *Special $L$-values* 572 entries / 111 KB; *Regulators over
$\mathbb{Q}$* of rank 1, 2, 3 at 1007 / 955 / 1061 entries and 217 / 211 /
241 KB.
