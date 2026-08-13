"""The one way a program puts numbers into a table.

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
        table = 'T42'
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

    ZetaAtIntegers().publish()

Generating is iterating; extending is iterating further; more precision is a
larger ``digits``. And verifying is *sampling* -- ten entries rather than a
thousand -- which matters because several of these tables take hours or days to
produce in full. A check that takes seconds is a check that gets run.

**There is one way to send them, and it does the careful things itself.** What
used to be arguments -- when to cache, when to batch, what to call the run,
whether to attach the source, whether to check permission first -- had a right
answer every time, and a right answer that has to be typed is a way of getting
it wrong. Caching, streaming, naming the run and attaching the code are not
preferences and are no longer asked about.

They are methods rather than functions taking a generator, so the whole of
writing is one public name. A generator is *for* a table, it knows which, and
what you can do with it is what it offers: ``publish``, ``preview``, ``verify``.

What remains to be asked is intent, because nothing else can determine it:
whether values already stored may be replaced, contradicted, coarsened or
removed. Each of those defaults to the conservative choice, and a refusal names
the argument that permits the operation.

Some tables cannot be computed one entry at a time: zeros found by a sweep,
values lifted from another database. Those override ``all_entries`` instead and
simply do not get cheap sampling. That is a real limitation, and better stated
than designed around.
"""

from __future__ import annotations

from typing import Any, Dict, Iterator, List, Mapping, Optional, Tuple

from . import _compare
from ._errors import DisagreementError
from ._write import DIGITS, Entries, to_text

__all__ = ['Generator', 'PublishOutcome', 'VerifyReport']

#: Entries held back before a batch is sent. Small enough that a crash costs
#: little, large enough that a thousand cheap values are not a thousand
#: requests.
BATCH_ENTRIES = 100

#: ...and sent anyway after this long, however few there are. Some tables take
#: hours for one entry, and waiting for a hundred of those before storing
#: anything would be waiting for a week.
BATCH_SECONDS = 60

