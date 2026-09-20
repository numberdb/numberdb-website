# Can T281 grow? "Davenport-Stothers polynomial triples", read on 2026-09-20

**The verdict: it can grow by exactly one class — three entries, 15 to 18 — and
then it is finished, because the next row after that would settle a question
that has been open since 1965.**

The missing class is Elkies's $M=5$ example. It is rational, it is printed in a
published paper the table does not cite, and I verified it here: $f$ of degree
10 and $g$ of degree 15 with integer coefficients, $h=f^3-g^2$ of degree 6, and
$2fg'-3f'g$ a nonzero constant (§3). With it the table would hold **every
Davenport-Stothers triple over $\mathbb Q$ that anybody knows**.

After that there is nothing to add, and the reason is not that nobody has got
round to it:

* The number of classes over $\mathbb C$ is known exactly —
  $D(M)=1,1,1,1,4,6,19,49,150,442,\dots$ — so the family is enormous (§1).
* Almost none of it can be written over $\mathbb Q$, which is what a `Q[]`
  table holds. Two of the four classes at $M=5$ are a mirror pair exchanged by
  complex conjugation, so they have no real coefficients at all, let alone
  rational ones (§2).
* For $M>5$, **whether even one rational triple exists is an open problem**:
  raised in Birch–Chowla–Hall–Schinzel (1965), restated as unsolved by Elkies
  in 2000, and consistent with two independent computations — Montanus reports
  nothing over $\mathbb Z$ for $6\leq M\leq11$, and Elkies–Watkins computed
  classes at $M=6,7,8,9,11,14,17$ and found every one of them defined over a
  number field, of degree 2 up to 47, never over $\mathbb Q$ (§4).

So this table was not stopped early by a choice of range, and it is not short of
room: 15 entries in 5,473 bytes is 1.3% of the entry limit and 0.2% of the block
limit, and none of that is available to it. Its range is bounded by the
literature at $M\leq5$ and by an open problem above that. The right reading is
the skill's "a named constant with one entry is finished", one size up: this is
a **complete catalogue of a known-to-be-tiny set**, which is a good table, and
the one change that matters is saying so on the page (§5).

## What was read

- **Skill:** `https://numberdb.org/skill`, 48,740 bytes, fetched fresh. The
  prompt's `--socks5-hostname 127.0.0.1:1080` route refuses on this builder; a
  direct fetch works. Already in `docs/agent-environment.md`.
- **Page:** `GET /T281` → 200, 35,498 bytes, rendered to text and read whole.
  No `Math input error`, no `argument ()`, no dictionary dumps: the eight
  findings of the September critique are all repaired in the live document.
- **Document:** `GET /api/table?id=T281` → 5,473 bytes, entries block 724 bytes.
- **Audit:** `GET /api/table/T281/audit` → `{"findings": [], "clean": true}`.
  I agree. On the question the audit raises about tables shaped like this one —
  a parameter whose values are words — the `part` ($f$, $g$, $h$) and class
  parameters are the good kind, parts of one object and a choice within one
  $M$; the definition now says so.
- **Generator:** `generators/davenport-stothers-polynomial-triples/generate.py`.
  It transcribes $f$ and $h$ for five examples and derives $g$ as an exact
  polynomial square root of $f^3-h$. There is no search in it, so there is no
  constant to raise: growth here is a transcription, not a longer run. §3 says
  what it would need.
- **Sources, in full.** Montanus, *Halltripels en kindertekeningen*, NAW 5/7
  nr. 3 (2006), 172–176 (the PDF the table links; read by inflating its Flate
  streams with `zlib`, since this builder has no `pdftotext` or `pdftoppm`).
  Elkies, *Rational points near curves and small nonzero $|x^3-y^2|$ via
  lattice reduction*, ANTS-IV, LNCS 1838 (2000), 33–63 — **arXiv:math/0005139,
  LaTeX source, §4.1**, which is the catalogue of rational examples and the
  open question. Elkies–Watkins, *Polynomial and Fermat–Pell families that
  attain the Davenport–Mason bound*
  (`magma.maths.usyd.edu.au/~watkins/papers/hall.ps`, a draft with `FIXME`
  markers in it), which has the class counts by monodromy, the higher-$M$
  solutions and their fields. Sijsling–Voight, arXiv:1311.2529 source, for
  what the methods are.
