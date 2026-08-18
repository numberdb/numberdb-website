"""Tests for the client package.

No network and no server: the opener is injected through ``Client``, so these
run anywhere, including in a plain interpreter without Sage.

    python3 -m unittest discover -s clients/python/tests -v
"""

import importlib.util
import io
import json
import os
import sys
import unittest
import urllib.error
import urllib.parse
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numberdb  # noqa: E402
from numberdb import _wire  # noqa: E402

#Recorded at import, not inside a test: other tests convert values to Sage,
#which puts it in sys.modules, and a later check would then measure test order
#rather than what importing the package costs.
SAGE_IMPORTED_BY_THE_PACKAGE = 'sage' in sys.modules


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
        padic = _wire.decode({'kind': 'Qp', 'prime': '5', 'valuation': '0',
                              'unit': '6', 'precision': '20'})
        self.assertEqual((padic.prime, padic.valuation, padic.unit,
                          padic.precision_absolute), (5, 0, 6, 20))
        self.assertEqual(str(padic), '6 + O(5^20)')

    def test_values_can_be_put_in_a_set(self):
        """Defining __eq__ drops __hash__, and numbers belong in sets."""
        one = _wire.decode({'kind': 'RIF', 'lower': '1', 'upper': '2'})
        same = _wire.decode({'kind': 'RIF', 'lower': '1', 'upper': '2'})
        other = _wire.decode({'kind': 'Qp', 'prime': '5', 'valuation': '0',
                              'unit': '3', 'precision': '2'})
        self.assertEqual(len({one, same, other}), 2)

    def test_an_unknown_kind_is_refused_by_name(self):
        """Dispatch is a table; a reply cannot name its own decoder."""
        with self.assertRaises(numberdb.UnsupportedNumberError) as caught:
            _wire.decode({'kind': 'os.system', 'value': 'rm -rf /'})
        self.assertIn('upgrading', str(caught.exception))

    def test_a_malformed_record_is_refused(self):
        for record in [{'kind': 'ZZ'}, {'kind': 'RIF', 'lower': '1'},
                       'not an object', None, 42]:
            with self.subTest(record=record):
                with self.assertRaises(numberdb.UnsupportedNumberError):
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
        with self.assertRaises(numberdb.UnsupportedNumberError):
            unknown.value

    def test_every_error_is_catchable_as_one_type(self):
        """So a new failure mode cannot escape an existing handler."""
        for error in [numberdb.UnsupportedNumberError, numberdb.RateLimitError,
                      numberdb.UnauthorizedError, numberdb.TransportError]:
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
        #Both forms: the query the server can resolve, and the fragment the
        #browser scrolls to.
        self.assertIn('?entry=n%3D1', results[0].url())
        self.assertTrue(results[0].url().endswith('#n=1'), results[0].url())

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
        with self.assertRaises(numberdb.RateLimitError) as caught:
            numberdb.search('pi', client=client)
        self.assertEqual(caught.exception.retry_after, 30)
        self.assertIn('API key', str(caught.exception))

    def test_a_rejected_key_is_distinguished_from_a_rate_limit(self):
        client = _client({}, status=403, api_key='bad')
        with self.assertRaises(numberdb.UnauthorizedError):
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
        """Sage costs seconds to import; most uses never need it."""
        self.assertFalse(SAGE_IMPORTED_BY_THE_PACKAGE,
                         'importing numberdb must not import Sage')

    def test_asking_for_a_sage_object_explains_what_is_missing(self):
        #Whether Sage can be imported, not whether it has been. Under
        #`sage -python` it is available but not yet in sys.modules, so the old
        #guard let this run in the one environment where it cannot hold.
        import importlib.util

        if importlib.util.find_spec('sage') is not None:
            self.skipTest('Sage is installed here')
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


class UnboundedValues(unittest.TestCase):
    """The database holds numbers past what a float can bound.

    310 stored values are beyond a double, and the server sends that end as
    '-infinity' or 'infinity'. QQ has no infinite element, so converting such a
    value to Sage used to raise "cannot convert NaN or infinity to rational
    number" -- .sage() was simply broken for them.
    """

    RECORD = {'kind': 'RIF', 'lower': '-infinity',
              'upper': '-17976931348623157081452742373'}

    def test_an_infinite_endpoint_decodes(self):
        value = _wire.decode(self.RECORD)
        self.assertEqual(value.lower, float('-inf'))
        self.assertIsInstance(value.upper, Fraction)

    def test_such_a_value_still_reaches_sage(self):
        try:
            import sage  # noqa: F401
        except ImportError:
            self.skipTest('needs SageMath')
        interval = _wire.to_sage(_wire.decode(self.RECORD))
        self.assertTrue(interval.lower().is_infinity())


class PAdicNormalForm(unittest.TestCase):
    """Q_p is not Z_p, and a ball has exactly one spelling.

    An integer lift spans Z_p only, so every value of negative order -- 1/5 in
    Q_5 -- was unrepresentable; 1000 of the 6712 stored p-adics have one. A bare
    representative fixed that but was not canonical: 1 and 1 + p**k denote the
    same ball at precision k and compared unequal.
    """

    def test_a_value_off_the_integers(self):
        value = _wire.decode({'kind': 'Qp', 'prime': '5', 'valuation': '-1',
                              'unit': '1', 'precision': '19'})
        self.assertEqual(value.valuation, -1)
        self.assertEqual(value.value, Fraction(1, 5))
        self.assertEqual(value.precision_relative, 20)

    def test_congruent_spellings_are_one_ball(self):
        """1 and 126 = 1 + 5**3 at precision 3. Sage agrees they are equal."""
        one = _wire.PAdic(5, 0, 1, 3)
        other = _wire.PAdic(5, 0, 126, 3)
        self.assertEqual(one, other)
        self.assertEqual(len({one, other}), 1)

    def test_a_unit_divisible_by_the_prime_is_refused(self):
        """Normalised means normalised; 5 is not a unit in Q_5."""
        with self.assertRaises(ValueError):
            _wire.PAdic(5, 0, 5, 3)

    def test_zero_has_no_order_and_no_unit(self):
        zero = _wire.PAdic(5, 20, 0, 20)
        self.assertEqual(zero.unit, 0)
        self.assertEqual(zero.value, 0)

    def test_such_a_value_reaches_sage(self):
        try:
            import sage  # noqa: F401
        except ImportError:
            self.skipTest('needs SageMath')
        from sage.rings.all import Qp, QQ
        self.assertEqual(_wire.to_sage(_wire.PAdic(5, -1, 1, 19)),
                         Qp(5, 20)(QQ(1) / 5))