#: How well a table's digits are known, weakest last.
#:
#: The distinction this whole attribute exists for: a hundred digits can be
#: proven, believed on a stated assumption, checked by agreement, or simply
#: assumed, and a table that does not say which presents all four identically.
#: See docs/design/rigour.md.
RIGOUR_LEVELS = (
    'exact',
    'proven',
    'assumed-bound',
    'heuristic (agreement-checked)',
    'heuristic',
)


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

    #: Which table this generates. A property of the generator, not of the
    #: call: a generator is written *for* a table, and one pointed at another
    #: would be writing its numbers under somebody else's parameters.
    table: Optional[str] = None

    #: Parameter names, in identity order. Empty for a table of bare values.
    parameters: tuple = ()

    #: What the values are: 'Z', 'Q', 'R', 'C', 'Qp', 'Z[]', 'Q[]'. The exact
    #: ones ignore ``digits``, because an exact value has no precision to
    #: choose -- writing fewer digits of a polynomial does not round it, it
    #: makes it a different polynomial.
    type: str = 'R'

    #: Significant **decimal** digits every entry is expected to carry. A
    #: hundred identifies any number in this database; more earns its place
    #: only when it was expensive to obtain.
    #:
    #: This is a promise that is checked. A value that comes back shorter stops
    #: the run, and the two things that cause it are worth telling apart: a
    #: field built in digits where Sage counts bits, which is a mistake; and a
    #: computation that lost more precision than the working field allowed for,
    #: which is ordinary and is fixed by computing wider. An entry that really
    #: is known no better says so for itself, by returning
    #: ``{'number': x, 'digits': 8}``.
    digits: int = DIGITS

    #: Which files to store with the numbers, named rather than guessed.
    #:
    #: Empty means "the file this generator is defined in", which is what most
    #: runs want -- the whole file, not the class, since the function a value
    #: was computed with usually sits beside the class rather than inside it.
    #: Name them when the computation is spread over several files, or when a
    #: note or a table of inputs belongs beside the values -- guessing at that
    #: from the directory would sweep up whatever else happened to be sitting
    #: there, which is nobody's intention and sooner or later somebody's
    #: private working file.
    #:
    #: Naming any file replaces the automatic one, so a generator that lists
    #: its helpers must list itself among them.
    #:
    #: Paths are read relative to the file the generator is defined in and
    #: stored under their bare names: a table's files are flat.
    files: tuple = ()

    #: How an approximate value is written. ``'decimal'`` is this database's
    #: convention and what almost all of it holds: ``3.14`` **is** the interval
    #: (3.13, 3.15) -- the digits written are known and the last is uncertain
    #: by one. No marker, and in particular not Sage's ``3.14?``, which appears
    #: nowhere in the corpus.
    #:
    #: ``'ball'`` writes ``3.14159 +/- 2.8e-25`` instead, for a table that
    #: records its radius rather than implying it. A thousand values are
    #: written that way and their generators should keep writing them that way.
    format: str = 'decimal'

    #: How well this generator's digits are known. One of `RIGOUR_LEVELS`.
    #:
    #: ``'proven'`` is the default and is enforced: a value must then be either
    #: exact or an interval of nonzero width, because those are the only two
    #: things that carry their own error. A point value of approximate type is
    #: refused -- wrapping a fixed-precision result in an interval field
    #: produces an interval of width zero, which claims, in the one type whose
    #: purpose is to carry error, that there is none. Twenty-nine tables in
    #: this corpus were built that way and nothing ever noticed.
    #:
    #: Say otherwise when it is otherwise. A computation that cannot be bounded
    #: is not a worse contribution, it is a differently qualified one, and the
    #: table will say so where a reader can see it.
    rigour: str = 'proven'

    EXACT_TYPES = frozenset(['Z', 'Q', 'Z[]', 'Q[]'])

    def digits_for(self, params: Mapping[str, Any]) -> int:
        """How many digits *this* entry should carry. Override to vary it.

        The default is the same for every entry -- ``self.digits`` -- which is
        what a table of one kind of thing wants. Override when the table is
        not: entries that get expensive further along, or a family where the
        first few are worth more precision than the rest.

            def digits_for(self, params):
                return 100 if params['n'] < 10 else 20

        This is the number handed to ``value``, so a generator sizes its
        working precision from it, and the number that entry is then held to.
        An entry that turns out to be known no better than it hoped says so
        when it returns: ``{'number': x, 'digits': 8}``.
        """
        return self.digits

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

        Compute in whatever you like -- ``RealIntervalField``, ``RealBallField``
        and their complex counterparts all arrive the same way. An approximate
        real is stored in one form, ``3.14159?``, meaning the digits written
        are known and the last is uncertain by one.

        Must be deterministic. The same parameters and digits must give the
        same string every time, or verification means nothing: no wall clock,
        no unseeded randomness, no iteration over an unordered set.

        May return a mapping to carry annotations with the value::

            return {'number': x, 'comment': 'conjectural'}

        ``digits`` in that mapping says this entry is known no better, and is
        how a table of varying precision is written: everything else is
        measured against the generator's own ``digits`` and refused if it falls
        short.

            return {'number': x, 'digits': 8}

        The ``digits`` handed in is **decimal digits**, because that is how
        this database writes numbers, and it is how many to *write* -- not how
        many to compute with. Sage's interval fields are built in bits, so the
        units have to be converted; and the field has to be built **wider than
        the answer**, because arithmetic loses low bits:

            field = RealIntervalField(numberdb.bits(digits))          # start here
            field = RealIntervalField(numberdb.bits(digits, losing=512))   # cancels

        How much wider depends on the computation and cannot be known in
        advance, so it is yours to choose. `publish` measures what each value
        actually pinned down and refuses the run if it fell short, which is
        what turns the choice into something you find out about.
        """
        raise NotImplementedError(
            '%s must implement value() or all_entries()'
            % (type(self).__name__,))

    def all_entries(self, digits: Optional[int] = None,
                    **bounds: Any) -> Iterator[Tuple[Mapping[str, Any], Any]]:
        """Yield ``(params, value)`` for every entry, for tables that cannot
        produce one at a time.

        The default walks ``enumerate`` and calls ``value``, which is what most
        generators want. Override it when the values only come in bulk -- and
        accept that verification then has to recompute the whole table.

        Yield rather than return where you can: what is yielded is cached and
        sent as it arrives, so a sweep that dies half way keeps what it found.
        """
        digits = self.digits if digits is None else digits
        for params in self.enumerate(**bounds):
            yield params, self.value(params, digits)

    def _entry(self, params, digits) -> Dict[str, Any]:
        return _as_entry(self.value(params, digits))

    #-- what you call ---------------------------------------------------

    def publish(self, only: Any = None, message: str = '',
                overwrite: bool = True, correcting: bool = False,
                lowering: bool = False, removing: bool = False,
                restating: bool = False,
                client: Any = None, **bounds: Any) -> PublishOutcome:
        """Send this generator's entries to its table. The whole of writing.

        Entries only: the definition, the references and the tags are somebody's
        prose, a generator has no opinion about them, and there is deliberately
        no way to send them from here. Prose is edited on the site, where a
        person signs it.

        Caching, streaming, naming the run and attaching the code that produced
        the numbers all happen without being asked for. What a run may do to
        values that already exist is asked, because only the person running it
        knows:

        ``overwrite`` (default true) lets recomputed values replace stored ones.
        Set it false to add what is missing and leave the rest untouched --
        which also skips computing those entries at all, so extending a table
        of a thousand expensive values by a hundred costs a hundred
        computations.

        ``correcting`` allows values that **contradict** what is stored.
        Without it, the first contradiction stops the run before anything is
        sent, which costs one entry rather than a day: a generator that has
        started producing different numbers is usually a broken environment,
        not a discovery. When it really is a discovery, this says so.

        ``lowering`` allows values with **fewer digits** than are stored. The
        stored precision may well have been unjustified, but throwing away
        digits somebody computed should be something they meant.

        ``removing`` deletes entries this run did not produce. Off by default:
        a run over `n = 2..100` has said nothing whatever about `n = 500`, and
        treating that silence as a deletion is how a narrowed bound quietly
        empties a table. What would have gone is listed in
        ``outcome.left_alone``.

        ``restating`` rewrites entries whose stored value says the same thing
        to the same precision in different digits. Off by default, and this is
        the argument that decides whether re-running a generator is a quiet
        no-op or a mass edit.

        The case it exists for: a value stored as ``...4689`` and recomputed as
        ``...4690``, because the old script truncated the last digit and this
        one rounds it. Under this database's convention both denote intervals
        that contain the number, to the same number of digits, so neither is
        more true than the other -- and the first table converted from an old
        script had 237 entries of exactly that kind out of 501. Rewriting them
        says nothing new about any number, while marking every one of them
        edited and costing anyone who cited one a moment of doubt.

        A value that is genuinely *better* -- more digits, a refinement -- is
        written whatever this says, because that is a real improvement rather
        than a restatement. Ones left alone are listed in ``outcome.agreed``.

        ``only`` computes and sends *some* entries and leaves the rest alone:
        the parameters to recompute, as mappings or as identities.

            generator.publish(only=[{'n': 17}, {'n': 42}])
            generator.publish(only=['17', '42'])
            generator.publish(only=generator.verify().to_fix())

        An identity is text, so its parameters arrive as text; a mapping
        arrives as it was given. Prefer mappings when the generator wants a
        number, and `VerifyReport.to_fix` hands back exactly that.

        Anything else is passed to ``enumerate``, so a bound is given here:
        ``generator.publish(limit=2000)``.
        """
        return _publish(self, only=only, message=message, overwrite=overwrite,
                        correcting=correcting, lowering=lowering,
                        removing=removing, restating=restating,
                        preview=False, client=client, **bounds)

    def preview(self, only: Any = None, overwrite: bool = True,
                correcting: bool = False, lowering: bool = False,
                removing: bool = False, restating: bool = False,
                client: Any = None, **bounds: Any) -> PublishOutcome:
        """Compute everything, send nothing, and report what `publish` would do.

        **This asks whether the generator is right.** `verify` asks whether the
        table is. The two questions look alike from a distance and want
        opposite behaviour up close, which is why both exist:

        * a preview is exhaustive and stops at the first contradiction,
          because you are about to write and something is wrong;
        * a verification samples and collects every disagreement it finds,
          because you are auditing and want the list.

        The same refusals apply as in `publish` -- a contradiction or a loss of
        precision is exactly what you ran this to find out about. The values
        are cached, so publishing afterwards does not compute them again.

        There is no ``preview=`` flag on `publish`, so there is no such thing
        as a publish that does not publish.
        """
        return _publish(self, only=only, overwrite=overwrite,
                        correcting=correcting, lowering=lowering,
                        removing=removing, restating=restating,
                        preview=True, client=client, **bounds)

    def verify(self, sample: Optional[int] = 10,
               digits: Optional[int] = None, client: Any = None,
               **bounds: Any) -> VerifyReport:
        """Recompute entries and compare them with what the table holds.

        **This asks whether the table is right** -- whether what is stored is
        still what this code produces, after the script or the software
        underneath it has changed. `preview` asks the other question, whether
        a generator about to write is right, and stops at the first
        contradiction rather than collecting them.

        Writes nothing, and needs no key: reading is public. It is the
        reason to insist on a per-entry ``value``: with one, ten entries can be
        checked in seconds; without one, the only way to ask is to regenerate a
        table that may take days, which means never.

        ``sample`` is how many entries to check, spread evenly through the
        table so the check is not confined to whichever end is cheapest.
        ``sample=None`` checks all of them.

        Differing *precision* is not a difference. A table built at 20 digits
        and checked by a generator running at 100 agrees with itself, and
        reporting those as errors would propose rewriting a table that was
        never wrong.
        """
        return _verify(self, sample=sample, digits=digits, client=client,
                       **bounds)

    #: Names this class needs for itself. A subclass defining one of them would
    #: replace the way its own numbers get published or checked, and nothing
    #: would say so at the point it mattered.
    RESERVED = ('publish', 'preview', 'verify')

    def __init_subclass__(cls, **kwargs):
        """Refuse a subclass that shadows the machinery, when it is written.

        ``verify`` is exactly the word a mathematician reaches for when writing
        their own check, and quietly overriding it would leave
        ``generator.verify()`` doing something else entirely. Raising here
        means finding out at the ``class`` statement rather than at the end of
        a long run.
        """
        super().__init_subclass__(**kwargs)
        for name in Generator.RESERVED:
            if name in cls.__dict__:
                raise TypeError(
                    '%s defines %s(), which is how a generator is published or '
                    'checked against its table. Give yours another name -- '
                    '%s_entries(), say -- so both survive.'
                    % (cls.__name__, name, name))

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


def _as_entry(produced) -> Dict[str, Any]:
    """One entry's value, however the generator chose to return it."""
    if isinstance(produced, Mapping):
        return dict(produced)
    return {'number': produced}


