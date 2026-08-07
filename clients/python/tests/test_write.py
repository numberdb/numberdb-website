"""Tests for building a table and submitting it.

No network: the opener is injected through ``Client``, as elsewhere in this
suite. What is checked is the shape of what would be sent, and the refusals --
a generator that gets a table's identities subtly wrong does not fail, it
publishes numbers under the wrong names.
"""

import json
import sys
import urllib.error
from fractions import Fraction

import pytest

sys.path.insert(0, '.')

import numberdb


class Sent:
    """A Client whose opener records the request instead of sending it."""

    def __init__(self, payload=None, status=None, body=None):
        self.payload = payload if payload is not None else {'tid': 'T1'}
        self.status = status
        self.body = body
        self.request = None

    def opener(self, request, timeout=None):
        self.request = request
        if self.status is not None:
            raise urllib.error.HTTPError(
                'http://x/', self.status, 'refused', {},
                _Readable(self.body or b'{}'))
        return _Readable(json.dumps(self.payload).encode('utf8'))

    def client(self, api_key='k'):
        return numberdb.Client(api_key=api_key, base_url='http://server',
                               opener=self.opener)


class _Readable:
    def __init__(self, data):
        self.data = data

    def read(self):
        return self.data

    def close(self):
        #HTTPError treats what it is handed as a file and closes it on
        #collection; without this the teardown raises into the test run.
        return None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class TestValues:

    def test_a_string_is_kept_exactly(self):
        assert numberdb.to_text('3.14159?') == '3.14159?'

    def test_an_integer_keeps_every_digit(self):
        assert numberdb.to_text(2 ** 80) == str(2 ** 80)

    def test_a_fraction_is_written_as_one(self):
        assert numberdb.to_text(Fraction(18, 11)) == '18/11'

    def test_a_whole_fraction_loses_its_denominator(self):
        assert numberdb.to_text(Fraction(4, 2)) == '2'

    def test_a_float_is_refused_and_says_why(self):
        """A float does not carry its own precision, so it cannot be stored."""
        with pytest.raises(TypeError) as raised:
            numberdb.to_text(3.14159)
        assert 'how precise' in str(raised.value)

    def test_a_boolean_is_not_a_number(self):
        with pytest.raises(TypeError):
            numberdb.to_text(True)


class TestEntries:

    def test_parameters_are_named_in_the_record(self):
        entries = numberdb.Entries('n')
        entries.add(n=3, number='3.14')
        assert entries.as_list() == [{'params': {'n': '3'}, 'number': '3.14'}]

    def test_several_parameters_keep_their_declared_order(self):
        entries = numberdb.Entries('N', 'c4', 'c6')
        entries.add(N=389, c4=112, c6=-856, number='1.5')
        assert list(entries.as_list()[0]['params']) == ['N', 'c4', 'c6']

    def test_a_missing_parameter_is_refused(self):
        """Otherwise the entry lands under an identity nobody meant."""
        entries = numberdb.Entries('N', 'c4')
        with pytest.raises(TypeError) as raised:
            entries.add(N=389, number='1.5')
        assert 'c4' in str(raised.value)

    def test_an_entry_with_no_number_is_refused(self):
        entries = numberdb.Entries('n')
        with pytest.raises(TypeError):
            entries.add(n=1, comment='nothing here')

    def test_annotations_are_carried(self):
        entries = numberdb.Entries('n')
        entries.add(n=1, number='3.14', comment='about pi', proof='CITE{x}')
        record = entries.as_list()[0]
        assert record['comment'] == 'about pi'
        assert record['proof'] == 'CITE{x}'

    def test_several_numbers_may_share_a_parameter(self):
        entries = numberdb.Entries('n')
        entries.add(n=1, number=['3.14', '3.15'])
        assert entries.as_list()[0]['number'] == ['3.14', '3.15']

    def test_a_parameter_is_not_reformatted(self):
        """`1/2` and `0.5` are different identities, so neither may drift."""
        entries = numberdb.Entries('x')
        entries.add(x=Fraction(1, 2), number='1')
        assert entries.as_list()[0]['params']['x'] == '1/2'

    def test_names_may_be_given_as_a_sequence(self):
        assert numberdb.Entries(['a', 'b']).names == ('a', 'b')

    def test_length_counts_entries(self):
        entries = numberdb.Entries('n')
        for n in range(5):
            entries.add(n=n, number=str(n))
        assert len(entries) == 5


