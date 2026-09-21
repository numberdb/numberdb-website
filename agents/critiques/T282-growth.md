<<<<<<< HEAD
# Can T282 grow? "Mahler measures of $x+x^{-1}+y+y^{-1}+k$", read on 2026-09-20

**The verdict: it can, and it should not.** The range can reach $k=1199$ —
exactly 1200 entries, the soft limit — for about two seconds of compute, 131 KB
of entries block, no new mathematics, and one changed constant in the attached
generator. Nothing mathematical, nothing metric and nothing in the definition
stops it. What stops it is the skill's own test, and 101 entries is where that
test puts a family like this one: the corpus median is 119 entries, and the
skill's sentence is "a hundred of a family is a reference; a thousand is a
listing of something nobody was looking for".

So the table was **not stopped early**. It was stopped at the right place with
the wrong sentence: `complete-note` says the bound is round, and a round bound
is the skill's own example of a non-reason. That is the one thing worth
changing here.

One hazard goes with the answer, and it only fires if somebody acts on it: the
attached generator no longer reproduces the table's own entries, so extending
the range by re-running it would quietly undo three repairs made on the site
four days ago. §5.

## What was read

- **Skill:** `https://numberdb.org/skill`, 48,740 bytes, fetched fresh. The
  prompt's `--socks5-hostname 127.0.0.1:1080` route refuses on this builder
  ("Connection refused", nothing listening on 1080); a direct fetch works.
  Already in `docs/agent-environment.md`.
- **Page:** `GET /T282` → 200, 70,304 bytes. T282 is published now; the
  September critique read it as a draft.
- **Document:** `numberdb.table('T282')` through the repository client:
  15,232 bytes as JSON, of which 11,663 are entries.
- **Audit:** `GET /api/table/T282/audit` → `{"findings": [], "clean": true}`.
  I agree; see §6.
- **Generator:** `https://numberdb.org/files/T282/generate.py?raw=1`,
  byte-identical to `generators/mahler-measures-square-lattice/generate.py`.
  The repository's `table.yaml` beside it is *not* identical to the published
  prose (§5).
- **Sources:** Guttmann–Rogers arXiv:1207.2815, full LaTeX source.
  Rogers–Zudilin arXiv:1102.1153, abstract. Boyd's talk
  `personal.math.ubc.ca/~boyd/sfu06.pdf`.
- **Not read, and it matters:** Boyd's 1998 paper is closed access
  (Project Euclid answers with an Incapsula block; Semantic Scholar reports
  `openAccessPdf: CLOSED`). So I could not check **how far Boyd himself
  tabulated $k$**, which is the one fact that could turn "100 is round" into
  "100 is Boyd's". If somebody has the paper, that is the question to ask it.
- **Computation:** five runs through `agents/sage.sh`. Nothing was written to
  any table.

## What is actually there

| | |
|---|---|
| entries | 101, $k=0\ldots100$, no gaps, no duplicates |
| digits | 100 significant on every row: 101 characters written, 102 on the three rows below 1, and a bare `0` at $k=0$ |
| document | 15,232 bytes: 3,569 prose, 11,663 entries |
| per row | 115 bytes |
| row comments | 3, at $k=0,1,4$; one `equals`, at $k=4$ |
| limits | 1200 entries soft (1000 recommended), 320 KB block soft |

Three checks on the stored range first, since a growth report that trusts the
range it reasons about is worth little:

- **Recomputation.** Eight rows ($k=1,2,3,4,5,50,99,100$) recomputed here with
  the attached generator agree with the stored digits to within
  $4\times10^{-100}$ — under half a unit in the last stored place, on every
  one, including the three that go through a different branch of the code.