- **My own computation:** an independent enumeration of the Hall trees, exact
  solving of the defining system in Sage over $\mathbb Q$ and over $GF(p)$
  through `agents/sage.sh` (three runs, one killed at the memory cap), and
  exact verification of Elkies's triple in plain Python with `Fraction`.
  Nothing was written to any table.
- **Unreachable from here, and it did not matter in the end:** OEIS (403,
  Cloudflare, direct and through the web-fetch agent), `WebSearch` (not
  permitted in this run), Shioda's *Elliptic surfaces and Davenport-Stothers
  triples* (closed access; Elkies–Watkins cite a Rikkyo URL), Montanus's
  unpublished LIO report, Beukers–Montanus 2008.

## What is there

| | |
|---|---|
| entries | 15 = 5 classes × 3 parts |
| document | 5,473 bytes; entries block 724 bytes of the 320 KB soft limit |
| longest entry | 112 characters ($g$ at $M=4$) |
| type / rigour | `Q[]` / `exact` |
| complete | `no` — "it holds every equivalence class for $M\leq4$, and for $M=5$ only Birch's symmetric class among the four classes described by [1]" |

Three checks before reasoning from these rows:

- **The defining relation and the degrees.** $h=f^3-g^2$ exactly, and
  $(\deg f,\deg g,\deg h)=(2M,3M,M+1)$, on all five rows.
- **Extremality, independently of the source.** $\deg h=M+1$ is equivalent to
  $2fg'-3f'g$ being a nonzero *constant*: differentiating $g^2/f^3$ gives
  $g\,(2fg'-3f'g)=3f'h-h'f$, the leading terms of $2fg'-3f'g$ cancel because
  $2\cdot3M=3\cdot2M$, and comparing degrees gives
  $\deg h=M+1+\deg(2fg'-3f'g)$. On the stored rows that expression is
  $6,-72,378,-513,-2$ — constant and nonzero every time. So every stored triple
  is extremal, not merely of the right shape. (Elkies–Watkins note that
  Uchiyama–Yorinaga used the same criterion.)
- **No gaps in what is claimed:** $M=1,\dots,5$, one class value under each.

## 1. What the definition promises: every class, and there are $D(M)$ of them

Montanus's theorem — Stothers had it in 1981, and Zannier proved it again in
1995 — is that equivalence classes of triples of type $M$ correspond to
*Hall trees*, plane trees with $M+1$ leaves and $M-1$ trivalent internal
vertices, hence to triangulations of a convex $(M+1)$-gon up to rotation:

$$D(M)=\frac{C(M-1)}{M+1}+\frac12 C\!\left(\frac{M-1}{2}\right)
      +\frac23 C\!\left(\frac{M-2}{3}\right),$$

$C(x)$ the $x$-th Catalan number for integral $x$ and $0$ otherwise. The
sequence he prints is
$1,1,1,1,4,6,19,49,150,442,1424,4522,14924,49536,167367,570285,\dots$

I enumerated the trees independently (all plane trees, canonical form over every
leaf-rooting, reflections *not* identified) and got
$1,1,1,1,4,6,19,49,150,442,1424,4522,14924$ for $M=1..13$: agreeing with
Montanus's printed sequence, with his "one class for $M\leq4$, four for $M=5$",
and — a third, independent check — with Elkies–Watkins's Table 1, which counts
classes by monodromy group and imprimitivity degree and whose lines sum to the
same numbers ($M=5$: $1+2+1$; $M=7$: $14+5$; $M=9$: $136+14$; $M=11$:
$1377+42+5$; $M=13$: $14792+132$; $M=14$: $49522+14$).

Two things follow. The family is far larger than any table (so `complete: no`
is permanent and right), and the count is not the binding constraint: on entry
count alone every class to $M=9$ would fit (232 classes, 696 entries), and
entry length would never bind, since a triple of type $M$ costs $O(M^2)$
characters.

