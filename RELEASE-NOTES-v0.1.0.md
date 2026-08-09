# numberdb 0.1.0

The write side is a different shape. Everything about reading is unchanged.

## One way to add numbers

Writing was fourteen public names and a `publish()` with twelve arguments.
Every one of those arguments started as a real failure mode — the lost update,
the run that dies at entry 900, the missing key discovered after three days —
and every fix was another parameter. But a parameter is a decision handed to
somebody who wanted to upload some numbers.

```python
class Zeta(numberdb.Generator):
    table = 'T42'
    parameters = ('n',)

    def enumerate(self, limit=1000):
        for n in range(2, limit + 1):
            yield {'n': n}

    def value(self, params, digits):
        return RealIntervalField(numberdb.bits(digits))(zeta(params['n']))

Zeta().publish()
```

`numberdb.Generator` is now the whole of it. Caching, streaming, naming the
run, attaching the code that produced the numbers and checking permission
before computing are not preferences and are no longer asked about.

`publish`, `preview` and `verify` are methods on the generator: a generator is
written *for* one table and knows which. A subclass that defines one of those
names is refused at the `class` statement rather than silently replacing the
way its own numbers get published.

**Removed:** `submit`, `document`, `create`, `Lease`, `attach`, `Entries`,
`to_text`, `submit_entries`, `check_writable`, `generate`. Sending a whole
document is how a generator deletes somebody's definition; that function no
longer exists. Prose is edited on the site, where a person signs it.

## What it asks, and why

`overwrite` (default true), and three that each default to the cautious answer
and are named in the refusal that mentions them: `correcting` for values that
contradict what is stored, `lowering` for values with fewer digits, `removing`
for entries this run did not produce. Each value is checked as it is computed,
so a run that has started producing different numbers stops at its first entry
rather than after a day.

## Digits are decimal, and now guaranteed

Sage builds interval fields in **bits**; this database counts **decimal
digits**. `RealIntervalField(digits)` reads perfectly well and delivers about a
third of what was meant. `numberdb.bits(digits)` converts, and `publish`
measures what each value actually pins down and refuses to store a table of
thirty-digit numbers that was meant to hold a hundred.

An entry genuinely known no better says so: `return {'number': x, 'digits': 8}`.

## The written form

An approximate real is stored as a plain decimal: `3.14159` **is** the interval
(3.14158, 3.14160). Intervals and balls, real and complex, Sage's and this
package's own, all arrive as that. Trailing zeros before the decimal point are
never written, because under this convention they are a claim.

Sage `RealBallField` and `ComplexBallField` values could not be written at all
before; they can now.

## Where the key comes from

`NUMBERDB_API_KEY`, then a `.env` beside your script or above it, then
`~/.config/numberdb/env`. Nothing in either file is executed.

## Renamed

Every exception ends in `Error`: `RateLimitError`, `UnauthorizedError`,
`ConflictError`, `TooBigError`, `UnsupportedNumberError`, and the new
`DisagreementError`. Results are named after the call that returns them:
`PublishOutcome`, `VerifyReport`.

## Sage

`import numberdb.sage as numberdb` reaches the whole public surface, including
`Generator` and `publish` — it did not before, which is exactly the audience
that writes generators. Whole Sage objects are accepted where their components
were wanted: `search_real_interval(RIF(3.14, 3.15))`, `search_p_adic(Qp(2)(1, 167))`.

`verify` no longer compares text. A table built at 20 digits and checked at 100
agrees with itself; the old check reported every entry as broken and proposed
rewriting all of them.
