"""Tests for the client package.

No network and no server: the transport is injected, so these run anywhere,
including in a plain interpreter without Sage.

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
from numberdb import _http, _wire  # noqa: E402


def _response(payload, status=200, headers=None):
    """A urlopen stand-in returning ``payload`` as JSON."""
    class _Fake(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            self.close()
            return False

    def urlopen(request, timeout=None):
        urlopen.request = request
        if status != 200:
            raise urllib.error.HTTPError(
                request.full_url, status, 'error', headers or {}, None)
        return _Fake(json.dumps(payload).encode('utf8'))

    return urlopen


def _number(kind_record, exact_text='', title='Pi', param='', url='Pi'):
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
             _wire.Interval(Fraction(1, 3), Fraction(1, 2))),
            ({'kind': 'RBF', 'lower': '1/3', 'upper': '1/2'},
             _wire.Interval(Fraction(1, 3), Fraction(1, 2))),
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
        #The exact endpoints of pi as the server sends them; they bracket it
        #without ever becoming floats on the way in.
        self.assertLessEqual(value.lower, value.upper)
        self.assertLess(value.lower, Fraction(3141592653589794, 10 ** 15))
        self.assertGreater(value.upper, Fraction(3141592653589793, 10 ** 15))

    def test_a_complex_box_and_a_p_adic(self):
        box = _wire.decode({'kind': 'CIF', 're_lower': '0', 're_upper': '1',
                            'im_lower': '2', 'im_upper': '3'})
        self.assertEqual(complex(box), complex(0.5, 2.5))
        padic = _wire.decode({'kind': 'Qp', 'prime': '5', 'precision': '20',
                              'lift': '6'})
        self.assertEqual((padic.prime, padic.precision, padic.lift), (5, 20, 6))

    def test_an_unknown_kind_is_refused_by_name(self):
        """Dispatch is a table; a reply cannot name its own decoder."""
        with self.assertRaises(_wire.UnsupportedNumber) as caught:
            _wire.decode({'kind': 'os.system', 'value': 'rm -rf /'})
        self.assertIn('upgrading', str(caught.exception))

    def test_a_malformed_record_is_refused(self):
        for record in [{'kind': 'ZZ'}, {'kind': 'RIF', 'lower': '1'},
                       'not an object', None, 42]:
            with self.subTest(record=record):
                with self.assertRaises(_wire.UnsupportedNumber):
                    _wire.decode(record)


class Searching(unittest.TestCase):

    def test_results_carry_the_number_and_where_it_lives(self):
        urlopen = _response({'results': [
            _number({'kind': 'RIF', 'lower': '3', 'upper': '4'},
                    exact_text='3.14', param='n=1')], 'messages': []})
        results = numberdb.search('pi', urlopen=urlopen)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].exact_text, '3.14')
        self.assertEqual(results[0].table.title, 'Pi')
        self.assertEqual(results[0].kind, 'RIF')
        self.assertIn('Pi#n=1', results[0].url())

    def test_messages_are_kept_rather_than_printed(self):
        urlopen = _response({'results': [], 'messages': [
            {'text': 'We only show the first 100 results.'}]})
        results = numberdb.search('x', urlopen=urlopen)
        self.assertEqual(results.warnings,
                         ['We only show the first 100 results.'])

    def test_an_empty_search_is_a_list_not_an_error(self):
        results = numberdb.search(
            'x', urlopen=_response({'results': [], 'messages': []}))
        self.assertEqual(list(results), [])


class Authentication(unittest.TestCase):

    def setUp(self):
        numberdb.api_key = None
        os.environ.pop('NUMBERDB_API_KEY', None)

    tearDown = setUp

    def test_no_key_sends_no_authorization_header(self):
        urlopen = _response({'results': [], 'messages': []})
        numberdb.search('pi', urlopen=urlopen)
        self.assertIsNone(urlopen.request.headers.get('Authorization'))

    def test_a_configured_key_is_sent_as_a_bearer_token(self):
        numberdb.api_key = 'secret-key'
        urlopen = _response({'results': [], 'messages': []})
        numberdb.search('pi', urlopen=urlopen)
        self.assertEqual(urlopen.request.headers.get('Authorization'),
                         'Bearer secret-key')

    def test_the_environment_supplies_the_key(self):
        """So a shared worksheet need not carry its author's key."""
        os.environ['NUMBERDB_API_KEY'] = 'from-env'
        urlopen = _response({'results': [], 'messages': []})
        numberdb.search('pi', urlopen=urlopen)
        self.assertEqual(urlopen.request.headers.get('Authorization'),
                         'Bearer from-env')

    def test_rate_limiting_says_how_to_lift_it(self):
        urlopen = _response({}, status=429, headers={'Retry-After': '30'})
        with self.assertRaises(numberdb.RateLimited) as caught:
            numberdb.search('pi', urlopen=urlopen)
        self.assertEqual(caught.exception.retry_after, 30)
        self.assertIn('API key', str(caught.exception))

    def test_a_rejected_key_is_distinguished_from_a_rate_limit(self):
        numberdb.api_key = 'bad'
        urlopen = _response({}, status=403)
        with self.assertRaises(numberdb.Unauthorized):
            numberdb.search('pi', urlopen=urlopen)

    def test_an_unreachable_server_is_reported_plainly(self):
        def urlopen(request, timeout=None):
            raise urllib.error.URLError('connection refused')
        with self.assertRaises(numberdb.NumberDBError):
            numberdb.search('pi', urlopen=urlopen)


class WithoutSage(unittest.TestCase):
    """The package must work in a plain interpreter."""

    def test_importing_does_not_pull_in_sage(self):
        self.assertNotIn('sage', sys.modules,
                         'importing numberdb must not import Sage')

    def test_asking_for_a_sage_object_explains_what_is_missing(self):
        if 'sage' in sys.modules:
            self.skipTest('running inside Sage')
        result = numberdb.search('pi', urlopen=_response({'results': [
            _number({'kind': 'ZZ', 'value': '7'})], 'messages': []}))[0]
        self.assertEqual(result.value, 7)
        with self.assertRaises(ImportError) as caught:
            result.sage()
        self.assertIn('exact_text', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
