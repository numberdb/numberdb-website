# Can T291 grow? — "Characteristic polynomials of the monodromy of the simple and unimodal singularities"

Read on 2026-09-19 against the skill as served at <https://numberdb.org/skill>
that day (fetched fresh, 48740 bytes). This is a report on **range only**: what
the table's definition promises, how much of it is here, and how the rest would
be computed. Nothing was changed.

**How it was read.** The SOCKS proxy is not up in this run (`ALL_PROXY` is
empty and port 1080 refuses), so `curl` went direct, which this box allows and
`docs/agent-environment.md` already records. The document came from
`GET /api/table?id=T291` with the zeta3 key, the audit from
`GET /api/table/T291/audit`, and the generator from
`generators/monodromy-characteristic-polynomials-simple-unimodal-singularities/generate.py`.
Every claim below about a polynomial was computed, not remembered: three Sage
runs through `agents/sage.sh`, one of them checking against Singular's
`spectrum` and `bfct`. The audit's single finding is about the length of the
Definition and says nothing about range; `agents/critiques/T291.md` covers the
reading of the page and is not repeated here.

---

## The short answer

**Part of it is finished and part of it was stopped early, and the two parts
are easy to tell apart.**

*Finished:* the twenty sporadic labels. $E_6,E_7,E_8$, the three parabolic
$P_8,X_9,J_{10}$, and all fourteen exceptional unimodal singularities are
present — that is the whole of Arnold's sporadic list for these classes, and
no amount of computing adds a twenty-first. That half of the table is a named
constant with one entry, and saying so is the right answer for it.

*Stopped early*, in three places, smallest first:

1. **The $n$ axis is seven rows short of being finished forever.** $\Delta_f$
   depends on $n$ only through its parity, so `with $n\leq3$` in the
   completeness note could be replaced by "every $n$" for the cost of seven
   entries.
2. **$A_k$ and $D_k$ stop at $k=12$ while everything else in the table runs to
   $\mu=14$.** The edge is ragged for no stated reason.
3. **The hyperbolic unimodal series $T_{p,q,r}$ is a third of what the title
   promises and none of what the table holds.** This is the only one that
   needs new mathematics, and the mathematics is a closed form I verified
   against Singular on ten triples.

All three together, bounded at $\mu\leq14$, come to **178 entries and 27 KB** —
15% of the soft entry limit and 8% of the soft block limit. Size is not the
constraint here and will not become one.

---

## What the definition promises, and what is here

