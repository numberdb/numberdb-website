<<<<<<< HEAD
# Can T285 grow? — "Minimum dilatations of pseudo-Anosov maps with orientable invariant foliations"

Read on 2026-09-20 against <https://numberdb.org/skill>, fetched at the start
of the run. The table is published and answers at `/T285`. It holds 5 real
values at 100 digits, `rigour: proven`, `complete: no`, indexed by genus
$g=1,\dots,5$ and headed $\delta_g^+$. Its entries block is 1450 bytes — 0.45%
of the 320 KB soft limit — and 5 entries is a 240th of the 1200 soft limit.

Nothing was changed. `manage.py audit_table` is not available on this runner;
`GET /api/table/T285/audit` returns `findings: []`, `clean: true`, and I agree
with it — the question below is not one a rule can see, because it is a
question about the literature rather than about the document.

## The answer

**The family is infinite and the table can never be complete, but the set of
*known* values is not infinite: $\delta_g^+$ has been determined for exactly
seven genera, $g\in\{1,2,3,4,5,7,8\}$, and T285 holds five of them. It can
grow by exactly two rows, today, by the method it already uses — two more
polynomials in `POLYNOMIALS` and one Sage run. After that it is finished until
somebody proves a new case.**

The two missing values are

    g = 7   1.115481109456591644051049459491537...
    g = 8   1.128760868070482219447652092514052...

Neither is anywhere in the corpus — I searched by value; see below.

**And the completeness note is now wrong.** It reads

> it holds $1\leq g\leq5$; in CITE{LT}, the next cases $g=6,7,8$ are given
> only as lower bounds

That is what Lanneau and Thiffeault's *abstract* says ("provide a lower bound
for genus six to eight"), and it is what the previous critique of this table
repaired the note to say. It is not what their paper says. Two pages later, in
the Remark following their lower-bound theorem:

> In addition, Aaber & Dunfield [Aaber2010] and Kin & Takasawa [Kin2010] have
> found a pseudo-Anosov homeomorphism realizing $\delta_7^+$, and Hironaka
> [Hironaka2009] has done the same for $\delta^+_8$. Hence, all the lower
> bounds in [the genus 6–8 table] except for genus 6 are known to be realized
> by a pseudo-Anosov homeomorphism.

A lower bound that is known to be attained is the minimum. So a reader who
arrives holding 1.1154811 is told by this page that their number is unknown,
when it has had a name and a proof since 2010.

## Findings, ranked

### 1. Add $g=7$ and $g=8$, and say that genus 6 is the open case. Worth doing.

This is the whole of the growth available, and it is two rows. The argument
for each, from the primary sources:

**Genus 7.** Lanneau–Thiffeault's lower-bound theorem gives
$\delta_7^+\geq\lambda$, $\lambda$ the largest root of
$x^{14}+x^{13}-x^9-x^8-x^7-x^6-x^5+x+1$. Aaber and Dunfield (arXiv:1002.3423,
Algebr. Geom. Topol. 10 (2010) 2315–2342) exhibit a genus-7 bundle monodromy
attaining it:

> The monodromy $\psi_7$ of the manifold $M_7$ minimizes dilatation among all
> pseudo-Anosovs of $\Sigma_7$ with orientable invariant foliations. In
> particular, one has $\delta_7^+ \approx 1.11548110945659$.

Their proof names the same polynomial as LT's ("which is exactly the
polynomial used in [LT] to give a lower bound on $\delta_7^+$"), so the two
statements are about one number, and their 14 printed digits after the point
agree with the root I isolated. Kin and Takasawa (arXiv:1003.0545, J. Math.
Soc. Japan 65 (2013), doi:10.2969/jmsj/06520411) prove it independently — their
Corollary "$\delta_7^+=\lambda_{(9,2)}$" combines their own upper bound with
LT's, over the same degree-14 factor — and each paper says the other got there
independently.