class BothPrecisionsAreNamed(unittest.TestCase):
    """Absolute and relative coincide at valuation zero and diverge elsewhere,
    so neither may be a bare ``precision`` a reader has to resolve."""

    def test_relative_follows_from_absolute_and_the_order(self):
        for valuation, absolute, relative in [(0, 20, 20), (-1, 19, 20),
                                              (2, 22, 20)]:
            with self.subTest(valuation=valuation):
                value = _wire.PAdic(5, valuation, 1, absolute)
                self.assertEqual(value.precision_relative, relative)

    def test_the_string_form_states_the_absolute_one(self):
        self.assertEqual(str(_wire.PAdic(5, -1, 1, 19)), '1/5 + O(5^19)')

    def test_sage_receives_the_absolute_one(self):
        try:
            import sage  # noqa: F401
        except ImportError:
            self.skipTest('needs SageMath')
        for valuation, absolute in [(-1, 19), (0, 20), (2, 22)]:
            with self.subTest(valuation=valuation):
                converted = _wire.to_sage(_wire.PAdic(5, valuation, 1, absolute))
                self.assertEqual(int(converted.precision_absolute()), absolute)


class SageFlavour(unittest.TestCase):
    """numberdb.sage returns Sage objects, with no mode to remember.

    An extra cannot do this -- pip extras install dependencies, and the code is
    identical either way -- and sniffing for Sage would make the same program
    behave differently in different environments. The import line says which
    world you are in, once.
    """

    def _sage_module(self):
        try:
            import numberdb.sage as flavoured
        except ImportError as error:
            self.skipTest(str(error)[:60])
        return flavoured

    def test_it_refuses_to_import_without_sage_and_says_why(self):
        if importlib.util.find_spec('sage') is not None:
            self.skipTest('Sage is installed')
        with self.assertRaises(ImportError) as caught:
            import numberdb.sage  # noqa: F401
        self.assertIn('numberdb', str(caught.exception))

    def test_values_come_back_as_sage_objects(self):
        flavoured = self._sage_module()
        client = _client({'results': [
            _record({'kind': 'RIF', 'lower': '1/3', 'upper': '1/2'})],
            'messages': []})
        value = flavoured.search('x', client=client)[0].value
        self.assertTrue(hasattr(value, 'parent'), repr(value))
        self.assertIn('Interval', str(value.parent()))

    def test_the_plain_module_is_unaffected(self):
        """Importing the Sage flavour must not change plain numberdb."""
        self._sage_module()
        client = _client({'results': [
            _record({'kind': 'ZZ', 'value': '7'})], 'messages': []})
        self.assertIsInstance(numberdb.search('x', client=client)[0].value, int)

    def test_it_stands_in_for_the_package(self):
        """So `import numberdb.sage as numberdb` works wholesale."""
        flavoured = self._sage_module()
        for name in ['search', 'table', 'tag', 'configure', 'Client',
                     'NumberDBError', 'RateLimitError', 'UnsupportedNumberError']:
            with self.subTest(name=name):
                self.assertTrue(hasattr(flavoured, name), name)

    def test_a_submodule_named_sage_does_not_shadow_real_sage(self):
        flavoured = self._sage_module()
        self.assertEqual(flavoured.__name__, 'numberdb.sage')
        import sage
        self.assertEqual(sage.__name__, 'sage')


class NoSageExtra(unittest.TestCase):
    """There must be no [sage] extra.

    It would be typed by the people it can hurt. Inside a full SageMath,
    `sage -pip install numberdb[sage]` installs passagemath over the top: the
    passagemath-flint wheel writes 383 files under sage/, 349 of which already
    exist there, including compiled .so extensions. pip reports no conflict,
    because Sage's own files belong to no pip distribution and so cannot be
    seen to clash.
    """

    def declared(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'pyproject.toml')
        with open(path) as handle:
            #Comments explain why there is no sage extra and name it while
            #doing so, so they are dropped before looking.
            return '\n'.join(line for line in handle
                             if not line.lstrip().startswith('#'))

    def test_the_package_declares_no_sage_extra(self):
        """No `sage` extra, by name.

        This used to forbid *any* extra, which was a proxy for the real rule
        and stopped being true the moment the package gained a `docs` one for
        pdoc -- a development tool that hurts nobody. The rule is about Sage.
        """
        declared = self.declared()
        for spelling in ('[sage]', 'sage =', 'sage=', '"sage"', "'sage'"):
            self.assertNotIn(spelling, declared.replace('numberdb.sage', ''))

    def test_nothing_is_required_to_install_it(self):
        """The extras that do exist are for developing it, not for using it."""
        declared = self.declared()
        self.assertIn('dependencies = []', declared)
        self.assertNotIn('numberdb[sage]', declared)


class BaseUrlJoining(unittest.TestCase):
    """A configured base URL must reach the server it names.

    urljoin replaces a final path segment that has no trailing slash, so
    'https://example.org/numberdb' would send requests to
    'https://example.org/api/search' -- the prefix silently dropped, and
    possibly a different application answering.
    """

    def setUp(self):
        os.environ.pop('NUMBERDB_URL', None)

    tearDown = setUp

    def test_the_default_is_numberdb_org(self):
        self.assertEqual(numberdb.Client().base_url, 'https://numberdb.org/')

    def test_every_reasonable_spelling_reaches_the_right_path(self):
        cases = [
            ('https://numberdb.org/', 'https://numberdb.org/api/'),
            ('https://numberdb.org', 'https://numberdb.org/api/'),
            ('http://localhost:8000', 'http://localhost:8000/api/'),
            ('https://example.org/numberdb',
             'https://example.org/numberdb/api/'),
            ('https://example.org/numberdb/',
             'https://example.org/numberdb/api/'),
        ]
        for configured, expected in cases:
            with self.subTest(base_url=configured):
                client = _client({'results': [], 'messages': []},
                                 base_url=configured)
                numberdb.search('pi', client=client)
                self.assertTrue(
                    client.opener.request.full_url.startswith(expected),
                    '%s -> %s' % (configured,
                                  client.opener.request.full_url))

    def test_the_environment_can_set_it(self):
        os.environ['NUMBERDB_URL'] = 'http://localhost:8000'
        self.assertEqual(numberdb.Client().base_url, 'http://localhost:8000/')

    def test_an_explicit_url_beats_the_environment(self):
        os.environ['NUMBERDB_URL'] = 'http://localhost:8000'
        self.assertEqual(numberdb.Client(base_url='https://elsewhere.test').base_url,
                         'https://elsewhere.test/')


