# Can T286 grow? "Pisot numbers less than the golden ratio"

Read on 2026-09-20 from branch `campaign/w4`. T286 is published, `rigour:
proven`, 100 digits, indexed by rank $r$ and headed $\theta_r$.

**The table is not what the queue says it is.** `agents/review-queue.tsv` row
287 reads `T286  50  18526`, and the brief for this run repeated it. The live
table holds **79 entries**, and its entries block is **22,602 bytes** measured
the way `numberdb_app/limits.py` measures it. It was grown from 50 to 79 at
02:52 today by `d6b11a7 repair: grow Pisot tables before the golden ratio`, on
the recommendation of two growth critiques written earlier the same morning
(`d7e3f0c` on `campaign/w2`, `0e48aec` on `campaign/w3`, both at
`agents/critiques/T286-growth.md`). This branch has none of those commits, so
the `generate.py` checked in here still says `RANKS = 50` and is not the file
that filled the table; `docs/agent-environment.md` on `w3` already records
that trap, and I did not re-derive it.

So the question this run was given -- was T286 stopped early? -- has already
been asked, answered and acted on. What follows is the question that is now
open: **is the range it was grown to the right one, and did the growth reach a
reader?** The answer to the second is no, and that is the finding.

## The answer

1. **No range is "the whole of what the definition promises."** The definition
   is "the $r$-th smallest Pisot number in $(1,\varphi)$" for $r\geq1$.
   Dufresnoy and Pisot proved the set is infinite and accumulates only at
   $\varphi$, and `formula-families` names every member. `complete: no` is
   permanent and right. The only question is where to stop, and the honest
   stopping rule is *where the numbers stop being distinguishable from
   $\varphi$*, not where the table stops fitting.
2. **Size never binds, at any range anybody would defend.** Measured below:
   at rank 145 the pair of tables would still be at roughly 14% and 11% of the
   320 KB soft block limit, and 12% of the 1200-entry limit.
3. **The reader's ceiling is rank 145**, where $\varphi-\theta_r$ falls below
   the resolution of a double near 1.618. Past that a reader holding one of
   these numbers is holding $\varphi$, and the row cannot answer them.
4. **Rank 79 is a defensible place inside that ceiling**, and I would not move
   it now. But the completeness note gives two measurements and never the
   criterion, so a reader cannot tell 79 from any other number (finding 2).
5. **The 29 rows the growth added answer no search at all**, and nothing on
   the page says so. Until a board member reviews the table, the growth has
   delivered nothing (finding 1). **Do not grow either table again until that
   review has happened and the new rows are confirmed findable.**

## How it was read

- **Skill** from <https://numberdb.org/skill>, 48,740 bytes. The prompt's
  `--socks5-hostname 127.0.0.1:1080` fetch fails in 0 ms on this runner;
  plain `curl` answers 200. Already documented; I did not look at the
  environment to find out why.
- **Documents**: `GET /api/table?id=T286`, `?id=T300`, `?id=T222`, `?id=T284`.
- **Audit**: `GET /api/table/T286/audit` returns `findings: []`, `clean: true`.
  I agree with it. Every finding below is about a range or about what search
  does with the rows, and no rule over the document can see either.
- **Rendering**: `GET /T286` returns 200 and 82,170 bytes. All 79 values
  render, the completeness note and `formula-families` render, and there is no
  "Math input error", no `argument ()`, no traceback and no swallowed section.
- **Computation**: `agents/sage.sh`, three runs. Every root of $P_n$ and $Q_n$
  in $(1,\varphi)$ for $2\leq n\leq90$ plus the root of $E$ -- 179 roots, at
  800 to 2000 bits.
- **Search**: `GET /api/lookup`, about sixty queries. The first thirty went
  without the key, hit the 60-per-hour anonymous limit, and came back as an
  `error` object that my parser read as an empty result list -- so an early
  sweep said "nothing found" for every row including the plastic ratio. Every
  measurement quoted here was rerun with the key and with the error checked.
- **Values**: not rechecked. The stored $\theta_1$ to $\theta_{10}$ agree with
  the roots my run computed, which is as far as I went.

## What the family does, measured

179 roots for $n\leq90$; every consecutive pair separated by its intervals;
179 distinct minimal polynomials, so the two families never collide. Both
families increase with $n$, so the range is naturally cut in $n$: **$E$ plus
both families to $n$ is exactly ranks 1 to $2n-1$.** The table's $n\leq40$ is
rank 79, which is why the note can state the range in one clause.