## 2. What of it can be written over $\mathbb Q$: six classes, and that is all anybody knows

The table's type is `Q[]` and its definition says $f,g,h\in\mathbb Q[t]$, so the
range is not $D(M)$ but the rational part of it. Two facts bound that, and they
agree.

**Chirality.** A triple with real — let alone rational — coefficients has a
dessin carried to itself by complex conjugation, which acts on the plane as a
reflection, so **a class whose tree is not isomorphic to its mirror image has no
representative over $\mathbb R$**. Montanus says exactly this at $M=5$: "Eén
van die klassen is de spiegeling van een andere. Omdat complexe conjugatie het
vlak spiegelt gaan de corresponderende Halltripels door complexe conjugatie in
elkaar over." Counting self-mirror trees (twice the count up to reflection,
minus the count) gives a ceiling on what a `Q[]` table could ever hold:

| $M$ | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| classes $D(M)$ | 1 | 1 | 1 | 1 | 4 | 6 | 19 | 49 | 150 | 442 | 1424 | 4522 | 14924 |
| self-mirror, so possibly rational | 1 | 1 | 1 | 1 | 2 | 2 | 5 | 5 | 14 | 14 | 42 | 42 | 132 |

**The catalogue.** Elkies's §4.1 lists every known rational example, and there
are six classes: $M=1$ ($x=t^2+2a$), $M=2$ ($x=t^4+4at$), $M=3$ and $M=5$ found
by Birch in a 1961 letter to Chowla, $M=4$ found by Hall, and $M=5$ again —
Elkies's own, announced in August 1998. The $M=1$ and $M=2$ entries are
one-parameter *twist* families: all values of $a\neq0$ become isomorphic over
$\overline{\mathbb Q}$, so each is one class in this table's sense, and the same
twisting applies to Birch's two.

**T281 holds five of those six.** The one it does not hold is Elkies's $M=5$.

## 3. The missing row, verified

Elkies's example, as printed in arXiv:math/0005139 §4.1 (and again in
Elkies–Watkins):

    f = t^10 + 2*t^9 + 33*t^8 + 12*t^7 + 378*t^6 - 336*t^5 + 2862*t^4
        - 2652*t^3 + 14397*t^2 - 9922*t + 18553

Both papers say how to get the rest: "$y$ is obtained by truncating the Laurent
expansion at infinity of $x^{3/2}$ after the constant term" — which is forced,
not a convention, since $\deg(f^3-g^2)=M+1<3M$ means $g=[f^{3/2}]_{\geq0}$
exactly. Carrying that out in exact arithmetic here gives

    g = t^15 + 3*t^14 + 51*t^13 + 67*t^12 + 969*t^11 - 33*t^10 + 10963*t^9
        - 9729*t^8 + 96507*t^7 - 108631*t^6 + 580785*t^5 - 700503*t^4
        + 2102099*t^3 - 1877667*t^2 + 3904161*t - 1164691

    h = 4591650240*t^6 + 5509980288*t^5 + 101934635328*t^4 - 58773123072*t^3
        + 730072388160*t^2 - 1151585880192*t + 5029693672896

and the checks all pass: $\deg(f,g,h)=(10,15,6)=(2M,3M,M+1)$, $h=f^3-g^2$
exactly, every coefficient an integer, and $2fg'-3f'g=110199605760$, a nonzero
constant, so the triple is extremal. Note that the transcription is
self-validating: a single wrong digit in $f$ would have left $\deg h=14$.

It is a different class from Birch's, not another representative of it: $f$ is
supported in every degree from 0 to 10, where Birch's is $t$ times a polynomial
in $t^3$; Elkies gives the Galois group of $f^3/g^2$ as $S_{30}$ against
$\mathrm{PSL}_2(\mathbb F_9)$ for Birch's, and Elkies–Watkins list them as
separate lines of Table 1 (imprimitivity degree 1 and 3). By §2 it is also the
second of the two self-mirror classes at $M=5$ — the two chiral ones are the
$d=2$ pair, which Elkies–Watkins found over a quadratic field.