- **Both methods, past the end.** The generator's main path (the series) and
  its independent check (direct arb integration of Jensen's formula) still
  produce overlapping balls at $k=101$, $200$ and $1199$. The method does not
  quietly stop working past the range.
- **Gaps.** None. The parameter constraint is $k\geq0$ and the rows are
  $0\ldots100$ with nothing missing.

## 1. The definition promises infinitely many, and that is not a defect

`Parameters` says $k\geq0$; the definition says "for a nonnegative integer
$k$". No finite range exhausts that, so `complete: no` is permanent and
correct, and the split the skill asks for — family in the parameter, range in
`complete-note` — is exactly what this table does.

The interesting question is not the upper bound but the word *integer*, and
there the table's scope is a real choice rather than an accident:

- The **arithmetic** reading wants integers. Boyd's conjecture,
  $m_k=r_kL'(E_k,0)$ with $r_k\in\mathbb{Q}$, is a statement about the curve
  $x+x^{-1}+y+y^{-1}+k=0$ over $\mathbb{Q}$, so $k$ integral is the case.
- The **lattice** reading wants real $k$. The table's own reference [2]
  (Guttmann–Rogers) writes the square-lattice spanning-tree generating
  function as $T_{sq}(z)=m(4/z)$ for $0\le z\le 1$ — that is, this family at
  every real $k\ge4$, not at integers. The table holds the single point $z=1$
  of it, $m_4=4G/\pi$, which is the row already linked to T153.

So the direction in which this family has the most numbers a reader could
arrive holding is **not more integers** — it is non-integer $k$, and that is
outside what the definition promises, deliberately. It would be a different
table (a real parameter, a grid of arguments chosen the way the error-function
tables chose theirs), not growth of this one. Nothing here needs to change;
it is worth saying only because "can it grow" has an answer in that direction
too, and the answer is "not here".

## 2. How far it could go, measured

The method is the series already printed on the page as formula (2), already
implemented, already the path every row $k\geq5$ takes. Cost, at the stored
100 digits:

| $k$ | series terms | seconds | radius |
|---|---|---|---|
| 5 | 605 | 0.160 | 8.0e-121 |
| 10 | 147 | 0.002 | 6.5e-121 |
| 50 | 53 | 0.001 | 3.2e-121 |
| 100 | 42 | 0.001 | 7.0e-123 |
| 200 | 34 | 0.001 | 1.7e-121 |
| 1000 | 24 | 0.000 | 2.5e-122 |
| 1199 | 23 | 0.001 | 2.7e-121 |

**Cost falls as $k$ grows**, because the series is in $16/k^2$: the most
expensive row in the table is $k=5$, which is already in it, and every row
past it is cheaper than the last. The independent Jensen integral the
generator checks against costs 0.005 s at $k=1199$. A rebuild of 1200 rows,
both methods, is a couple of seconds.

Precision does not degrade: the enclosure radius stays near $10^{-121}$ the
whole way, so the house 100 digits survive to $k=1199$ and far beyond.

Two values past the range, computed here and stored nowhere:

    m_101  = 4.614924371080287426669163937392538999391754642696114515104201693931403354894112179705160359520434271
    m_1199 = 7.089241763816559005843999185870607017565579351578494458785703588568676350701839596251251224638490243

Size, projected at the measured 101-character value and the observed key
costs: $k\le999$ is 109 KB of entries block, $k\le1199$ is 131 KB. Both are
under the 320 KB soft limit and under the skill's stricter 160 KB advice. So
**the block limit is not what binds — the entry count is**, and $k=0\ldots1199$
is exactly 1200 entries, the soft limit to the row.

**So: $k\le1199$, for seconds of compute, by changing `MAX_K` and nothing
else.** ($k\le999$ if one prefers to stay under the 1000 the skill recommends.)

## 3. What a far row would carry

A growth argument that says only "it is cheap" is worth nothing, so I measured
what is actually in a row. Boyd's conjecture is the content, and it is
checkable: computing $E_k$ from the cubic $x^2y+xy^2+kxyz+xz^2+yz^2$ and
$L'(E_k,0)=N_kL(E_k,2)/4\pi^2$,

| $k$ | 1 | 2 | 3 | 5 | 6 | 7 | 8 | 9 | 10 | 12 | 16 | 19 | 30 | 50 | 82 | 100 | 101 | 200 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| $N_k$ | 15 | 24 | 21 | 15 | 120 | 231 | 24 | 195 | 840 | 48 | 15 | 6555 | 26520 | 2760 | 550056 | 3120 | 1028685 | 14280 |
| $r_k$ | 1 | 1 | 2 | 6 | 1/2 | 1/2 | 4 | 1/2 | 1/8 | 2 | 11 | 1/40 | 1/240 | 1/16 | 1/2496 | 1/16 | 1/3936 | 1/64 |

Every one of these is a clean rational to twelve digits or better, including
the two past the end of the table. So a new row would **not** be arithmetically
empty; Boyd's identity keeps holding and keeps being checkable.

What does decay is who can look the curve up. The conductor follows
$N_k=c\cdot\operatorname{rad}(k(k^2-16))$ with $c\in\{\tfrac12,1,4,8\}$ on
every $k\le140$ I computed, so it grows like $k^3$ apart from the smooth
exceptions:
$N_{100}=3120$ but $N_{101}=1{,}028{,}685$ and $N_{1199}=1{,}723{,}664{,}415$.
Already inside the stored range, **seven rows have curves past conductor
500,000** — $k=82,83,87,89,91,93,97$, the largest $N_{97}=911{,}121$ — which is
where the complete Cremona tables stop. Past $k=100$ most rows are curves
nobody has tabulated. (At $k=1199$ my own $L$-value check stopped producing a
recognisable rational in three seconds; I did not pursue it, so treat that one
column of the story as unfinished rather than as evidence.)

That is the honest shape of it: the far rows are real mathematics that is
getting harder to connect to anything a reader has, while the number itself
gets easier for the reader to compute — the page's own formula (2) gives
$m_{700}$ to a hundred digits from a couple of dozen terms of an elementary
series.

## 4. Why it should not grow

The skill's §3, which is the only thing that settles this: "is this a value
somebody could plausibly encounter and want to identify? … A hundred of a
family is a reference; a thousand is a listing of something nobody was looking
for, and it makes the search results worse for everybody by burying the values
that are common."

T282 has 101 entries. `numberdb_app/limits.py` records the corpus median as
119. This table is the median table, and the five rows anybody actually
arrives holding — $k=0$ (zero, with its factorisation), $k=1$
(Rogers–Zudilin's theorem), $k=2,3$, and $k=4$ ($4G/\pi$, the square-lattice
spanning-tree entropy) — are all in it, with the interior of the family
$0\le k\le4$ complete. The ninety-six rows above them are the reference
margin around those five. Twelve hundred would be a listing with the same five
useful rows in it.

## 5. What I would change

### (a) `complete-note` gives no reason. Worth doing, and first.

It reads, and renders as, "Table is complete: no (it holds Boyd's integer
family through the round bound $0\leq k\leq100$)".

