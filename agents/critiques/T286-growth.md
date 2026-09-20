# Can T286 grow? "Pisot numbers less than the golden ratio"

Read on 2026-09-20. T286 is live, 50 entries, `rigour: proven`, 100 digits,
indexed by rank $r$ and headed $\theta_r$. `agents/review-queue.tsv` records
18,526 bytes; that is `full_yaml` for the *whole document*. The entries block,
which is what the 320 KB soft limit measures, is 14,145 bytes.

## The answer

**The definition promises an infinite family, so no range is the whole of it,
and the question is only where to stop.** The table stops at rank 50 and gives
a reason -- "after that the two infinite families are already within
$3\cdot10^{-6}$ of $\varphi$". The *kind* of reason is exactly right: this
family accumulates at $\varphi$, so the range should end where the numbers
stop being telling apart. But $3\cdot10^{-6}$ is not where that happens. At
rank 50 every entry is still a unique, unambiguous hit for a reader carrying
an ordinary double-precision value, and stays one for about another ninety
ranks.

**It was stopped early, by roughly a factor of 1.6 to 3, and the growth is
free.** I recommend extending to $n\leq40$ in both families -- ranks 1 to 79,
about 23 KB, under a minute of Sage -- and stating the range in $n$ rather
than in $r$. The outer bound anybody could defend is $n\leq72$ (rank 143); past
that the entries begin answering searches for the golden ratio itself. The
hard ceiling, where two entries would store the same 100 digits, is rank 478.

Details, measurements and the two things that have to move with it are below.

## How it was read

- **Skill:** fetched from <https://numberdb.org/skill> (48,740 bytes). The
  SOCKS proxy on 127.0.0.1:1080 refuses connections on this runner and plain
  `curl` works; `docs/agent-environment.md` documents that at length already,
  so I have added nothing there.
- **Document:** `GET /api/table?id=T286`, and `?id=T300`, `?id=T222` for the
  neighbours.
- **Audit:** `GET /api/table/T286/audit` returns `findings: []`, `clean: true`.
  I agree with it; nothing here is a thing a rule could see, since every
  finding is about where a range ought to end.
- **Rendering:** `GET /T286` returns 200 and 60,268 bytes. The Formulas block,
  the completeness note and all 50 row comments render; the $\Delta(2,n,\infty)$
  links in rows 1 to 21 and the `Golden_ratio#phi` link resolve. No "Math input
  error", no `argument ()`, no swallowed section.
- **Generator:** both copies. The one attached to the table
  (`/files/T286/generate.py?raw=1`, 6,831 bytes) and the one in this repository
  (`generators/pisot-numbers-less-than-golden-ratio/generate.py`, 5,859 bytes).
  They differ; see "What has to move with it".
- **Computation:** `agents/sage.sh`, twice. All roots of $P_n$, $Q_n$ in
  $(1,\varphi)$ for $n\leq130$ (259 roots, 36 s) and for $n\leq250$ (499 roots,
  2 m 15 s), each at 100 digits, with the entries block modelled by the same
  `yaml.dump` of flat records that `numberdb_app/limits.py` measures. The model
  gives 12,963 bytes for ranks 1-50 against the live block's 14,145; the 1.2 KB
  it misses is the plastic-ratio and Coxeter prose on the early rows, which is a
  fixed cost and does not scale. I have added it to the projections below.
- **Values:** not rechecked. The first ten minimal polynomials match the ones
  the table already stores, which is as far as I went.

## What the definition promises, and where the cut actually falls

> For an integer $r\geq1$, $\theta_r$ is the $r$-th smallest
> Pisot-Vijayaraghavan number in the interval $(1,\varphi)$.

$r\geq1$, unbounded. And the Formulas block names the whole set: the roots in
$(1,\varphi)$ of $P_n(x)=x^n(x^2-x-1)+1$ and $Q_n(x)=x^n(x^2-x-1)+x^2-1$ for
$n\geq2$, plus the root of $E$. Dufresnoy and Pisot proved that this is all of
them. So the family is infinite, completely classified, and every member is
reachable by the same three lines of code -- about as growable as a table can
be. `complete: no` is permanent here, and correctly so.

The set $\{E\}\cup\{P_m,Q_m : m\leq n\}$ has $2n-1$ elements, and both families
increase with $n$, so

> **ranks $1$ to $2n-1$ $\iff$ both families taken to $n$.**

