# Can T293 grow? "Regulators of elliptic curves over real quadratic fields"

Read on 2026-09-20 against the skill as served at <https://numberdb.org/skill>
that day (fetched fresh).

**How it was read.** The SOCKS proxy on 127.0.0.1:1080 refused every
connection, as `docs/agent-environment.md` records at length, so `/skill` and
`/T293` were fetched direct (200, 48,740 and 890,234 bytes). The document came
from `numberdb.table('T293')` through `clients/python`. `GET
/api/table/T293/audit` with the zeta3 key returns `"findings": [], "clean":
true` — the HTTP 500 recorded in the 2026-09-17 critique is gone. The source
counts below were recomputed from ecnf-data at the pinned commit
`10b28418e80392032b106ea00e6c5aa109d28e7b`, reading the `mwdata` files for
fourteen real quadratic fields directly.

**The premise of this run is false and was already known to be.** I was asked
whether a table of "32 entries in 13825 bytes" could grow. It holds **1171
entries in 279 KB**. That figure comes from `agents/review-queue.tsv:294`, a
snapshot committed before the repairs of 2026-09-19; the staleness is written
up under "The growth queue selects from a committed snapshot, and the snapshot
goes stale" in `docs/agent-environment.md`, and a growth pass on the same table
has already been done and its repairs recorded in `T293-growth-repaired.md`. I
have not repeated that note.

## The answer

**T293 is finished. It cannot grow, and the reason is sound.** It sits at
97.6% of the 1200-entry soft limit and 87% of the 320 KB block limit, and both
axes of growth — more curves, or more digits on the curves it has — are closed
by those limits rather than by anything about the mathematics. Nothing here
needs doing to the range.

What follows is the arithmetic behind that, because the prior passes reported
the two endpoints (250 → 1171, 255 → 1213) and nobody checked between them.

---

## 1. The headroom is 24 entries, and it is at conductor norm 254

The table stops at conductor norm 250. The bounds in between, over the six
fields $D\in\{5,8,12,13,17,21\}$, counted from the pinned source:

    N <= 249    1171        N <= 252    1189
    N <= 250    1171        N <= 253    1189
    N <= 251    1177        N <= 254    1195
                            N <= 255    1213   over the soft limit

So the largest bound that fits is 254, and it buys 24 rows, a 2% extension,
at the price of a cutoff no reader would recognise as a choice. 250 is the
right place to stop. My count at 250 is 1171 and at 255 is 1213, both exactly
matching the live table and its `complete-note`; the note's arithmetic is
correct.

Every larger step overshoots, and not narrowly:

    N <= 260 over six fields      1305
    N <= 300                      1639
    N <= 500                      3577
    the next field, D = 24, at N <= 250     +577  (to 1748)

There is no method by which this table reaches 1300 entries and stays a table
this corpus wants. Growth here means a `Size exception`, and a size exception
is a person's decision, not a generator's.

## 2. It cannot deepen either, which is the part that has not been said

The entries block is 279 KB against a 320 KB soft limit. The values are kept
to 35 significant digits, 43 KB in total. Taking them to the 100 digits the
skill treats as the house precision would add about 76 KB and put the block at
**355 KB, past the soft limit** — so the table could not be made more precise
even if it were made no larger.

That is academic in any case: `rigour details` says the final digits of
ecnf-data's `reg` field are not stable, which is why 35 was chosen. More digits
would mean recomputing 1171 height-pairing determinants in Sage from the
recorded generators, not transcribing further. That is a new computation with a
new rigour level, not an extension, and it would not fit.

So both doors are shut, and the table is in the unusual position of having no
cheap direction at all. Worth saying plainly in a growth report, because the
default assumption for a table under the limits is that one of the two is open.

## 3. Why the ceiling arrives at so small a conductor bound

1171 rows hold **569 distinct values**. 1093 of the rows — 93% — share their
number with at least one other row.

    D      rows   distinct
    5        17         10
    8        63         33
    12      253        126
    13      195         93
    17      295        130
    21      348        177

This is not a fault, and the table says why: comment (2) records that a curve
and its Galois conjugate have the same regulator, and the row is keyed by the
curve, so both belong. A reader who searches 0.0397... should be told both
curves it came from. But it is the fact a person weighing a size exception
would want in front of them: **the entry budget buys about half as many
searchable numbers as rows**, and that is why 1200 is reached at conductor
norm 250 rather than somewhere near 500.

It also disposes of the obvious way to make room. Dropping conjugate rows would
free roughly 600 entries and would make the table lie about which curves have a
given regulator. Don't.

For completeness on the source side: ecnf-data itself stops at conductor norm
988 for $D=17$ and 1989 for $D=13$, so a range over these six fields becomes
ragged for a reason about the source somewhere above 988. The corpus limit
binds at 255. The source ceiling never comes into it.