class ExactConversion(unittest.TestCase):
    """Scalars become exact rationals, so interval arithmetic cannot narrow.

    Rounding an endpoint inward is a silent false negative: the number is in
    the database and the search does not find it. Converting first and doing
    the arithmetic in Fraction removes the possibility rather than managing it.
    """

    def test_python_scalars_convert_exactly(self):
        from numberdb._convert import to_exact
        cases = [(7, Fraction(7)), (Fraction(2, 3), Fraction(2, 3)),
                 ('1/3', Fraction(1, 3)), ('0.1', Fraction(1, 10)),
                 (0.5, Fraction(1, 2))]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(to_exact(value), expected)

    def test_a_float_converts_to_its_own_value_not_a_prettier_one(self):
        """0.1 and '0.1' are different numbers; each converts to itself."""
        from numberdb._convert import to_exact
        self.assertEqual(to_exact('0.1'), Fraction(1, 10))
        self.assertNotEqual(to_exact(0.1), Fraction(1, 10))
        self.assertEqual(to_exact(0.1), Fraction(0.1))

    def test_ball_arithmetic_does_not_narrow(self):
        """The case floats would have broken: center - radius rounding inward."""
        from numberdb._convert import to_exact
        center, radius = 3.14159266, 1e-8
        lower = to_exact(center) - to_exact(radius)
        upper = to_exact(center) + to_exact(radius)
        #Exact, so the endpoints bracket every float in the ball.
        self.assertLessEqual(lower, to_exact(center - radius))
        self.assertGreaterEqual(upper, to_exact(center + radius))
        self.assertEqual(upper - lower, 2 * to_exact(radius))

    def test_a_bool_is_not_a_number(self):
        from numberdb._convert import to_exact
        for value in [True, False]:
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    to_exact(value)

    def test_things_that_cannot_state_themselves_exactly_are_refused(self):
        from numberdb._convert import to_exact
        for value in [None, [1], object(), 'not a number', complex(1, 2)]:
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    to_exact(value)

    def test_an_object_with_numerator_that_is_not_a_rational_is_refused(self):
        """Sage polynomials and p-adics both have numerator() and
        denominator(), returning objects of their own type."""
        from numberdb._convert import to_exact

        class NotARational:
            def numerator(self):
                return self          # a polynomial returns a polynomial

            def denominator(self):
                return 1

        with self.assertRaises(TypeError):
            to_exact(NotARational())


class ExactConversionOfSageValues(unittest.TestCase):
    """The same contract for Sage's numbers."""

    def setUp(self):
        try:
            import sage  # noqa: F401
        except ImportError:
            self.skipTest('needs SageMath')

    def test_sage_scalars_convert_exactly(self):
        from sage.rings.all import QQ, RR, ZZ
        from numberdb._convert import to_exact
        self.assertEqual(to_exact(ZZ(7)), Fraction(7))
        self.assertEqual(to_exact(QQ(2) / 3), Fraction(2, 3))
        self.assertEqual(to_exact(RR(0.5)), Fraction(1, 2))

    def test_a_sage_rational_is_not_mangled_the_way_fraction_mangles_it(self):
        """Fraction(QQ(1)/3) does not raise -- it stores the bound methods."""
        from sage.rings.all import QQ
        from numberdb._convert import to_exact
        self.assertEqual(to_exact(QQ(1) / 3), Fraction(1, 3))

    def test_a_sage_polynomial_is_refused_despite_having_a_numerator(self):
        from sage.rings.all import QQ
        from numberdb._convert import to_exact
        ring = QQ['x']
        with self.assertRaises(TypeError):
            to_exact(ring([-1, 1]))

    def test_a_sage_p_adic_is_refused_despite_having_a_numerator(self):
        from sage.rings.all import Qp
        from numberdb._convert import to_exact
        with self.assertRaises(TypeError):
            to_exact(Qp(5, 20)(6))


class TypedSearches(unittest.TestCase):
    """Each takes basic arguments, so nothing has to be constructed first."""

    def _sent(self, call, *args, **keywords):
        client = _client({'results': [], 'messages': []})
        call(*args, client=client, **keywords)
        query = urllib.parse.parse_qs(
            urllib.parse.urlparse(client.opener.request.full_url).query)
        return query

    def test_an_integer_is_sent_as_an_exact_value(self):
        sent = self._sent(numberdb.search_integer, 7)
        self.assertEqual(json.loads(sent['number'][0]),
                         {'kind': 'ZZ', 'value': '7'})

    def test_a_rational_takes_numerator_and_denominator(self):
        self.assertEqual(json.loads(self._sent(
            numberdb.search_rational, 2, 3)['number'][0]),
            {'kind': 'QQ', 'value': '2/3'})
        #The denominator defaults, so a Fraction may be passed alone.
        self.assertEqual(json.loads(self._sent(
            numberdb.search_rational, Fraction(2, 3))['number'][0]),
            {'kind': 'QQ', 'value': '2/3'})

    def test_a_non_integer_is_refused_by_search_integer(self):
        with self.assertRaises(ValueError):
            numberdb.search_integer(Fraction(1, 2))

    def test_a_ball_becomes_an_exact_interval(self):
        """Converted before the arithmetic, so the width is exactly 2r."""
        sent = json.loads(self._sent(
            numberdb.search_real_ball, '1/2', '1/8')['number'][0])
        self.assertEqual(Fraction(sent['lower']), Fraction(3, 8))
        self.assertEqual(Fraction(sent['upper']), Fraction(5, 8))

    def test_endpoints_given_the_wrong_way_round_are_sorted(self):
        sent = json.loads(self._sent(
            numberdb.search_real_interval, 2, 1)['number'][0])
        self.assertEqual((sent['lower'], sent['upper']), ('1', '2'))

    def test_a_complex_ball_widens_to_the_square_that_contains_it(self):
        sent = json.loads(self._sent(
            numberdb.search_complex_ball, 0, 0, '1/4')['number'][0])
        self.assertEqual(Fraction(sent['re_lower']), Fraction(-1, 4))
        self.assertEqual(Fraction(sent['im_upper']), Fraction(1, 4))

    def test_a_p_adic_needs_its_precision_named(self):
        with self.assertRaises(TypeError):
            numberdb.search_p_adic(5, 0, 1)
        with self.assertRaises(TypeError):
            numberdb.search_p_adic(5, 0, 1, absolute_precision=3,
                                   relative_precision=3)

    def test_relative_precision_is_converted_to_absolute(self):
        sent = json.loads(self._sent(
            numberdb.search_p_adic, 5, -1, 1, relative_precision=20)['number'][0])
        self.assertEqual(sent['precision'], 19)
        self.assertEqual(sent['valuation'], -1)

    def test_text_goes_by_the_websites_grammar(self):
        self.assertEqual(self._sent(numberdb.search_text, '3.14')['text'],
                         ['3.14'])

    def test_a_polynomial_is_not_merely_a_search_term(self):
        """Different questions, so different parameters.

        A search term is ambiguous -- it might be a title or a tag -- and
        because polynomials are canonicalised under renaming of variables, a
        single-term one would match any word at all. The search bar ignores
        those on purpose. Saying "this is a polynomial" removes the ambiguity.
        """
        sent = self._sent(numberdb.search_polynomial, 'x^2-2')
        self.assertEqual(sent['polynomial'], ['x^2-2'])
        self.assertNotIn('text', sent)

    def test_an_expression_is_the_only_one_that_asks_the_server_to_compute(self):
        client = _client({'results': [], 'messages': []})
        numberdb.search_by_expression('pi', client=client)
        self.assertIn('/api/search', client.opener.request.full_url)
        client = _client({'results': [], 'messages': []})
        numberdb.search_integer(7, client=client)
        self.assertIn('/api/lookup', client.opener.request.full_url)


