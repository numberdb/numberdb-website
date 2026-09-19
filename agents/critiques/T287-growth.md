# Can T287 grow? "Roots of the $k$-XORSAT threshold equation"

Read on 2026-09-19. T287 is public and holds 10 real values at 100 digits,
`rigour: proven`, indexed by $3\leq k\leq12$ and headed $\xi_k$: 5,548 bytes,
a fifty-eighth of the 320 KB soft block limit and a hundred-and-twentieth of
the 1200-entry one. I changed nothing.

**The answer in one paragraph.** The family is infinite, so the table is not
complete and never will be: $\xi_k$ exists and is unique for every integer
$k\geq3$, and I have the proof below rather than a sample. The range is
inherited, not chosen: the generator says it follows T272, whose note says it
follows the graph-core table, and behind both is the $k=3,\ldots,7$ table
Dietzfelbinger, Goerdt, Mitzenmacher, Montanari, Pagh and Rink printed. So the
table was stopped early in the sense that nothing about the mathematics, the
method or the limits stops it there: the attached generator computes 52 more
rows in 0.53 seconds, and it still reproduces the table exactly, so the growth
path is one constant. But the extension buys less than its price of almost
nothing suggests, because $\xi_k$ runs into the integer $k$ from below at the rate
$k^2e^{-k}$: by $k=20$ the row is $19.9999991755\ldots$, by $k=44$ nobody
computing in double precision can produce anything but $44$, and at $k=235$ the
stored hundred digits *are* the integer. **What I would do: extend to $k=20$,
not further, and only together with T272** -- every row's comment links to a
T272 row, T272 stops at 12, and a link to a row that does not exist answers 200
with a "this table has no entry" banner and no row highlighted. And the overlap
with T288 has to be settled first:
T288 now holds $\xi_{k,1}=\xi_k$ for exactly $3\leq k\leq12$, the audit says so,
and extending T287 alone would make it the longer of two copies of one column.

## How it was read

- **Skill:** <https://numberdb.org/skill>, fetched today. The SOCKS proxy on
  1080 refused every connection in this run; `curl` direct to numberdb.org
  works, as `docs/agent-environment.md` says it does, and the direct fetch is
  the thing to try before looking at the environment.
- **Documents:** `GET /api/table?id=T287`, and T272, T273, T274, T288 the same
  way. **Rendering:** `GET /T287` answers 200 to an anonymous request (it was a
  draft when `agents/critiques/T287.md` read it on 2026-09-17) and reads clean;
  this is a growth report, not a re-read, and that critique and
  `T287-repaired.md` cover the prose.
- **Audit:** `GET /api/table/T287/audit` returns one finding, `clean: false`.
  See finding 3. `manage.py audit_table` does not run here: this box has no
  Django.
- **Generator:** `https://numberdb.org/files/T287/generate.py?raw=1` is
  byte-identical to `generators/xorsat-threshold-equation-roots/generate.py`,
  and running it reports `10/10 matched, 0 differing, 0 missing, 0 extra` with
  its own integrity checks passing in 0.8 s. Unlike T288's, this generator is
  the file that made the table, so it is a growth path and not a repair job.
- **Computation:** two scripts under `agents/sage.sh`, neither writing
  anything: the roots for $13\leq k\leq64$ plus probes at 100, 150, 200,
  225--244, 250--300, a monotonicity check, and an independent mpmath solve at
  120 digits. Numbers below are measured unless they say otherwise.

## Findings, ranked

### 1. Nothing in the mathematics stops the table anywhere. Worth writing into `complete-note`, which today gives the range no reason at all.

Two facts, and they are what "can it grow naturally" means here.

**A root exists and is unique for every $k\geq3$.** Multiplying through by
$e^\xi$, the equation is $k=\psi(\xi)$ with

$$\psi(x)=\frac{x(e^x-1)}{e^x-1-x}=x+\frac{x^2}{e^x-1-x},$$

an identity worth having because everything else follows from it.
$\psi(0^+)=2$, $\psi\to\infty$, and

$$\psi'(x)=\frac{(e^x-1)^2-x^2e^x}{(e^x-1-x)^2}
        =\frac{e^x\left(4\sinh^2(x/2)-x^2\right)}{(e^x-1-x)^2}>0
\quad\text{for }x>0,$$

because $2\sinh(x/2)>x$. So $\psi$ is a bijection from $(0,\infty)$ to
$(2,\infty)$: one root for every $k\geq3$, none for $k=2$, at every range. The
Definition's word "unique" and the Parameters' constraint $k\geq3$ stay correct
however far the table runs, and no new caveat is ever needed. (`T287-repaired.md`
records this inequality as the argument used for the repair; I confirmed the
sign of the numerator and of $\sinh(x/2)-x/2$ in ball arithmetic at 1,238
points from $10^{-39}$ to 300, all decided positive.)