class TestDocument:

    def test_the_title_comes_first(self):
        """Section order is content: a sorted document rewrites the table."""
        doc = numberdb.document(title='Zeta', parameters={'n': {}},
                                entries=numberdb.Entries('n'))
        assert list(doc)[0] == 'Title'

    def test_sections_are_given_prose_names(self):
        doc = numberdb.document(title='X', data_properties={'type': 'R'})
        assert doc['Data properties'] == {'type': 'R'}

    def test_a_document_needs_a_title(self):
        with pytest.raises(ValueError):
            numberdb.document(title='')

    def test_entries_may_be_plain_records(self):
        doc = numberdb.document(title='X',
                                entries=[{'params': {'n': '1'},
                                          'number': '2'}])
        assert doc['Numbers'][0]['number'] == '2'


class TestSubmitting:

    def doc(self):
        entries = numberdb.Entries('n')
        entries.add(n=1, number='3.14159')
        return numberdb.document(title='Probe', parameters={'n': {'type': 'Z'}},
                                 entries=entries)

    def test_a_key_is_required_before_anything_is_sent(self):
        """A script that forgot its key should be told, not handed a 401."""
        sent = Sent()
        with pytest.raises(numberdb.Unauthorized) as raised:
            numberdb.submit('T1', self.doc(), client=sent.client(api_key=''))
        assert 'API key' in str(raised.value)
        assert sent.request is None

    def test_the_key_travels_as_a_bearer_token(self):
        sent = Sent()
        numberdb.submit('T1', self.doc(), client=sent.client())
        assert sent.request.headers['Authorization'] == 'Bearer k'

    def test_it_posts_to_the_table(self):
        sent = Sent()
        numberdb.submit('T42', self.doc(), client=sent.client())
        assert sent.request.get_method() == 'POST'
        assert sent.request.full_url.endswith('/api/table/42')

    def test_a_t_prefix_is_accepted(self):
        sent = Sent()
        numberdb.submit('T42', self.doc(), client=sent.client())
        assert sent.request.full_url.endswith('/api/table/42')

    def test_the_program_is_named(self):
        """Readers are entitled to know a revision came out of a script."""
        sent = Sent()
        numberdb.submit('T1', self.doc(), produced_by='zeta-generator',
                        client=sent.client())
        assert sent.request.headers['X-produced-by'] == 'zeta-generator'

    def test_an_unnamed_program_still_says_it_is_one(self):
        sent = Sent()
        numberdb.submit('T1', self.doc(), client=sent.client())
        assert sent.request.headers['X-produced-by'] == 'numberdb-python'

    def test_the_base_revision_is_sent_when_given(self):
        sent = Sent()
        numberdb.submit('T1', self.doc(), base='abc123', client=sent.client())
        assert sent.request.headers['X-base-revision'] == 'abc123'

    def test_the_body_keeps_its_section_order(self):
        sent = Sent()
        numberdb.submit('T1', self.doc(), client=sent.client())
        body = sent.request.data.decode('utf8')
        assert body.index('Title') < body.index('Numbers')

    def test_creating_posts_to_the_collection(self):
        sent = Sent(payload={'tid': 'T108'})
        result = numberdb.create(self.doc(), client=sent.client())
        assert sent.request.full_url.endswith('/api/tables')
        assert result['tid'] == 'T108'