class TheContainer(unittest.TestCase):
    """search() takes an object; the search_* functions take components."""

    def _kind(self, value):
        client = _client({'results': [], 'messages': []})
        numberdb.search(value, client=client)
        query = urllib.parse.parse_qs(
            urllib.parse.urlparse(client.opener.request.full_url).query)
        if 'text' in query:
            return 'text'
        return json.loads(query['number'][0])['kind']

    def test_python_and_package_types_are_dispatched(self):
        cases = [(7, 'ZZ'), (Fraction(2, 3), 'QQ'), ('3.14', 'text'),
                 (numberdb.RealInterval(Fraction(1), Fraction(2)), 'RIF'),
                 (numberdb.PAdic(5, -1, 1, 19), 'Qp'),
                 (numberdb.ComplexInterval(
                     numberdb.RealInterval(Fraction(0), Fraction(1)),
                     numberdb.RealInterval(Fraction(2), Fraction(3))), 'CIF')]
        for value, expected in cases:
            with self.subTest(value=repr(value)[:30]):
                self.assertEqual(self._kind(value), expected)

    def test_a_bare_float_is_refused_and_says_what_to_do(self):
        with self.assertRaises(TypeError) as caught:
            numberdb.search(3.14159)
        self.assertIn('search_real_ball', str(caught.exception))

    def test_a_bool_is_not_a_number(self):
        with self.assertRaises(TypeError):
            numberdb.search(True)

    def test_something_unsearchable_is_refused_by_name(self):
        with self.assertRaises(TypeError):
            numberdb.search(object())


class OneWrittenFormForApproximateReals(unittest.TestCase):
    """Whatever a generator computes with, the table gets `3.14159?`.

    That form says what this database means by an approximate number: the
    digits written are known, and the last one is uncertain by one. A table
    holding four spellings of that would make every reader work out which
    convention each row was written under.
    """

    def setUp(self):
        try:
            import sage.all  # noqa: F401
        except ImportError:
            self.skipTest('needs SageMath')

    def test_every_sage_real_type_is_written_the_same_way(self):
        from sage.all import (ComplexBallField, ComplexIntervalField,
                              RealBallField, RealIntervalField, zeta)

        from numberdb._write import to_text

        precision = numberdb.bits(20)
        wanted = '1.2020569031595942854'
        self.assertEqual(to_text(RealIntervalField(precision)(zeta(3)), 20),
                         wanted)
        self.assertEqual(to_text(RealBallField(precision)(zeta(3)), 20),
                         wanted)
        self.assertEqual(
            to_text(ComplexIntervalField(precision)(zeta(3), 1), 20),
            wanted + ' + i * 1')
        self.assertEqual(
            to_text(ComplexBallField(precision)(zeta(3), 1), 20),
            wanted + ' + i * 1')

    def test_it_is_a_plain_decimal_and_carries_no_marker(self):
        """`3.14` IS the interval (3.13, 3.15). Sage writes `3.14?` for that;
        the corpus writes it plain, in 36,946 of its 45,834 values, and not one
        of them ends in a question mark."""
        from sage.all import RealIntervalField, zeta

        from numberdb._write import to_text

        written = to_text(RealIntervalField(numberdb.bits(20))(zeta(3)), 20)
        self.assertNotIn('?', written)
        self.assertNotIn('+/-', written)

    def test_exactly_the_digits_asked_for(self):
        """Not a few more because the field happened to be built wider."""
        from sage.all import RealIntervalField, zeta

        from numberdb._write import to_text

        for digits in (10, 40, 100):
            with self.subTest(digits=digits):
                written = to_text(
                    RealIntervalField(numberdb.bits(digits))(zeta(2)), digits)
                significant = written.lstrip('-').replace('.', '').lstrip('0')
                self.assertEqual(len(significant), digits)

    def test_significant_digits_not_decimal_places(self):
        """Counting places wrote 1234.567 for three digits, and wrote 0.000 --
        not a loss of precision but a loss of the number."""
        from numberdb import RealInterval
        from numberdb._write import to_text

        self.assertEqual(to_text(RealInterval('1234.5678', '1234.5679'), 3),
                         '1.23e3')
        self.assertEqual(
            to_text(RealInterval('0.000012345', '0.000012346'), 3),
            '0.0000123')

    def test_agreement_is_looked_for_at_every_length(self):
        """[2.4999999, 2.5000001] disagrees at one digit -- 2 against 3 -- and
        agrees at every length after that. Stopping at the first disagreement
        wrote `2` for a number known to seven places."""
        from numberdb import RealInterval
        from numberdb._write import to_text

        self.assertEqual(to_text(RealInterval('2.4999999', '2.5000001'), 6),
                         '2.50000')

    def test_trailing_zeros_before_the_point_are_never_written(self):
        """They are a claim, under this convention. `123000000` says the value
        is known to (122999999, 123000001); with four digits known the truth is
        (122950000, 123050000), an overclaim by five orders of magnitude."""
        from numberdb import RealInterval
        from numberdb._write import to_text

        self.assertEqual(to_text(RealInterval('1.2299e8', '1.2301e8'), 4),
                         '1.230e8')

    def test_the_exponent_is_spelled_as_the_corpus_spells_it(self):
        """`1.23e160`, no plus and no padding, as 708 of its values are."""
        from numberdb import RealInterval
        from numberdb._write import to_text

        written = to_text(RealInterval('1.2299e160', '1.2301e160'), 4)
        self.assertEqual(written, '1.230e160')
        self.assertNotIn('e+', written)

    def test_small_values_stay_in_fixed_point_while_they_are_readable(self):
        """A trailing zero after the point is significant, not a claim."""
        from numberdb import RealInterval
        from numberdb._write import to_text

        self.assertEqual(
            to_text(RealInterval('0.00012299', '0.00012301'), 4),
            '0.0001230')

    def test_an_interval_too_wide_for_any_decimal_becomes_a_ball(self):
        """`5` for something in (1, 9) would claim (4, 6)."""
        from numberdb import RealInterval
        from numberdb._write import to_text

        self.assertIn('+/-', to_text(RealInterval('1', '9'), 5))

    def test_the_ball_form_is_available_for_tables_that_use_it(self):
        from sage.all import RealIntervalField, zeta

        from numberdb._write import to_text

        written = to_text(RealIntervalField(numberdb.bits(20))(zeta(3)), 20,
                          'ball')
        self.assertIn('+/-', written)

    def test_a_ball_is_not_truncated_as_text(self):
        """`[1.20205690 +/- 2.8e-25]` cut to twenty characters keeps the centre
        and mangles the radius into `+/- 0.00000`, claiming an uncertainty a
        hundred million times too wide."""
        from sage.all import RealBallField, zeta

        from numberdb._write import to_text

        written = to_text(RealBallField(numberdb.bits(20))(zeta(3)), 20)
        self.assertNotIn('+/-', written)
        self.assertEqual(written, '1.2020569031595942854')

    def test_ball_fields_were_refused_outright_before_this(self):
        """Sage names them `Real ball field`, not `Real Ball Field`, so a test
        for 'Ball' matched nothing and every ball raised."""
        from sage.all import RealBallField

        self.assertNotIn('Ball', str(RealBallField(53)))
        self.assertIn('ball', str(RealBallField(53)))