Rank 50 is not of that form. $2n-1=49$ at $n=25$ and $51$ at $n=26$, which is
why the completeness note has to say "the roots of $P_n$ for $2\leq n\leq25$,
and the roots of $Q_n$ for $2\leq n\leq26$": a cut in $r$ chops the two
families in different places, and the note has to spend a clause explaining an
asymmetry that is an artefact of the number 50. A cut in $n$ needs no such
clause, and a reader holding $Q_{26}$ but not finding $P_{26}$ needs no
explanation either.

## How fast it converges, measured

Distance below $\varphi$, and the gap to the previous entry, by rank
(logs base 10, from the $n\leq250$ run):

| rank | which | $\varphi-\theta_r$ | gap to $\theta_{r-1}$ |
|---|---|---|---|
| 50 | $Q_{26}$ | $10^{-5.57}$ | $10^{-11.0}$ |
| 80 | $Q_{41}$ | $10^{-8.71}$ | $10^{-17.3}$ |
| 100 | $Q_{51}$ | $10^{-10.8}$ | $10^{-21.5}$ |
| 150 | $Q_{76}$ | $10^{-16.0}$ | $10^{-31.9}$ |
| 200 | $Q_{101}$ | $10^{-21.2}$ | $10^{-42.4}$ |
| 300 | $Q_{151}$ | $10^{-31.7}$ | $10^{-63.3}$ |
| 450 | $Q_{226}$ | $10^{-47.4}$ | $10^{-94.6}$ |

Two rates, not one. $\varphi-\theta_r$ falls by a factor $\varphi$ per step in
$n$ -- a decimal digit every 4.8 steps, and since each $n$ contributes two
entries, a decimal digit every 9.6 ranks. The entries come in pairs
$(P_n,Q_{n+1})$ whose separation is the *square* of that -- the gap column is
twice the distance column, digit for digit, all the way down. So the rank at
which two rows stop being distinguishable always arrives first, and it arrives
twice as early as the distance to $\varphi$ would suggest.

Where the leading digits go: the value first agrees with $\varphi$ in its first
6 decimals at rank 55, 10 decimals at 95, 15 at 141, 17 at 161, 25 at 241, 50
at 481.

## Three ceilings, in the order they bite

**1. Rows stop being separate answers -- rank ~72.** Neighbouring entries are
$10^{-15.4}$ apart at about rank 71 and closer after that, which is the
resolution of an IEEE double at 1.6. From there on, a reader who computed a
root in floating point and looks it up gets *two* rows, not one. This is a soft
ceiling and arguably not a fault: both rows are genuinely that close, and each
row's comment carries its own minimal polynomial, which is exactly what tells
them apart. I would not stop here, but I would not pretend the table is doing
one-to-one identification past it either.

**2. Rows start answering searches for $\varphi$ -- rank ~145.**
$\varphi-\theta_r$ falls below $10^{-15}$ at rank 141 and below $10^{-16}$ at
about rank 150. A lookup for the golden ratio at 15 digits today returns five
results, and all five *are* the golden ratio:

    {"kind":"RIF","lower":"1.61803398874989","upper":"1.61803398874990"}
    -> T32 phi, T35 1,-1,-1,2, T153 hard-core,line,kappa,
       T222 [(3,3,inf)], T297 25,ramanujan

A table taken to rank 200 would put 60 more rows in that interval, none of them
the golden ratio. This is the skill's "every hit in the corpus is worth a
little less for it", and it is sharper here than in the general case, because
the limit point of this family is itself a table in this corpus. **This is the
real ceiling.** Growth past it does not merely add rows nobody arrives holding;
it degrades a lookup somebody else's table already answers.

**3. Two rows store the same digits -- rank 478.** At 100 digits, the stored
strings of a pair $(P_n,Q_{n+1})$ first coincide at ranks 478 and 480. Past
that the table would hold visibly identical values on consecutive rows. The
320 KB block limit arrives essentially on top of it, at about rank 488 -- the
entries block is 23 KB at rank 79, 51 KB at rank 143, 229 KB at rank 400 and
299 KB at rank 470. It grows quadratically, not linearly, because the $P_n$
minimal polynomials are dense and each row's comment writes one out: the
comment on rank 499 is 2,437 characters against 87 for its neighbour. So the
1200-entry limit is unreachable here and only the byte limit and the digit
collision matter, and they agree with each other.

## What I recommend, and what it costs

