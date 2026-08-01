"""Tests for the client package.

No network and no server: the opener is injected through ``Client``, so these
run anywhere, including in a plain interpreter without Sage.

    python3 -m unittest discover -s clients/python/tests -v
"""

import io
import json
import os
import sys
import unittest
import urllib.error
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numberdb  # noqa: E402
from numberdb import _wire  # noqa: E402


def _client(payload, status=200, headers=None, **kwargs):
    """A Client whose opener answers with ``payload``, so no server is needed."""
    class _Fake(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            self.close()
            return False

    def opener(request, timeout=None):
        opener.request = request
        opener.timeout = timeout
        if status != 200:
            raise urllib.error.HTTPError(
                request.full_url, status, 'error', headers or {}, None)
        return _Fake(json.dumps(payload).encode('utf8'))

    client = numberdb.Client(opener=opener, **kwargs)
    client.opener = opener          # so tests can inspect the request
    return client


def _record(kind_record, exact_text='', title='Pi', param='', url='Pi'):
    return {
        'number': {'number': kind_record, 'exact_text': exact_text,
                   'str_short': exact_text, 'param': param, 'type': 'r'},
        'table': {'tid': 'T1', 'title': title, 'url': url},
    }


class Decoding(unittest.TestCase):
    """A response may select a decoder and nothing else."""

    def test_every_kind_the_server_sends(self):
        cases = [
            ({'kind': 'ZZ', 'value': '7'}, 7),
            ({'kind': 'QQ', 'value': '2/3'}, Fraction(2, 3)),
            ({'kind': 'RIF', 'lower': '1/3', 'upper': '1/2'},
             _wire.RealInterval(Fraction(1, 3), Fraction(1, 2))),
            ({'kind': 'RBF', 'lower': '1/3', 'upper': '1/2'},
             _wire.RealInterval(Fraction(1, 3), Fraction(1, 2))),
        ]
        for record, expected in cases:
            with self.subTest(kind=record['kind']):
                self.assertEqual(_wire.decode(record), expected)

    def test_a_big_integer_is_not_rounded(self):
        """The database holds integers of over a thousand digits."""
        big = '9' * 400
        self.assertEqual(_wire.decode({'kind': 'ZZ', 'value': big}), int(big))

    def test_endpoints_stay_exact(self):
        value = _wire.decode({'kind': 'RIF',
                              'lower': '884279719003555/281474976710656',
                              'upper': '7074237752028441/2251799813685248'})
        self.assertIsInstance(value.lower, Fraction)
        self.assertIsInstance(value.upper, Fraction)
        self.assertLessEqual(value.lower, value.upper)
        self.assertLess(value.lower, Fraction(3141592653589794, 10 ** 15))
        self.assertGreater(value.upper, Fraction(3141592653589793, 10 ** 15))

    def test_a_complex_interval_and_a_p_adic(self):
        box = _wire.decode({'kind': 'CIF', 're_lower': '0', 're_upper': '1',
                            'im_lower': '2', 'im_upper': '3'})
        self.assertEqual(complex(box), complex(0.5, 2.5))
        padic = _wire.decode({'kind': 'Qp', 'prime': '5', 'precision': '20',
                              'lift': '6'})
        self.assertEqual((padic.prime, padic.precision, padic.lift), (5, 20, 6))
        self.assertEqual(str(padic), '6 + O(5^20)')

    def test_values_can_be_put_in_a_set(self):
        """Defining __eq__ drops __hash__, and numbers belong in sets."""
        one = _wire.decode({'kind': 'RIF', 'lower': '1', 'upper': '2'})
        same = _wire.decode({'kind': 'RIF', 'lower': '1', 'upper': '2'})
        other = _wire.decode({'kind': 'Qp', 'prime': '5', 'precision': '2',
                              'lift': '3'})
        self.assertEqual(len({one, same, other}), 2)

    def test_an_unknown_kind_is_refused_by_name(self):
        """Dispatch is a table; a reply cannot name its own decoder."""
        with self.assertRaises(numberdb.UnsupportedNumber) as caught:
            _wire.decode({'kind': 'os.system', 'value': 'rm -rf /'})
        self.assertIn('upgrading', str(caught.exception))

    def test_a_malformed_record_is_refused(self):
        for record in [{'kind': 'ZZ'}, {'kind': 'RIF', 'lower': '1'},
                       'not an object', None, 42]:
            with self.subTest(record=record):
                with self.assertRaises(numberdb.UnsupportedNumber):
                    _wire.decode(record)


class ForwardCompatibility(unittest.TestCase):
    """The server will learn new kinds of number. Old packages must cope.

    Decoding used to happen when a result arrived, so a single unfamiliar kind
    raised out of search() and discarded every other result with it -- one
    addition to the server would have broken every deployed client.
    """

    MIXED = {'results': [
        _record({'kind': 'ZZ', 'value': '7'}, exact_text='7'),
        _record({'kind': 'SomeFutureKind', 'value': '?'}, exact_text='1.23'),
    ], 'messages': []}

    def test_an_unknown_kind_does_not_spoil_the_search(self):
        results = numberdb.search('x', client=_client(self.MIXED))
        self.assertEqual(len(results), 2)

    def test_the_readable_results_are_still_readable(self):
        results = numberdb.search('x', client=_client(self.MIXED))
        self.assertEqual(results[0].value, 7)

    def test_the_unreadable_one_keeps_its_text_and_says_so(self):
        results = numberdb.search('x', client=_client(self.MIXED))
        unknown = results[1]
        self.assertEqual(unknown.exact_text, '1.23')
        self.assertEqual(unknown.kind, 'SomeFutureKind')
        self.assertFalse(unknown.is_readable)
        self.assertEqual(results.unreadable, [unknown])
        with self.assertRaises(numberdb.UnsupportedNumber):
            unknown.value

    def test_every_error_is_catchable_as_one_type(self):
        """So a new failure mode cannot escape an existing handler."""
        for error in [numberdb.UnsupportedNumber, numberdb.RateLimited,
                      numberdb.Unauthorized, numberdb.TransportError]:
            with self.subTest(error=error.__name__):
                self.assertTrue(issubclass(error, numberdb.NumberDBError))


class Searching(unittest.TestCase):

    def test_results_carry_the_number_and_where_it_lives(self):
        client = _client({'results': [
            _record({'kind': 'RIF', 'lower': '3', 'upper': '4'},
                    exact_text='3.14', param='n=1')], 'messages': []})
        results = numberdb.search('pi', client=client)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].exact_text, '3.14')
        self.assertEqual(results[0].table.title, 'Pi')
        self.assertEqual(results[0].kind, 'RIF')
        self.assertIn('Pi#n=1', results[0].url())

    def test_messages_are_text_not_the_websites_css_classes(self):
        client = _client({'results': [], 'messages': [
            {'text': 'We only show the first 100 results.',
             'tags': 'alert-warning'}]})
        results = numberdb.search('x', client=client)
        self.assertEqual(results.messages,
                         ['We only show the first 100 results.'])

    def test_an_empty_search_is_a_list_not_an_error(self):
        results = numberdb.search(
            'x', client=_client({'results': [], 'messages': []}))
        self.assertEqual(list(results), [])

    def test_an_error_payload_is_raised(self):
        with self.assertRaises(numberdb.NumberDBError):
            numberdb.table('T99', client=_client({'error': 'no such table'}))

    def test_a_non_object_payload_is_refused(self):
        with self.assertRaises(numberdb.TransportError):
            numberdb.search('x', client=_client(['not', 'an', 'object']))


