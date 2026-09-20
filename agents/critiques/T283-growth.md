# Can T283 grow? — "Mahler measures of $1+x_1+\dots+x_{n-1}$", read 2026-09-20

**Answer: it already did, and it should now stop.** The task describes a table
of 4 entries in 6756 bytes; that is the draft of 2026-09-16. T283 today holds
**200 entries, $n=1$ to $n=200$, contiguous, 12936 bytes of entries block**.

Its range is the whole of what the definition promises in the only sense that
is reachable — the definition promises every $n\geq1$, which is infinitely many
— and the one *gap* against it, the missing $n=1$ and $n=2$, has been closed.

It could be carried to $n=1000$ for well under an hour of compute and about
58 KB, by the generator that is already attached to it, with no new
mathematics and **no new expense**: I measured a value at $n=1000$ at 0.4
seconds against 12.3 seconds at $n=200$. It should not be. §3 gives the number
that settles it. §4 is the growth worth having, and it is a `Programs` block
rather than 800 rows.

## How it was read

- **Skill.** The SOCKS proxy on 127.0.0.1:1080 is down — every `curl` I made
  through it returned exit 7 with no status. What I read as the skill is
  `.claude/skills/numberdb-table/SKILL.md`, 48740 bytes, `md5
  e88d5664…`, byte-identical to a `/tmp/skill.txt` fetched at 16:03 by another
  run on this box. `docs/agent-environment.md` already records both that the
  proxy does not recover on its own and that the repository copy is what the
  site serves. Read on ranges (§2 "Hold the numbers that turn up", §3 "include
  what is common, and stop", the limits table) and on where a range is
  recorded (§4, `complete` / `complete-note`).
- **Table.** `GET /api/table?id=T283` and `GET /T283` with the key, both from
  inside `agents/sage.sh`'s container, which reaches numberdb.org where this
  runner's Python does not.
- **Audit.** `GET /api/table/T283/audit` → `{"findings": [], "clean": true}`.
  I agree. It is silent on everything below; the audit has no notion of how
  far a range could go, and `complete: no` is not a finding to it.
- **Rendering.** 110562 bytes, 200 row labels, and zero occurrences of `Math
  input error`, `argument ()`, `Error while parsing`, or an unrendered `CITE{`
  or `HREF{`. The newly added asymptotic formula and the comment quoting it
  both typeset. Nothing to report there.
- **Generator.** `generators/mahler-measures-short-random-walks/generate.py`
  and `eta-integrals.py`.
- **Not rechecked:** the 200 values. The build and `verify` did that. One fell
  out incidentally — see §2.

### A correction to the premise, and a caution for whoever reads this next

The table has been extended twice, and the second time was today:

| when | entries | title |
|---|---|---|
| 2026-09-16 draft, still recorded in the repo's `table.yaml` | 4 ($n=3..6$) | …(short random walks) |
| snapshot on this box at 05:44 today | 198 ($n=3..200$) | …(short random walks) |
| my reads at 16:45 and 17:00 today | 200 ($n=1..200$) | …(uniform random walks in the plane) |

Everything below is about the last row. I could not have caught the middle row
honestly — the 05:44 HTML was a file another run had left in `/tmp`, which I
read believing my own `curl` had fetched it. It had not; the proxy was already
dead. Treat the counts here as of 17:00 UTC and re-read before acting.

## 1. The range is a choice, the table says so, and the reason it gives is the wrong one

This is the finding worth acting on, and it is one clause.

`complete-note` now reads, in full:

> it holds $\mu_n$ from $n=1$ to $n=200$, a contiguous range chosen because
> **the Bessel integral is cheap and the rows remain short there**, while
> larger $n$ are better described by the asymptotic expansion (4): $n=1,2$ are
> exact zeros, $n=3,4$ from closed forms, $n=5,6$ from conjectural eta-integral
> evaluations, and from $n=7$ to $n=200$ from the Bessel integral (3)

The structure is right — it is the sentence a reader checking whether their own
number belongs here wants, and it finishes "complete: no (…)" properly. But the
first reason is false in the direction it is offered. "Cheap **there**" implies
dear beyond. Measured, by the method the table itself used, at the same two
working precisions its `rigour details` names (55 and 63 digits), both
precisions per row:

| $n$ | seconds | digits the two precisions agree on |
|---|---|---|
| 200 | 12.3 | 71 |
| 300 | 12.6 | 70 |
| 500 | 2.9 | 71 |
| 1000 | 0.4 | 71 |

The cost **falls**, by a factor of thirty between $n=200$ and $n=1000$, and the
achieved precision does not degrade at all. The generator's own docstring says
as much ("the cost falls as n grows, because J_0(x)^n decays like x^{-n/2}"),
so the table is contradicted by the file attached to it. Rows do not lengthen
either: every row carries 50 significant digits at every $n$, by construction.

So neither half of the first clause bounds anything. The second clause is the
whole of the real reason, and §3 shows it is a good one.

**Smallest fix**, one clause of `complete-note`:

> it holds $\mu_n$ from $n=1$ to $n=200$, a contiguous range that stops where
> the asymptotic expansion (4) takes over rather than where the computation
> becomes hard: the Bessel integral is cheapest at large $n$, and a reader with
> a value for $n$ in the hundreds is answered by (4) to more digits than they
> are likely to hold.

Then the rest of the existing sentence, from "$n=1,2$ are exact zeros",
unchanged.

## 2. Nothing stops it growing, so the bound has to be argued rather than found

Taking the measurements in §1 at face value, $n=201$ to $n=1000$ costs:

- **Time**: roughly 20 minutes for $n=201..300$, 23 for $301..500$, 12 for
  $501..1000$ — call it an hour of Sage-box time including API round trips, and
  the generator already takes its bound from `NUMBERDB_UP_TO`, so it is one
  environment variable and no edit.
- **Size**: the mean stored entry is 56 JSON characters, so 800 more rows is
  about 45 KB, for a block of roughly 58 KB. The soft block limit is 320 KB and
  the skill's target is half of it. No objection.
- **Count**: 1000 entries is *exactly* the recommended figure, and the soft
  limit is 1200. No objection.
- **Method**: formula (3) holds for every $n\geq3$ and needs no closed form.
  No objection.

Two incidental confirmations that the method is still sound out there, neither
of them a verification pass:

- At $n=200$ my recomputation reproduced the stored value to **all 50 digits**.
- At $n=300$, $500$ and $1000$ the computed values sit above
  $\tfrac12(\log n-\gamma)+\tfrac1{8n}$ by $1.9271\times10^{-7}$,
  $6.9403\times10^{-8}$ and $1.7356\times10^{-8}$, against $5/(288n^2)$ — the
  next term of formula (4) — of $1.9290\times10^{-7}$, $6.9444\times10^{-8}$
  and $1.7361\times10^{-8}$. The ratios are 0.99899, 0.99940 and 0.99970,
  approaching 1 as they should.

So the answer to "was it stopped early?" is: it was stopped *deliberately*, at
a point nothing forced. That makes §3 the whole question.

## 3. The number that settles it: the page already answers the reader it would be growing for

Formula (4) on the page gives six coefficients of the asymptotic expansion. I
checked how many digits they actually deliver, against the table's own values,
in 70-digit decimal arithmetic:

| $n$ | correct digits from $\tfrac12(\log n-\gamma)+\tfrac1{8n}$ | correct digits from all six coefficients |
|---|---|---|
| 100 | 8 | **15** |
| 200 | 9 | **18** |
| 300 | 10 | 19 |
| 500 | 10 | 21 |
| 1000 | 11 | **23** |

This confirms the table's own comment (11), which claims "about 16 correct
digits at $n=100$ and 18 at $n=200$" — 15 and 18 on my count, so that sentence
is accurate and I would leave it alone.

It is also the argument. Split the readers who could arrive holding a value of
$\mu_n$ for $n$ in the hundreds:

- **Fewer than ~18 digits** — which is everyone who got their number from a
  simulation, a plot, or a textbook asymptotic. Formula (4) is on the page and
  answers them. A stored row tells them nothing (4) did not.
- **More than ~18 digits.** There is exactly one way to have those: compute
  formula (3) yourself. Anyone who has done that already knows what the number
  is.

The band a new row would serve is empty, and — this is the part that makes it a
stopping rule rather than a preference — **it stays empty however far you go**,
because the digits formula (4) delivers *grow* with $n$ while the digits a row
carries stay fixed at 50. There is no $n$ at which rows start paying again.
That is the skill's "include what is common, and stop", with a number attached.

**So: do not extend the range.** Not to 1000, not to 500.

Two honest qualifications, neither of which changes the verdict:

- The argument bites at $n\approx100$, not at 200. 200 is a round number, not a
  threshold. Not worth acting on: the hundred rows between cost about 6 KB, and
  shortening a published range to prove a point is worse than leaving it.
- Comment (11) notes that optimal truncation of the *full* series would
  reproduce about $0.394954\,n$ digits, so around $n=125$ the 50 stored digits
  become redundant in principle. In practice that needs about 114 coefficients
  and six are published, so it does not weaken §3 — but it does mean the table
  cannot claim the rows above 125 hold anything unobtainable, only anything
  unobtained.

## 4. The growth worth having is `Programs`, and it is now writable

`Programs` holds four lines of mpmath that compute $\mu_3$ and $\mu_4$ — two of
the 200 rows, and the two whose closed forms are already printed twice on the
page. A reader who wants $\mu_{201}$, which is the entire population §3 declines
to serve with rows, gets nothing. The skill's test for `Programs` is "the
standard incantation for a reader who wants one more value", and this fails it.

The September critique saw this and said, rightly, "leave the program as it is
unless somebody writes and checks a better one" — its own attempt with
`mp.quadosc` was wrong in the 8th place at $n=4$. I have now written and
checked one. It is the body of `generate.py`'s `_mu`, about fifteen lines, and
on this box it **reproduced $\mu_{200}$ to all 50 stored digits in 12 seconds**
and returned $\mu_{1000}$ in 0.4:

```python
import mpmath as mp

def mu(n, dps=65):                      # mu_n for n >= 3, from formula (3)
    mp.mp.dps = dps
    head = mp.quad(lambda x: (mp.besselj(0, x) ** n - 1) / x, [0, 1])
    zero = lambda k: mp.besseljzero(0, int(k))
    first = mp.quad(lambda x: mp.besselj(0, x) ** n / x, [1, zero(1)])
    # Between consecutive zeros of J_0, then accelerated: the zeros approach
    # spacing pi, so an oscillatory quadrature assuming a fixed period stalls
    # at about sixteen digits.
    tail = mp.nsum(lambda k: mp.quad(lambda x: mp.besselj(0, x) ** n / x,
                                     [zero(k), zero(k + 1)]),
                   [1, mp.inf], method="r+s")
    return mp.log(2) - mp.euler - head - first - tail
```

This is the honest way to serve an infinite tail: with a method, not with rows.
It is also the change that makes §3's "stop at 200" defensible to a reader
rather than merely stated at them — right now the page declines to hold
$\mu_{500}$ *and* declines to tell them how to get it.

Keep the existing four lines too; they are the incantation for the closed-form
rows, and both blocks are wanted. Whoever adds this should re-time it rather
than quoting my seconds: the figures above are one box, one run.

## Noted only

- **The repo's `table.yaml` is the 16 September draft.** It still carries the
  4-entry `complete-note`, the old title, no `formula-asymptotic`, and the
  Pólya gloss that the repair fixed. Nothing in `agents/` or `scripts/` reads
  it, so unlike T284's generator this cannot regress anything by being run —
  it is a stale record, not a loaded gun. Worth refreshing from the live
  document the next time somebody touches this directory, so that the next
  reader of the range does not start where I did.
- **$\mu_1=\mu_2=0$ as rows.** Two skill rules meet here and point opposite
  ways: "a value belongs in a row, not in a comment", against the warning that
  values which are a handful of small integers "match everything and tell
  nobody anything". Whoever added them chose rows, stored exact `0` (correctly
  — no decimal point, so the convention reads it as an exact integer in an `R`
  table), and put the reason in each entry comment, including Jensen's formula
  for $\mu_2$. I agree with the choice: it closes the only real gap between the
  range and the definition, and two zeros in a 55,939-entry corpus is not what
  makes search by number worse.
