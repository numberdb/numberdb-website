"""The interface a table's generator implements.

A table should have a program that can recompute its entries, and that program
has four jobs, not one: produce the table to begin with, extend it, recompute
it to greater precision, and -- the one that gets skipped -- check that it
still produces what is stored, after the script or the software underneath it
has changed.

The 82 generators in the data repository do only the first. 66 of them hardcode
their precision, 18 hardcode their bound, none takes any input at all, and one
defines a function. Written that way a generator supports exactly one of the
four jobs, once.

All four fall out of one shape: **a function from one entry's parameters to
that entry's value**, plus a way to enumerate the parameters.

    class ZetaAtIntegers(numberdb.Generator):
        parameters = ('n',)
        type = 'R'

        def enumerate(self, limit=1000):
            for n in range(2, limit + 1):
                yield {'n': n}

        def value(self, params, digits):
            #Sage's RealIntervalField, not numberdb.RealInterval. Both are
            #accepted and the names collide; a generator running under Sage
            #will normally have the Sage one to hand. Build the field wider
            #than the digits asked for -- `digits` is how many are written,
            #not how many to compute with -- and `to_text` truncates.
            return RealIntervalField(4 * digits)(zeta(params['n']))

Generating is iterating; extending is iterating further; more precision is a
larger ``digits``. And verifying is *sampling* -- ten entries rather than a
thousand -- which matters because several of these tables take hours or days to
produce in full. A check that takes seconds is a check that gets run.

Some tables cannot be computed one entry at a time: zeros found by a sweep,
values lifted from another database. Those override ``all_entries`` instead and
simply do not get cheap sampling. That is a real limitation, and better stated
than designed around.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional

from ._write import DIGITS, Entries, to_text

__all__ = ['Generator', 'Report', 'generate', 'verify', 'publish']


class Generator:
    """Base class for a table's generator.

    Subclasses declare what the table is and implement one or both of
    ``value`` and ``all_entries``.

    ``parameters`` names the parameters in the order the identities are built
    in. That order is fixed when a table is created and may not be changed
    afterwards: an entry's identity is its parameter values, so reordering
    reassigns every identity at once, and citations do not break -- they
    resolve and point at different numbers.
    """

    #: Parameter names, in identity order. Empty for a table of bare values.
    parameters: tuple = ()

    #: What the values are: 'Z', 'Q', 'R', 'C', 'Qp', 'Z[]', 'Q[]'. The exact
    #: ones ignore ``digits``, because an exact value has no precision to
    #: choose -- writing fewer digits of a polynomial does not round it, it
    #: makes it a different polynomial.
    type: str = 'R'

    #: Significant digits when the caller does not say. A hundred identifies
    #: any number in this database; more earns its place only when it was
    #: expensive to obtain.
    digits: int = DIGITS

    #: Which table this generates, when it is tied to one.
    tid: Optional[str] = None

    #: Which files to store with the numbers, named rather than guessed.
    #:
    #: Empty means "this generator's own source", which is what most runs want.
    #: Name them when the computation is spread over several files, or when a
    #: note or a table of inputs belongs beside the values -- guessing at that
    #: from the directory would sweep up whatever else happened to be sitting
    #: there, which is nobody's intention and sooner or later somebody's
    #: private working file.
    #:
    #: Paths are read relative to the file the generator is defined in and
    #: stored under their bare names: a table's files are flat.
    files: tuple = ()

    EXACT_TYPES = frozenset(['Z', 'Q', 'Z[]', 'Q[]'])

    def enumerate(self, **bounds: Any) -> Iterator[Mapping[str, Any]]:
        """Yield one mapping of parameter values per entry.

        The values are the generator's own objects -- an ``int`` for `n`, a
        ``Fraction`` for a rational parameter -- and the same mapping is handed
        back to ``value``. Nothing converts between a typed value and its
        written form and back, because that round trip is where identities move:
        `0.5` and `1/2` are the same number and different identities.

        ``bounds`` is whatever the generator wants to be asked for: a limit, a
        range, a discriminant bound. Extending a table means calling this with
        a larger one.
        """
        raise NotImplementedError(
            '%s must implement enumerate() or all_entries()'
            % (type(self).__name__,))

    def value(self, params: Mapping[str, Any], digits: int) -> Any:
        """The value of one entry, to ``digits`` significant figures.

        Return anything ``to_text`` understands: an ``int``, a ``Fraction``, a
        ``RealInterval``, a ``PAdic``, a ``Polynomial``, a Sage object, or a
        string already in the database's form. A bare ``float`` is refused --
        it does not carry its own precision, so there is no honest way to store
        one.

        Must be deterministic. The same parameters and digits must give the
        same string every time, or verification means nothing: no wall clock,
        no unseeded randomness, no iteration over an unordered set.

        May return a mapping to carry annotations with the value::

            return {'number': x, 'comment': 'conjectural'}
        """
        raise NotImplementedError(
            '%s must implement value() or all_entries()'
            % (type(self).__name__,))

    def all_entries(self, digits: Optional[int] = None,
                    **bounds: Any) -> Entries:
        """Every entry, for tables that cannot produce one at a time.

        The default walks ``enumerate`` and calls ``value``, which is what most
        generators want. Override it when the values only come in bulk -- and
        accept that verification then has to recompute the whole table.
        """
        digits = self.digits if digits is None else digits
        entries = Entries(*self.parameters)
        for params in self.enumerate(**bounds):
            entries.add(**dict(params), **self._entry(params, digits))
        return entries

    def _entry(self, params, digits) -> Dict[str, Any]:
        produced = self.value(params, digits)
        if isinstance(produced, Mapping):
            return dict(produced)
        return {'number': produced}

    def environment(self) -> Dict[str, str]:
        """What produced these values, for a later run to be compared against.

        Verification exists to catch "the script or the software underneath it
        changed", so a mismatch is only useful if something recorded what the
        first run was.

        **Nothing here is collected or sent on its own.** It reports the Python
        and Sage versions, which are facts about the computation, and `publish`
        never calls it. There is no `pip freeze`: what is installed on
        somebody's machine is their business, most of it has nothing to do with
        the numbers, and publishing a package list because a script happened to
        run is not a trade anybody agreed to.

        Override it to add the versions that matter to *this* generator, and
        attach the result deliberately if it belongs with the table.
        """
        import platform
        import sys

        out = {'python': platform.python_version(),
               'numberdb': _version()}
        if 'sage' in sys.modules:
            try:
                from sage.version import version as sage_version
                out['sage'] = sage_version
            except Exception:
                pass
        return out


def _version():
    from . import __version__
    return __version__


class Report:
    """What a verification found.

    ``ok`` is true only when every entry checked matched. ``differing`` holds
    ``(identity, stored, recomputed)``, because "T42 disagrees" is not
    actionable and "entry n=17 was 3.14159 and is now 3.14158" is.
    """

    __slots__ = ('tid', 'checked', 'matched', 'differing', 'missing', 'extra')

    def __init__(self, tid, checked=0, matched=0, differing=None,
                 missing=None, extra=None):
        self.tid = tid
        self.checked = checked
        self.matched = matched
        self.differing = list(differing or [])
        self.missing = list(missing or [])
        self.extra = list(extra or [])

    @property
    def ok(self) -> bool:
        return not self.differing and not self.missing and not self.extra

    def __bool__(self) -> bool:
        return self.ok

    def __repr__(self):
        return ('<Report %s: %d/%d matched, %d differing, %d missing, '
                '%d extra>' % (self.tid, self.matched, self.checked,
                               len(self.differing), len(self.missing),
                               len(self.extra)))


def generate(generator: Generator, digits: Optional[int] = None,
             cache: Any = True, **bounds: Any) -> Entries:
    """Run a generator and return its entries.

    Computed values are kept on disk as they are produced, so a run that dies
    -- or is stopped, because somebody saw a wrong number go past -- can be
    resumed without recomputing what it already had. Pass ``cache=False`` to
    compute afresh, or a path to keep it somewhere particular.

    The cache is keyed by a fingerprint of the generator's own source, its
    parameters, the precision and the bounds. A changed generator therefore
    reads an empty cache rather than its predecessor's values: a cached number
    produced by code that has since changed is a wrong number wearing the
    authority of having been computed.
    """
    from ._cache import RunCache

    #A generator whose values only come in bulk cannot be cached entry by
    #entry, and pretending otherwise would mean calling an enumerate() it does
    #not have. It computes all of them or none, which is the cost it accepted
    #by not being able to produce one at a time.
    if cache is False or _is_bulk(generator):
        return generator.all_entries(digits=digits, **bounds)

    digits = generator.digits if digits is None else digits
    store = RunCache(generator, digits, bounds,
                     path=cache if isinstance(cache, str) else None)

    entries = Entries(*generator.parameters)
    for params in generator.enumerate(**bounds):
        identity = ','.join(str(params[name]) for name in generator.parameters)
        found = store.get(identity)
        if found is None:
            found = generator._entry(params, digits)
            #Written before anything else happens to it, because what this
            #protects against is the next line never running.
            store.put(identity, _plain(found, digits))
            entries.add(**dict(params), **found)
        else:
            entries.add(**dict(params), **found)
    return entries


def _is_bulk(generator):
    """Whether this generator produces everything at once."""
    return type(generator).all_entries is not Generator.all_entries


def _plain(entry, digits):
    """An entry as text, which is what can be written to a file and read back."""
    out = {}
    for key, value in entry.items():
        out[key] = (to_text(value, digits) if key == 'number'
                    else value if isinstance(value, (str, int, float, list))
                    else str(value))
    return out


def verify(generator: Generator, tid: Optional[str] = None,
           sample: Optional[int] = 10, digits: Optional[int] = None,
           client: Any = None, **bounds: Any) -> Report:
    """Recompute entries and compare them with what the table holds.

    Writes nothing, and needs no key: reading is public. This is the check that
    answers "does the code still produce the table", and it is the reason to insist on a per-entry ``value``: with
    one, ten entries can be checked in seconds; without one, the only way to
    ask is to regenerate a table that may take days, which means never.

    ``sample`` is how many entries to check, spread evenly through the table so
    the check is not confined to whichever end is cheapest. ``sample=None``
    checks all of them.
    """
    from . import table as fetch_table

    tid = tid or generator.tid
    if not tid:
        raise ValueError('which table? pass tid= or set it on the generator')

    digits = generator.digits if digits is None else digits
    stored = _stored_entries(fetch_table(tid, client=client))

    wanted = list(generator.enumerate(**bounds))
    if sample is not None and len(wanted) > sample:
        step = len(wanted) / float(sample)
        wanted = [wanted[int(i * step)] for i in range(sample)]

    report = Report(tid)
    for params in wanted:
        identity = ','.join(_text(params[name]) for name in generator.parameters)
        report.checked += 1
        if identity not in stored:
            report.missing.append(identity)
            continue
        recomputed = to_text(generator._entry(params, digits)['number'], digits)
        if stored[identity] == recomputed:
            report.matched += 1
        else:
            report.differing.append((identity, stored[identity], recomputed))
    return report


def _text(value):
    from ._write import _param_text

    return _param_text(value)


def _stored_entries(document: Mapping[str, Any]) -> Dict[str, str]:
    """A fetched table's entries as {identity: value}, in either stored form."""
    block = None
    for name in ('Numbers', 'Data'):
        if name in document:
            block = document[name]
            break
    if block is None:
        return {}

    out = {}  # type: Dict[str, str]

    if isinstance(block, list) and block and isinstance(block[0], Mapping) \
            and 'params' in block[0]:
        for record in block:
            params = record.get('params') or {}
            identity = ','.join(str(v) for v in params.values())
            out[identity] = _value_of(record)
        return out

    def walk(node, prefix):
        if isinstance(node, Mapping):
            if {'number', 'numbers', 'equals'} & set(node):
                inner = node.get('numbers')
                if isinstance(inner, Mapping):
                    walk(inner, prefix)
                    return
                out[','.join(prefix)] = _value_of(node)
                return
            for key, value in node.items():
                walk(value, prefix + (','.join(
                    p.strip() for p in str(key).split(',')),))
            return
        out[','.join(prefix)] = node if isinstance(node, str) else str(node)

    walk(block, ())
    return out