---

## Worth doing: one clause

### The completeness note argues the range from above and not from below

**What a reader sees.**

> Table is complete: no (it holds every positive-rank curve in ecnf-data over
> the six real quadratic fields of smallest discriminant,
> $D\in\{5,8,12,13,17,21\}$, with conductor norm at most $250$; this cutoff is
> deliberate, since the same source gives $1213$ entries at conductor norm
> $N\leq255$, above the $1200$-entry soft limit)

**Why it is wrong.** The skill asks the completeness note to carry the argument
for the range: "none of them is a reason for any particular number to be
present". As written, the whole reason 250 is 250 is the soft limit — a fact
about this website, in the field where a reader checks whether their own number
belongs here. The mathematical half of the argument exists and the table
already knows it: comment (7) records that the smallest conductor norms among
positive-rank curves over $D=5$ and $D=8$ are 199 and 103. That is what forces
the bound *up*. At $N\leq150$ the table would hold no curve over
$\mathbb{Q}(\sqrt5)$ at all, and at $N\leq200$ it would hold six. The bound is
squeezed between 199 below and the soft limit above, and there is almost no
room between them. That is a good argument and a much better sentence than the
one there now; comment (7) states the fact without saying what it is for.

**Smallest fix.** Add the lower half to `complete-note`, before the existing
clause: "the bound is above $199$ so that $\mathbb{Q}(\sqrt5)$ is represented,
since that is the smallest conductor norm at which it has a curve of positive
rank". Then comment (7) is the supporting fact and can stay as it is.

---

## Noted only

### Two of the three attached files are stale, and the bigger one contradicts the table

`/files/T293` offers three files for download together: `generate.py` (8,484
bytes, the one that made the numbers), `curve_data.py` (660,880 bytes) and
`t293_generate.py` (8,215 bytes).

* `curve_data.py` holds 823 curve records over **five** fields —
  $D\in\{5,8,12,13,17\}$, no $D=21$ — and its docstring says so: "The table
  uses every positive-rank curve over D in {5, 8, 12, 13, 17}". The table has
  six fields and 1171 rows. `generate.py` does not import it; it reads
  ecnf-data over the network. It is the snapshot of the intermediate 823-row
  state, left behind when $D=21$ was added.
* `t293_generate.py` is `generate.py` with single quotes, a working copy from
  the same repair run.

So "Download the table and its files together — as of this version, so the code
in it is the code that produced the numbers in it" hands a reader 677 KB of
which 8.5 KB is true, and the largest file tells them the wrong range. The skill
says `generate.py` "is the program that reproduces and extends *this* table".
Detaching the other two is the fix. I have ranked this below the clause above
only because it is invisible from the table page; on the files page it is the
first thing you see, and a reader who trusts `curve_data.py` will conclude the
table stops at $D=17$.

### The entry comment restates the row's own address

Every comment opens "LMFDB curve 2.2.5.1-199.1-c1 has ...", where `5` and
`199.1-c1` are the row's two parameter values and comment (2) already explains
how to assemble the full label. That prefix is 39,548 characters, 14% of the
entries block. 1163 of the 1171 comments also carry "rank $1$", which
`rigour details` states once for all but the eight rank-2 rows over $D=21$.

I am noting this and not recommending it. The block is not the binding limit —
entries are — so shortening the comments buys no growth, and the conductor
ideal and Weierstrass equation in the rest of each comment are exactly what a
reader holding a regulator came for. It would only matter if somebody ever
wanted the 100-digit version in §2, where it is the one lever that would make
it fit.

---

## What I checked and found sound

* **The completeness note's arithmetic.** Independently recounted from
  ecnf-data at the pinned commit: 1171 rows at $N\leq250$, 1213 at $N\leq255$,
  577 more from $D=24$. All three match what the table and the prior repair
  claim.
* **Comment (7)'s claim** that the smallest positive-rank conductor norms over
  $D=5$ and $D=8$ are 199 and 103. Both confirmed against the source.
* **The per-discriminant raggedness is the mathematics, not a stopped run.**
  $D=5$ contributes 17 rows and $D=21$ contributes 348 at the same bound,
  because ecnf-data has no positive-rank curve over $\mathbb{Q}(\sqrt5)$ below
  norm 199. A previous pass declined to flatten this and was right to.
* **The audit** returns `clean: true`, and I agree with it: there is nothing in
  the range or the size that a rule would catch.
* **The definition still promises more than the table holds**, and should. It
  says "real quadratic fields", of which there are infinitely many; no range
  makes this table complete, and `complete: no` with a note saying what it does
  cover is the right shape.