class ExceptionsAreNamedAsExceptions(unittest.TestCase):
    """Every public exception ends in Error, so a reader knows what it is.

    The family used to be half and half -- NumberDBError and TransportError
    beside RateLimited, Unauthorized, Conflict and TooBig -- which left the
    bare ones reading like data rather than like something raised. PEP 8 asks
    for the suffix; this keeps the next one from drifting back.
    """

    def test_every_public_exception_says_so(self):
        for name in numberdb.__all__:
            thing = getattr(numberdb, name)
            if isinstance(thing, type) and issubclass(thing, Exception):
                with self.subTest(name=name):
                    self.assertTrue(name.endswith('Error'), name)

    def test_they_all_answer_to_the_base(self):
        """`except numberdb.NumberDBError` has to keep catching all of it."""
        for name in numberdb.__all__:
            thing = getattr(numberdb, name)
            if isinstance(thing, type) and issubclass(thing, Exception):
                with self.subTest(name=name):
                    self.assertTrue(issubclass(thing, numberdb.NumberDBError))

    def test_none_of_them_shadows_a_builtin(self):
        """OverflowError was a candidate for TooBigError, and would have
        replaced the builtin for anyone doing `from numberdb import *`."""
        import builtins

        for name in numberdb.__all__:
            with self.subTest(name=name):
                self.assertIsNone(getattr(builtins, name, None))


class SageModuleStaysComplete(unittest.TestCase):
    """The Sage module lists its functions explicitly, so tooling can see them.

    Generating them in a loop kept the modules from drifting but made them
    invisible: a checker reported "Module has no attribute search_integer" and
    editors offered no completion, for exactly the audience the module serves.
    This test buys the same guarantee the loop did, without the cost.
    """

    def _module(self):
        try:
            import numberdb.sage as flavoured
        except ImportError as error:
            self.skipTest(str(error)[:50])
        return flavoured

    def test_it_mirrors_every_search_function(self):
        flavoured = self._module()
        expected = [n for n in numberdb.__all__ if n.startswith('search')]
        for name in expected:
            with self.subTest(name=name):
                self.assertIn(name, flavoured.__all__)
                self.assertTrue(callable(getattr(flavoured, name)))

    def test_the_whole_public_surface_is_reachable(self):
        """`import numberdb.sage as numberdb` has to be a drop-in.

        It was not: a Sage user following the documented idiom could not reach
        Generator or publish at all, which is exactly the audience that writes
        generators. Writing needs no Sage flavour of its own -- a Sage object
        is already understood wherever one is accepted -- but it does need to
        be there.
        """
        flavoured = self._module()
        for name in numberdb.__all__:
            with self.subTest(name=name):
                self.assertTrue(hasattr(flavoured, name))
                self.assertIn(name, flavoured.__all__)

    def test_the_signatures_match_the_plain_ones(self):
        """Minus the client, which the Sage module supplies itself."""
        import inspect
        flavoured = self._module()
        for name in [n for n in numberdb.__all__ if n.startswith('search')]:
            with self.subTest(name=name):
                plain = list(inspect.signature(
                    getattr(numberdb, name)).parameters)
                sage = list(inspect.signature(
                    getattr(flavoured, name)).parameters)
                self.assertEqual(plain, sage)

    def test_each_carries_the_plain_documentation_plus_a_note(self):
        flavoured = self._module()
        for name in [n for n in numberdb.__all__ if n.startswith('search')]:
            with self.subTest(name=name):
                text = getattr(flavoured, name).__doc__ or ''
                self.assertIn('Sage objects', text)
                self.assertGreater(len(text), 120, name)


class NoFlavourFlagInSignatures(unittest.TestCase):
    """as_sage is configuration and belongs on the Client.

    Exposed on every search function it meant two ways to ask for Sage values,
    and a parameter on eleven signatures that almost no caller should touch.
    """

    def test_no_search_function_exposes_it(self):
        import inspect
        for name in [n for n in numberdb.__all__ if n.startswith('search')]:
            with self.subTest(name=name):
                self.assertNotIn(
                    'as_sage',
                    str(inspect.signature(getattr(numberdb, name))))

    def test_the_client_carries_it(self):
        self.assertFalse(numberdb.Client().as_sage)
        self.assertTrue(numberdb.Client(as_sage=True).as_sage)

    def test_for_sage_keeps_the_rest_of_the_configuration(self):
        original = numberdb.Client(api_key='k', base_url='https://x.test',
                                   timeout=5)
        twin = original.for_sage()
        self.assertTrue(twin.as_sage)
        self.assertEqual(twin.api_key, 'k')
        self.assertEqual(twin.base_url, 'https://x.test/')
        self.assertEqual(twin.timeout, 5)
        self.assertFalse(original.as_sage)


class VendoredCanonicalisation(unittest.TestCase):
    """The client and the server must produce the same polynomial key.

    A lookup sends a digest of the key rather than the polynomial, because the
    longest stored one is 58866 characters and a URL is rejected past 8k. That
    only works while one canonicalisation defines the key, so the module is
    copied here byte for byte rather than reimplemented -- and this test is
    what stops the copy drifting.
    """

    ORIGINAL = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))))),
        'utils', 'numbers', 'polynomial.py')

    def test_the_copy_is_byte_identical(self):
        if not os.path.exists(self.ORIGINAL):
            self.skipTest('not inside the numberdb-website repository')
        vendored = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'numberdb', '_polynomial.py')
        with open(self.ORIGINAL, 'rb') as handle:
            original_bytes = handle.read()
        with open(vendored, 'rb') as handle:
            vendored_bytes = handle.read()
        self.assertEqual(original_bytes, vendored_bytes,
                         'the vendored copy has drifted from the original; '
                         'copy utils/numbers/polynomial.py across')

    def test_the_key_is_invariant_under_renaming(self):
        from numberdb._polynomial import parse_polynomial
        for one, other in [('x^2-2', 'y^2-2'), ('x^2*y', 'y^2*x')]:
            with self.subTest(pair=(one, other)):
                self.assertEqual(parse_polynomial(one).canonical_hash(),
                                 parse_polynomial(other).canonical_hash())

    def test_a_long_polynomial_is_sent_as_a_digest(self):
        long_one = '+'.join('%d*x^%d' % (n, n) for n in range(1, 400))
        self.assertGreater(len(long_one), 1500)
        client = _client({'results': [], 'messages': []})
        numberdb.search_polynomial(long_one, client=client)
        query = urllib.parse.parse_qs(
            urllib.parse.urlparse(client.opener.request.full_url).query)
        self.assertIn('polynomial_hash', query)
        self.assertNotIn('polynomial', query)
        self.assertLess(len(client.opener.request.full_url), 300)

    def test_a_short_one_is_sent_whole(self):
        """Readable in a log, and the server can say what it made of it."""
        client = _client({'results': [], 'messages': []})
        numberdb.search_polynomial('x^2-2', client=client)
        query = urllib.parse.parse_qs(
            urllib.parse.urlparse(client.opener.request.full_url).query)
        self.assertEqual(query['polynomial'], ['x^2-2'])


