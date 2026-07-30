# How numbers are represented, and why there are two representations

Status: describes existing behaviour

Short version: **the string is the source of truth; the floats are a working
copy.** They are not two encodings of the same thing, and the conversion
between them only runs one way without loss.

## The two representations

| | where | role |
|---|---|---|
| Text, as the contributor wrote it | `TableData.raw_yaml`, `full_yaml`, `json` | **canonical** |
| Interval endpoints as `float64` | `Number.number_blob`, `lower`, `upper` | derived search index |

`Number` has no string field at all. That is deliberate, not an oversight.

Both are user-visible, in different places:

* Table pages render from the YAML (`numberdb_app/views.py`, via
  `table.data.full_yaml`), so a reader sees what the contributor actually wrote.
* Advanced-search results render `str_short()` from the float blob
  (`templates/includes/advanced-search-results.html`), because that is what was
  matched against.

## Why the round trip cannot be closed

A written value like `5.5?` denotes a real interval with *exact decimal*
bounds. Those bounds are generally not representable in binary floating point,
so converting to `float64` must round **outward** -- the stored interval is
slightly wider than the one written. That is fine for searching, which only
needs containment.

It is not fine as a source of truth, because the widening is not recoverable.
Rendering the widened interval back to text does not return the original
string, and the loss compounds. Measured with Sage 10.9:

```
string      -> rendered   -> rendered again
5.5?        -> 6.?        -> 6.?          stable, but already far from the input
3.14159?    -> 3.1416?    -> 3.142?       loses a digit per pass
2.675?      -> 2.68?      -> 2.7?         loses a digit per pass

RIF('5.5?')  lower = 5.39999999999999
             upper = 5.60000000000001
exact decimal bounds would be [5.45, 5.55] -- not representable
```

So the text -> interval -> text cycle is **not a fixed point**. Any code that
reads a number out of the index and writes it back to the canonical store
degrades it, silently, every time it runs.

## Consequences

1. **Never write back to `TableData` from `Number`.** The index is downstream.
   Rebuild the index from the text, never the reverse.
2. **Do not "fix" the widening.** It is required for correct containment
   search. An interval that rounded inward could fail to match a number it
   genuinely contains.
3. **Do not treat `str_short()` as the number.** It is a rendering of the
   working copy, and is expected to differ from the contributor's string --
   `5.5?` legitimately displays as `6.?` in search results.
4. When moving `web` off Sage
   (`utils/number_decode.py`), the target is to reproduce the *existing
   rendering of the working copy* byte-for-byte -- pinned by
   `tests/golden/number_decoding.json`. It is explicitly **not** to make the
   round trip lossless. That is impossible, and the current design does not
   attempt it.

## If the canonical store ever moves into the database

Today the text lives in the `numberdb-data` git repository and is imported, so
the database is reproducible and the index can be rebuilt at any time. Once
authoring moves into the site, `TableData` becomes irreplaceable: it is the only
copy of the canonical text, and the float index cannot regenerate it. Backups
have to exist before that switch, not after it.