class PublishOutcome:
    """What a run did to a table, or -- under ``preview`` -- would have done.

    The counts are the point. A run that reports 100 added and 0 updated did
    what extending a table looks like; one that reports 0 added and 900
    updated rewrote a table somebody may have been reading, and that should be
    visible without going and looking.
    """

    __slots__ = ('table', 'run', 'added', 'updated', 'unchanged', 'agreed',
                 'left_alone', 'removed', 'files', 'revision', 'applied')

    def __init__(self, table, run=''):
        self.table = table
        self.run = run
        #: Identities this run put in the table for the first time.
        self.added = []          # type: List[str]
        #: Identities whose stored value this run changed.
        self.updated = []        # type: List[str]
        #: Identities this run recomputed and found already correct.
        self.unchanged = []      # type: List[str]
        #: Identities whose stored value says the same thing to the same
        #: precision, in different digits, and which were therefore left as
        #: they are. See ``restating``.
        self.agreed = []         # type: List[str]
        #: Identities in the table that this run did not produce, and so did
        #: not touch. Reported rather than deleted -- a run that computed
        #: n = 2..100 has said nothing at all about n = 500.
        self.left_alone = []     # type: List[str]
        #: Identities deleted, which only ``removing=True`` can produce.
        self.removed = []        # type: List[str]
        #: Files stored alongside, by name.
        self.files = []          # type: List[str]
        #: The revision the server recorded, or None under ``preview``.
        self.revision = None
        #: False under ``preview``: nothing was sent.
        self.applied = False

    @property
    def entries(self) -> int:
        """How many entries this run produced."""
        return (len(self.added) + len(self.updated) + len(self.unchanged)
                + len(self.agreed))

    def __repr__(self):
        return ('<PublishOutcome %s: %d added, %d updated, %d unchanged, '
                '%d agreed, %d left alone, %d removed%s>'
                % (self.table, len(self.added), len(self.updated),
                   len(self.unchanged), len(self.agreed), len(self.left_alone),
                   len(self.removed), '' if self.applied else ', not sent'))