It does name the range, which is the field's first job and which the T283 note
failed at. But "the round bound" tells a reader the number 100 was chosen
because it is round — and the skill says that in as many words: "a denominator
bound, a size target, a count that matches the older tables — none of them is a
reason for any particular number to be present. Say which range you chose and
why in the completeness note. That sentence is the argument."

Smallest fix that makes it an argument a reader can use:

> it holds every integer $k$ with $0\leq k\leq100$: the five values $k\leq4$,
> where $m_k$ has a closed form or a proved $L$-value identity, and a hundred
> of Boyd's family above them, where CITE{formula-large-k} gives any larger $k$
> from a few terms

That sentence tells the reader who holds $m_{137}$ both that it is not here and
how to get it, which "the round bound" does not. If somebody can read Boyd's
paper and the bound really is his tabulation, say *that* instead — it is the
better reason and it is the one the phrase "Boyd's integer family" is already
reaching for.

### (b) Re-running the generator would undo the September repairs. Blocking, if anyone acts on §2.

This is the hazard that the growth answer walks into, because growing the range
means re-running the attached file.

`generate.py` builds each row's comment in `_entry_comment`, and what it builds
is the **pre-repair** text:

    return ("Rogers and Zudilin proved an identity relating this value "
            "to the $L$-series of a conductor 15 elliptic curve.")

The published row $k=1$ says something else — the identity itself,
$m_1=\frac{15}{4\pi^2}L(E_{15},2)$ — because `agents/critiques/T282.md`
finding 3 was applied on the site. Likewise the published $k=4$ carries
`equals: Entropy_constants_of_lattice_models#spanning-tree,square,entropy`
(finding 2), and nothing in the generator emits an `equals`. And the file's
`--publish` path is `fill_draft_once`, which calls `submit_entries(...,
upsert=False)` — documented in the client as "the entries are replaced, which
is what a full regeneration means".

So a run with a larger `MAX_K` would restore the vague comment and drop the
`equals`, and both losses are invisible in the diff of what the run *meant* to
do, which is add rows.

Nothing catches this. `verify` compares an attachment's *values* against the
table — `.gitignore` records 126 of 128 attachments recomputing their table's
values — and the values here are right; it is the comments that have drifted,
and no check reads those.

Smallest fix, before any re-run: put the published $k=1$ text into
`_entry_comment`, and have `value()` attach the `equals` at $k=4$. Then the
generator reproduces the table it is attached to, which is what a reader
downloading it is entitled to assume.

### (c) The repository's `table.yaml` is the pre-repair prose. Known failure mode; decide rather than fix.

`generators/mahler-measures-square-lattice/table.yaml` still has
`title: parameter` for $k$, the old vague `comment-family`, the old
`complete-note` ("it holds every integer $k$ with $0\leq k\leq100$") and the
rigour note with the build-size sentence — all six of the September findings,
unrepaired, because the repairs were made on the site. Both files under
`generators/` were committed with the draft and never touched again.

