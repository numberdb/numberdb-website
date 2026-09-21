# T19, "Pólya's random walk constants": can it grow?

Read on 2026-09-21 as a growth review. 8 entries, 2756 bytes in the stored
entries block — 0.7% of the 1200-entry soft limit and 0.9% of the 320 KB block
limit. The question asked was whether the range is the whole of what the
definition promises, or whether the table was stopped early.

**Answer: it was stopped early, and by its source rather than by its subject.**
The definition promises every $d \geq 1$. The table holds $d \leq 8$ because
OEIS holds $d \leq 8$ — the table says so itself, in `sources: CITE{OEIS} for
$d \geq 4$` — and nothing about the mathematics stops there. $p(d)$ is one
one-dimensional integral; I computed $d = 3 \dots 40$ to 170 digits in
**25 seconds**, and the computation reproduces every one of the 566 digits the
table already stores, exactly.

So the range can grow, the method is cheap, and — measured, not assumed — every
value it would add is a value the corpus answers "no match in database" to
today. §5 says how far I would take it. §6 ranks the changes, and the one I
would do first is **not** a row: it is the definition, which does not currently
determine which walk this is.

## 1. How I read it

- **Rendered page:** `curl https://numberdb.org/T19` — direct, no proxy. The
  SOCKS proxy at `127.0.0.1:1080` refuses connections on this runner;
  `docs/agent-environment.md` already records it, and direct HTTPS works. The
  page sets cleanly: no broken maths, no `argument ()`, no eaten `<`.
- **Document:** `GET /api/table?id=T19`. 8 entries, type `R`,
  `rigour: heuristic`, `complete: no` with **no `complete-note`**.
- **Provenance:** `/revisions/T19`. Five revisions. One real one, from the data
  repository on **2021-03-10**, three migrations, and one annotation by
  bmatschke on 2026-08-15 that added the `rigour details` paragraph. The
  numbers have not been touched in five and a half years.
- **Generator:** there is none in this repository. Nothing in `generators/`
  mentions T19, and `Programs` is empty. The `rigour details` note refers to "the
  script's own attempt to compute them", which lives in the 2021 data repository
  and says it does not work.
- **Audit:** `GET /api/table/T19/audit` returns `"clean": true`, no findings.
  §7 says where I agree and where the rules did not reach.
- **Computation:** `agents/sage.sh` on `/tmp/polya.py`, `/tmp/polya2.py`,
  `/tmp/polya4.py`. §3.
- **Search:** 88 calls to `/api/lookup`, §4. This is where the range answer
  came from.

## 2. What the range is, and what the definition promises

The Definition reads:

> For $d\geq 1$, $p(d)$ is the probability that a random walk on a
> $d$-dimensional lattice returns to the origin.

`Parameters` says `$d$ — integer ($d \geq 1$)`. That is correct practice and
worth saying so: it describes the family, not the run, which is what the skill
asks for and what many tables get wrong. The consequence, though, is that the
promise is unbounded and the table stops at 8 with nothing saying why.

`complete: no` carries no note, so the page renders the bare words **"Table is
complete: no"** with nothing in brackets after it. A reader cannot tell whether
$d \leq 8$ is a deliberate range, an unfinished one, or all that is known. The
skill is explicit that this clause is the sentence a reader actually wants.

The real rule is reconstructible from `sources` and the Links block: the table
holds exactly what OEIS holds. A086230 is $d=3$; A086232 to A086236 are
$d=4 \dots 8$; there is no A0862xx for $d = 9$. Every transcribed entry carries
87 significant digits, which is a fact about an OEIS constant listing and not
about $p(d)$. That is a stopping rule about somebody else's database, not about
random walks, and it is the clearest evidence that the table was stopped early.

## 3. The method, and what it costs

$u(d) = \sum_n P(S_n = 0)$ is the expected number of visits to the origin, and
$p(d) = 1 - 1/u(d)$. Writing $1/(1-x) = \int_0^\infty e^{-t(1-x)}\,dt$ under the
Fourier integral for $u(d)$ and substituting $s = t/d$ collapses the
$d$-dimensional integral to one dimension:

$$u(d) = \frac{1}{(2\pi)^d}\int_{[-\pi,\pi]^d} \frac{dx}{1 - \frac{1}{d}\sum_j \cos x_j}
       = \int_0^\infty e^{-t} I_0(t/d)^d\,dt
       = d \int_0^\infty g(s)^d\,ds, \qquad g(s) = e^{-s} I_0(s).$$

