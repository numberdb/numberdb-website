# Design: how numbers are represented internally

Status: proposed
Related: `docs/design/number-representation.md` (why the string is canonical and
the float index is derived)

## Summary

Three layers, with a different type and a different job at each:

| layer | type | job |
|---|---|---|
| **notation** | `Decimal`, `Fraction` | faithful: what was written, what we render, where the uncertain digit is |
| **semantics** | `Fraction` | exact bounds; comparison, containment, equality |
| **search** | `float` + magnitude | indexed, outward-rounded, deliberately lossy |

`Decimal` for what the contributor wrote, `Fraction` for what it means, `float`
for finding it.

Callers touch only a wrapper class. The `Decimal` is never exposed, because
`Decimal` arithmetic is context-rounded and must not be used for computation.

## Why the current representation is not adequate

Not hypothetical -- measured against production:

**Exact rationals are silently downgraded.** `Number.number_blob` is two 8-byte
halves, so an exact rational only fits while numerator and denominator are
small. Sampling the Bernoulli numbers, which are exact rationals by definition:

    stored types: {b'r': 32, b'q': 18, b'z': 2}
    B_36 stored as an interval -> -1.3711655205088333e13

Two-thirds are stored as float intervals. The exactness is discarded at import
and cannot be recovered.

**Exact values are displayed as inexact.** `str_short()` routes rationals
through `to_RIF()`, so `-1/2` renders as `-0.50000000000000000` -- which, under
the documented convention, asserts it is an interval.

**The float relaxation overflows.** 310 rows have already saturated `float64`:

    rows with upper >= 1e308: 152      rows with lower <= -1e308: 158
    type r  lower 1.7976931348623157e+308  upper inf  ->  [1.797e308,+infinity]

Those numbers are mutually indistinguishable to search, and users are told they
are infinite.

**Binary conversion compounds.** Storing decimal input as `float64` means the
text -> value -> text cycle is not a fixed point; it loses a digit per pass
(`3.14159? -> 3.1416? -> 3.142?`). That is what makes `5.5` display as `6.`.

## Layer 1: notation

The documented notations are preserved as written, not derived from the bounds.

    ExactRational(Fraction)         5/6, -3/2, 42        arbitrary denominator
    DecimalExpansion(Decimal)       3.14, 12e2           value +- one ulp
    DecimalInterval(lower, upper)   [2, 2.3728596]       endpoints exact
    DecimalBall(centre, radius)     3.14 +/- 2e-2        both exact

Endpoints, centre and radius accept `Decimal` **or** `Fraction`, so `[1/3, 1/2]`
becomes expressible. Today it parses as `None` in every format, which is a gap
rather than a decision.

### Why notation is stored rather than derived

Deriving a rendering from the bounds alone is unsound. `3.14 +/- 2e-2` denotes
`[3.12, 3.16]`, and:

* as a decimal expansion with `e = -2`, `3.14` means `[3.13, 3.15]` -- which
  does **not contain** `[3.12, 3.16]`. It would claim precision that is absent.
* as a decimal expansion with `e = -1`, `3.1` means `[3.0, 3.2]` -- sound, but
  five times wider, discarding most of what the contributor knew.

So for this value no decimal expansion is both sound and faithful, and nothing
in the bounds distinguishes "ball" from "interval `[3.12, 3.16]`" -- that choice
exists only in how it was written.

For a 100-digit expansion derivation *would* work, since the radius is exactly a
power of ten. A rule that works for some values and silently fails for others is
worse than one that always works.

Storing the notation makes rendering a lookup instead of a derivation: total,
free of a class of rounding bugs, and an exact round trip.

### The one exception: p-notation