**What adding it costs.** Three entries, about 400 characters, taking the
entries block from 724 bytes to roughly 1.1 KB. No new mathematics, no search,
and a verification that runs in under a second. One thing in the generator has
to change: it currently recovers $g$ as the exact square root of $f^3-h$, which
needs $h$, and Elkies prints only $f$. The series truncation above is the
replacement, it is four lines, and it is the *stronger* check of the two,
because it re-derives $g$ from $f$ alone rather than from a second transcribed
polynomial. (The existing five rows pass the new path too: each stored $g$ has
positive leading coefficient and $h=f^3-g^2$ has degree $M+1$, which together
force $g=[f^{3/2}]_{\geq0}$.)

Two smaller consequences to decide before writing it:

- **The class key.** The published values are `unique` (twelve rows) and `Birch`
  (three). Keys are frozen once cited, so the new row's key has to join that
  vocabulary — `Elkies` is the honest choice. The better scheme was available
  and is now out of reach: Elkies–Watkins index each class by $(M,d)$ with $d$
  the imprimitivity degree of the monodromy group, which names *every* class of
  *every* type, where a person's name names one. That was finding 3 of the
  September critique, and this is the cost of having published past it: at best
  the new row's *display* can say "Elkies, primitive".
- **The references.** Elkies ANTS-IV is where this row comes from, so it joins
  `References` (with `arxiv: math/0005139`, which renders as a link) and
  `sources`. It is also a better citation than the current ones for two things
  already on the page: the twist remark and the $M=3,4$ representatives.

## 4. Above $M=5$ the table's range is bounded by an open problem

Elkies, in the same section: "The question, raised in [Birch–Chowla–Hall–
Schinzel], whether there are any $x,y,k\in\mathbb Q[t]$ of degrees $2m,3m,m+1$
with $m>5$, remains unsolved."

That sentence is the whole answer to how far this table can go. Two computations
say the same thing from the other side:

- Montanus: "maar het lijkt er op dat bijvoorbeeld voor $m=6,\dots,11$ er geen
  klassen zijn met representanten die coëfficiënten in $\mathbb Z$ hebben" — no
  class of type 6 to 11 has an integral representative. That is stated over
  $\mathbb Z$, and for this equivalence it is the same as over $\mathbb Q$: given
  $(f,g,h)\in\mathbb Q[t]^3$, take $u=1/N$ and $w=N^M$ for $N$ a common
  denominator, and $w^2f(ut)=\sum a_jN^{2M-j}t^j$, $w^3g(ut)=\sum b_kN^{3M-k}t^k$,
  $w^6h(ut)=\sum c_lN^{6M-l}t^l$ are all integral, every exponent of $N$ being
  non-negative ($j\leq2M$, $k\leq3M$, $l\leq M+1$), with $w\in\mathbb Q$ so the
  transformation stays rational.
- Elkies–Watkins computed classes above $M=5$ explicitly, by $p$-adic Newton
  lifting plus LLL recognition, and every one landed in a number field: degree 6
  for $M=6$ (the sextic $z^6-z^5-60z^4-267z^3-514z^2-480z-180$), degree 14 for
  the primitive $M=7$, degree 47 for the primitive $M=8$, degree 42 for
  $(M,d)=(11,2)$ and $(17,3)$, degree 14 for $(14,3)$, a quintic for $(7,2)$,
  degree 14 for $(9,2)$, and at $(11,3)$ — the one case where their "each line
  is one Galois orbit" expectation fails — an imaginary quadratic solution and a
  cubic one, still nothing rational. Their Table 1 has no line with a single
  class above $M=5$,
  and a single class in a line is what forces rationality.

So the honest statement of the table's range is: **every rational triple known,
and whether there is another is an open question.** That is a much better
sentence than a bound on $M$, and it is stable — it will not go stale until
somebody proves something.

## 5. Worth doing, in order

1. **Repair `table.yaml` from the live document first.** The copy in the
   repository is the pre-repair draft: definition "of type $M$", formulas still
   the `{name, text}` records that rendered as Python dictionaries, the older
   `complete-note`, and the two false Similar-tables glosses. Anybody who adds
   the new class by editing the YAML and re-publishing will silently undo the
   September repairs. (Not a growth finding; it is what would go wrong first.)