The Definition admits "a simple singularity, a parabolic unimodal singularity,
or an exceptional unimodal singularity in Arnold's classification", and the
`singularity` parameter's constraint says `$A_k$ with $k\geq1$, $D_k$ with
$k\geq4$` — correctly the family, not the run, as the skill asks. So the
definition promises:

| class | how many | how many are here |
|---|---|---|
| $A_k$, $k\geq1$ | infinite | 12 |
| $D_k$, $k\geq4$ | infinite | 9 |
| $E_6,E_7,E_8$ | 3 | 3 |
| parabolic $P_8,X_9,J_{10}$ | 3 | 3 |
| exceptional unimodal | 14 | 14 |

and the `n` constraint says "at least the corank", which is unbounded, while
the table holds $n\leq3$.

The **title** promises more than the Definition does: "the simple and unimodal
singularities". Arnold's unimodal list has three parts — the three parabolic,
the hyperbolic series $T_{p,q,r}$ with $1/p+1/q+1/r<1$, and the fourteen
exceptional. The table holds two of the three and the `complete-note` says so
honestly ("the hyperbolic unimodal families $T_{p,q,r}$ are not included"), but
a `complete-note` is not in the search index and a title is its first weight. A
reader who has a unimodal singularity has, roughly, a one-in-three chance that
it is one this table declines.

---

## Worth doing

### 1. Seven rows finish the $n$ axis permanently

The suspension formula the table already carries is
$\Delta_{f+u^2}(t)=(-1)^\mu\Delta_f(-t)$, and $\mu$ does not change under
suspension, so applying it twice gives $(-1)^{2\mu}\Delta_f(t)=\Delta_f(t)$.
**$\Delta_f$ is exactly 2-periodic in $n$.** I checked this on all 41 labels
for $n$ from the corank to corank$+5$: no exception. It is visible in the
stored data too — $A_1$ holds `t + 1` at $n=1$ and `t + 1` again at $n=3$.

So the $n$ parameter, which looks unbounded, has exactly two values per
singularity. The table holds both for the corank-1 and corank-2 labels and only
one for the seven of corank 3, because the generator's loop is
`range(spec.corank, 4)` and for those the loop runs once. The missing seven are
$n=4$:

| | $n=3$ (stored) | $n=4$ (missing) |
|---|---|---|
| $P_8$ | $t^8+t^7+t^6-2t^5-2t^4-2t^3+t^2+t+1$ | $t^8-t^7+t^6+2t^5-2t^4+2t^3+t^2-t+1$ |
| $Q_{10}$ | $t^{10}+t^9+t^8-t^6-t^5-t^4+t^2+t+1$ | $t^{10}-t^9+t^8-t^6+t^5-t^4+t^2-t+1$ |
| $Q_{11}$ | $t^{11}+t^{10}+t^9+t^2+t+1$ | $t^{11}-t^{10}+t^9-t^2+t-1$ |
| $Q_{12}$ | $t^{12}+t^{11}+t^{10}+t^7+t^6+t^5+t^2+t+1$ | $t^{12}-t^{11}+t^{10}-t^7+t^6-t^5+t^2-t+1$ |
| $S_{11}$ | $t^{11}+t^{10}+t^9+t^8+t^3+t^2+t+1$ | $t^{11}-t^{10}+t^9-t^8+t^3-t^2+t-1$ |
| $S_{12}$ | $\Phi_{13}(t)$ | $\Phi_{26}(t)$ |
| $U_{12}$ | $t^{12}+t^{11}+t^{10}+2t^9+\cdots$ | $t^{12}-t^{11}+t^{10}-2t^9+\cdots$ |

None of these is a repeat of anything in the table, each is a 3-fold
singularity somebody could be holding, and $S_{12}$ at $n=4$ is $\Phi_{26}$,
which is exactly the kind of value that walks in from somewhere else.

The real gain is the sentence. With them, `complete-note` stops saying "with
$n\leq3$" — a fact about Tuesday — and says something a reader can act on:

> …at every $n$: $\Delta_f$ depends on $n$ only through its parity, by the
> suspension formula, and both parities are here.

That is a range that is the whole of what the definition promises, on that
axis, forever. It is also the cheapest thing in this report: `range(corank, 4)`
becomes `range(corank, corank + 2)` together with the existing $n\le3$ rows —
94 entries, 14,828 bytes, up from 87 and 13,544.

One thing to fix while doing it: `normal_form_latex` and `singular_expression`
index `VARIABLES = ("x", "y", "z")`, so $n=4$ needs a fourth name. I used `w`;
the comment then reads `$f=x^3+y^3+z^3+w^2$`, which is fine, but the Definition
writes the added squares as $x_{c+1},\ldots,x_n$ and the suspension formula
writes $u^2$. That is finding 5 of `agents/critiques/T291.md` and a fourth
spelling would make it worse, not better.

### 2. $A_k$ and $D_k$ stop at $\mu=12$; everything else runs to $\mu=14$

$\mu(A_k)=\mu(D_k)=k$, so the two infinite families are cut at $\mu=12$. The
sporadic labels go to $\mu=14$ ($E_{14}$). Nothing says why, and "$1\leq k\leq
12$, $4\leq k\leq 12$" in the completeness note is the clause the skill warns
about: a number that describes a run rather than a choice.

**Raising both to $k=14$ makes the whole range one sentence:** *every
singularity in the definition with Milnor number at most 14*. $\mu\leq14$ is
the smallest bound that contains every sporadic label the table already holds,
so it is the classification's number and not a chosen one. It costs ten more
entries: 104 entries, 16,708 bytes.

The generator needs no new mathematics for this. `MAX_A` and `MAX_D` are two
constants, and the $D_k$ weights and Milnor basis (`d_basis`) are already
written generically in $k$ — only the twenty sporadic bases are by hand. I ran
the generator's own method past its current edge and checked it against
Singular's `spectrum`:

    A18  n=2: agrees with Singular  (116 chars)
    A24  n=2: agrees with Singular  (158 chars)
    D18  n=3: agrees with Singular  (19 chars)
    D24  n=3: agrees with Singular  (19 chars)

so the method is sound wherever you stop.

### 3. The hyperbolic series $T_{p,q,r}$: either hold them, or narrow the title

This is the finding with content, and it is not a bigger loop — the generator
as written **cannot** reach these rows, for two separate reasons.

*The convention does not carry over.* The Definition says the modulus is set to
$0$. For the parabolic and exceptional families that is harmless. For the
hyperbolic ones it is not a normalisation, it is a different singularity:

    x^3+y^3+z^4 has mu=12; T_{3,3,4} has mu=9
    x^2+y^3+z^7 has mu=12; T_{2,3,7} has mu=11

(Singular, `milnor`.) Worse, $x^3+y^3+z^4$ is $U_{12}$, which is already a row
in this table. So extending here means narrowing the stated convention to "with
the modulus set to $0$ for the parabolic and exceptional families", and taking
the hyperbolic rows at a *generic* modulus.

*The method does not carry over either.* $T_{p,q,r}=x^p+y^q+z^r+axyz$ is not
quasi-homogeneous, so there are no weights to feed
`monodromy_exponents`. But there is a closed form, and I verified it rather
than trusting it:

$$\Delta_{T_{p,q,r}}(t)=(t-1)^2\cdot\frac{t^p-1}{t-1}\cdot\frac{t^q-1}{t-1}\cdot\frac{t^r-1}{t-1}$$

of degree $p+q+r-1=\mu$. Checks run:

* against the three rows the table already stores — $P_8=T_{3,3,3}$,
  $X_9=T_{2,4,4}$, $J_{10}=T_{2,3,6}$ are the parabolic members of the same
  series, and the closed form reproduces all three stored polynomials exactly;
* against Singular's `spectrum` on $x^p+y^q+z^r+xyz$ for $T_{3,3,3}$,
  $T_{2,3,7}$, $T_{3,3,4}$, $T_{2,4,5}$, $T_{2,3,8}$, $T_{3,4,4}$, $T_{2,5,5}$,
  $T_{4,4,4}$, $T_{2,6,7}$, $T_{5,5,5}$ — agreement on all ten, with
  `milnor` returning $p+q+r-1$ each time;
* against the modulus: $T_{3,3,4}$ at $a=1,2,5$ gives the same polynomial, so
  "generic" needs no further qualification for *this* table.

So the method for the hyperbolic rows is: the closed form for the value, and
Singular's `spectrum` as the independent check, exactly the shape the table's
`rigour details` already describes. The existing `run_singular_checks` can
check them unchanged.

**How far:** $\mu=p+q+r-1$, so a Milnor bound makes the series finite.
$\mu\leq14$ gives **37 triples**, from $T_{3,3,4}$ ($\mu=9$) to $T_{5,5,5}$
($\mu=14$), two entries each (corank 2 when $p=2$, corank 3 otherwise), 74
entries and about 10 KB. Those 37, with the parabolic three already here, are
every hyperbolic singularity with $\mu\leq14$.

**If they are not added,** the title should be narrowed instead — "of the
simple, parabolic and exceptional singularities" — because the title is the
first weight in the search index and currently promises a class the table
declines. That is the one-field alternative, and it is worse: the rows are
cheap, they are checkable, and they are the reason the title was written that
way.

---

## The range I would state

> **complete: no** — it holds every simple or unimodal singularity with Milnor
> number $\mu\leq14$: $A_k$ and $D_k$ for $k\leq14$, $E_6,E_7,E_8$, the
> parabolic $P_8,X_9,J_{10}$, all fourteen exceptional unimodal singularities,
> and the hyperbolic $T_{p,q,r}$ with $p+q+r\leq15$; at every $n$, since
> $\Delta_f$ depends on $n$ only through its parity.

Measured, that is:

| | labels | entries | Numbers block | longest value | longest entry |
|---|---|---|---|---|---|
| as stored | 41 | 87 | 13,544 B | 80 ch | 190 ch |
| + the missing parity | 41 | 94 | 14,828 B | 80 | 190 |
| + $A,D$ to $k=14$ | 45 | 104 | 16,708 B | 88 | 190 |
| + hyperbolic $\mu\leq14$ | 82 | **178** | **27,223 B** | 98 | 190 |

against soft limits of 1200 entries and 320 KB, with the skill's advice to aim
at 160 KB. The longest entry does not grow at all across those four rows,
because the bound is on $\mu$ and $\mu$ is the degree.

---

## Noted only

### 4. It could go much further, and I would not

Measured, keeping every label at both parities:

| $\mu\leq$ | labels | entries | block | longest value |
|---|---|---|---|---|
| 14 | 82 | 178 | 27 KB | 98 ch |
| 16 | 114 | 244 | 38 KB | 108 |
| 20 | 209 | 438 | 70 KB | 144 |

and, for the two infinite families alone (no hyperbolic rows):

| $k\leq$ | entries | block | longest value | longest entry |
|---|---|---|---|---|
| 30 | 184 | 35 KB | 200 ch | 335 ch |
| 60 | 334 | 86 KB | 410 | 600 |
| 100 | 534 | 184 KB | 691 | 852 |

So $k=100$ — the skill's house range for a family of polynomials indexed by
degree — fits the entry limit and overshoots the 160 KB target. The reason not
to go there is not size. $\Delta_{A_k}$ at $n=1$ is
$1+t+\cdots+t^k$ and at $n=2$ is the same with alternating signs: at $k=100$
that is a 691-character row of ones, and three hundred such rows would bury the
twenty sporadic labels that are the reason this table exists. The skill's test
is whether somebody arrives holding the value, and somebody holding
$1+t+\cdots+t^{73}$ identifies it as a cyclotomic quotient (T95 holds those),
not as $A_{73}$.

Bounding by $\mu$ rather than by $k$ is also what keeps the three axes in step:
it is one number that cuts the two infinite families and the hyperbolic series
at the same place, and it is the number the classification is stratified by. If
$\mu\leq14$ later looks too tight, $\mu\leq20$ is the next defensible stop —
438 entries, 70 KB, still a fifth of the block limit — and nothing in the
method changes.

### 5. Choose the key spelling for the hyperbolic labels before publishing, not after

A parameter's key is an address and is frozen at publication. The existing keys
are `A1`, `D4`, `E6`, `P8` — digits glued to a letter. Glue three numbers the
same way and `T2310` is both $T_{2,3,10}$ and $T_{2,31,0}$; $T_{2,3,10}$ has
$\mu=14$ and is inside the range above, so the collision is real and not
hypothetical. `T2_3_10` or `T2,3,10` avoids it. This costs nothing to decide
now and cannot be changed later.

### 6. T290 is the same table in another quantity, and has the same range word for word

T290 (Bernstein–Sato polynomials of the same list) has the same 41 labels, the
same 87 entries, and a `complete-note` identical to this one character for
character. The two are linked to each other with a relation that holds row by
row. Any range change made here and not there breaks that correspondence, so
they should move together.

The hyperbolic rows are reachable for T290 too — Singular's `bfct` on
$x^p+y^q+z^r+xyz$ returned in 0.2 to 7.5 seconds for $T_{3,3,3}$, $T_{3,3,4}$,
$T_{2,3,7}$ and $T_{4,4,4}$ — but with a caution I did not chase: `bfct` at
$a=1$ gives $-1$ with multiplicity 2 or 3, and for T291 the modulus provably
does not matter while for T290 it may. Whoever extends the pair should check
the parabolic rows of T290 at $a=0$ against $a\neq0$ before assuming the
convention carries.

### 7. Nothing in the corpus competes for this range

`GET /api/search?q=singularity` returns nothing today, as do `monodromy`,
`Milnor` and `hyperbolic`, because the pair is still a draft. There is no
existing table the hyperbolic rows would duplicate, and no third table these
would need to be split from: the 37 new labels name *what the polynomial is
of*, like $A_k$ does, and the value column stays $\Delta_f(t)$ rather than
falling back on `value`. Adding them does not turn this into two tables.