The only difficulty is the tail: $g(s) \sim (2\pi s)^{-1/2}$, so $g^d$ decays
only like $s^{-d/2}$ and at $d=3$ the part beyond $s = 3000$ is still 0.5% of
the answer. I split at $S$, did $[0,S]$ with mpmath's `quad`, and did the tail
in closed form from $I_0(z) \sim e^z(2\pi z)^{-1/2}\sum_k a_k z^{-k}$ with
$a_k = ((2k-1)!!)^2/(k!\,8^k)$, raising that series to the $d$-th power and
integrating term by term.

**It reproduces the table.** Every stored digit is an exact prefix of the
computed value — not "agrees to within rounding", a literal prefix:

| $d$ | stored digits | all correct? | relative difference |
|---|---|---|---|
| 3 | 131 | yes | 1.69e-132 |
| 4 | 87 | yes | 4.41e-88 |
| 5 | 87 | yes | 1.82e-87 |
| 6 | 87 | yes | 9.01e-87 |
| 7 | 87 | yes | 1.44e-88 |
| 8 | 87 | yes | 9.06e-88 |

and at $d=3$ it agrees with the table's own closed form, Formula (2), to 171
digits. **The transcription was done correctly**, which is a useful thing for
the next person to know before they rebuild: this is not a correction job.

**It costs nothing.** In one throwaway Sage container, at 170 decimal digits of
working precision:

    d = 3       4.99 s   (first call; builds the quadrature nodes)
    d = 4..8    0.12–0.20 s each
    d = 24      0.56 s
    d = 40      0.91 s
    d = 3..40   25.1 s total

Two independent split points, $S = 1500$ and $S = 3000$, agree to 1e-171, and
the last retained tail term is below 1e-260 throughout. Nothing here is close
to a limit of the method; it would go to $d = 400$ as happily as to 40, and
gets *faster* as $d$ grows because the tail decays faster.

For the record, the first ten new values at 100 significant digits:

    9   0.06344774965272473309556229583862092543841602880327134617130861804771645067612364597374920615106347684
    10  0.05619753597426778812097369256252412572131681661862210185319744794884561748614255392778281480798058524
    11  0.05045515982133130675349768151610300931946165502289539810969053514045851758487948267758994370900430909
    12  0.04578912090062103788311882692646461254679406752980630494852660034747344004838321547187668566897208159
    13  0.04191989707897463321726587580021820451192321896855816833194779639197097739750859880121835291375396338
    14  0.03865787709067398563123860871290373350439168350655296818105470054523292056065247582389469754965337028
    15  0.03586962312535651422940427078451975465049107884717585903712209471210775666484879110805079172755505899
    16  0.03345836446578852979169613649642419772929599895495342275548869167129342222881511669912496403704895132
    17  0.03135214039702685418547646802863779023830116440533515593627290088234997167324912775579864597934894135
    18  0.02949628913328060737448449212923433617280864170050708885240578015950528889927957510241915290048198798

These are computed here, not taken from anywhere, and should be checked
independently before publication — §6 says how.

## 4. What growth would cost and what it would buy

**Size never binds.** At 100 significant digits a value is 102–103 characters.
The current block spends about 344 bytes an entry including record structure,
and its values average only 71 characters, so at 100 digits a table to
$d = 32$ is roughly 12 KB: under 4% of the block limit and 3% of the entry
limit. Even $d \leq 100$ would be inside every limit. The constraint the skill
names as usually binding — readability of the largest entry — does not bite
either: the entries do not grow, they shrink.

**So the question is whether anybody arrives holding one.** I measured what the
corpus answers today for each candidate, truncating $p(d)$ to 4, 5, 6 and 8
significant digits and asking `/api/lookup`, over all 374 published tables:

| query length | $d=9\dots24$: how many of the 16 get any hit |
|---|---|
| 4 significant digits | 11 of 16 (all incidental — T340, T353, T209, T363, …) |
| 5 significant digits | 4 of 16 |
| 6 significant digits | **0 of 16** |
| 8 significant digits | **0 of 16** |

and, for contrast, every value already in the table resolves to T19 *alone* by
5 or 6 digits ($p(3)$ and $p(7)$ already at 4).

That is the whole argument for growth, and it is the exact opposite of what the
same measurement said about T30 three hours ago. There, growth would have taken
a search's first slot from a table that had something to say. Here there is no
first slot to take: a reader who computes a nine-dimensional lattice Green
function today, gets 0.0634477, and asks the database is told "No match in
database". That answer is currently true and unhelpful, and each row converts it
into a true and useful one while displacing nothing.