class VerifyReport:
    """What a verification found.

    ``ok`` is true only when nothing contradicted and nothing was missing.
    ``differing`` holds ``(identity, stored, recomputed)``, because "T42
    disagrees" is not actionable and "entry n=17 was 3.14159 and is now
    3.14158" is.

    A stored value written to fewer digits than the run produces is not a
    disagreement and is not listed there -- it is the same number, known
    better. Those land in ``refined``, and the reverse in ``coarser``.
    """

    __slots__ = ('table', 'checked', 'matched', 'differing', 'missing',
                 'extra', 'params', 'coarser', 'refined')

    def __init__(self, table, checked=0, matched=0, differing=None,
                 missing=None, extra=None):
        self.table = table
        self.checked = checked
        self.matched = matched
        self.differing = list(differing or [])
        self.missing = list(missing or [])
        self.extra = list(extra or [])
        #: Identities where the run produced more digits than are stored.
        self.refined = []        # type: List[str]
        #: Identities where the run produced fewer -- consistent, but a loss
        #: if it were published.
        self.coarser = []        # type: List[str]
        #: The parameters of every entry named above, as the generator
        #: produced them. `publish(only=report.to_fix())` is then the natural
        #: next step and does not fail on a type.
        self.params = {}

    def to_fix(self):
        """The parameters of every entry that differed or was missing.

        Feeds straight back: `numberdb.publish(g, only=report.to_fix())`
        recomputes exactly those and leaves the rest of the table alone.
        """
        wanted = [identity for identity, _stored, _now in self.differing]
        wanted += list(self.missing)
        return [self.params[identity] for identity in wanted
                if identity in self.params]

    @property
    def ok(self) -> bool:
        return not self.differing and not self.missing and not self.extra

    def __bool__(self) -> bool:
        return self.ok

    def __repr__(self):
        return ('<VerifyReport %s: %d/%d matched, %d differing, %d missing, '
                '%d extra>' % (self.table, self.matched, self.checked,
                               len(self.differing), len(self.missing),
                               len(self.extra)))


def _verify(generator, sample=10, digits=None, client=None,
            **bounds) -> VerifyReport:
    """Behind `Generator.verify`, which carries the documentation."""
    from . import table as fetch_table

    table = _table_of(generator)
    digits = generator.digits if digits is None else digits
    stored = _stored_entries(fetch_table(table, client=client))

    wanted = list(generator.enumerate(**bounds))
    if sample is not None and len(wanted) > sample:
        step = len(wanted) / float(sample)
        wanted = [wanted[int(i * step)] for i in range(sample)]

    report = VerifyReport(table)
    for params in wanted:
        identity = _identity(params, generator.parameters)
        report.checked += 1
        if identity not in stored:
            report.missing.append(identity)
            report.params[identity] = dict(params)
            continue

        wanted = _digits_for(generator, params, digits)
        recomputed = to_text(generator._entry(params, wanted)['number'],
                             wanted, generator.format)
        verdict = _compare.compare(stored[identity], recomputed)
        if verdict == _compare.CONTRADICTS:
            report.differing.append((identity, stored[identity], recomputed))
            #Kept as the generator produced them, not as text. An identity is
            #text by nature, and handing text back to a generator that expects
            #an integer makes the natural next step -- recompute what differs
            #-- fail on a type rather than on a number.
            report.params[identity] = dict(params)
            continue

        report.matched += 1
        if verdict == _compare.REFINES:
            report.refined.append(identity)
        elif verdict == _compare.COARSENS:
            report.coarser.append(identity)
        if verdict in (_compare.REFINES, _compare.COARSENS):
            report.params[identity] = dict(params)
    return report


