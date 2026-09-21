# T18, "Feigenbaum constants": can it grow?

Read on 2026-09-21 as a growth review. 6 entries, 7558 bytes in the stored
entries block — 0.5% of the 1200-entry soft limit and 2.3% of the 320 KB block
limit. The question asked was whether the range is the whole of what the
definition promises, or whether the table was stopped early.

**Answer: it is finished, and not by anybody's decision to stop.** Its subject
is one object — the period-doubling renormalisation fixed point for a map with
a quadratic critical point — and that object has six numbers attached to it:
$\alpha$, $\delta$, the zero $b$ of the fixed-point function, the real and
imaginary parts $c$ and $d$ of its nearest complex singularity, and the order
$\kappa$ of that singularity. All six are here. There is no index to run: no
degree, no order, no argument, nothing that takes a next value. This is the
"a named constant with one entry is finished" case, with six constants instead
of one.

That is the good answer, but it is not the whole of this table's situation,
because **T18 nowhere says it is complete** — it carries no `complete` key at
all — and because it is *large* on the axis nobody watches. Its longest value
writes 1019 digits, twice the 500-digit soft limit, and that is the corpus
maximum recorded in `numberdb_app/limits.py`: the table at the top of that
column is this one. It carries no `Size exception`. The audit's single finding
is exactly that, and I agree with it.

There is also one row genuinely missing, and it is a convention rather than a
range: §4. A reader holding the second Feigenbaum constant in the form
Wikipedia, MathWorld and the OEIS sequence this table links for it all print —
$2.502907875\ldots$, positive — is told **"No match in database"**. I measured
that in the search box, not inferred it.

## 1. How I read it

- **Rendered page:** `curl https://numberdb.org/T18` — direct, no proxy. The
  SOCKS proxy at `127.0.0.1:1080` refuses connections on this runner;
  `docs/agent-environment.md` records it already, `ALL_PROXY` is empty and
  `NUMBERDB_REMOTE=local`, and direct HTTPS works for numberdb.org and for
  every outside source below. The page sets cleanly: no broken mathematics,
  no `argument ()`, no eaten `<`, and the six entry anchors `#delta`, `#alpha`,
  `#b`, `#c`, `#d`, `#kappa` all exist in the HTML.
- **Document:** `GET /api/table?id=T18`. Six entries, type `R`,
  `rigour: heuristic`, `reliability: unknown`, `sources: CITE{Broadhurst}`,
  **no `complete`, no `complete-note`**. `Comments`, `Formulas`, `Programs`,
  `Keywords`, `Similar tables` and `Display properties` are all empty.
- **Provenance:** `/revisions/T18`. Seven revisions: three imports from the
  data repository in March 2021, three 2026 migrations, and one annotation by
  bmatschke on 2026-08-15 that added the `rigour details` paragraph. The
  numbers have not been touched in five and a half years.
- **Generator:** there is none. Nothing in `generators/` mentions T18 and
  `Programs` is empty, which is consistent with `rigour details`: the values
  are transcribed.
- **The source:** `http://www.plouffe.fr/simon/constants/feigenbaum.txt`, the
  Broadhurst letter of 22 March 1999 that the table cites. I read all of it.
  §2 is what it says.
- **Audit:** `GET /api/table/T18/audit` — one finding, the digit count. §6.
- **Search:** a dozen candidate values looked up by digits against
  `/api/lookup`, and the three of §4 typed into the search box on `/` as a
  reader would. §3 and §4 are what they measured.
- **Computation:** three runs of `agents/sage.sh`, on `/tmp/feig.py`,
  `/tmp/feig4.py` and `/tmp/feig6.py`, implementing Briggs's collocation
  scheme. §3.1 and §7.

## 2. Why there is no seventh entry

The six constants are not a selection. They are the complete analytic
description of one function, and Broadhurst's letter states the whole of it in
five lines. With $g$ and $f$ even, $g(0)=f(0)=1$:

$$g(\alpha x)/\alpha = g(g(x)), \qquad
  \delta f(\alpha x)/\alpha = g'(g(x))f(x) + f(g(x))$$

with $\delta$ as large as possible, and then $b$, $c$, $d$ the positive numbers
with

$$g(b) = 0 = 1/g(c+id)$$

and $b$, $c^2+d^2$ as small as possible, and $\kappa$ the order of that
singularity, $1/g(c+id+z) = O(z^{\kappa})$ as $z \to 0$. That is: the scaling
constant, the eigenvalue, the nearest real zero, the nearest complex
singularity, and its order. Nothing else about $g$ is a number somebody quotes.

