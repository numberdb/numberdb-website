# Backlog

Ordered roughly by value over cost. Items carry enough detail to be picked up
cold; design docs live in `docs/design/`.

## Real users, editing content on the site

The priority ahead of any further ingestion. Today a contribution means a pull
request against the `numberdb-data` repository, which limits contributors to
people comfortable with git and GitHub -- a small fraction of the people who
know these numbers.

Wanted: accounts that can add and modify content through the website, and
probably review each other's changes before they go live. Editing and review
are separable, and editing alone is already worth having.

This is the change that makes the data no longer merely a mirror of a git
repository, so it decides several things currently taken for granted:

- **Deletion and privacy.** So far nothing needed deleting: the data comes from
  the data repo, a Wikipedia crawl and an OEIS artifact. User-submitted content
  changes that.
- **Provenance.** `Contributor` and `TableCommit` presently model git history.
  They would need to record edits made on the site instead.
- **Rebuilds.** The builder currently treats the repo as the source of truth and
  rebuilds from it. Once content originates on the site, a rebuild that starts
  from the repo would destroy it.

## Ingest the data repo's issue page, and pages like it

Numbers and polynomials submitted as GitHub issues on the data repo should be
brought in automatically, driven by Codex or Claude, and further pages added
the same semi-automatic way.

Deliberately later: worth doing only once the site itself has moved on
considerably, and after the editing story above, since that decides where
ingested content should land in the first place.

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

The one Sage feature with no passagemath home is **`SymmetricGroup`**, which
needs libgap. It is used in exactly one place -- `polynomial_modulo_variable_names`
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

## Issue API keys from the website

Keys exist and work (`ApiKey`, `numberdb_app/throttle.py`), but are minted
through the Django admin and the help page tells users to write in for one. A
logged-in user should be able to create a key, label it, see when it was last
used, and revoke it. The token is shown once and stored only as a hash, so the
page has to make that clear at the moment of issue.

Blocked on nothing; it is small, and it is the last step that makes the rate
limit self-service rather than a mailbox.

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

## Cleanups

- Delete `utils/number_decode.py`. Obsolete since the exact layer landed, and
  the source of the `240/480 cases (b 0/120, r 0/120)` line printed after every
  test run, which reads like failures.
- Rename `str_short`. It is the uniform search-result view, not an abbreviation;
  `utils/numbers/display.uniform_real_text` is the implementation.

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