- **"short random walk" survives in `Keywords`** now that the title says
  "uniform random walks in the plane". That is exactly what `Keywords` is for —
  same index weight as the title, holding the literature's term for the subject
  after the title stopped using it. Right as it stands; I mention it only
  because it looks like drift and is not.
- **The keyword "Lehmer problem"** is still unjustified by anything in the
  prose, as the September critique said. Unchanged, still small, still either
  a deletion or a sentence.
- **No `Size exception` question arises** and none should: 200 entries and
  13 KB against 1200 and 320 KB.

## What I checked hardest, and what I did not

Hardest, because §3 turns on it: that the six published coefficients really do
give 15 to 23 digits across the range, computed in `decimal` at 70 places
against the table's own stored values rather than taken from comment (11) —
which it then confirmed. And that the cost of formula (3) genuinely falls with
$n$ rather than merely being claimed to, measured at four values of $n$ at both
of the working precisions the table declares, with $n=200$ as a control against
the stored value.

Not checked: whether coefficients $b_7$ onward are published anywhere. If they
are, the "114 coefficients" qualification in §3 weakens and rows above
$n\approx125$ become redundant in practice as well as in principle — which
would strengthen the verdict, not change it. I did not reach the literature:
the proxy was down for the whole run, and I asked the container for
numberdb.org only, never for an outside site, so I do not know whether it
would have answered.

Also not checked: the 200 values, beyond the single $n=200$ control.