**Extend to $n\leq40$: ranks 1 to 79.** Every entry still differs from
$\varphi$ by about $2\cdot10^{-9}$ or more, so no row can be mistaken for the golden
ratio by any reader at any ordinary precision; the identification service the
table performs -- "you have a small Pisot number, here is which one, and here
is its minimal polynomial" -- reaches minimal polynomials of degree 42 instead
of 28. Cost: an entries block of about 23 KB, 7% of the soft limit, and well
under a minute of computation.

**State the range in $n$**, e.g. `complete-note`: "it holds the root of $E$ and
the roots of $P_n$ and $Q_n$ for $2\leq n\leq40$, which is $\theta_1$ to
$\theta_{79}$; past $n=40$ the roots are within $2\cdot10^{-9}$ of $\varphi$,
and by $n\approx72$ they are within $10^{-15}$, where they would begin
answering searches for $\varphi$ itself." That sentence is checkable by a
reader against their own polynomial, which "the first 50 ranks" is not, and it
says why the table stops rather than only where.

**The method is one constant.** The attached generator already computes both
families for $n\leq80$ -- 159 roots -- and discards everything past rank 50:

    RANKS = 50
    MAX_N = 80

Raising `RANKS` to 79 is the whole change. Nothing else needs touching: the
attached copy carries a guard that recomputes $P_{80}$ and $Q_{80}$ and raises
`ArithmeticError` unless both exceed $\theta_{\text{RANKS}}$, so the claim that
the first `RANKS` ranks are complete is checked rather than asserted, and it
holds for any `RANKS` up to about 155. The 100-digit isolation is interval
arithmetic on exact integer polynomials, so `rigour: proven` survives
unchanged. I confirmed independently that for every $n\leq250$ each of $P_n$
and $Q_n$ contributes exactly one root in $(1,\varphi)$ -- 499 roots for
$n\leq250$, which is exactly $2\cdot249+1$.

**If a reviewer prefers to stop where the table stops today, the entry count is
defensible and the stated reason is not.** $3\cdot10^{-6}$ is a distance at
which every row is still perfectly distinct; it reads as a reason but is not
one. Whatever range is chosen, the note should name the threshold that actually
binds.

## What has to move with it

**T300 is pinned to this table's range by rank.** "Minimal polynomials of the
Pisot numbers less than the golden ratio" holds 50 entries and says its range
is "matching the range in the root table exactly", and each of its comments
links to `...#r` in T286. Growing T286 alone makes that sentence false. T300's
generator has the same `RANKS = 50` and `MAX_N = 80`, so the change there is
the same constant; its entries are far cheaper (a polynomial against a hundred
digits plus the same polynomial in prose), so it will be nowhere near any
limit. **Grow them in one act or not at all.**

**The generator in this repository is the pre-repair version.** The copy
attached to the live table has all eight repairs from the 2026-09-17 critique
(`agents/critiques/T286-repaired.md`); the copy at
`generators/pisot-numbers-less-than-golden-ratio/generate.py` has none of them.
It still writes row comments as "$P_{2}$ family; minimal polynomial ...; this
is the plastic ratio." -- the semicolon fragments that finding 5 asked to be
rewritten -- has no $\Delta(2,n+1,\infty)$ links, and lacks the completeness
guard. `generators/.../table.yaml` is stale the same way: its `complete-note`
is still "it holds the first $50$ ranks in increasing order". The repair commit
(e43b274) touched only the critique record.

So whoever grows this table by editing the obvious file and running it with
`--publish` will raise `RANKS` **and silently revert five of the eight
repairs**. Start from `/files/T286/generate.py?raw=1`, and commit it back over
the repository copy as part of the same change.

## Noted only

- The completeness note's "so the table stops at a readable initial segment" is
  a remark about this website rather than about the mathematics. If the note is
  rewritten anyway, the threshold sentence replaces it.
- A cut stated in *degree* rather than in $n$ would be even easier for a reader
  to check, since a reader holds a polynomial and knows its degree. It is not
  quite a cut in $n$: the minimal polynomial of $P_n$ has degree $n$ for odd
  $n$ and $n+1$ for even $n$, while $Q_n$'s has degree $n+2$. Mentioning it
  because it is the more reader-facing sentence, not because $n$ is wrong.
- Extending T286 gains no new cross-links to T222: that table's own range stops
  at triangle labels $\leq12$, so $\Delta(2,n+1,\infty)$ exists there only for
  $n\leq11$, which the current 50 rows already cover in full.
