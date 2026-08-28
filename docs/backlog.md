# Backlog

Ordered roughly by value over cost. Items carry enough detail to be picked up
cold; design docs live in `docs/design/`.

**Adding an item.** Write a heading and a paragraph saying what is wrong and how
you would know it was fixed. Rough is fine -- an item nobody can act on yet is
still better than one nobody wrote down. Move a finished item to *Done* at the
bottom with a one-line note rather than deleting it, so it does not get
proposed again.

## Backups that survive losing the server

The one item where waiting risks something that cannot be undone.

Today there is exactly one automatic copy: a systemd user timer on the laptop
(`scripts/systemd/`) pulls a verified dump from production nightly. That covers
the server dying. It does not cover the laptop dying, being stolen, or being
the thing that is away for a month.

Wanted: the server also pushes a nightly copy to an object store, encrypted
before it leaves, with credentials that **can write but cannot delete**
(Backblaze B2 with Object Lock, or rsync.net). That is what makes the copy
survive an attacker who is already root on the server, which plain off-site
storage does not.

Encrypt with `age` to a public key, not with a passphrase, so the server can
write backups without holding anything that can read them back. Plain encrypted
files rather than restic or borg: at 29 MB a night, deduplication buys little,
and a restore that is one pipe with no tool-version risk is worth a great deal
at the moment it is needed.

Blocked on credentials that cannot be created from here: a bucket with Object
Lock on, an application key **without `deleteFiles`**, and an `age` keypair in
Bitwarden. Once those exist: `scripts/backup-push.sh`, a systemd timer on the
server, `restore.sh --from-remote`, and a weekly `make restore_check`.

## What is left of saying how well each number is known

Most of it is done -- see *Done* at the bottom, and `docs/design/rigour.md`.
Four things were designed and not built, and one question is nobody's to answer
but Benjamin's.

**The measured constants.** Four tables hold numbers that were never computed:
the fine-structure constant, the proton-to-electron mass ratio, the mass ratios
and the magnetic moment ratios. None of the five levels fits, because all five
describe a calculation. Their `reliability` prose already says the right thing
-- "chosen to contain all measurements up to five measurement uncertainties" --
so the choice is whether to add a `measured` level or leave them unlabelled.
Leaving them is defensible; the audit did.

**Per-entry levels and `proven_digits`.** The level lives on the table today.
Polya's random walk constants is the case that needs more: it is proven for
d <= 3 and has no error bounds beyond, which its prose says and no field can.
The same tables want `proven_digits` -- a number known rigorously to twenty
digits and heuristically to a hundred should say so rather than pick one.

**Agreement-checking in the package.** T55 does it by hand, in eight lines that
every heuristic generator will otherwise copy: compute at two precisions and
hand over `field(low).union(field(high))`. Lifting it into the package is the
difference between one implementation and eleven.

**`weakening`.** A run cannot yet be stopped from replacing a proven value with
a heuristic one. Nothing can weaken anything until per-entry levels exist, so
this waits on them.

**The fourteen tables with no script.** Pi, e, the golden ratio, the zeta
zeros: their numbers came from somewhere, and nothing here records where. That
is a provenance question rather than a rigour one, and it overlaps with the
*bundle* item below.

## Recompute the rank 1 L-values with the bound Sage already provides

Of the fourteen `assumed-bound` tables, the L-value ones have a documented
error bound and nobody used it. `E.lseries().deriv_at1()` returns the value
*and* "a bound on the error in the approximation" -- a series-truncation bound
from Cohen's algorithm. Measured on 37a: a thousand terms gives a bound of
2e-118, so **118 proven digits in under a tenth of a second**.

The tables were built with `taylor_series` instead, which documents a precision
in bits and no accuracy, and then widened by four ulps chosen by hand. Using
the bounded method turns the special value of the L-function of rank 1 curves
from `assumed-bound` into `proven`, at no cost worth measuring.

It covers rank 0 and rank 1 only -- `at1` is `L(E,1)`, `deriv_at1` is `L'(E,1)`
assuming the first vanishes. The rank 2 and rank 3 tables have no such method.