def _publish(generator, only=None, message='', overwrite=True,
             correcting=False, lowering=False, removing=False,
             restating=False, preview=False, client=None,
             **bounds) -> PublishOutcome:
    """Behind `Generator.publish` and `Generator.preview`, which carry the
    documentation. ``preview`` computes and compares but sends nothing."""
    from ._cache import RunCache

    table = _table_of(generator)
    if removing and only is not None:
        raise ValueError(
            'removing= deletes what this run did not produce, and a run given '
            'only= did not produce almost anything. Naming entries and '
            'emptying the table are different acts.')

    digits = generator.digits
    files = _source_files(generator)

    #Before computing anything. A generator may run for hours, and "no API key
    #was set" is knowable in the first second -- as are "this account may not
    #write yet" and "there is no table T42". Finding out at the end costs
    #whatever the computation cost.
    if not preview:
        from ._write import check_writable

        check_writable(table, client=client)

    stored = _current_entries(table, client)
    outcome = PublishOutcome(table, run='' if preview else _run_name(generator))

    #Keyed by the bytes that will be attached, so a cached value can never
    #outlive the code that made it: editing any attached file changes the
    #fingerprint, and a changed fingerprint reads an empty cache rather than
    #its predecessor's numbers.
    cache = RunCache(generator, digits, bounds, source=_digest(files),
                     read=only is None)

    produced = Entries(*generator.parameters) if removing else None
    sender = _Sender(table, outcome, message, generator, client, preview)

    skip = (lambda identity: identity in stored) if not overwrite else None
    seen = set()
    for identity, params, entry, asked in _stream(generator, only, digits,
                                                  bounds, cache, skip):
        seen.add(identity)
        entry = dict(entry)
        #An entry may declare that it is less precise on purpose -- a constant
        #that is only known to eight digits does not become wrong by being
        #stored to eight. Anything else is measured against what the generator
        #asked for, per entry.
        wanted = int(entry.pop('digits', asked) or asked)
        #Converted once, here, and sent as text. Entries.add would otherwise
        #convert the raw value again with its own defaults -- a hundred digits
        #and the decimal form -- so the string that was checked for
        #contradictions and precision was not the string that reached the
        #table, and a generator asking for twenty digits stored a hundred.
        _check_rigour(generator, table, identity, entry['number'])
        entry['number'] = _written(entry['number'], wanted, generator.format)
        text = (entry['number'][0] if isinstance(entry['number'], list)
                else entry['number'])
        _check_precision(table, identity, text, wanted, lowering)
        send = True
        if identity in stored:
            _judge(table, identity, stored[identity], text,
                   correcting, lowering, sender)
            verdict = _compare.compare(stored[identity], text)
            if verdict == _compare.SAME:
                outcome.unchanged.append(identity)
                #Nothing to say. Sending a value identical to the stored one
                #is a write that changes nothing, and a thousand of them is a
                #revision that changes nothing.
                send = False
            elif verdict == _compare.AGREES and not restating:
                #Different digits, same claim, same precision -- the usual
                #cause being that the two disagree about the last digit
                #because one rounds and the other truncates. Under this
                #database's convention both denote intervals that contain the
                #value, so rewriting says nothing new about the number while
                #marking the entry edited and costing whoever cited it a
                #moment of doubt.
                outcome.agreed.append(identity)
                send = False
            else:
                outcome.updated.append(identity)
        else:
            outcome.added.append(identity)

        #Always, even when nothing is sent: this is the full replacement set
        #that `removing` writes, and leaving out the entries this run chose
        #not to restate would delete them.
        if produced is not None:
            produced.add(**dict(params), **entry)
        if send:
            sender.add(params, entry)

    outcome.left_alone = [identity for identity in stored
                          if identity not in seen]

    if removing and outcome.left_alone:
        #Sent whole, as a replacement, once everything is computed: streaming a
        #replacement would delete the not-yet-computed rest of the table
        #between the first batch and the second.
        outcome.removed = list(outcome.left_alone)
        outcome.left_alone = []
        sender.replace_with(produced)
    else:
        sender.flush()

    if not preview:
        outcome.files = _attach(generator, table, outcome.run, client, files,
                                message=message)
        outcome.applied = True
    return outcome


def _carries_its_own_error(value) -> bool:
    """Whether ``value`` says how wrong it might be.

    True for an exact number -- nothing to be wrong about -- and for an
    interval or ball of nonzero width. False for a float, a string, and for an
    interval of width zero, which is what wrapping a fixed-precision result in
    an interval field produces.
    """
    from fractions import Fraction

    if isinstance(value, (int, Fraction)):
        return True
    if isinstance(value, (str, float)):
        return False
    lower, upper = getattr(value, 'lower', None), getattr(value, 'upper', None)
    if lower is not None and upper is not None:
        try:
            return lower() != upper()
        except TypeError:
            return lower != upper
    #A Sage Integer, Rational or polynomial. `is_exact()` lives on the parent
    #rather than on the element -- ZZ(2) has no such attribute, ZZ does -- and
    #asking the element instead is how the first version of this refused every
    #exact value a Sage generator produced.
    #
    #Checked after the endpoints, deliberately: an interval field is not exact,
    #so a point interval still reaches the refusal it deserves.
    parent = getattr(value, 'parent', None)
    if parent is not None:
        try:
            exact = getattr(parent(), 'is_exact', None)
            if exact is not None and exact():
                return True
        except (TypeError, AttributeError):
            pass
    return False


