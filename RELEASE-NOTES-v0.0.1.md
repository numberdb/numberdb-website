First release of the `numberdb` client package for Python and SageMath.

```
pip install numberdb
```

```python
import numberdb
numberdb.search_real_ball(3.14159265, 1e-8)      # is this a known number?
numberdb.search_text('matrix multiplication')
```

In SageMath the same calls return Sage objects, and nothing else changes:

```python
import numberdb.sage as numberdb
numberdb.search('pi')[0].value                   # 3.141592653589794?
```

**What it searches.** Integers, rationals, real and complex intervals and
balls, p-adic numbers, polynomials, free text, and Sage expressions — through
one `search()` that takes a value of any supported type, or a named
`search_*` for a specific one.

**Notes on this version.** The version number is deliberately small: the API
is settled enough to use, but nobody outside the project has used it yet, and
0.0.x should be read as an invitation to tell us what is wrong with it.

Three things it is careful about, which are easy to get wrong quietly:

* Intervals are only ever widened, never narrowed — by the client when it
  bounds an oversized query, and by the Sage conversion when an endpoint has
  no exact Sage representation. A search returns more than it must, never less.
* Long queries are trimmed to 100 significant digits before they are sent, and
  results are re-checked against the original query afterwards.
* Polynomials are matched up to renaming of variables, by a canonicalisation
  the client and server compute identically, so a 58k-character polynomial
  travels as a 128-bit hash.

The package has no dependencies, needs no SageMath, and never imports Sage
unless you ask for `numberdb.sage`. MIT licensed.