2. **Add Elkies's $M=5$ class** — §3. This is the table's whole remaining
   growth, it is three entries, and the values are above.
3. **Rewrite `complete-note` to say what bounds the range.** Now:
   "it holds every equivalence class for $M\leq4$, and for $M=5$ only Birch's
   symmetric class among the four classes described by [1]". After adding the
   row, the sentence a reader wants is roughly: "it holds every class known to
   have a representative over $\mathbb Q$: the unique class for each
   $M\leq4$ and both such classes at $M=5$; whether any class with $M>5$ has
   one is an open question CITE{ElkiesANTS}". If the row is *not* added, the
   same sentence with "one of the two such classes at $M=5$" is still a large
   improvement, because it tells a reader that the missing classes are missing
   for a reason.
4. **Say how many classes exist, in the comment that already counts them.**
   `comment-class-count` says Montanus gives one class for each $M\leq4$ and
   four for $M=5$. He gives more: a closed formula and the sequence to $M=16$.
   One clause — "and in general $D(M)$, the number of triangulations of a
   convex $(M+1)$-gon up to rotation" — tells a reader how much of the family
   exists, which is the other half of what a range means, and makes the table
   findable by somebody who arrived from the combinatorics rather than from
   Hall's conjecture.
5. **State the chirality fact** in one clause of the same comment: two of the
   four $M=5$ classes are exchanged by complex conjugation, so they have no real
   representative. It is one sentence of Montanus's, it is why the count of rows
   will never approach $D(M)$, and without it a reader cannot tell whether the
   table is incomplete or the family is.

## 6. Noted only

- **A twist is not a new row, and a reader cannot tell.** At $M=1$ every
  $x=t^2+2a$ with $a\neq0$ is the same class, and the rational twists are
  genuinely inequivalent over $\mathbb Q$ while becoming equivalent over
  $\overline{\mathbb Q}$. Somebody who computed $t^2+14$ and searched for it
  finds nothing, although the answer is row 1. `comment-equivalence` covers this
  in principle ("an equivalent representative can have different coefficients
  until this substitution is made") but never says that the constants are
  allowed to be irrational, which is the whole point of a twist. Half a
  sentence, and it decides whether a search hit happens.
- **A companion table over number fields is possible and I would not build it.**
  The corpus can hold values outside the seven searchable types if they carry a
  `type name`, so the $M\geq6$ classes could be published as shown-and-cited
  rather than found. But they would not answer the question the database exists
  to answer, the field degrees run to 47, and there are $D(M)$ of them per type
  with no principled stopping point.
- **The Miranda–Persson dessins are not a source here.** Beukers and Montanus
  computed all 191 Belyi maps on that degree-24 list. The
  Davenport–Stothers shape of degree 24 is $M=4$, the partition $19,1,1,1,1,1$
  at the top of their list, where this table is already complete. Worth knowing
  so nobody mines it twice.
- My attempt to settle $M=5$ by brute algebra instead of by literature is
  worth recording as a cost: the ideal for $M=4$ took 7 minutes to saturate
  over $\mathbb Q$ (one component, one class, as it should be), and at $M=5$ the
  same computation was killed at the container's memory cap, both over
  $\mathbb Q$ and over $GF(32003)$. Elkies–Watkins say why in one line —
  Gröbner bases stop being feasible at about six variables here, which is why
  they use $p$-adic Newton plus LLL. Reading the sources first would have saved
  40 minutes of compute.

## What reads well

The first screen shows $f$, $g$ and $h$ side by side under each $M$, which is
what somebody holding one polynomial of a triple needs; the definition is one
sentence and defines; the rigour details say which polynomial was transcribed
and which was derived. And the table's own structure is what made this report
easy: because it stores one representative per *class* rather than per $M$, the
missing row has an obvious place to go, and the count of classes is a fact the
page can state. A table indexed only by $M$ would have had to be rebuilt to say
any of this.
