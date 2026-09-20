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
