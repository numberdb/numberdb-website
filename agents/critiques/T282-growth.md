# Can T282 grow? "Mahler measures of $x+x^{-1}+y+y^{-1}+k$"

Read on 2026-09-20. T282 is published and holds 101 real values $m_k$ for
$0\leq k\leq100$, `rigour: proven`, `complete: no`. The question asked here is
only about the range: is $0\leq k\leq100$ the whole of what the definition
promises, and if not, how far could it go and by what method.

**The short answer.** The definition promises an infinite family, so the table
is not complete and cannot be made complete. Nothing stopped it: the entry
count binds only at $k=1199$, and computing every row from 101 to there was
measured at 8 seconds. It was stopped at a round number -- and the round number
turns out to be almost exactly the right place, for a reason nobody wrote down.
Each row is an elliptic curve $E_k$, and I computed their conductors: **22 of
the 23 values of $k\leq400$ whose curve has conductor below 1000 are inside the
present range.** The one outside is $k=112$. Sweeping on to $k=1199$, the
entry-count ceiling, turns up one further curve of conductor below ten thousand
in 799 rows.

So there are two defensible answers and I recommend the second:

1. Leave the range at 100 and put the measurement into `complete-note`, which
   at present gives a reason that does not bear on the decision.
2. Extend by twelve rows to $k\leq112$, about 1.4 KB and under a second of
   computation, so that the bound has a reason rather than a roundness.

Either way the growth this table most needs is not rows at all; it is
finding 4.

## How it was read

- **Skill:** fetched from <https://numberdb.org/skill>, 48740 bytes; §3 ("How
  much to include") and "Hold the numbers that turn up" read against this
  table, and `docs/design/corpus-shape.md` beside them.
- **Document:** `GET /api/table?id=T282` with the key, direct. The SOCKS proxy
  answered the first request of the session and refused every later one
  (`000`); that is already in `docs/agent-environment.md` and I have not
  re-recorded it.
- **Rendering:** `/T282` returns 200 and renders. The Numbers block, the
  parameter line, all three formulas, both comments and the whole of Data
  properties read as text. No `Math input error`, no `argument ()`, no broken
  `HREF`.
- **Audit:** `GET /api/table/T282/audit` returns `"findings": []`,
  `"clean": true`. No Django here, so no `manage.py audit_table`. The audit has
  no opinion about a range and I have no quarrel with it.
- **Generator:** `generators/mahler-measures-square-lattice/generate.py`. The
  `table.yaml` beside it in the repository is the pre-repair draft text; the
  live document is what I read for the prose.
- **Literature:** Rogers and Zudilin, arXiv:1102.1153 §1, and Guttmann and
  Rogers, arXiv:1207.2815 §5.1, both fetched and read. **Boyd 1998 I could not
  reach**; see "What I could not check".
- **Computation:** three runs through `agents/sage.sh`, for the cost of
  extension and for the conductor of $E_k$. Term counts and $m_k-\log k$ were
  computed here from the stored values in 140-digit `Decimal`. Sizes measured
  on the document as served.

## 1. What the definition promises, and what is held

The definition opens "For a nonnegative integer $k$", the parameter is `Z` with
`constraints: $k\geq0$`, and comment (4) disposes of the negatives honestly:
$m_{-k}=m_k$. So the family the table names is every nonnegative integer, with
no upper bound stated anywhere in the document.

Comment (5) widens the promise rather than narrowing it. Boyd's conjecture is
given there for integer $k\neq0,4$, and Rogers and Zudilin describe Boyd's
finding the same way: similar identities hold numerically for the family
$k+X+X^{-1}+Y+Y^{-1}$ "whenever $k\in\mathbb{Z}$" (arXiv:1102.1153, §1). There
is no $k$ at which the arithmetic stops. Row 741 would be as much a
conjectural $L'$-value as row 41.

What is held is $0\leq k\leq100$, contiguous, with no row missing inside it. A
window on an infinite family, correctly described by `complete: no`.

## 2. What stops it: nothing, until $k=1199$

Measured on the document as served, not estimated:

| | held, $k\leq100$ | $k\leq1199$ | limit |
|---|---|---|---|
| entries | 101 | 1200 | **1200 soft** |
| entries block | 11.7 KB | about 138 KB | 320 KB soft; 160 KB house target |
| longest written value | 102 chars | 102 chars | -- |
| digits | 100 | 100 | 100 recommended |

The row to look at is the third. **The values do not grow.** $m_k\sim\log k$,
so every entry is the same 100 significant digits and about 115 bytes of
serialised text whatever $k$ is. This is the opposite of the case the size
advice is written for: on a polynomial table the block limit binds around
$n=150$ and readability binds before that, whereas here the entry *count* is
the only thing that moves, and it binds at exactly 1200 entries -- $k\leq1199$,
about 138 KB, still under the 160 KB house target. No entry becomes unreadable,
no digit budget is strained, no size exception is needed.

Nor does time stop it. Measured in the deployed Sage image:

    one value from the large-k series, mean of k=101..120   0.007 s
    one independent Jensen integral (the integrity check)   0.035 s
    so k=101..1199 would cost                               8 s of values
                                                            38 s of checks