Two facts confirm the table took all of it rather than some of it. Broadhurst's
file contains exactly these six values and no others. And the digit counts
match his two sentences: "the Feigenbaum zero nearest to the origin was located
to 1018 places. The nearest complex singularity was located to 868 places" —
so $\alpha$, $\delta$, $b$ carry 1018 decimals here and $c$, $d$, $\kappa$
carry 868. The table reproduces that split silently; §5 item 5 is the one
clause that would explain it.

So the definition's promise and the range coincide. The promise is worded
badly — "additional Feigenbaum constants considered by Broadhurst" is a
bibliographic boundary, not a mathematical one, and §5 item 2 is about that —
but the numbers behind the wording are a closed set, and they are all present.

## 3. The three things that look like growth

### 3.1 More digits: this is precision, and the table is already over the limit

1018 places is what Broadhurst published, and he says what it cost: three days
on a 433 MHz DEC alpha at a collocation of $N=700$ points, checked in three and
a half days at $N=720$. Going beyond that means redoing that computation, not
transcribing a better source; the only other high-precision value I could find,
Hofstätter's 2015 Julia notebook, reaches 245 digits.

I ran the scheme myself to see what it costs today. `/tmp/feig.py` implements
Briggs's method (Newton on the collocation equations
$g(1)g(x_i) = g(g(g(1)x_i))$, then $\delta$ as the largest eigenvalue of
$V^{-T}L$ by the power method), in mpmath inside `agents/sage.sh`:

    dps=60,  n=40   alpha to 52 correct digits, delta to 49    24 s + 35 s
    dps=120, n=80   alpha to 99 correct digits, delta to 97   161 s + 148 s

"Correct" means a literal character-by-character prefix of what T18 stores.
**So the stored values are reproducible and the transcription is sound** — this
is not a correction job. That is a *rigour* opportunity, not a range one: a
recomputation of a few hundred digits costs minutes and would let `rigour` stop
saying "transcribed from the literature" and `reliability` stop saying
"unknown".

What it would not do is add digits. The accuracy is set by $n$, and matching
Broadhurst means $n \approx 700$ at about 1030 digits of working precision,
where the $n^3$ dense solve in this implementation stops being reasonable:
extrapolating the two runs above gives weeks, not the three days he spent in
1999 with a tuned program. Somebody could certainly do better than my hundred
lines of mpmath, and the point stands either way — **these digits are the
expensive kind**, which matters for the next paragraph.

What matters for growth is the other direction. The table writes 1019 digits
including the leading one, against a soft limit of 500, and it carries no
`Size exception`. `numberdb_app/limits.py` says in as many words that the
500-digit threshold "flags four tables, which are exactly the 'these digits
were expensive' cases that ought to say so". T18 is one of the four and does
not say so. Broadhurst's own sentence is the missing justification.

### 3.2 Other critical orders $z$: a real family, and it cannot live here

$\delta$ and $\alpha$ exist for every map with a critical point of order $z$,
not just $z=2$, and that is an honest index: one pair of constants for each
$z$, which is the skill's "a parameter that is an argument, not a name" case.
The values are published — OEIS A195102 is $|\alpha|$ for the biquadratic
($z=4$) solution of the Feigenbaum–Cvitanović equation, and its b-file gives 49
digits — and I could not find any of them in this corpus: `1.690302971`,
`7.2846862` and every other candidate in §3.3 answer "no match" today.

Three things nevertheless say this is a separate table and not more rows here.

1. **The server refuses it.** Adding a parameter $z$ changes the set of
   parameter names, and `numberdb_app/editing.py` raises `ParametersChanged`
   on any published table for exactly the reason that matters here: "Every
   entry's identity is its parameter values, so changing the set or the order
   of parameters silently reassigns every identity in the table."
2. **Citations already resolve on the current identities.** T168 links
   `HREF{Feigenbaum_constants#delta}` from its Feigenbaum formula, and the
   published skill uses `HREF{Feigenbaum_constants#delta}[$\delta$]` as its
   worked example of linking a number rather than a table. Both point at the
   address `delta`, which a second parameter would turn into `2,delta`.
3. **The precision would be ragged and stay ragged.** 1018 digits at $z=2$
   against 49 at $z=4$ and fewer elsewhere, and $b$, $c$, $d$, $\kappa$ have no
   published analogue at $z \neq 2$ at all, so most of the grid would be empty.
   The skill names a ragged range as a sign of two tables rather than one
   unfinished.

The method does carry over — §7 says how far I got running it at $z>2$ — so a
table "Feigenbaum constants for maps with a critical point of order $z$" is a
buildable proposal for somebody who wants it. It is not this table's range.

### 3.3 Other universality classes: same name, different objects

