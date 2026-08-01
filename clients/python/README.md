# numberdb

Look a number up in [NumberDB](https://numberdb.org) and find out whether it is
already known, and where else it appears.

```console
$ pip install numberdb
```

```python
>>> import numberdb
>>> for result in numberdb.search('pi'):
...     print(result.exact_text, '--', result.table.title)
3.14159265358979323846264338327950288419716939937510582097494 -- Pi
3.14159265358979323846264338327950288419716939937510582097494 -- Complete elliptic integral ...
```

## In SageMath

The same package. Install it into Sage's Python and ask a result for its Sage
form:

```console
$ sage -pip install numberdb
```

```python
sage: import numberdb
sage: results = numberdb.search('{n: pi^n for n in [1..5]}')
sage: results[0].sage()
3.141592653589794?
sage: results[0].sage().parent()
Real Interval Field with 53 bits of precision
```

Sage is optional and is not imported until `.sage()` is called, so the package
starts instantly in a plain interpreter.

## What you get back

`search()` returns a list of results, each carrying:

| | |
|---|---|
| `.value` | the number in plain Python |
| `.exact_text` | how the database writes it — the form to quote or paste back into a search |
| `.str_short` | a short form, comparable across results |
| `.table` | where it lives (`.tid`, `.title`, `.url`) |
| `.param` | which entry of that table it is |
| `.sage()` | the number as a Sage object |
| `.url()` | where to read about it |

`.value` is one of `int`, `Fraction`, `Interval`, `Box`, `PAdic` or
`Polynomial`. Exact values stay exact: integers are Python `int` (unbounded —
the database holds integers of over a thousand digits), rationals are
`Fraction`, and interval endpoints are exact `Fraction`s rather than rounded
floats. Converting to `float` is your decision, never an accident of transport.

```python
>>> result.value
Interval(884279719003555/281474976710656, 7074237752028441/2251799813685248)
>>> float(result.value)          # the midpoint, explicitly lossy
3.141592653589793
```

The search itself may have something to say — that it was capped, or that part
of the expression was rejected:

```python
>>> results = numberdb.search('...')
>>> results.warnings
['We only show the first 100 results.']
```

## Rate limits and API keys

Anonymous use is rate limited. A key raises the limit:

```python
>>> numberdb.api_key = '...'
```

or, better, keep it out of your worksheet — a shared notebook should not carry
its author's key:

```console
$ export NUMBERDB_API_KEY=...
```

Exceeding the limit raises `numberdb.RateLimited`, which carries `.retry_after`
in seconds when the server supplies it.

## Other calls

```python
>>> numberdb.table('T12')       # a whole table, as stored
>>> numberdb.tag('Irrational')  # the tables carrying a tag
```

## Why a package and not a file to copy

The API sends JSON, and turning it into numbers has to happen somewhere. Doing
it by hand is how the previous example client came to call `loads()` on
server-supplied bytes — which executes whatever those bytes say, handing code
execution to anyone able to answer the request. In this package decoding is a
fixed table: a response can select one of seven decoders and nothing else.

Being a package also means it is versioned. When the wire format changes, that
is a version bump and a clear error telling you to upgrade, rather than an
exception in the middle of your session.

## Licence

GPL-3.0-or-later, matching NumberDB.