class TestRefusals:

    def doc(self):
        return numberdb.document(title='Probe',
                                 entries=[{'params': {}, 'number': '1'}])

    def refuse(self, status, body):
        sent = Sent(status=status, body=json.dumps(body).encode('utf8'))
        return sent.client()

    def test_a_size_refusal_says_what_was_too_big(self):
        client = self.refuse(413, {'error': 'The table is over a size limit.',
                                   'detail': ['this table holds 90000 entries']})
        with pytest.raises(numberdb.TooBig) as raised:
            numberdb.submit('T1', self.doc(), client=client)
        assert '90000 entries' in str(raised.value)

    def test_an_untrusted_key_is_reported_as_unauthorised(self):
        client = self.refuse(403, {'error': 'not yet',
                                   'detail': 'opens after 5 edits'})
        with pytest.raises(numberdb.Unauthorized) as raised:
            numberdb.submit('T1', self.doc(), client=client)
        assert '5 edits' in str(raised.value)

    def test_a_concurrent_change_is_a_conflict(self):
        client = self.refuse(409, {'error': 'Somebody changed this table.'})
        with pytest.raises(numberdb.Conflict):
            numberdb.submit('T1', self.doc(), client=client)

    def test_a_bad_document_reports_the_servers_reason(self):
        client = self.refuse(400, {'error': 'The table has no Title.'})
        with pytest.raises(numberdb.NumberDBError) as raised:
            numberdb.submit('T1', self.doc(), client=client)
        assert 'no Title' in str(raised.value)


class TestSubmittingEntriesOnly:
    """A generator computes values; it must not be able to delete prose."""

    def entries(self):
        e = numberdb.Entries('n')
        e.add(n=1, number='3.14159')
        return e

    def test_it_posts_to_the_entries_of_the_table(self):
        sent = Sent()
        numberdb.submit_entries('T42', self.entries(), client=sent.client())
        assert sent.request.full_url.endswith('/api/table/42/entries')

    def test_only_the_records_are_sent(self):
        """No Title, no Parameters: nothing that could overwrite a section."""
        sent = Sent()
        numberdb.submit_entries('T42', self.entries(), client=sent.client())
        body = sent.request.data.decode('utf8')
        assert 'params' in body
        assert 'Title' not in body
        assert 'Parameters' not in body

    def test_plain_records_are_accepted(self):
        sent = Sent()
        numberdb.submit_entries('T1', [{'params': {'n': '1'}, 'number': '2'}],
                                client=sent.client())
        assert 'number' in sent.request.data.decode('utf8')

    def test_the_program_is_named(self):
        sent = Sent()
        numberdb.submit_entries('T1', self.entries(), produced_by='zeta-gen',
                                client=sent.client())
        assert sent.request.headers['X-produced-by'] == 'zeta-gen'

    def test_a_key_is_still_required(self):
        sent = Sent()
        with pytest.raises(numberdb.Unauthorized):
            numberdb.submit_entries('T1', self.entries(),
                                    client=sent.client(api_key=''))


class Zeta(numberdb.Generator):
    """A generator small enough to check by eye."""

    parameters = ('n',)
    type = 'Q'
    tid = 'T7'

    def enumerate(self, limit=5):
        for n in range(1, limit + 1):
            yield {'n': n}

    def value(self, params, digits):
        return Fraction(1, params['n'])


class TestGenerator:

    def test_generating_walks_the_enumeration(self):
        entries = numberdb.generate(Zeta(), limit=3)
        assert [r['number'] for r in entries] == ['1', '1/2', '1/3']

    def test_parameters_are_named_in_the_records(self):
        entries = numberdb.generate(Zeta(), limit=2)
        assert entries.as_list()[1]['params'] == {'n': '2'}

    def test_extending_is_the_same_call_with_a_larger_bound(self):
        assert len(numberdb.generate(Zeta(), limit=9)) == 9

    def test_a_generator_may_return_annotations_with_the_value(self):
        class WithComment(Zeta):
            def value(self, params, digits):
                return {'number': Fraction(1, params['n']),
                        'comment': 'reciprocal'}

        record = numberdb.generate(WithComment(), limit=1).as_list()[0]
        assert record['comment'] == 'reciprocal'

    def test_a_generator_with_neither_method_says_so(self):
        class Empty(numberdb.Generator):
            parameters = ('n',)

        with pytest.raises(NotImplementedError):
            numberdb.generate(Empty())

    def test_a_bulk_generator_needs_no_per_entry_value(self):
        """For tables whose values only come all at once."""
        class Bulk(numberdb.Generator):
            parameters = ('n',)

            def all_entries(self, digits=None, **bounds):
                entries = numberdb.Entries('n')
                entries.add(n=1, number='3.14')
                return entries

        assert len(numberdb.generate(Bulk())) == 1

    def test_the_environment_is_recorded(self):
        """A mismatch later is only useful if something said what ran first."""
        assert 'python' in Zeta().environment()


