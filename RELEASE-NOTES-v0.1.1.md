Two features and three fixes, all of them from converting real tables and
finding out what the package did wrong.

```
pip install --upgrade numberdb
```

**A generator says how well its digits are known.** A hundred digits can be
proven, believed on a stated assumption, checked by agreement, or assumed, and
until now a table presented all four identically:

```python
class UnitBallVolume(numberdb.Generator):
    rigour = 'proven'          # the default, and enforced
```

`proven` is checked in the one direction it can be: a value that carries no
error cannot have a proven one, so an exact number or an interval of nonzero
width is required. A point, a float or a string is refused. That matters more
than it sounds — wrapping a fixed-precision result in an interval field
produces an interval of **width zero**, which says the value is exact, so the
digits then written are however many were asked for. Twenty-nine tables in
NumberDB were built that way and nothing ever noticed.

The other levels are `exact`, `assumed-bound`,
`heuristic (agreement-checked)` and `heuristic`. The level is sent once per run
and shown on the table's page.

`numberdb.sage.assume_accurate(value, ulps, because)` turns a bound you can
justify into a ball, so everything after it is interval arithmetic and the
error propagates instead of vanishing at the first multiplication. There is no
default for `ulps` and `because` is required: PARI's documentation mentions
"ulp" in one of its 1271 documented functions and mpmath's `airyaizero` says
nothing about accuracy, so the bound is your assertion and the reason is what
makes it checkable later.

**`publish` no longer rewrites values that merely agree.** A value stored as
`...4689` and recomputed as `...4690` — the old script truncated the last
digit, this one rounds it — says the same thing to the same precision under
this database's convention. The first table converted had 237 such entries out
of 501. Rewriting them says nothing new about any number while marking every
one edited, so `restating=False` is the default and they are reported in
`outcome.agreed`. A value that is genuinely better is still written.

**Fixes**

* The refusal for a short value recommended `RealIntervalField(numberdb.bits(digits))`
  — which is what had just failed. It now names both causes, and computes a
  starting guard from the shortfall it measured. `digits` is how many to
  *write*, never how many to compute with.
* A run's message reaches the revision. Everything a run does lands in one
  revision and the attachment writes last, so a run described as "extended to
  n = 2000" was recorded as "a file that produced these entries".
* Sage exact values (`ZZ`, `QQ`, polynomials) are recognised as exact —
  `is_exact()` is on the parent, not the element.

MIT licensed, still no dependencies, still no SageMath required.