**Genus 8.** Hironaka (arXiv:0909.4517, Algebr. Geom. Topol. 10 (2010)
2041–2060) states it as a corollary of her upper bound together with LT's
lower bound:

> Putting [her upper-bound theorem] together with Lanneau and Thiffeault's lower bound for
> $g=8$ gives: **Corollary.** For $g=8$, we have $\delta_8^+ =
> \lambda_{(1,8)}$.

Her Table 1 marks $g=1,2,3,4,5,8$ with an asterisk as "verified to equal
$\delta_g^+$", and her 5-digit 1.12876 is the largest root of LT's genus-8
polynomial $x^{16}-x^9-x^8-x^7+1$. Aaber and Dunfield say the same thing from
the outside: "the work of Lanneau–Thiffeault and Hironaka combine to determine
$\delta_g^+$ when $g\in\{2,3,4,5,8\}$."

**Genus 6 is open, and interestingly so.** LT's lower-bound polynomial for
genus 6 is $x^{12}-x^7-x^6-x^5+1$, and it is not irreducible: Sage factors it
as
$(x^2-x+1)\cdot(x^{10}+x^9-x^7-x^6-x^5-x^4-x^3+x+1)$, the second factor being
Lehmer's polynomial. So the genus-6 bound *is* Lehmer's number — the table's
own $g=5$ row — which is how LT get "in particular $\delta_6^+\geq\delta_5^+$"
and the remark that genus 6 is the first genus at which $\delta_g^+$ fails to
decrease (Farb's Question 7.2). Hironaka's family produces no orientable
genus-6 example at all (her Table 1 has "–" there; her construction covers
$g\equiv 2,4 \bmod 6$). I found nothing later that settles it.

**A survey says the same thing in one sentence.** Hironaka's 2014 survey of
the minimum dilatation problem (arXiv:1403.2987, §1 and §6) states:

> In the orientable case, $\delta_g^+$ has been computed for $g=2,3,4,5,7,8$
> beginning with work by Lanneau and Thiffeault [LT09] and continuing with
> [Hironaka:LT], [AD10], [KT11].

and, in the orientable section, "An example realizing $\delta_7^+$ was found in
[AD10] and in [KT11], and an example realizing $\delta_8^+$ was found in
[Hironaka:LT]. The exact value for $\delta_6^+$ is not known." Its Table 1
lists exactly those six values, which with the torus are the seven this table
could hold; its 5-digit decimals match the roots I isolated.

So the range to aim at is $g\in\{1,2,3,4,5,7,8\}$ — a hole at 6, which is
honest and is the most interesting thing the page would then say.

### 2. What changes, concretely. Worth doing with 1; none of it is large.

In `generators/minimum-dilatations-pseudo-anosov-maps/generate.py`:

- `POLYNOMIALS`: add
  `7: x**14 + x**13 - x**9 - x**8 - x**7 - x**6 - x**5 + x + 1` and
  `8: x**16 - x**9 - x**8 - x**7 + 1`.
- `SOURCE_ROUNDED`: add `7: "1.11548110945659"` (Aaber–Dunfield's printed
  value) and `8: "1.12876"` (Hironaka's). One caution: `_rounded_interval`
  builds a *half*-ulp interval each side, which assumes the source rounded,
  and Hironaka says in so many words that her table is "truncated to 5 decimal
  places". Here it does not matter — the root is 1.1287608…, inside both the
  rounded and the truncated interval — but the helper is checking a weaker
  thing than it looks like it is, and a source that truncates at the wrong
  digit would pass or fail for the wrong reason.
- `_entry_comment`: a sentence each for the two new rows, naming who realized
  the bound. Neither value has a corpus neighbour to link (see finding 4).
- Nothing else in the method changes: both are exact integer polynomials, and
  `_root_greater_than_one` isolates in `RealIntervalField` and checks the sign
  change across the isolating interval, exactly as for the five stored rows.

In the document:

- `complete-note`: replace with something that names the real state of
  knowledge — "it holds every genus for which $\delta_g^+$ is known:
  $1\leq g\leq5$ and $g=7,8$. Genus 6 is open; CITE{LT} prove
  $\delta_6^+\geq\delta_5^+$ and no pseudo-Anosov attaining that bound is
  known."
- `formula-polynomials`: add $P_7$ and $P_8$, and attribute — the polynomials
  are LT's, the realizations are not.
- A comment for the non-monotonicity, which only becomes visible once row 7 is
  there: $\delta_7^+<\delta_8^+$, and $\delta_6^+\geq\delta_5^+$, so
  $\delta_g^+$ does not decrease with genus. Without it a reader meets two
  rows out of order and assumes a typo.
- `References`: three new entries (Hironaka; Aaber–Dunfield; Kin–Takasawa),
  each with `arxiv` and `doi` as above. This is the real cost of the two rows,
  and it is small.
- `comment-salem` needs no change but would be improved by one clause: see
  finding 3.

Cost: the entries block goes from 1450 bytes to about 2.0 KB, and the Sage run
is seconds. Nothing here is near any limit, and nothing about this table's
range is decided by size.

### 3. Say why the two new rows are *not* in the Salem table. Worth doing if 1 is done.

`comment-salem` says "For $2\leq g\leq5$, the values are Salem numbers", and a
reader who sees rows 7 and 8 appear outside that range will ask why the scope
stops at 5 — the natural guess being that nobody checked. It is not an
oversight: they are not Salem numbers. Counting conjugates in 400-bit ball
arithmetic:

    g   degree  irreducible  |conj| = 1   |conj| < 1   |conj| > 1
    2       4       yes           2           1            1      Salem
    3       6       yes           4           1            1      Salem
    4       8       yes           6           1            1      Salem
    5      10       yes           8           1            1      Salem   (Lehmer)
    7      14       yes           8           3            3      not Salem
    8      16       yes          10           3            3      not Salem

A Salem number has exactly one conjugate outside the unit circle; these have
three. So $\delta_7^+$ and $\delta_8^+$ are reciprocal Perron numbers and not
Salem numbers, which is also why they do not appear in T284 (Salem numbers
less than 1.3) or T301 even though both are well under 1.3. One clause in
`comment-salem` — "the values for $g=7,8$ are reciprocal Perron numbers but
not Salem numbers, having three conjugates outside the unit circle" — answers
the question before it is asked, and it is a fact about the mathematics rather
than about the database.

### 4. The two values are not in the corpus at all. Noted, and it is the argument for adding them.

Searched with the client, at radius $10^{-12}$:

    1.176280818259917506... (control, delta_5^+)   3 hits: T222, T284, T285
    1.115481109456591644...                        0 hits
    1.128760868070482219...                        0 hits

So the growth adds two numbers the database does not hold, rather than two
more copies of numbers it does. The control also shows the search working, and
shows what the $g=7,8$ rows would *not* get: the $g\leq5$ rows each have a
second life as a Coxeter growth rate or a small Salem number, and rows 7 and 8
will stand alone. Their entry comments should therefore carry the
realization rather than a cross-link, since there is nothing to link.

### 5. The repository's `table.yaml` is the pre-repair document. Noted only, but it will bite whoever grows this.

`generators/minimum-dilatations-pseudo-anosov-maps/table.yaml` still says
`Title: Minimum dilatations of pseudo-Anosov maps` and still carries the
"convention" comment and the "they note evidence that $\delta_5<\delta_5^+$"
clause — all three of which were repaired on the live table in September and
are correct there now. The yaml has not been touched since `496c237`. It is
not read by `generate.py` (which writes numbers only), so nothing is broken
today; but the next person to extend this table works in that directory, and
the file beside their edit is a stale copy of the document they are extending.
Either refresh it from the live document or delete it.

## Growth directions that are other tables, not this one

Each of these would make T285 bigger and all of them are refused by its own
definition — recording them so the next run does not have to re-derive the
answer:

- **$\delta_g$, the unrestricted minimum.** Known only for $g\leq2$
  (classical for the torus, Cho–Ham for $g=2$), where it coincides with
  $\delta_g^+$ and is
  already here. Two rows that duplicate rows 1 and 2 are not a table.
- **Smallest *known* dilatations.** Hironaka's genus-1-to-12 table and
  Aaber–Dunfield's, which run into the twenties, both in the orientable and
  the unconstrained case. These are upper bounds, they move when somebody
  finds a better example, and mixing them into a `rigour: proven` table of
  minima would make the header $\delta_g^+$ false of most rows. If anybody
  wants them, they are a separate table with a title that says "known".
- **The conjectural values.** LT ask whether $\delta_g^+=|p_g|$ for even $g$,
  $p_n(t)=t^{2n}-t^{n+1}-t^n-t^{n-1}+1$, which Hironaka's survey states as an
  open question.
  For $g=6$ that predicts $\delta_6^+=\delta_5^+$ exactly, since $p_6$ is
  $\sigma\cdot$Lehmer. A table of conjectured minima is a different rigour
  level and a different claim; it does not belong in this one, and a row for
  $g=6$ carrying the conjecture would be the worst of the options.
- **Punctured discs and braids.** LT's own forthcoming-paper remark, and
  arXiv:2412.01648 (2024). Different surfaces, different index, different
  table.
- **Non-orientable surfaces**, Liechti–Strenner and others: again a different
  family, and the parameter would not be the genus of $\Sigma_g$.
- **Restricted constructions** — Liechti's minimal dilatation in Penner's
  construction (arXiv:1602.07603), Contractor–Reed for the Thurston
  construction (arXiv:2412.16314). These minimize over a subclass, so they are
  neither $\delta_g$ nor $\delta_g^+$.

## How this was checked

- **Skill**: fetched at the start of the run. The SOCKS proxy on port 1080
  refused connections throughout; the site answers directly from this runner,
  as `docs/agent-environment.md` already records.
- **Document**: `GET /api/table?id=T285` with the key. **Rendering**: `/T285`
  returns 200 and 29 KB, with no `Math input error` and no `argument ()`.
- **Sources read**: the LaTeX sources of LT (arXiv:0905.1302), Hironaka
  (0909.4517), Aaber–Dunfield (1002.3423), Kin–Takasawa (1003.0545) and
  Hironaka's survey (1403.2987), pulled from `arxiv.org/e-print` — which is
  the cheap way to read a theorem statement here, since this runner has no
  `pdftotext` and the PDFs are otherwise opaque. Every quotation above is from
  the source, not from an abstract.
- **Arithmetic**: one Sage script through `agents/sage.sh`, isolating the root
  greater than 1 of each of the eight polynomials in a 400-bit
  `RealIntervalField` with a sign-change check, factoring each over $\mathbf{Q}$, and
  counting conjugates by modulus in `ComplexBallField(400)`. The five stored
  values were reproduced to the digits printed; I did not re-verify all 100
  digits of the existing rows, which is `verify`'s job.
- **Literature search**: the arXiv API, by title and abstract, on "minimum
  dilatation", "minimal dilatation", "least dilatation", "small dilatation",
  "minimal stretch factor", and by author for Takasawa, Strenner and Dunfield.
  That is a weak instrument: it does not search full text and it has no
  citation graph, and MathSciNet and zbMATH are not reachable from here. What
  it supports is "no paper whose title or abstract announces a new genus has
  appeared since 2011", and the 2014 survey is a stronger witness for the same
  period: it says $\delta_6^+$ is not known and lists $2,3,4,5,7,8$ as the
  computed cases. The gap I cannot close from here is 2014 to now. A person
  with MathSciNet should spend five minutes on the papers citing LT before the
  two rows go in — not because $\delta_7^+$ and $\delta_8^+$ are in doubt, but
  because a genus-6 or genus-9 result would be found there and not here, and
  it would change what the completeness note should say.
=======
# T285 growth: the range already is every genus that is known

*A note for whoever merges this.* `main` already carries a file at this path,
written at 02:44 today from `campaign/w2`, which found that $g=7$ and $g=8$
were missing and was acted on at 02:53. This is a second reading of the same
table taken afterwards, from `campaign/w3`, and it reaches the same conclusion
about the mathematics from the sources independently. The two do not replace
each other and this branch cannot merge cleanly: keep both, under two names.

Read on 2026-09-20 (04:0x UTC). **The table cannot grow by computing anything.**
Its definition promises $\delta_g^+$ for every $g\geq1$, and the family is
infinite, but only seven of its members have ever been determined: $g=1$ to
$5$, $7$ and $8$. Those seven are exactly the rows the table holds. Genus $6$
is open, genus $9$ and above have upper bounds and a conjecture and no values,
and no amount of precision or CPU turns either into a row. The next entry
waits on a theorem.

The brief for this run said "5 entries in 5268 bytes". That was the document
as of 2026-09-16. Another worker added $g=7$ and $g=8$ at 02:53 this morning
(revisions "added realized genus 7 and 8 orientable dilatations" and, at 02:55,
"explained realized genus 7 and 8 values"), so the table already grew to the
ceiling described here, an hour before I read it. I checked the two new rows
rather than taking them on trust; they are right, and the report below is
about what is left.

## What is known, genus by genus

| $g$ | $\delta_g^+$ | how it is known |
|---|---|---|
| 1 | $(3+\sqrt5)/2$ | the torus case, recalled in Lanneau-Thiffeault §1 |
| 2 | $1.72208\ldots$ | Cho-Ham; LT Theorem 1.1, where $\delta_2=\delta_2^+$ |
| 3, 4, 5 | $1.40127\ldots$, $1.28064\ldots$, $1.17628\ldots$ | LT Theorem 1.2 |
| **6** | **not known** | LT Theorem 1.3 gives $\delta_6^+\geq$ the largest root of $X^{12}-X^7-X^6-X^5+1$, and no example attains it |
| 7 | $1.11548\ldots$ | LT Theorem 1.3's bound, realized by Aaber-Dunfield and independently by Kin-Takasawa |
| 8 | $1.12876\ldots$ | LT Theorem 1.3's bound, realized by Hironaka |
| $\geq9$ | not known | explicit families give upper bounds only; for even $g$ the Lanneau-Thiffeault question asks whether $\delta_g^+=|LT_{1,g}|$ |

Two things in that table are worth stating in full, because they are what the
growth question turns on.

**Genus 6 is open and the bound is not weakly open.** I factored LT's genus-6
polynomial: $X^{12}-X^7-X^6-X^5+1=(X^2-X+1)\cdot L(X)$, where $L$ is Lehmer's
polynomial. So their lower bound for $\delta_6^+$ *is* $\delta_5^+$, exactly,
which is why they remark that $\delta_g^+$ is not strictly decreasing, and it
is why closing genus 6 needs two things and not one: an example, and a bound
better than the one whose value is a previous row. Hironaka's family produces
no orientable class at all when $g\equiv0\pmod 6$, so the obvious source of
examples is silent exactly here. Her 2014 survey, which the table already
cites, says it plainly: "The exact value for $\delta_6^+$ is not known."

**Nothing since 2011 has settled another genus.** I read the ~200 papers
citing Lanneau-Thiffeault, and the papers citing Hironaka and Aaber-Dunfield,
by title and year through 2026. The work that continues this problem goes
sideways rather than up in genus: to punctured surfaces and braids, to
nonorientable surfaces (Liechti-Strenner), to asymptotics of $g\log\delta_g$,
and to restricted classes. None of it claims $\delta_6^+$ or any $\delta_g^+$
with $g\geq9$. This is a metadata search, not a reading of the literature: I
can say I found nothing, not that nothing exists.

**Size is not what binds, and will not be.** The document is 7.5 KB, of which
the entries block is 1.9 KB: 7 entries of the 1200 the soft limit allows, and
0.6% of the 320 KB block limit. If every genus to 50 were somehow determined
tomorrow, 50 rows at 101 characters would still be under 10 KB. This table
will never be large, and that is a fact about the mathematics rather than a
fault.

**If a genus is settled, the method is already written.** The generator takes
a dictionary of exact polynomials, isolates the unique real root above 1 in
interval arithmetic, checks the polynomial changes sign across the isolating
interval, and compares against the rounded value printed in the source. Adding
a genus is one polynomial, one source decimal, and a run of a few seconds. The
hard part of an entry here is the citation, not the computation.

## Findings, ranked

### 1. The generator attached to the table is the five-genus file from before the growth. Worth doing.

`/files/T285` says "As of the current version, 2026-09-20 02:55" and lists
`generate.py`, 4290 bytes, last changed **2026-09-16**. I downloaded it
(`/files/T285/generate.py?raw=1`) and its `POLYNOMIALS` dictionary has genera 1
to 5 and nothing else. It is byte-identical to the copy checked in on this
branch, and differs from the seven-genus copy that `main` now carries.

So the program the site hands a reader as "the program that reproduces this
table" reproduces five of its seven rows, and says nothing about the other two.
Worse, it says so silently. I ran it as its header instructs:

    <VerifyReport T285: 5/5 matched, 0 differing, 0 missing, 0 extra>

It passes. `verify()` walks the *generator's* enumeration and compares each
identity against the table; rows the generator no longer knows about are never
looked at, and `VerifyReport.extra` is never populated by anything (see the
lesson proposal filed with this report). A reader who downloads the file,
adds a genus and runs `--publish` would be publishing from a file that does not
know $g=7$ and $g=8$ exist.

Fix: re-attach the updated `generate.py` — `main`'s copy already has the two
polynomials, the two source decimals and the two entry comments. Nothing about
the document or the values needs to change.

### 2. The completeness note says genus 6 is open without saying what it is waiting for. Worth doing, small.

The note reads:

> it holds the exact values known in the cited small-genus results:
> $1\leq g\leq5$ and $g=7,8$; genus $6$ is open in [HironakaSurvey]

The range half is right and is the sentence a reader wants. The last clause is
a citation where a fact would fit, and "open in [7]" reads as though the
openness were a property of the survey. The table already proves elsewhere
(`comment-monotonicity`) that $\delta_6^+\geq\delta_5^+$, so the missing half
sentence is short: *"genus $6$ is open: the only lower bound known for it is
$\delta_5^+$ itself CITE{HironakaSurvey}"*. That tells a reader with a
genus-6 computation both that their number is not here and why nobody's is,
which is the whole job of that line.

### 3. Noted only

- **The two new entry comments are attribution rather than mathematics.**
  "Aaber and Dunfield, and independently Kin and Takasawa, realized Lanneau and
  Thiffeault's lower bound for this genus" is also, nearly verbatim, in
  `rigour details`. The skill wants a comment to state a fact about the
  mathematics; here the fact is *which* theorem pins the row, so it is not
  wrong, and I would leave it. If it were rewritten I would make it say what
  the reader cannot see: that this row, unlike the five above it, is a bound
  proved in one paper and attained in another.
- **The two new values do not answer a numeric search yet.** The three
  revisions of 2026-09-20 are unreviewed; the last reviewed version is
  2026-09-16 22:08. That is the pipeline working as designed, and the only
  action is somebody reviewing.
- **Where the appetite for a bigger table should go.** Three neighbouring
  families have many more known values than this one ever will: minimal
  dilatations on punctured discs and braids $\delta(D_n)$, minimal stretch
  factors on closed nonorientable surfaces (Liechti-Strenner), and the
  Lanneau-Thiffeault polynomial roots $|LT_{1,g}|$, which are the dilatations
  of explicit orientable classes for $g\equiv2,4\pmod6$ and so are honest
  upper bounds for $\delta_g^+$. Each is a different quantity with its own
  name and its own literature, so each is a table of its own and none of them
  is a row here. The third would want care: its values are upper bounds, not
  minima, and a table of them must not be titled as though they were.
- **This worktree is behind.** `generators/minimum-dilatations-pseudo-anosov-maps/`
  on `campaign/w3` holds the pre-growth generator and a `table.yaml` with the
  pre-growth prose; `main` has both updated. `docs/agent-environment.md`
  already records this trap ("A critique worktree can hold a generator two
  commits behind the table it describes"), and it caught me here too: the
  brief's entry count came from the same stale place.

## What I checked hardest, and it was fine

- **The two new values.** Both were recomputed from their polynomials in
  interval arithmetic and checked the way the written digits claim: the
  polynomial changes sign across the interval the last decimal place denotes.
  $g=7$: $1.115481109456591644051049459491537349015684842137962589492\ldots$,
  sign change `- +`, freshly isolated root strictly inside. $g=8$:
  $1.128760868070482219447652092514052433140710223291609899416\ldots$, the
  same. The $g=7$ value agrees with Aaber-Dunfield's printed
  $1.11548110945659$ and the $g=8$ value with LT's and Hironaka's $1.12876$.
- **The Salem claim, which is the one that could quietly have gone wrong.**
  `comment-salem` says the values are Salem numbers for $2\leq g\leq5$ and
  that $g=7,8$ are reciprocal Perron but not Salem, "each has three algebraic
  conjugates outside the unit circle". That is exactly right, and I nearly
  believed the opposite: a check that looks only at *real* roots reports both
  new polynomials as Salem. Over `ComplexBallField` they have three conjugates
  of modulus $>1$ (second largest $1.0828\ldots$ and $1.0821\ldots$). The
  corpus agrees from the other side: T284 holds the 47 known Salem numbers
  below 1.3 and its smallest is Lehmer's number $1.17628\ldots$, so a genuine
  Salem number at $1.11548$ would have been a smaller one than anybody knows.
  The `Similar tables` gloss for T284 is correspondingly still true: it holds
  the rows $g=4$ and $g=5$, and should not be widened to the new ones.
- **The audit.** `GET /api/table/T285/audit` returns `findings: []`,
  `clean: true`. I agree with it as far as it goes, and it cannot see finding
  1: the audit reads the document, and a generator that has fallen behind the
  table it fills is invisible from there.

## How this was read

- The live page (`https://numberdb.org/T285`, 7 rows) and the document
  (`GET /api/table?id=T285`), read directly. The SOCKS proxy served two
  requests at the start of the run and then refused connections (exit 7) for
  the rest; numberdb.org and arxiv.org both answer directly from this runner,
  which is what `docs/agent-environment.md` already says.
- The sources, from their arXiv e-prints rather than from memory:
  Lanneau-Thiffeault 0905.1302 (Theorems 1.1, 1.2, 1.3, and the Remark after
  1.3 naming who realized genus 7 and 8), Aaber-Dunfield 1002.3423 (the proof
  of $\delta_7^+$, with the degree-18 polynomial and its factorization),
  Hironaka 0909.4517 (Theorem and Corollary giving $\delta_8^+=|LT_{1,8}|$,
  and Table 1), and Hironaka's 2014 survey 1403.2987, §"Orientable
  pseudo-Anosov mapping classes", which lists the determined genera as
  $2,3,4,5,7,8$ and states that genus 6 is not known.
- Sage, through `agents/sage.sh`: root isolation and bracket checks for all
  eight polynomials, the factorization of the genus-6 bound, the complex
  moduli for the Salem question, and the attached generator's own `verify`.
>>>>>>> origin/campaign/w3
