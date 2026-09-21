# T11, Factorial of natural numbers: can it grow?

Read on 2026-09-21 against <https://numberdb.org/skill>. Nothing was changed.

**The short answer.** T11 holds $n!$ for $0 \leq n \leq 100$. Its definition
promises every $n \geq 0$, so no range makes it complete: the range is a
choice, and the table states no argument for the one it made. It was not
stopped by a limit -- 8954 bytes is 2.7% of the soft block limit and 101
entries is 8% of the soft entry limit -- and it was not stopped by an argument
either. It was stopped by its source: the 101 stored values are, key for key
and digit for digit, OEIS A000142's b-file, which runs `0..100` and no
further, and the 2021 generator that built the table has `[0..100]` written
into it.

There is exactly one boundary beyond 100 with a reason behind it rather than a
count, and it is $n = 170$: that is the largest factorial a double-precision
calculation can hand anybody back finite, since $171!$ overflows. Extending
there costs about 17 KB and adds seventy values that cannot collide with
anything.

So: **extend to $n \leq 170$, and say so in a completeness note.** If only one
thing is done, do the note, on the range that is there today.

## What is there

101 entries, $n = 0$ to $100$, type `Z`, `rigour: exact`, `complete: no` with
no `complete-note`. The page renders cleanly: no broken mathematics, the
parameter reads "$n$ — integer ($n \geq 0$)", the value column is headed
`$n!$`, and the 158-digit last entry wraps without breaking the layout. The
audit returns `{"findings": [], "clean": true}` and I agree with it on
everything it checks; what it does not check is the subject of this file.

The values agree with A000142's b-file on all 101 entries and with a
recomputation. That check cost two seconds and is not where the work is; it is
reported only so the rest of this file can be about the range.

## 1. The table never says what its range is. Worth doing, and worth doing first.

A reader who wants to know whether their $137!$ is here reads "Table is
complete: no" and learns nothing, then scrolls 101 rows to the bottom and
infers it. The skill is explicit that this sentence is the one such a reader
actually reads: "Say which range you chose and why in the completeness note.
That sentence is the argument."

The smallest change, under `Data properties`:

    complete-note: it holds $n!$ for every $n$ with $0\leq n\leq 100$

which renders as "Table is complete: no (it holds $n!$ for every $n$ with
$0 \leq n \leq 100$)". T13, the nearest sibling in the corpus, already reads
exactly like that, and its note goes on to give the reason: "which covers the
Bernoulli numbers used by Euler-Maclaurin expansions at about a hundred
digits". T11 should carry both halves too.

This is worth doing whether or not anybody extends the table. It is worth
doing first because writing the sentence is what forces the decision in
section 3.

## 2. How far it could go: the ceilings, measured

The block model is `len(str(n!)) + len(str(n)) + 17.5` bytes per entry,
calibrated against the stored block: it predicts 8.7 KB at $n = 100$ where the
table stores 8954 bytes.

| range | entries | entries block | largest entry |
|---|---|---|---|
| 0..100 (today) | 101 | 8.7 KB | 158 digits |
| 0..170 | 171 | 26 KB | 307 digits |
| 0..250 | 251 | 59 KB | 493 digits |
| 0..400 | 401 | 161 KB | 869 digits |
| 0..550 | 551 | 320 KB | 1252 digits |

Three ceilings, and they are not in the order the task's framing suggests:

* **The entry limit never binds.** 1200 entries would be $n = 1199$, and the
  block at that range is 1.7 MB, five times the soft block limit. For this
  table the headroom in entries is not headroom in anything.
* **The block limit binds at $n \approx 550$**, and the corpus's own target of
  half of it, 160 KB, binds at $n \approx 400$. That is the absolute ceiling
  and nothing below argues for going near it.
* **Readability binds later than either**, which is unusual here. The corpus
  brought the Fibonacci polynomials back from $n = 150$ (2248 characters) to
  $n = 100$ (1107) because an entry stops being something a person reads. On
  that measure $400!$ at 869 digits is still shorter than $F_{100}$. T11 is
  the cheapest growing family in the corpus at the house range: one integer
  per $n$, not $n/2$ coefficients.

So the house range of $n = 100$ -- which corpus-shape.md derives from what
fits for *polynomials*, and which T108 pays 42 KB for -- costs T11 8.7 KB.
T11 is sitting at a bound that was measured for somebody else's entries.

## 3. Where it should actually stop

Capacity is not a reason, and the skill says so plainly: "a denominator bound,
a size target, a count that matches the older tables -- none of them is a
reason for any particular number to be present." So $n = 400$ is out because
it is where the bytes run out, and $n = 250$ is out because it is where T13
happens to stop. The question is which factorials somebody arrives holding.

**Two arguments say extend.**

*There is a real boundary at 170.* $170! = 7.257415615307998967\ldots \times
10^{306}$ is the largest factorial that fits in a double; $171!$ overflows.
Every factorial that reaches a person through floating-point arithmetic --
`scipy.special.factorial`, `gamma`, any spreadsheet, any numerical library --
is therefore $n \leq 170$, and a reader who pastes the repr `7.257415615307999e306`
into the search box is searching an interval that contains the stored integer,
because the corpus reads a written decimal as its last-place interval. That is
the same species of argument as the one that re-based the error-function
tables on "every argument of two decimal places": a boundary set by how
numbers reach people, not by a count.

