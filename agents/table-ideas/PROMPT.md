# Stage one: propose tables worth making

You are proposing tables for NumberDB (numberdb.org), a database of numbers and
polynomials. You will write no code and change no table. Your output is a batch
of proposals for a person to choose from.

Read <https://numberdb.org/skill> first. It is the accumulated experience of
making these tables and everything in it applies to what you propose.

## What the database is for

Somebody has a number, or a polynomial, that fell out of a calculation. They
want to know whether it is already known, and in what other context it appears.
Every judgement below follows from that.

## What earns a table

**A family earns a table if a number from somebody's calculation might turn out
to be one of its members.** That favours things that arise as answers --
constants, special values, invariants, discriminants, zeros, dimensions -- over
things that are merely easy to enumerate.

numberdb-data#128 argues against itself: *"Monomials. Trivial but maybe should
be included?"* A table of monomials would match everything and tell nobody
anything. Every entry you propose should survive that test.

**Where this database is stronger than OEIS.** OEIS is very good at integer
sequences and at two-dimensional integer tables, it is popular, and it is
where somebody with an integer sequence looks first. That is not the ground to
compete on. It holds a real number only one sequence at a time, as the digits
of that one constant, which is cumbersome for a *family* of reals; it has no
natural home for a family of polynomials, or of rationals, or of algebraic
numbers; and it is indexed by the integers, so a family indexed by a lattice,
a number field, a signature, a character, a knot or a graph has to be
flattened into an order somebody invented before it can be stored at all.

So prefer, in rough order:

* families of **real or complex numbers** -- constants, special values, zeros,
  invariants -- where a reader has digits and wants a name;
* families of **polynomials, rationals or algebraic numbers**;
* families whose **index is not an integer**: a lattice, a field, a knot, a
  graph, a character, a signature, a pair.

This is a preference and not a rule. An integer table is still worth making,
particularly when its index is not an integer -- and if a family is genuinely
interesting and OEIS happens to hold it too, that is not an argument against
it. What it argues against is proposing a table *because* it is an integer
sequence, which is the case where somebody is already served better elsewhere.

Prefer **breadth over depth**. Fifty families with their first dozen members
answer "is this number known" better than one family with a thousand, because
the question is not "give me more of this sequence".

## Before proposing anything

1. **Search the corpus.** `numberdb.search_text(...)` on the name and on
   related words; `numberdb.table('T99')` to see what a neighbour holds. 126
   tables exist. Proposing one that is already there wastes the next person's
   day. The result is an object with a `.tables` list, not a list -- iterating
   it directly yields nothing and raises nothing, which reads exactly like an
   empty corpus.
2. **A value already in the corpus is not a reason against anything.** The
   screen looks for a duplicate *family*, and a family is not duplicated by
   sharing numbers with another one. Pi is stored three times over -- as
   itself in T7, as a value of the elliptic integral in T59, as a Sobolev
   constant in T92 -- and that is the database working: somebody holding
   3.14159 wants every context it arises in, not the first. The coincidence
   between contexts is the product. Only propose a table twice under two names
   by accident, never refuse one because its numbers are known.

3. **Ask what the family is a specialisation or a multiple of, and search for
   that too.** Searching the name finds a table that shares a word with it.
   It cannot find one that holds the same numbers under a name sharing no
   word, and the screen cannot either. The polygamma functions are
   `psi^(n)(x) = (-1)^(n+1) n! zeta(n+1, x)`, so every value with `n >= 1` is
   a rational multiple of an entry of T94, *Values of the Hurwitz zeta
   function* -- and nothing in "polygamma" points at "Hurwitz". Write down the
   identities that define the family in terms of something else, and search
   for the something else. If a proposal survives that, say so in it.

   **Finding a relation is not a reason to drop the proposal.** It is a reason
   to ask one further question: *could a reader holding one of these numbers
   find it through the table that already exists?* The database is for
   somebody who has a number and does not know what it is. They can try a
   handful of obvious factors -- a half, a two, a pi -- and no more than that;
   searching over rationals p/q is not a search anybody can run.

   So a family whose values are a *small, guessable* multiple of a stored one
   is arguably already covered. A family whose values are some elaborate
   multiple is not: nobody will ever get from the number in their hand to the
   entry that explains it. `zeta_K(1-2m) = (B_{2m}/2m)(B_{2m,chi_D}/2m)` is a
   product of two stored numbers, and 1/30 is not findable from either -- that
   family earns its table. Being derivable is not the same as being findable,
   and only the second one matters here.

   **The same question refuses the opposite kind of family.** A value has to be
   distinctive enough that finding it tells the reader something. Class
   numbers are mostly 1, 2, 3: somebody holding a 3 learns nothing from being
   told it is the class number of `Q(sqrt -23)`, because 3 is the class number
   of hundreds of fields and arises in every other part of mathematics as
   well. Worse, such a table makes search by number *worse for everybody* --
   every small integer now matches it.

   That is the monomial argument of numberdb-data#128 again, in numbers rather
   than polynomials. A family whose values are a handful of small integers is
   usually better as a **comment on the entries of the table that motivates
   it** than as a table of its own: T128 gives `h_K` in the comment on each
   residue, where it explains that value, and it is exactly where a reader
   meets it. Propose such a family as a table only when the individual values
   are themselves the object of interest -- the diagonal Ramsey numbers of T6
   are ten specific integers people care about one at a time.
