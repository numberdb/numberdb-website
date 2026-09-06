# When two tables hold the same number

Written after three lattice tables were built in one campaign and one of them
turned out to be a subset of another. The complaint was not that the tables
overlap -- they should -- but that search would answer with the same number
three times over.

## What the overlap is

Measured on the corpus, comparing stored text rather than parsed values, so
these are numbers that would collide in search:

| | entries | shares with |
|---|---|---|
| T136 Gauss-Kronrod quadrature | 816 | **209** with T132 Gauss-Legendre |
| T148 densest known packings | 96 | **45** with T147 classical lattices |
| T149 Hermite's constants | 9 | **9** with T147 |
| T150 covering radii | 234 | 24 with T147 |

## The distinction that does not work

The obvious rule is to fold values that are equal, and it is wrong. Consider
the two largest cases.

T136 stores, for each Kronrod rule, the nodes and weights of the Gauss rule
embedded in it. Those are the Gauss-Legendre nodes: the same roots of the same
Legendre polynomial, computed the same way. One table repeats another.

T149 stores Hermite's constant $\gamma_n$, and nine of its nine values equal a
Hermite number in T147 -- $\gamma_8 = \gamma(E_8) = 2$ -- because Blichfeldt
proved the supremum over all lattices in dimension 8 is attained at $E_8$. Two
differently defined quantities meet, and the meeting is a theorem. That is the
most interesting thing this database can say about a number, and folding it
away would destroy exactly what the corpus exists to record.

Both are exact equality between two tables. Nothing in the values tells them
apart.

## The criterion that does not work either

The first attempt was "does the equality need a theorem?" -- fold when
unfolding a definition suffices, keep both when a theorem is required. It
fails on its own flagship example. $\gamma_8 = \gamma(E_8)$ needs a theorem to
say *which lattice*, and once that is known the number is an ordinary
invariant of an ordinary lattice, computed by the same formula as T147's. It
is both things at once.

T148 has the same shape: "the densest known lattice in dimension 24"
identifies an object before evaluating an invariant on it, and the only
difference from T149 is that its selection rests on a survey claim rather than
a proof. That is a difference in the evidence for the selection, not in the
construction.

Two further repairs were tried and dropped. Provenance -- did this generator
compute the value or transcribe it? -- classifies a table by how somebody
happened to write its generator: T149's values were transcribed from theorem
statements, but an author who built $E_8$ and evaluated $\mu/(\det L)^{1/8}$
would get the opposite answer for the same table. A declared map from one
table's parameters to another's fails too, because $\Gamma(n) = (n-1)!$ has
one.

The conclusion is that there is no per-entry predicate here, and the design
should stop needing one.

## What is done instead

The claim is made once per table, by a person, in `Data properties`:

    Data properties:
      repeats: HREF{Nodes_and_weights_of_Gauss_Legendre_quadrature}

meaning: *where this table's values coincide with that table's, that table
states them first.* At the granularity of two tables the question is
answerable by reading two definitions -- T136 obviously repeats T132, T149
obviously does not repeat T147 -- and the hard cases disappear because nobody
has to rule on 248 entries one at a time.

`equals`, on an entry, keeps the meaning it already had in 608 entries across
39 tables: these two values are provably the same, whether that takes a
theorem or not. It is not narrowed and not migrated.

## What search does with it

`fold_repeats` in `numberdb_app/search.py`. A row is dropped when its
table repeats another table that is **also among the answers** and holds the
**same stored text**. The folded table is attached to the surviving row as
`also_in` and named on the page, so a fold decides what leads rather than what
exists.

Two guards follow from the shape rather than from taste. Only equal values
fold, because a result set answers a query and not a single number; and a copy
whose original is not among the answers stands on its own, because folding may
never remove the only answer.

## Why the relation is kept one hop deep

`Table.repeats` is a foreign key to another table, and `_sync_repeats`
refuses a declaration that would make a chain: a table that some other table
repeats may not itself repeat a third.

That is what makes cycles impossible rather than merely rare. Every table in a
cycle would have to both repeat and be repeated, so the depth rule excludes
them; the graph is a disjoint union of stars. It also means a fold resolves in
one lookup, with no recursive query and no visited-set.

The read side does not trust the invariant anyway. Two tables edited at the
same moment can each validate against a snapshot in which the other has no
declaration, and a cycle can be written straight into the database by hand.
So resolution follows at most one hop and stops: a corrupt graph degrades to
"nothing folds", which is the right failure for a presentation feature.

Where the depth rule bites -- a third table that genuinely repeats a copy --
the answer is to point at the original, and the refusal should say which table
that is.

## What this does not address

A search for `1` still meets 31 Gauss-Lobatto weights. That is a question
about trivial values, not about identity, and `one_per_table` plus grouping is
already the answer: one row per table, headed by the table the number is
named after.
