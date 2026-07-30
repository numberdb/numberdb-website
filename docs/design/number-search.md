# Design: searching for numbers

Status: proposed
Related: `docs/design/number-datastructures.md` (the exact representation this
depends on), `docs/design/number-representation.md` (string canonical, index
derived)

## The premise everything follows from

A stored entry denotes **one exact real number**, recorded as an interval only
because it is known to limited precision, or because a thousand digits are more
than anyone needs.

So overlapping intervals do **not** mean two entries are the same number. If
they *are* the same number their (correct) enclosures must overlap -- which is
what makes an overlap index sound, with no false negatives -- but the converse
fails. Two distinct constants can be indistinguishable at the stored precision.

Search therefore returns **candidates consistent with the query**, never
"matches". The UI should say so; a user seeing 146 results for `3.14` should
understand why rather than conclude the search is broken.

## Two query intents, two different correct answers

`3.14` and `[3.13, 3.15]` denote the *same interval* and should return
*different* result sets.

**Point query** -- the user has a specific real in mind, typed to some
precision. The interval is an uncertainty bound around an intended `x`.

* candidate iff `S ∩ Q ≠ ∅` (necessary for `stored = x`)
* every result is "consistent with", ordered by likelihood
* no certain/uncertain split exists; nothing here is decidable

**Range query** -- the user wants every real in an interval. `Q` is the target
set itself, not an uncertainty.

* **certainly in range**: `S ⊆ Q`
* **possibly in range**: `S ∩ Q ≠ ∅` but `S ⊄ Q` -- the stored number is not
  known precisely enough to decide
* **not in range**: disjoint

Overlap versus containment. A relevance ranking is the wrong presentation for
the second: someone asking "which constants lie between 2 and 3" wants a
definite list sorted **by value**, plus an explicit "these might also qualify"
group. Blending them into one scored list hides the very distinction they asked
about.

The index predicate is the same for both -- overlap generates candidates either
way, and only the post-processing differs. One index, two interpretations.

**The certain/possible split requires the exact layer.** With float-only bounds
`S ⊆ Q` is not reliably decidable, because outward rounding blurs the boundary.
Trustworthy range queries are a capability the site cannot offer today at all.

### Telling the intents apart

The notations already carry the natural reading: `3.14`, `12e2`, `1p31415` and
`3.14 +/- 2e-2` all say "I know this number to here" (point), while `[a, b]`
says "this range". Default on that, and make it explicitly overridable -- the
same text can legitimately mean either, and guessing silently would violate the
rule that a user should never have to wonder what the site means.

## Scoring point-query candidates

Score by the fraction of the stored uncertainty that the query accounts for:

    score = |Q ∩ S| / |S|

| situation | score | reading |
|---|---|---|
| stored exact, inside Q | 1 (by convention) | this exact number lies in your range |
| `S ⊆ Q` (stored precise, query loose) | 1 | you searched loosely and found something pinned down |
| `S ≈ Q` | ≈1 | equally precise, consistent |
| `Q ⊆ S` (stored coarse) | \|Q\|/\|S\| | consistent, but so is much else |

The asymmetry is deliberate. A symmetric measure such as Jaccard would penalise
the second row, which is the most useful outcome in a database of constants:
type a few digits, discover something known to three hundred.

### Known limits of this score

* **`|S| = 0` is 0/0.** An exact stored value inside `Q` scores 1 by definition.
* **It saturates.** Two entries both wholly inside `Q`, one known to 50 digits
  and one to 300, both score 1. Arguably correct -- both are equally consistent
  with what was asked -- but the score alone does not order them, so a tiebreak
  is required.
* **The probability reading is a heuristic.** It assumes a uniform prior over
  `S`, and a stored constant is not "uniformly distributed" over its interval;
  it is a definite number known imprecisely. The ordering behaves well; the
  calibration should not be taken literally.

### Gating, not just ordering

A value stored to 4 digits, matched by a 40-digit query, has a width ratio
around 10^-36. That is not a weak match, it is noise. Below a threshold
(10^-6, say) fold candidates into a collapsed "lower-precision candidates (12)"
section: present, but not competing.

