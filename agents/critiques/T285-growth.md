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