*Extending costs search nothing.* This is the unusual part, and it is why the
usual caution does not apply. The skill's warning about over-long tables is
that they bury the common values: class numbers are 1, 2, 3 and match
everything. The values this extension would add are 160- to 307-digit
integers. Measured on the live corpus: $0! = 1$ matches 98 tables, $5! = 120$
matches five, $14!$ matches two, and $50!$ and $100!$ match one -- this one.
From about $n = 14$ upward a factorial is already unique in the database, and
nothing added between 101 and 170 can dilute a single other table's hit. The
cost of extending here is 17 KB and no more.

**One argument says leave it.** Nobody has to consult a database to identify a
large factorial: count the trailing zeros, invert Legendre's formula to get
$n$ within a block of five, divide once to confirm. The database's real work
on this family is at small $n$, where the number is short and unmarked. That
argument is true, and it is an argument against $n = 400$ rather than against
$n = 170$: it does not distinguish 100 from 170, and 170 is where a machine
stops being able to hand you the number at all.

On balance: **170**. It is a fact about the family rather than about the
storage, it is a sentence that finishes "complete: no (...)", and it leaves
the table at 8% of the soft block limit, so the next person can move it again
without breaching anything.

    complete-note: it holds $n!$ for every $n$ with $0\leq n\leq 170$, which
      is every factorial representable as a double, since $171!$ overflows

If the owner would rather not move the range, the note on `0..100` is still
worth writing, and it has a source to cite: it is the range of A000142's
b-file.

## 4. By what method

Trivially, and that is the point: nothing about this range was limited by the
computation.

The attached `generate.sage` is 275 bytes from 2021-03-04 and predates the
`numberdb` package. It dumps a YAML file into a repository path that no longer
exists in this shape:

    numbers = {int(n): int(n.factorial()) for n in [0..100]}

Extending is the edit `100` → `170`, and the whole run is milliseconds. If the
file is being touched anyway, it is worth replacing with a `numberdb.Generator`
whose `value` returns `ZZ(n).factorial()` and whose `enumerate` yields
`n = 0..170`, so that `verify()` works against the table and the next person
gets the checks for free.

Independent checks available without writing any new mathematics: the
recurrence $n! = n \cdot (n-1)!$ against a direct product; the trailing-zero
count against Legendre's formula $\sum_k \lfloor n/5^k \rfloor$; A000142's
b-file over the part already stored; and $170!$ against the double above.

## Other things a reader would see, not about growth

Noted because I noticed them, ranked below everything above.

1. **The `Programs` snippet is broken as a program.** The page shows

       numbers = {n.factorial() for n in [0..100]}

   which in Sage is a *set* comprehension: it returns 100 values, not 101,
   because $0!$ and $1!$ are both 1 and a set keeps one of them, and it throws
   away $n$, so nothing in the result says which factorial is which. The
   generator has it right -- `{int(n): int(n.factorial()) for n in [0..100]}`
   -- and the key was dropped somewhere between the two. The skill wants
   `Programs` to be the incantation for a reader who wants *one more value*,
   so the smallest fix is smaller still: `n.factorial()`, or `factorial(n)`.
   Worth doing; it is the one thing on the page a reader copies.

2. **The definition does not cover $n = 0$, and the first row is $n = 0$.**
   "$n! := 1\cdot 2\cdots n$" read at $n = 0$ is an empty product, which is a
   convention the reader has to supply, and the parameter constraint $n \geq 0$
   promises it. One clause fixes it: "with $0! = 1$, the empty product."
   Worth doing.

3. **T9 holds these same numbers and neither table says so.** `Similar tables`
   is empty. T9, "Values of the Gamma function at rational numbers", stores
   $\Gamma(s)$ at $s = 1, \ldots, 30$, so it holds $0!$ through $29!$ as
   100-digit reals, and a search for $14!$ answers with both tables today.
   That is the good case rather than a duplication -- the agreement is
   $n! = \Gamma(n+1)$, a theorem, so both should answer, and `repeats:` would
   be wrong here. What is missing is the relation named in `Similar tables`,
   and a link at the first mention of the Gamma function, which `Formulas`
   already names in formula (2) as plain text. Worth doing, and it is the
   cheapest way to make the second formula useful.

4. `Comments` and `Keywords` are empty. Both are fine: the title carries the
   only word anybody would type, and there is no convention to warn about
   beyond point 2. Noting it only so the next reader does not spend a turn on
   it.

## On the audit

`GET /api/table/T11/audit` returns clean, and it is right to. Every rule it
enforces is satisfied: the parameter states the family's constraint and not
the run's, the value column is headed with a symbol rather than the word
`value`, no value hides in a comment, no display carries a formula, there is
one parameter and it is an argument rather than a name. The three things above
that a reader does see -- an absent completeness note, a set comprehension
where a dict was meant, a definition that stops one case short of its own
parameter -- are all outside what it checks.