Period-$n$-tupling has its own pair for each $n$ ($\delta \approx 55.26$,
$\alpha \approx 9.277$ for the period-3 window, Delbourgo, Hart and Kenny,
*Phys. Rev. A* **31** (1985) 514); area-preserving maps have
$\delta \approx 8.7211$; the golden-mean circle map has
$\delta \approx 2.8336$. None of these is in the corpus — I checked each by
digits and got no match — and each is a different fixed point of a different
renormalisation operator that shares a discoverer's name. That is the skill's
"several named objects share a subject but not a name": separate tables, tied
by `Similar tables`, not rows here. The honest caveat for whoever proposes
them is that the quoted precision is four to seven digits, which is thin.

## 4. The one row that is missing, and it is a sign

T18 stores $\alpha = -2.5029\ldots$, which is Broadhurst's convention and is
right: the negative sign is the one that makes $g(\alpha x)/\alpha = g(g(x))$
true, and the skill is clear that a table should not throw away a sign its
source certified. But the positive form is what almost every reader holds.
Wikipedia prints $\alpha = 2.502907875\ldots$; MathWorld prints it positive;
and so does **the OEIS sequence this table itself links for it**, A006891,
"Decimal expansion of Feigenbaum reduction parameter", whose b-file begins
`1 2`, `2 5`, `3 0`.

Measured in the reader's search box, `https://numberdb.org/?q=...`:

    2.5029078750958928     ->  No match in database
    -2.5029078750958928    ->  1 result: Feigenbaum constants #alpha
    4.6692016091029906     ->  1 result: Feigenbaum constants #delta

and `/api/lookup` agrees: the match is on the signed value, and nothing tries
the negation. So the second-most-famous constant in bifurcation theory is
unfindable from the form in which it is usually written, in the table that
holds it.

The fix that serves that reader is a row. The corpus has the precedent
exactly: the skill names "$\beta$ and $e^\beta$ for Lévy's constant" as two
entries of one table because a reader holding either should land in the same
place, and $|\alpha|$ is the same thing one step cheaper. It costs about 1 KB
and no parameter change — a new *value* of the existing `constant` parameter is
an ordinary edit, only the set of parameter *names* is frozen — and it would be
the only row this table has ever needed. A comment saying the convention is a
weaker second best: it helps a reader who has already arrived, which is the
reader who needed no help, and the skill forbids putting the value itself in a
comment.

I would not do the same for $1/\alpha$ or $\alpha^2$: those are arithmetic a
reader can guess. A sign is not a guess a search box makes for you.

## 5. The changes worth making, ranked

**1. Make $|\alpha|$ findable** — §4. It is the only change here that alters
what a reader with a number in their hand gets back.

**2. Say what $b$, $c$, $d$ and $\kappa$ are.** The definition reads in full:
"$\delta$ and $\alpha$ are the first and second Feigenbaum constants. $b$, $c$,
$d$, $\kappa$ are additional Feigenbaum constants considered by Broadhurst."
The second sentence defines nothing: it names a person and a paper. Two people
could not build this table from it, a reader holding $1.8312\ldots$ cannot tell
from the page what they have, and — this is the growth consequence — nobody
except the source can say what a seventh entry would be. The smallest fix is to
put Broadhurst's two functional equations in `Formulas` and one sentence in
`Comments` saying that $b$ is the zero of $g$ nearest the origin, $c+id$ its
nearest complex singularity and $\kappa$ the order of that singularity. The
`Definition` itself should stay two sentences.

**3. Write `complete: yes` and the note.** The table says nothing at all about
its range today. One clause — "it holds every constant Broadhurst's
computation of the period-doubling fixed point produced: $\alpha$, $\delta$,
the zero $b$ of $g$, the nearest singularity $c+id$, and its order $\kappa$" —
is this whole review in a sentence, and it is what stops the next growth run
asking the same question.

**4. Add the `Size exception`.** 1019 digits against a soft limit of 500, with
the reason already written in the source: three days of computation at $N=700$
in 1999, checked at $N=720$. This is the audit's only finding and it is right.

**5. Explain the 1018/868 split** in `rigour details`, one clause: the zero
nearest the origin was located to 1018 places and the nearest complex
singularity to 868, which is why three entries are shorter. A reader who counts
digits currently sees an inconsistency where there is a fact.

**6. Fill `Similar tables`.** It is empty, while three tables point here and
name the relation: T168 (the ratios of consecutive bifurcation gaps tend to
$\delta$), T169 (each window's cascade has the same $\delta$) and T171 (the
logistic map at $r=4$ is the endpoint of the route). The link that matters most
is T168, which holds the cascade itself, including $r_\infty$ and its
$c$-normalised value $-1.4011551890\ldots$ — the number a reader who has been
reading about "the Feigenbaum point" is most likely to arrive with, and which
is correctly *not* in T18.

