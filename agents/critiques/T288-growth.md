# Can T288 grow? "Roots of the cuckoo hashing threshold equation"

Read on 2026-09-19. T288 holds 35 real values at 100 digits, `rigour: proven`,
indexed by $2\leq k\leq7$ and $1\leq\ell\leq6$ with $(k,\ell)=(2,1)$ absent.
13,003 bytes: a tenth of the 320 KB soft block limit, a thirty-fourth of the
1200-entry one. I changed nothing.

**The answer in one paragraph.** The table can grow, easily, and it was stopped
early: its range is not the family's and not a limit's, it is the rectangle
Dietzfelbinger, Goerdt, Mitzenmacher, Montanari, Pagh and Rink printed, copied
from the companion table T274, whose generator says so in a comment. The
definition promises $\xi_{k,\ell}$ for every $k\geq2$ and $\ell\geq1$ except
$(2,1)$, so `complete: no` is permanent and the only question is which finite
piece to hold. The natural next piece is $2\leq k\leq12$, $1\leq\ell\leq8$ --
87 rows, about 31 KB, 2.6 seconds of arithmetic, the existing generator with
two constants changed. Nothing about the method breaks there: I computed the
whole of that rectangle. What eventually stops the table is neither size nor
compute but the mathematics -- $\xi_{k,\ell}$ approaches the integer $k\ell$
exponentially fast, and past a contour I give below the stored digits are
$k\ell$ followed by zeros.

## How it was read

- **Skill:** <https://numberdb.org/skill>, fetched today. `ALL_PROXY` is empty
  in this run and `curl` reaches the site directly; the file is byte-identical
  to the copy an earlier run left in `/tmp`.
- **Document:** `GET /api/table?id=T288`, and T274, T287, T272 the same way.
  **Rendering:** `GET /T288` answers 200 to an anonymous request, 53,607 bytes,
  and reads clean; this is a growth report, not a re-read, and the 2026-09-17
  critique in `agents/critiques/T288.md` covers the prose.
- **Audit:** `GET /api/table/T288/audit` returns `{"findings": [], "clean":
  true}`. I agree with it, and note that it has nothing to say about range: no
  rule it checks can see that a rectangle came from a printed table, or that
  the corpus holds the continuation of one of this table's columns next door.
- **Computation:** three scripts under `agents/sage.sh`, none of which writes
  anything -- the whole proposed rectangle, a set of probes further out, and a
  monotonicity sample. Numbers below are measured unless they say otherwise.
- **One caveat on my own checks.** My monotonicity sample probed $f_\ell$ at
  $x=10^{-6}$ as well as on a grid, and at $\ell=8$ that probe returned NaN:
  $Q(10^{-6},9)\approx3\cdot10^{-60}$ is smaller than the cancellation error of
  computing it as $1-e^{-x}\sum x^j/j!$ at the precision I used, so the ball
  contained zero. That is my probe, not the function.

## Findings, ranked

### 1. The generator attached to the table no longer reproduces it, and it is the growth path. Worth doing first; everything else waits on it.

`https://numberdb.org/files/T288/generate.py?raw=1` is byte-identical to
`generators/cuckoo-hashing-threshold-equation-roots/generate.py` in this
repository, and both are the version from before the 2026-09-17 repair. They
still enumerate $(k,\ell)=(2,1)$, still return `QQ(0)` for it, and their
docstring still explains the "removable extension at $\xi=0$" that the table's
Definition, Formulas, Comments and `rigour details` no longer carry.

Run as its own header tells a reader to run it, and again under the sweep this
repository keeps for exactly this question:

    <VerifyReport T288: 35/36 matched, 0 differing, 1 missing, 0 extra>
    RESULT MISMATCH T288 <VerifyReport T288: 9/10 matched, ... 1 missing ...>

The 36th is the $(2,1)$ row the repair deleted. So the file exits non-zero for
anybody who downloads it, and `--publish` would put the deleted row back
together with a comment ("This is the removable limiting root") that contradicts
the page it appears on.

Smallest fix: delete the four `if k == 2 and ell == 1` branches (`root`,
`threshold_from_xi`, `value`, `_mpmath_root`), skip the pair in `enumerate`,
cut the two docstring sentences, and re-attach. The repair note
`agents/critiques/T288-repaired.md` records the repair as done for the
document; the generator was not part of it. `agents/verify-generator.py`
exists to catch this and does -- it was simply not run after the repair.