The method is one constant, `MAX_K`. Every $k\geq5$ goes through
`_large_k_series`, which sums $\log k-\sum_n\binom{2n}{n}^2/(2nk^{2n})$ with a
geometric majorant on the tail, and that series converges *faster* the larger
$k$ is -- terms needed for the generator's own stopping test:

| $k$ | terms at 15 digits | terms at 100 digits |
|---|---|---|
| 5 | 68 | 502 |
| 10 | 17 | 122 |
| 100 | 5 | 35 |
| 200 | 4 | 28 |
| 1199 | 2 | 19 |

Two things a person extending it should know. `run_integrity_checks` recomputes
every row a second way, arb integration of formula (1), and that cost is per
row where the series cost is not -- it is five sixths of the total above, and
still trivial. And `__main__` calls `fill_draft_once`, which was written to
fill a *fresh* draft and submits with `upsert=False`: one request carrying
every entry, replacing the table's numbers wholesale. For a longer run the
batched, resumable `publish()` path is the one to use, so a failure at entry
900 costs one entry rather than the run.

## 3. Where the family actually ends, measured

Cost says nothing, so the question is the skill's: "whether anybody will arrive
holding one of them." That is usually a judgement. Here it can be measured,
because Boyd's conjecture names the object each row is of.

The curve is the plane cubic $x^2y+xy^2+xz^2+yz^2+kxyz=0$, which carries the
rational point $(1:0:0)$, so `EllipticCurve_from_cubic` and `.conductor()` give
$E_k$ for each $k$. Conductors of the first twenty, computed:

| $k$ | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| $N$ | 15 | 24 | 21 | singular | 15 | 120 | 231 | 24 | 195 | 840 |

| $k$ | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 |
|---|---|---|---|---|---|---|---|---|---|---|
| $N$ | 1155 | 48 | 663 | 840 | 3135 | 15 | 4641 | 1848 | 6555 | 240 |

Two things fall out at once. $k=4$ is singular, which is why $m_4$ is a
Dirichlet $L$-value, $4G/\pi$, and not an elliptic one -- the table's formula
(3) and its `equals` to T153 are the shadow of that, and the document never
says so. And the conductor is nothing like monotone in $k$: $k=1$, $5$ and $16$
all give conductor 15.

So "the interesting ones are the small $k$" needed checking rather than
asserting. Over $1\leq k\leq400$, the $k$ whose curve has conductor below 1000
are

    1 2 3 5 6 7 8 9 10 12 13 14 16 20 24 28 32 36 48 64 68 96   and   112

-- twenty-two inside the present range and exactly one outside it. Sweeping on
to the mechanical ceiling settles it: of the 799 values $401\leq k\leq1199$,
**exactly one has a conductor below ten thousand**, $k=976$ with $N=6405$, and
none is below a thousand. Extending the table the whole way to $k=1199$ would
buy 1099 rows and one curve anybody computes with.

The distribution moves by two orders of magnitude at the boundary:

| | min | first quartile | median | third quartile | max |
|---|---|---|---|---|---|
| conductor, $k\leq100$ | 15 | 1 320 | 17 160 | 103 071 | 911 121 |
| conductor, $101\leq k\leq200$ | 609 | 145 992 | 703 185 | 2 432 760 | 7 877 415 |

This is the argument the table is missing. A reader arrives holding one of
these numbers because they were computing with a curve somebody computes with,
and those curves are 15, 21, 24, 48, 240 -- they stop, in this family, at
$k=112$. Past that the rows are periods of curves of seven-figure conductor,
and nobody meets one of those by accident.

The same conclusion arrives from the physics. Guttmann and Rogers show this
family *is* the square-lattice spanning tree generating function,
$T_{sq}(z)=m(4/z)$ (arXiv:1207.2815, eq. 22). That reader arrives at $k=4/z$:
$z=1$ is $k=4$, the spanning-tree entropy the table already marks with an
`equals` to T153, and $z=\tfrac12,\tfrac13,\tfrac14,\tfrac15$ are $k=8$, $12$,
$16$, $20$. Small $z$ means large $k$ and means nothing in the physics.

For completeness on the other side: the rows do stay distinct. $m_{100}$ and
$\log 100$ part company in the fourth significant figure ($m_k-\log k$ is
$-1.0\times10^{-1}$ at $k=5$, $-2.0\times10^{-4}$ at $k=100$), and the corpus
holds no table of $\log n$ for them to collide with. The case against extending
is not that the numbers would be indistinct; it is that they are not values
anybody is looking up, and per the skill they would bury the ones that are.

**So: $0\leq k\leq100$ is right, and it is right for a reason the table does
not give.** The only change to the numbers I would consider is twelve rows,
$101\leq k\leq112$, which costs 1.4 KB and under a second and buys a bound that
can be stated: every $k$ up to 400 whose curve has conductor below 1000 is
then in the table. That is a judgement, and the criterion is one I chose after
seeing the data; a reader who thinks a round 100 with the measurement recorded
beside it is better has not lost much. What would be wrong is extending to 200
or 400 or 1199, which adds hundreds of rows to catch nothing.