def _value_of(record):
    number = record.get('number')
    if isinstance(number, list):
        return number[0] if number else ''
    return number if isinstance(number, str) else str(number)


def publish(generator: Generator, tid: Optional[str] = None,
            digits: Optional[int] = None, message: str = '',
            batch: Optional[int] = None, run: str = '', preflight: bool = True,
            cache: Any = True, source_name: Optional[str] = 'generate.py',
            client: Any = None, **bounds: Any) -> Dict[str, Any]:
    """Send a generator's entries to its table.

    Entries only: the definition, the references and the tags are somebody's
    prose and a generator has no opinion about them.

    ``batch`` sends them as they are computed, in groups of that size, instead
    of computing everything and sending it at the end. That is what a generator
    of expensive values wants: a run that dies at entry 900 has already stored
    the first 899, and a rerun continues rather than starting again.

    All the batches of one run land in a single revision, so the history shows
    one act of regeneration rather than a thousand -- which is also what keeps
    the stored size sane, since every revision holds the whole document.
    """
    from ._write import submit_entries

    tid = tid or generator.tid
    if not tid:
        raise ValueError('which table? pass tid= or set it on the generator')

    #Before computing anything. A generator may run for hours, and "no API key
    #was set" is knowable in the first second -- as are "this account may not
    #write yet" and "there is no table T42". Finding out at the end costs
    #whatever the computation cost.
    if preflight:
        from ._write import check_writable

        check_writable(tid, client=client)

    run = run or _run_name(generator)

    #Compute first, send once. The network is then needed at one moment
    #instead of continuously: a connection that drops during a computation
    #costs nothing, and a submission that fails can simply be repeated because
    #every value is still on the disk.
    #
    #It also makes stopping deliberate. A run interrupted half way has
    #published nothing, and whoever stopped it decides whether to send what is
    #there.
    if not batch:
        from ._write import submit_entries

        entries = generate(generator, digits=digits, cache=cache, **bounds)
        answer = submit_entries(tid, entries, message=message,
                                produced_by=type(generator).__name__,
                                run=run, client=client)
        _attach_source(generator, tid, run, client, source_name)
        return answer

    #Sending as it goes, for a caller that wants the values visible early. The
    #lease then matters, because between one batch and the next anybody else
    #may write.
    from ._write import Lease

    with Lease(tid, run=run, note='generated by %s' % (type(generator).__name__,),
               client=client):
        answer = _publish_held(generator, tid, digits, message, batch, run,
                               client, cache, bounds)
        _attach_source(generator, tid, run, client, source_name)
        return answer