### 2. At $\ell=1$ the table stops at $k=7$ while T287 holds the same roots to $k=12$. Worth doing; it is five rows and they are already computed.

T287, "Roots of the $k$-XORSAT threshold equation", holds $\xi_k$ for
$3\leq k\leq12$, and $\xi_k=\xi_{k,1}$ -- not by an identity but because the
two equations are the same equation, which the 2026-09-17 critique established
and this table's `comment-capacity-one` states. I recomputed $\xi_{k,1}$ for
$3\leq k\leq12$ with this generator's bisection and compared the 100-digit
strings with T287's stored values: **all ten agree character for character**,
including the five ($k=8,\dots,12$) that T288 does not hold.

So the family's own $\ell=1$ column already runs to 12 in this corpus, in
another table, and T288 stops it at 7 for no reason of its own. Extending costs
five rows and no new computation.

It also sharpens a decision that is still open. Finding 1 of the 2026-09-17
critique -- keep both tables with `repeats`/`equals`, or fold T287 into T288 --
was left for a person, and `agents/critiques/T288-repaired.md` records it as
left. Today T288 contains nine tenths of T287; extended to $k=12$ it would
contain all of it. That is an argument for deciding before extending rather
than a reason not to extend, but the two should be decided together.

### 3. Bucket capacity stops at 6 because the printed table did, and 7 and 8 are the capacities implementations use. Worth doing, on judgement rather than measurement.

T274's generator says where the rectangle came from:

    # Dietzfelbinger, Goerdt, Mitzenmacher, Montanari, Pagh and Rink print a
    # table indexed by the obstructing core degree. Their row l is this
    # table's bucket capacity ell = l - 1.

and its `PUBLISHED_TEN_DIGITS` has exactly the 35 pairs T288 holds. A range
copied from a source's printed table is the source's range: it says what fitted
on their page, not which pairs a reader meets. Blocked cuckoo hashing is
implemented with a bucket that is a machine word or a cache line, so capacities
2, 4 and 8 are the ones that get built, and 8 is outside this table while 5 and
6, which nothing in particular uses, are inside. This is a judgement about the
subject and not something I measured; I flag it as that.

The arithmetic is undemanding there, and the values are still values. At
$(4,8)$ the root sits $1.1\cdot10^{-5}$ below $32$, which a double-precision
computation still distinguishes -- the test for whether anybody can arrive
holding it.

### 4. The range I would extend to, and what it costs. Measured.

$2\leq k\leq12$ and $1\leq\ell\leq8$, less $(2,1)$: **87 rows**.

| | measured |
|---|---|
| value plus comment characters | 15,012 |
| stored size, scaled by the 2.09 this table shows between those characters and its 13,003 bytes | **about 31 KB** |
| wall clock for all 87 roots at 100 digits | **2.6 s** |
| worst ball radius | $10^{-106}$, unchanged from the present rows |
| bracket sign checks at both ends | passed on all 87 |
| $\ell=1$ rows against T287 | identical, all ten |

`WORKING_GUARD = 64` still does its job at the far corner, so the method is the
existing one with `K_MAX = 12` and `ELL_MAX = 8`. 31 KB is a tenth of the soft
block limit and a fifth of the 160 KB the corpus notes take as the target.

For scale in the other direction: at 371 bytes a row the block limit binds
before the entry limit does, at about 880 rows, and the 160 KB target at about
440. Neither is anywhere near this family's useful range, which is the point of
finding 5.

The exclusion set does not grow with the range. A positive root exists exactly
when $k\ell>\ell+1$, because $f_\ell(x)=xQ(x,\ell)/Q(x,\ell+1)$ rises from
$\ell+1$ at $0^+$; for $\ell\geq2$ every $k\geq2$ satisfies it, so $(2,1)$
stays the only excluded pair however far the table runs, and the Definition and
Parameters need no new caveat. I sampled $f_\ell$ at 3000 points in $(0,150]$
for each $\ell\leq8$ and found it increasing every time, which is a sample and
not a proof; the Definition's word "unique" rests on it, and it is the same
check the 2026-09-17 critique ran for $\ell\leq6$.

### 5. What actually stops the table: the rows become the integer $k\ell$. Measured, and the reason to stop somewhere.

$\xi_{k,\ell}<k\ell$ always, and the gap closes exponentially:

$$k\ell-\xi_{k,\ell}\approx k\ell\,e^{-k\ell}(k\ell)^{\ell}/\ell!$$

which I checked against the computed roots -- $1.84\cdot10^{-10}$ against
$1.84\cdot10^{-10}$ at $(7,6)$, $3.15\cdot10^{-23}$ against $3.15\cdot10^{-23}$
at $(60,1)$, within a tenth of a digit elsewhere. In digits, the number of
leading digits a stored value shares with $k\ell$ is about
$\ell(k-1-\ln k)/\ln10$. Measured over the proposed rectangle:

          ell  1     2     3     4     5     6     7     8
    k=2         .   0.5   0.8   1.1   1.3   1.5   1.7   1.9
    k=3       0.5   1.2   1.8   2.3   2.7   3.1   3.6   4.0
    k=4       1.0   1.9   2.7   3.5   4.3   5.0   5.7   6.5
    k=5       1.4   2.6   3.8   4.9   5.9   7.0   8.1   9.2
    k=6       1.8   3.4   4.8   6.3   7.7   9.2  10.6  12.0
    k=7       2.2   4.1   5.9   7.8   9.6  11.4  13.2  14.9
    k=8       2.6   4.8   7.1   9.3  11.4  13.6  15.8  18.0
    k=9       3.0   5.6   8.2  10.8  13.4  15.9  18.5  21.0
    k=10      3.3   6.4   9.4  12.3  15.3  18.2  21.2  24.1
    k=11      3.7   7.2  10.6  13.9  17.3  20.6  23.9  27.3
    k=12      4.1   8.0  11.7  15.5  19.2  23.0  26.7  30.4

Sixteen is the number that matters: past it, somebody who computes
$\xi_{k,\ell}$ in double precision gets exactly $k\ell$ and never types the
stored value into anything. About fourteen of the 87 rows are past it --
$(12,8)$ is $95.999\ldots$ with thirty nines. They are not wrong and they are
cheap, and a high-precision arrival still lands on them, so I would keep them
inside a rectangle that is easy to state rather than cut a ragged region out of
it. But that is where the family stops repaying storage, and it is the sentence
a `complete-note` should carry: beyond roughly $\ell(k-1-\ln k)>37$ the entries
are the integer $k\ell$ with a correction below the last digit anybody computes.

A table that ran to the point where the correction falls below the hundredth
digit -- $\ell(k-1-\ln k)>230$, which includes $(2,750)$ and $(237,1)$ -- would
be storing decimal integers dressed as 100-digit reals, and the skill's rule
about `3.000000000000000000` would bite. That is far outside anything worth
holding, which is a comfortable thing to know: the useful range ends long
before the representable one.

### 6. Growth is coupled to T274. Worth knowing before extending either.

Every row of T288 carries `HREF{T274#k,ell}` in its comment, so extending T288
alone points 52 of 87 rows at rows of T274 that do not exist. I checked what
that looks like: `GET /T274?entry=12,8` answers **200** and renders the table
with nothing highlighted -- it fails silently, which is worse than a 404 for
anybody auditing. T274 has the same rectangle from the same source and the same
generator shape, so the two should be extended in one go, or neither.

## Noted only

- **`complete-note` would need one clause, not a rewrite.** It reads "it holds
  $\xi_{k,\ell}$ for every $2\leq k\leq7$ and $1\leq\ell\leq6$ except
  $(k,\ell)=(2,1)$, the case with no positive root" -- already the right shape,
  already naming the covered rectangle rather than apologising. An extension
  changes two numbers in it. What it does not say, and what finding 5 argues it
  should, is *why* that rectangle: at present a reader cannot tell the range was
  chosen rather than inherited.
- **35 entries is small for this corpus** -- the median is 502 and nineteen
  tables hold under ten -- but small is not itself a fault. Here it happens to
  coincide with a range that was inherited, which is why it is worth asking.
- **The $k=2$ column is where the numbers stay interesting furthest out.**
  $\xi_{2,16}=31.976\ldots$ and $\xi_{2,24}=47.9975\ldots$ are still three and
  four digits from their integers. If somebody wants more rows than the
  rectangle gives, large $\ell$ at $k=2,3$ is the direction that pays, not large
  $k$.
- **Nothing here is a reason to hold the table back.** What it holds is correct,
  checked three ways, and complete for the range it claims. Findings 2 and 3 are
  about a table that could serve more readers for no extra cost, and finding 1
  is about the file that would do it.
