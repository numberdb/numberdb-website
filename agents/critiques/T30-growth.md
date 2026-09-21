# T30, "Rational numbers": can it grow?

Read on 2026-09-21 as a growth review. 39 entries, 1382 bytes in the stored
entries block — 3% of the 1200-entry soft limit and 0.4% of the 320 KB block
limit. The question asked was whether the range is the whole of what the
definition promises, or whether the table was stopped early.

**Answer: neither. The definition promises an infinite set, so no range is
ever the whole of it, and the table was not stopped early — it was never
started, because it is not that kind of table.** T30 is a landmark: an
ontological entry for $\mathbb{Q}$, beside `Integers`, `Zero`, `One` and T41's
hyperreals, whose rows are examples rather than a reference list. It should
not grow, and the reason is measurable rather than a matter of taste: every
row added takes the first slot away from a table that has something to say.

It *could* grow, without breaching anything, to 1111 entries. §4 says what
that would cost, with the numbers, so the next person can disagree with a fact
rather than with a feeling. §5 is the one change I would ask somebody to make,
and it is a sentence of prose, not an entry.

## 1. How I read it

- **Document:** `numberdb.table('T30')` through the client in
  `clients/python`. 39 entries, type `Q`, `rigour: exact`, `complete: no` with
  no `complete-note`.
- **Rendered page:** `curl https://numberdb.org/T30` — direct, no proxy. The
  SOCKS proxy at `127.0.0.1:1080` refuses connections on this runner, which
  `docs/agent-environment.md` already records. The page sets cleanly; there is
  no rendering fault in it.
- **Provenance:** `/revisions/T30`. Five revisions. One real one, from the
  data repository on **2021-03-12**, and four migrations since. Nothing has
  been added to this table in five and a half years, while three hundred and
  fifty tables were built around it.
- **Generator:** there is none, and there never was. No `generate.py` is
  attached and nothing in `generators/` points at T30. `Programs` holds the
  Sage line `numbers = QQ`.
- **Audit:** `GET /api/table/T30/audit` returns three findings. §6 says which
  I agree with; none of them is about the range, and one of them is a rule
  that is right in general and wrong here.
- **Search:** 128 calls to `numberdb.search_rational`, described in §3 and §4.
  This is where the answer came from.

## 2. What the range actually is — nobody says, so I reconstructed it

The table does not state its range anywhere. `complete: no` renders on the
page as the bare words "Table is complete: no", with nothing in brackets after
it, and the reader is left to infer the rule from thirty-nine rows.

The rule is exact and worth writing down, because it is the thing a
`complete-note` should say:

> every $a/b$ in lowest terms with $|a| \leq 5$ and $1 \leq b \leq 5$.

That is 39 numbers, and it reproduces the stored set exactly — 11 integers,
then 6, 8, 6 and 8 at denominators 2 through 5. It is not a Farey range and
not a height bound; it is a box on the numerator and the denominator
separately, which is why $5/4$ is here and $6/5$ is not.

Two things follow from having it written down. First, it is a perfectly
reasonable rule, and a reader who knew it could tell in one second whether
their own number is here. Second, it is *arbitrary* in the precise sense the
skill names: "a denominator bound, a size target, a count that matches the
older tables — none of them is a reason for any particular number to be
present." Which is fine for this table, for a reason §3 gives, and would stop
being fine the moment anybody tried to justify a larger bound.

One inconsistency, noted in passing: `Integers` runs $-10$ to $10$, and T30's
integer rows run $-5$ to $5$. The same eleven numbers are in both tables and
nine more are in one of them. Neither table mentions the other's range.

## 3. The definition promises an infinite set, so "complete" is the wrong axis

> The field of rational numbers $\mathbb{Q}$ is the field of fractions of the
> integers $\mathbb{Z}$.

That is a good definition. It defines, it stops, and it links `Integers` at
first mention, which is what the skill asks for. It also promises a countably
infinite set, so `complete: yes` is unreachable and `complete: no` carries no
information: it is true of $\mathbb{Q}$ the way it is true of the integers, by
the nature of the object rather than by the state of the work.

