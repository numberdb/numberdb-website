<<<<<<< HEAD
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
=======
# T286, Pisot numbers less than the golden ratio: can it grow?

Read on 2026-09-20 against <https://numberdb.org/skill>, fetched the same day.
The table is public and holds 50 real values at 100 digits, `rigour: proven`,
indexed by rank $r$, in 18526 bytes.

What I ran:

* `GET /api/table/T286/audit` — `"findings": [], "clean": true`. I agree; the
  audit has nothing to say about a range, and this report is about the range.
* `/tmp/t286_growth.py` under `agents/sage.sh`: built $P_n$ and $Q_n$ for
  $2\leq n\leq100$ plus $E$, isolated each Pisot root, and measured
  $\varphi-\theta_r$, the gap to the neighbouring entry, and the characters
  each entry would cost, out to rank 190.
* `/tmp/t286_reach.py`: checked the Coxeter identity the entry comments assert,
  at $q$ past where they assert it.
* `/tmp/t286_search.py`: counted, for each stopping rank, how many rows a
  search for $\varphi$ written to $k$ places would return. Controlled against
  the live site, which agrees exactly.
* Live lookups: `/api/lookup?text=1.618`, `1.61803`, `1.6180339887`.

## The short answer

**The table was not stopped early. It is stopped at about the last place it
could be stopped without making the corpus worse, and the note on the page
already gives the right reason.** The definition promises an infinite sequence
and always will: $\theta_r$ is defined for every $r\geq1$, the $\theta_r$
increase to $\varphi$, and no finite table is complete. So the question is not
whether 50 is the end but whether 50 is a good place to stand, and it is.

Growing it is mechanically trivial — one constant in the generator — and every
resource limit is far away. What stops it is the one thing the database is for.
The values converge to $\varphi$ geometrically, so past rank 50 each new entry
is another decimal place of agreement with the most-searched constant in the
corpus, and it arrives in search results as a rival to it.

Nothing below asks for the table to be changed. Findings 3 and 4 are about the
things around it.

---

## 1. Why the range cannot grow: search, and nothing else. Worth knowing; nothing to do.

Three constraints could bind, and two of them do not.

**Size does not bind.** Entry text runs 10.1 KB at rank 50 and 60.5 KB at rank
190; scaled by the ratio the live block shows at rank 50, a table to rank 190
would be about 111 KB, inside the 320 KB soft limit and inside the skill's
160 KB target.

**Readability does not bind.** The longest entry comment is 251 characters at
rank 50 and 881 at rank 190 — the polynomial is dense for even $n$ in the $P$
family and sparse for odd, so the comment length alternates. 881 characters is
still under the line the skill draws with the Fibonacci polynomials, where
1107 was kept and 2248 was not.

**Precision does not bind.** Neighbouring entries stay apart at 100 digits far
past any range anyone would propose: the nearest-neighbour gap is
$9.8\cdot10^{-12}$ at rank 50 and $5.4\cdot10^{-41}$ at rank 190, and two
stored values would not become the same 100-digit string until about rank 460.

**Search binds, and it binds now.** $\varphi-\theta_r$ falls like
$\varphi^{-n}$: the first value agreeing with $\varphi$ to 6 decimal places is
rank 45, to 10 places rank 83, to 15 places rank 131. A decimal written to $k$
places denotes the interval its last digit denotes, so the rows a query for
$\varphi$ returns are:

    query for phi     rows of T286 inside it, if the table stops at
    to k places       r=50      r=100     r=150     r=190
      3 (1.618)         26        76        126       166
      5 (1.61803)        8        58        108       148
      6                  0        46         96       136
      8                  0        28         78       118
     10                  0        10         60       100

The live site confirms the first column exactly. `/api/lookup?text=1.618`
returns 51 results today, **26 of them rows of T286** — half the answer to the
commonest query in that neighbourhood is already one table's geometric tail.
`text=1.61803` returns 14 results, 8 of them T286. `text=1.6180339887` returns
6, none of them T286, because rank 50 diverges from $\varphi$ in the sixth
place.

That last line is the whole argument. Rank 50 is the last rank at which
somebody holding $\varphi$ to eight digits — which is what a numerical
computation hands back — gets $\varphi$ and not a Pisot number. Extending to
rank 100 puts 28 Pisot numbers inside an eight-digit query for $\varphi$, and
rank 190 puts 118 inside it. That is the skill's rule about values that match
everything and tell nobody anything, in its geometric form.

The table's own `complete-note` says this: "after that the two infinite
families are already within $3\cdot10^{-6}$ of $\varphi$, so the table stops at
a readable initial segment". It is the right sentence and it is already there.

## 2. If somebody does extend it, this is the method and the one thing to check. Worth recording.