class ConnectionReuse(unittest.TestCase):
    """A Client keeps its connection open between requests.

    Setting up TLS costs about 0.28s from Europe to the server, against 0.16s
    for an answered request, so a script doing many lookups spent most of its
    time shaking hands. Measured against the live server: eight requests take
    0.72s on fresh connections and 0.46s on one, and that is on the machine
    itself -- over the network the handshake dominates and the gap widens.
    """

    class _Socket:
        """Stands in for the held connection."""

        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    def test_a_client_can_be_closed_and_reopened(self):
        client = numberdb.Client()
        self.assertIsNone(client._connection)
        held = self._Socket()
        client._connection = held              # as a request would leave it
        client.close()
        self.assertTrue(held.closed)
        self.assertIsNone(client._connection)

    def test_a_client_is_a_context_manager(self):
        with numberdb.Client() as client:
            held = self._Socket()
            client._connection = held
        self.assertTrue(held.closed)
        self.assertIsNone(client._connection)

    def test_an_injected_opener_keeps_the_connectionless_path(self):
        """The test seam must not silently start pooling."""
        client = _client({'results': [], 'messages': []})
        numberdb.search_text('3.14', client=client)
        self.assertIsNone(client._connection)

    def test_for_sage_does_not_share_a_socket(self):
        """Two clients interleaving on one connection would corrupt both."""
        original = numberdb.Client()
        original._connection = self._Socket()
        twin = original.for_sage()
        self.assertIsNot(twin, original)
        self.assertIsNone(twin._connection)


class QueriesAreBounded(unittest.TestCase):
    """A query is trimmed to a hundred significant digits, always outward.

    Rounding an endpoint inward would hide the number the caller is looking
    for. Rounding outward can only return more than was strictly needed.
    """

    def _sent(self, call, *args, **keywords):
        client = _client({'results': [], 'messages': []})
        call(*args, client=client, **keywords)
        query = urllib.parse.parse_qs(
            urllib.parse.urlparse(client.opener.request.full_url).query)
        return json.loads(query['number'][0])

    def test_a_long_interval_is_trimmed_outward(self):
        from numberdb._limits import SIGNIFICANT_DIGITS
        lower = Fraction(1, 3)
        upper = Fraction(1, 3) + Fraction(1, 10 ** 300)
        sent = self._sent(numberdb.search_real_interval, lower, upper)
        self.assertLessEqual(Fraction(sent['lower']), lower)
        self.assertGreaterEqual(Fraction(sent['upper']), upper)
        self.assertLess(len(sent['lower']), 4 * SIGNIFICANT_DIGITS)

    def test_a_short_query_is_left_alone(self):
        sent = self._sent(numberdb.search_real_interval, '3.1415', '3.1416')
        self.assertEqual(Fraction(sent['lower']), Fraction('3.1415'))
        self.assertEqual(Fraction(sent['upper']), Fraction('3.1416'))

    def test_a_huge_integer_becomes_an_interval_containing_it(self):
        """It cannot be conveyed in a hundred digits, so it is conveyed as the
        range it lies in."""
        huge = 10 ** 500 + 7
        sent = self._sent(numberdb.search_integer, huge)
        self.assertEqual(sent['kind'], 'RIF')
        self.assertLessEqual(Fraction(sent['lower']), huge)
        self.assertGreaterEqual(Fraction(sent['upper']), huge)

    def test_a_short_integer_stays_exact(self):
        self.assertEqual(self._sent(numberdb.search_integer, 7),
                         {'kind': 'ZZ', 'value': '7'})

    def test_each_complex_coordinate_is_bounded_on_its_own(self):
        """A large real part must not cost the imaginary one its precision."""
        sent = self._sent(numberdb.search_complex_interval,
                          10 ** 200, 10 ** 200, Fraction(1, 3), Fraction(1, 3))
        self.assertLessEqual(Fraction(sent['im_lower']), Fraction(1, 3))
        self.assertGreaterEqual(Fraction(sent['im_upper']), Fraction(1, 3))

    def test_p_adic_precision_is_counted_in_its_own_digits(self):
        from numberdb._limits import p_adic_digits
        self.assertEqual(p_adic_digits(2), 333)     # 100 * log(10)/log(2)
        self.assertEqual(p_adic_digits(5), 144)
        self.assertEqual(p_adic_digits(10 ** 60), 2)   # the floor
        sent = self._sent(numberdb.search_p_adic, 2, 0, 1,
                          relative_precision=10 ** 4)
        self.assertLessEqual(sent['precision'], 333)


class TextFindsWordsAsWellAsNumbers(unittest.TestCase):
    """A term is two questions, and the answers must not be confused."""

    def test_tables_and_tags_arrive_beside_the_numbers_not_among_them(self):
        client = _client({
            'results': [_record({'kind': 'ZZ', 'value': '3'})],
            'tables': [{'tid': 'T7', 'title': 'Pi', 'url': 'Pi',
                        'number_count': 4}],
            'tags': [{'name': 'transcendental', 'url': 'transcendental',
                      'table_count': 2, 'number_count': 2}],
            'messages': [],
        })
        found = numberdb.search_text('Pi', client=client)
        #The list is numbers only: iterating a search must never hand back a
        #table where a value was expected.
        self.assertEqual(len(found), 1)
        self.assertEqual([t.title for t in found.tables], ['Pi'])
        self.assertEqual([t.name for t in found.tags], ['transcendental'])
        self.assertEqual(found.tables[0].number_count, 4)
        self.assertEqual(found.tags[0].table_count, 2)

    def test_total_counts_everything_the_term_matched(self):
        """len() speaks for the numbers; total speaks for the search."""
        client = _client({
            'results': [],
            'tables': [{'tid': 'T5', 'title': 'Exponent of matrix'
                        ' multiplication complexity', 'url': 'Matrix',
                        'number_count': 1}],
            'tags': [{'name': 'matrix multiplication',
                      'url': 'matrix+multiplication',
                      'table_count': 1, 'number_count': 1}],
            'messages': [],
        })
        found = numberdb.search_text('matrix multiplication', client=client)
        self.assertEqual(len(found), 0)
        self.assertEqual(found.total, 2)
        #The list must not lie about its length, so this stays false.
        self.assertFalse(bool(found))

    def test_total_equals_len_when_only_numbers_matched(self):
        client = _client({'results': [
            _record({'kind': 'ZZ', 'value': '3'})], 'messages': []})
        found = numberdb.search_text('3', client=client)
        self.assertEqual(found.total, len(found), 1)

    def test_total_is_zero_when_nothing_matched(self):
        client = _client({'results': [], 'messages': []})
        self.assertEqual(numberdb.search_text('zzz', client=client).total, 0)

    def test_a_server_that_sends_neither_is_not_an_error(self):
        """An older server, or any number search, simply has no such keys."""
        client = _client({'results': [], 'messages': []})
        found = numberdb.search_text('3.14159', client=client)
        self.assertEqual(found.tables, [])
        self.assertEqual(found.tags, [])

    def test_number_searches_expose_the_same_empty_attributes(self):
        client = _client({'results': [], 'messages': []})
        found = numberdb.search_integer(3, client=client)
        self.assertEqual(found.tables, [])
        self.assertEqual(found.tags, [])