**The range came from a source's printed table, two tables away.** The
generator says so:

    # The range follows T272, the companion satisfiability threshold table. The
    # source table CITE{DGMMPR} prints k=3..7, and T272 extends the reference
    # range to k=12 where alpha_k is already within 4e-4 of 1.

T272's own note says its range matches "the companion graph-core table", which
is T273 at $3\leq k\leq8$. T287's note says only "matching the companion
satisfiability-threshold table". The 2026-09-17 critique already flagged that
phrase for pointing at a table instead of naming it; the growth reading adds
that it also hands the reader no reason. A reader cannot tell whether 12 is
where the family ends, where the method ends, or where somebody's afternoon
ended.

Smallest fix, and the one thing here I would do whether or not the table is
ever extended: give the note the reason, which finding 5 supplies. For example
"it holds $\xi_k$ for every $k$ with $3\leq k\leq12$, the range of
HREF{T272}[the satisfiability thresholds $\alpha_k$]; beyond it $\xi_k$ differs
from the integer $k$ by less than $10^{-4}$". That is a sentence about the
mathematics, it names the table it depends on, and it survives an extension
with two numbers changed.

### 2. Growth is coupled to T272 through every row's comment. Worth knowing before touching either; it is why I would not extend T287 alone.

All ten comments read "The associated satisfiability threshold is
`HREF{Satisfiability_thresholds_of_random_k-XORSAT#k}[$\alpha_k$]`", and T272
holds $3\leq k\leq12$ -- exactly this table's range. Extending T287 to $k=20$
gives eight rows whose comment points at a T272 row that does not exist, and I
checked what that looks like: `GET /T272?entry=13` answers **200** with the
warning "This table has no entry 13. It may have been renumbered or removed;
the table itself is shown below", no row highlighted. So it fails softly rather
than silently -- a reader sees a banner, not a 404, and `audit_table` will not
see it at all, since it checks only the slug before the `#`.

T272 is extensible on the same terms -- $\alpha_k=\xi_k/(k(1-e^{-\xi_k})^{k-1})$
is a division away from what this table already stores -- so the coupling is a
reason to extend the two together, not a reason to stop. Extend both or
neither.

### 3. The overlap with T288 has to be decided before the range is. I agree with the audit; this is its finding, and it bears directly on growth.

The audit returns exactly one thing:

    5 of the 8 distinctive values sampled here are also in T288 (Roots of the
    cuckoo hashing threshold equation); if these are the same numbers, one of
    the two tables should not exist, and if they are not, say how they differ
    in Similar tables

It is right, and the situation is worse than the sample shows. T288 was
extended since `agents/critiques/T288-growth.md` was written: its note now
reads $2\leq k\leq12$, $1\leq\ell\leq8$, and its $\ell=1$ column is
$3\leq k\leq12$. That growth critique verified character for character that
$\xi_{k,1}=\xi_k$ for all ten. So **T288 today contains the whole of T287**,
and T288's `Similar tables` says as much ("the same roots in the rows with
bucket capacity $\ell=1$ and $k\geq3$"), while neither table carries `repeats`.
The audit's sample found 5 because it samples 8; the true figure is 10 of 10.

Both tables are legitimate -- the same equation arrives in two subjects, and
the skill is explicit that context is the product -- but the skill is equally
explicit that where one table states a number first, the other says `repeats`
so search answers with the original and names the other beside it. That
decision was left for a person by the 2026-09-17 critique (finding 1) and left
again by `T288-repaired.md`. It is now the blocking question for growth: any
extension of T287 past $k=12$ lengthens a column T288 also holds, and whichever
way the duplication is resolved changes which table should be extended at all.

What the audit cannot see: anything about range. No rule it checks can tell
that a range was inherited from a printed table two tables away, or that the
values converge to the integers.

### 4. How far it could go, and by what method. Measured.

The method is the attached generator with `K_MAX` changed, and nothing else.
The bisection brackets on $[1,4k+10]$, which holds for every $k$; ball radius
is $10^{-106}$ at every $k$ I tried, out to 300; the sign checks at both ends
of the final bracket passed every time; and an independent mpmath solve at 120
digits agrees at $k=13,20,30,45,64$.

| range | new rows | new value+comment characters | added |
|---|---|---|---|
| $3\leq k\leq20$ | 8 | 1,704 | about 2.0 KB |
| $3\leq k\leq25$ | 13 | 2,769 | about 3.3 KB |
| $3\leq k\leq30$ | 18 | 3,834 | about 4.5 KB |
| $3\leq k\leq44$ | 32 | 6,816 | about 8.1 KB |
| $3\leq k\leq64$ | 52 | 11,076 | about 13.1 KB |
| $3\leq k\leq100$ | 88 | 18,746 | about 22.2 KB |

All 52 roots to $k=64$ took 0.53 s, 0.010 s each. At about 255 bytes a row the
320 KB block limit would bind near 1,250 rows and the 1200-entry limit just
before it, so **no limit in `limits.py` is anywhere near this family**: the
table could hold $3\leq k\leq1200$ and still fit. That is the wrong question,
and finding 5 is the right one.