def _publish_held(generator, tid, digits, message, batch, run, client, cache,
                  bounds):
    from ._cache import RunCache
    from ._write import submit_entries

    if not batch:
        entries = generate(generator, digits=digits, **bounds)
        return submit_entries(tid, entries, message=message,
                              produced_by=type(generator).__name__,
                              run=run, client=client)

    digits = generator.digits if digits is None else digits
    store = (RunCache(generator, digits, bounds,
                      path=cache if isinstance(cache, str) else None)
             if cache is not False and not _is_bulk(generator) else None)
    pending = Entries(*generator.parameters)
    sent = {'entries': 0, 'batches': 0}
    answer = {}

    def flush():
        nonlocal pending
        if not len(pending):
            return
        result = _with_retry(
            lambda: submit_entries(tid, pending, message=message,
                                   produced_by=type(generator).__name__,
                                   upsert=True, run=run, client=client))
        sent['entries'] += len(pending)
        sent['batches'] += 1
        answer.update(result)
        pending = Entries(*generator.parameters)

    if _is_bulk(generator):
        #Nothing to stream: it is all computed or none of it is.
        for record in generator.all_entries(digits=digits, **bounds):
            pending._records.append(dict(record))
        flush()
        answer.update(sent)
        answer['run'] = run
        return answer

    for params in generator.enumerate(**bounds):
        identity = ','.join(str(params[name]) for name in generator.parameters)
        found = store.get(identity) if store is not None else None
        if found is None:
            found = generator._entry(params, digits)
            if store is not None:
                store.put(identity, _plain(found, digits))
        pending.add(**dict(params), **found)
        if len(pending) >= batch:
            flush()
    flush()

    answer.update(sent)
    answer['run'] = run
    return answer


