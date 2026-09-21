# T2, "Integers": can it grow?

Read on 2026-09-21 as a growth review. 21 entries; the entries block measures
800 bytes by `numberdb_app/limits.py`'s own formula (the brief says 1019, which
is a different serialisation of the same twenty-one rows; nothing below turns
on which). Either way it is about 0.2% of the 320 KB block limit and 1.8% of
the 1200-entry limit. The question asked was whether the range is the whole of
what the definition promises, or whether the table was stopped early.

**Answer: it was not stopped early, and it should not grow. T2 is a window of
examples, not an unfinished family, and the corpus has already written that
sentence down — on T2's sibling T30, "Rational numbers", whose `complete-note`
reads "it holds every $a/b$ in lowest terms with $|a| \leq 5$ and
$1 \leq b \leq 5$, **as examples of the field rather than as a reference
list**". T2 is the same kind of table and carries no such note, and that
absence is the whole reason this question can be asked (§2).**

The brief asks me to read the table's completeness note and its generator. T2
has neither. `Data properties` says `complete: no` and stops; `/files/T2` says
"This table carries no files." Those two absences are the finding, and the
third is the biggest: **the `Definition` field is the empty string**, so the
table promises nothing in writing and the only statement of range anywhere in
the document is the `Programs` snippet `numbers = [-10..10]` (§3).

So the two changes worth making are both sentences, not rows:

1. A `complete-note` in T30's register, saying that the table holds a window of
   small integers as examples of the ring and is not a reference list of
   integers. **Worth doing** (§2).
2. A `Definition`. The audit finds this too, and it is the only thing the audit
   finds. **Worth doing** (§3).

Everything else below is the argument that no row should be added, which is
worth having written down because the arithmetic says the opposite: T2 could
mechanically run to $-599 \ldots 599$ inside every soft limit (§5), and the one
structural argument for extending it dissolves on inspection (§7).

## 1. How I read it

- **Rendered page:** `curl https://numberdb.org/T2` — **direct, no proxy.**
  Nothing listens on `127.0.0.1:1080` on this runner; `--socks5-hostname` gives
  exit 7 on every URL and direct HTTPS gives 200. That is already recorded at
  `docs/agent-environment.md:1117-1134` and counted four times, so I have not
  added a fifth copy.
- **Document:** `/api/table?id=T2`, and the same table as YAML from
  `/bundle/T2`. They agree. The bundle holds `T2/table.yaml` and
  `T2/README.txt` and nothing else — **no `generate.py`**.
- **Provenance:** `/history/T2`. Created 13 January 2021 by bmatschke, in the
  commit "modified One, Zero; added Zeros of Riemann Zeta, Integers" — T2 is
  one of the database's first half-dozen tables. The last edit that touched it
  as data was March 2021, and the March 2021 entry in the list is the global
  rename of "collection" to "table". **The range has not been revisited in five
  and a half years**, which is consistent either with "nobody got round to it"
  or with "it was right"; §2 and §4 decide which.
- **Siblings:** T1 "One", "Zero", T30 "Rational numbers" and T42 "42", read
  from their rendered pages and bundles. These are the tables T2 was made with
  and the ones that point at it, and they are what answer the question.
- **Audit:** `GET /api/table/T2/audit` with the key. One finding,
  `"Definition is empty"`, `clean: false`. §9.
- **Search behaviour:** `/api/lookup?text=7`, `-3`, `13`, `101` against the live
  corpus, before the allowance ran out. §4.
- **Size modelling:** `numberdb_app/limits.py`'s own
  `yaml.dump(block, default_flow_style=False, allow_unicode=True)` byte count,
  applied to synthetic blocks for $-N \ldots N$. §5.
- **No Sage was needed, and running it would have been a mistake.** Every value
  in this table is its own parameter. There is nothing to recompute and no
  precision to check, and a growth review that spent a Sage run confirming that
  the integer 7 equals 7 would have been measuring the wrong thing.
- **One thing I could not finish:** a census of which tables link to
  `HREF{Integers}` across the whole corpus. I walked `/api/table?id=Tn` for
  n = 1..400 and the hourly API allowance ran out at n = 43, so the three
  inbound links I report in §7 are from T1 to T43 only and there may be more
  further up. The allowance is shared with the other campaign runs on this box;
  see §11 and the environment note.

## 2. The corpus has already answered this question, one table over — worth doing

