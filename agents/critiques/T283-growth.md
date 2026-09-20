# Can T283 grow? — "Mahler measures of $1+x_1+\dots+x_{n-1}$ (uniform random walks in the plane)"

Read on 2026-09-20 against the skill as served at <https://numberdb.org/skill>
that day (fetched fresh, 48740 bytes). This is a report on **range only** —
what the definition promises, how much of it is here, and how the rest would be
computed. Nothing was changed.

**How it was read.** The SOCKS proxy on port 1080 refuses connections in this
run, so `curl` went direct, which this box allows and `docs/agent-environment.md`
already records. The document came from `GET /api/table?id=T283` with the zeta3
key, the audit from `GET /api/table/T283/audit`, the rendered page from
`GET /T283` (200, 108669 bytes, no `Math input error`, no `mjx-merror`, no bare
`CITE{`/`HREF{`), the attached generator from `GET /files/T283/generate.py`, and
the repository copy from
`generators/mahler-measures-short-random-walks/generate.py`. Every numerical
claim below was computed in this run through `agents/sage.sh`, not remembered.
`agents/critiques/T283.md` is the reading of the page as prose and is not
repeated here; where it and this report disagree about the state of the table,
this one is later.

---

## First: the brief is describing a table that no longer exists

The task says T283 "has 4 entries in 6756 bytes". It has **198 entries,
$n=3$ to $n=200$, in a 12384-byte entries block** — 16% of the soft entry limit
and 3.9% of the soft block limit. The growth this report was commissioned to
recommend has already happened, on `campaign/w4` and merged into this branch:

    1b43a91  a generator for T283: the Bessel integral, between the zeros of J_0
    48c1bed  T283 generator: accelerate without Euler-Maclaurin, and carry 50 digits
    d4699e6  T283 generator states the digits each value carries
    bc8dacc  T283 generator computes each value in a child process
    bfe6872  T283 generator goes to n = 200, and takes the bound from the environment

The title changed with it, from "(short random walks)" to "(uniform random
walks in the plane)", which was the right move: a table running to $n=200$ is
not a table of short walks.

What is still at the old state is
`generators/mahler-measures-short-random-walks/table.yaml` in this repository.
Its title, `Definition`, `comment-indexing`, `complete-note` and `rigour
details` are all the pre-growth text, and it has neither `formula-mahler` nor
`comment-asymptotics`. Nothing in this repository reads it —
`data_pipeline/build.py` and `scripts/normalise_data_repo.py` read `table.yaml`
files out of the legacy *numberdb-data* checkout, not out of `generators/` — so
it is a stale working copy and not a pipeline hazard. `.gitignore:193` says as
much in so many words — "Generators are working copies, not the record", the
record being the copy attached to the table on the site — so this is the
repository behaving as designed rather than a fault, and it is noted only
because the repository copy is still the first thing the next person extending
this table will open. Noted, not ranked.

The attached `generate.py` on the site is byte-identical to the repository copy,
so the code and the table do agree.

---

## The short answer

**The definition promises an infinite family, so the table can never be
complete, and the only question is where to stop. It is not stopped early any
more. It is stopped slightly late, and for a reason that is stated on the page
and is false.**

The `Definition` reads "For $n\geq1$, let $\mu_n=m(1+x_1+\cdots+x_{n-1})$", and
the parameter constraint is `$n\geq1$` — the family, not the run, exactly as the
skill asks. There is no largest $n$ and no $n$ at which the object stops
existing, so `complete: no` is permanent and correct. Cost is not a limit
either: $J_0(x)^n$ decays like $x^{-n/2}$, so a value gets *cheaper* as $n$
grows, and `UP_TO` is an environment variable with a default of 200. Somebody
could run this to $n=1000$ this afternoon.

They should not, and I can now say why with a number rather than with taste.

**From about $n=125$ on, every one of the fifty stored digits is reproduced by
a closed-form asymptotic series with exact rational coefficients.** The 76 rows
from $n=125$ to $n=200$ are not answering a question a two-line formula does not
already answer. Below that they are: at $n=50$ the series gives 21 digits of the
50 stored, at $n=100$ it gives 40, at $n=7$ it gives 3.

So the three directions this table could still grow, ranked:

1. **Not further along $n$.** There is no case for $n>200$, and the case for
   $n>125$ is thin. See finding 1.
2. **Down to $n=1$ and $n=2$**, which are $0$ and are presently written inside
   a comment. Two rows, and the skill has a rule about exactly this. Finding 3.
3. **In digits, not in $n$.** Every row carries 50; the recommended default is
   100; $n=3$ and $n=4$ are closed forms and cost nothing. Finding 2.

---

## What the asymptotic expansion actually does

