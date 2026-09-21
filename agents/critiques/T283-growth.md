# T283, "Mahler measures of $1+x_1+\dots+x_{n-1}$ (uniform random walks in the plane)": can the range grow?

Read on 2026-09-20. Nothing was changed.

## The assignment's snapshot is out of date

The assignment describes a table of **4 entries in 6756 bytes**. That was the
private draft of 2026-09-16, the one `agents/critiques/T283.md` reads, holding
$\mu_3$ to $\mu_6$; `agents/review-queue.tsv:284` still carries that row and
the old title, "(short random walks)".

The live table is not that table. It is **published**, `/T283` answers 200,
`GET /api/table/T283/audit` returns `clean: true` with no findings, and it
holds **200 entries, $n=1$ to $n=200$ with no holes**, every one to 50
significant digits. The document is 20,684 bytes, of which the entries block is
about 12.7 KB. Commits `1b43a91`, `48c1bed`, `d4699e6`, `bc8dacc`, `bfe6872`
wrote the generator that did it and carried it to $n=200$.

So the question "was it stopped early?" has already been answered once, in the
direction of growth, and the interesting question is the one left over:
**is 200 the right place to stop, and would 1200 be better?**

My answer is **no, do not grow it** — and the reason is the table's own, which
is a good reason badly served by the page. Details below.

## What I checked, and how