class TestVerify:

    def stored(self, entries):
        """A client whose table() call answers with these stored entries."""
        return Sent(payload={'Title': 'Probe', 'Numbers': entries}).client()

    def test_a_matching_table_verifies(self):
        client = self.stored([{'params': {'n': '1'}, 'number': '1'},
                              {'params': {'n': '2'}, 'number': '1/2'}])
        report = numberdb.verify(Zeta(), client=client, limit=2, sample=None)
        assert report.ok
        assert report.matched == 2

    def test_a_changed_value_is_reported_with_both_forms(self):
        """'T7 disagrees' is not actionable; naming the entry is."""
        client = self.stored([{'params': {'n': '1'}, 'number': '1'},
                              {'params': {'n': '2'}, 'number': '0.5'}])
        report = numberdb.verify(Zeta(), client=client, limit=2, sample=None)
        assert not report.ok
        assert report.differing == [('2', '0.5', '1/2')]

    def test_an_entry_the_table_lacks_is_reported_as_missing(self):
        client = self.stored([{'params': {'n': '1'}, 'number': '1'}])
        report = numberdb.verify(Zeta(), client=client, limit=2, sample=None)
        assert report.missing == ['2']

    def test_sampling_checks_only_some_of_them(self):
        """Why a per-entry value matters: seconds instead of days."""
        client = self.stored([{'params': {'n': str(n)},
                               'number': '1' if n == 1 else '1/%d' % n}
                              for n in range(1, 101)])
        report = numberdb.verify(Zeta(), client=client, limit=100, sample=5)
        assert report.checked == 5

    def test_sampling_spreads_through_the_table(self):
        """Not just the cheap end, which is where a sweep would stop.

        The stored values are written the way `to_text` writes them -- `1`
        rather than `1/1` -- because a table storing the other spelling really
        would differ, and this test is about which entries get checked.
        """
        client = self.stored([{'params': {'n': str(n)},
                               'number': '1' if n == 1 else '1/%d' % n}
                              for n in range(1, 101)])
        report = numberdb.verify(Zeta(), client=client, limit=100, sample=4)
        assert report.matched == 4
        assert report.checked == 4

    def test_the_nested_stored_form_is_understood_too(self):
        """Both forms coexist, so verification must read either."""
        client = Sent(payload={'Title': 'Probe',
                               'Numbers': {'1': '1', '2': '1/2'}}).client()
        report = numberdb.verify(Zeta(), client=client, limit=2, sample=None)
        assert report.ok

    def test_verification_writes_nothing(self):
        sent = Sent(payload={'Title': 'Probe',
                             'Numbers': {'1': '1', '2': '1/2'}})
        numberdb.verify(Zeta(), client=sent.client(), limit=2, sample=None)
        assert sent.request.get_method() == 'GET'

    def test_it_needs_to_know_which_table(self):
        class Untied(Zeta):
            tid = None

        with pytest.raises(ValueError):
            numberdb.verify(Untied(), client=self.stored([]))