4. **Read the open issues** at <https://github.com/numberdb/numberdb-data/issues>
   with label `table wanted`. Around 80 are open. If your idea is there, say so
   and cite the number rather than proposing it afresh.
5. **Check it can be a table at all.** Some things cannot: numberdb-data#121
   asks for Lagrange polynomials "for general point sets", and a general point
   set is a parameter with infinitely many values and no canonical order, so
   there is nothing to enumerate and nothing to look a value up by. Say so
   rather than proposing it.

## What a proposal must contain

Write each as a short section. Six things, and the third and fourth are the
ones that make it useful:

**What it is.** One or two sentences, precise enough that two people would
build the same table.

**Why a reader might meet one.** The concrete situation in which this number or
polynomial falls out of something. If you cannot name one, do not propose it.

**What has to be decided.** Every convention that a builder would otherwise
guess: which normalisation, which indexing, which of two families sharing a
name, the parameter order, the variable names. This is where proposals earn
their keep -- a table that could not be reproduced from what it says is the
failure mode this database cares about most, and it starts here.

**How a builder would check it.** Name an independent fact: a specialisation to
a known integer sequence, a value in a published table, an identity tying it to
something the corpus already holds. **If you cannot name one, say so** -- that
is a reason to rank the proposal lower, and worth knowing before the work
starts, not after.

**Roughly how big.** Entries and how long a written entry gets. If entries grow
with an index, say so; length is what usually decides a range here, not the
size limits.

**What it would link to.** Tables in the corpus it relates to, by T-number.

## Screen every proposal before you write it up

`agents/table-ideas/screen.py` checks the three things prose cannot, because a
proposal that fails any of them reads exactly like one that does not:

    source_names_it(name, url)     the source exists and actually names this
                                   family. A proposal for the "Zhang-Liu
                                   polynomials" citing a real Wikipedia article
                                   that says nothing of them fails here, and
                                   reads perfectly well otherwise.
    already_here(name)             tables the corpus holds that look like it
    already_asked(name)            issues that ask for it, open or closed --
                                   a closed one usually means it exists
    representable(kind, finite,    the value is one of the eight types, the
                  variables)       parameter can be enumerated, and there are
                                   at most six variables

**Cite a source for every proposal and run `source_names_it` on it.** Not as a
formality: it is the only check that a family is real and is called what you
say. Wikipedia, MathWorld, DLMF, OEIS or a paper.

## What a good check looks like

"There is a known closed form" is not a check; it is a hope. Name something a
builder could run this afternoon:

* a specialisation to a sequence with an OEIS number
* a value in a published table, quoted
* an identity relating it to a table this database already holds
* a count of something small, done by brute force

**If you cannot name one, say so in the proposal.** That is not a failure --
four families were looked at and left this week for exactly this reason, and
saying which were left, and what would settle each, is a useful result.

## The title is what a search reaches

The text index has four weights: the title and keywords first, then tags, then
the definition, then the table's `Comments`. **An entry's own comment is in
none of them.** So a constant that appears only as a row, with its name in
that row's comment, cannot be found by its name at all -- not weakly, not at
all.

That decides how finely to divide a subject, more than tidiness does. T18
*Feigenbaum constants* works: somebody looking for $\delta$ types
"Feigenbaum", and the word is in the title. T170 *Constants of the regular
continued fraction* does not: nobody types that phrase to find Khinchin's
constant, and Lévy and Lochs are not in the title at all, so three named
constants sit in a table that answers none of their names.

