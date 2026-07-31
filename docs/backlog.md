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

Enter and the magnifier should both run the search. What they should land on is
the open question, and it decides the size of the job:

- **the best match** -- cheap, no new page; but silently discards the rest, and
  "best" is only well defined now that results are scored
- **a full results page** -- the honest answer for a query matching thousands,
  and the natural home for the hundred-result cap and the score ordering, but
  no such page exists yet (`/advanced-search` is a different thing)

The second is the better fit for how search now works: broad queries routinely
match tens of thousands of values, and a dropdown cannot represent that.

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
- **Degenerate p-adic balls.** `_coarser_ball_strings` does not emit the ball
  around zero, reached when precision drops to or below the valuation, which is
  written `"p,0,000..."` rather than as a prefix. Such matches are too coarse to
  be useful, but the omission is deliberate rather than proven unreachable.