## The current complex index, and why to replace it

`NumberComplex.__init__` builds a **Z-order (Morton) code**: interleaved base-2
digits of real and imaginary parts, prefixed by an exponent and two sign
characters, after multiplying by a fixed generic complex constant. Prefix
matching is then quadtree cell lookup.

The technique is standard and the indexing is done properly -- Django creates a
`text_pattern_ops` B-tree and the planner uses it:

    Index Cond: (number_searchstring ~>=~ '1++0101') AND (~<~ '1++0102')
    Execution Time: 2.101 ms

**The data structure is right; the query is incomplete.** Correctness requires
querying every cell that overlaps the query region. The implementation queries
exactly one, and both resulting failures are measurable.

**Coarse values are invisible to precise queries.** The filter asks
`stored.startswith(query)`, which finds only cells *inside* the query. A value
stored imprecisely is an *ancestor* cell, and that direction is never asked:

    stored (coarse)  len 13   1++0000010000
    query  (precise) len 105  1++00000100001001000
    stored.startswith(query)?  False   <- what the filter asks
    query.startswith(stored)?  True    <- the query point is inside the stored box

Not hypothetical: stored strings in production run from 78 to 109 characters.

**Cell boundaries are cliffs.** Two numbers a thousandth apart share a
zero-character prefix when `|generic·z|` crosses a power of ten, because the
exponent leads the string:

    z=4.1680 -> 1++1101000110111
    z=4.1690 -> 2++0000000110111
    common prefix: 0

The same happens across the two sign characters. The generic constant relocates
these discontinuities to an arbitrary circle and axes; it does not remove them.

## Recommended: GiST box overlap

Postgres has this natively -- no PostGIS:

    PostgreSQL 14.20
    box '(0,0),(1,1)' && box '(0.5,0.5),(0.7,0.7)'  ->  1
    access methods: btree, gist, spgist

Store each number's bounding box as a native `box` built from outward-rounded
bounds, index with GiST, query with `&&`.

* **overlap is symmetric**, so coarse-versus-precise works in both directions --
  no ancestor enumeration
* **no cell boundaries**, hence no cliffs at magnitudes or axes
* **no generic transformation**, so stored values stay interpretable and boxes
  stay axis-aligned with what users actually query
* mixed precision is handled by construction

The deeper reason this is the right trade: with an exact layer to refine
against, the index only needs to be a **sound over-approximation**. False
positives are free -- they are discarded exactly. The Z-order scheme optimises
for tightness and pays in false negatives, which is the wrong way round.

### Magnitude saturation

`box` is float8 internally, so it inherits the ~1.8e308 ceiling that already
saturates 310 rows. Indexing `(asinh(re), asinh(im))` is monotone and
overlap-preserving, compresses magnitude smoothly, and handles zero and huge
values alike. Worth adopting while the index is being rebuilt anyway.

## Blurring belongs to candidate generation, not semantics

`blur_real_interval` is applied uniformly to every query (`api.py:210`,
`views.py:1038`), widening by ~2^-51 relative with no distinction of intent. As
a float-error guard for point queries that is right. For a range query it
silently widens a deliberate boundary, so a number just outside `[2, 3]` can be
reported as inside.

With exact bounds: blur only the **index lookup**, where over-approximation is
deliberate and harmless, then apply the exact unblurred test during refinement.
Blur stops being part of the semantics.

## Candidate volumes

Measured against production, showing that query precision -- not stored
precision -- dominates:

    0.5       (1 digit)  ->  898 candidates
    1.6       (2 digits) ->  916
    3.14      (3 digits) ->  146
    3.14159   (6 digits) ->    3
    3.1415926 (8 digits) ->    3

A coarse query legitimately admits many candidates, because at three digits 146
stored constants genuinely cannot be distinguished from pi. No index design
changes that; presentation and language have to carry it.

## Open questions

1. Tiebreak among candidates that all score 1.
2. Whether the gating threshold should be fixed or relative to result count.
3. Whether real (1-D) search should also move to a range type with GiST, or stay
   on the existing float columns, which are adequate for one dimension.
4. p-adic and polynomial search are unchanged here and may deserve the same
   treatment later.