class Configuration(unittest.TestCase):

    def setUp(self):
        os.environ.pop('NUMBERDB_API_KEY', None)
        os.environ.pop('NUMBERDB_URL', None)

    tearDown = setUp

    def test_no_key_sends_no_authorization_header(self):
        client = _client({'results': [], 'messages': []})
        numberdb.search('pi', client=client)
        self.assertIsNone(client.opener.request.headers.get('Authorization'))

    def test_a_configured_key_is_sent_as_a_bearer_token(self):
        client = _client({'results': [], 'messages': []}, api_key='secret-key')
        numberdb.search('pi', client=client)
        self.assertEqual(client.opener.request.headers.get('Authorization'),
                         'Bearer secret-key')

    def test_the_environment_supplies_the_key(self):
        """So a shared worksheet need not carry its author's key."""
        os.environ['NUMBERDB_API_KEY'] = 'from-env'
        client = _client({'results': [], 'messages': []})
        numberdb.search('pi', client=client)
        self.assertEqual(client.opener.request.headers.get('Authorization'),
                         'Bearer from-env')

    def test_an_explicit_key_beats_the_environment(self):
        os.environ['NUMBERDB_API_KEY'] = 'from-env'
        client = _client({'results': [], 'messages': []}, api_key='explicit')
        numberdb.search('pi', client=client)
        self.assertEqual(client.opener.request.headers.get('Authorization'),
                         'Bearer explicit')

    def test_two_clients_do_not_share_configuration(self):
        """The reason configuration is not a module global."""
        one = _client({'results': [], 'messages': []}, api_key='one')
        two = _client({'results': [], 'messages': []}, api_key='two')
        self.assertNotEqual(one.api_key, two.api_key)

    def test_the_base_url_can_point_at_a_development_server(self):
        client = _client({'results': [], 'messages': []},
                         base_url='http://localhost:8000/')
        numberdb.search('pi', client=client)
        self.assertTrue(
            client.opener.request.full_url.startswith('http://localhost:8000/'))

    def test_the_timeout_is_configurable(self):
        client = _client({'results': [], 'messages': []}, timeout=5)
        numberdb.search('pi', client=client)
        self.assertEqual(client.opener.timeout, 5)

    def test_the_request_identifies_the_package_and_wire_version(self):
        client = _client({'results': [], 'messages': []})
        numberdb.search('pi', client=client)
        headers = client.opener.request.headers
        self.assertIn('numberdb-python', headers.get('User-agent', ''))
        self.assertTrue(headers.get('X-numberdb-api-version'))