T2 and T30 are the same table in two rings, made in the same fortnight by the
same person. Put their `Data properties` side by side:

    T30   complete: 'no'
          complete-note: it holds every $a/b$ in lowest terms with
            $|a| \leq 5$ and $1 \leq b \leq 5$, as examples of the field
            rather than as a reference list
          repeats: HREF{Integers}

    T2    complete: 'no'

The clause after the comma in T30 is the answer to the growth question for both
tables, and it exists on only one of them. It says that the range is not a
prefix of an enumeration that somebody will extend: it is a handful of examples
chosen to show what the object is, and the table is doing its whole job at that
size. T30 renders it as "Table is complete: no (it holds every $a/b$ … as
examples of the field rather than as a reference list)", which is the sentence a
reader checking whether their own number belongs there actually reads.

On T2 the same field renders as the bare words **"Table is complete: no"**.
What a reader sees is a table of the integers from $-10$ to $10$ that describes
itself as incomplete, with no statement of what it does cover and no statement
of why it stops. That reads as unfinished, and it is why a growth queue picked
it up. The skill is explicit that this is the field's job: "not that the table
is incomplete, which is true of almost all of them, but what it *does* cover".

**Smallest change:** add a `complete-note` to T2 in T30's register. Something
like: `it holds every integer $n$ with $|n| \leq 10$, as examples of the ring
rather than as a reference list of integers`. One line, no rows, and the growth
question stops being askable.

I note in passing that this is a decision for whoever owns the table, not a
fact I can establish: it is possible that the intent in 2021 was "start with
ten and extend later". Nothing in the document says so, the five and a half
years of silence are weak evidence against it, and §4 is the argument that it
would be the wrong intent anyway.

## 3. The `Definition` is the empty string, which is why the range is undefined — worth doing

`Definition: ''` in the stored YAML. On the page this renders as a section
heading with nothing under it:

    <div class="table-section-title">Definition</div>
    <div class="table-section-container">
    </div>

A reader arriving on T2 — from a search for the number 7, which is how they
would arrive; T2 is the first result for it, §4 — sees the title "Integers",
twenty-one rows, and then the word "Definition" over empty space. The next
thing on the page is the comment "The integers form a ring with their usual
addition and multiplication", which is doing the definition's job from the
wrong section: a ring axiom is a *property*, and it is where the skill puts
properties, but with nothing above it a reader has to take it as the
definition.

This bears directly on growth rather than being a separate tidiness point. The
growth question is "is its range the whole of what its definition promises?"
and **the definition promises nothing, because there is no definition**. The
only sentence in the entire document that states a range is
`Programs: numbers = [-10..10]`, which is the bound hard-coded in a field whose
job is something else (§10). So the question the brief asks cannot be answered
from the document at all; it can only be answered from the sibling table, which
is what §2 does.

