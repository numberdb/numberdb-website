# T280, "Counterexamples to Euler's sum of powers conjecture": can it grow?

Read on 2026-09-20 as a growth review. 96 entries, 7759 bytes in the stored
document — 8% of the 1200-entry soft limit and 0.6% of the 320 KB block limit.
The question asked was whether the range is the whole of what the definition
promises or whether the table was stopped early.

**Answer: it was not stopped early. The table holds every solution anybody
knows, for every exponent where one exists, and the two exponents that are not
here are empty for reasons that are not going to change.** It is small because
sixty years of computer search have produced twenty-three solutions, not
because a bound was chosen for convenience.

There is exactly one way to add rows without waiting for somebody to discover
something, and I do not think it should be taken. It is set out in §3, with
the numbers, so that the next person can disagree with a fact rather than with
a feeling.

## 1. How I read it

- **Document:** `GET /api/table?id=T280`. 23 solutions, 19 at $k=4$ and 4 at
  $k=5$, stored as 96 parts: 717 characters of actual values in a 1988-byte
  entries block.
- **Rendered page:** `curl https://numberdb.org/T280` — direct, no proxy; the
  SOCKS proxy refuses connections on this runner and
  `docs/agent-environment.md` already says to try the direct `curl` first.
  The page sets cleanly.
- **Audit:** `GET /api/table/T280/audit` returns `clean: true`, no findings. I
  agree, and it is silent on this question by construction: none of its rules
  is about whether a range is the right range.
- **Generator:** `generators/counterexamples-euler-sum-powers/generate.py`. It
  is a checked transcription — two hard-coded tables, a re-derivation of the
  $b=20615673$ row from Elkies' parametrisation at $v=-31/467$, and a
  comparison of the fourth-power $b$ column against the OEIS b-file. There is
  no search in it and no loop that could be given a larger bound. That is the
  right shape for this table, and it is also why "extend the range" is not a
  matter of turning a dial.
- **Sources read:** the Wikipedia article's wikitext, the OEIS A003828 b-file
  (the OEIS entry itself is behind a Cloudflare challenge from here, as in the
  2026-09-16 critique), the arXiv abstract of Braun 2603.05549, MathWorld's
  "Diophantine Equation--4th Powers", and Jean-Charles Meyrignac's EulerNet
  database `http://euler.free.fr/database.txt` (472 KB, last updated 2009).
- **Computation:** Sage, via `agents/sage.sh`. Described in §3.

## 2. The definition's four axes, one at a time

The definition is

> Primitive nonzero integer solutions of $a_1^k+\cdots+a_{k-1}^k=b^k$ with
> $b>|a_i|$ for every $i$ and no pair $a_i=-a_j$; for even $k$ the $a_i$ are
> positive.

so the family is indexed by $k>2$ and, within each $k$, by the solution. Take
the exponents in turn.

**$k=3$ is empty, and provably.** The equation is $a_1^3+a_2^3=b^3$ in nonzero
integers, which is Fermat's last theorem at $n=3$ — Euler, 1770. No row will
ever appear. The table holds none, which is correct, and nothing is missing.