* **Skill**: fetched from <https://numberdb.org/skill> (47 KB), read on range
  (§"Hold the numbers that turn up") and on the limits table.
  The `--socks5-hostname 127.0.0.1:1080` form in the prompt failed with
  "Connection refused"; this builder reaches the site directly. Already recorded
  in `docs/agent-environment.md` ("On this builder there is no SOCKS proxy at
  all"), so no new note. I also hit the stale-`/tmp` trap that note warns
  about, twice.
* **Document**: `GET /api/table?id=T283`.
* **Range**: every $n$ from 1 to 200 present, none missing, none duplicated.
* **Arithmetic of the stopping argument**: `/tmp/t283_growth.py` and
  `/tmp/t283_root.py` through `agents/sage.sh`.
* **Cost of a further row**: `/tmp/t283_cost.py` through `agents/sage.sh`,
  reproducing the generator's method self-contained at $n=3$, 201, 400 and 800.
* **Values**: not rechecked. The build checked them, `verify` and the audit
  check them, and repeating that is the least useful thing I could do. Two
  things fell out anyway and both agree with the table — see "What reads well".

## The range against the definition

The Definition says "For $n\geq1$". That family is infinite, so the table can
never be complete and `complete: no` is right and permanent. The range that is
here is an initial segment of it with no gap, which is the best shape an
initial segment can have: a reader who arrives holding a number and knows their
walk had 137 steps finds row 137.

Nothing about the range is bibliographic any more. The old draft stopped at
$n=6$ because that is where the literature's closed forms stop; the current
generator's docstring says so and says why that is not a limit on what can be
computed. Rows 7 to 200 are the Bessel integral of Borwein, Straub, Wan and
Zudilin, which holds for every $n\geq3$.

## Findings, ranked

### 1. The reason the table stops hands the reader to a method the page does not equip them to use. Worth doing.

`comment-asymptotics` reads, in part:

> Truncating that series at its least term reproduces about
> $-\log_{10}|J_0(j'_{0,1})|\,n=0.394954\ldots n$ decimal digits for the
> entries here [...] It gives about 21 of the 50 stored digits at $n=50$, 40 at
> $n=100$, and all 50 from about $n=125$. The table stops at $n=200$ because
> beyond this range the asymptotic expansion is a better way to compute further
> values than adding more rows.

The constant is right. The first positive zero of $J_0'$ is $3.8317059702\ldots$,
$J_0$ there is $-0.4027593957\ldots$, and $-\log_{10}|J_0|=0.394954319\ldots$;
$50/0.394954 = 126.6$, so "all 50 from about $n=125$" is right too.

What is missing is **how many coefficients "truncating at its least term"
needs**. The least term of this series sits near $k^\ast \approx
-\ln|J_0(j'_{0,1})|\cdot n = 0.9094\,n$: about 45 terms at $n=50$, 91 at
$n=100$, **114 at $n=125$**, 182 at $n=200$. `formula-asymptotic` prints
**six**. A reader who does what the sentence says, with what the page gives
them, gets this (correct digits of $\frac12(\log n-\gamma)-\sum_{k\leq K}b_kn^{-k}$
against the stored value):

| $n$ | $K=1$ | $K=2$ | $K=3$ | $K=4$ | $K=5$ | $K=6$ | the note's claim |
|---|---|---|---|---|---|---|---|
| 20 | 4.5 | 6.2 | 7.3 | 8.7 | 8.9 | 8.8 | |
| 50 | 5.4 | 7.6 | 9.0 | 11.3 | 12.3 | **13.8** | "about 21" |
| 100 | 6.1 | 8.6 | 10.3 | 12.9 | 14.2 | **16.0** | "40" |
| 125 | 6.3 | 8.9 | 10.7 | 13.4 | 14.8 | **16.7** | "all 50" |
| 200 | 6.7 | 9.6 | 11.6 | 14.4 | 16.1 | **18.2** | |

Six coefficients cap the error at $|b_7|n^{-7}$, so they buy about $7\log_{10}n$
digits and no more, ever: 18 at $n=200$, 20 at $n=400$, 22 at $n=800$
(measured, not extrapolated). Against 50 digits on every row.

Two things follow, and the second is the growth answer. A reader told that the
expansion supersedes the table, who then wants $\mu_{201}$, gets **18 digits
where the table was giving 50** — and does not learn from the page that this is
what happened. And the rows past $n=125$ are worth more than the note lets on:
they are not redundant with anything a reader can actually run.

Smallest fix: one clause in `comment-asymptotics` saying what the six printed
coefficients deliver, and that the least-term truncation needs about $0.9n$ of
them. For instance — "the least term sits near $k=0.909\,n$, so that accuracy
needs about 114 coefficients at $n=125$; the six given here reach $|b_7|n^{-7}$,
about 16 digits at $n=100$ and 18 at $n=200$." The sentence after it then has to
change too, which is finding 2.

### 2. The number 200 is not the number the stated reason produces. Worth doing, one clause.

The note computes its own crossover — $n\approx125$ — and then stops at 200
"because beyond this range the asymptotic expansion is a better way". Those are
two different numbers with one reason between them, and a reader who follows
the arithmetic will ask what the extra 75 rows are for.

There is a good answer and the page does not give it. By finding 1 the expansion
does not in fact overtake the table at 50 digits anywhere a reader can reach, so
the honest reason for 200 is not a crossover at all: it is that the rows are
cheap, that 200 is where a walk-length table stops being something anybody looks
up, and that 200 is round.

Smallest fix: say which it is. Either "the table stops at $n=200$: the Bessel
integral is cheap and the rows are short, and beyond a couple of hundred steps
the asymptotic expansion of CITE{formula-asymptotic} is what a reader wants" —
or keep the crossover argument and stop nearer 125. I would keep the 200 and fix
the sentence; deleting 74 correct rows to match a sentence is the wrong repair.

### 3. `complete-note` says what and how, but not why this range. Worth doing, one clause.

It reads: "it holds $\mu_n$ from $n=1$ to $n=200$: $n=1,2$ are exact zeros,
$n=3,4$ from closed forms, $n=5,6$ from conjectural eta-integral evaluations,
and from $n=7$ to $n=200$ from the Bessel integral CITE{formula-bessel}". As a
statement of coverage and provenance that is better than most in the corpus —
it tells a reader holding $\mu_{93}$ exactly what they have.

But the skill puts the *why* here: "Say which range you chose and why in the
completeness note. That sentence is the argument, and it is what a reader
checking whether their own number belongs here actually reads." The why is
currently three paragraphs away in `comment-asymptotics`, where a reader
checking whether their number belongs will not look.

Smallest fix: after "$n=200$", add the reason in six words, once findings 1 and
2 have settled what it is — e.g. "...to $n=200$, beyond which a reader is
better served by the asymptotic expansion CITE{formula-asymptotic} than by more
rows". One clause, and the comment can keep the arithmetic.

### 4. "about 21 ... at $n=50$" is 19.7 by the note's own rate. Noted only.

$0.394954\times50=19.75$, and the measured optimal truncation agrees. "About 21"
is not wrong enough to matter and I would leave it; I mention it only because
the other two numbers in the same sentence (40 at $n=100$, 50 at $n=125$) match
to a tenth, so this one looks like a different calculation rather than rounding.

## If it should grow anyway: how far, by what method, at what cost

Everything needed is already in the repository and none of the three usual
brakes binds.

**Method.** `generators/mahler-measures-short-random-walks/generate.py`,
unchanged. It reads its upper bound from the environment —
`NUMBERDB_UP_TO=1200 python3 generate.py --publish` — so extending is a run,
not an edit, and `overwrite=False` means the 50-digit closed-form rows at
$n=3$ to 6 cannot be trodden on.

**Cost falls as $n$ grows**, which is the opposite of the usual case and the
reason growth is easy here: $J_0(x)^n$ decays like $x^{-n/2}$, so the
oscillatory tail converges faster the further out you go. Measured, both
working precisions, self-contained reproduction of the generator's method:

| $n$ | dps 40 | dps 48 | the two precisions agree to |
|---|---|---|---|
| 3 | 50.9 s | 57.2 s | 56.0 digits |
| 201 | 4.1 s | 4.7 s | 56.7 digits |
| 400 | 0.7 s | 1.4 s | 57.7 digits |
| 800 | 0.2 s | 0.2 s | 56.8 digits |

So $n=201$ to 1200 is on the order of ten minutes of arithmetic in total, not
hours; the wall clock would be dominated by one API request a value, which is
how the generator publishes deliberately. And the precision cap is not the
binding one either: at $n=201$ the two runs agree to 56.7 digits, so `MOST_DIGITS
= 50` is what stops the row, exactly as it does at $n=200$. Every new row would
carry the same 50 digits as the old ones.

**Size never binds.** 200 rows are about 12.7 KB of entries block at ~64 bytes a
row; 1200 rows would be about 77 KB. The soft limits are 1200 entries and 320 KB,
and the skill's own target is half of 320 KB. A table of 1200 rows here lands at
a quarter of the target.

**So the brake is the skill's question, not the machine's.** "The question a
table has to answer about its range is not how many entries that makes, nor how
simply they can be described, but whether anybody will arrive holding one of
them." Somebody arrives holding $\mu_5$ because Rodriguez Villegas conjectured
an evaluation for it. Somebody arrives holding $\mu_{40}$ because they ran a
walk. Nobody arrives holding $\mu_{950}$: by the time $n$ is that large, the
only way anyone has the number is that they computed it from
$\frac12(\log n-\gamma)+\frac1{8n}+\cdots$, and a person who computed a number
from a formula already knows what it is. Filling to 1200 would put a thousand
rows in the corpus that answer searches they cannot inform, which is the cost
the skill names and it is not storage.

**The growth worth having is in $k$, not in $n$.** The thing this table is
short of is coefficients $b_k$, not rows: twenty more $b_k$ would turn
`formula-asymptotic` from an 18-digit formula into a 30-digit one and make the
handoff at $n=200$ real, where a thousand more rows would only push the same
handoff to $n=1200$. I have **not** checked whether a recursion for the $b_k$
is published — CITE{BSWZ} and CITE{StraubZudilin} are where I would look — so
this is a direction, not a proposal, and somebody should establish that the
coefficients are derivable before anybody promises them.

## What reads well

The range is contiguous from the first member of the family, and the mixed
provenance of the rows — exact, proved closed form, conjectural evaluation,
quadrature — is labelled row by row and summarised in `complete-note`, so a
reader can tell what kind of number they are looking at without reading the
rigour note. The generator states its own stopping rule, takes its bound from
the environment, and refuses to overwrite better digits with worse. The findings
of `agents/critiques/T283.md` were acted on: $m(P)$ is now defined in the
Definition, `comment-indexing` names what it points at, and the Pólya gloss no
longer calls the step count a dimension.

Two things I did not set out to check and got for free, both agreeing with the
table: the continuation is smooth across the boundary ($\mu_{201}=2.36366694\ldots$
against the stored $\mu_{200}=2.36117628\ldots$, an increment matching the
$199\to200$ one to three figures), and `comment-asymptotics`' claim that $\mu_n$
approaches $\frac12(\log n-\gamma)$ **from above** holds at every $n$ tested,
with the gap tracking $1/(8n)$ to six figures ($0.00062232$ against $1/1608 =
0.00062189$ at $n=201$; $0.000156277$ against $1/6400 = 0.00015625$ at $n=800$).
That is $b_1=-1/8$ confirmed independently of the rows.

## Verdict

The table was stopped early once and is not stopped early now. It cannot be
complete, its range is a clean initial segment, and it has room, method and
budget to be three times the size — and should not be. Findings 1 to 3 are
about one sentence's worth of reasoning that is nearly right and is carrying
more weight than it can hold; fixing them costs three clauses and no
recomputation.