class Batching(unittest.TestCase):
    """Many numbers in one request, each answer saying which it answers."""

    def test_a_batch_sends_one_request_and_groups_the_answers(self):
        client = _client({'results': [
            dict(_record({'kind': 'ZZ', 'value': '3'}), index='0'),
            dict(_record({'kind': 'ZZ', 'value': '3'}), index='0'),
            dict(_record({'kind': 'QQ', 'value': '1/3'}), index='1'),
        ], 'messages': []})
        grouped = numberdb.search_many([3, Fraction(1, 3)], client=client)
        self.assertEqual({k: len(v) for k, v in grouped.items()}, {0: 2, 1: 1})
        self.assertIn('numbers', client.opener.request.full_url)

    def test_a_position_that_matched_nothing_is_an_empty_list_not_a_gap(self):
        """The keys are the caller's indices, whatever the server answered.

        A missing key would make results[i] raise on exactly the case worth
        asking about -- that the number is not in the database -- and would be
        indistinguishable from an answer the server dropped.
        """
        client = _client({'results': [
            dict(_record({'kind': 'QQ', 'value': '1/3'}), index='1'),
        ], 'messages': []})
        grouped = numberdb.search_many([3, Fraction(1, 3), 7], client=client)
        self.assertEqual(sorted(grouped), [0, 1, 2])
        self.assertEqual(grouped[0], [])
        self.assertEqual(len(grouped[1]), 1)
        self.assertEqual(grouped[2], [])

    def test_an_index_outside_the_batch_is_kept_rather_than_dropped(self):
        """A server answering about a position nobody asked about is visible."""
        client = _client({'results': [
            dict(_record({'kind': 'ZZ', 'value': '3'}), index='7'),
        ], 'messages': []})
        grouped = numberdb.search_many([3], client=client)
        self.assertEqual(sorted(grouped), [0, 7])
        self.assertEqual(grouped[0], [])
        self.assertEqual(len(grouped[7]), 1)

    def test_the_batch_size_is_capped(self):
        from numberdb._limits import MAX_BATCH
        with self.assertRaises(ValueError) as caught:
            numberdb.search_many([1] * (MAX_BATCH + 1))
        self.assertIn('Split it', str(caught.exception))

    def test_text_cannot_be_batched(self):
        """A batch carries numbers; text and expressions are other questions."""
        with self.assertRaises(TypeError):
            numberdb.search_many(['3.14'])


class WideningIsRefined(unittest.TestCase):
    """A widened query is sound but brings back extras; the client drops them.

    Filter and refine: the coarse interval goes to the server, which cannot
    miss with it, and the exact one is applied here, where the original bounds
    are still known. Without this a caller asking to 500 digits would be
    answered to 100 and told nothing about the difference.
    """

    def _client_returning(self, *intervals):
        results = []
        for lower, upper in intervals:
            results.append(_record({'kind': 'RIF', 'lower': lower,
                                    'upper': upper}))
        return _client({'results': results, 'messages': []})

    def test_a_result_outside_the_original_query_is_dropped(self):
        #Query to 300 digits; the server, asked to 100, also returns a value
        #that only matches the widening.
        lower = Fraction(1, 3)
        upper = Fraction(1, 3) + Fraction(1, 10 ** 300)
        client = self._client_returning(
            ('1/3', '1/3'),                     # inside the original
            ('1/2', '1/2'))                     # only inside the widened one
        found = numberdb.search_real_interval(lower, upper, client=client)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].value, numberdb.RealInterval(
            Fraction(1, 3), Fraction(1, 3)))

    def test_nothing_is_dropped_when_the_query_was_not_widened(self):
        client = self._client_returning(('1/2', '1/2'), ('3', '4'))
        found = numberdb.search_real_interval(0, 10, client=client)
        self.assertEqual(len(found), 2)

    def test_a_result_that_cannot_be_decoded_is_kept(self):
        """It might be the answer, and dropping it unexamined is worse."""
        lower = Fraction(1, 3)
        upper = Fraction(1, 3) + Fraction(1, 10 ** 300)
        client = _client({'results': [
            _record({'kind': 'SomeFutureKind', 'value': '?'})], 'messages': []})
        found = numberdb.search_real_interval(lower, upper, client=client)
        self.assertEqual(len(found), 1)

    def test_the_messages_survive_refinement(self):
        lower = Fraction(1, 3)
        upper = Fraction(1, 3) + Fraction(1, 10 ** 300)
        client = _client({'results': [], 'messages': [
            {'text': 'We only show the first 100 results.'}]})
        found = numberdb.search_real_interval(lower, upper, client=client)
        self.assertEqual(found.messages,
                         ['We only show the first 100 results.'])