class TestSageValues:
    """Sage's own types, which is what a generator actually returns.

    Skipped without Sage. Worth having under it: the example in the docs
    returns a Sage real interval, and `to_text` could not write one -- the
    commonest value in the database, 65 of the 107 tables.
    """

    def sage(self):
        pytest.importorskip('sage.all')
        import sage.all as sage
        return sage

    def test_a_real_interval_gets_the_question_mark_form(self):
        sage = self.sage()
        text = numberdb.to_text(sage.RealIntervalField(400)(sage.pi), digits=20)
        assert text.startswith('3.14159265358979')
        assert text.endswith('?')

    def test_digits_are_respected(self):
        sage = self.sage()
        value = sage.RealIntervalField(400)(sage.pi)
        assert len(numberdb.to_text(value, digits=20).rstrip('?')) == 21
        assert len(numberdb.to_text(value, digits=50).rstrip('?')) == 51

    def test_a_complex_interval_is_spelt_as_the_database_spells_it(self):
        """`a + i * b`: 1847 values use it and none uses Sage's `a + b*I`."""
        sage = self.sage()
        text = numberdb.to_text(
            sage.ComplexIntervalField(200)(sage.pi, sage.sqrt(2)), digits=15)
        assert ' + i * ' in text
        assert '*I' not in text

    def test_exact_types_keep_every_digit(self):
        """Truncating an exact value does not round it, it changes it."""
        sage = self.sage()
        big = sage.ZZ(2) ** 80
        assert numberdb.to_text(big, digits=10) == str(big)
        assert numberdb.to_text(sage.QQ(18) / 11, digits=2) == '18/11'

    def test_a_polynomial_is_written_out(self):
        sage = self.sage()
        ring = sage.PolynomialRing(sage.QQ, 'x')
        assert numberdb.to_text(ring([1, 0, -1])) == '-x^2 + 1'

    def test_a_p_adic_keeps_its_precision(self):
        sage = self.sage()
        assert 'O(2^' in numberdb.to_text(sage.Qp(2)(1, 167))

    def test_a_failure_says_what_it_could_not_write(self):
        """It used to swallow the reason and blame the type."""
        sage = self.sage()
        with pytest.raises(Exception):
            numberdb.to_text(sage.Words('ab'))


class TestComplexSpelling:
    """`i` before the digits, so a truncated value still says which part it is."""

    def value(self):
        from fractions import Fraction
        return numberdb.ComplexInterval(
            numberdb.RealInterval(Fraction(1, 2), Fraction(1, 2)),
            numberdb.RealInterval(Fraction(-3, 4), Fraction(-3, 4)))

    def test_the_marker_comes_before_the_imaginary_digits(self):
        text = numberdb.to_text(self.value())
        assert ' + i * ' in text
        #Whatever follows the marker is the imaginary part, so an abbreviated
        #value still identifies itself.
        assert text.index(' + i * ') < text.index('-3/4')

    def test_sage_s_own_spelling_is_not_produced(self):
        assert '*I' not in numberdb.to_text(self.value())

    def test_a_negative_imaginary_part_keeps_its_sign_in_place(self):
        """`a + i * -b`, never `a - i * b`: the separator is always plus."""
        text = numberdb.to_text(self.value())
        assert ' - i ' not in text
        assert '-3/4' in text


