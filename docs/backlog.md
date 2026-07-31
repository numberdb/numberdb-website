# Backlog

Ordered roughly by value over cost. Items carry enough detail to be picked up
cold; design docs live in `docs/design/`.

## Submitting a search from the keyboard or the magnifier

Today the only way to reach a result is to pick an entry from the autocomplete
dropdown. In `numberdb_app/templates/includes/searchbar.html` the input is not
wrapped in a `<form>`, so Enter submits nothing, and the magnifier's handler
only focuses the box:

```js
$( "#searchbox-image, #searchbox-component").bind("click", function() {
    var sb = document.getElementById("searchbox");
    if (sb !== document.activeElement) { sb.focus(); }
});
```

Enter and the magnifier should both run the search, and the results should
appear **under the search bar on the front page**, in more detail than the
dropdown shows. The dropdown stays as it is, for immediate results as you type.

The two are different views of the same query, not alternatives: the dropdown
answers "did you mean one of these" while you type, the panel answers "here is
what matched" once you commit. The panel is also where the parts of search that
a dropdown cannot express belong -- the hundred-result cap, the score ordering,
and how many matched in total.

The payoff beyond presentation is that **a search gets a URL**. It becomes
linkable, bookmarkable, and survives the back button, and it gives the search
behaviour something addressable to test against and to cite in a bug report.
That argues for a plain GET form whose query string is the search, with the
results rendered server-side, rather than state held only in JavaScript.

## Fractional-part search still asks the wrong question

`numberdb_app/views.py` searches fractional parts by containment, the pattern
replaced elsewhere in `numberdb_app/search.py`:

```python
frac_lower__range = (lo, hi),
frac_upper__range = (lo, hi),
```

A coarsely-known fractional part cannot sit inside a precise query, so it is
never returned. 39344 of 45832 stored fractional parts are interval-valued, 784
of them wider than 1e-9.

The fix mirrors `value_range`: a `frac_range` column, a GiST index, a backfill
migration, and the two-step query. One question first -- fractional parts wrap
at 1 (`if frac <= 0: frac += 1`), so an interval straddling an integer may need
two ranges or a widening to `[0,1]`. Check what `frac()` currently produces
before choosing.

## Tests for the search semantics

Nothing pins down what `numberdb_app/search.py` guarantees. Everything was
established interactively and then discarded: symmetry in both directions for
reals, complex values and p-adics; score in (0,1] and exactly 1 for contained
values; the early exit returning a full page; inclusive range bounds.

That last one is the dangerous gap. `NumericRange(x, x)` defaults to `[x, x)`,
which Postgres reads as *empty*, so getting it wrong removes every exactly
known value -- 4426 of them -- from search with no error anywhere.

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