Self-collision is not a risk either. Consecutive values are separated by about
$1/(2d^2)$ — 0.0005 at $d = 32$ — so they stay distinguishable at four digits
forever, and at 100 digits they could not collide in any case.

## 5. How far, then

**There is no mathematical stopping point, and the asymptotics do not supply
one.** I checked the obvious candidate: if $p(d) \approx 1/(2d)$ eventually
named the number well enough that a reader could identify it by arithmetic, the
rows would become redundant. It does not. $2d\,p(d)$ is

    d = 8    1.1666
    d = 16   1.0707
    d = 24   1.0451
    d = 32   1.0331
    d = 40   1.0262

— convergence like $1/d$, so the leading term gives two digits at $d = 40$ and
would need $d \sim 10^3$ to give six. The table is never made redundant by a
formula, and it is never forced to stop by size. **The cutoff is a judgement,
and the skill's actual requirement is that the judgement be written down.**

My recommendation is **$d \leq 32$**, and I want to be clear that the number
itself is the weakest part of this report. What I can defend: it is four times
the present range for about 11 KB and one 25-second run; every value in it is
one a reader could plausibly arrive holding, since anyone who computes $u(d)$ at
all computes it in a dimension somebody named; and it leaves the table at 3% of
the entry limit, so the next person can extend it further without a size
exception or an argument. What I cannot measure from here is where readership
actually falls off — whether it is at 12, 32 or 100. If somebody who knows the
lattice-Green-function literature says 16, take 16; the important thing is that
whichever number is chosen appears in `complete-note`, because at the moment no
number appears there at all.

**What would not be growth of this table.** The three-dimensional Pólya constant
is the one for the *simple cubic* lattice. The body-centred and face-centred
cubic lattices have their own return probabilities — the other Watson integrals
— and those are a different family indexed by a lattice name, not by $d$. They
belong in their own table, and the corpus has no table of Watson integrals or
lattice Green functions at all: I checked all 374 titles and tags for "Watson",
"lattice", "Green", "walk". That is a table-wanted idea, not a range for T19.

## 6. The changes worth making, ranked

**1. Say which walk it is. Do this before adding any row.** The definition says
"a random walk on a $d$-dimensional lattice". That does not determine the
object: it names neither the lattice nor the step distribution, and at $d = 3$
the simple cubic, body-centred cubic and face-centred cubic lattices give three
different constants. Two people would not build the same table from this
sentence. The stored 0.340537… is the simple cubic one. The smallest fix is to
replace "a random walk on a $d$-dimensional lattice" with "the simple random
walk on $\mathbb{Z}^d$, each step uniform among the $2d$ nearest neighbours" —
one clause, no new sections. This is the finding I would act on even if nothing
else in this report is taken, because it is what any extension has to build
from.

**2. Write the `complete-note`.** One clause finishing "complete: no (…)". If
the range stays at 8: "it holds the dimensions tabulated in OEIS, $1 \leq d \leq
8$". If it grows: "it holds every $d$ with $1 \leq d \leq 32$". Either is an
enormous improvement on the current blank.

**3. Replace the transcription with a computation, and extend in the same
run.** One generator, three lines of substance, 25 seconds for the whole range.
This is worth more than the rows themselves: it retires `sources: OEIS`, it
lets `rigour details` describe a method instead of an apology, and it addresses
`reliability: no error bounds specified for $d \geq 4$ (help needed)`, which has
been asking for help since 2021. §3 gives the method and §8 what I got as far as
on making it rigorous. Fill `Programs` at the same time — for a table whose
whole growth question is "can another value be computed", an empty `Programs`
block is conspicuous, and the incantation is short.

**4. Regularise the precision.** $d = 3$ carries 131 digits and $d = 4 \dots 8$
carry 87, because those are the lengths two different OEIS entries happened to
have. The house is 100. A rebuild makes them uniform for free.

**5. Then the rows**, $d = 9$ upward, with the range recorded in
`complete-note`.

Items 1, 2 and 4 are prose and cost an afternoon between them. Item 3 is the
one with real value. Item 5 is cheap once 3 is done and pointless before it.

## 7. Things I noticed that are not about growth

Ranked, and the last two are noted only because I was looking.

**Four of the six OEIS links point at the wrong sequence.** In the rendered
page:

    href="https://oeis.org/A086230/">A086230<     correct (d=3)
    href="https://oeis.org/A086232/">A086232<     correct (d=4)
    href="https://oeis.org/A086230/">A086233<     wrong
    href="https://oeis.org/A086230/">A086234<     wrong
    href="https://oeis.org/A086230/">A086235<     wrong
    href="https://oeis.org/A086230/">A086236<     wrong

