# Stage five: split a table that holds more than one quantity

A draft in the review queue holds two or more named quantities behind a
parameter -- `form: ehrhart | h-star`, `quantity: psi | H`, `form: generating
| signed`. Your job is to make it one table per quantity, or to say why this
one is right as it is.

Read <https://numberdb.org/skill> first. The rule is in it, under *one table or
several*, and so are the three cases where bundling is correct. This prompt is
the order of work and the ways the splitting itself has gone wrong.

## First, decide whether to split at all

The audit asks a question; it does not give a verdict. Three answers are good
ones, and a table with any of them should be left alone with a sentence saying
so:

* **Parts of one object.** The $abc$-triples hold $a$, $b$, $c$; an elliptic
  curve is $N$, $c_4$, $c_6$. A reader holding one part wants the others
  beside it.
* **One number in two conventions.** $E_1$ and $\operatorname{Ei}$, $\beta$
  and $e^\beta$, a quantity and its logarithm, the same volume in three
  normalisations. A reader holding either should land in the same place --
  which is possible only when each form determines the other, so **the test
  is invertibility**. A specialisation is not a convention: $C_n(q,1)$ does
  not give $C_n(q,t)$ back, and the Carlitz $q$-Catalan numbers are their own
  sequence with their own literature. A table and the thing you get by
  setting one of its variables to a number are two tables.

  Invertible is necessary and not sufficient. Two forms that do determine
  each other are still two tables when their **parameters differ** (the
  Krawtchouk polynomials by integer alphabet size against rational $p$), when
  **one is far more compact and can therefore be carried further** (the
  $h^*$-polynomial of a Birkhoff polytope writes 134 characters where the
  Ehrhart polynomial writes 381, and for the permutohedra it is the other way
  round), or when **the conversion costs more than the storage**.
* **A parameter that is an argument**, not a name: $\nu = 0, 1, 2$.

The question to ask: does the parameter name *what the number is of*, or
*which quantity is taken of it*? A different name in the literature, with its
own definition and its own references, is a different table.

**If you decide not to split, stop and say so.** Write what makes these one
thing into the definition, so that the next reader does not ask again, and
leave the table otherwise alone. That is a complete and successful run.

## The order of work

**1. Read the live document.** `GET /api/table?id=<TID>` and the rendered
page. Count the entries per label. You are about to move them, and the count
is the post-condition that tells you whether it worked.

**2. Name the tables.** Each new title must say its own quantity, findable by
somebody who knows only that name -- "Ehrhart polynomials of the Birkhoff
polytopes", not "the other half". The table that keeps the T-number keeps it:
a draft's address follows its title, so retitling it is safe and free, and
nobody has linked to a draft. Claim each new title by creating its draft; if a
title is refused because it exists, that table is already there and this split
has been done, wholly or in part.

**3. Move the entries, and check the count at every step.** The one way this
has destroyed a table: `publish(removing=True, overwrite=False)` on a
generator that yields only *some* of the entries removes everything it did not
send, because unsent and not-produced look the same from the server. T197 lost
1121 entries that way. So:

* rehearse with `preview()` and read what it says it will do,
* send the new table's entries first and verify the count there,
* only then remove them from the original, and verify its count,
* if either count is wrong, stop and say so rather than trying again.

**4. Drop the parameter that has become empty.** A table of one quantity must
not keep a parameter with one value: it is a column of the same word, and it
makes every entry's address carry a constant. Its `Display properties:
number-header` becomes that quantity's symbol -- `$\psi(x)$`, `$h^*_P(z)$` --
because a table of one thing can name it.

**5. Relate them.** Each table gets a `Similar tables` line naming the other
and *saying the relation in words*: what one is to the other, the identity
that connects them if there is one, and which of the two a reader holding a
number is likely to want. "See also" is not a relation. If one is derivable
from the other -- a logarithm, a binomial transform -- say the formula.

**6. Split the generator too.** The generator is the record of how the numbers
were made, and a generator that fills a table which no longer exists is a
lie. Either one directory per table, or one file with a class per table; both
are in the corpus. Every generator says in its docstring which table it fills
and how to run it, and the first line carries `numberdb.org/T<number>`.

**7. Audit both, and offer both.** `GET /api/table/<TID>/audit` for each --
the splitting finding should be gone from both, and a new one must not have
appeared. Then offer each for review. Do not publish.

## What must not happen

**No entry may be lost.** The entries in the new tables plus those left in the
original must add up to what you counted in step 1. Say the three numbers in
your report.

**No value may be recomputed by hand.** Move what is there. If a value needs
recomputing, the generator does it and you verify against the stored value
before sending.

**No cross-reference may be left dangling.** Other tables point at this one by
address. Searching the corpus for its slug and its T-number is part of the
work, and `audit_table --links` is what checks it afterwards.