This is the case `.gitignore` already names: "Generators are working copies,
not the record… A second copy in git competed with that and lost three times in
one day", listing T197, T219 and T218. `generators/` is ignored for anything
new; these two files predate that and are still tracked. So there is nothing
to discover here and two ways to act: refresh the file from the live document,
or drop the tracked copies and let the attachment be the record, which is what
the policy says. Either is a decision for somebody, not a fix; what matters
for growth is only that a person extending this table from the repository
would read prose that the site replaced four days ago.

### (d) The generator's note about its own range invites extension without a view. One sentence.

    # Measured before filling the draft: k = 0..100 gives 101 entries, each
    # written to 100 digits. [...] so the range leaves room for extension.
    MAX_K = 100

"The range leaves room for extension" is true and is the only thing the code
says about why 100. The next person reads it as permission. If §4 is right,
the comment should say what the room is *for*: that the limit is 1200 entries
and the reason to stop at 100 is editorial, not metric.

## 6. The audit

`{"findings": [], "clean": true}`, and I agree with it. The three things it
could plausibly have caught and didn't are not present: there is one integer
parameter with no second family hiding under it, the column headings are $k$
and $m_k$ with bare integers as row labels, and every `HREF` and `CITE` on the
page resolves. It has nothing to say about ranges, which is right — no rule
can decide where a family should stop.

Worth noting against the T283 experience: this generator's docstring carries
`sage -pip install numberdb` and `sage -python generate.py`, so the two
Sage-only rules that misfire on pure-Python generators do not misfire here.

## 7. Noted only because I noticed

- **Three rows are exact multiples of other rows, and the page does not say
  so.** $E_1$, $E_5$ and $E_{16}$ all lie in isogeny class 15a, and $E_2$,
  $E_8$ in 24a, so Boyd's conjecture forces relations between their Mahler
  measures. Measured to 95 digits: $m_5=6m_1$, $m_{16}=11m_1$, $m_8=4m_2$.
  ($m_1$ is Rogers–Zudilin's theorem, so these three are conjectural at the
  same strength as Boyd's $r_k$.) They are not `equals` — the numbers differ —
  but they are the most surprising thing in the table, and a reader holding
  $2.7646\ldots$ is told nothing about why it is eleven times row 1. If
  anything is worth *adding* to this table, it is three entry comments, not a
  thousand rows. I am recording it here rather than as a finding because this
  report is about the range.
- **$k=0$ is stored as an exact `0` in a table of type `R`.** T283 solved the
  same problem by leaving its zero rows out and explaining them in a comment.
  Here the row is present and its comment gives the factorisation that makes it
  zero, which is at least as good: the reader who arrives at the row is told
  why, rather than having to find the comment that says the row is missing.
  Nothing to do.
- **Formula (2)'s "for $k>4$" is right.** Guttmann–Rogers state the closed form
  for all $k$ as $\Re\bigl(\log k-\frac{2}{k^2}\,{}_4F_3(\ldots;16/k^2)\bigr)$,
  which is an analytic continuation rather than the convergent series; the
  series itself needs $k>4$ and the page says so.

## Ranking

| | finding | worth doing? |
|---|---|---|
| 1 | `complete-note` says the bound is round, which is not a reason | yes, first |
| 2 | re-running the generator would undo the $k=1$ comment and the $k=4$ `equals` | yes — blocking before any growth |
| 3 | repository `table.yaml` predates all six September repairs | a decision, not a fix |
| 4 | `MAX_K`'s comment invites extension without saying whether to | one sentence |
| 5 | $m_5=6m_1$, $m_{16}=11m_1$, $m_8=4m_2$ are unsaid | a different report's business |

**And the growth answer, once more: the room is there and it is nearly free —
$k=1199$, 1200 entries, 131 KB, seconds of compute, one constant changed — and
it should not be used.** The range is not short of what the definition
promises in any way a reader is hurt by; it is a hundred of a family, which is
what a reference is. Fix the sentence that defends it, not the range.
=======
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
- **Rendering:** `/T282` returns 200. The Numbers block, the parameter line,
  all three formulas, both comments and the whole of Data properties were read
  as text stripped out of the HTML. The parameter line reads
  "$k$ — constant term ($k\geq0$)", not `argument ()`; both `HREF`s in formula
  (3) come through as links and every `CITE` as a numbered reference. I cannot
  say there is no `Math input error`: this page typesets with MathJax in the
  browser, so a `curl` of it never carries that failure. What I can say is that
  the `$` delimiters balance and no `<` appears inside the mathematics.
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
>>>>>>> origin/campaign/w3