class TestStreamingEntries:
    """Sending values as they are computed, rather than all at the end.

    A generator of expensive values that must finish before it sends anything
    loses everything when it dies at entry 900. The batches of one run land in
    a single revision, so the history shows one act of regeneration.
    """

    def gen(self):
        class Slow(numberdb.Generator):
            parameters = ('n',)
            type = 'Q'
            tid = 'T7'

            def enumerate(self, limit=6):
                for n in range(1, limit + 1):
                    yield {'n': n}

            def value(self, params, digits):
                return Fraction(1, params['n'])

        return Slow()

    def test_upsert_and_run_are_sent(self):
        sent = Sent()
        numberdb.submit_entries('T7', numberdb.Entries('n'), upsert=True,
                                run='run-1', client=sent.client())
        assert sent.request.headers['X-entries-mode'] == 'upsert'
        assert sent.request.headers['X-run-id'] == 'run-1'

    def test_neither_is_sent_by_default(self):
        """Replacing is what a full regeneration means."""
        sent = Sent()
        entries = numberdb.Entries('n')
        entries.add(n=1, number='1')
        numberdb.submit_entries('T7', entries, client=sent.client())
        assert 'X-entries-mode' not in sent.request.headers

    def test_publishing_in_batches_sends_several_times(self):
        posts = []

        class Recording(Sent):
            def opener(self, request, timeout=None):
                posts.append(request)
                return _Readable(json.dumps({'tid': 'T7'}).encode('utf8'))

        recorder = Recording()
        result = numberdb.publish(self.gen(), batch=2, limit=6,
                                  preflight=False, client=recorder.client())
        entries = [r for r in posts if r.full_url.endswith('/entries')]
        assert len(entries) == 3
        assert result['entries'] == 6
        assert result['batches'] == 3

    def test_every_batch_carries_the_same_run(self):
        """Otherwise each becomes its own revision of the whole document."""
        posts = []

        class Recording(Sent):
            def opener(self, request, timeout=None):
                posts.append(request)
                return _Readable(json.dumps({'tid': 'T7'}).encode('utf8'))

        numberdb.publish(self.gen(), batch=2, limit=6, preflight=False,
                         client=Recording().client())
        entries = [r for r in posts if r.full_url.endswith('/entries')]
        runs = {r.headers['X-run-id'] for r in entries}
        assert len(runs) == 1

    def test_batches_are_upserts(self):
        """Each sends what it has; replacing would delete the earlier ones."""
        posts = []

        class Recording(Sent):
            def opener(self, request, timeout=None):
                posts.append(request)
                return _Readable(json.dumps({'tid': 'T7'}).encode('utf8'))

        numberdb.publish(self.gen(), batch=2, limit=6, preflight=False,
                         client=Recording().client())
        entries = [r for r in posts if r.full_url.endswith('/entries')]
        assert entries and all(r.headers['X-entries-mode'] == 'upsert'
                               for r in entries)

    def test_without_a_batch_it_sends_once(self):
        sent = Sent()
        numberdb.publish(self.gen(), limit=4, preflight=False,
                         client=sent.client())
        assert sent.request.headers.get('X-entries-mode') is None


class TestRetryingABusyTable:
    """Writes to one table are serialised, so a batch can be told to wait.

    For a run of hours that is a normal event: the values are computed and
    resending costs nothing, while losing them costs whatever they took.
    """

    def gen(self):
        class Slow(numberdb.Generator):
            parameters = ('n',)
            type = 'Q'
            tid = 'T7'

            def enumerate(self, limit=2):
                for n in range(1, limit + 1):
                    yield {'n': n}

            def value(self, params, digits):
                return Fraction(1, params['n'])

        return Slow()

    def test_a_busy_answer_is_tried_again(self):
        calls = []

        class Busy(Sent):
            def opener(self, request, timeout=None):
                calls.append(request)
                if request.full_url.endswith('/entries') and len(
                        [r for r in calls if r.full_url.endswith('/entries')]) == 1:
                    raise urllib.error.HTTPError(
                        'http://x/', 429, 'busy', {'Retry-After': '0'},
                        _Readable(b'{"error": "busy"}'))
                return _Readable(json.dumps({'tid': 'T7'}).encode('utf8'))

        numberdb.publish(self.gen(), batch=2, limit=2, preflight=False,
                         client=Busy().client())
        entries = [r for r in calls if r.full_url.endswith('/entries')]
        assert len(entries) == 2

    def test_a_refused_document_is_not_tried_again(self):
        """Repeating it will not make it true."""
        calls = []

        class Refusing(Sent):
            def opener(self, request, timeout=None):
                calls.append(request)
                raise urllib.error.HTTPError(
                    'http://x/', 413, 'too big', {},
                    _Readable(b'{"error": "over a size limit"}'))

        with pytest.raises(numberdb.TooBig):
            numberdb.publish(self.gen(), batch=2, limit=2, preflight=False,
                             client=Refusing().client())
        assert len(calls) == 1