| rank | which | $\varphi-\theta_r$ | decimals shared with $\varphi$ |
|---|---|---|---|
| 50 | $Q_{26}$ | $2.67\cdot10^{-6}$ | 5 |
| 79 | $P_{40}$ | $1.95\cdot10^{-9}$ | 8 |
| 100 | $Q_{51}$ | $1.59\cdot10^{-11}$ | 10 |
| 145 | $P_{73}$ | $2.48\cdot10^{-16}$ | 15 |
| 177 | $P_{89}$ | $1.12\cdot10^{-19}$ | 18 |

Both $\varphi-\theta_r$ and the spacing $\theta_{r+1}-\theta_r$ fall by
$\log_{10}\varphi/2 = 0.1045$ per rank -- measured, and equal to the asymptotic
$\varphi-\theta(P_n)\sim\varphi^{-n}/\sqrt5$ with $r\approx2n$. Two
consequences:

- **Rank 145 is where a double stops separating $\theta_r$ from $\varphi$.**
  $2.48\cdot10^{-16}$ against an ulp of $2.2\cdot10^{-16}$ at 1.618. A reader
  who computed a growth rate in floating point and got $1.6180339887498949$
  has $\varphi$, whatever they actually computed.
- **The 100 stored digits give out at about rank 950**, where consecutive rows
  would share all 100 and a row would round to $\varphi$. That is a real
  ceiling and it is nowhere near the one that matters. (`d7e3f0c` puts this at
  rank 478; my measurement is the spacing itself rather than the $n$ at which
  a root rounds to $\varphi$, and the two differ by the factor $r\approx2n$.)

Cost, if anybody ever wanted to go to the reader's ceiling:

| rank | T286 block | T300 block | largest minimal polynomial |
|---|---|---|---|
| 79 (now) | 22.6 KB (6.9%) | 18.7 KB (5.7%) | 348 chars |
| 145 | ~46 KB (14%) | ~34 KB (11%) | 636 chars |

(The rank-145 figures add the measured growth in minimal-polynomial text --
20,378 characters to rank 145 against 6,788 to rank 79 -- to the live blocks,
plus 100 digits and the fixed part of a comment for each new row.)

The skill's readability test -- the Fibonacci polynomials came back from
$n=150$ to $n=100$ at 1107 characters an entry -- is not close to binding
either. **Nothing about this family is expensive. The whole of the range
argument is about who is holding the number.**

## Findings

### 1. The 29 rows the growth added answer no search, and are not marked

**Worth doing, and it is the reason not to grow again yet.**

What a reader sees: paste a value from the middle of the table into the search
box and get nothing back. Measured with the key, at 10, 12, 16, 20 and 30
significant digits of each stored value:

    rank  1..50   own row returned at every precision
    rank 51..79   nothing returned at any precision

T300 has the identical cut: its polynomials for ranks 1 to 50 are found, 51 to
79 are not. Two tables, two different value types, the same boundary -- and the
boundary is exactly the range each table had before this morning's growth.

Why: `_identifiable` in `numberdb_app/search.py` filters
`reviewed = True`, and a row is `reviewed` only when a board member has
reviewed the table at the revision that holds it. The growth wrote a new head
revision; rows 1--50 were unchanged and kept their flag, rows 51--79 are new
and do not have it. The skill says this plainly at section 9: "Values are held
out of search by number until a board member reviews them."

What is wrong is the second half of that sentence. The skill continues: "a
reader looking at a table can see an entry is unreviewed, and somebody typing
digits into a search box cannot." **On T286 they cannot see it.** The dagger
that exists for exactly this -- `includes/not-findable-mark.html`, whose own
comment says it is there so that "the table and the search [do not]
contradict each other" -- is driven by `not_findable`, which is
`findable_by_number(number)` in `views.py:1350`, and that function tests the
stored precision and nothing else. It has no way to know a row is unreviewed.
So 29 of 79 rows are plainly on the page, findable by no search, and unmarked.
The page I fetched contains no dagger and no other review marker.

**Smallest fix:** none that belongs to this table. The fix is the review, which
this account may not do. Somebody should be told that T286 and T300 are sitting
on 58 unsearchable rows between them. The marker gap is a site bug and is
written up in `docs/agent-environment.md` by this run.

**What it means for growth:** a range decision does not reach a reader when it
is published. Growing these tables again before the present growth is reviewed
would add more rows that answer nothing, on top of 58 that already do not.

### 2. The completeness note measures but does not decide

**Worth doing. One sentence.**

> it holds the root of $E$ and the roots of $P_n$ and $Q_n$ for
> $2\leq n\leq40$, which are $\theta_1$ to $\theta_{79}$; at $n=40$ the largest
> root is still more than $1.9\cdot10^{-9}$ below $\varphi$, while by $n=72$
> the roots are within $10^{-15}$ of $\varphi$

Both measurements are correct -- I get $1.954\cdot10^{-9}$ at $P_{40}$ and
$4\cdot10^{-16}$ at $P_{72}$. The first clause is exactly right: it states the
range in $n$, which is the index the family is cut on, and gives the ranks.