This is the measurement the rest of the report rests on, so here is the whole
of it.

Start from `formula-bessel`, which the table already states and attributes to
Borwein, Straub, Wan and Zudilin:

$$\mu_n=\log2-\gamma-\int_0^1\frac{J_0(x)^n-1}{x}\,dx-\int_1^\infty\frac{J_0(x)^n}{x}\,dx .$$

Substitute $x=y/\sqrt n$. The two pieces join into
$\int_0^\infty\bigl(J_0(y/\sqrt n)^n-\mathbb 1_{y<1}\bigr)\,dy/y$ at the cost of
a $\tfrac12\log n$, and with $\log J_0(t)=\sum_{m\geq1}\ell_m t^{2m}$
($\ell_1=-1/4$, $\ell_2=-1/64$, $\ell_3=-1/576$, …),

$$J_0(y/\sqrt n)^n=e^{-y^2/4}\exp\Bigl(\sum_{m\geq2}\ell_m\,y^{2m}\,n^{-(m-1)}\Bigr).$$

Expanding the second exponential in $1/n$ and integrating term by term against
$\int_0^\infty y^{2m-1}e^{-y^2/4}dy=2^{2m-1}(m-1)!$ gives

$$\mu_n\;\sim\;\tfrac12\log n-\tfrac{\gamma}{2}-\sum_{k\geq1}\frac{b_k}{n^k},
\qquad b_1=-\tfrac18,\; b_2=-\tfrac{5}{288},\; b_3=\tfrac1{192},\;
b_4=\tfrac{1711}{172800},\; b_5=\tfrac{101}{34560},\;
b_6=-\tfrac{153841}{12192768},\;\dots$$

every $b_k$ an exact rational, computed from the $\ell_m$ by a four-line
recurrence. The first two reproduce the two terms `comment-asymptotics` already
quotes ($1/(8n)$, and $5/288=0.017361\ldots$ over $n^2$), which is the check
that the code is right.

I computed $b_1$ to $b_{140}$ exactly, truncated at the smallest term, and
compared with the stored entries:

| $n$ | digits of the stored value the series reproduces |
|---|---|
| 7 | 3 |
| 10 | 4 |
| 15 | 6 |
| 20 | 8 |
| 30 | 12 |
| 40 | 16 |
| 50 | 21 |
| 60 | 25 |
| 70 | 29 |
| 80 | 33 |
| 90 | 37 |
| 100 | 40 |
| 110 | 44 |
| 120 | 48 |
| 130 | 49 |
| 140 | 50 |
| 150 | 49 |
| 175 | 49 |
| 200 | 50 |

From $n=130$ the count is capped by the stored precision, not by the series:
49 and 50 both mean "everything the table holds". The smallest term of the
series at $n=120$ is $1.5\times10^{-126}$ and at $n=200$ is $1.4\times10^{-157}$,
far below the agreement, so what limits the series is not truncation but the
beyond-all-orders remainder — the contribution of the first oscillation lobe of
$J_0$, of size $|J_0(j'_{0,1})|^n$ with $J_0(3.83170597)=-0.4027593957$. That
predicts $-\log_{10}(0.4027594)\,n=0.39495\,n$ digits, and the measured column
is $0.395n+1$ across the whole range. The law is not a fit; it is the constant
the table's own integrand hands over.

Fifty digits therefore arrive at $n\approx125$, and the measurement puts the
crossing between $n=120$ (48) and $n=130$ (all of them).

**Two things this is and is not.** It *is* an independent check of the
computation: the entries were made by oscillatory quadrature between consecutive
zeros of $J_0$ with Richardson and Shanks acceleration, and this is exact
rational arithmetic against Gaussian moments — no shared code, no shared
quadrature, no shared failure mode. Fifty-digit agreement at nineteen values of
$n$ is strong evidence that the generator is right, and it says so most loudly
exactly where the table's own check (reproducing Smyth's closed forms at $n=3$
and $n=4$) says least. It is *not* an independent check of the identity: both
start from `formula-bessel`. That identity is checked at $n=3,4$ against Smyth,
and nowhere else.

---

## Findings, ranked

### 1. `comment-asymptotics` defends the range with a claim that is false. Worth doing.

The page reads:

> At $n=200$ the two terms $\tfrac12(\log n-\gamma)+\tfrac{1}{8n}$ agree with
> $\mu_{200}$ to six decimal digits only, so the fifty digits stored for each
> $n$ are not predicted by the asymptotics.