Items 3, 4, 5 and 6 are prose and cost an hour between them. Item 2 is the one
that makes the table self-contained. Item 1 is the one a reader would notice.

## 6. The audit, and what it did not see

`GET /api/table/T18/audit` returns one finding:

    size: the longest value writes is 1019 digits, above the usual limit of 500

**I agree with it**, and §5 item 4 is the fix: not fewer digits — these are the
expensive kind the limit exists to admit — but the sentence saying why.

Four things this review found are outside its rules, and two of them look cheap
to add:

- **No `complete` key at all.** A published table that says nothing about its
  range is a commoner fault than an empty `complete-note` and nothing checks
  for it. This one would have fired here.
- **A reference nobody cites.** `References[Fei]`, the Feigenbaum 1976 report,
  appears as "[1]" on the page and no `CITE{Fei}` exists anywhere in the
  document. Either the definition's history clause should cite it or it is
  furniture. Grepping the document for each reference key is a two-line check.
- **`Similar tables` empty while other tables link in.** The site knows both
  sides of that; an audit could say "three tables link here and this one links
  back to none".
- **The sign convention of §4.** That one is a judgement about the literature
  and I would not want a rule to guess at it.

## 7. What I ran at $z > 2$, and what it cost

`/tmp/feig6.py` solves the collocation system at each even order in turn, each
starting from the previous order's coefficients, at 40 digits and $n=30$
collocation points with a damped Newton step, and checks $|\alpha|$ at $z=4$
against the 49 digits of OEIS A195102.

    z=2  alpha=-2.50290787509589282228390287322  delta=4.66920160910299067185320382047   15s + 23s
    z=4  alpha=-1.69030297140524485334378031653  delta=7.28468621707334336430901359271   15s + 21s
    z=6  alpha=-1.46774245031990094445510360324  delta=9.29624683277137010279834724033   17s + 20s
    z=8  alpha=-1.35801727913805033563858191915  delta=10.9486242659415917950588174843   15s + 21s

The collocation residual is below $10^{-39}$ throughout. The $z=2$ row is a
prefix of what T18 stores, and $|\alpha|$ at $z=4$ agrees with OEIS A195102 to
24 significant digits, which is what $n=30$ collocation points support; $n$ and
the working precision are the only things between that and Broadhurst's 1018.
The $z=6$ and $z=8$ rows have no independent check here beyond the residual,
and would need one before anybody published them.

Two practical notes for whoever does. Continuation in a *non-integer* $z$ is
not a route: $g(1)$ is negative, so a fractional power of $g(1)x_i$ leaves the
reals, mpmath returns a complex number and nothing raises — a first attempt
stepping $z$ by $1/4$ ran for twelve minutes and produced plausible-looking
complex $\delta$ before it was caught. Even $z$ needs no continuation anyway:
Newton converges at $z=8$ from the $z=2$ coefficients. And the sign question of
§4 is systematic rather than particular to $z=2$ — the computation gives
$\alpha<0$ at every order, and OEIS lists the magnitude at every order.

This is recorded for whoever picks up §3.2, not because T18 should hold any of
it.

## 8. What I checked hardest and did not find

- **Is it one table?** The `constant` parameter takes six *names*, which is the
  structure the skill warns about. Here it is the good kind, and specifically
  the first good kind: parts of one object. All six numbers are attached to the
  single function $g$ of §2, a reader holding one wants the others beside it,
  and the value column does not fall back on the word `value` — each row is
  labelled with its own symbol, `show-in-parameter-list` is `no`, and there is
  no `number-header` claiming something untrue of any row. `param-latex` is not
  used, correctly: these values *are* words, so the symbol map is the right
  tool, and no column repeats a heading.
- **Does it read as prose?** Two sentences, both finished, no dashes, no
  fragments, nothing pointing at "the former" or "the first factor", and no
  claim anywhere about how good a search hit would be or what a reader should
  conclude. The `rigour details` paragraph is unusually honest — "nothing in
  this table connects these digits to that work" — and is the reason this
  review could tell transcription from computation at a glance.
- **Does the page render?** Yes, and I looked at the HTML rather than the
  document: the 1018-digit values sit in ordinary `table-number` cells like
  every other table's, all six anchors resolve, and the citation superscripts
  work. The only oddity is cosmetic and is the site's, not the table's: the
  definition's two citations render as "[6][3]" because reference numbering
  follows the Links block rather than first use.
- **Is anything named that should be linked?** No family the corpus holds is
  named in T18's prose at all — the prose is two sentences — so there is
  nothing to link inward. The missing links are the outward ones of §5 item 6.

---

Nothing in this report was applied. The table stands as it was.
