# T293, *Regulators of elliptic curves over real quadratic fields* — can it grow?

**Verdict: no, and it should not be reshaped either.** T293 holds 1171 entries
in 273.1 KB against soft limits of 1200 entries and 320 KB. It has 29 entries
of headroom. It was not stopped early; it was stopped, by measurement, one
step short of the ceiling, and the completeness note already says so and says
so correctly.

The premise this run was dispatched on — "32 entries in 13825 bytes, under a
tenth of the soft limits" — is a stale figure from `agents/review-queue.tsv`
line 294, which predates the 2026-09-19 repairs that took the table from 32
rows to 1171. That is already recorded in `docs/agent-environment.md` ("The
growth queue selects from a committed snapshot, and the snapshot goes stale"),
so I have not repeated it there.

One finding is worth acting on, and it is a sentence. Everything else below is
the working that says so.

## What is actually there

Measured from the live document (`numberdb.table('T293')`) and the rendered
page on 2026-09-20:

| | T293 | recommended | soft limit |
|---|---|---|---|
| entries | **1171** | 1000 | 1200 |
| entries block, nested YAML | **273.1 KB** | — | 320 KB |
| entries block, flat records | **299.0 KB** | — | 320 KB |
| digits | 35 | 100 | 500 |

Per discriminant: $D=5$ 17 rows, $D=8$ 63, $D=12$ 253, $D=13$ 195, $D=17$ 295,
$D=21$ 348. By rank: 1163 rows of rank 1 and 8 of rank 2, the rank-2 rows all
over $D=21$.

No `Size exception` is declared and none is needed. The audit
(`GET /api/table/T293/audit`) returns clean, and I agree with it on this axis:
nothing about the range breaks a rule.

## Is the range the whole of what the definition promises?

No, and it cannot be. The definition is "let $K=\mathbb{Q}(\sqrt{D})$ and let
$E/K$ be an LMFDB-labelled elliptic curve of positive Mordell-Weil rank", with
$D$ constrained only to be a positive fundamental discriminant. That family is
unbounded. Even inside the pinned source it is enormous: at commit
`10b28418`, ecnf-data's `RQF` directory holds 130 real quadratic fields, and
over T293's own six fields alone it holds

    D = 5     4228 positive-rank curves     (table holds 17)
    D = 8     8254                          (63)
    D = 12   13022                          (253)
    D = 13    4012                          (195)
    D = 17    2687                          (295)
    D = 21    5370                          (348)
             ------
             37573 positive-rank curves     (table holds 1171, 3.1%)

So `complete: no` is right, and the table is a sample. The question is whether
it is the right sample, because it is certainly not going to be a bigger one.

## Why it cannot grow

**The entry count binds, and nothing buys entries.** The obvious lever is the
comments: every row carries "LMFDB curve `2.2.5.1-199.1-c1` has conductor
ideal $(-3w+16)$, rank $1$, and equation …", and those comments are 200 KB of
the 273 KB block — strip them and the block is 73.1 KB. But stripping them
would buy nothing at all, because at 1171 of 1200 entries it is the *count*
that is 29 away from the limit, not the bytes. Any byte-saving leaves the
table exactly as extensible as it is now, and costs the reader the only facts
on the page that identify the curve. I agree with the earlier repair run that
declined this.

**The remaining headroom is 24 rows and not worth a revision.** I reproduced
the note's arithmetic against the source. Uniform conductor-norm cutoffs give

    N <= 250    1171 entries    (what the table holds)
    N <= 254    1195            the largest uniform bound inside 1200
    N <= 255    1213            exactly the figure the note quotes
    N <= 256    1305

The note's "$1213$ entries at conductor norm $N\leq255$" is exact. The only
extension available as one table is $N\leq254$, which adds two rows over $D=5$
and twenty-two over $D=21$ and moves nothing.

**The corpus's own growth path for this quantity is unavailable here.** Over
$\mathbb{Q}$ the same regulator is held as three tables split by rank —
`Regulators_of_elliptic_curves_over_Q_of_rank_1` (1007 entries, 209 KB), rank
2 (955, 203 KB), rank 3 (1061, 231 KB). That is how this corpus grew a
regulator family past one table. It does not transfer: T293 is 1163 rank-1
rows and 8 rank-2 rows, so a rank split gives one table of 1163 and one of 8.

## The one thing worth doing

**The completeness note gives the cutoff a size reason where a mathematical
one is available, and the mathematical one is better.**

A reader looking at "conductor norm at most $250$; this cutoff is deliberate,
since the same source gives $1213$ entries at $N\leq255$, above the
$1200$-entry soft limit" learns that 250 is where the table stopped fitting.
The skill asks a completeness note to be the argument for the range — "that
sentence is the argument, and it is what a reader checking whether their own
number belongs here actually reads" — and a limit is not an argument about
elliptic curves.

There is one to hand. The smallest conductor norm at which a curve of rank
$\geq2$ appears, in each of the six fields:

    D = 21    N = 235        <- the only one below 250
    D = 17    N = 478
    D = 13    N = 637
    D = 12    N = 814
    D = 8     N = 1031
    D = 5     N = 1831

$N\leq250$ is, within fifteen of the norm, *the smallest uniform cutoff that
reaches a rank-2 curve at all*. Below $N=235$ the table would hold nothing but
rank-1 rows, where the regulator is a single height and the "determinant of
the height pairing" in the definition is a $1\times1$ determinant. The eight
rank-2 rows over $D=21$ are the only rows in the table where the definition
does the work it is written to do — and the `rigour details` already single
them out as the ones whose height-pairing determinant was recomputed in Sage.

Smallest change: one clause in `complete-note`, along the lines of *"and the
cutoff reaches the first curves of rank $2$, which begin at conductor norm
$235$ over $D=21$"*. It converts a bound chosen by counting into a bound
chosen by the mathematics, which is what the skill asks for, and it costs a
line. **Worth doing.**

## Noted, not urged

**The $17$-against-$348$ raggedness is defensible, for a reason nobody has
written down.** A uniform norm cutoff is not a uniform depth: the first
positive-rank curve sits at $N=199$ over $D=5$ and at $N=17$ over $D=17$ and
$D=21$, so $\mathbb{Q}(\sqrt5)$ — the real quadratic field a reader is likeliest
to arrive from — gets 17 rows and $\mathbb{Q}(\sqrt{21})$ gets 348. The
obvious fix is equal depth, about 195 curves per field, which needs per-field
cutoffs of

    D = 5   N <= 655     D = 13   N <= 244
    D = 8   N <= 361     D = 17   N <= 188
    D = 12  N <= 213     D = 21   N <= 153

An earlier repair run declined this as a judgement rather than a defect. It
should stay declined, and for a harder reason than that: compare those six
bounds with the six first-rank-2 norms above. Every one of them is below its
own field's first rank-2 curve — 153 against 235 over $D=21$ most of all. The
equal-depth table would be 1171 rank-1 rows and would contain no instance of
its own general case. The raggedness is the price of holding a rank-2 row, and
it is worth paying.

**Splitting by $D$ is against the skill's structural test, and I do not
recommend it.** $D$ names what the number is of rather than which quantity is
taken of it; every row's value is the same symbol, and the column heading
`$R_{E/K}$` is true of all 1171 of them. Both are the skill's signs of one
table. For the record, the shape that would work if somebody decided
otherwise: $\mathbb{Q}(\sqrt5)$ alone, every positive-rank curve of conductor
norm at most 1831, is 1194 rows — inside the entry limit, and the bound is
exactly where that field's first rank-2 curve appears. It would also repeat
17 of T293's rows and need `repeats:`. A person's call, not a critique's.

**The headroom in this corner of the corpus belongs to the companion table,
not to this one.** `Special_L-values_of_elliptic_curves_over_real_quadratic_fields`
holds 572 entries in 110.3 KB — one row per isogeny class, five fields
$D\in\{5,8,12,13,17\}$, $N\leq150$. Carried to T293's six fields at $N\leq200$
it would be 1058 isogeny classes, inside every limit. If anything here is
meant to grow, that is the table with room to do it.

**While looking at that pair: T293's `Similar tables` calls it "the
$L^*(E/K,1)$ side of the Birch and Swinnerton-Dyer formula for the same
ecnf-data curves", and the two ranges are not the same in either direction.**
The $L$-value table holds rank-0 classes and $D=5$ classes of conductor norm
31 and 100, where T293's first row over $D=5$ is at norm 199; T293 holds
$D=21$ and everything in $150<N\leq250$, which that table does not. A reader
who follows the link expecting the other half of the formula for the row they
are looking at will usually not find it. "for curves from the same ecnf-data
source" would be true. Small, and it is a wording finding rather than a growth
one, but it is the sentence the two tables are joined by.

## How this was checked

    curl -sS https://numberdb.org/T293            # renders; no proxy on this box
    curl -sS https://numberdb.org/api/table/T293/audit      # clean
    PYTHONPATH=.../clients/python python3         # run from /tmp, not the checkout
        numberdb.table('T293')                    # 1171 entries, 279665 YAML bytes

Counts come from the pinned source the generator names, read directly:
`https://raw.githubusercontent.com/JohnCremona/ecnf-data/10b28418e80392032b106ea00e6c5aa109d28e7b/RQF/mwdata.2.2.<D>.1`,
positive-rank rows selected exactly as `generate.py` selects them. My
class-counting reproduces the $L$-value table's 572 entries on the nose, which
is the control for the class counts quoted above. No Sage was needed and none
was run; no value was recomputed, which is the build's job and not this one's.
