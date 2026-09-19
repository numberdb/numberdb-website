# Can T289 grow? -- "Minimisers in the core threshold formula of random $k$-uniform hypergraphs"

Read on 2026-09-19 against the skill as served at <https://numberdb.org/skill>
that day. The table is live and public: `GET /api/table?id=T289` answers 200
with no key, and `https://numberdb.org/T289` renders (58 KB). 42 entries,
14836 bytes by the review queue's count; the entries block as the server
measures it (`numberdb_app/limits.py:measure`, a `yaml.dump` of the block) is
10068 bytes.

The audit is clean: `{"tid": "T289", "findings": [], "clean": true}`. I agree
with it, and it says nothing about range -- no rule there is about how far a
family was carried.

**The short answer.** It is not complete and it was not stopped by anything
about the mathematics. The definition promises every $k\geq3$ and every
$r\geq2$; the table holds the $6\times7$ box $3\leq k\leq8$, $2\leq r\leq8$,
because that is the box its companion T273 holds. Every part of the machinery
-- the bracket, the guard bits, the uniqueness proof, the cross-check --
carries to $k=200$ and $r=64$ untouched, and a 700-entry version would cost
about four minutes of compute. So the question is not *can* it but *which*
rows are worth having, and the honest ceiling is set by two things that are
not size: what a reader arrives holding, and the companion tables that every
row of this one points at.

---

## What was measured

**Cost per entry is flat, which is unusual and worth saying.** Every entry is
a 100-digit real, so unlike a polynomial family this table has no entry that
grows. Measured on the stored block: 239.7 bytes per entry with the per-row
comment, 111.7 without it. The skill's advice is to aim at half the soft block
limit, about 160 KB; at 239.7 bytes that is **about 700 entries**, and the
soft entry count (1200) would arrive at 288 KB, just under the 320 KB block
limit. The recommended 1000 entries would make a 234 KB block -- the largest
in the corpus today is 236 KB, so 1000 is the outer edge rather than a target.

**Compute is nearly free.** Re-running the generator's bisection at 100 digits
in a throwaway Sage container:

    k=3   r=2    0.02s      k=40  r=40   0.07s
    k=20  r=20   0.05s      k=3   r=60   0.10s
    k=200 r=2    0.01s      k=8   r=64   0.11s

A full grid $3\leq k\leq20$, $2\leq r\leq12$ -- 198 entries -- computed in
4.2 s, i.e. 0.021 s each; 700 entries projects to 15 s. The independent mpmath
check the generator runs on every row costs more, 0.18--0.32 s per row, so a
700-entry rebuild with its verification intact is about 4 minutes. Neither is
a constraint.

**The rigour argument scales without change.** At every corner tested
($(k,r) = (200,2)$, $(40,3)$, $(40,40)$, $(3,60)$, $(8,64)$): the left
endpoint $(r-1)-1/(k-1)$ still had $g<0$, the right endpoint $4(k+r)+10$ never
needed doubling, no sign was undecidable at 64 guard bits, and the final
bracket still closed with opposite signs at radius $10^{-106}$. The table's own
proof is general -- $g'$ vanishes only at $\lambda^*=(r-1)-1/(k-1)$, $g(0)=0$
and $g\to1$, so there is exactly one positive zero whenever $\lambda^*>0$ --
and nothing in it degrades with $k$ or $r$. Extending needs no new mathematics
and no new precision analysis.

**The values do not crowd enough to matter.** Neighbour gaps, which decide
whether a reader holding five decimal places gets one hit or two:

    along k, r=2:   k=3   0.647     k=20  0.065     k=120  0.0098
    along r, k=3:   r=2   1.96      r=16  1.29      r=64   1.16

Along $r$ the values stay about 1.2 apart for ever. Along $k$ they thin like
$\lambda_{k,2}\sim\log k$ -- 1.256, 1.904, 2.337, ... , 6.755 at $k=128$ --
but even at $k=120$ consecutive entries differ in the third decimal, so
ambiguity is not what stops the $k$ axis. What stops it is that nobody quotes
$\lambda_{120,2}$.

---

## What is worth doing

### 1. The $k=2$ column: ten numbers the database holds nowhere as values

The generator already computes $\lambda_{2,r}$ -- it uses those values to
check T156 -- and then throws them away, because the parameter says $k\geq3$.
Meanwhile T156, "$k$-core thresholds of the Erdős–Rényi random graph", keeps
them **only in entry comments**: "The minimum is attained at
$\lambda_{3}=1.79328213290$", to twelve digits, for $3\leq k\leq12$. The skill
is explicit that an entry's own comment is in no index. So a reader who
minimised the graph core function and got 1.7932821329 can search this
database and get nothing, while the number sits in two places on the site as
prose.

I recomputed them at 100 digits and they agree with T156's twelve digits
exactly:

    lambda_{2,3}  = 1.793282132901      lambda_{2,8}  =  9.097344402576
    lambda_{2,4}  = 3.383634282853      lambda_{2,9}  = 10.447030681326
    lambda_{2,5}  = 4.881277491346      lambda_{2,10} = 11.777906606454
    lambda_{2,6}  = 6.322505551033      lambda_{2,11} = 13.093042498286
    lambda_{2,7}  = 7.724583600437      lambda_{2,12} = 14.394738901917

This is the one extension that adds content rather than grid. It also does not
repeat any stored value: T273 excludes $k=2$ deliberately, because the
*threshold* there is a different convention (T156 writes average degree, T273
edges per vertex, and they differ by a factor of two). The *minimiser* has no
such split -- $\lambda_{2,r}$ is the same number in both readings, which is
exactly why it can live here.

