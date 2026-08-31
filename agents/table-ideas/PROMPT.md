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
2. **Ask what the family is a specialisation or a multiple of, and search for
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
3. **Read the open issues** at <https://github.com/numberdb/numberdb-data/issues>
   with label `table wanted`. Around 80 are open. If your idea is there, say so
   and cite the number rather than proposing it afresh.
4. **Check it can be a table at all.** Some things cannot: numberdb-data#121
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

## What you must not do

Do not create tables, do not write generators, do not publish anything. Do not
propose a family whose definition you would be guessing -- say what would settle
it instead.
