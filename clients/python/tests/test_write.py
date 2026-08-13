"""Tests for the one way a program puts numbers into a table.

No network: the opener is injected through ``Client``. What is checked is the
shape of what would be sent, and the refusals -- a generator that gets a
table's identities subtly wrong does not fail, it publishes numbers under the
wrong names.

The write surface is deliberately small. `numberdb.Generator` is the whole of
it, and most of what used to be arguments is now decided by the package, so
most of what is tested here is that those decisions are actually made: that a value
reaches the disk before anything else can go wrong with it, that permission is
checked before a three-day computation rather than after, that a contradiction
stops a run at its first entry.
"""

import json
import sys
import urllib.error
from fractions import Fraction

import pytest

sys.path.insert(0, '.')

import numberdb
from numberdb._write import Entries, submit_entries, to_text

#: What `check_writable` says it is doing. Recognised here so a preflight is
#: not mistaken for a run's own writing.
PREFLIGHT = 'checking that this table can be written to'


@pytest.fixture(autouse=True)
def cache_in_a_temporary_place(tmp_path, monkeypatch):
    """Never the developer's real cache.

    Without this a test run would write computed values into ~/.cache/numberdb
    and, worse, read them back on the next run -- so a test could pass because
    of what an earlier run had left behind.
    """
    monkeypatch.setenv('NUMBERDB_CACHE', str(tmp_path / 'cache'))


class Server:
    """A NumberDB that answers without a network.

    Routes by method and path, because `publish` reads the table before it
    writes: to know whether a value contradicts what is stored, loses digits,
    or is new, it has to know what is stored.
    """

    def __init__(self, entries=None, names=('n',), busy=0, status=None,
                 body=None):
        #: identity -> stored value, as the table holds it.
        self.stored = dict(entries or {})
        self.names = tuple(names)
        self.posts = []        # (path, headers, body), preflight excluded
        self.preflights = 0
        self.files = {}        # name -> content
        self.busy = busy       # answer "busy" this many times first
        self.status = status
        self.body = body
        self.fetched = 0

    def document(self):
        records = []
        for identity, value in self.stored.items():
            params = dict(zip(self.names, identity.split(',')))
            records.append({'params': params, 'number': value})
        return {'Title': 'Probe', 'Numbers': records}

    def opener(self, request, timeout=None):
        path = request.full_url.split('http://server/')[-1]

        if request.data is None:
            self.fetched += 1
            return _Readable(json.dumps(self.document()).encode('utf8'))

        if self.status is not None:
            raise urllib.error.HTTPError(
                'http://x/', self.status, 'refused', {},
                _Readable(self.body or b'{}'))

        headers = dict(request.headers)
        body = request.data.decode('utf8')

        if _message(headers) == PREFLIGHT:
            self.preflights += 1
            return _Readable(b'{"tid": "T7"}')

        if '/file/' in path:
            self.posts.append((path, headers, body))
            self.files[path.rsplit('/file/', 1)[1]] = body
            return _Readable(b'{"ok": true}')

        if self.busy > 0:
            self.busy -= 1
            raise urllib.error.HTTPError(
                'http://x/', 409, 'busy', {},
                _Readable(b'{"error": "table is busy"}'))

        self.posts.append((path, headers, body))
        return _Readable(json.dumps({'tid': 'T7', 'revision': 'r1'})
                         .encode('utf8'))

    def client(self, api_key='k'):
        return numberdb.Client(api_key=api_key, base_url='http://server',
                               opener=self.opener)

    #-- what the tests ask it ------------------------------------------

    def entry_posts(self):
        """Every post that carried entries, ignoring files."""
        return [post for post in self.posts if '/file/' not in post[0]]

    def sent_entries(self):
        """Every entry sent, as {identity: value}."""
        out = {}
        for _path, _headers, body in self.entry_posts():
            for record in _parsed(body) or []:
                params = record.get('params') or {}
                out[','.join(str(v) for v in params.values())] = \
                    str(record.get('number'))
        return out

    def modes(self):
        return [_header(headers, 'X-entries-mode')
                for _path, headers, _body in self.entry_posts()]


def _parsed(body):
    """What was sent, read back however it was written.

    The package writes YAML when PyYAML is installed and JSON when it is not --
    JSON being a subset, the server reads either. A test that insisted on YAML
    passed everywhere PyYAML happened to be present and failed in the one
    environment that proves the package needs nothing: the release gate.
    """
    import json

    try:
        return json.loads(body)
    except ValueError:
        import yaml

        return yaml.safe_load(body)


def _header(headers, name):
    """urllib title-cases what it is given, so both spellings are looked for."""
    return headers.get(name) or headers.get(name.title())


def _message(headers):
    return _header(headers, 'X-edit-message') or ''