## 4. The growth this table can use: what the rows say, not how many

Worth doing, and the recommendation here that adds most.

98 of the 101 rows are a bare number; only $k=0$, $1$ and $4$ carry a comment.
A reader who arrives holding $m_{12}=2.4705\ldots$ is shown the row, the $k$,
and nothing else. The family comment tells them $m_k=r_kL'(E_k,0)$ for some
curve $E_k$ and some rational $r_k$ -- and then the table never names an $E_k$
except at $k=1$.

The useful growth is a comment on each row naming the curve by its conductor,
and by its LMFDB label where it has one. That is a fact the row cannot carry by
itself, which is the skill's test for a comment earning its place, and it turns
a column of decimals into a hundred identified objects. It is also what makes
the range defensible to the reader rather than only in a critique file: seeing
`conductor 15` on $k=1$, $k=5$ and $k=16$ and `conductor 911121` on the row
below tells them, without being told, where this family stops being something
they will meet.

Cost: at about 120 characters a row that is some 12 KB on an 11.7 KB entries
block, leaving it at 24 KB, under a tenth of the soft limit.

The conductors above are computed and can be reused, but should be recomputed
by whoever writes them, and the sanity check is that $k=1$ must come out 15 and
$k=4$ must fail to be an elliptic curve at all. The comment should stop at
naming the curve: which $k$ have a *proved* Boyd identity is a moving list in
the literature and belongs in one sentence of the family comment with a
citation, not repeated a hundred times.

## 5. `complete-note` gives a reason that does not bear on the decision

Worth doing, one clause.

The note ends: "for $k>100$, CITE{formula-large-k} gives $m_k$ from a few
terms". As a statement about computing, true -- 34 terms at 100 digits, 4 at
15. As the reason a range stops, it is the wrong direction entirely. NumberDB
exists for the reader who *has* a number and wants to know what it is, and that
reader cannot apply formula (2), because applying it needs $k$, which is what
they came to find out. Forward cheapness is a property of nearly every
real-valued table in this corpus and has never been a reason to stop one.

It also points the wrong way on its own terms. The series is cheapest exactly
where the note uses it to justify an absence: 35 terms at $k=100$ against 502
at $k=5$, for the table's own precision. Read literally it argues for dropping
$k=20$ through $100$ at least as strongly as for declining $k=101$. The next
person will draw the opposite conclusion from the one intended -- cheap to
compute, therefore cheap to extend -- and nothing in the document stops them.

Smallest fix: replace that clause with the reason that is actually operating,
now that it has been measured. Something of the shape: "the members anybody
meets are at the bottom of the family, where the curve $E_k$ has small
conductor: of the $k\leq400$ whose curve has conductor below 1000, all but
$k=112$ are here, and beyond $k=100$ the conductors run to seven figures". The
first part of the note, listing what the range covers, is good and should stay.

I record that the earlier text of this same field, live earlier on the day I
read it, called the range "the round bound $0\leq k\leq100$" -- at least honest
about there being no argument. Most of the change since is an improvement; the
clause added to supply the missing argument does not supply one.

## Noted only

- **T282 and T283 do not point at each other.** T283, *Mahler measures of
  $1+x_1+\dots+x_{n-1}$ (uniform random walks in the plane)*, is published and
  holds 200 entries. It is the nearest thing in the corpus to this table, and
  neither one's `Similar tables` names the other; both name T153 instead. Worth
  a sentence in each direction. Not a growth finding; I met it looking for
  tables this family should coordinate with.
- **The corpus median is not a reason.** `docs/design/corpus-shape.md` records
  a median of 502 entries per table, and 101 looks small beside it. Nineteen
  published tables hold fewer than ten. A count that matches the other tables
  is exactly the kind of reason the skill names and rejects, and it should not
  be what moves this range.
- **The document changed under me while I read it.** The rendered
  `complete-note` at my first fetch and at my second, about fifteen minutes
  apart, were different texts; both are quoted above. Another worker is editing
  this table. Everything here is against the document as served at 16:20 UTC on
  2026-09-20, whose `complete-note` begins "it holds every integer $k$ with
  $0\leq k\leq100$".
- **The stored values are fine.** I did not re-verify the table and was not
  asked to, but the $k=100$ row came up in passing and it is right: the
  recomputed ball sits inside the stored decimal once that decimal is read as
  an interval of one unit in its last place. My first check omitted the
  widening and reported a disagreement on a correct entry; that trap is in the
  lesson proposal beside this file.

## What I could not check

**The range Boyd himself tabulated.** If Boyd's 1998 tables stop at a
particular $k$, "every $k$ Boyd computed" would be a citable reason for a
range and would settle this better than the conductor argument above. I could
not reach the paper: Project Euclid serves `curl` a 1.1 KB JavaScript shell,
and the EMIS mirror of *Experimental Mathematics* does not carry volume 7.
Rogers and Zudilin's summary of Boyd's result names no range, only "whenever
$k\in\mathbb{Z}$". Somebody with the paper should check whether the present
bound happens to match it; if it does, the fix in finding 5 is to say so.