### 5. What actually stops it: the rows become the integer $k$. Measured, and the reason to stop early rather than late.

From the identity above, $k-\xi_k=\xi_k^2/(e^{\xi_k}-1-\xi_k)$ exactly, so
$k-\xi_k\approx k^2e^{-k}$, and the number of leading digits a row shares with
$k$ is about $(k-2\ln k)/\ln10$. I checked the identity against the computed
roots at $k=3,12,40,100$: agreement to $10^{-98}$ every time.

       k        k - xi_k    digits shared with k   the row
       3       8.509e-01            0.1           2.14912579990706254207908...
       7       4.654e-02            1.3           6.95345571335347457175775...
      12       8.855e-04            3.1           11.9991145095218418799418...
      15       6.883e-05            4.2           14.9999311675349260493395...
      20       8.245e-07            6.1           19.9999991755379035746263...
      25       8.680e-09            8.1           24.9999999913200350119488...
      30       8.422e-11           10.1           29.9999999999157813932735...
      44                            16.0          the double-precision floor
      45       5.797e-17           16.2           44.9999999999999999420339...
      60       3.152e-23           22.5           59.9999999999999999999999...
     234                            97.0          the last row that says anything
     235                                          235.000000000000000000...0

Three crossings, each of which I computed as the solution of
$k-2\ln k=D\ln10$ and then confirmed by rendering the row:

- **$k\approx44$: double precision.** Past it, somebody who solves
  $\psi(x)=k$ in floating point gets exactly $k$ and can never arrive holding
  the stored value. This is the test the corpus cares about -- a table is for a
  reader who met a number -- and it is the real ceiling.
- **$k\approx125$: the table's own `Programs` snippet**, which sets
  `mp.dps = 50`. A reader following the page cannot reproduce rows past there
  without editing it.
- **$k=235$: the stored hundred digits.** I found the crossing by rendering
  every $k$ from 225 to 244: $k=234$ still shows a tail, $k=235$ and everything
  above print as $k$ followed by zeros. Those rows would breach the skill's rule
  about `3.000000000000000000` in its sharpest form: $\xi_k$ is provably *not*
  an integer, since $k-\xi_k=\xi_k^2/(e^{\xi_k}-1-\xi_k)>0$, so a row reading
  `235.000...0` is "a rounding presented as a hundred significant places", and
  here the fix is not fewer digits but not storing the row.

So the useful range ends around $k=44$ and the representable one around
$k=234$, and both are far short of any limit. Within the useful range the
honest question is the skill's: "the question is not what fits but what anybody
is looking up." Random $k$-XORSAT and blocked cuckoo hashing are read at
$k=3,4,5$; the literature's own table stops at 7; and past $k=12$ the
satisfiability threshold this root exists to produce is within $10^{-5}$ of 1.
I would extend to $k=20$, where the row still differs from the integer in its
seventh significant figure and somebody working a $p$-spin or large-$k$ 2-core
calculation could plausibly hold it, and I would stop there rather than at 44.
That is a judgement about the subject, not a measurement; the measurement is
that everything from 13 to 234 is available for 0.01 s a row.

## Noted only

- **`complete: no` is permanent and that is fine.** The prompt's "a named
  constant with one entry is finished" does not apply: this is an infinite
  family, and the note's job is to say what is covered, which it does.
- **The generator's mpmath cross-check is an absolute tolerance**
  (`abs(xi - independent) < 1e-95`) and goes vacuous far out: at $k=250$ both
  sides round to $250$ at that tolerance, so the comparison passes without
  comparing anything. Measured: it still discriminates at $k=229$ and not at
  $k=250$. Irrelevant to any range worth publishing, and the fix if anybody
  ever needs it is to compare $k-\xi_k$ rather than $\xi_k$.
- **T272 degenerates at the same rate, which is a second reason to stop.**
  From $\alpha_k=\xi_k/(k(1-e^{-\xi_k})^{k-1})$ with $\xi_k=k-k^2e^{-k}$,
  $1-\alpha_k\approx e^{-k}$: that gives $3.4\cdot10^{-4}$ at $k=8$, which is
  the figure T272's own note quotes, and $10^{-16}$ at $k\approx37$. A coupled
  extension therefore buys rows of $0.99999\ldots$ next to rows of
  $k.00000\ldots$, and it is the pair that should be judged, not either alone.
- **Ten entries is small** -- `agents/critiques/T288-growth.md` puts the corpus
  median at 502 -- but small is not a fault by itself. It is worth asking about
  here only because the range turned out to be inherited.
- **Nothing found here is a reason to hold the table back.** What it holds is
  correct, its generator reproduces it, and the range it claims is the range it
  covers. Findings 1 and 3 are about a sentence and a decision, not about the
  numbers.
