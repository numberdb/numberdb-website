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

**Still open, and now easy:** the real periods can be *proven*. `real_period`
is pi divided by an AGM, and arb implements the AGM in ball arithmetic --
`RBF.pi() / RBF(a).agm(RBF(b))` from the exact algebraic `_abc`, measured at
695 accurate bits out of 700. What it needs is a generator, and the curve list
vendored beside it the way T69 vendors `curves.py`.

See `docs/design/rigour.md`.

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