`generators/pisot-numbers-less-than-golden-ratio/generate.py` has `RANKS = 50`
and `MAX_N = 80`. Raising `RANKS` is the whole of the change; `MAX_N` is the
search depth and must stay ahead of it. The generator sorts every root it found
and takes the first `RANKS`, so its answer is right only if no polynomial with
$n>\texttt{MAX\_N}$ has a root below $\theta_{\texttt{RANKS}}$, and the
correctness argument for that is already in the table's rigour details: at a
root of $P_n$, $P_{n+1}(x)=1-x<0$, and at a root of $Q_n$,
$Q_{n+1}(x)=-(x-1)^2(x+1)<0$, while both are positive at $\varphi$, so the
roots increase with $n$ in each family. It suffices that the $P_{\texttt{MAX\_N}}$
and $Q_{\texttt{MAX\_N}}$ roots exceed the cutoff. Ranks go roughly as $2n$:
rank 49 is $P_{25}$, rank 50 is $Q_{26}$, rank 190 is $Q_{96}$. `MAX_N = 100`
determines the first 190 ranks and takes 86 seconds to do it.

Two incidental facts the generator's structure implies and that I confirmed:
the families produce no duplicate minimal polynomials at all up to $n=100$
(199 polynomials, 199 distinct), so the deduplication step never fires; and
$E$ is not a factor of any $P_n$ or $Q_n$ in that range.

## 3. The one occurrence class that continues past the range, and the comments stop asserting it too early. Worth doing.

The entry comments say "It is the growth rate of $\Delta(2,n+1,\infty)$" for
ranks 1 to 21, that is for $P_2$ through $P_{11}$, and then stop. The earlier
critique (`agents/critiques/T286.md`, finding 3) asked for exactly this: state
it for the range checked, $2\leq n\leq11$, *or give a source for all $n$*. The
repair took the first option, and $n\leq11$ is where the Coxeter table T222
stops, not where the mathematics stops.

I checked the mathematics. Computing the growth rate of $\Delta(2,q,\infty)$
from Steinberg's formula and comparing with the root of $P_{q-1}$, they agree
for $q = 3, 12, 13, 20, 40, 60$ — the last two far outside anything T222 holds.
The identity is general, which is what Floyd's theorem (reference [1] of T222)
says.

Why this matters for growth: it is the only class of readers who could arrive
holding a value past rank 21. Somebody computing the growth series of
$\Delta(2,30,\infty)$ lands on $\theta_{57}$, which the table does not have. It
is also, honestly, a weak argument for extending, because that growth rate is
$1.6180339$ to seven places and a reader who has it will recognise $\varphi$
before they think to search — which is finding 1 again, from the other side.

The smallest change: make the comment's claim unconditional rather than
implicitly bounded, and say it once in `Comments` instead of on every $P$ row —
"the root of $P_n$ is the growth rate of the Coxeter triangle group
$\Delta(2,n+1,\infty)$", with the reference. Then the rows carry a link where
T222 has the entry and nothing where it does not, and a reader who extends
T222 does not have to notice that T286's comments were silently tied to its
range.

## 4. T300 holds the same 50 ranks and T286 does not name it. Worth doing.

`Minimal polynomials of the Pisot numbers less than the golden ratio` (T300) is
public and holds the minimal polynomial $m_r(x)$ for $r = 1,\ldots,50$. Its
`complete-note` says the range matches "the root table exactly", and its
`Similar tables` names T286. T286's `Similar tables` names T222, T284 and T32,
and does not name T300.

This is a growth finding, not only an editorial one: the two tables have one
range between them, and from T286's page that coupling is invisible. Anybody
who extends T286 has to extend T300 to keep T300's own note true, and nothing
on T286 tells them T300 exists.

The smallest change: one entry in T286's `Similar tables` with the converse of
T300's relation — "holds the minimal polynomial of each $\theta_r$ here, over
the same range".

## Noted only

* This worktree's copy of the generator is the pre-repair one. The live table's
  entry comments read "A root of $P_{2}$, with minimal polynomial $x^{3}-x-1$.
  ..."; the generator here produces "$P_{2}$ family; minimal polynomial ...",
  and its `complete-note` is the old short one. The aligned version is commit
  `2cffd60` on another branch. Running `--publish` from this branch would
  overwrite the reviewed prose with the draft prose. Not a fault in the table,
  and nothing to fix in the corpus; worth knowing before anybody edits the
  range from this checkout.
* The convergence means the table's rows get *less* distinctive as $r$ grows,
  which is the reverse of the usual shape, where a table's later entries are
  rarer and safer. There is a defensible argument for a *shorter* range — rank
  21 is where the named constants and the Coxeter correspondence with T222 both
  end, and it would take the 26 rows out of a `1.618` query. I am not
  recommending it. The range is published, the note defends it, and 26 rows
  with comments that each explain themselves is a much milder version of the
  fault than the rule is aimed at. But it is the honest answer to "is 50 the
  right number", and it points down rather than up.
>>>>>>> origin/campaign/w3