def _with_retry(send, attempts=4):
    """Send a batch, waiting and trying again when the table is busy.

    Writes to one table are serialised, so a batch can be told that somebody
    else is writing just now. For a run of hours that is a normal event and not
    a failure: the values are already computed and resending them costs
    nothing, whereas losing them costs whatever they took to produce.

    Only for "busy" -- a refused document or a rejected key is not going to
    become true by being repeated.
    """
    import time

    from ._errors import RateLimited

    for attempt in range(attempts):
        try:
            return send()
        except RateLimited as busy:
            if attempt == attempts - 1:
                raise
            time.sleep(getattr(busy, 'retry_after', None) or 2 * (attempt + 1))
    raise AssertionError('unreachable')


def _attach_source(generator, tid, run, client, source_name):
    """Send the files that produced these numbers, in the same revision.

    What to send is declared on the generator rather than discovered: a
    directory sweep would collect whatever else happened to be sitting there,
    which is nobody's intention and sooner or later somebody's private working
    file. With nothing declared it sends the generator's own source, which is
    the one file certainly relevant.

    Best effort. A run whose numbers are stored and whose source could not be
    read has still done the useful part, and failing at the end over a missing
    file would be a poor trade.
    """
    import inspect
    import os

    from ._write import attach

    def send(name, body):
        try:
            #Stored under the bare name: a table's files are flat.
            attach(tid, os.path.basename(name), body, run=run, client=client,
                   message='a file that produced these entries')
        except Exception:
            pass

    declared = tuple(getattr(generator, 'files', ()) or ())
    if declared:
        try:
            beside = os.path.dirname(inspect.getfile(type(generator)))
        except (OSError, TypeError):
            beside = '.'
        for named in declared:
            path = named if os.path.isabs(named) else os.path.join(beside, named)
            try:
                with open(path, 'r', encoding='utf8') as handle:
                    send(named, handle.read())
            except OSError:
                continue
        return

    if not source_name:
        return
    try:
        source = inspect.getsource(type(generator))
    except (OSError, TypeError):
        return
    send(source_name, source)


def _run_name(generator):
    """A name for one run of this generator.

    Derived from the generator and the moment it started, so two runs of the
    same script do not amend each other's revision and one run's batches all
    find their own.
    """
    import time

    return '%s-%d' % (type(generator).__name__[:40], int(time.time()))
