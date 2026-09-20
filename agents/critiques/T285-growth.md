# T285 growth: the range is every genus anybody has proved, and two of its rows answer no search

*For whoever merges this.* Two files already exist at this path: one written
at 02:44 today from `campaign/w2`, which found $g=7$ and $g=8$ missing, and one
at 04:03 from `campaign/w3`, which read the grown table and found its attached
generator lagging. This is a third reading, from `campaign/w4` at 05:2x–05:4x,
after the repairs both of them asked for had been made. It does not replace
either; keep all three under three names, or keep the earliest and this one.
This branch carries none of those commits.

Read on 2026-09-20. T285 is published, `rigour: proven`, 100 digits, indexed
by genus $g$ and headed $\delta_g^+$.

## The answer

**The table cannot grow by computing anything, and it is not one row short.**
Its definition promises $\delta_g^+$ for every $g\geq1$; the family is
infinite; and exactly seven of its members have ever been determined, by
anybody, in any paper: $g=1,2,3,4,5,7,8$. The table holds those seven and
nothing else. Genus 6 is open. Genus 9 and above have explicit families giving
upper bounds, and a question of Lanneau and Thiffeault, and no values. The next
entry waits on a theorem, not on CPU.

Size is not and never will be the constraint: 7 entries of the 1200 allowed,
an entries block of **1,918 bytes** — 0.59% of the 320 KB soft limit — and a
whole document of 7,803 bytes. Fifty genera, if they were ever settled, would
still be under 10 KB.