class WholeSageObjectsAsInput(unittest.TestCase):
    """In Sage you are holding the interval, not its endpoints.

    Requiring `x.lower(), x.upper()` asks somebody to take an object apart so
    that a function can put it back together, and it is the natural thing to
    have in hand: `search(x)` already accepted it, but the component functions
    did not.
    """

    def sage(self):
        try:
            import sage.all  # noqa: F401
        except ImportError:
            self.skipTest('Sage is not installed here')
        import sage.all as sage
        return sage

    def sent(self, payload=None):
        return _client(payload if payload is not None
                       else {'results': [], 'messages': []})

    def test_a_real_interval_may_be_given_whole(self):
        sage = self.sage()
        value = sage.RealIntervalField(200)(sage.pi)
        found = numberdb.search_real_interval(value, client=self.sent())
        self.assertEqual(len(found), 0)

    def test_it_agrees_with_giving_the_endpoints(self):
        """The same interval either way, or one of the two forms is lying."""
        sage = self.sage()
        value = sage.RealIntervalField(200)(sage.pi)
        whole = _capture(lambda c: numberdb.search_real_interval(value, client=c))
        parts = _capture(lambda c: numberdb.search_real_interval(
            value.lower(), value.upper(), client=c))
        self.assertEqual(whole, parts)

    def test_a_complex_box_may_be_given_whole(self):
        sage = self.sage()
        value = sage.ComplexIntervalField(100)(sage.pi, sage.sqrt(2))
        numberdb.search_complex_interval(value, client=self.sent())

    def test_a_p_adic_may_be_given_whole_and_brings_its_precision(self):
        """The point of passing the whole thing: it knows its own precision."""
        sage = self.sage()
        whole = _capture(lambda c: numberdb.search_p_adic(sage.Qp(2)(1, 167),
                                                          client=c))
        parts = _capture(lambda c: numberdb.search_p_adic(
            2, 0, 1, absolute_precision=20, client=c))
        self.assertEqual(whole, parts)

    def test_this_package_s_own_types_are_accepted_too(self):
        from fractions import Fraction

        numberdb.search_real_interval(
            numberdb.RealInterval(Fraction(1, 2), Fraction(3, 4)),
            client=self.sent())

    def test_the_components_still_work(self):
        numberdb.search_real_interval('3.1415', '3.1416', client=self.sent())
        numberdb.search_complex_interval(0, 1, 0, 1, client=self.sent())

    def test_one_number_is_not_an_interval(self):
        """A single float says nothing about how wide it is."""
        with self.assertRaises(TypeError) as raised:
            numberdb.search_real_interval(3.14, client=self.sent())
        self.assertIn('two endpoints', str(raised.exception))


def _capture(call):
    """The query one of these searches would send."""
    import json

    seen = {}

    def opener(request, timeout=None):
        seen['url'] = request.full_url

        class Answer:
            def read(self):
                return json.dumps({'results': [], 'messages': []}).encode()

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        return Answer()

    call(numberdb.Client(base_url='http://x', opener=opener))
    return seen['url']


class WhereTheKeyComesFrom(unittest.TestCase):
    """Exporting a variable works and is what a server wants.

    It is not what somebody running a generator from a directory wants: the
    export lives in one shell and is gone from the next, and the usual repair
    -- putting it in the script -- is how a key ends up in a repository.
    """

    def setUp(self):
        import tempfile

        self.home = tempfile.mkdtemp()
        self.where = os.getcwd()
        self.had = os.environ.get('NUMBERDB_API_KEY')
        os.environ.pop('NUMBERDB_API_KEY', None)
        #So the developer's own key cannot make one of these pass.
        os.environ['XDG_CONFIG_HOME'] = os.path.join(self.home, 'config')

    def tearDown(self):
        os.chdir(self.where)
        if self.had is not None:
            os.environ['NUMBERDB_API_KEY'] = self.had
        else:
            os.environ.pop('NUMBERDB_API_KEY', None)

    def write(self, where, text):
        os.makedirs(os.path.dirname(where), exist_ok=True)
        with open(where, 'w', encoding='utf8') as handle:
            handle.write(text)

    def test_a_dot_env_beside_the_script_is_read(self):
        self.write(os.path.join(self.home, '.env'),
                   'NUMBERDB_API_KEY=from-dot-env\n')
        os.chdir(self.home)
        self.assertEqual(numberdb.Client().api_key, 'from-dot-env')

    def test_it_is_looked_for_above_the_working_directory_too(self):
        """A script in a subdirectory of its project is the ordinary case."""
        self.write(os.path.join(self.home, '.env'), 'NUMBERDB_API_KEY=above\n')
        deeper = os.path.join(self.home, 'a', 'b')
        os.makedirs(deeper, exist_ok=True)
        os.chdir(deeper)
        self.assertEqual(numberdb.Client().api_key, 'above')

    def test_the_per_user_file_is_the_fallback(self):
        """In no project directory, so it cannot be committed by accident."""
        self.write(os.path.join(self.home, 'config', 'numberdb', 'env'),
                   'NUMBERDB_API_KEY=from-user-config\n')
        os.chdir(self.home)
        self.assertEqual(numberdb.Client().api_key, 'from-user-config')

    def test_the_environment_beats_a_file(self):
        self.write(os.path.join(self.home, '.env'), 'NUMBERDB_API_KEY=file\n')
        os.chdir(self.home)
        os.environ['NUMBERDB_API_KEY'] = 'environment'
        self.assertEqual(numberdb.Client().api_key, 'environment')

    def test_what_was_passed_beats_everything(self):
        self.write(os.path.join(self.home, '.env'), 'NUMBERDB_API_KEY=file\n')
        os.chdir(self.home)
        os.environ['NUMBERDB_API_KEY'] = 'environment'
        self.assertEqual(numberdb.Client(api_key='given').api_key, 'given')

    def test_quotes_and_export_are_tolerated(self):
        """Every example anybody copies has them half the time, and a key with
        a quotation mark in it fails for a reason nobody will guess."""
        from numberdb._key import read_env_file

        path = os.path.join(self.home, 'quoted.env')
        self.write(path, '# a comment\n'
                         'export NUMBERDB_API_KEY="quoted-value"\n'
                         'OTHER=\'single\'\n'
                         'nonsense line without an equals\n')
        found = read_env_file(path)
        self.assertEqual(found['NUMBERDB_API_KEY'], 'quoted-value')
        self.assertEqual(found['OTHER'], 'single')
        self.assertNotIn('nonsense line without an equals', found)

    def test_nothing_in_the_file_is_executed(self):
        """A configuration file that runs is one that can be made to run
        something else."""
        from numberdb._key import read_env_file

        path = os.path.join(self.home, 'evil.env')
        self.write(path, 'NUMBERDB_API_KEY=$(rm -rf /)\n')
        self.assertEqual(read_env_file(path)['NUMBERDB_API_KEY'],
                         '$(rm -rf /)')

    def test_no_key_anywhere_is_not_an_error(self):
        """Reading is public; the refusal belongs where writing is attempted."""
        os.chdir(self.home)
        self.assertIsNone(numberdb.Client().api_key)


class VersionFromASourceTree(unittest.TestCase):
    """A checkout that was never installed still knows what it is.

    `importlib.metadata` answers for an installed distribution and raises for a
    source tree -- which is how a generator author works. The fallback used to
    be `0.0.0+unknown`, which is honest and useless: the version is recorded so
    a disagreement a year from now can be traced to a change, and "unknown"
    traces to nothing.
    """

    def test_it_reports_something_usable(self):
        import numberdb

        self.assertNotEqual(numberdb.__version__, '0.0.0+unknown')
        self.assertRegex(numberdb.__version__, r'^\d+\.\d+\.\d+')

    def test_a_source_tree_says_so(self):
        #So nobody reads a dirty checkout as a release.
        from numberdb import _installed_version

        try:
            from importlib.metadata import version
            version('numberdb')
        except Exception:
            self.assertTrue(_installed_version().endswith('+source'))