`1p31415` normalises to the decimal expansion `3.1415`. It is not a distinct
semantic form -- its own documentation defines it by translation ("ApB
corresponds to the decimal expansion 0.BeA") -- and it exists as a shorthand for
typing into the search bar, not as a way of writing a number in a table.

## Why `Decimal` and not only `Fraction`

`Decimal` preserves **significance**, which is load-bearing under the ±1
convention. `Fraction` destroys it:

    3.14     digits=(3,1,4)      exponent=-2   means [3.13, 3.15]
    3.140    digits=(3,1,4,0)    exponent=-3   means [3.139, 3.141]

    Fraction(Decimal("3.14"))   = 157/50
    Fraction(Decimal("3.1400")) = 157/50       identical -- different intervals

A notation layer built on `Fraction` would silently discard every trailing zero
a contributor wrote, widening their interval tenfold per zero.

Further properties, all verified:

* Construction from a string is **exact regardless of context precision** -- a
  300-digit decimal round-trips exactly at the default `prec=28`. The context
  governs arithmetic, not construction.
* `.as_tuple()` yields `(sign, digits, exponent)`, so the uncertain digit is
  `digits[-1]` and its place value is `10^exponent`. The renderer gets the
  dotted position without string surgery.
* No overflow: `Decimal('1E+1000')` is unremarkable, so the faithful layer holds
  the values that saturate `float64` today.
* `Fraction(Decimal('3.14')) == 157/50` -- the bridge to layer 2 is exact.

`Decimal` cannot represent `1/6` or `5/6`, so `ExactRational` holds a `Fraction`.
The two coexist; neither replaces the other.

### The caveat this design exists to contain

`Decimal` arithmetic is context-rounded:

    Decimal(1)/Decimal(3) = 0.3333333333333333333333333333    (28 digits)

So **`Decimal` is a storage and presentation type only.** Every computation goes
through `Fraction`. This is easy to violate by accident, which is why the
`Decimal` is private to the wrapper and never returned.

## Layer 2: the wrapper

```
ExactReal                                  # the only type callers touch
  .bounds()        -> (Fraction, Fraction) # exact, always
  .render()        -> (text, dotted_index) # dotted_index None unless expansion
  .search_bounds() -> (float, float)       # outward-rounded, magnitude-aware
  __eq__/__hash__  by bounds, not by notation

ExactComplex                               # a pair of ExactReal (a box)
  .real(), .imag()
```

`5/6 + 5.5I` stores `ExactRational(5/6)` and `DecimalExpansion(5.5)` side by
side, and renders as `5/6 + 5.5I` with a dot under the final `5` -- the mixed
exactness that the current four-float schema cannot express at all.

### Equality is by value, not by spelling

`3.14` and `[3.13, 3.15]` are the same set and compare equal; dedup keeps one,
arbitrarily choosing its rendering. This is the one place where "preserve what
was written" and "equal things are equal" pull against each other, and it is
resolved deliberately in favour of value equality, because search and dedup
depend on it.

## Rendering, and the dotted digit

`.render()` returns structure, not a bare string: the text plus the index of the
digit that may be off by one, or `None`.

The rule is systematic: an index is present **exactly** for `DecimalExpansion`,
and `None` for exact rationals, intervals and balls. So absence of a dot means
exact, and the notation becomes self-describing rather than requiring a reader
to recall which position they are looking at.

This resolves a genuine ambiguity: the same glyphs mean different things by
context. `3.14` bare denotes `[3.13, 3.15]`; inside `[3.14, 4]` it is exactly
3.14; before `+/-` it is exactly 3.14.

Consumers:

* **HTML** -- the digit is wrapped in a dotted-underline span with a tooltip and
  a link to the help anchor. Copy-paste still yields `5.5`, valid input, because
  the mark is presentation only. Dotted rather than wavy: browsers use wavy for
  spelling errors, which reads as "this is wrong"; dotted conventionally means
  "there is a definition here", which is the intent.
* **Screen readers** -- styling is invisible to them, so an explicit label is
  required or the distinction is lost entirely.
* **JSON API** -- cannot carry styling, and should carry the exact bounds
  explicitly so machine consumers never infer from notation.
* **Plain text** -- the mark is gone; only the convention carries it.

Display length is a separate concern from notation. Truncating a 100-digit
expansion for a table cell is always *widening*, hence sound: showing ten digits
with the last dotted contains the original comfortably. "Show more" is a UI
affordance, not a change to what is stored.

## Layer 3: the searchable relaxation

Unchanged in principle, and already the pattern used by `NumberPAdic`
(`number_string` plus indexed `prime`/`valuation`) and `Polynomial`
(`number_string` plus `number_string_hash`). Reals and complex are the outliers,
storing *only* the lossy projection with no faithful layer at all.

Bounds are rounded **outward**, guaranteeing no false negatives; false positives
are refined by exact comparison on the candidate set. Filter and refine.

`float64` saturates at ~1.8e308, and the data exceeds that (310 rows today), so
the relaxation must be magnitude-aware. Two shapes:

1. **Log-magnitude bounds** -- store `(sign, log10_lower, log10_upper)`. A
   double's exponent range covers magnitudes to 10^(10^308). Cleaner, needs care
   around zero and intervals spanning it.
2. **Split mantissa and exponent** -- keep float bounds for the ordinary range
   and add an indexed base-10 exponent. Preserves existing indexes and queries;
   only the overflow path is new.

Efficient search -- particularly for complex numbers, where the current
searchstring approach works but is not the best available -- is deliberately out
of scope here and is the subject of its own discussion.

## Other types

* **p-adic**: a ball `(p, precision, exact representative)`. Already exact;
  needs normalising, not redesigning.
* **Polynomial**: exact rational coefficients. Already exact -- `parse_polynomial`
  rejects `.` outright.

## Implementation notes

* The value classes are **plain Python** -- `int`, `Fraction`, `Decimal`, no Sage
  import. Conversion lives in a separate adapter used only by the evaluator and
  the importer. This makes the exactness work and the "remove Sage from `web`"
  work the same change rather than two competing ones, and it makes the whole
  layer testable with `python3` alone.
* Python's `int` is arbitrary-precision, so 1000-digit values need no special
  handling. But Python 3.11+ caps int<->str conversion at 4300 digits by default
  (a DoS guard, not an arithmetic limit); `sys.set_int_max_str_digits()` must be
  set explicitly, since the data exceeds it.
* Canonicalisation becomes correctness-critical, since dedup depends on it.
  Property test: `canon(parse(canon(x))) == canon(x)`.
* Storage is arbitrary-precision text, not fixed-width binary. The 2x8-byte blob
  is precisely what lost two-thirds of the Bernoulli numbers.

## Migration

Reimporting ~55k rows is free while `numberdb-data` holds the canonical text and
the index is derived from it. Once authoring moves into the site, `TableData`
becomes the only copy, the float index provably cannot regenerate it, and this
becomes a data migration with no safety net.

That argues for doing it before the GitHub migration, not after.

## Open questions

1. Efficient search, especially for complex numbers -- separate discussion.
2. Which relaxation shape (log-magnitude versus split exponent).
3. Whether interval endpoints should accept arbitrary `Fraction`s in the *input*
   grammar, now that the representation supports them.
4. Whether truncated display should be the default for long expansions, and at
   what width.
