# Can T286 grow? — "Pisot numbers less than the golden ratio"

Read on 2026-09-20 against <https://numberdb.org/skill>, fetched at the start
of the run. The table is published and answers at `/T286`. It holds 50 real
values at 100 digits, `rigour: proven`, `complete: no`, indexed by rank
$r=1,\dots,50$ and headed $\theta_r$. Its entries block is 13.3 KB — 4% of the
320 KB soft limit — and 50 entries is a twenty-fourth of the 1200 soft limit.

Nothing was changed. `manage.py audit_table` was not available here; the API
audit (`GET /api/table/T286/audit`) returns `findings: []`, `clean: true`, and
I agree with it: nothing below is a thing a rule could see.

## The answer

**The family is infinite, so the table can never be complete, and `complete:
no` is right. It can grow, and growing it is nearly free — two constants in
the generator and about two minutes of Sage. But this family has a ceiling no
version of this table can pass: the values converge to $\varphi$, and at rank
471 two consecutive entries are written identically at 100 significant
digits.** Between the present 50 and that 471 sit four softer limits, and the
tightest of them — how precise a reader's own number has to be before the
table can tell them which row they hold — falls at about rank 70.

**50 is a good place to be stopped, and I would not grow it.** If somebody
does, 100 is the most I could argue for and the completeness note would have
to say what the extra fifty are for. The growth that would actually serve a
reader is sideways, not upwards in rank; see the last section.

## What the definition promises

"For an integer $r\geq1$, $\theta_r$ is the $r$-th smallest
Pisot–Vijayaraghavan number in the interval $(1,\varphi)$." That is an
infinite set: Dufresnoy and Pisot showed $\varphi$ is the smallest limit point
of the Pisot numbers, so the ones below it form an increasing sequence
converging to $\varphi$, and the page says so in `comment-classification`. A
"complete" T286 is not a thing that exists. The range is therefore always an
initial segment, and the only question is where to cut it.

The range that is here is an exact initial segment, not a ragged one. I
rebuilt the family independently of the generator and checked three things:

- for $n=2,\dots,150$ each of $P_n$ and $Q_n$ has exactly one root in
  $(1,\varphi)$, giving 299 distinct minimal polynomials with **no duplicates
  at all** — the deduplication step in `generate.py` never fires in this
  range;
- each family's root is strictly increasing in $n$, throughout, which is what
  makes truncating $n$ safe and is the argument the rigour details already
  give;
- the first 50 ranks need $n\leq26$, the first 100 need $n\leq51$, the first
  200 need $n\leq101$ — rank $\approx 2n$, the two families interleaving
  $P_n,\ Q_{n+1},\ P_{n+1},\ Q_{n+2},\dots$

So the method for growing is: raise `RANKS` and `MAX_N` in
`generators/pisot-numbers-less-than-golden-ratio/generate.py`, with
`MAX_N` a little above `RANKS/2 + 1`. Nothing else in the method changes.

## Cost is not what stops it

Measured under `agents/sage.sh`, in the deployed image:

    all 479 Pisot numbers with n <= 240, factored and isolated   67 s
    P_500 (degree 502): factor over Q                           0.6 s
    P_500: isolate the root in RealIntervalField(512)           1.1 s

The whole of what could ever be stored costs about a minute. Compute is not a
constraint at any range this table could want, and a critique that stopped at
"it is only 50 of 1200" would be right that there is room and wrong about what
the room is for.

## Ceiling 1 — the values run out of room. Hard, rank 470.

$\varphi-\theta$ shrinks geometrically: measured against the computed roots,
$\varphi-\theta(P_n)=0.4472\,\varphi^{-n}$ and
$\varphi-\theta(Q_n)=0.7236\,\varphi^{-n}$, to six figures from $n=40$ on.

What decides whether two rows can be told apart is not that, though, but the
*spacing between neighbours*, and it closes twice as fast. Because
$0.7236/\varphi=0.4472$ exactly, $\theta(P_n)$ and $\theta(Q_{n+1})$ agree to
first order, and their separation is second order:

    theta(Q_n+1) - theta(P_n)  =  0.276393 * phi^(-2n)     (measured, n = 20..100)
    theta(P_n)   - theta(Q_n)  =  0.276393 * phi^(-n)