The trouble is "while". The reader is given two numbers and left to work out
what they are for. Why is $1.9\cdot10^{-9}$ enough and what would not be? What
happens at $n=72$ that stops the table -- and if it is what stops the table,
why does the table stop at 40? The skill is explicit that this note is where
the argument goes: "Say which range you chose and why in the completeness
note. That sentence is the argument, and it is what a reader checking whether
their own number belongs here actually reads."

A reader holding $\theta$ with $\varphi-\theta\approx10^{-12}$ wants to know
whether their number is missing or does not exist. As written they cannot tell.

**Smallest fix:** say what the second number is the limit of. Something like
"...; the range stops where the roots are still separated from $\varphi$ by
far more than a double can resolve, which they cease to be by $n=72$." Then
$1.9\cdot10^{-9}$ is a margin rather than a fact, and $n=72$ is the boundary
rather than an aside.

### 3. Rank 79 is defensible, and rank 145 is the most anybody could defend

**Noting. I would leave it.**

The case for staying: at rank 79 the last entry already agrees with $\varphi$
to 8 decimal places, and the rows beyond it are increasingly answers to a
question nobody asks in that form. The skill's test is "is this a value
somebody could plausibly encounter and want to identify?" -- and these are
encountered as growth rates of $\Delta(2,n+1,\infty)$ and as $\beta$-expansion
bases, where the person doing the computing knows which $n$ they used.

The case that the cost is real and already paid, measured on `/api/lookup`:

| query | results | from T286 | golden ratio |
|---|---|---|---|
| `1.618` | 51 | 26 (50%) | 1 |
| `1.6180` | 27 | 18 (66%) | 1 |
| `1.61803` | 14 | 8 (57%) | 1 |
| `1.618034` | 6 | 0 | 1 |
| `1.618033988749894848` | 6 | 0 | 1 |

A reader who types four or five decimal places of the golden ratio gets a page
that is two-thirds Pisot numbers, with $\varphi$ itself one row among them.
That is the "every hit in the corpus is worth a little less for it" cost the
skill names, and it is visible at 79 entries already. It is bounded -- at six
decimal places and beyond it vanishes -- and I do not think it argues for
shrinking. It does argue against going much past 79 for its own sake: every
additional rank lands inside those short windows and inside no others, because
every additional rank is nearer $\varphi$ than the ones before it.

Worth knowing, and against my own reading above: these measurements are of the
50 *reviewed* rows only. The flood is already 26 rows deep with 29 rows still
invisible, so reviewing the growth will make it worse before anybody decides
anything.

### 4. Growing T286 moved the ragged edge to T222

**Noting only.**

`comment-coxeter` says the root of $P_n$ is the growth rate of
$\Delta(2,n+1,\infty)$ "for every $n\geq2$", and ten rows carry an
`HREF{...#[inf,q]}` link to T222 for that group. T222 holds
$\Delta(2,q,\infty)$ only for $q\leq12$, so the links stop at rank 21
($P_{11}$). Before this morning the table held $P_n$ to $n=25$ and the links
covered 10 of 24 $P$ rows; it now holds $P_n$ to $n=40$ and they cover 10 of
39.

Nothing here is false -- the claim is a theorem for all $n$, and the links
exist where the target does. But if anybody wants a growth job in this
neighbourhood, this is the one: T222 is at 345 entries and 107 KB, and the
$r=\infty$ family is one more polynomial root each. It is a question about
T222's range, not T286's, and I have not looked at whether T222's uniform
$\leq12$ bound has a reason.

### 5. The `Programs` snippet stops at $n=29$

**Noted because I noticed it. Not worth a write on its own.**

`polys = [P(n) for n in range(2, 30)] + [Q(n) for n in range(2, 30)] + [E]`,
then `[:10]`. It is honest for what it prints -- the first ten -- and it was
already `range(2, 30)` when the table held 50. A reader who changes `[:10]` to
see more gets silently short answers past rank 57. If the note is ever
rewritten for finding 2, changing 30 to 41 costs nothing and makes the snippet
reproduce the table it sits on.

## What I could not check

- **The generator attached to the table.** `/T286/files` answers 404 to a
  bearer key; it wants a session. So I could not confirm that the attached
  `generate.py` produces the 79 rows that are there, or that it and the repair
  agree. The copy in this worktree is two commits behind and is not evidence
  either way.
- **The review flags themselves.** `reviewed` is not exposed by any route I
  can reach. The mechanism in finding 1 is inferred from `_identifiable`, from
  the boundary falling exactly at the previous range, and from the same
  boundary appearing independently in T300. I am confident but I did not read
  the flag.