def _check_rigour(generator, table, identity, value):
    """Refuse a value that cannot support the rigour the generator claims.

    Only ``proven`` is enforceable, and only in one direction: a value that
    carries no error cannot have a proven one. The weaker levels are the
    author's word, which is the whole content of them.
    """
    level = getattr(generator, 'rigour', 'proven')
    if level not in RIGOUR_LEVELS:
        raise ValueError(
            '%s.rigour is %r, which is not one of: %s'
            % (type(generator).__name__, level, ', '.join(RIGOUR_LEVELS)))
    if level not in ('exact', 'proven'):
        return
    if generator.type in Generator.EXACT_TYPES:
        return
    if _carries_its_own_error(value):
        return
    raise DisagreementError(
        '%s entry %s: rigour is %r, and this value carries no error of its '
        'own -- it is a point, a float or a string. Wrapping a '
        'fixed-precision result in an interval field does not make it an '
        'enclosure: the interval has width zero, which says the value is '
        'exact, and the digits then written are however many were asked for. '
        'Either compute in interval arithmetic throughout, or say what this '
        'actually is: rigour = %r, or %r if two precisions were compared. If '
        'the value really is exact, return it as an exact number -- an int or '
        'a Fraction -- rather than as an interval around one.'
        % (table, identity, level, 'heuristic',
           'heuristic (agreement-checked)'),
        identity=identity, stored='', produced=str(value)[:80],
        verdict='unbounded')


def _check_precision(table, identity, text, wanted, lowering):
    """Whether this value carries the digits the generator asked for.

    Short values are the quiet failure of this whole interface, and there are
    two ways to arrive at one.

    The mundane one: Sage's interval fields are built in **bits** and this
    database counts **decimal digits**, so ``RealIntervalField(digits)`` --
    which reads perfectly well -- delivers about thirty digits where a hundred
    were meant.

    The ordinary one, which is not a mistake at all: **arithmetic loses
    precision**. A field built at the width of the intended answer does not
    produce an answer that wide, and how much is lost depends on the
    computation -- a cancellation can cost hundreds of bits, a long product a
    handful. Nobody can know the figure in advance, which is why the working
    precision is the author's to choose and why this check exists to measure
    what came out. The remedy is a wider field, raised until the digits appear.

    ``numberdb.bits(digits)`` converts the units and adds a small guard. It is
    the right starting point and emphatically not a guarantee: for anything
    that cancels it will be nowhere near enough, and the guard is a parameter
    -- ``bits(digits, losing=512)`` -- for exactly that reason.
    """
    if lowering or not _compare.counts_digits(text):
        return
    got = _compare.digits_of(text)
    if got >= wanted:
        return
    raise DisagreementError(
        '%s entry %s: %d digits were asked for and this value carries %d. '
        'Two things cause that. Either the working precision was too low for '
        'this computation -- arithmetic loses low bits, by an amount that '
        'depends on the problem and cannot be known in advance, so the field '
        'has to be built wider than the answer is meant to be: try '
        'numberdb.bits(%d, losing=%d) or more, and raise it until the digits '
        'come back. Or the field was built in digits where Sage counts bits, '
        'which is the same mistake by a factor of about 3.3 -- %d digits is '
        '%d bits before any guard at all. If instead this entry is genuinely '
        'known no better, say so where it is produced -- '
        'return {"number": x, "digits": %d} -- or pass lowering=True for a '
        'run of them.'
        % (table, identity, wanted, got,
           wanted, max(64, 4 * (wanted - got)),
           wanted, int(_bits(wanted) - 16), got),
        identity=identity, stored='', produced=text, verdict='short')


def _bits(digits):
    from ._write import bits

    return bits(digits)


def _judge(table, identity, stored_text, produced_text, correcting, lowering,
           sender):
    """Whether this value may replace the one already there.

    Checked as each value is computed rather than at the end, so a run whose
    first entry already contradicts the table stops having spent one entry.
    """
    verdict = _compare.compare(stored_text, produced_text)

    if verdict == _compare.CONTRADICTS and not correcting:
        raise DisagreementError(
            '%s entry %s: the table holds %s and this run produced %s. They '
            'cannot both be right, so nothing further was sent%s. If the '
            'stored values are wrong and this run is meant to replace them, '
            'pass correcting=True.'
            % (table, identity, _short(stored_text), _short(produced_text),
               sender.so_far()),
            identity=identity, stored=stored_text, produced=produced_text,
            verdict=verdict)

    if verdict == _compare.COARSENS and not lowering:
        raise DisagreementError(
            '%s entry %s: the table holds %d digits and this run produced %d. '
            'The values agree, so nothing further was sent%s. If the stored '
            'precision was never justified, pass lowering=True.'
            % (table, identity, _compare.digits_of(stored_text),
               _compare.digits_of(produced_text), sender.so_far()),
            identity=identity, stored=stored_text, produced=produced_text,
            verdict=verdict)


def _short(text, width=40):
    text = str(text)
    return text if len(text) <= width else text[:width] + '...'