So every other gap in the table is the square-rooted one. Building the sorted
list out to $n=240$ and writing each value to the 100 significant digits the
table stores, **the first collision is at ranks 471 and 472** — $P_{236}$ and
$Q_{237}$ produce the same decimal string, character for character. That is
the end of the family as a 100-digit table: past it the table would hold two
rows a reader cannot distinguish and search cannot separate, which is the
opposite of what a table is for.

Already at rank 50, ranks 49 and 50 ($P_{25}$ and $Q_{26}$) are $9.8\cdot
10^{-12}$ apart, and $\varphi-\theta_{50}=2.67\cdot10^{-6}$ — both as the
completeness note says.

## Ceiling 2 — the entries block grows quadratically. Rank ~330.

Each comment carries the minimal polynomial. The $Q_n$ rows are cheap — the
minimal polynomial is always $x^{n+2}-x^{n+1}-x^n+x^2-1$, about 35 characters
— but the $P_n$ rows carry a polynomial with between $n/2$ and $n$ terms. So
the block is not 267 bytes an entry as the current 50 suggest; it is
quadratic. Reconstructing the entries in the live table's own wording and
measuring the block as `numberdb_app/limits.py` measures it:

    ranks     block      of soft limit     longest comment
       50    13.0 KB           4%              251 chars
      100    29.3 KB           9%              485
      200    74.8 KB          23%              937
      300   138.9 KB          43%             1437
      400   222.2 KB          69%             1937
      470   291.3 KB          91%             2277

(13.0 KB against the live table's 13.3 KB: the reconstruction is not
byte-identical, so read these as the shape rather than to the byte.)

The skill says to aim at **half the soft limit, about 160 KB**, "not at the
limit… a table that only just fits cannot be extended by the next person".
That lands at about rank 330. The two ceilings very nearly coincide: the
arithmetic runs out at 470 and the block is 91% full at the same place.

## Ceiling 3 — the entry stops being readable. Rank ~230.

The skill's own precedent: the Fibonacci polynomials came back from $n=150$ to
$n=100$ because "$F_{150}$ is 2248 characters and $F_{100}$ is 1107, and
somewhere between those an entry stops being something anybody reads". T286's
comments cross 1107 characters at about rank 230 and 2248 at about rank 465.
By the standard the corpus already applied to another table, this one should
not pass 230.

There is a nearer version of the same complaint, visible on the page today.
Rows 39 to 50 all begin `1.61802` or `1.61803`, and rows 49 and 50 agree in
their first eleven digits. A reader scrolling the column sees it stop varying
a fifth of the way from the bottom. Growing the table extends that stretch and
nothing else.

## Ceiling 4 — the reader's own number stops picking out a row. Rank ~70.

This is the one that decides it, and it is about what happens when somebody
arrives holding a number.

Search is interval overlap, and the query is an interval no narrower than the
reader's own precision. Somebody who arrives from a numerical computation has
a `double`: about 16 to 17 correct significant digits, so a query about
$10^{-16}$ wide. The narrow gaps measured above fall below $2\cdot10^{-16}$
at $n=37$, which is **ranks 73 and 74**. From there on, every second pair of
entries sits inside one query interval, the table answers such a reader with
two rows and no way to choose between them, and by rank 140 the wide gaps have
gone the same way and the ambiguity is general.

Below about rank 70 the table always answers with exactly one row. That is a
real boundary, it is a fact about this family and about how precisely anybody
arrives rather than a fact about the website, and it is the best argument I
can find for any number larger than the present 50.

Two live checks behind that, and they disagree with each other, which is worth
knowing before anybody repeats them. The site's own search box is generous —
it reads a typed decimal as uncertain in its last place:

    /suggestions?term=1.3247            -> T286 row 1, and T222's [inf,3]
    /suggestions?term=1.324717957       -> T286 row 1, and T222's [inf,3]

The API's expression endpoint is not. It *evaluates* what it is given, so a
truncated decimal is a different number and matches nothing:

    /api/search?expression=1.324717957244746   -> T222 and T286
    /api/search?expression=1.32471795724474    -> nothing
    /api/search?expression=1.618033988749895   -> T32, T35, T153, T222, T297
    /api/search?expression=1.61803398874989    -> nothing

Neither changes the ceiling, which comes from the reader's precision and not
from the parser: on the generous path the query interval is one unit in the
reader's last digit, and on the strict path it is a few ulps of a double.
Both are about $10^{-16}$ for somebody holding a `double`.

## Ceiling 5 — nobody arrives holding $\theta_{200}$. Rank ~21.