The arithmetic is right — I get 6 digits from those two terms at $n=200$, and
$n(\mu_n-\tfrac12(\log n-\gamma))=0.125086674108$ there, matching the
`0.12508667\ldots` the comment quotes. The inference is wrong. "The
asymptotics" is not two terms; it is a series, and the same series at eight
terms gives 22 digits and at its optimal truncation gives all fifty. The
sentence says the far rows carry information, and they do not.

This matters more than a wrong sentence usually does, because it is the only
argument on the page for the range. A reader deciding whether $\mu_{170}$ is
worth looking up here is reading it.

Fix, replacing the second half of that comment: state the series with its first
few $b_k$, and say where it takes over —

> The expansion $\mu_n\sim\tfrac12(\log n-\gamma)-\sum_{k\geq1}b_k n^{-k}$ has
> exact rational coefficients $b_1=-1/8$, $b_2=-5/288$, $b_3=1/192$, … At its
> optimal truncation it reproduces about $0.395n$ digits, the rate being
> $-\log_{10}|J_0(j'_{0,1})|$; so it gives about 21 of the fifty digits stored
> at $n=50$, 40 at $n=100$, and all fifty from about $n=125$. The table stops
> at $n=200$ because past there the expansion serves a reader better than a
> row would.

That is a fact about the mathematics and it finishes the argument the present
sentence starts. Better still, put the expansion in `Formulas`, where it is the
thing a reader wanting $\mu_{500}$ actually needs, and let the comment point at
it. Nothing else in the table gives that reader anything.

**On cutting the range.** If somebody wants the honest line, it is $n=125$, and
I have measured it. I do not recommend cutting. The seventy-six rows from
$n=125$ on cost 4561 bytes, they do answer a search by an exact value, and
unpublishing rows is a larger act than leaving them. But **do not extend past
200**, and the reason is
not cost — the cost falls — it is that the rows would be a slower way of
evaluating a formula.

### 2. Fifty digits everywhere, where the recommendation is a hundred and two rows are free. Worth deciding; I am not sure which way.

`$n=3$` is $\mathrm{Cl}_2(\pi/3)/\pi$ and `$n=4$` is $7\zeta(3)/(2\pi^2)$.
Both are in `Formulas`, both are two lines of mpmath, and both are held to 50
digits. Those are the two numbers in this table anybody actually arrives
holding — they are Smyth's constants, they are in `Keywords` as $m(1+x+y)$ and
$m(1+x+y+z)$, and T153 holds $\mu_3/2$ and $5\mu_3$ under two other names. A
reader arriving with 60 digits of $\mathrm{Cl}_2(\pi/3)/\pi$ cannot confirm
them here.

The skill's recommendation is 100 digits and the soft limit is 500. Raising
$n=3,4$ to 100 costs one line. For the rest I ran the generator's own algorithm
at a claimed 110 digits, and the cost is not flat along the range:

| $n$ | seconds at 110 digits |
|---|---|
| 200 | 24.5 |
| 100 | 225.7 |
| 50 | killed at the 320 MB container cap (exit 137) |
| 7 | did not finish in 28 minutes |

For comparison, $n=7$ at the stored precision — the generator's `LOW`/`HIGH`,
which are working `dps` 55 and 63 — took 50.3 s and 49.3 s in the same
container. So the $n$ axis and the digit axis pull opposite ways: the rows that
are cheapest to *add* are the ones already nearest to being predicted by a
formula, and the rows anybody actually wants deeper are the expensive end.
Doubling the precision of the whole table is not an afternoon's run.

(The kill at $n=50$ is this deployment's 320 MB cap on `agents/sage.sh`, not a
property of the method — a laptop with more memory finishes it. It is recorded
in `docs/agent-environment.md`. The two values that did finish reproduce the
stored 50-digit entries, which is a precision check on the generator rather
than an independent one, since it is the same algorithm.)

So the shape of the answer, if somebody wants it: **$n=3$ and $n=4$ to 100
digits from the closed forms, and leave the rest at 50 with a sentence in
`rigour details` saying why.** Those are the two rows that are looked up, the
two that are free, and the two whose precision is limited by nothing at all.

The 80-decimal ceiling that `rigour details` quotes for $\mu_6$ is not a real
ceiling, incidentally: it bounds how far Borwein, Straub, Wan and Zudilin
confirmed the *eta-integral identity*, and from $n=7$ on this table does not
use that identity at all. The Bessel integral computes $\mu_5$ and $\mu_6$ to
whatever precision is asked for, on the same footing as every other row.

Against all of that: uniform precision is worth something, and a table reading
100, 100, 50, 50, 50, … is ragged in a way a reader has to be told about. This
is a judgement for whoever decides, not a fault. I note it because it is the
only axis along which this table has room left that would serve somebody.

### 3. $\mu_1$ and $\mu_2$ are values written into a comment. Worth doing, two rows.

`comment-indexing` ends: "The values $\mu_1$ and $\mu_2$ are exactly zero,
since $m(1)=m(1+x)=0$, and are not listed as rows." The parameter constraint is
$n\geq1$. The skill is unambiguous:

> **A value belongs in a row, not in a comment.** … A number written into an
> entry comment answers no search, carries no type, and cannot be cited.

So the one place this table's range really is short of what its definition
promises is the bottom, and closing it costs two entries. `T283#1` and `T283#2`
would then resolve, and the completeness note could say $1\leq n\leq200$
instead of explaining an exception.

The argument against is that nobody arrives holding $0$, which is true, and
that a row of `0` in a table whose rigour is `heuristic (agreement-checked)`
misdescribes two values that are exact. The second is the real objection and it
is answerable — the entry comments already carry $m(1)=m(1+x)=0$ — but somebody
should answer it rather than let it stand. This is the smallest of the three
and I would do it last.

---

## The audit

`GET /api/table/T283/audit` returns two findings, both about the attachment and
neither about range:

    generate.py does not say how to install what it imports; put the run
    commands in its docstring
    generate.py does not give the command to run it in its first forty lines

I disagree with both as stated, and agree with the convention behind them.
`numberdb_app/management/commands/audit_table.py:309` tests for the literal
strings `sage -pip install numberdb` and `sage -python generate.py`, which are
the three lines the skill's own generator template carries. The generator's
docstring, on lines 7-9, says

    $ pip install numberdb mpmath        # once
    $ python3 generate.py                # check the table against this code
    $ python3 generate.py --publish      # send it, with NUMBERDB_API_KEY set

which is a complete and correct set of run commands — this generator imports
only `mpmath` and `numberdb`, needs no Sage, and runs under plain CPython. So
"does not say how to install what it imports" is false of this file. What is
true is that a reader who downloads it into a Sage session finds the wrong
incantation, and the house convention is the Sage one. Adding the two Sage lines
beside the CPython ones satisfies the audit and loses nothing. It is a
one-minute fix and it is not a growth question.

The finding is worth passing upstream rather than just satisfying, though: a
generator that imports only `mpmath` has no reason to mention Sage, and the
audit's rule reads as if every table's code needed it. A contributor on their
own laptop with no Sage hits this on a table that is perfectly correct.

Nothing the audit checks bears on the range, and nothing it misses about the
range is something a rule could have caught: the case for stopping at 200 is a
statement about an asymptotic series, and no audit is going to derive one.

---

## What reads well, on the range specifically

- The parameter says `$n\geq1$` and the completeness note says
  "$n=3$ to $n=200$", which is the split the skill asks for — the family in
  `Parameters`, the run in `complete-note`, and neither pretending to be the
  other.
- `complete-note` names *three* methods across the range ("$n=3,4$ from closed
  forms, $n=5,6$ from conjectural eta-integral evaluations, and from $n=7$ to
  $n=200$ from the Bessel integral"), so a reader landing on a row knows what
  kind of number they have without reading `rigour details`.
- The range grew and the title grew with it. "Short random walks" would have
  been a lie about a table holding $\mu_{200}$, and somebody noticed.
- `UP_TO` being an environment variable with a documented default is the right
  shape for a bound that is a choice: the next person changes a number in a
  shell, not in a file. The only thing missing is a sentence saying the default
  is a decision.

## Reproducing the measurement

Five runs through `agents/sage.sh`. The three that establish the finding are
cheap; the two cost probes are not, and one of them was killed.

- `b_k` for $k\leq140$ as exact `Fraction`s from the $\log J_0$ series, summed
  at `mp.mp.dps = 120` against the 198 stored values, with truncation at the
  smallest term. This produced the table above.
- The same at $k\leq8$, printing the $b_k$ and
  $-\log_{10}|J_0(j'_{0,1})|=0.39495432$.
- The two-term check at $n=200$ quoted in finding 1.
- The generator's own `_mu` at working `dps` 55 and 63 for $n=7$, and at
  working `dps` 125 for $n=200,100,50$ — the timings in finding 2. The last
  exits 137 under the 320 MB cap.

The scripts were written to `/tmp` and are not in this repository; they are
about forty lines and the derivation above is enough to rebuild them. The one
piece worth keeping is the recurrence: with
$S=\sum_{k\geq1}\ell_{k+1}u^{k+1}\epsilon^k$ and $G=e^S=\sum_k P_k(u)\epsilon^k$,
take $kP_k=\sum_{j=1}^k j\,\ell_{j+1}u^{j+1}P_{k-j}$, then
$b_k=\sum_m [u^m]P_k\cdot 2^{2m-1}(m-1)!$.