**Done for the rest of that group, 2026-08-15**, by reading the implementations
rather than the docstrings. Every one now says what is and is not known about
it, in its own words:

  * *Regulators (T64-66).* `E.regulator(proof=True)` proves the Mordell-Weil
    basis, so the quantity is right; the numerics are not bounded. Heights come
    from PARI's `ellheight`, whose documentation gives the normalisation and no
    accuracy. Sage's own implementation truncates Silverman's series at a count
    derived from his published bound but tracks no rounding, and its working
    precision is a guard arrived at by patching failures ("100 extra bits is
    not enough when the discriminant is ~1e-92"). The matrix is ordinary
    floating point with a cancelling subtraction off the diagonal, then a
    determinant. Measured: recomputing at double precision agrees to ~204
    digits.

  * *Real periods (T72-74) and L-values (T70-71).* These were mislabelled
    *upward*. They compute at two precisions and assert agreement, which is an
    agreement check, not an assumed bound.

**Done 2026-08-17: the real periods are proven.** All 3,023 entries of T72,
T73 and T74 were recomputed as `pi / agm` in ball arithmetic and agree, at
about 395 accurate bits out of 400. No curve list was needed after all: the
entries carry N, c4 and c6, and the c-invariants determine the curve, so each
entry rebuilds its own and its conductor is checked against the N it claims.
Both branches of Sage's own implementation are followed -- `pi/agm(a,b)` for
positive discriminant, `pi/agm(|a|, |Re a|)` for negative.

See `docs/design/rigour.md`.

## The arb sweep, and what it does not reach

`manage.py sweep_arb` recomputes stored values in ball arithmetic and reports
anything the site's own parsers would read as a different number. It runs as
`numberdb-sweep.service` on the server, checkpointed per entry so a restart
resumes rather than begins.

First run, 2026-08-16: **5,205 entries recomputed, none wrong** -- Gamma and
zeta at rationals, the d-sphere, the AGM, roots of unity, cos(pi x). It took
six seconds, not the hours budgeted for it: arb is fast and these are cheap
functions. The expense is in what is *not* covered, and the registry is meant
to grow.

**Fourth run, 2026-08-17: 23,260 entries across 28 tables, none wrong.** Added
the Hurwitz zeta values, the zeta zeros -- against arb's certified enclosures,
now permanently rather than as a one-off check -- and the eight tables of Airy
and Bessel zeros and extrema, 8,199 values, by a different kind of check.

Those tables hold the *location* of a zero, so nothing is recomputed and
compared. The function is evaluated in ball arithmetic at both ends of the
interval the written digits denote, and opposite strict signs put a zero
between them by the intermediate value theorem. No root-finder, no tolerance.
It does not establish the index -- that this is the nth zero and not a
neighbour -- which needs a count of the zeros below, and arb's counting is not
exposed in Sage. The tables now say exactly that.

**Third run, 2026-08-17: 14,030 entries across 18 tables, none wrong.** The
Platonic solids, the Sobolev constants, the p-adic agm once its convention was
established, and the Taylor coefficients of the completed zeta -- assembled
from `zetaderiv` and polygamma, since Sage has no zeta of a power series over a
ball field. That last one needs 2600 bits to work at all: at s0 = 1/2 the
log Gamma series has radius 1/2, so its coefficients reach 1e75 by k = 250
while the answer they combine to give is 1.5e-471, and the 546 orders of
magnitude in between are pure cancellation. At 1400 bits the k = 250
coefficient has no correct digits.

**Second run, 2026-08-16: 10,217 entries, none wrong.** The p-adic engine went
in -- Teichmueller representatives, the p-adic logarithm, exponential, Gamma
and the Artin-Hasse exponential, each written from its definition rather than
by calling the Sage function the original script called, so it can notice a
wrong function and not merely a wrong transcription. T17 joined on the real
side.

Three of the p-adic definitions were wrong before they were right, all at
p = 2, and the tables were correct every time: the Teichmueller limit k^(p^n)
tends to 1 for every k at p = 2, because squaring destroys the sign that
carries the answer; the p-adic exponential does not converge at v(x) = 1, which
is the whole reason the Artin-Hasse exponential exists, so E_p has to be built
as a formal series with p-integral coefficients; and the logarithm needed the
Iwasawa branch to reach 702 of T45's 856 entries.

What it cannot reach yet, roughly in order of what it would take:

  * **Needs mathematics.** T50, the Kubota-Leopoldt zeta function: Sage has no
    implementation, and the table's own definition pins the value only at
    negative integers k = 1 mod (p-1), while its entries include s = -50 at
    p = 2. Everything else follows by continuity, so checking it means Kummer's
    congruences.

  * **A different check.** The fifteen tables with generators are better
    served by `verify`, which recomputes from the file attached to the table.

  * **Nobody knows how, yet.** Stieltjes constants (T16, T31, T34, T36), prime
    zeta (T24), multiple zeta values (T53, T54), and everything resting on
    elliptic curve L-functions and regulators (T64-T66, T70-T74). These are
    the tables whose labels say least, and they are exactly the ones no
    independent implementation can currently check.

## Search by number was answering for a third of the corpus

Fixed 2026-08-17, and worth keeping written down because nothing failed
loudly. Searching for pi did not find the table called Pi.

Unreviewed values are deliberately held out of search by number: a reader
looking at a table can see an entry is marked unreviewed and weigh it, and
somebody typing digits cannot. What decides is `changed_params`, the difference
between a table's reviewed revision and its head -- and it compared
representations rather than values. The corpus holds the same entry in several
shapes, and normalising a tree moves annotations about:

    Numbers: ['3.14159...']                             # as imported
    Numbers: [{'params': {}, 'number': '3.14159...'}]   # as rewritten

    param-latex comes off the entry; url and both signs move onto it
    a lone value gets wrapped: number: ['-188.5']
    a bare list is ambiguous -- several entries, or one entry of several values

Every one of those read as a changed entry. A run of `set_rigour`, which
touches nothing but a table's Data properties, therefore declared the whole
corpus unreviewed: 71% of stored reals and *every* complex, p-adic and
polynomial value silently left search by number. 55,432 values, of which 41,582
were held back.

The comparison is now over the sequence of values an entry states, with
annotations compared only where both sides carry them, and it is down to 2
rows -- T32's corrected `phi_inv` and its new `phi_conj`, which genuinely
changed and are genuinely waiting for review. Nine tests hold the line between
a shape that moved and a digit that changed.

Two things to take from it. Metadata edits must not be able to invalidate a
review of digits, which is now true. And the site's own headline claim -- give
us a number, we will tell you whether it is known -- had no test that ran
against real data; it was found by checking the README's example by hand while
sweeping the documentation.

## Two tables that could not be reproduced from what they said

Found by the sweep, and neither was a wrong digit: both were a table that did
not say enough for a reader to get its numbers back. Both fixed 2026-08-17.

**T52, the p-adic arithmetic-geometric mean.** Its definition gave the
iteration `a_{n+1} = (a_n+g_n)/2, g_{n+1} = sqrt(a_n g_n)` and never said
*which* square root. Over Q_p that is not a detail: both roots are there and
they lead to different limits -- reading it the natural way gives a different
number for every entry at every odd prime, which is what happened.

The rule was established by asking PARI rather than guessing at it. The agm is
unchanged by one step, so `agm(a,b) == agm((a+b)/2, r)` holds for the root PARI
took and fails for the other; at every prime tried it takes the root nearer the
**new** arithmetic mean. With that rule all 990 entries reproduce, p = 2
included. The definition now says so, and the table carries the step-invariance
as a formula, since that identity is what makes the choice checkable at all.

**T45's parameter constraint was wrong; fixed 2026-08-16.** It read
`k = 1 mod p`, and 702 of its 856 entries were outside that -- p = 3 with
k = -49 among them. The values were right: what the table holds is every
integer coprime to p, in every residue class, and all 856 verify. The
constraint now reads `p does not divide k`, and the table states the extension
that makes those entries exist -- `log_p(k) = log_p(k^(p-1))/(p-1)`, since the
series converges only in the residue class of 1.

## Three tables that are still guesses

The audit is complete -- 107 of 107 tables state a level -- and after the
2026-08-15 pass these are the computed tables that remain `heuristic`, with
what each would take:

  * **T24, prime zeta.** `mpmath.primezeta`, which documents no accuracy.
    Provable: `P(s) = sum_n mu(n)/n log zeta(ns)` with arb's rigorous zeta and
    an explicit tail bound (for `ns >= 2`, `|log zeta(ns)| < 2^(1-ns)`, so the
    tail past N is geometric). The care is in the terms with `ns <= 1`, where
    `log zeta` goes complex -- which is why the table's type is `C` -- and in
    the singularities at `s = 1/k` the table already excludes.

  * **T53, T54, multiple zeta values.** Sage gets these from PARI's
    `zetamult`/`zetamultall` in `RealField`; PARI documents no accuracy, as
    with `ellheight`. There is no ball implementation of general MZVs. The
    cheap honest step is an agreement check at two precisions, which is what
    the stored digits actually rest on and would move them one level. Proving
    them means Euler-Maclaurin on the nested sum with a rigorous tail.

  * The transcribed tables -- T4 (LMFDB), T18 (Feigenbaum), T38, T84 (LMFDB
    Maass forms), and the tail of T19 -- are a different problem: the digits
    were never computed here, so no amount of care in this repository can
    raise them. Either recompute or leave them saying what they are.

`numberdb.sage.agreeing` handles the real case; T24 would need a complex
counterpart, since it is the only one of these whose values are not real.

## A bundle does not always reproduce its table

A table's bundle carries the head revision's files. If half the entries were
produced by an earlier `generate.py` and the file has since changed, those
entries cannot be reproduced from the bundle -- and nothing in the bundle says
so, which is the worse half of the problem.

Wanted: include every file version that some surviving entry was produced
under, plus a manifest mapping entries to the version that made them. The
revisions are content-addressed already, so the versions are all still there;
what is missing is the entry-to-version link and the selection at bundle time.

Would be fixed when a bundle of a table whose generator changed mid-way
contains both generators and says which entries came from which.

## Move every generator script onto the numberdb package

0.1.0 is on PyPI, the site tells people to install it, and nothing has yet been
published *through* it. The goal is not a sample of two: **every** script that
produced entries in the corpus should be converted into a `Generator`
subclass, as far as that is possible, so that a table's stored source is
something that can be re-run to reproduce it rather than a historical artefact
in a language the site no longer speaks.

Start with a handful by hand -- that is the first real test of the design, and
the only way the awkward parts will surface -- then convert the rest in bulk,
which is the sort of mechanical rewriting an agent does well once there are
worked examples to copy.

Expect a residue that cannot be converted, and record it rather than quietly
skipping it: scripts whose dependencies are gone, that took days on hardware
nobody has, or that were never checked in at all. A list of "these tables have
no runnable generator, and here is why" is itself worth having, and it is what
the *bundle* item above needs in order to be honest.

**Where to start is now known rather than guessed.** The rigour audit
(`docs/rigour-audit.tsv`) names the eleven tables whose digits are least
supported -- the ones still labelled `heuristic` -- and most of them are the
same shape as T55: `mpmath.mp.somethingzero(n)` wrapped in an interval field.
Airy Bi, the four Bessel families and the local extrema can be converted from
T55's generator almost mechanically, and each conversion moves a table from
"believed because fifty extra digits were computed" to "agreement-checked".
That is a better order than working down the table list.

It is also the prerequisite for the item below: an agent asked to fill a "table
wanted" issue needs worked examples to copy, and those do not exist yet.

## Tell the numberdb-data repository it is no longer where editing happens

The `numberdb-data` repository is still, to anyone arriving at it, the way to
contribute: it is where the tables visibly live, it has an issue tracker people
are using, and nothing on it says otherwise. Editing moved onto the site, and
the repository has not been told.

A notice at the **very top** of its README -- above everything, before the
first heading anyone reads past -- saying that tables are edited on
numberdb.org now, and linking to the help page and the `numberdb` package
documentation that explain how. Not a paragraph buried in a section: someone
who opens the repository to file a pull request should learn it before they
start writing one.

Worth doing soon and cheaply, because the cost of leaving it is paid by other
people: work done in the wrong place, which is the most discouraging kind to
have to redo. Coordinate with the *bundle* and *generator* items above, which
decide what the repository is still for once it is no longer the editing
surface -- an archive, a mirror, or something to retire.

## Audit the help, the docs and the READMEs against what the site does

Several places are known to be out of date, and documentation that describes a
site other than this one costs more than none: it is believed. The site changed
a great deal in a short time -- editing moved on-site, keys became
self-service, the package landed, a table's source became something you can
re-run -- and the prose did not always follow.

Everything that describes the system, read against the system: `/help`,
`/about`, `/api/docs`, the root `README.md`, `clients/python/README.md`, the
package docstrings that `make docs` renders, `AGENTS.md`, and `docs/design/`.
Where they disagree, the code wins and the prose gets fixed.

Worth doing as one deliberate pass rather than opportunistically, since the
value is in knowing that a reader can trust the whole of it.

## Ingest the data repo's issue page, and pages like it

Numbers and polynomials submitted as GitHub issues on the data repo should be
brought in automatically, driven by Codex or Claude, and further pages added
the same semi-automatic way.

Now unblocked in principle -- the package and the write API are the interface
such an agent would use -- but wants the worked examples above first.

## A postal address for the legal notice

`/impressum` gives a name and an email address and no address, deliberately:
a private address published there is published permanently and to everyone.
German law (&sect; 5 DDG) reads "gesch&auml;ftsm&auml;&szlig;ig" broadly enough
that this may not be sufficient, and the fix is a decision rather than a
change -- a department, a PO box, or his own.

Left open because it is Benjamin's to make, not because it is unclear what to
write.

## Follow a discussion without visiting it

Tables now have discussions, and nothing tells anyone that a message was
posted. The author of a table learns that somebody questioned one of their
numbers by happening to look, which for most tables means never.

Wanted, roughly in this order: a list of recent messages across the whole site,
so the board can moderate without opening tables one at a time; a way to watch
a table; and only then email, which is the expensive part and the one that
needs an unsubscribe link, a bounce policy and a rate at which it is not spam.

The schema already allows a thread on a **tag** as well as a table, which is
unused. That would be the place for a discussion spanning many tables, and it
costs one more view.

Not urgent while the number of messages is zero, and genuinely urgent the week
it is not: an unwatched discussion is worse than none, because it looks like a
place where somebody is listening.

## Move the web app to passagemath

The web image is 4.9 GB of Sage on a 961 MB VM already at ~700 MB used with
swap nearly full. Measured on passagemath 10.8.7, the replacement is **2.0 GB**
of site-packages -- worth doing, but less than half, not a tenth.

Feasible: every number type the app uses works.

    passagemath-flint      ZZ QQ RR RIF RBF CBF PolynomialRing infinity Integer
    passagemath-pari       Qp
    passagemath-symbolics  SR I latex factor continued_fraction ceil log
    passagemath-repl       sage.repl.preparse (used by utils/preparse.py)

Verified arithmetic under that set: interval endpoints, p-adic lifts, complex
boxes, ball radii and exact rationals all behave.

The work is import rewriting, not redesign. **passagemath has no `sage.all` or
`sage.rings.all`** -- those monolithic namespaces come from sagemath-standard,
and every module here imports through them:

    from sage.all import infinity, ceil, log, I      ->  ModuleNotFoundError
    from sage.rings.all import ZZ, QQ, RIF, CIF      ->  ModuleNotFoundError

Each symbol names its own module instead. Verified working under passagemath:

    ZZ   sage.rings.integer_ring        RBF  sage.rings.real_arb
    QQ   sage.rings.rational_field      CBF  sage.rings.complex_arb
    RIF  sage.rings.real_mpfi           CIF  sage.rings.cif
    RR   sage.rings.real_mpfr           CC   sage.rings.cc
    Qp   sage.rings.padics.factory      PolynomialRing
                                             sage.rings.polynomial.polynomial_ring_constructor

Note `CIF` and `CC` live in their own small modules holding the default
instances -- `sage.rings.complex_interval_field` and `sage.rings.complex_mpfr`
hold the *constructors* (`ComplexIntervalField`, `ComplexField`), not the
instances. There is no circular-import problem and no required import order.

The one Sage feature that did not work under passagemath is **`SymmetricGroup`**,
which needs libgap: `from sage.libs.gap.libgap import libgap` failed in two
trials, once alongside the other distributions and once with `passagemath-gap`
alone. That is not proof that no combination works -- a companion distribution
may be missing -- but it does not matter, for the reason below. It is used in
exactly one place -- `polynomial_modulo_variable_names`
in `utils/utils.py`, called from `numberdb_app/models.py` to build a
polynomial's search key, which canonicalises it under renaming of variables.

It does not need solving, because it is already solved:
`utils/numbers/polynomial.py` has `canonical_under_renaming()`, which does the
same job with `itertools.permutations` and no Sage. It parses the whole stored
corpus without error. Switching to it removes the last group-theory dependency
entirely, so **passagemath-gap is not needed**.

The catch: the two produce different key *formats* -- Sage yields the string
`1,15360*x^7-16128*x^5+...`, the Python version a nested tuple -- so they are
not drop-in interchangeable. `Polynomial.number_string` and
`number_string_hash` are stored and searched on, so the switch means rebuilding
those keys for the 1038 stored polynomials. Bounded, and it can be done before
the passagemath move rather than during it.

Files importing Sage, in the order they matter:
`numberdb_app/models.py`, `views.py`, `api.py`, `utils/utils.py`,
`utils/preparse.py`, `utils/my_timer.py`, `utils/number_json.py`,
`utils/numbers/sage_adapter.py`, `data_pipeline/build*.py`.

The evaluator sandbox keeps full Sage either way -- it runs arbitrary user
expressions, which is exactly what the trimmed distributions cannot promise.

## Refine matches against exact_text

Search filters on the float projection and returns the survivors directly. The
design was filter-and-refine -- the index gives a sound over-approximation,
then the exact value settles it -- but the refine step was never written, so
anything the projection cannot represent produces false positives.

The clearest case is underflow, the mirror of the saturation handled by
unbounded ranges. Several stored values are tiny enough to land in the
subnormal doubles:

    Volume of the d-dimensional unit ball   float range [5e-324, 1e-323]
                                            exact_text  0.0000000000...

so the projection keeps about one bit while the stored value is known to full
precision. Those rows match anything in the subnormal range.

Refining in Python against `exact_text` -- which every row now has -- would
drop them, and is cheap: it runs on at most a hundred survivors.

## The two search entry points disagree about precision

The same text means different things to `/suggestions` and `/api/search`:

    3.14159265358979
      search bar   parse_real_interval -> blurred width 3.86e-14 -> finds pi
      /api/search  RIF("...")          -> blurred width 4e-15    -> finds nothing

Both are defensible -- the search bar reads a typed decimal as uncertain in its
last digit, advanced search reads an expression at face value, and pi really
does differ from that decimal at the fifteenth digit. But a user who tries the
same string in both places gets results in one and silence in the other, with
nothing explaining why. At minimum advanced search should say that it searched
and found nothing at the precision given.

## Record what a run cost

`publish()` could report the wall and CPU time a table's generation took, which
is the number a reader wants when deciding whether to reproduce it. Postponed
deliberately: the measurement is easy, deciding what it *means* across machines
is not.

## Cleanups

- Delete `utils/number_decode.py`. Obsolete since the exact layer landed, and
  the source of the `240/480 cases (b 0/120, r 0/120)` line printed after every
  test run, which reads like failures.
- Rename `str_short`. It is the uniform search-result view, not an abbreviation;
  `utils/numbers/display.uniform_real_text` is the implementation.

## Deadline for edits in discussion + user profile pages

In the discussions of a table, one can edit messages. There should be a reasonable deadline for how long this is possible, say 10 min? What is standard in these chats?
Also the user/author of the message should be clickable, pointing to the public profile of the user.
This requires also a public profile of the user. 
The public profile should be perhaps similar to the ones on wikipedia, content-wise. Perhaps with a history of all edits, or the number of edits, entries, the last discussion items, not sure how much should be openly available, or whether the user can choose to show them on their profile.

## Deferred, with the trigger to revisit

- **A GiST box index for complex search.** 1849 rows, 0.2 ms sequential; worth
  doing if that table grows by orders of magnitude.
- **The Z-order searchstring is dead, and crashes at zero.** `NumberComplex`
  still builds `number_searchstring` (`models.py`), but nothing searches it any
  more -- complex search matches by box overlap, and the only remaining reader
  is `tests/golden/generate_golden.py`. It also cannot represent zero:

      exponent = t.abs().log(10).upper().ceil()
      ValueError: Calling ceil() on infinity or NaN

  so constructing a complex value at 0 raises. No such value is in the corpus,
  which is why this has never been hit. Dropping the field removes both the
  dead weight and the crash, but needs a migration and a golden-file update, so
  it is not a drive-by.

- **Degenerate p-adic balls.** `_coarser_ball_strings` does not emit the ball
  around zero, reached when precision drops to or below the valuation, which is
  written `"p,0,000..."` rather than as a prefix. Such matches are too coarse to
  be useful, but the omission is deliberate rather than proven unreachable.

## Done

- **Real users, editing content on the site.** Accounts, editing of settings,
  text, numbers and source through the site, content-addressed revisions with
  an author and a required message, and a trust threshold before an edit
  publishes. The data is no longer a mirror of the `numberdb-data` repo:
  production is the source of truth, and a rebuild from the repo would now
  destroy site content. What this item left unfinished is *Deletion, privacy,
  and what happens to an account*, above.
- **Issue API keys from the website.** `/profile/keys`: create, label, copy,
  optional expiry, revoke, with the token shown once and stored only as a hash.
- **The `numberdb` client package.** Published to PyPI (0.1.0), with a
  `Generator` class as the single path for submitting a table.
- **Privacy, deletion, and the legal pages.** `/privacy` and `/impressum`,
  reachable from a footer on every page; no third party is contacted by any
  page; reading sets no cookie, which is what makes having no cookie banner
  correct; server logs mask the address and rotate; the API log records the
  client version and never a token. An account can be exported and deleted,
  keeping its contributions under a placeholder name. What is left of this
  item is the postal address, above.
- **Saying how well each number is known.** Five levels, closed and enforced:
  a generator claiming `proven` must return an exact value or an interval of
  nonzero width, so the point-interval trap is refused rather than published.
  The level is sent once per run and shown on the table. **All 107 tables are
  labelled** as of 2026-08-15, audited in `docs/rigour-audit.tsv` -- 33 exact,
  39 proven, 15 agreement-checked, 7 assumed-bound, 9 heuristic, 4 measured.
  The last fifteen had no generating script, so they were checked here: pi, e,
  the golden ratio and exp(pi*sqrt(163)) against ball arithmetic, and all 1000
  zeta zeros against arb's certified enclosures, none disagreeing. Five tables
  moved from `heuristic` to `proven` by being recomputed in arb ball
  arithmetic (T25, T26, T59, T40, T93), every entry matching what was stored.
  What is left is above.
- **Discussions on tables.** A thread per table, linked beside its title.
  Anyone reads, anyone who may edit posts, the board can hide a message
  (kept, not deleted). The models had been designed and migrated long before
  and were sitting unused; what was missing was the pages.

## Links from published tables into the new families

Done. T110 to T117 are published -- the polynomial families answering
numberdb-data#80, #81, #82, #98, #114, #115, #121 and #122 -- and the links
back are in place:

    T13   Bernoulli numbers      -> T114 Bernoulli, T115 Euler polynomials
    T98   Chebyshev, first kind  -> T117 Dickson, with 2 T_n(x) = D_n(2x, 1)
    T99   Chebyshev, second kind -> T117 Dickson
    T20   Zeros of Bessel J      -> T116 Bessel polynomials, saying they are
                                    a different object
    T101  Legendre polynomials   -> T111 and T112, as the other two bases

`audit_table` refuses a link from a published table into a draft, which it
used to pass: a draft answers 404 to everybody, so the link would be dead on
every page view. Two drafts may link to each other.

## Transformations: finding a number that appears here in a different form

The use case the whole database serves is: a number came out of a calculation,
and the question is whether it is already known somewhere else. A table that
holds `x/5` when the searcher has `x` fails that question, and fails it
silently -- the searcher concludes the number is new.

Advanced search already answers part of this from the searcher's side: it takes
a batch of numbers, so `x*p/q` for bounded `p, q` can be asked as one query,
and the searcher decides which transformations are worth trying. That is the
right place for a searcher's guesses.

**What is missing is the table's side.** Some transformations are natural to a
particular table rather than to a particular search, and the table is the only
place that knows them:

* The zeros of the Riemann zeta function are stored as their imaginary parts.
  Somebody holding the complex zero `1/2 + 14.134...i` should find them, and
  somebody holding the modulus perhaps too.
* An orthogonal family on `[-1,1]` has a natural twin on `[0,1]`, reached by
  `x -> 2x - 1`. Somebody who met the shifted form should find the table.
* A polynomial met with its coefficients reversed, or scaled to be monic, is
  the same object for the purpose of "have I seen this before".

None of these should need a second table. A second table for the shifted
Legendre polynomials would double the corpus for no new mathematics, and the
two would then have to be kept in step.

### The shape of it

A table declares transformations of its own entries that are also searchable.
The index carries the transformed values; the table stores what it stores.

Four things have to be settled and none of them is obvious:

**A hit must say which form matched.** "Your number is in T3" is wrong if what
is in T3 is half of it. The result has to carry the transformation, or the
answer misleads in exactly the way the database exists to prevent.

**Rigour is derived, not inherited.** `sqrt(x)` of a proven interval is proven
only if the square root was taken in interval arithmetic. Taking it of the
printed digits gives a number whose last places are wrong, and the T93 episode
is what that looks like when nobody checks. A transformation has to be computed
the way the entry was.

**Every transformation added makes a hit mean less.** If enough forms are
searchable, every number matches something and the answer "this is known"
stops carrying information. This is the real cost and it is not a
storage cost. A short, argued list per table is worth more than a general
mechanism applied everywhere.

**The index grows by a factor per transformation**, on 56,000 entries.

### Worth considering, roughly in order of how often they would help

    x -> p x / q for small p, q        already available from the search side
    x -> 1/x                           reciprocals are met constantly
    x -> -x                            a sign convention differing
    complex <-> real and imaginary parts, and modulus
    polynomial: reversal, monic scaling, x -> ax + b

### For now

Each table should hold the most natural form of its objects, so that the
question arises as rarely as possible.

The polynomial tables here do. Worth being exact about why: a family does not
live "on an interval" -- the interval is where it is orthogonal, which is a
property and not the definition. T98 defines the Chebyshev polynomials by
`T_n(cos a) = cos(na)`, which determines them and leaves nothing to choose;
the Bernstein basis is given by its formula; the Lagrange basis names its
nodes. The shifted families are genuinely different polynomials, reached by
`x -> 2x - 1`, which is exactly why they are a transformation to find rather
than a convention to pick.

Where a table did have a choice -- the two Hermite conventions, the
factorial in the Bernoulli polynomials of the second kind, the parameter order
in Bernstein -- the definition says which was taken. That is what the
convention rule in `corpus-shape.md` is for, and the reason it is there is
T52, which could not be reproduced from what it said.

## Finding table ideas at scale

Two halves, and only the second is what has been done so far.

**Which families are worth a table** is the harder half, and the use case
answers it: a family earns a table if a number from somebody's calculation
might turn out to be one of its members. That favours things that arise as
answers -- constants, special values, invariants, discriminants -- over things
that are merely easy to generate. numberdb-data#128 makes the point against
itself: "Monomials. Trivial but maybe should be included?" A table of monomials
would match everything and tell nobody anything.

It also argues for breadth over depth. Fifty families with their first dozen
members are worth more than one family with a thousand, because the question is
"is this number known", not "give me more of this sequence".

**Adding them** is what the last few days have been: measure before choosing a
range, check every identity before writing it down and again on the values read
back, reference tables that exist here rather than encyclopedias, and let
`audit_table` catch what a person would not. That part is repeatable and could
be run in batches by a program that has the skill and an API key -- with
publication still an act by a person, for the reasons in
`guarding-generated-tables.md`.