The skill's actual test for a range: "is this a value somebody could plausibly
encounter and want to identify?" Everything I can check says the answer stops
being yes early.

- Wikipedia's "Small Pisot numbers" table, which the rigour details name as
  the source check, lists **ten**, each with its own OEIS A-number
  (A060006, A086106, A228777, A092526, A293508, A293509, A293557, A374002,
  A293506, A374003). Somebody thought those ten worth a sequence each. There
  is no eleventh.
- The corpus gives a second identity to ten rows: ranks 1, 4, 6, 9, 11, 13,
  15, 17, 19, 21 are the growth rates of $\Delta(2,n+1,\infty)$ in T222, for
  $P_2$ through $P_{11}$. Rows 1 and 4 are the plastic and supergolden ratios.
  **Past rank 21 no row on the page has any identity but its rank.**
- Dufresnoy and Pisot's paper itself, per the note Wikipedia hangs on it,
  lists the smallest of these numbers in numerical order on one page.

Ranks 22 to 50 are already the part of the table nobody comes looking for, and
they earn their place by being the completion of a classified set rather than
by being met. That is a fair reason for fifty and a thin one for five hundred.

## If somebody does extend it, three things to do first

**1. The generator in the repository is not the one that made the live table,
and new rows would come out in the old style.** `generators/pisot-numbers-
less-than-golden-ratio/table.yaml` and `generate.py` are the pre-critique
version (last touched in `f4889d1`); the repairs listed in
`agents/critiques/T286-repaired.md` were made on the site. `entry_comment`
still produces the fragment style — "`$P_{2}$ family; minimal polynomial
$x^{3} - x - 1$; this is the plastic ratio.`" — where the live rows read "A
root of $P_{2}$, with minimal polynomial $x^{3} - x - 1$. This is the plastic
ratio, the smallest Pisot number." Rows 1–50 are safe: `_publish` compares the
*number* and skips an entry whose value is unchanged, so the old comments are
never written back. Rows 51 upwards are not: they would be added with the
comment style the critique removed, and the table would read in two voices.
Bring `generate.py` and `table.yaml` up to the live document before adding a
single row.

**2. The guard on `MAX_N` is a count, not the argument.** `records()` raises if
fewer than `RANKS+1` roots were found, which does not by itself show that no
larger $n$ supplies a smaller root. The rigour details give the real argument
(both families increase in $n$; $P_{26}$ and $Q_{27}$ already exceed
$\theta_{50}$). Make the code assert *that*: that $\theta_{\text{RANKS}}$ is
below the roots of $P_{\text{MAX\_N}}$ and $Q_{\text{MAX\_N}}$. Otherwise
`proven` stops covering the index as soon as somebody moves the constants.

**3. The completeness note names $n\leq25$ and $n\leq26$ and $\theta_{50}$,**
and the rigour details name $P_{26}$ and $Q_{27}$. All four numbers move.

## The growth that would be natural is sideways

The definition of this table is a completed classification: "all Pisot numbers
in $(1,\varphi)$" is a theorem with two polynomial families and one
exceptional polynomial as its answer, and 50 of them is a generous
illustration of it. What a reader holding a small Pisot number actually risks
is holding one *above* $\varphi$ — where the set is no longer a sequence, is
not given by a closed family, and is where the computational literature
is (Boyd's work on Pisot and Salem numbers in intervals of the real line,
already in the Wikipedia article this table links). A companion table there
would answer searches T286 cannot, and would be a new table rather than more
rows of this one. I have not costed it and it needs its own check of what is
known; I note it because "can this grow" has a better answer than a larger
`RANKS`.

## What I checked hardest, and what I did not

Hardest: the collision rank, which I first derived from the asymptotic
$0.2764\,\varphi^{-2n}$ and then confirmed by building all 479 numbers with
$n\leq240$ and comparing the written strings — the prediction (rank 471) and
the direct search (ranks 471 and 472) agree exactly. Second, the quadratic
block growth, because the linear extrapolation from the present 50 entries
gives ~1200 entries at the soft limit and is wrong by a factor of four.
Third, the search threshold, probed on two different numbers in two different
tables.

Not checked: the values, which `verify` and the audit cover; and whether the
literature contains a longer list of small Pisot numbers than Wikipedia's ten
— I read the Wikipedia source and the table's own references list, not
Dufresnoy–Pisot or Bertin et al. themselves. If Bertin's appendix tabulates
forty, that is an argument for forty and I did not see it.