**The brief for this run said "5 entries in 5268 bytes".** That was the
document on 2026-09-16. The live table has held seven rows since 02:53 this
morning. `agents/review-queue.tsv` and the campaign brief both read from a
committed snapshot, and `docs/agent-environment.md` records that trap twice
already; it caught this run as well, one step further down (see "How it was
read").

## What is known, genus by genus, checked against the sources

| $g$ | $\delta_g^+$ | minimal polynomial | how it is known |
|---|---|---|---|
| 1 | $2.61803\ldots=(3+\sqrt5)/2$ | $x^2-3x+1$ | the torus case, recalled in LT §1 |
| 2 | $1.72208\ldots$ | $x^4-x^3-x^2-x+1$ | Cho–Ham; LT Theorem 1.1, where $\delta_2=\delta_2^+$ |
| 3 | $1.40127\ldots$ | $x^6-x^4-x^3-x^2+1$ | LT Theorem 1.2 |
| 4 | $1.28064\ldots$ | $x^8-x^5-x^4-x^3+1$ | LT Theorem 1.2 |
| 5 | $1.17628\ldots$ (Lehmer) | $x^{10}+x^9-x^7-x^6-x^5-x^4-x^3+x+1$ | LT Theorem 1.2 |
| **6** | **not known** | — | LT Theorem 1.3 gives $\delta_6^+\geq$ the largest root of $x^{12}-x^7-x^6-x^5+1$; no example attains it |
| 7 | $1.11548\ldots$ | $x^{14}+x^{13}-x^9-x^8-x^7-x^6-x^5+x+1$ | LT's Theorem 1.3 bound, realized by Aaber–Dunfield and independently by Kin–Takasawa |
| 8 | $1.12876\ldots$ | $x^{16}-x^9-x^8-x^7+1$ | LT's Theorem 1.3 bound, realized by Hironaka |
| $\geq9$ | not known | — | explicit families give upper bounds only |

Three things in that table are what the growth question turns on, and each was
read out of a source rather than recalled.

**Lanneau–Thiffeault's abstract understates their own paper, and the table's
note used to follow the abstract.** The abstract says genus six to eight are
lower bounds. The Remark after Theorem 1.3, in their LaTeX source
(`systole.tex`, lines 381–390), says: "Aaber & Dunfield and Kin & Takasawa have
found a pseudo-Anosov homeomorphism realizing $\delta_7^+$, and Hironaka has
done the same for $\delta^+_8$. Hence, all the lower bounds in [the
lower-bound table] except for genus 6 are known to be realized." The `campaign/w2` reading found this and
the repair acted on it; I confirmed it independently from the same source, and
from the other side: Aaber–Dunfield's abstract names "a genus 7 example which
minimizes dilatation among all those with orientable invariant foliations", and
Hironaka's names "the minimum dilatations for orientable mapping classes for
genus $g=2,3,4,5,8$".

**Genus 6 is open, and the bound there is a previous row.** LT's genus-6
polynomial factors as $(x^2-x+1)\cdot L(x)$ with $L$ Lehmer's polynomial — I
factored it — so their lower bound for $\delta_6^+$ *is* $\delta_5^+$ exactly.
Closing genus 6 therefore needs both an example and a better bound. Hironaka's
2014 survey (`traintrack.tex`) states the position twice: line 817, "In the
orientable case, $\delta_g^+$ has been computed for $g = 2,3,4,5,7,8$", and
line 1048, "The exact value for $\delta_6^+$ is not known."

**Nothing since has settled another genus.** I walked the 78 papers citing LT,
the 66 citing Hironaka and the 60 citing Aaber–Dunfield, by title and year
through 2026, and read the abstracts of the six that could plausibly have done
it. The work goes sideways rather than up in genus: punctured surfaces and
braids, nonorientable surfaces, restricted classes (Penner's construction, the
Thurston construction, fully-punctured maps), asymptotics of $g\log\delta_g$.
None claims $\delta_6^+$ or any $\delta_g^+$ with $g\geq9$. That is a search
over titles and abstracts, not a reading of the literature: I can say I found
nothing, not that nothing exists.

## Findings

### 1. Rows $g=7$ and $g=8$ are on the page and answer no number search. Worth doing, and not by this table.

What a reader sees: paste either new value into the search box and get nothing,
while the five older rows answer. Measured against `/api/lookup` with the key,
an interval of one unit in the 18th place around each stored value:

| row | results |
|---|---|
| $g=3$, $1.40126836793985491\ldots$ | T222, T285 |
| $g=5$, $1.17628081825991750\ldots$ | T222, T284, T285 |
| **$g=7$**, $1.11548110945659164\ldots$ | **none** |
| **$g=8$**, $1.12876086807048221\ldots$ | **none** |

Why: `/revisions/T285` shows the last **reviewed** revision is 2026-09-16
22:08. The six revisions since — 02:53, 02:53, 02:55, 04:07, 04:08 and 04:47
today — are unreviewed, so the rows they added are held out of search by number.
That is the pipeline working as designed, and the skill says so at section 9.

What is not working as designed is the justification the skill gives beside it:
"a reader looking at a table can see an entry is unreviewed". On this page they
cannot. The mark that exists for this —
`numberdb_app/templates/includes/not-findable-mark.html`, whose own comment
says it is there so that the table and the search do not "contradict each
other" — is driven by `not_findable` in `views.py:1350`, which is
`findable_by_number()` in `models.py:643`, and that function tests the stored
precision and nothing else. It cannot know a row is unreviewed. I grepped the
delivered HTML: no dagger, no review marker, nothing.

So two rows of seven are plainly on the page, findable by no search, and
unmarked, three hours after they were published.

**Smallest fix: none that belongs to this table.** The fix is the review, and
this account may not do it. Somebody should be told that T285's growth is
sitting unreviewed. The marker gap is a site defect; it is in none of the
branches' `docs/agent-environment.md`, and the skill's sentence about it is
wrong, so I have filed it as a lesson proposal rather than an environment note
— a contributor with a laptop hits exactly this after publishing.

**What it means for growth:** it does not change where the range should stop,
because the range is already where the mathematics stops. It does mean the
growth has delivered nothing to a reader yet.

### 2. The numbers column jumps from 5 to 7 with nothing at the gap. Worth doing, small.

A reader scanning the values sees `1:`, `2:`, `3:`, `4:`, `5:`, `7:`, `8:`. The
completeness note explains the gap well — "genus $6$ is open: Lanneau and
Thiffeault's lower bound for genus $6$ is $\delta_5^+$ itself, and Hironaka's
survey states that the exact value is not known" — but that note is in
`Data properties`, four sections below the numbers, and a reader holding a
genus-6 computation is looking at the column.

`comment-monotonicity` is the natural home and is already half of the sentence:
"Lanneau and Thiffeault prove $\delta_6^+\geq\delta_5^+$, so the orientable
minimum dilatations are not strictly decreasing with genus. The known values
also have $\delta_7^+<\delta_8^+$." One clause finishes it: *"There is no
$g=6$ row because $\delta_6^+$ is not known; that bound is all that is known
of it."* Then the comment says why both the odd shape of the column and the
odd shape of the sequence are real.

### 3. Noted only

- **The generator lag `campaign/w3` found is fixed.** `/files/T285/generate.py`
  is now revision 2630 and its `POLYNOMIALS` dict has all seven genera, with
  `SOURCE_ROUNDED` carrying `7: "1.11548110945659"` and `8: "1.12876"`. I
  downloaded it and read it rather than trusting the revision label. The copy
  in this worktree, `generators/minimum-dilatations-pseudo-anosov-maps/`, is
  still the five-genus file; that is this branch being behind, not the table.
- **Where an appetite for a bigger table should go**, with the genus lists,
  since the neighbours are the part of this subject that *can* grow:
  Liechti–Strenner determine the smallest stretch factor with an orientable
  invariant foliation on the closed **nonorientable** surface of genus
  4, 5, 6, 7, 8, 10, 12, 14, 16, 18 and 20 — eleven values, more than this
  table will ever have — and the smallest for an **orientation-reversing**
  pseudo-Anosov map with orientable foliations on the closed orientable surface
  of genus 1, 3, 5, 7, 9 and 11. Minimal dilatations on punctured discs
  $\delta(D_n)$ are a third family. Each is a different quantity with its own
  name, so each is a table of its own and none is a row here. A fourth,
  the roots $|LT_{1,g}|$ of the Lanneau–Thiffeault polynomials, would need
  care: for $g\equiv2,4\pmod 6$ they are dilatations of explicit orientable
  classes and hence upper bounds for $\delta_g^+$, and a table of them must
  not be titled as though they were minima.
- **The two new entry comments are attribution rather than mathematics** —
  "Aaber and Dunfield, and independently Kin and Takasawa, realized Lanneau and
  Thiffeault's lower bound for this genus" — and the same sentence is in
  `rigour details`. `campaign/w3` noted this and left it; I agree, and would
  leave it for the same reason: which theorem pins a row *is* the fact a reader
  of these two rows needs, and it is the fact that distinguishes them from the
  five above.

## What I checked hardest, and it was fine

- **The two new values, from the polynomials up.** Both roots re-isolated in
  400-bit interval arithmetic, with the polynomial required to change sign
  across the isolating interval, and the 100 digits recomputed and compared
  character by character against the stored strings. $g=7$:
  `1.115481109456591644051049459491537349015684842137962589492…`, $g=8$:
  `1.128760868070482219447652092514052433140710223291609899416…`. Both agree
  with the stored entries at all 100 places, and with the five decimals printed
  in LT's lower-bound table and in the survey's table of minimum dilatations.
- **The Salem claim, which is the one that could quietly have gone wrong.**
  `comment-salem` says the values are Salem numbers for $2\leq g\leq5$ and that
  $g=7,8$ are reciprocal Perron numbers but not Salem, "for each such $g$,
  $P_g$ has exactly three roots outside the unit circle, including
  $\delta_g^+$ itself". Over a 600-bit complex interval field: $P_7$ and $P_8$
  have exactly three roots of modulus $>1$ each, the second largest being
  $1.0828052$ and $1.0821293$, so each root is still strictly dominant and the
  number is Perron; $P_2,\ldots,P_5$ have exactly one, with every other root of
  modulus 1, so those are Salem. All seven polynomials are irreducible and
  palindromic. The comment is exactly right, including its careful exclusion of
  $g=1$, whose conjugate $0.382$ is inside the circle rather than on it — that
  value is Pisot, not Salem. A check that looks only at *real* roots reports
  both new polynomials as Salem, which is the trap; the corpus agrees from the
  other side, since T284's smallest Salem number below 1.3 is Lehmer's
  $1.17628$, and a genuine Salem number at $1.11548$ would be smaller than any
  anybody knows.
- **The audit.** `GET /api/table/T285/audit` returns `findings: []`,
  `clean: true`. I agree with it. Neither finding above is visible to a rule
  over the document: one is about the review state of a revision and the other
  is about what a reader's eye does to a column.
- **The page.** `GET /T285` answers 200 with 33,436 bytes. All seven rows
  render, the completeness note and both comments render, every `CITE{}`
  resolves to a numbered reference, and there is no "Math input error", no
  `argument ()`, no traceback and no swallowed section.

## How it was read

- **Skill** from <https://numberdb.org/skill>, 48,740 bytes, and then fetched
  a second time directly and diffed, because the first fetch was suspect (below).
  They agree but for one blank line.
- **The table**: the rendered page, `GET /api/table?id=T285`, `/revisions/T285`,
  `/files/T285` and `/files/T285/generate.py`, all read directly.
- **The sources, from their arXiv e-prints rather than from memory**:
  Lanneau–Thiffeault 0905.1302 (`systole.tex`: Theorems 1.1, 1.2, 1.3, the two
  polynomial tables, and the Remark naming who realized genus 7 and 8) and
  Hironaka's 2014 survey 1403.2987 (`traintrack.tex`: §"Orientable
  pseudo-Anosov mapping classes", its table of minimum dilatations and PF
  polynomials, and the Lanneau–Thiffeault Question). Abstracts for
  Aaber–Dunfield 1002.3423, Hironaka 0909.4517, Kin–Takasawa 1003.0545,
  Kin–Kojima–Takasawa 1104.3939, Liechti–Strenner 1806.00033 and 1807.08940,
  Hironaka–Tsang 2210.13418, Yazdi 1610.04278, Contractor–Reed 2412.16314.
  Citation lists from the Semantic Scholar graph API.
