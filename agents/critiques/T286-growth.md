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
