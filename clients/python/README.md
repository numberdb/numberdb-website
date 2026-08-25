# numberdb

Look a number up in [NumberDB](https://numberdb.org) and find out whether it is
already known, and where else it appears.

```console
$ pip install numberdb
```

```python
>>> import numberdb
>>> for result in sorted(numberdb.search_real_ball(3.14159265, 1e-8),
...                      key=lambda r: r.table.title):
...     print(result.exact_text[:24], '--', result.table.title)
3.1415926535897932384626 -- Best Sobolev constant for $W^{1,p}(\mathbb{R}^n)$
3.1415926535897932384626 -- Complete elliptic integral of the third kind $\Pi(n,m)$
3.1415926535897932384626 -- Pi
```

One number, three places it is known to appear; that is the question this
package exists to answer.

## In Python

Every call below is a complete example. Each returns a list of results, and the
counts shown are what numberdb.org answers today.

**A number you have, of whatever type.** `search` accepts a single value and
works out what it is:

```python
>>> from fractions import Fraction
>>> len(numberdb.search(10))                                  # int
2
>>> len(numberdb.search(Fraction(1, 3)))                      # fractions.Fraction
2
>>> len(numberdb.search('3.14159265358979'))                  # decimal string
3
>>> len(numberdb.search(numberdb.RealInterval('3.1415', '3.1416')))  # lower, upper
3
>>> len(numberdb.search(numberdb.PAdic(2, 0, 1, 167)))  # prime, valuation, unit, precision
6
```

`RealInterval` takes any scalar for its endpoints (`int`, `Fraction`, a
decimal string, a float, or a Sage number), and keeps it exactly, as a
`Fraction`. `PAdic` takes four integers, and its precision is absolute:
`PAdic(2, 0, 1, 167)` is `1 + O(2^167)`.

**A number whose type you want to state.** These take the number's components
directly, so nothing has to be spelled as a string first:

```python
>>> len(numberdb.search_integer(10))
2
>>> len(numberdb.search_rational(1, 3))                       # numerator, denominator
2
>>> len(numberdb.search_real_interval('3.1415', '3.1416'))    # lower, upper
3
>>> len(numberdb.search_real_ball(3.14159265, 1e-8))          # centre, radius
3
>>> len(numberdb.search_complex_interval(0, 1, 0, 1))         # re_lower, re_upper, im_lower, im_upper
100
>>> len(numberdb.search_complex_ball(0, 1, '1/1000'))         # re_centre, im_centre, radius
2
>>> len(numberdb.search_p_adic(2, 0, 1, absolute_precision=167))   # prime, valuation, unit
6
```

`search_p_adic` takes `absolute_precision` or `relative_precision`; give
exactly one.

**Polynomials**, matched up to renaming of the variables. The database stores
this one in `x`, and asking in `y` finds it:

```python
>>> [r.table.title for r in
...  numberdb.search_polynomial('x^20 + x^15 + x^10 + x^5 + 1')]
['Cyclotomic polynomials']
>>> numberdb.search_polynomial('y^20 + y^15 + y^10 + y^5 + 1')[0].exact_text
'x^20 + x^15 + x^10 + x^5 + 1'
```

**Text, in the search bar's grammar.** This reads the string as a *number* in
any of the written forms the website accepts: `'3.14159'` for a real,
`'1415'` for a fractional part, `'Q5:1010'` or `'1 + O(5^20)'` for a p-adic,
`'1/2 + i*0.866'` for a complex number, `'x^2-2'` for a polynomial. A string
states its own precision, which is why text is a sound way to search and a bare
float is not:

```python
>>> len(numberdb.search_text('3.14159265358979'))
3
```

The same term is also read as **words**, against tag names and against the
whole of each table's document -- its title, definition, comments and formulas,
not the title alone. Those matches arrive as `.tables` and `.tags` rather than
in the list itself, since they are signposts and not numbers:

```python
>>> found = numberdb.search_text('matrix multiplication')
>>> len(found)
0
>>> ('Exponent of matrix multiplication complexity'
...  in [table.title for table in found.tables])
True
>>> [tag.name for tag in found.tags]
['matrix multiplication']
>>> numberdb.tag(found.tags[0].url)['table_count']
1
```

Note the `0`: the list holds numbers, and this term matched none, so `len()`
and `if not found:` speak only for the numbers. `total` counts everything the
term matched, and is the question usually meant:

```python
>>> len(found), found.total > 0
(0, True)
>>> if not found.total:
...     print('nothing at all')
```

Both are asked, because a term is often both questions: `'0.5'` is a number,
`'matrix multiplication'` is words, and `'Pi'` is honestly each. A term
containing `:` or `^` is machinery written for a parser, and is not offered to
the word search. Every other search fills `.tables` and `.tags` with empty
lists.

**An expression**, evaluated by SageMath on the server:

```python
>>> len(numberdb.search_by_expression('pi'))
3
```

**Several numbers in one request.** Cheaper than one call each (one round trip
and a reduced rate-limit cost), and the result is keyed by position in the
list:

```python
>>> results = numberdb.search_many([10, Fraction(1, 3), numberdb.PAdic(2, 0, 1, 167)])
>>> {index: len(found) for index, found in sorted(results.items())}
{0: 2, 1: 2, 2: 6}
```

At most 100 numbers per call. Every position asked about is present in the
result, so `results[i]` always answers for `values[i]`; a number that matched
nothing maps to an empty list.

**Tables and tags**, fetched whole:

```python
>>> sorted(numberdb.table('T12'))[:6]
['Comments', 'Data properties', 'Definition', 'Display properties', 'Formulas', 'Keywords']
>>> sorted(numberdb.tag('matrix+multiplication'))
['name', 'number_count', 'table_count', 'tables']
```

## In SageMath

The same package, installed into Sage's own Python, with one import line:

```console
$ sage -pip install numberdb
```

```python
sage: import numberdb.sage as numberdb
```

Every function above is present under the same name and signature. Two things
change: Sage's own types are accepted as arguments, and `.value` comes back as
a Sage object in the natural parent.

A whole interval may be given where the components are expected, since in Sage
that is what you are holding:

```python
sage: len(numberdb.search_real_interval(RIF(3.1415, 3.1416))) > 0
True
sage: len(numberdb.search_complex_interval(CIF(RIF(0, 1), RIF(0, 1)))) > 0
True
sage: len(numberdb.search_p_adic(Qp(2)(1, 167))) > 0     # brings its own precision
True
```

```python
sage: numberdb.search(10)[0].value.parent()
Integer Ring
sage: numberdb.search(1/3)[0].value.parent()
Rational Field
sage: numberdb.search(RIF(3.1415, 3.1416))[0].value
3.141592653589794?
sage: numberdb.search(RIF(3.1415, 3.1416))[0].value.parent()
Real Interval Field with 53 bits of precision
sage: numberdb.search(Qp(2)(1, 167))[0].value
1 + O(2^167)
sage: R.<x> = QQ[]
sage: numberdb.search(x^20 + x^15 + x^10 + x^5 + 1)[0].value
x^20 + x^15 + x^10 + x^5 + 1
```

The component-wise calls behave identically and also accept Sage scalars:

```python
sage: len(numberdb.search_rational(1, 3))
2
sage: len(numberdb.search_real_ball(3.14159265, 1e-8))
3
sage: len(numberdb.search_real_interval(3.1415, 3.1416))
3
sage: len(numberdb.search_p_adic(2, 0, 1, absolute_precision=167))
6
sage: len(numberdb.search_by_expression('pi'))
3
sage: numberdb.search_polynomial('y^20 + y^15 + y^10 + y^5 + 1')[0].value
x^20 + x^15 + x^10 + x^5 + 1
```

`numberdb.sage` uses the SageMath you already have and installs nothing. Plain
`import numberdb` never imports Sage, so it starts instantly; a single result
can be converted on demand with `.sage()` either way.

**[passagemath](https://github.com/passagemath/passagemath) works too.** It
ships Sage as separate pip distributions, so the parts this package needs go
into an ordinary virtual environment without a full Sage installation:

```
$ pip install passagemath-symbolics numberdb
```

passagemath is modular, so which values convert depends on what is installed.
Read out of the 10.8.9 wheels:

| values | needs |
|---|---|
| integers, rationals, polynomials | `passagemath-categories` |
| real and complex intervals | `passagemath-flint` |
| p-adic numbers | `passagemath-pari` |

`passagemath-symbolics` pulls in the first two, which covers everything except
p-adics; add `passagemath-pari` for those:

```console
$ pip install passagemath-symbolics passagemath-pari numberdb
```

A ring that is not installed is not an error until something asks for it, and
then the error names the distribution to install. So a narrow environment
converts everything it can and says precisely what it cannot.

Install passagemath into a fresh environment, never into an existing SageMath,
where it would overwrite the installation.

Nothing here asks for `sage.all`, and each ring is imported on its own, so a
distribution that lacks one still converts everything else.

### The import is the same either way

| | no Sage | SageMath | passagemath |
|---|---|---|---|
| `import numberdb` | yes | yes | yes |
| `import numberdb.sage as numberdb` | says what to install | yes | yes |

`import numberdb` never imports Sage and works anywhere. `numberdb.sage` is the
same interface returning Sage objects, and it does not care which Sage it
found; without one it raises an `ImportError` that names both ways to get one.
So a script that does

```python
try:
    import numberdb.sage as numberdb
except ImportError:
    import numberdb
```

runs everywhere, with exact values where Sage is available and plain Python
values where it is not.

## What a search returns

A search returns a `SearchResults`: a `list` of `Result` objects, which also
carries

| Attribute | Type | Meaning |
|---|---|---|
| `.messages` | `list[str]` | remarks from the server about the search itself, if it had any |
| `.unreadable` | `list[Result]` | results whose value this version of the package cannot decode |
| `.tables` | `list[Table]` | tables whose title matched, filled in by `search_text` alone |
| `.tags` | `list[Tag]` | tags whose name matched, likewise |
| `.total` | `int` | everything matched: numbers, tables and tags together. `len()` counts the numbers alone |

A `Table` carries `.tid`, `.title`, `.url` and `.number_count`; a `Tag` carries
`.name`, `.url`, `.table_count` and `.number_count`. Both are signposts;
`numberdb.table(tid)` and `numberdb.tag(url)` fetch the contents.

Each `Result` carries:

| Attribute | Type | Meaning |
|---|---|---|
| `.value` | see below | the number itself, decoded on first access |
| `.exact_text` | `str` | the database's own spelling; the form to quote, or to paste back into a search |
| `.str_short` | `str` | an abbreviated form, comparable across results |
| `.kind` | `str` | one of `ZZ`, `QQ`, `RIF`, `RBF`, `CIF`, `Qp`, `polynomial` |
| `.param` | `str` | which entry of its table this is |
| `.table` | `Table` | where it lives, with `.tid`, `.title` and `.url` |
| `.is_readable` | `bool` | whether `.value` can be decoded by this version |
| `.url()` | `str` | the address of this value, e.g. `.../Pi?entry=n%3D1#n=1` |
| `.sage()` | Sage object | the value converted to Sage, on request |

The type of `.value` depends on which module you imported:

| `.kind` | plain `numberdb` | `numberdb.sage` |
|---|---|---|
| `ZZ` | `int` (unbounded) | `Integer` |
| `QQ` | `fractions.Fraction` | `Rational` |
| `RIF`, `RBF` | `RealInterval`, endpoints exact `Fraction`s | element of `RealIntervalField` |
| `CIF` | `ComplexInterval` of two `RealInterval`s | element of `ComplexIntervalField` |
| `Qp` | `PAdic(prime, valuation, unit, precision_absolute)` | element of `Qp(prime)` |
| `polynomial` | `Polynomial(variable_count, text)` | element of a polynomial ring over `QQ` |

Exact values stay exact. Integers are Python `int`, which is unbounded (the
database holds integers of over a thousand digits); rationals are `Fraction`,
and interval endpoints are exact `Fraction`s rather than rounded floats.
Conversion to `float` is therefore explicit, never an accident of transport:

```python
>>> result = numberdb.search_real_ball(3.14159265, 1e-8)[0]
>>> result.value
RealInterval(884279719003555/281474976710656, 7074237752028441/2251799813685248)
>>> float(result.value)          # the midpoint, explicitly lossy
3.141592653589793
```

A `PAdic` carries its unit as an integer together with a valuation, because
Q_p is not Z_p: a value of negative valuation such as 1/5 in Q_5 has no integer
form. Its precision is **absolute**: the ball is everything congruent to the
value modulo `prime ** precision_absolute`, matching the `O(p^k)` in the
printed form.

### When the server is newer than the package

NumberDB will learn new kinds of number. An older package still returns every
result: values are decoded only when asked for, so an unfamiliar one costs you
that value and nothing else, and its `.exact_text` is there regardless.

```python
>>> for result in numberdb.search_text('3.14159'):
...     if result.is_readable:
...         value = result.value       # an object of the natural kind
...     else:
...         print(result.exact_text)   # still perfectly readable
```

`results.unreadable` lists them. Every exception the package raises derives
from `numberdb.NumberDBError`, so a single `except` covers it;
`TransportError`, `RateLimitError`, `UnauthorizedError` and `UnsupportedNumberError` are the
specific cases.

## Adding numbers

Write the program that computes them, and publish it. That is the whole of
writing — `numberdb.Generator` is the only public name involved, and what you
can do with a generator is what it offers:

```python
class Zeta(numberdb.Generator):
    table = 'T14'          # the table this fills, which must already exist
    parameters = ('n',)
    digits = 100

    def enumerate(self, limit=1000):
        for n in range(2, limit + 1):
            yield {'n': n}

    def value(self, params, digits):
        #Sage builds interval fields in BITS; this database counts DIGITS.
        return RealIntervalField(numberdb.bits(digits))(zeta(params['n']))

Zeta().publish()
```

The careful things happen without being asked for:

- **values are cached as they are computed**, under a fingerprint of the code
  that made them, so a run that dies resumes rather than starting again — and
  editing that code invalidates the cache instead of quietly reusing it;
- **they are sent as they arrive**, so a crash at entry 900 keeps the first 899;
- **the whole run lands in one revision**, not nine hundred;
- **permission is checked in the first second**, not after three days;
- **one written form**: compute in `RealIntervalField`, `RealBallField` or
  their complex counterparts, and the table gets a plain decimal either way.
  `3.14159` **is** the interval (3.14158, 3.14160) — the digits written are
  known and the last is uncertain by one. No marker, and in particular not
  Sage's `3.14159?`. Set `format = 'ball'` on the generator for a table that
  records its radius instead;
- **the digits you asked for are the digits you get**: `digits` is decimal,
  Sage's fields are binary, and `RealIntervalField(digits)` — which reads
  perfectly well — delivers about a third of what was meant. `numberdb.bits()`
  converts the units; how much *more* than that to compute with is yours to
  choose, since arithmetic loses low bits by an amount that depends on the
  problem — `bits(digits, losing=512)` for something that cancels. `publish`
  measures what each value actually pins down and refuses a table that would
  silently hold a third of its claimed precision.
  An entry genuinely known no better says so: `return {'number': x, 'digits': 8}`;
- **the file that produced the numbers is stored beside them**, in the same
  revision, so a reader finds the code that made a value rather than the code
  that happens to be there now. Spread over several files? List them in
  `files = ('generate.py', 'helpers.py')` — and list your own file among them,
  since naming any replaces the automatic one.

A table's prose — its definition, comments, references and tags — is written by
a person on the site. There is deliberately no way to send it from here, so a
generator cannot delete a definition by assembling a document out of what it
happens to know.

### How well are the digits known?

A hundred digits can be proven, believed on a stated assumption, checked by
agreement, or simply assumed, and a table that does not say presents all four
identically. `rigour` says which, and the table shows it:

| | |
|---|---|
| `exact` | an integer, a rational, a polynomial. Nothing to be wrong about |
| `proven` | interval or ball arithmetic throughout; the digits follow from the width of the result |
| `assumed-bound` | fixed precision, with an error bound you assert and justify — see `assume_accurate` below |
| `heuristic (agreement-checked)` | computed twice at different precisions, keeping the digits that agree |
| `heuristic` | one computation and a guard chosen by judgement |
| `measured` | not computed at all — an experimental value, whose uncertainty is the experiment's |

**`proven` is the default, and it is enforced** — in one direction, since a
value that carries no error cannot have a proven one:

```python
class UnitBallVolume(numberdb.Generator):
    rigour = 'proven'                       # the default; said out loud

    def value(self, params, digits):
        field = RealIntervalField(numberdb.bits(digits, losing=256))
        return field.pi() ** half / (field(half) + 1).gamma()
```

A point, a float or a string is refused under `proven`. That matters more than
it sounds: wrapping a fixed-precision result in an interval field produces an
interval of **width zero**, which says the value is exact, so the digits then
written are however many were asked for. Twenty-nine tables in this database
were built that way and nothing ever noticed. If the value really is exact,
return an exact number — an `int` or a `Fraction` — rather than an interval
around one.

When the computation cannot be bounded, say so. It is not a worse
contribution, it is a differently qualified one:

```python
class AiryAiZeros(numberdb.Generator):
    rigour = 'heuristic (agreement-checked)'

    def value(self, params, digits):
        return numberdb.agreeing(
            lambda working: self._zero(params['n'], working),
            at=(150, 200))                          # two working precisions
```

`agreeing` calls your function once per precision — in **decimal digits**, not
bits — and returns the union of the results as intervals. The union has real
width, so only the digits every computation supports are written, and the
precision check has something to measure, which it does not when handed a
point.

The precisions are written out rather than derived from `digits`, and a run
that falls short does not quietly try again with more: the file attached to a
table is meant to say how those numbers were made, and a computation that
raised its own precision behind your back would not be saying it. If the
agreement is too short, raise the numbers in the file.

In SageMath, `assume_accurate` turns a bound you can justify into a ball, so
that everything after it is interval arithmetic and the error propagates
instead of vanishing at the first multiplication:

```python
value = numberdb.assume_accurate(
    pari_result, ulps=2,
    because='PARI ellL1 at 38 digits; agrees with an independent '
            'implementation to 30 digits on this curve')
```

### Who ran the publish

A revision records what produced it: the generator, the versions of the package
and of Sage, and -- when a tool submitted the run -- which one.

```
$ export NUMBERDB_ASSISTED_BY=claude-opus-5      # or codex-cli, or ...
$ sage -python generate.py --publish
```

which is stored as `Zeta (numberdb=0.1.2, python=3.12.5, sage=10.9), assisted
by claude-opus-5` and shown in the table's history and blame views.

Read from the environment rather than written into the generator, and
deliberately: a name hard-coded in a file keeps claiming that tool's work after
somebody else edits and republishes it, so it would record who wrote the file
rather than who submitted the run. `publish(assisted_by=...)` overrides it for
a caller that knows better. Unset means a person ran it, which needs no
ceremony.

The author is the person whose key published it. Authorship is accountability
and a model can neither answer for a wrong value nor agree to the licence, so
this is a disclosed method rather than a co-authorship.

There is no default for `ulps` and `because` is required. Neither is
bureaucracy: checked against the documentation, PARI mentions "ulp" in one of
its 1271 documented functions and mpmath's `airyaizero` says nothing about
accuracy at all, so the bound is your assertion and the reason is what makes it
checkable later.

The first five are ordered, weakest last. **`measured` is not on that scale**: a
well-determined physical constant can be known to more digits than a heuristic
computation and fewer than a proven one, and "is measurement better than
agreement-checking" has no answer, because they are not the same kind of claim.
A generator may declare it — one reading CODATA, say — but nothing about it can
be checked here, since the uncertainty belongs to an experiment this program
never saw.

Agreement bounds **rounding** error, not **method** error. Two runs of a wrong
algorithm agree perfectly and are both wrong.

### Arguments that control what a publish may change

A generator can work out everything about a table except what you intended, so
these are the decisions it asks you to state explicitly. Each one defaults to
the conservative choice. When `publish` refuses to carry out an operation, the
error message names the argument that would permit it.

| | |
|---|---|
| `overwrite=True` | recomputed values replace stored ones. `False` adds only what is missing — and skips computing the rest, so extending a table of a thousand expensive values by a hundred costs a hundred computations |
| `correcting=False` | allow values that **contradict** what is stored. Without it the first contradiction stops the run, which costs one entry rather than a day |
| `lowering=False` | allow values with **fewer digits** than are stored |
| `removing=False` | delete entries this run did not produce. A run over `n = 2..100` has said nothing about `n = 500`; what would have gone is listed in `outcome.left_alone` |
| `only=[...]` | compute and send just these, leaving the rest alone |
| `digits_for(params)` | how many digits *this* entry should carry, when the table is not all of one kind. The default is `digits` for every entry; the number reaches `value`, and is what that entry is held to |
| `preview()` | a method rather than a flag, so there is no such thing as a publish that does not publish: computes everything, sends nothing, applies the same refusals |

Differing precision is not a disagreement: a table built at 20 digits and
recomputed at 100 agrees with itself.

### Checking a generator, and checking a table

`preview()` asks **whether the generator is right**. `verify()` asks **whether
the table is** — whether what is stored is still what this code produces, after
the script or the software underneath it has changed.

They look alike from a distance and want opposite behaviour up close, which is
why both exist. A preview is exhaustive and stops at the first contradiction,
because you are about to write and something is wrong. A verification samples
and collects every disagreement, because you are auditing and want the list.

Neither writes anything and neither needs a key, which is what makes `verify`
worth running:

```python
zeta = Zeta()
report = zeta.verify()                # ten entries, spread through the table
if not report.ok:
    zeta.publish(only=report.to_fix())
```

`publish`, `preview` and `verify` are reserved: a subclass that defines one is
refused at the `class` statement rather than quietly replacing the way its own
numbers get published.

## Rate limits and API keys

Anonymous use is rate limited; a key raises the limit. Keep it out of your
worksheet; a shared notebook should not carry its author's key:

```console
$ export NUMBERDB_API_KEY=...
```

or, if you must set it in code:

```python
>>> numberdb.configure(api_key='...')                 # doctest: +SKIP
Client(base_url='https://numberdb.org/', api_key=set)
```

For more than one server or key in a process, use a client directly:

```python
>>> client = numberdb.Client(api_key='...')            # doctest: +SKIP
>>> numberdb.search_text('3.14159', client=client)    # doctest: +SKIP
```

Exceeding the limit raises `numberdb.RateLimitError`, which carries `.retry_after`
in seconds when the server supplies it.

## Using a different server

The default is `https://numberdb.org`. Override it to use a development server
or a private instance:

```console
$ export NUMBERDB_URL=http://localhost:8000
```

```python
>>> client = numberdb.Client(base_url='https://example.org/numberdb')  # doctest: +SKIP
>>> numberdb.search_text('3.14159', client=client)                    # doctest: +SKIP
```

A trailing slash is optional, and a base URL with a path prefix keeps it either
way.

## Where this lives, and how to work on it

The package is kept inside the website's repository, under
[`clients/python/`](https://github.com/numberdb/numberdb-website/tree/main/clients/python),
rather than in one of its own. That is deliberate: about a third of the changes
that touch the package also touch the server it talks to, because the two share
one wire format — the written form of a number, the conversion from decimal
digits to bits, the canonical form of a polynomial. Keeping them together means
such a change is one commit and one test run rather than a release cycle.

It has no dependencies and needs no SageMath, so its own tests run against a
plain interpreter:

```console
$ cd clients/python
$ python -m pytest tests -q
```

Issues and pull requests go to the
[website repository](https://github.com/numberdb/numberdb-website/issues).

## Licence

MIT.