class _Readable:
    def __init__(self, data):
        self.data = data

    def read(self):
        return self.data

    def close(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class Zeta(numberdb.Generator):
    """A generator with a per-entry value, which is what most tables want."""

    table = 'T7'
    parameters = ('n',)
    type = 'Q'

    def enumerate(self, limit=3):
        for n in range(1, limit + 1):
            yield {'n': n}

    def value(self, params, digits):
        return Fraction(1, int(params['n']))


class TestValues:
    """`to_text` is internal now, but it still decides how a number is
    written, and every generator depends on it."""

    def test_a_string_is_kept_exactly(self):
        assert to_text('3.14159?') == '3.14159?'

    def test_an_integer_keeps_every_digit(self):
        assert to_text(2 ** 80) == str(2 ** 80)

    def test_a_fraction_is_written_as_one(self):
        assert to_text(Fraction(18, 11)) == '18/11'

    def test_a_whole_fraction_loses_its_denominator(self):
        assert to_text(Fraction(4, 2)) == '2'

    def test_a_float_is_refused_and_says_why(self):
        """A float does not carry its own precision, so it cannot be stored."""
        with pytest.raises(TypeError) as raised:
            to_text(3.14159)
        assert 'how precise' in str(raised.value)

    def test_a_boolean_is_not_a_number(self):
        with pytest.raises(TypeError):
            to_text(True)


class TestEntries:

    def test_parameters_are_named_in_the_record(self):
        entries = Entries('n')
        entries.add(n=3, number='3.14')
        assert entries.as_list() == [{'params': {'n': '3'}, 'number': '3.14'}]

    def test_several_parameters_keep_their_declared_order(self):
        entries = Entries('N', 'c4', 'c6')
        entries.add(N=389, c4=112, c6=-856, number='1.5')
        assert list(entries.as_list()[0]['params']) == ['N', 'c4', 'c6']

    def test_a_missing_parameter_is_refused(self):
        """Otherwise the entry lands under an identity nobody meant."""
        entries = Entries('N', 'c4')
        with pytest.raises(TypeError) as raised:
            entries.add(N=389, number='1.5')
        assert 'c4' in str(raised.value)

    def test_an_entry_with_no_number_is_refused(self):
        entries = Entries('n')
        with pytest.raises(TypeError):
            entries.add(n=1, comment='nothing here')

    def test_annotations_are_carried(self):
        entries = Entries('n')
        entries.add(n=1, number='3.14', comment='about pi', proof='CITE{x}')
        record = entries.as_list()[0]
        assert record['comment'] == 'about pi'
        assert record['proof'] == 'CITE{x}'

    def test_a_parameter_is_not_reformatted(self):
        """`1/2` and `0.5` are different identities, so neither may drift."""
        entries = Entries('x')
        entries.add(x=Fraction(1, 2), number='1')
        assert entries.as_list()[0]['params']['x'] == '1/2'


class TestThereIsNoWayToSendADocument:
    """The one thing a program must not be able to do.

    A generator that assembled a document out of what it knows -- a title, the
    parameters, the numbers -- and sent it would delete the definition, the
    comments, the references and the tags, and the table would look perfectly
    ordinary afterwards. That is not a discipline anybody has to remember: the
    functions do not exist.
    """

    @pytest.mark.parametrize('name', ['submit', 'document', 'create', 'Lease',
                                      'attach', 'Entries', 'to_text',
                                      'submit_entries', 'check_writable',
                                      'generate', 'publish', 'verify'])
    def test_it_is_not_public(self, name):
        assert not hasattr(numberdb, name)

    def test_the_generator_is_the_whole_surface(self):
        for verb in ('publish', 'preview', 'verify'):
            assert callable(getattr(numberdb.Generator, verb))


class TestReservedNames:
    """A subclass that shadows the machinery is refused where it is written.

    `verify` is exactly the word a mathematician reaches for when writing their
    own check of a computation. Silently overriding it would leave
    ``generator.verify()`` doing something else entirely, and the failure would
    surface at the end of a long run rather than at the class statement.
    """

    @pytest.mark.parametrize('verb', ['publish', 'preview', 'verify'])
    def test_shadowing_one_is_refused(self, verb):
        with pytest.raises(TypeError) as raised:
            exec('class Mine(numberdb.Generator):\n'
                 '    def %s(self): pass\n' % (verb,),
                 {'numberdb': numberdb})
        assert verb in str(raised.value)

    def test_the_refusal_suggests_a_way_out(self):
        with pytest.raises(TypeError) as raised:
            exec('class Mine(numberdb.Generator):\n'
                 '    def verify(self): pass\n', {'numberdb': numberdb})
        assert 'verify_entries()' in str(raised.value)

    def test_an_ordinary_subclass_is_fine(self):
        """Including one that subclasses another generator, which the tests
        here do constantly."""

        class Mine(Zeta):
            def value(self, params, digits):
                return Fraction(1, 1)

        assert Mine().table == 'T7'


class TestPublishing:

    def test_a_generator_needs_a_table(self):
        class Homeless(Zeta):
            table = None

        with pytest.raises(ValueError) as raised:
            Homeless().publish(client=Server().client())
        assert 'table = "T42"' in str(raised.value)

    def test_the_entries_are_sent(self):
        server = Server()
        outcome = Zeta().publish(client=server.client())
        assert server.sent_entries() == {'1': '1', '2': '1/2', '3': '1/3'}
        assert outcome.added == ['1', '2', '3']
        assert outcome.applied is True

    def test_it_posts_to_the_table(self):
        server = Server()
        Zeta().publish(client=server.client())
        assert server.entry_posts()[0][0].endswith('api/table/7/entries')

    def test_the_program_is_named(self):
        """Readers are entitled to know a revision came out of a script."""
        server = Server()
        Zeta().publish(client=server.client())
        assert 'Zeta' in _header(server.entry_posts()[0][1], 'X-produced-by')

    def test_every_batch_of_one_run_carries_the_same_run_id(self):
        server = Server()
        outcome = Zeta().publish(limit=250, client=server.client())
        runs = {_header(headers, 'X-run-id')
                for _p, headers, _b in server.entry_posts()}
        assert len(runs) == 1
        assert outcome.run in runs

    def test_a_run_writes_its_own_message(self):
        """History should never carry a blank line because nobody typed one."""
        server = Server()
        Zeta().publish(client=server.client())
        message = _message(server.entry_posts()[-1][1])
        assert 'Zeta' in message and 'added' in message

    def test_a_given_message_is_kept(self):
        server = Server()
        Zeta().publish(message='first values',
                         client=server.client())
        assert _message(server.entry_posts()[0][1]) == 'first values'


class TestCheckingBeforeComputing:
    """A generator may run for hours. "No API key was set" is knowable in the
    first second."""

    def gen(self, computed):
        class Expensive(Zeta):
            def value(inner, params, digits):
                computed.append(int(params['n']))
                return Fraction(1, int(params['n']))

        return Expensive()

    def test_it_happens(self):
        server = Server()
        Zeta().publish(client=server.client())
        assert server.preflights == 1

    def test_a_missing_key_is_found_before_anything_is_computed(self):
        computed = []
        server = Server()
        with pytest.raises(numberdb.UnauthorizedError):
            self.gen(computed).publish(
                             client=server.client(api_key=''))
        assert computed == []

    def test_a_refusal_is_found_before_anything_is_computed(self):
        computed = []
        server = Server(status=403, body=b'{"error": "not allowed yet"}')
        with pytest.raises(numberdb.NumberDBError):
            self.gen(computed).publish(client=server.client())
        assert computed == []


class TestOverwriting:

    def test_recomputed_values_replace_stored_ones_by_default(self):
        server = Server(entries={'1': '1', '2': '1/2'})
        outcome = Zeta().publish(client=server.client())
        assert outcome.unchanged == ['1', '2']
        assert outcome.added == ['3']

    def test_not_overwriting_skips_computing_what_is_there(self):
        """The point of it: extending a table of expensive values should cost
        the extension, not the table."""
        computed = []

        class Counted(Zeta):
            def value(inner, params, digits):
                computed.append(int(params['n']))
                return Fraction(1, int(params['n']))

        server = Server(entries={'1': '1', '2': '1/2'})
        outcome = Counted().publish(overwrite=False,
                                   client=server.client())
        assert computed == [3]
        assert outcome.added == ['3']
        assert server.sent_entries() == {'3': '1/3'}


class TestContradictions:
    """The check that costs nothing: each computed value is compared with what
    the table holds, so a run that has started producing different numbers
    stops at its first entry rather than after three days."""

    def test_a_contradiction_stops_the_run(self):
        server = Server(entries={'1': '2'})   # the table says 1 -> 2
        with pytest.raises(numberdb.DisagreementError) as raised:
            Zeta().publish(client=server.client())
        assert 'correcting=True' in str(raised.value)
        assert server.sent_entries() == {}

    def test_it_stops_before_computing_the_rest(self):
        computed = []

        class Counted(Zeta):
            def value(inner, params, digits):
                computed.append(int(params['n']))
                return Fraction(1, int(params['n']))

        server = Server(entries={'1': '2'})
        with pytest.raises(numberdb.DisagreementError):
            Counted().publish(limit=500, client=server.client())
        assert computed == [1]

    def test_correcting_lets_it_through(self):
        server = Server(entries={'1': '2'})
        outcome = Zeta().publish(correcting=True,
                                   client=server.client())
        assert outcome.updated == ['1']
        assert server.sent_entries()['1'] == '1'

    def test_the_refusal_names_the_entry_and_both_values(self):
        server = Server(entries={'1': '2'})
        with pytest.raises(numberdb.DisagreementError) as raised:
            Zeta().publish(client=server.client())
        error = raised.value
        assert error.identity == '1'
        assert error.stored == '2' and error.produced == '1'


class TestPrecision:
    """Differing precision is not a disagreement. It is the same number known
    better or known worse, and only one of those is a loss."""

    class Rounded(numberdb.Generator):
        table = 'T7'
        parameters = ('n',)
        #Said out loud, because this generator really does produce six.
        digits = 6

        def enumerate(self, limit=1):
            for n in range(1, limit + 1):
                yield {'n': n}

        def value(self, params, digits):
            return '3.14159'

    def test_more_digits_than_stored_is_not_a_disagreement(self):
        server = Server(entries={'1': '3.14'})
        outcome = self.Rounded().publish(client=server.client())
        assert outcome.updated == ['1']

    def test_fewer_digits_than_stored_is_refused(self):
        server = Server(entries={'1': '3.14159265358979323846'})
        with pytest.raises(numberdb.DisagreementError) as raised:
            self.Rounded().publish(client=server.client())
        assert 'lowering=True' in str(raised.value)
        assert 'digits' in str(raised.value)

    def test_lowering_lets_it_through(self):
        server = Server(entries={'1': '3.14159265358979323846'})
        outcome = self.Rounded().publish(lowering=True,
                                   client=server.client())
        assert outcome.updated == ['1']

    def test_an_identical_value_is_not_a_change(self):
        server = Server(entries={'1': '3.14159'})
        outcome = self.Rounded().publish(client=server.client())
        assert outcome.unchanged == ['1']


class TestValuesShorterThanAskedFor:
    """The quiet failure of this whole interface.

    Sage builds interval fields in bits and this database counts decimal
    digits. ``RealIntervalField(digits)`` reads perfectly well and delivers
    about a third of what was meant -- nothing is wrong with what gets stored,
    there is just a third of it, and no exception ever fires.
    """

    class Short(numberdb.Generator):
        table = 'T7'
        parameters = ('n',)
        digits = 100

        def enumerate(self, limit=1):
            yield {'n': 1}

        def value(self, params, digits):
            return '3.14159'          # six digits, not a hundred

    def test_it_is_refused(self):
        with pytest.raises(numberdb.DisagreementError) as raised:
            self.Short().publish(client=Server().client())
        assert 'carries 6' in str(raised.value)

    def test_the_refusal_names_both_causes(self):
        """It used to name one: the units mistake, with
        `RealIntervalField(numberdb.bits(digits))` as the remedy. That is the
        remedy for the *other* cause, and this check fires precisely when
        `bits(digits)` was not enough -- so it was recommending the thing that
        had just failed.

        Losing precision during a computation is the ordinary cause and is not
        a mistake at all; the fix is a wider field, not a corrected unit.
        """
        with pytest.raises(numberdb.DisagreementError) as raised:
            self.Short().publish(client=Server().client())
        message = str(raised.value)

        # the ordinary cause, and a remedy that is actually larger
        assert 'wider' in message
        assert 'losing=' in message

        # the units mistake, still named, no longer as the only explanation
        assert 'digits where Sage counts bits' in message

        # and it does not offer the bare conversion as the answer
        assert 'RealIntervalField(numberdb.bits(digits)) is what' not in message

    def test_an_entry_may_say_it_is_known_no_better(self):
        """A constant known to eight digits does not become wrong by being
        stored to eight."""

        class Honest(numberdb.Generator):
            table = 'T7'
            parameters = ('n',)
            digits = 100

            def enumerate(self, limit=1):
                yield {'n': 1}

            def value(self, params, digits):
                return {'number': '3.14159', 'digits': 6}

        server = Server()
        outcome = Honest().publish(client=server.client())
        assert outcome.added == ['1']
        assert server.sent_entries() == {'1': '3.14159'}

    def test_the_declared_digits_are_not_stored_as_an_annotation(self):
        class Honest(numberdb.Generator):
            table = 'T7'
            parameters = ('n',)

            def enumerate(self, limit=1):
                yield {'n': 1}

            def value(self, params, digits):
                return {'number': '3.14159', 'digits': 6}

        server = Server()
        Honest().publish(client=server.client())
        record = _parsed(server.entry_posts()[0][2])[0]
        assert 'digits' not in record

    def test_lowering_allows_a_whole_run_of_them(self):
        server = Server()
        outcome = self.Short().publish(lowering=True, client=server.client())
        assert outcome.added == ['1']

    def test_an_exact_value_is_not_short(self):
        """`1/3` states every digit there is; it is not thirty digits shy."""
        server = Server()
        outcome = Zeta().publish(client=server.client())
        assert outcome.added == ['1', '2', '3']

    def test_a_polynomial_is_not_measured_in_digits(self):
        """It has precision, but not decimal precision, and counting its
        characters would refuse a perfectly good polynomial."""

        class Polys(numberdb.Generator):
            table = 'T7'
            parameters = ('n',)
            type = 'Z[]'
            digits = 100

            def enumerate(self, limit=1):
                yield {'n': 1}

            def value(self, params, digits):
                return 'x^2 + 1'

        server = Server()
        assert Polys().publish(client=server.client()).added == ['1']


class TestPerEntryDigits:
    """Where a generator says how precise each entry should be."""

    def test_digits_for_varies_it_by_parameter(self):
        asked = []

        class Tapering(numberdb.Generator):
            table = 'T7'
            parameters = ('n',)
            digits = 100

            def digits_for(self, params):
                return 100 if int(params['n']) < 3 else 20

            def enumerate(self, limit=4):
                for n in range(1, limit + 1):
                    yield {'n': n}

            def value(self, params, digits):
                asked.append(digits)
                return '3.' + '1' * (digits - 1)

        server = Server()
        outcome = Tapering().publish(client=server.client())
        #The number reaches value(), so a generator sizes its working
        #precision from it...
        assert asked == [100, 100, 20, 20]
        #...and is what the entry is then held to: twenty digits where twenty
        #were asked for is not short.
        assert len(outcome.added) == 4

    def test_the_class_attribute_is_the_default(self):
        class Flat(numberdb.Generator):
            table = 'T7'
            parameters = ('n',)
            digits = 12

            def enumerate(self, limit=1):
                yield {'n': 1}

            def value(self, params, digits):
                assert digits == 12
                return '3.' + '1' * 11

        assert Flat().publish(client=Server().client()).added == ['1']


class TestTheWrittenForm:

    class Pi(numberdb.Generator):
        table = 'T7'
        parameters = ('n',)
        digits = 19

        def enumerate(self, limit=1):
            yield {'n': 1}

        def value(self, params, digits):
            from numberdb import RealInterval
            return RealInterval('3.14159265358979323845',
                                '3.14159265358979323847')

    def test_a_plain_decimal_by_default(self):
        """`3.14` IS (3.13, 3.15) in this database. No marker."""
        server = Server()
        self.Pi().publish(client=server.client())
        written = server.sent_entries()['1']
        assert written == '3.141592653589793238'
        assert '?' not in written and '+/-' not in written

    def test_what_is_checked_is_what_is_sent(self):
        """Entries.add used to convert the raw value again with its own
        defaults -- a hundred digits, the decimal form -- so the string checked
        for contradictions was not the string that reached the table, and a
        generator asking for twenty digits stored a hundred."""
        server = Server()
        self.Pi().publish(client=server.client())
        written = server.sent_entries()['1']
        significant = written.replace('.', '').lstrip('0')
        assert len(significant) == 19

    def test_a_generator_may_say_it_writes_balls(self):
        class Ball(TestTheWrittenForm.Pi):
            format = 'ball'

        server = Server()
        Ball().publish(client=server.client())
        assert '+/-' in server.sent_entries()['1']


class TestRemoving:
    """A run over n = 1..3 has said nothing whatever about n = 500."""

    def test_entries_this_run_did_not_produce_are_left_alone(self):
        server = Server(entries={'500': '1/500'})
        outcome = Zeta().publish(client=server.client())
        assert outcome.left_alone == ['500']
        assert outcome.removed == []
        assert set(server.modes()) == {'upsert'}

    def test_removing_sends_a_replacement(self):
        server = Server(entries={'500': '1/500'})
        outcome = Zeta().publish(removing=True,
                                   client=server.client())
        assert outcome.removed == ['500']
        assert outcome.left_alone == []
        #The replacement is one send of everything, not a stream: streaming a
        #replacement would delete the rest of the table between batches.
        assert server.modes()[-1] != 'upsert'
        assert set(server.sent_entries()) == {'1', '2', '3'}

    def test_removing_and_naming_entries_together_is_refused(self):
        with pytest.raises(ValueError) as raised:
            Zeta().publish(only=[{'n': 1}], removing=True,
                             client=Server().client())
        assert 'did not produce' in str(raised.value)


class TestNamingSomeEntries:

    def test_only_those_are_computed(self):
        computed = []

        class Counted(Zeta):
            def enumerate(inner, limit=1000):
                computed.append('walked')
                yield from Zeta.enumerate(inner, limit=limit)

            def value(inner, params, digits):
                computed.append(int(params['n']))
                return Fraction(1, int(params['n']))

        server = Server()
        Counted().publish(only=[{'n': 17}, {'n': 42}],
                         client=server.client())
        assert computed == [17, 42]

    def test_an_identity_may_be_named_instead(self):
        server = Server()
        Zeta().publish(only=['42'], client=server.client())
        assert set(server.sent_entries()) == {'42'}

    def test_an_identity_of_the_wrong_shape_is_refused(self):
        with pytest.raises(ValueError):
            Zeta().publish(only=['1,2'], client=Server().client())

    def test_naming_entries_never_replaces_the_table(self):
        server = Server(entries={'9': '1/9'})
        outcome = Zeta().publish(only=[{'n': 17}],
                                   client=server.client())
        assert set(server.modes()) == {'upsert'}
        assert outcome.left_alone == ['9']


class TestPreview:

    def test_nothing_is_sent(self):
        server = Server(entries={'1': '1'})
        outcome = Zeta().preview(client=server.client())
        assert server.posts == []
        assert server.preflights == 0
        assert outcome.applied is False

    def test_it_says_what_would_happen(self):
        server = Server(entries={'1': '1', '500': '1/500'})
        outcome = Zeta().preview(client=server.client())
        assert outcome.unchanged == ['1']
        assert outcome.added == ['2', '3']
        assert outcome.left_alone == ['500']

    def test_what_it_computed_is_not_computed_again(self):
        computed = []

        class Counted(Zeta):
            def value(inner, params, digits):
                computed.append(int(params['n']))
                return Fraction(1, int(params['n']))

        server = Server()
        Counted().preview(client=server.client())
        assert computed == [1, 2, 3]
        Counted().publish(client=server.client())
        assert computed == [1, 2, 3]


class TestTheCache:

    def test_a_second_run_does_not_recompute(self):
        computed = []

        class Counted(Zeta):
            def value(inner, params, digits):
                computed.append(int(params['n']))
                return Fraction(1, int(params['n']))

        server = Server()
        Counted().publish(client=server.client())
        Counted().publish(client=server.client())
        assert computed == [1, 2, 3]

    def test_a_value_reaches_the_disk_before_the_run_can_die(self):
        """What this protects against is the next line never running."""
        computed = []
        breaks = [True]

        class Dies(Zeta):
            def enumerate(inner, limit=4):
                yield from Zeta.enumerate(inner, limit=limit)

            def value(inner, params, digits):
                n = int(params['n'])
                computed.append(n)
                if n == 3 and breaks[0]:
                    raise RuntimeError('the machine fell over')
                return Fraction(1, n)

        server = Server()
        with pytest.raises(RuntimeError):
            Dies().publish(client=server.client())
        assert computed == [1, 2, 3]

        #Same file, same parameters, so the same fingerprint: the rerun picks
        #up what was already computed.
        computed.clear()
        breaks[0] = False
        Dies().publish(client=server.client())
        assert computed == [3, 4]


class TestTheCacheKnowsWhenItIsStale:
    """The fingerprint covers exactly the bytes that get attached.

    It used to hash ``inspect.getsource(type(generator))`` -- the class body --
    while the attachment was the whole file. Editing a helper function beside
    the class then changed the numbers without changing the fingerprint, so a
    rerun reused stale values and attached the edited file: a table carrying
    code that did not produce its numbers, with nothing saying so.
    """

    def write(self, tmp_path, scale):
        module = tmp_path / 'gen_under_test.py'
        module.write_text(
            'from fractions import Fraction\n'
            'import numberdb\n'
            '\n'
            'SCALE = %d\n'
            '\n'
            '\n'
            'def scaled(n):\n'
            '    return Fraction(1, n * SCALE)\n'
            '\n'
            '\n'
            'class Sample(numberdb.Generator):\n'
            "    table = 'T7'\n"
            "    parameters = ('n',)\n"
            '\n'
            '    def enumerate(self, limit=2):\n'
            '        for n in range(1, limit + 1):\n'
            '            yield {"n": n}\n'
            '\n'
            '    def value(self, params, digits):\n'
            '        return scaled(int(params["n"]))\n' % (scale,))
        return module

    def load(self, module):
        """Import it the way an import does.

        Registering in sys.modules is not incidental: ``inspect.getfile`` of a
        class looks the file up through ``sys.modules[cls.__module__]``, so a
        module loaded without being registered has no findable file and
        nothing would be attached at all.
        """
        import importlib.util

        spec = importlib.util.spec_from_file_location('gen_under_test',
                                                      str(module))
        loaded = importlib.util.module_from_spec(spec)
        #Left registered: publish looks the file up through sys.modules while
        #it runs, so unregistering here would be unregistering mid-import.
        sys.modules['gen_under_test'] = loaded
        spec.loader.exec_module(loaded)
        return loaded.Sample()

    @pytest.fixture(autouse=True)
    def forget_the_module_afterwards(self):
        yield
        sys.modules.pop('gen_under_test', None)

    def test_editing_a_helper_beside_the_class_invalidates_the_cache(
            self, tmp_path):
        module = self.write(tmp_path, scale=1)
        server = Server()
        self.load(module).publish(client=server.client())
        assert server.sent_entries() == {'1': '1', '2': '1/2'}

        #The class body is untouched; only the constant above it changes.
        self.write(tmp_path, scale=10)
        server = Server()
        self.load(module).publish(client=server.client())
        assert server.sent_entries() == {'1': '1/10', '2': '1/20'}

    def test_the_attached_file_is_what_was_fingerprinted(self, tmp_path):
        module = self.write(tmp_path, scale=1)
        server = Server()
        self.load(module).publish(client=server.client())
        assert server.files['gen_under_test.py'] == module.read_text()


class TestBatching:
    """Sent as they are computed, so a crash at entry 900 keeps the first 899
    -- and all of one run's batches land in one revision."""

    def test_many_entries_are_sent_in_batches(self):
        server = Server()
        Zeta().publish(limit=250, client=server.client())
        assert len(server.entry_posts()) >= 3
        assert len(server.sent_entries()) == 250

    def test_a_slow_entry_is_not_held_back_for_ninety_nine_more(self,
                                                                monkeypatch):
        """Some tables take hours per entry. Batching by count alone would mean
        storing nothing for a week."""
        monkeypatch.setattr(numberdb._generate, 'BATCH_SECONDS', 0)
        server = Server()
        Zeta().publish(client=server.client())
        assert len(server.entry_posts()) == 3


class TestRetryingABusyTable:
    """Writes to one table are serialised, so a batch can be told somebody else
    is writing. For a run of hours that is normal, and the values are already
    computed."""

    def test_a_busy_table_is_tried_again(self, monkeypatch):
        monkeypatch.setattr('time.sleep', lambda seconds: None)
        server = Server(busy=2)
        outcome = Zeta().publish(client=server.client())
        assert outcome.entries == 3

    def test_it_gives_up_eventually(self, monkeypatch):
        monkeypatch.setattr('time.sleep', lambda seconds: None)
        server = Server(busy=99)
        with pytest.raises(numberdb.NumberDBError):
            Zeta().publish(client=server.client())


class TestAttachingTheSource:
    """What is stored beside the numbers is the file that produced them.

    It used to be ``inspect.getsource(type(generator))``, which returns the
    class body and nothing else. A generator whose ``value`` called a function
    defined above it in the same file stored an attachment named generate.py
    that did not contain the code computing the number, and would not run.
    """

    def test_the_whole_file_is_attached(self):
        import generator_module

        server = Server()
        generator_module.Sample().publish(client=server.client())
        stored = server.files['generator_module.py']
        assert stored == open(generator_module.__file__).read()
        #The parts a class-only attachment lost.
        assert 'def scaled' in stored
        assert 'SCALE = 3' in stored

    def test_the_file_names_itself(self):
        import generator_module

        server = Server()
        outcome = generator_module.Sample().publish(
                                   client=server.client())
        assert outcome.files == ['generator_module.py']

    def test_files_ride_on_the_same_run(self):
        """So a reader finds the code that made these numbers, not the code
        that happens to be there now."""
        import generator_module

        server = Server()
        outcome = generator_module.Sample().publish(
                                   client=server.client())
        for path, headers, _body in server.posts:
            if '/file/' in path:
                assert _header(headers, 'X-run-id') == outcome.run

    def test_declared_files_replace_the_generators_own(self):
        import generator_module

        class Declaring(generator_module.Sample):
            files = ('generator_module.py',)

        server = Server()
        outcome = Declaring().publish(client=server.client())
        assert outcome.files == ['generator_module.py']

    def test_a_declared_file_that_cannot_be_read_is_refused(self):
        """Not skipped quietly: the numbers would be stored without the code
        that was meant to accompany them."""
        import generator_module

        class Missing(generator_module.Sample):
            files = ('generator_module.py', 'not_here.py')

        with pytest.raises(ValueError) as raised:
            Missing().publish(client=Server().client())
        assert 'not_here.py' in str(raised.value)

    def test_two_files_with_the_same_bare_name_are_refused(self, tmp_path):
        """A table's files are flat, so one would silently replace the other."""
        import generator_module

        #Two real files, in different directories, with one name between them.
        for where in ('solvers', 'series'):
            (tmp_path / where).mkdir()
            (tmp_path / where / 'util.py').write_text('#%s\n' % (where,))

        class Colliding(generator_module.Sample):
            files = (str(tmp_path / 'solvers' / 'util.py'),
                     str(tmp_path / 'series' / 'util.py'))

        with pytest.raises(ValueError) as raised:
            Colliding().publish(client=Server().client())
        assert 'flat' in str(raised.value)
        assert 'util.py' in str(raised.value)

    def test_a_generator_with_no_file_attaches_nothing(self):
        """A notebook cell is not a script, so it is not stored as one.

        ``inspect`` cannot reach the source of a class defined in a fileless
        __main__ at all -- getfile raises, and getsource calls getfile -- so
        the only alternative to sending nothing would be sending the class
        body under a name like generate.py, which claims to be runnable code
        and is not.
        """
        import __main__

        source = ('class Live(numberdb.Generator):\n'
                  "    table = 'T7'\n"
                  "    parameters = ('n',)\n"
                  '    def enumerate(self, limit=1):\n'
                  '        yield {"n": 1}\n'
                  '    def value(self, params, digits):\n'
                  '        return Fraction(1, 1)\n')
        namespace = {'numberdb': numberdb, 'Fraction': Fraction,
                     '__name__': '__main__'}
        exec(compile(source, '<ipython-input-1>', 'exec'), namespace)

        had = getattr(__main__, '__file__', None)
        if had is not None:
            del __main__.__file__
        try:
            server = Server()
            outcome = namespace['Live']().publish(
                                       client=server.client())
            assert outcome.files == []
            assert server.files == {}
        finally:
            if had is not None:
                __main__.__file__ = had


class TestBulkGenerators:
    """Some tables cannot be computed one entry at a time: zeros found by a
    sweep, values lifted from another database."""

    class Sweep(numberdb.Generator):
        table = 'T7'
        parameters = ('n',)

        def all_entries(self, digits=None, **bounds):
            for n in (1, 2):
                yield {'n': n}, Fraction(1, n)

    def test_they_are_sent(self):
        server = Server()
        self.Sweep().publish(client=server.client())
        assert server.sent_entries() == {'1': '1', '2': '1/2'}

    def test_they_cannot_be_asked_for_some(self):
        with pytest.raises(ValueError) as raised:
            self.Sweep().publish(only=[{'n': 1}],
                             client=Server().client())
        assert 'all at once' in str(raised.value)

    def test_what_they_yield_is_kept_as_it_arrives(self, tmp_path):
        """Yielding rather than returning is what lets a sweep that dies half
        way keep what it found."""
        import os

        self.Sweep().preview(client=Server().client())
        cached = os.listdir(str(tmp_path / 'cache'))
        assert len(cached) == 1
        assert 'identity' in open(str(tmp_path / 'cache' / cached[0])).read()


class TestVerify:
    """Reads, computes, compares. Needs no key."""

    def test_a_table_that_matches_is_ok(self):
        server = Server(entries={'1': '1', '2': '1/2', '3': '1/3'})
        report = Zeta().verify(client=server.client())
        assert report.ok
        assert report.matched == 3

    def test_a_contradiction_is_reported(self):
        server = Server(entries={'1': '1', '2': '99', '3': '1/3'})
        report = Zeta().verify(client=server.client())
        assert not report.ok
        assert [identity for identity, _s, _n in report.differing] == ['2']

    def test_what_differs_feeds_straight_back(self):
        server = Server(entries={'1': '1', '2': '99', '3': '1/3'})
        report = Zeta().verify(client=server.client())
        assert report.to_fix() == [{'n': 2}]

    def test_a_missing_entry_is_reported(self):
        server = Server(entries={'1': '1'})
        report = Zeta().verify(client=server.client())
        assert set(report.missing) == {'2', '3'}

    def test_fewer_stored_digits_is_not_a_disagreement(self):
        """The bug this replaced: comparing text reported every entry of a
        table built at 20 digits as broken when checked at 100, and then
        proposed rewriting all of them."""

        class Pi(numberdb.Generator):
            table = 'T7'
            parameters = ('n',)

            def enumerate(self, limit=1):
                yield {'n': 1}

            def value(self, params, digits):
                return '3.14159265358979323846'

        server = Server(entries={'1': '3.14159'})
        report = Pi().verify(client=server.client())
        assert report.ok
        assert report.refined == ['1']

    def test_a_sample_is_spread_through_the_table(self):
        seen = []

        class Watched(Zeta):
            def value(inner, params, digits):
                seen.append(int(params['n']))
                return Fraction(1, int(params['n']))

        server = Server(entries={str(n): '1/%d' % n for n in range(1, 101)})
        Watched().verify(sample=5, limit=100,
                        client=server.client())
        assert len(seen) == 5
        assert seen[0] == 1 and seen[-1] > 50


class TestSubmittingEntriesOnly:
    """The internal call `publish` is built on. Entries and nothing else."""

    def test_it_posts_only_entries(self):
        server = Server()
        entries = Entries('n')
        entries.add(n=1, number='3.14')
        submit_entries('T7', entries, client=server.client())
        body = _parsed(server.entry_posts()[0][2])
        #A list of entries, and nothing that could be mistaken for a document.
        assert [sorted(record) for record in body] == [['number', 'params']]

    def test_upsert_is_announced_in_a_header(self):
        server = Server()
        entries = Entries('n')
        entries.add(n=1, number='3.14')
        submit_entries('T7', entries, upsert=True, client=server.client())
        assert server.modes() == ['upsert']


class TestRestating:
    """Whether a re-run rewrites values that merely agree with what is stored.

    The case this exists for turned up the first time an old script was
    converted. The original truncated the final digit and the package rounds
    it, so on 237 of that table's 501 entries the two differed in that digit
    while denoting intervals of the same width, both containing the number.
    Neither is more true. Rewriting them all is a mass edit that says nothing
    about any number, and marks every entry as changed.
    """

    class Rounded(numberdb.Generator):
        """Produces a value that agrees with the stored one to the same
        precision, in a different final digit."""

        table = 'T7'
        parameters = ('n',)
        type = 'R'
        digits = 4

        def enumerate(self):
            yield {'n': 1}

        def value(self, params, digits):
            return '1.235'

    def test_a_value_that_only_agrees_is_left_alone(self):
        server = Server(entries={'1': '1.234'})
        outcome = self.Rounded().publish(client=server.client())
        assert outcome.agreed == ['1']
        assert outcome.updated == []
        assert server.sent_entries() == {}

    def test_and_restating_writes_it_after_all(self):
        server = Server(entries={'1': '1.234'})
        outcome = self.Rounded().publish(restating=True,
                                         client=server.client())
        assert outcome.updated == ['1']
        assert server.sent_entries() == {'1': '1.235'}

    def test_an_identical_value_is_never_sent(self):
        """Writing a value byte-identical to the stored one is a write that
        changes nothing, and a thousand of them is a revision that does."""
        server = Server(entries={'1': '1'})

        class Same(TestRestating.Rounded):
            digits = 1

            def value(inner, params, digits):
                return '1'

        outcome = Same().publish(client=server.client())
        assert outcome.unchanged == ['1']
        assert server.sent_entries() == {}

    def test_a_refinement_is_written_whatever_restating_says(self):
        """More digits is a real improvement, not a restatement."""
        server = Server(entries={'1': '1.2'})

        class Longer(TestRestating.Rounded):
            digits = 6

            def value(inner, params, digits):
                return '1.23456'

        outcome = Longer().publish(client=server.client())
        assert outcome.updated == ['1']
        assert server.sent_entries() == {'1': '1.23456'}

    def test_a_new_entry_is_written_whatever_it_says(self):
        server = Server(entries={})
        outcome = self.Rounded().publish(client=server.client())
        assert outcome.added == ['1']
        assert server.sent_entries() == {'1': '1.235'}

    def test_what_is_not_restated_still_survives_a_removing_run(self):
        """`removing` sends the table as a replacement. An entry left alone
        because it merely agreed must still be in it, or declining to rewrite
        a value would delete it -- the worst possible reading of "leave it
        as it is"."""
        server = Server(entries={'1': '1.234', '2': '9.9'})
        outcome = self.Rounded().publish(removing=True,
                                         client=server.client())
        assert outcome.agreed == ['1']
        assert outcome.removed == ['2']
        assert server.sent_entries() == {'1': '1.235'}

    def test_the_source_is_attached_even_when_no_number_changed(self):
        """The reason to re-run a converted generator at all: the table gets
        the code that produces its numbers, whether or not any of them move."""
        server = Server(entries={'1': '1.234'})
        outcome = self.Rounded().publish(client=server.client())
        assert server.sent_entries() == {}
        assert outcome.files


class TestTheRunsMessageIsWhatTheHistoryShows:
    """A published run lands in one revision, and whichever part of it writes
    last decides what the table's history says happened.

    The attachment writes last, so a run described as "extended to n = 2000"
    was recorded as "a file that produced these entries" -- which is true of
    every run ever made and therefore tells a reader nothing. Found by
    publishing a real table and then reading its history.
    """

    def test_the_message_reaches_the_attachment(self):
        server = Server(entries={})
        Zeta().publish(message='extended to n = 3', client=server.client())
        files = [(path, headers) for path, headers, _body in server.posts
                 if '/file/' in path]
        assert files
        assert all(_message(headers) == 'extended to n = 3'
                   for _path, headers in files)

    def test_and_there_is_still_a_message_when_none_was_given(self):
        server = Server(entries={})
        Zeta().publish(client=server.client())
        files = [headers for path, headers, _body in server.posts
                 if '/file/' in path]
        assert files
        assert all(_message(headers) for headers in files)
