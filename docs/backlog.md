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

The stated goal, and the case has only strengthened. The web image is 4.9 GB of
Sage on a 961 MB VM already at ~707 MB used with swap nearly full. The exact
number layer under `utils/numbers/` is already Sage-free and a test enforces it;
search now resolves reals, complex values and p-adics in plain Python and SQL.
What still imports Sage: `numberdb_app/models.py`, `views.py`, `api.py`, and
`utils/utils.py`. The evaluator sandbox keeps full Sage either way.

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