class TestCheckingBeforeComputing:
    """A generator may run for hours; "no API key was set" is knowable at once."""

    def gen(self, counter):
        class Counted(numberdb.Generator):
            parameters = ('n',)
            type = 'Q'
            tid = 'T7'

            def enumerate(self, limit=3):
                for n in range(1, limit + 1):
                    yield {'n': n}

            def value(self, params, digits):
                counter.append(params['n'])
                return Fraction(1, params['n'])

        return Counted()

    def test_a_missing_key_is_found_before_anything_is_computed(self):
        computed = []
        sent = Sent()
        with pytest.raises(numberdb.Unauthorized):
            numberdb.publish(self.gen(computed), client=sent.client(api_key=''))
        assert computed == []

    def test_a_refusal_is_found_before_anything_is_computed(self):
        computed = []
        sent = Sent(status=403,
                    body=b'{"error": "not yet", "detail": "opens after 5"}')
        with pytest.raises(numberdb.Unauthorized):
            numberdb.publish(self.gen(computed), client=sent.client())
        assert computed == []

    def test_the_check_sends_no_entries(self):
        sent = Sent()
        numberdb.check_writable('T7', client=sent.client())
        body = sent.request.data.decode('utf8')
        assert body.strip() in ('[]', '[]\n')
        assert sent.request.headers['X-entries-mode'] == 'upsert'

    def test_it_can_be_turned_off(self):
        computed = []
        sent = Sent()
        numberdb.publish(self.gen(computed), preflight=False,
                         client=sent.client())
        assert computed == [1, 2, 3]


class TestHoldingATableForARun:
    """The claim covers the run, not one write.

    Without it two generators on one table interleave: neither can amend its
    own revision, and a thousand entries each becomes two thousand revisions.
    """

    def test_taking_it_posts_to_the_lease(self):
        sent = Sent(payload={'held': True, 'expires': 'x', 'minutes': 20})
        numberdb.Lease('T42', run='r1').take() if False else None
        lease = numberdb.Lease('T42', run='r1', client=sent.client())
        lease.take()
        assert sent.request.full_url.endswith('/api/table/42/lease')
        assert sent.request.headers['X-run-id'] == 'r1'

    def test_the_note_is_sent(self):
        sent = Sent(payload={'held': True, 'minutes': 20})
        numberdb.Lease('T42', note='regenerating', client=sent.client()).take()
        assert sent.request.headers['X-lease-note'] == 'regenerating'

    def test_dropping_it_uses_delete(self):
        sent = Sent(payload={'held': False})
        numberdb.Lease('T42', client=sent.client()).drop()
        assert sent.request.get_method() == 'DELETE'

    def test_it_refreshes_well_inside_the_term(self):
        """One entry may take longer than the lease lasts."""
        sent = Sent(payload={'held': True, 'minutes': 30})
        lease = numberdb.Lease('T42', client=sent.client())
        lease.take()
        #A third of the term, so two refreshes can be missed and it still holds.
        assert lease.every == pytest.approx(30 * 60 / 3.0)

    def test_a_table_held_by_somebody_else_is_a_conflict(self):
        sent = Sent(status=409,
                    body=b'{"error": "being generated by somebody else"}')
        with pytest.raises(numberdb.Conflict):
            numberdb.Lease('T42', client=sent.client()).take()

    def test_a_context_manager_takes_and_drops(self):
        calls = []

        class Watching(Sent):
            def opener(self, request, timeout=None):
                calls.append(request.get_method())
                return _Readable(json.dumps(
                    {'held': True, 'minutes': 20}).encode('utf8'))

        with numberdb.Lease('T42', client=Watching().client()):
            pass
        assert calls[0] == 'POST'
        assert calls[-1] == 'DELETE'

    def test_publishing_holds_one_for_the_whole_run(self):
        methods = []

        class Watching(Sent):
            def opener(self, request, timeout=None):
                methods.append((request.get_method(), request.full_url))
                return _Readable(json.dumps(
                    {'tid': 'T7', 'held': True, 'minutes': 20}).encode('utf8'))

        class Slow(numberdb.Generator):
            parameters = ('n',)
            type = 'Q'
            tid = 'T7'

            def enumerate(self, limit=4):
                for n in range(1, limit + 1):
                    yield {'n': n}

            def value(self, params, digits):
                return Fraction(1, params['n'])

        numberdb.publish(Slow(), batch=2, limit=4, preflight=False,
                         client=Watching().client())
        leases = [m for m in methods if m[1].endswith('/lease')]
        assert leases[0][0] == 'POST'
        assert leases[-1][0] == 'DELETE'
