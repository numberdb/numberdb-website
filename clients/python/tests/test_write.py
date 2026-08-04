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