Two things have to be said when it is done, and both are one clause:

* the parameter constraint becomes $k\geq2$;
* $(k,r)=(2,2)$ has no entry, and the table's own formula says why:
  $\lambda^*=(r-1)-1/(k-1)=0$ there, so $g$ increases from $0$ and never
  returns to it. This is the continuous emergence of the graph 2-core that
  T273's `comment-graph-case` already describes. The `complete-note` should
  carry the exception rather than leave a reader to notice a hole: "...for
  every $k\geq2$ and $r\geq2$ in the box, except $(2,2)$, where the minimum is
  approached as $\lambda\to0$ and there is no minimiser".

The cuckoo pair is the precedent: T274, "Cuckoo hashing thresholds of random
$k$-uniform hypergraphs", and its companion T288, "Roots of the cuckoo hashing
threshold equation", both run $2\leq k\leq7$ -- the graph case included, in a
table whose subject is hypergraphs.

### 2. Square the box to $3\leq k\leq12$, $2\leq r\leq12$ -- but move T273 with it

110 entries, about 26 KB, under a minute of compute. $k\leq12$ is not a new
choice: it is the range T156 already holds, so the three tables in this
neighbourhood would agree on where the graph column ends. Along $r$, $r\leq12$
keeps every entry a number with a name ("the 12-core") rather than a grid
point.

The reason to move T273 in the same change is mechanical, and it is the real
ceiling on extending T289 alone:

* **Every entry comment links into T273.** Each row says "The associated core
  threshold is $c_{k,r}$" as `HREF{Core_thresholds_of_random_k-uniform_hypergraphs#k,r}`.
  I fetched such a link for a row T273 does not have: the page answers 200 and
  shows a banner, "This table has no entry 9,2. It may have been renumbered or
  removed; the table itself is shown below." Not a 404, but every new row of
  T289 would greet its reader with that.
* **Every row's verification compares against T273.** `run_integrity_checks`
  reads `T273[k][r]` for the derived threshold and for T273's own comment
  digits. Outside the $8\times8$ box that is a `KeyError`, not a soft skip --
  and the graph loop reads `T156[r]`, so it breaks above $r=12$ the same way.
  **Scope both checks to the overlap before extending anything**, otherwise the
  first attempt to grow the table dies in its own checks with a traceback that
  names a dictionary key rather than the reason. Two lines.

T273 costs 194.9 bytes an entry, so the pair at $12\times11$ plus the $k=2$
column is 26 KB and 21 KB -- nowhere near anything.

### 3. If more is wanted after that, grow $r$, not $k$

$r$ is the cheap axis in both senses: the values stay 1.2 apart, and each is
the threshold for a named object. $3\leq k\leq12$, $2\leq r\leq20$ plus the
$k=2$ column is 208 entries, about 50 KB. Going the other way -- $k$ past
about 20 at fixed $r$ -- adds rows whose values are $\log k$ apart and which,
as far as I can tell from the corpus's neighbourhood (T156 stops at 12, T273
at 8, the cuckoo tables at 7, the LDPC table at degree 12), nobody has ever
written down. The skill's test is whether anybody arrives holding the number,
and a large-$k$ row fails it while costing the same 240 bytes as a row that
passes.

I would stop at **about 210 entries**: $k\in\{2\}\cup[3,12]$, $r\leq12$ now,
$r\leq20$ if somebody wants a second pass. That is a third of the reachable
700 and it is where the rows stop being numbers and start being a grid.

---

## Noting only

* **The per-row comment is the lever if this table ever needs to be big.** It
  costs 128 bytes of the 240, and it is the same sentence 42 times with two
  numbers changed; dropping it would raise the 160 KB ceiling from about 700
  entries to about 1460. It earns its place at the present size -- it is the
  link to the number a reader most likely wants next, which the skill asks for
  -- and I am not proposing removing it. But a future range that wants 1000
  rows should spend that budget on rows.
* **More digits is not a growth direction here.** At 0.02 s an entry these are
  cheap digits, and the skill is clear that cheap digits past a hundred add
  nothing. 100 is right.
* **The repository's `generators/core-threshold-minimisers/table.yaml` is stale
  against the live document.** It still carries the pre-repair title
  ("Minimisers of the core threshold"), the old definition, and the companion's
  copied keywords; the live table has all seven repairs from
  `agents/critiques/T289-repaired.md`. Whoever extends the range will want to
  edit `complete-note` and the `k` constraint -- if they edit that file and
  upload it, they will undo the repair. Worth reconciling the file first. This
  is a repository finding, not a reading of the table.

## How it was read

The proxy on 127.0.0.1:1080 was refusing connections throughout this run
(`curl` exit 7 on every attempt after the first). This box reaches numberdb.org
directly, which `docs/agent-environment.md` says twice and which I confirmed
afterwards: `curl https://numberdb.org/T289` with no proxy answers 200, and
`curl https://numberdb.org/skill` with no proxy returns a file byte-identical
to the copy this reading was done against, so the skill above is the live one.

Everything else was fetched from inside the throwaway Sage container, which
reaches numberdb.org over the public API: the document and the audit with the
zeta3 key, the rendered `/T289` page, T273, T156, and the missing-entry page.
All computations ran in that container via `agents/sage.sh` -- the minimiser
transcribed from the generator, the mpmath cross-check, the gaps, and the
$k=2$ column. Nothing was written to any table, and nothing about T289 was
changed.