class _Sender:
    """Entries on their way to the table, in batches of one run.

    Batched by count *and* by time. A thousand cheap values should not be a
    thousand requests, and one value that took three hours should not wait for
    ninety-nine more before it is stored anywhere.
    """

    def __init__(self, table, outcome, message, generator, client, preview):
        import time

        self.table = table
        self.outcome = outcome
        self.message = message
        self.generator = generator
        self.client = client
        self.preview = preview
        self.pending = Entries(*generator.parameters)
        self.clock = time.monotonic
        self.last = self.clock()
        self.sent = 0

    def add(self, params, entry):
        self.pending.add(**dict(params), **entry)
        if (len(self.pending) >= BATCH_ENTRIES
                or self.clock() - self.last >= BATCH_SECONDS):
            self.flush()

    def flush(self):
        if self.preview or not len(self.pending):
            return
        from ._write import submit_entries

        answer = _with_retry(
            lambda: submit_entries(
                self.table, self.pending, message=self._message(),
                produced_by=type(self.generator).__name__,
                upsert=True, run=self.outcome.run,
                rigour=getattr(self.generator, 'rigour', ''),
                client=self.client))
        self.sent += len(self.pending)
        self.outcome.revision = answer.get('revision', self.outcome.revision)
        self.pending = Entries(*self.generator.parameters)
        self.last = self.clock()

    def replace_with(self, entries):
        """The whole table, once, for a run that means to delete what it did
        not produce."""
        if self.preview:
            return
        from ._write import submit_entries

        answer = _with_retry(
            lambda: submit_entries(
                self.table, entries, message=self._message(),
                produced_by=type(self.generator).__name__,
                upsert=False, run=self.outcome.run,
                rigour=getattr(self.generator, 'rigour', ''),
                client=self.client))
        self.sent = len(entries)
        self.outcome.revision = answer.get('revision', self.outcome.revision)
        self.pending = Entries(*self.generator.parameters)

    def so_far(self):
        """What a refusal has to admit was already stored."""
        if not self.sent:
            return ''
        return (' (%d entries of this run were already sent, as one revision '
                'you can revert)' % (self.sent,))

    def _message(self):
        """An honest default, so no revision arrives with a blank line.

        Written from what the run did rather than asked for, because a message
        somebody has to invent for every run is a message that ends up saying
        'update'.
        """
        if self.message:
            return self.message
        outcome = self.outcome
        parts = []
        if outcome.added:
            parts.append('%d added' % (len(outcome.added),))
        if outcome.updated:
            parts.append('%d updated' % (len(outcome.updated),))
        what = ', '.join(parts) or 'no change'
        return '%s: %s' % (type(self.generator).__name__, what)


def _current_entries(table, client):
    """What the table holds now, as {identity: value}.

    Fetched once, before anything is computed. Every question this run has to
    answer about an existing value -- does it contradict, does it lose digits,
    is it even there -- is answerable from this, and asking the server per
    entry would be a request per value on a table of thousands.
    """
    from . import table as fetch_table

    return _stored_entries(fetch_table(table, client=client))


def _stream(generator, only, digits, bounds, cache, skip=None):
    """Yield ``(identity, params, entry, digits)``, computing as it goes.

    ``skip`` is consulted *before* the value is computed, which is the whole
    value of ``overwrite=False``: skipping afterwards would still have paid for
    the entry.
    """
    names = tuple(generator.parameters)

    if _is_bulk(generator):
        if only is not None:
            raise ValueError(
                '%s produces its entries all at once, so it cannot be asked '
                'for only some of them. Give it an enumerate() and a value() '
                'if that is wanted.' % (type(generator).__name__,))
        for params, value in generator.all_entries(digits=digits, **bounds):
            params = dict(params)
            identity = _identity(params, names)
            if skip is not None and skip(identity):
                continue
            entry = _as_entry(value)
            wanted = _digits_for(generator, params, digits)
            cache.put(identity, _plain(entry, wanted, generator.format))
            yield identity, params, entry, wanted
        return

    for params in _wanted(generator, only, bounds):
        params = dict(params)
        identity = _identity(params, names)
        if skip is not None and skip(identity):
            continue
        wanted = _digits_for(generator, params, digits)
        found = cache.get(identity)
        if found is None:
            found = generator._entry(params, wanted)
            #Written before anything else happens to it, because what this
            #protects against is the next line never running.
            cache.put(identity, _plain(found, wanted, generator.format))
        yield identity, params, found, wanted


def _identity(params, names):
    """An entry's identity: its parameter values, as a citation writes them."""
    return ','.join(_text(params[name]) for name in names)


def _digits_for(generator, params, fallback):
    """What this entry is held to, which the generator may vary per entry."""
    asked = generator.digits_for(params)
    return int(fallback if asked is None else asked)


def _written(number, digits, form):
    """One entry's value as text. A list stays a list: an entry may hold
    several numbers, and each is written the same way."""
    if isinstance(number, (list, tuple)):
        return [to_text(one, digits, form) for one in number]
    return to_text(number, digits, form)


def _plain(entry, digits, form='decimal'):
    """An entry as text, which is what can be written to a file and read back."""
    out = {}
    for key, value in entry.items():
        out[key] = (_written(value, digits, form) if key == 'number'
                    else value if isinstance(value, (str, int, float, list))
                    else str(value))
    return out