class Failures(unittest.TestCase):

    def setUp(self):
        os.environ.pop('NUMBERDB_API_KEY', None)

    tearDown = setUp

    def test_rate_limiting_says_how_to_lift_it(self):
        client = _client({}, status=429, headers={'Retry-After': '30'})
        with self.assertRaises(numberdb.RateLimited) as caught:
            numberdb.search('pi', client=client)
        self.assertEqual(caught.exception.retry_after, 30)
        self.assertIn('API key', str(caught.exception))

    def test_a_rejected_key_is_distinguished_from_a_rate_limit(self):
        client = _client({}, status=403, api_key='bad')
        with self.assertRaises(numberdb.Unauthorized):
            numberdb.search('pi', client=client)

    def test_an_unreachable_server_is_reported_plainly(self):
        def opener(request, timeout=None):
            raise urllib.error.URLError('connection refused')
        client = numberdb.Client(opener=opener)
        with self.assertRaises(numberdb.TransportError):
            numberdb.search('pi', client=client)


class WithoutSage(unittest.TestCase):
    """The package must work in a plain interpreter."""

    def test_importing_does_not_pull_in_sage(self):
        self.assertNotIn('sage', sys.modules,
                         'importing numberdb must not import Sage')

    def test_asking_for_a_sage_object_explains_what_is_missing(self):
        if 'sage' in sys.modules:
            self.skipTest('running inside Sage')
        result = numberdb.search('pi', client=_client({'results': [
            _record({'kind': 'ZZ', 'value': '7'})], 'messages': []}))[0]
        self.assertEqual(result.value, 7)
        with self.assertRaises(ImportError) as caught:
            result.sage()
        self.assertIn('exact_text', str(caught.exception))


class Metadata(unittest.TestCase):

    def test_the_version_is_not_declared_twice(self):
        """Two declarations drift; the installed metadata is the one truth."""
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'numberdb', '__init__.py')
        with open(path) as handle:
            source = handle.read()
        self.assertNotIn("__version__ = '0.1", source)

    def test_the_public_names_all_exist(self):
        for name in numberdb.__all__:
            with self.subTest(name=name):
                self.assertTrue(hasattr(numberdb, name), name)


if __name__ == '__main__':
    unittest.main()