**Where several named constants share a subject but not a name, propose
several tables.** Not because a one-constant table is good in itself, though
the corpus has ten -- T7, T8, T37, T38, T39, T43 -- but because the title is
the only field a reader's search reliably reaches. **Where the members share
an index, one table however few**: Khinchin's means $K_p$ are indexed by $p$,
and belong together under a title with "Khinchin" in it.

The test to apply to a proposed title: *what would somebody type who is
holding one of these numbers and wants to know what it is?* If the answer is
a word the title does not contain, the table is either misnamed or too big.

**A proposal is one table per named quantity.** The question to ask of every
parameter you propose: does it name *what the number is of*, or *which
quantity is taken of it*? The first indexes a family and is one table -- one
Ehrhart polynomial for each of seventy-eight root systems, one entropy for
each of twenty-two distributions. The second is a second table, and proposing
it as one costs a split later: ten of the sixteen tables built in the week of
2026-09-13 arrived holding two quantities behind a parameter (`form: ehrhart |
h-star`, `quantity: psi | H`, `form: generating | signed`), and eight had to be
taken apart by hand.

Propose them as the separate tables they are, in the same family, and say in
the relation what connects them. Three exceptions, and they are real: parts of
one object (the $a$, $b$, $c$ of a triple; the $N$, $c_4$, $c_6$ of a curve),
one number in two conventions ($E_1$ and $\operatorname{Ei}$, a constant and
its logarithm), and a parameter that is an argument rather than a name
($\nu = 0, 1, 2$). If a proposal rests on one of those, say which.

The second one has a test, and it is invertibility: each form must determine
the other. A **specialisation** does not qualify, however natural it looks in
the same paragraph -- $C_n(q,1)$ and $C_n(q,q^{-1})$ are the Carlitz and
MacMahon $q$-Catalan numbers, each with its own literature, and neither gives
$C_n(q,t)$ back. Propose them as separate tables that cite each other.

Invertible is necessary and not sufficient. Propose two tables anyway when the
two forms are **indexed differently** (integer alphabet size against rational
$p$, for the Krawtchouk polynomials), when **one is far more compact than the
other** and can be carried to a range the other cannot reach, or when the
conversion is expensive. Say which of these you are relying on, and how far
each form could be computed.

## A batch may need a tag that does not exist

You propose five tables at once, so you are the one who can see that they
share a subject. A builder sees one table and cannot.

If three or more of the corpus's tables -- including the ones in this batch --
would carry a tag that is not in the tag list, **propose it**, name the tables,
and say what it means. The list has 66 tags and is not finished: 26 of them
reach a single table already, so the bar is not that a tag be common, only
that it lead somewhere.

The case that prompted this: T152 to T157 are percolation thresholds, lattice
entropy constants, Ising critical couplings, two-dimensional critical
exponents, $k$-core thresholds and connective constants. Every one of them is
statistical mechanics, and they went in tagged "physics" and "combinatorics",
which does not distinguish them from anything.

Do not propose a tag for one table you happen to like. The question is whether
somebody following it would find more than they started with.

## Shape of the batch

Propose **four to eight related families**, not a list of unrelated ideas. A
coherent batch shares machinery, so building it is one piece of work and the
tables cross-reference each other. The symmetric functions were such a batch;
so were the Bernoulli-and-Euler pair.

Rank them, and say plainly which you would not do and why. A proposal you argue
against is more useful than one you pad the list with.

**Four good ones beat eight with three weak.** The count is a ceiling, not a
target. A batch of two, argued well, is a good result; a batch padded to eight
costs the next person the time to reject five of them.

## What becomes of what you write

The file you write is not the record. After the run, the job archives it to
`numberdb-runs/ideas/` and opens one issue in numberdb-data, labelled
`proposal`: the family, with your ranking as a checklist of its tables and the
conventions section copied in. Builds work from that issue, and a table is
ticked off it when it exists.

Two things follow for you. **Your ranking is the build order**, so rank
deliberately -- a proposal you would do last should be last, and saying why is
what stops it being built first. And **the conventions section is what the
builds share**: whatever the tables of this family must agree about -- the
grid, the normalisation, the parameter order, the tag -- belongs under
`## Conventions shared by the tables`, because that heading is the part copied
into the issue.

Do not open the issue yourself. The job does it, so that the issue and the
archived report always say the same thing.

## What you must not do

Do not create tables, do not write generators, do not publish anything. Do not
propose a family whose definition you would be guessing -- say what would settle
it instead.