def _wanted(generator, only, bounds):
    """Which entries this run is for.

    Everything the generator enumerates, or just the ones named. Named ones are
    not filtered out of the enumeration but built directly, so recomputing one
    entry of a million costs one computation rather than a walk of the million
    -- which for a generator whose enumeration is itself expensive is the
    difference between a minute and an afternoon.
    """
    if only is None:
        yield from generator.enumerate(**bounds)
        return

    names = tuple(generator.parameters)
    for wanted in only:
        if isinstance(wanted, Mapping):
            yield dict(wanted)
            continue
        #An identity: the values, comma-joined, as a citation writes them.
        parts = [part.strip() for part in str(wanted).split(',')]
        if len(parts) != len(names):
            raise ValueError(
                '%r does not name the %d parameter(s) %s'
                % (wanted, len(names), ', '.join(names)))
        yield dict(zip(names, parts))


def _is_bulk(generator):
    """Whether this generator produces everything at once."""
    return type(generator).all_entries is not Generator.all_entries


def _table_of(generator):
    table = getattr(generator, 'table', None)
    if not table:
        raise ValueError(
            'which table? %s needs a table = "T42" -- a generator is written '
            'for one table, and pointing it at another would store its '
            'numbers under somebody else\'s parameters.'
            % (type(generator).__name__,))
    return str(table)


def _text(value):
    from ._write import _param_text

    return _param_text(value)


def _source_files(generator) -> Dict[str, str]:
    """The files that will be stored with these numbers, by stored name.

    One decision, made once, used twice: these bytes are what gets attached and
    what the cache is fingerprinted by. Deciding it twice is how a cache comes
    to hand back values that the attached code did not produce.

    What to send is declared on the generator rather than discovered: a
    directory sweep would collect whatever else happened to be sitting there,
    which is nobody's intention and sooner or later somebody's private working
    file. With nothing declared it is the generator's own file -- the whole
    file, since ``inspect.getsource`` of a class returns the class body alone,
    and the function that computed the number usually sits beside it.
    """
    import inspect
    import os

    out = {}  # type: Dict[str, str]
    declared = tuple(getattr(generator, 'files', ()) or ())

    try:
        own = inspect.getfile(type(generator))
    except (OSError, TypeError):
        #Defined in a notebook or a session, where there is no file. Nothing
        #is attached rather than the class body on its own: a fragment stored
        #under a name like generate.py claims to be a script and is not one.
        own = None

    if not declared:
        if own:
            body = _read(own)
            if body is not None:
                out[os.path.basename(own)] = body
        return out

    beside = os.path.dirname(own) if own else '.'
    for named in declared:
        path = named if os.path.isabs(named) else os.path.join(beside, named)
        body = _read(path)
        if body is None:
            raise ValueError(
                '%s lists %r among its files, and it could not be read at %s. '
                'A declared file is not a guess, so this is not skipped '
                'quietly: the numbers would be stored without the code that '
                'was meant to accompany them.'
                % (type(generator).__name__, named, path))
        #Stored under the bare name: a table's files are flat.
        name = os.path.basename(named)
        if name in out:
            raise ValueError(
                "%s lists two files named %r. A table's files are flat, so "
                'one would silently replace the other.'
                % (type(generator).__name__, name))
        out[name] = body
    return out


def _read(path):
    try:
        with open(path, 'r', encoding='utf8') as handle:
            return handle.read()
    except OSError:
        return None


def _digest(files: Mapping[str, str]) -> str:
    """A fingerprint of exactly the bytes that will be attached."""
    import hashlib

    digest = hashlib.sha256()
    for name in sorted(files):
        digest.update(name.encode('utf8'))
        digest.update(b'\0')
        digest.update(files[name].encode('utf8'))
        digest.update(b'\0')
    return digest.hexdigest()


def _attach(generator, table, run, client, files, message='') -> List[str]:
    """Store the files that produced these numbers, in the same revision.

    Carries the run's own message. Everything a run does lands in one revision,
    and whichever part writes last decides what the history says it was -- so
    without this a published run was described in the table's history as "a
    file that produced these entries", whatever the caller had said it was
    doing.

    Best effort at this point. A run whose numbers are stored and whose source
    could not be sent has still done the useful part, and failing at the end
    over a file would be a poor trade -- the unreadable case was already
    refused, before anything was computed.
    """
    from ._write import attach

    stored = []
    for name in sorted(files):
        try:
            attach(table, name, files[name], run=run, client=client,
                   rigour=getattr(generator, 'rigour', ''),
                   message=message or 'a file that produced these entries')
            stored.append(name)
        except Exception:
            continue
    return stored


def _run_name(generator):
    """A name for one run of this generator.

    Derived from the generator and the moment it started, so two runs of the
    same script do not amend each other's revision and one run's batches all
    find their own.
    """
    import time

    return '%s-%d' % (type(generator).__name__[:40], int(time.time()))


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

    from ._errors import ConflictError, RateLimitError

    for attempt in range(attempts):
        try:
            return send()
        except (ConflictError, RateLimitError):
            if attempt == attempts - 1:
                raise
            time.sleep(2 ** attempt)
    raise AssertionError('unreachable')


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
                walk(value, prefix + [str(key)])
            return
        if isinstance(node, list):
            for item in node:
                walk(item, prefix)
            return
        out[','.join(prefix)] = str(node)

    walk(block, [])
    return out


def _value_of(node):
    """One entry's value, however the document spells it."""
    for key in ('number', 'equals', 'numbers'):
        if key in node:
            value = node[key]
            if isinstance(value, list):
                return str(value[0]) if value else ''
            return str(value)
    return ''