So the growth question has to be asked differently, and the skill asks it:
*will anybody arrive holding one of these numbers and be served?* Here the
answer has an unusual shape, because **T30's value column is a copy of its
parameter column.** The rendered page shows it without disguise: two columns,
both headed `$a$`, and each row reads `-5:` and then `-5`. A reader who
arrives holding $3/4$ already knows the one thing the row tells them.

That is not a fault. It is what a landmark table is: `Zero` holds one entry,
`One` holds one entry, T42 holds the integer 42, and none of them is a
reference to be consulted. They exist so that the corpus has a name for the
thing, so `HREF{Rational_numbers}` resolves, and so the tags `ring` and
`Abelian group` have something to group. For that job, thirty-nine rows are
already more than enough, and the correct number of further rows is zero.

The contrast with T29, next door, makes the point sharply. "Rational multiples
of pi" has 319 entries and the same kind of parameter, and it earns every one
of them, because there the parameter is $a/b$ and the *value* is
$2.0943951\ldots$ — a number a reader can hold without knowing what it is.
T30 has no such gap between parameter and value to fill.

## 4. What growth would cost, measured

**Size never binds.** At about 35 bytes an entry, the box $|a|, b \leq N$
gives:

| $N$ | entries | entries block | of the 1200-entry limit |
|---|---|---|---|
| 5 (now) | 39 | 1.4 KB | 3% |
| 10 | 127 | 4.6 KB | 11% |
| 18 | 407 | 15 KB | 34% |
| 30 | 1111 | 43 KB | 93% |

So the mechanical answer to "how far could it go" is $N = 30$: 1111 entries,
43 KB, a thirteenth of the block limit, no `Size exception` needed, and a
generator anybody could write in four lines. Nothing in `limits.py` stops it.

**Search is what binds, and the cost is at the top of the results list.** Two
measurements.

*What T30 already does.* I searched all 39 of its own values.
**T30 is the first table answering 27 of the 39**, and 462 hits from other
tables sit below it across those searches. The twelve where it is not first
are the integers and $-1/2$, where a lower-numbered table gets there first.
The reason is not relevance: search by number returns tables in **ascending
T-number order**. I printed the T-numbers for three searches — $3$, $3/4$ and
$1/6$, 47 results between them — and there is not one inversion. So a table
numbered 30 that holds a common value holds the first slot for it
permanently. Somebody searching $3/4$ is told "Rational numbers: 3/4" before
they are told that $3/4$ is a critical exponent of the two-dimensional
universality classes (T155).

*What growth would do.* I took the 368 rationals inside $|a|, b \leq 18$ that
are not already stored, sampled 80 of them, and searched each:

- **56 of 80 (70%) are in no table at all.** Today a reader searching $5/11$
  is told "No match in database", which is a true and useful answer: the
  corpus does not know this number. After growth they would get a hit that
  looks like an answer and is not.
- **19 of 80 (24%) have an informative first answer that T30 would demote** —
  $7/4$ from T155, $5/8$ and $3/8$ from T177, $-1/9$ from T161, $1/14$ from
  T253, and so on.

Scaled to the 368, extending merely to $N = 18$ would manufacture about 257
rows that answer a search which currently answers honestly, and push about 87
informative first hits into second place. At $N = 30$ it is roughly three
times that. This is the skill's "every hit in the corpus is worth a little
less for it", in the one table where it is not a rounding error but the whole
effect, and it runs the wrong way: the rows that cost the most are exactly the
ones a bigger bound would add.

There is no version of this that is better. A larger box, a Farey range, a
Stern–Brocot enumeration, denominators up to 18 to match the error-function
tables — each is a different arbitrary rule with the same consequence,
because for a table of the rationals *qua* rationals there is no distinguished
finite subset to choose. Every rational is exactly as much a rational as every
other. That is the difference between this table and every other one in the
corpus, and it is why "which range" has no answer here rather than a hard one.

## 5. What is worth doing: three sentences, no entries

### (a) A `complete-note` that says the range is deliberate — worth doing

This is the whole deliverable of a growth review on this table. The page
currently says "Table is complete: no" and stops, which invites exactly the
question I was sent to answer and leaves the next person to answer it again.
The note renders inside "complete: no (...)", so:

> `complete-note`: it holds every $a/b$ in lowest terms with $|a| \leq 5$ and
> $b \leq 5$, as examples of the field rather than as a reference list, since
> any rational a reader meets is better identified by the table it came from

That is one clause, it states the rule, and it says why there are not more —
which is the sentence a reader checking whether their own number belongs here
actually needs.

### (b) `repeats: HREF{Integers}` — worth doing

Eleven of T30's thirty-nine entries are the integers $-5$ to $5$, which
`Integers` also holds, as the same numbers transcribed rather than as an
agreement between two computations. Search answers with both today: I saw it
on $3$, on $-4$ and on $5$. This is what the field is for — "where these two
tables hold the same number, that one states it first" — and declaring it
makes search answer with `Integers` and name T30 beside it, instead of saying
the same thing twice.

### (c) The `Programs` line claims the whole field — worth doing, small

`numbers = QQ` is not an incantation that produces one more value; it names
the field, and so it says the table holds all of $\mathbb{Q}$, contradicting
the range in (a). The four-line replacement says what is actually here:

    numbers = [a/b for b in [1..5] for a in [-5..5] if gcd(a,b) == 1]

I would not raise (c) on its own, but if somebody is editing the document for
(a) it costs nothing and removes the only other place the page overstates its
range.

## 6. The audit: two findings I agree with, one I do not

`GET /api/table/T30/audit` returns `clean: false` with three findings.

**"Tags: `field` reaches only this table" and "Tags: `rational` reaches only
this table" — agreed, and there is a better fix than deleting them.** I
checked: `field` and `rational` each reach exactly one table, T30, while
`ring` reaches 3 and `Abelian group` 2. A tag with one table on it is not a
way through the corpus. But the useful move is not to drop two tags; it is to
add `algebraic`, which reaches **29 tables and 12,972 numbers** and which
every rational carries by being an algebraic number of degree 1. That puts
T30 on a path a reader actually browses, beside `Algebraic numbers of degree
2` and `$\cos(\pi x)$ for rational $x$. Whether `field` and `rational` then
stay is a judgement for whoever owns the tag list, and the skill's rule —
propose a tag when three or more tables would carry it — suggests `field`
would earn its place if `Integers` and T41 ever acquire companions, and
`rational` probably will not.

**"Definition links to another table; a cross-reference belongs in Similar
tables or a comment" — I disagree, and I think the rule is right in form and
wrong here.** The skill's instruction is the opposite one and is explicit:
"Link the first mention of a thing to what explains it. A table if the corpus
holds one... first mention, once per section." More than that, this particular
link is load-bearing rather than decorative: the definition *is* "the field of
fractions of the integers", so $\mathbb{Z}$ is not a cross-reference the
sentence happens to mention, it is a term the definition cannot do without.
It renders correctly as a link, once. Leave it. If the audit's rule is meant
to catch definitions that have grown a "see also" clause, this is a false
positive on the one case where the link is part of the mathematics.

The audit is silent on the range, which is correct by construction: none of
its rules is about whether a range is the right range, and on this table that
is the only interesting question.

## 7. Noted only

Things I noticed and would not ask anybody to act on.

- **`Keywords` is empty.** A reader who wants the concept rather than a value
  types "rational", "fraction" or "Q". The title carries the first; the other
  two are not in any indexed field. `Keywords: fraction, Q` costs nothing.
  Small, and unrelated to growth.
- **`Similar tables` is empty**, where the relation to `Integers` could be
  stated in words — "the field of fractions of these" — which is the thing
  the `HREF` in the definition cannot carry. Worth a line if somebody is in
  the document anyway. Not worth a revision of its own.
- **`Integers` runs $-10..10$ and T30's integers run $-5..5$.** Aligning them
  would be tidy and would add eight rows that say nothing, so it is the wrong
  kind of tidy. Mentioned because a reader who compares the two tables will
  notice, and the `repeats` declaration in (b) is the honest way to explain
  the overlap.
- **`Integers` has an empty `Definition`** and a `number-header` reading
  "$n$th integer" over rows keyed by the integer itself. That is a fault in a
  different table and belongs in its own critique, not this one.

## 8. The answer in one line

T30 is finished. Not complete — it cannot be — but finished, and the smallest
change that says so is one clause of `complete-note`.