**Smallest change:** one sentence, saying what the object is and stopping — the
ring $\mathbb{Z}$ of integers, in the register T30 uses ("The field of rational
numbers $\mathbb{Q}$ is the field of fractions of the integers $\mathbb{Z}$").
Compare "Zero" and "One", which are one-entry tables and both have proper
definitions; T2 is the one table in this cluster without one.

## 4. What growth would cost, measured: the search for a small integer is already full

This is the argument that no row should be added, and it is empirical rather
than a matter of taste.

`/api/lookup?text=7` returns **100 results and the message "We only show the
first 100 results."** The first of those hundred is T2, row `7`. The same query
for `-3` returns 100, with T2 fourth. For `13` and `101` — integers outside
T2's window — it also returns 100, and T2 is not among them.

So the reader holding a small integer is not underserved for want of hits;
they are at the cap. What T2 contributes to that capped list is the row
"7: 7" in a table called Integers, which tells somebody who typed 7 that 7 is
an integer. Every row added to T2 puts that same non-answer at or near the top
of one more already-capped search: extending to $|n| \leq 100$ would do it 180
times, and would displace, for `13`, the current first result — T130, "Values
of Dedekind zeta functions of real quadratic fields at negative odd integers",
which is a thing somebody could actually have been holding.

This is the case the skill names in §1 and again in §3: "values that are a
handful of small integers … match everything and tell nobody anything, and
putting them in a table makes search by number worse for everyone", and "A
table is a reference, not a dump … is this a value somebody could plausibly
encounter and want to identify?" T2 is the limiting case of that family — it is
the small integers as such — and the right size for it is the smallest one that
does its other job (§7).

The existing twenty-one rows are not free either, by the same argument. I am
not proposing they be removed: they are what "Zero" and "One" point into and
what T30 declares as the original of its own integer rows, and three tables
depend on their addresses. But it is worth being clear that the twenty-one are
a cost the corpus decided to bear once, not a down payment.

## 5. What growth would cost in size: nothing, and that is the trap

The reason this table reaches a growth queue is that it is tiny, so here is the
arithmetic done properly, with `limits.py`'s own measure:

    range        entries    block      % of 320 KB   % of 1200 entries
    -10..10           21    0.8 KB            0.2%                1.8%
    -50..50          101    3.8 KB            1.2%                8.4%
    -100..100        201    7.5 KB            2.3%               16.8%
    -500..500       1001   38.7 KB           12.1%               83.4%
    -599..599       1199   46.4 KB           14.5%               99.9%
    -1000..1000     2001   77.8 KB           24.3%              166.8%

So the binding soft limit is the entry count, not the block, and it does not
bind until $N = 599$. A table of $-599 \ldots 599$ would sit at 46 KB, below
the corpus median block of 56 KB, and pass every check the server makes.

That is exactly the reasoning the skill refuses: "a denominator bound, a size
target, a count that matches the older tables — none of them is a reason for
any particular number to be present." There is no $N$ at which a reader's odds
of learning something from a row of T2 improve, because the information content
of the row "$n$: $n$" is zero for every $n$. A range chosen to fill the limit
would be 1199 entries of nothing, and it would pass.

I include the table because somebody will otherwise do this arithmetic and
reach the opposite conclusion from it. The measurement is real and the
conclusion it invites is wrong.

## 6. There is no method, and none is needed

The brief asks by what method the table could grow. There is none to describe,
and the reason is worth a sentence because it is unusual in this corpus:
**the value of each entry is its own parameter.** Row `n` holds the number `n`.
There is no computation, no precision, no convention, no branch, nothing that
could be got wrong and nothing an independent source could check. `rigour:
exact` with the standard boilerplate is right, and vacuously so.

Consistent with that: there is no `generate.py` (`/files/T2`: "This table
carries no files"), and `Programs` is `numbers = [-10..10]`, which is the range
and not an incantation. A generator here would be `range(-N, N+1)`, which is
not a program anybody needs attached to a table.

This is the same evidence the T5 review used in the opposite direction — there,
`Programs` was empty because no incantation returns one more value of $\omega$.
Here `Programs` is non-empty and trivial for the same underlying reason: the
family has no computational content. In both cases the emptiness of the method
is a statement about what the table is, and in both cases it points at "this
table is the size it should be".

## 7. The one structural argument for growth, and why it dissolves

There is a real argument for extending T2, and it took reading four sibling
tables to dispose of it, so it is worth writing down.

Rows `0` and `1` of T2 carry `equals: HREF{Zero}` and `equals: HREF{One}` —
the corpus holds one-entry tables for those two integers and T2 links to them
from the rows. The corpus also holds **T42, a one-entry table for the number
42**. T42 is outside T2's window, so the pattern breaks: two of the three
integers in this corpus that have their own tables are rows of T2 with an
`equals` link, and the third is not reachable from T2 at all. The obvious
repair is to extend T2 to cover 42.

It dissolves on reading T42. Its `Similar tables` says:

    integers — contained in

and Zero and One say the same thing. That relation is a fact about the
*mathematics* — $42 \in \mathbb{Z}$ — not a claim that 42 is a row of T2. So
nothing in the corpus requires T2's window to reach any particular integer, and
extending it to 42 would buy one `equals` link at the price of sixty-four rows
of nothing, and would leave the pattern broken again the moment somebody adds a
table for 1729.

The thing the asymmetry actually shows is a missing link in the other
direction, and it costs no rows:

**Smallest change (noted, minor):** T2's `Similar tables` is the empty string,
while Zero, One and T42 all declare `integers — contained in`. T2 could name
them back, with the relation stated — the named integers this corpus holds
separately, and T30 as the same construction over $\mathbb{Q}$. That is the
skill's point that "splitting does not lose the connection; it puts it where it
belongs", and it is the right home for "where are the integers this database
has something to say about", which is the only question growth would have been
answering.

## 8. The row order is only tolerable because the table is small

The twenty-one rows render in the document's order, which is $-10, -9, \ldots,
9, 10$. The first screen of T2 is therefore $-10$ through about $-2$, and the
rows anybody arrives wanting — $0$, $1$, $2$, the two with `equals` links on
them — are in the middle.

The skill names this exact failure: "a table led with $a=-50$ and put $a=2$ —
the row anybody arrives wanting — halfway down. Enumerate by $|a|$, positive
first."

At $|n| \leq 10$ this is a small annoyance: the whole table is one screen, so
nothing is really buried. I raise it under growth rather than as a separate
finding because **it is the clearest evidence that nobody has ever thought of
this range as provisional**. A range meant to be extended would have been
ordered so that extending it was safe; this one is ordered so that extending it
to $|n| \leq 100$ would open the page on $-100, -99, -98$, which is the
rendering the skill warns about, reached by following the existing pattern.

**Worth doing only if the table is ever extended**, in which case reordering is
not optional. At twenty-one rows I would leave it: reordering rewrites the
document for a benefit of one line of scrolling, and the row addresses
(`HREF{Integers#1}`, which T1 uses) are unaffected either way, so it is
harmless but not worth a revision on its own.

## 9. The audit: one finding, and it is right

`GET /api/table/T2/audit` returns:

    {"tid": "T2", "title": "Integers",
     "findings": ["Definition is empty"], "clean": false}

I agree with it, and §3 is that finding argued at length. It is the right thing
to have caught and the most important single fact about this document.

Two things it does not ask, neither of which is a fault in the audit:

- **`complete: no` with no `complete-note`.** T2 declares itself incomplete and
  says nothing about what it holds. A rule could catch this — "a table that
  says `complete: no` should say what it does cover" — and it would fire on a
  great many tables, most of which really are unfinished, so it would be a
  weak signal. On T2 it is the finding that matters (§2). I am not proposing
  the rule; I am recording that the audit's silence here is not evidence.
- **Nothing can ask my question.** Whether a range is a deliberate window or a
  stopped enumeration is not visible in any field, precisely *because* the
  field that would carry it is the one that is missing. That is the shape of
  this whole review: the audit found the empty `Definition`, and the empty
  `Definition` is why a human had to go and read T30 to find out what T2 is.

## 10. Noted only, because I noticed

None of these is worth a revision on its own. Listed so the next person does
not spend their afternoon rediscovering them.

- **`Programs: numbers = [-10..10]`.** The skill says `Programs` is "the
  standard incantation … for a reader who wants one more value", and this
  snippet returns exactly the table and not one value more; it would also be
  silently wrong the day the range changed, since the bound is written into it.
  T30's snippet has the same shape (`[a/b for b in [1..5] for a in [-5..5] if
  gcd(a,b) == 1]`) but is at least a rule rather than a literal. For a table
  whose value is its parameter there is no honest snippet, which is §6 again;
  `numbers = [-10..10]` is as close as it gets and I would leave it.
- **`number-header: $n$<sup>th</sup> integer`.** Raw HTML in a field where the
  rest of the corpus writes LaTeX. It renders correctly — I checked, the
  superscript comes through — so this is a consistency remark, not a rendering
  fault. The heading also claims a little more than the table does: there is no
  standard enumeration of $\mathbb{Z}$ in which the $n$th integer is $n$, and
  what the column actually holds is $n$ itself. `$n$` would be truer and
  shorter. Note that the header is *not* the fallback word `value`, so the
  structural tell for "two tables wearing one title" is absent; T2 is one
  table.
- **A doubled space** in the comment: "their usual addition and  multiplication".
- **`Keywords` is empty.** Defensible here — "integer" and "integers" both stem
  to the title — and I mention it only because the cluster's other tables are
  the same and somebody might take it for an oversight.
- **The row addresses are stable and in use.** T1's definition is "The neutral
  element of multiplication in the ring of `HREF{Integers#1}[integers]`", so
  row `1` of T2 is a citation target. Whatever is done to this table, the
  existing twenty-one parameter values must keep their keys. Extending the
  range would not disturb them; reordering (§8) would not either. Trimming it
  would, which is one more reason the answer to "can it grow" is not "it should
  shrink".

## 11. One environment finding, recorded elsewhere

The corpus-wide link census in §1 stopped at n = 43 with `HTTP 429`, and
retrying it with the API key was refused on every one of 400 requests with
"Rate limit exceeded (1000 requests per 60 minutes)" — the *keyed* allowance,
already spent by the other campaign runs sharing this key. `/bundle/Tn` and the
rendered pages answered 200 throughout, at the same moment `/api/table` was
answering 429, and that is how §2 and §7 were read at all.

Written up in `docs/agent-environment.md` (the shared key, this deployment) and
proposed as a lesson in
`agents/lessons/proposals/20260921T201824Z-critique.md` (`/bundle/Tn` as the
free way to read a table's document; a refused request still costs a unit), in
the two halves the brief asks for.