**$k=4$ holds the complete published list.** The 19 stored values of $b$ are
exactly the 19 terms of OEIS A003828 ("numbers $k$ such that $k^4$ is a
primitive sum of 3 positive fourth powers"), ending at $1871713857$, with the
sequence complete to $1986560000$. MathWorld's page on the 4.1.3 equation
names Frye's solution, Elkies' solution and MacLeod's 1997 one and no others;
all three are here. EulerNet records only the minimal solution per $(k,m,n)$
and adds nothing. I found no published fourth-power solution that the table
lacks.

**$k=5$ holds all four known, including the two the definition's signed clause
lets in.** This is the axis where the definition could have over-promised, and
I checked it rather than assuming. Because the $a_i$ may be negative for odd
$k$, a solution of $x_1^5+x_2^5=y_1^5+y_2^5+y_3^5$ — an EulerNet $(5,2,3)$ —
becomes a row of this table as soon as you move everything but the largest of
the five terms to one side. So every known $(5,2,3)$ solution is a row the
definition promises. The EulerNet database lists exactly one $(5,2,3)$,
`14132+220=14068+6237+5027` (Scher and Seidl, 1997), and it is the table's
$b=14132$ row. Braun's 2026 solution is the second. Both $(5,1,4)$ solutions
are here too. Four known, four stored: the signed clause promises nothing the
table does not deliver.

**$k\geq6$ is empty as far as anybody knows.** Resta and Meyrignac showed in
2002 that $a_1^6+\cdots+a_5^6=b^6$ has no solution with $b\leq730000$; for
$k\geq7$ nothing at all is known. A single row at $k=6$ would be a result
worth a paper, and the table would get it the week it appeared.

So three of the four axes are closed by mathematics and the fourth is closed
by the literature. The growth rate of this table is the growth rate of the
subject: the fourth-power list took from 1988 to about 2009 to reach 19 terms,
and the fifth-power list gained its fourth member in August 2026.

## 3. The one avenue that exists, measured

Elkies proved in 1988 that there are infinitely many primitive solutions at
$k=4$, and the particular slice of his construction that Wikipedia and Piezas
quote is a curve you can put in Sage:

$$(85v^2+484v-313)^4+(68v^2-586v+10)^4+(2u)^4=(357v^2-204v+363)^4,$$
$$u^2=22030+28849v-56158v^2+36941v^3-31790v^4.$$

I did that. Translating the known point $v=-31/467$ to the origin
($t=v+31/467$, $q=30731278/218089$, and $g(t)=At^4+Bt^3+Ct^2+Dt+q^2$ with
$A=-31790$, $B=21193407/467$, $C=-14035127773/218089$,
$D=3751065898092/101847563$) gives the Weierstrass model

$$y^2=x^3+Cx^2+(BD-4Aq^2)x+(B^2q^2+AD^2-4ACq^2),$$

with $x=(-2q(w-q)+Dt)/t^2$ and $y=(x^2/(2q)-2Aq)t-Dx/(2q)-qB$, an
identity I checked in the function field of the quartic rather than recalling
it. Sage reports that curve as rank 3 with torsion $\mathbb{Z}/2$. Mapping
1372 points of the Mordell–Weil group back to $v$ and clearing denominators
gives, in increasing order of $b$:

| $b$ | digits | in T280? |
|---|---|---|
| 20615673 | 8 | yes |
| 589845921 | 9 | yes |
| 638523249 | 9 | yes |
| 3393603777 | 10 | **no** |
| 5062297699257 | 13 | no |
| 20249506709579721 | 17 | no |
| 62940516903410601 | 17 | no |
| 108593344076382641697 | 21 | no |
| 19874054816411213708481009 | 26 | no |
| … | | |

Nine more members with $b<10^{30}$, fifty-one with $b<10^{60}$. The rank claim
is Sage's; the solutions are not. Every one of them satisfies its identity in
exact integer arithmetic with $\gcd=1$, and the smallest new one is small
enough to check by hand:

$$664793200^4+2448718655^4+3134081336^4=3393603777^4.$$

Three facts follow that are worth having whatever is decided.

**The family is a thin slice, not the picture.** Only 3 of the 19 stored
fourth-power solutions lie on this curve. The other 16 were found by
exhaustive search, and no parametrisation is known that produces them.

**Size is not what stops the table.** Adding the nine members below $10^{30}$
costs 36 entries and 4192 characters: the table would go from 96 entries and a
2 KB block to 132 entries and about 6 KB. Even taking the family to $10^{60}$
— 51 more solutions, largest entry 60 characters — lands near 300 entries and
30 KB, a quarter of the entry limit and a tenth of half the block limit. The
constraint the skill warns about for polynomial families does not bind here at
any range anybody would choose.

**The new members sit just above the searched range.** $3393603777$ is only
$1.71\times$ the bound to which A003828 is complete. So the gap between what
has been searched and the first thing anybody can write down is one factor of
two — which is also the honest forecast for when this table next grows on its
own: the next exhaustive push, not the next elliptic curve.

### My recommendation: note it, do not add it

Adding the family members would be defensible and I would not argue hard
against somebody who did it. I would not, for three reasons, in decreasing
order of weight.

1. **Nobody arrives holding one.** The skill's test for a range is whether
   somebody will turn up with the number. $1871713857$ reaches a reader from a
   search or from OEIS. $3393603777$ reaches a reader only from running the
   parametrisation — and somebody who has run the parametrisation already
   knows what their number is. The three family members already in the table
   are there because a search found them independently, which is the
   difference.
2. **The table would become the primary source.** I could not find these
   values published anywhere: Piezas' page is a Google Site that serves no
   text to `curl`, the sci.math thread Wikipedia cites is gone, and the
   EulerNet database predates none of this but lists only minimal solutions.
   A table of *known solutions to a Diophantine equation* that contains
   numbers known only because this table computed them is a different kind of
   object, and that is a decision for a person, not a fill.
3. **The cap would be arbitrary.** $10^{30}$, $10^{60}$, "nine more" — none of
   those is a reason for any particular row to be present, which is exactly
   the counting-rather-than-choosing the skill names. The current range has a
   reason a reader can state in one clause: everything that has been found.

### What is worth doing, and it is one sentence

The page never tells a reader that infinitely many fourth-power solutions
exist. Comment (3) says $b=20615673$ is "the first solution Elkies found",
which reads as a fact about Elkies' luck rather than about the family. A
reader who arrives holding a 12-digit fourth-power solution — the likeliest
kind of reader this table has, because that is what a home search produces
next — is not told why it is not here.

Smallest fix, in `Comments`, beside the existing quartic-range comment:

> Elkies' construction CITE{Elkies1988} produces infinitely many primitive
> fourth-power solutions; the smallest is the $b=20615673$ row. The table
> holds the range that has been searched exhaustively, so all but the
> smallest members of that family are outside it.

That is worth doing. It costs one sentence, it turns the completeness note
from a bound into an explanation, and it is the only finding in this review
I would ask somebody to act on.

## 4. Noted only

- **`complete-note` already makes two different kinds of claim** and does not
  mark them as different: "the four fifth-power primitive solutions listed in
  …" is a statement about the frontier of knowledge, and "no further terms up
  to $1986560000$" is a statement about a search. Both are true and both are
  sourced. I mention it because if the table ever does take on family members
  the note will need a third clause, and the seam is already there.
- **The largest stored $b$ is $1871713857$ and the stated bound is
  $1986560000$.** Not a fault — the bound is the search's, not the data's —
  but a reader scanning the last row and the note sees two numbers that do not
  match and has to work out why. Nothing needs changing.
- **The $k$ parameter is written as the family, "an integer exponent $k>2$",
  not as $\{4,5\}$.** That is right by the skill's rule, and it is also what
  makes this review's question answerable: the definition genuinely does
  promise all exponents, and §2 is the check that the promise is kept.
- **The generator cannot be pointed at a larger range**, because there is no
  range to point it at. If the family members are ever wanted, the code to add
  is the elliptic curve above — about thirty lines, and it would give the
  generator a second independent check on the three family rows it already
  holds.