A reader who clicks "A086236 $(d=8)$" — which is the *source* the table cites
for that value — lands on the three-dimensional sequence. Since `sources` names
this link as the provenance of five of the eight entries, this is the one
non-growth finding I would call a real defect. The fix is four characters in the
`Links[OEIS]` string, and the audit cannot see it because both URLs are valid
and answer 200.

**Formula (2) links "Gamma function" to Wikipedia, and the corpus holds it.**
T9, "Values of the Gamma function at rational numbers", contains
$\Gamma(1/24)$, $\Gamma(5/24)$, $\Gamma(7/24)$ and $\Gamma(11/24)$ — I checked
all four are present — which is exactly the product in that formula. The skill
is direct about this: a reference to a table here is worth more than a link to
Wikipedia for the same thing, because the reader following it lands on the
numbers. `Similar tables` is empty and T9 is the obvious occupant.

**`/files/T19` answers HTTP 500.** The link labelled "files" is on the table
page itself. `/files/T30`, `/files/T9` and `/files/T116` all answer 200, so this
is specific to T19 rather than a dead feature. I could not diagnose it further
without the database. This is a site bug rather than a table fault, and I have
written it up in `docs/agent-environment.md`.

**Everything else reads well.** I checked hardest for the faults the standard
names: the page renders with no broken mathematics and no display artefacts; the
Definition is one sentence and does not drift into history or range (its problem
is under-specification, not over-stuffing); `Parameters` describes the family and
not the run; no field points at something rather than naming it; no claim on the
page is about the website rather than about the mathematics. The `rigour details`
paragraph is unusually honest — "the script's own attempt to compute them carries
the comment that it does not work" — and it is the reason this review had
somewhere to start.

## 8. The audit, and one thing I could not finish

`GET /api/table/T19/audit` says `"clean": true`. **I agree it is clean on its own
rules**, and I checked why it does not see the two things §7 lists first. The
"points outside for something this database holds itself" check runs over
`Links`, and the Wikipedia Gamma link is inside a *Formula*, so it is out of
reach; the first-mention link check matches a phrase against table titles, and
"Gamma function" does not match "Values of the Gamma function at rational
numbers". Neither is a bug in the audit, and neither is worth a new rule on this
evidence. There is no check for `complete: no` with an empty `complete-note`,
and none for two Links carrying the same URL under different labels; both would
be cheap, and both would have fired here.

**What I could not finish.** I tried to produce a *rigorous* enclosure, so that
`reliability` could stop asking for help. The scheme is sound and I want it
recorded so the next person does not rediscover it:

- Arb (`ComplexBallField.integral`) gives a rigorous enclosure of
  $\int_0^S g(s)^d ds$, and `bessel_I` is rigorously enclosed at any argument —
  I checked it at $s = 10^{62}$.
- The tail has an elementary envelope. From
  $g(s) = \frac{1}{\pi}\int_0^\pi e^{-s(1-\cos t)}dt$ and $1-\cos t \geq
  2t^2/\pi^2$ on $[0,\pi]$, $g(s) \leq \sqrt{\pi/(8s)}$, so
  $\int_S^\infty g^d \leq (\pi/8)^{d/2} S^{1-d/2}/(d/2-1)$, which is added to the
  ball as a one-sided error. For 60 digits this needs $S = 10^{18}$ at $d = 9$
  and $S = 10^{62}$ at $d = 4$.
- **The trap**, which cost me two runs: Arb integrates over complex *ellipses*
  with foci at the ends of the interval, and for a long interval $[a,b]$ with
  $b \gg a$ those reach into $\mathrm{Re}(x) < 0$, where $e^{-x}I_0(x)$ contains
  $e^{-2x}$ and the bound explodes. `CBF.integral(f, 10^3, 10^5)` at $d = 9$
  returned a ball of radius **1e193465**, and summing such pieces gives `nan`
  with no indication of which one was responsible. Intervals with $b = 2a$ keep
  every ellipse in $\mathrm{Re}(x) > a/2$ and the bound stays tame — but that is
  about fifty pieces to reach $10^{18}$ and two hundred to reach $10^{62}$, and
  the run did not finish inside the budget I gave it.

So the rigorous version is unfinished, not blocked. Whoever does item 3 should
budget for it, or find a sharper tail bound than the crude $\sqrt{\pi/(8s)}$ —
the asymptotic series with a proved remainder would cut $S$ from $10^{62}$ to
something small, and arb bounds that series itself.

---

Nothing in this report was applied. The table stands as it was.