- **Sage**, through `agents/sage.sh`, two runs: root isolation and bracket
  checks for all seven stored polynomials plus LT's three lower-bound
  polynomials, the genus-6 factorisation, the 100-digit values, and the complex
  root moduli.
- **Search**: `/api/lookup` with the key, `RIF` intervals of one unit in the
  18th place, four rows.
- **Values**: recomputed, as above. The five older rows were re-derived too,
  and match.

**The first page I read was another worker's, three hours stale.** The brief's
`curl -s --socks5-hostname 127.0.0.1:1080 https://numberdb.org/T285 -o
/tmp/T285.html` reported `HTTP 000` and wrote nothing — and left in place a
`/tmp/T285.html` that a sibling campaign branch had fetched at 02:32, before
the growth. It parsed cleanly, had a complete footer, and said the table held
five rows and stopped at $g\leq5$ "given only as lower bounds". Nothing in it
looked truncated or old. `docs/agent-environment.md` on `main` already records
this exactly — "Treat `HTTP:000` with a non-empty output file as a failed fetch
of a stale file, not as a fetch" — so I have added no new note; what this run
adds is only that on this box the stale file can be *hours* old and belong to
another branch reading the same table, so the stale copy is a plausible-looking
earlier state of the very page you are checking. `curl --noproxy '*'` works and
is what every command here used after that.
