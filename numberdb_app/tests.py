import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "numberdb.settings.dev")
django.setup()

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

#print("INSTALLED_APPS:", INSTALLED_APPS)

from .models import UserProfile
from .models import Wanted

from .models import Table
from .models import TableData
from .models import TableSearch
from .models import TableCommit
from .models import Contributor
from .models import Tag
from .models import Number
from .models import NumberPAdic
from .models import NumberComplex
from .models import Polynomial

from .models import OeisNumber
from .models import OeisSequence
from .models import WikipediaNumber

from .common import test_table_ids

from data_pipeline.build import numberdb_data_repository, build_numberdb_data

class DataBuildTest(TestCase):
    def setUp(self):
        
        print(" --- SETTING UP TEST DATABASE ---")
        
        data_repo = numberdb_data_repository()
        build_numberdb_data(data_repo, test_data=True)        

        print(" --- DONE: SETUP OF TEST DATABASE ---")
   
    def test_db_tables(self):
        tables = Table.objects.all()
        self.assertEqual(len(tables), len(test_table_ids))
    
    def test_table_view(self):
        tid0 = test_table_ids[0]
        table0 = Table.objects.get(tid=tid0)
        url = reverse('db:table', kwargs={'tid': tid0})
        resp = self.client.get(url)
        #print('resp:', resp)
        self.assertEqual(resp.status_code, 200)
        #print('resp.content:', resp.content)
        self.assertIn(table0.title, str(resp.content))


class DocumentedNumberFormatsTestCase(TestCase):
    '''
    Every real-number format promised to users must parse and render.

    The formats come from two user-facing documents, which are the
    specification: help.html section "Number types and displayed accuracy",
    and the front-page tips in templates/includes/search-tips.html. If a format
    is documented there, it has to work here.
    '''

    #(input, expected interval) from help.html.
    DOCUMENTED_REALS = [
        ('3.14', (3.13, 3.15)),            # decimal expansion, last digit +-1
        ('12e2', (1100.0, 1300.0)),        # scientific notation
        ('[2, 2.3728596]', (2.0, 2.3728596)),   # explicit interval
        ('3.14 +/- 2e-2', (3.12, 3.16)),   # real ball
        ('1p31415', (3.1414, 3.1416)),     # NumberDB p-notation
    ]

    def test_every_documented_real_format_parses(self):
        from utils.utils import parse_real_interval

        for source, (low, high) in self.DOCUMENTED_REALS:
            with self.subTest(source=source):
                parsed = parse_real_interval(source)
                self.assertIsNotNone(
                    parsed, '%r is documented but does not parse' % (source,))
                #Endpoints are approximate: converting exact decimal bounds to
                #binary must round outward, so assert containment with a little
                #slack rather than equality.
                self.assertLessEqual(float(parsed.lower()), low + 1e-9)
                self.assertGreaterEqual(float(parsed.upper()), high - 1e-9)

    def test_real_ball_matches_the_importer(self):
        #Search and import must agree: numberdb-data stores the Riemann zeta
        #zeros and the physical constants in real-ball form, so a value that
        #imports has to be findable.
        from utils.utils import parse_real_interval

        zeta_zero = '14.1347251417346937904572519835625 +/- 2.5e-31'
        parsed = parse_real_interval(zeta_zero)
        self.assertIsNotNone(parsed)
        self.assertLess(float(parsed.lower()), 14.13472514173470)
        self.assertGreater(float(parsed.upper()), 14.13472514173469)

    def test_wide_interval_determines_no_partial_quotient(self):
        from utils.utils import StableContinuedFraction, parse_real_interval

        #[1100, 1300] contains many integers, so no floor is unique.
        wide = parse_real_interval('12e2')
        self.assertEqual(StableContinuedFraction(wide).determined_coefficients(), [])

        #A well-determined interval still yields coefficients.
        narrow = parse_real_interval('3.14159265')
        self.assertGreater(
            len(StableContinuedFraction(narrow).determined_coefficients()), 0)

    def test_search_accepts_every_documented_format(self):
        #The search bar is the path the documentation actually promises, and it
        #passes the term as a query parameter, so formats containing '/' work
        #here even though they cannot appear in a URL path segment.
        for source, _ in self.DOCUMENTED_REALS:
            with self.subTest(source=source):
                response = self.client.get(
                    reverse('db:suggestions'), {'term': source})
                self.assertEqual(
                    response.status_code, 200,
                    '%r is documented but search returns %s'
                    % (source, response.status_code))

    #Documented on the front page (templates/includes/search-tips.html).
    #All contain '+', which is what makes them a regression test.
    DOCUMENTED_P_ADICS = ['3 + O(2^5)', '2^0+2^1+O(2^5)', 'Q2:1010']

    def test_path_segments_are_not_decoded_twice(self):
        #properties() used to call unquote_plus on a segment Django had already
        #decoded. unquote_plus maps '+' to a space, so every documented format
        #containing a plus was corrupted before it ever reached a parser.
        from utils.utils import parse_p_adic, parse_real_interval

        self.assertIsNotNone(parse_real_interval('3.14 +/- 2e-2'))
        for source in ['3 + O(2^5)', '2^0+2^1+O(2^5)']:
            with self.subTest(source=source):
                self.assertIsNotNone(
                    parse_p_adic(source),
                    '%r is documented but does not parse' % (source,))

    #Every worked example from the two user-facing documents, as
    #(input, prime, exponents present, exponent in the O-term).
    #search-tips.html for the first block, help.html for the second.
    DOCUMENTED_P_ADIC_EXAMPLES = [
        ('Q2:1010',        2, [0, 2],     4),
        ('Q2:1.1010',      2, [-1, 0, 2], 4),
        ('3 + O(2^5)',     2, [0, 1],     5),
        ('2^0+2^1+O(2^5)', 2, [0, 1],     5),
        ('Q2:110',         2, [0, 1],     3),
        ('Q2:1.110',       2, [-1, 0, 1], 3),
        ('Q13:01.02',     13, [-1],       1),   # plus 2*13^0, checked separately
    ]

    def test_documented_examples_mean_what_the_docs_say(self):
        #The documentation is the specification, so its worked examples belong
        #in the test suite. Two of these were wrong before: search-tips.html
        #claimed O(2^5) for Q2:1010 and Q2:1.1010, where the precision is the
        #number of digits after the point, i.e. O(2^4).
        from sage.rings.all import Qp
        from utils.utils import parse_p_adic

        for source, prime, exponents, big_oh in self.DOCUMENTED_P_ADIC_EXAMPLES:
            if source == 'Q13:01.02':
                continue    # has a coefficient of 2; covered below
            with self.subTest(source=source):
                parsed = parse_p_adic(source)
                self.assertIsNotNone(parsed)
                field = Qp(prime, prec=big_oh - min(exponents) + 2)
                expected = sum(field(prime) ** e for e in exponents)
                self.assertEqual(parsed, expected.add_bigoh(big_oh),
                                 '%r does not match the documentation' % (source,))
                self.assertEqual(
                    parsed.precision_absolute(), big_oh,
                    '%r: documentation says O(%d^%d)'
                    % (source, prime, big_oh))

    def test_documented_example_with_multi_digit_prime(self):
        #help.html: "Q13:01.02" represents 13^-1 + 2*13^0 + O(13^1), i.e. digits
        #are written in base 10 with as many characters as the prime.
        from sage.rings.all import Qp
        from utils.utils import parse_p_adic

        field = Qp(13, prec=5)
        expected = (field(13) ** -1 + 2 * field(1)).add_bigoh(1)
        self.assertEqual(parse_p_adic('Q13:01.02'), expected)

    def test_every_documented_p_adic_format_parses(self):
        from utils.utils import parse_p_adic

        for source in self.DOCUMENTED_P_ADICS:
            with self.subTest(source=source):
                #Must not raise, and must not silently return None.
                self.assertIsNotNone(
                    parse_p_adic(source),
                    '%r is documented but does not parse' % (source,))

    def test_p_adic_with_decimal_point_does_not_crash(self):
        #Regression: 'Q2:1.1010' is documented on the front page, and raised
        #TypeError: unable to convert '.' to an integer. The regex group
        #(?:\d*\.)? captures the separator, so '.' was counted as a digit and
        #then evaluated as one.
        from utils.utils import parse_p_adic

        with_point = parse_p_adic('Q2:1.1010')
        self.assertIsNotNone(with_point)
        #Documented meaning: 2^-1 + 2^0 + 2^2 + O(2^5), so it has a negative
        #valuation, unlike the same digits without a point.
        self.assertLess(with_point.valuation(), 0)
        self.assertGreaterEqual(parse_p_adic('Q2:1010').valuation(), 0)

    def test_search_accepts_every_documented_p_adic(self):
        #p-adics are searchable. They have no properties page -- properties()
        #dispatches only to integer, rational, real-interval and polynomial
        #parsers -- which is a feature gap, not a regression, so it is asserted
        #here as current behaviour rather than as a bug.
        for source in self.DOCUMENTED_P_ADICS:
            with self.subTest(source=source):
                response = self.client.get(
                    reverse('db:suggestions'), {'term': source})
                self.assertEqual(response.status_code, 200)

    def test_properties_page_serves_documented_formats(self):
        #Regression: /properties/12e2 returned 500 with "continued fraction can
        #not represent infinity", because the view asked Sage for the empty
        #continued fraction instead of taking its own 'Insufficient precision.'
        #branch.
        #
        #Real balls are excluded here, and not because they fail to parse: the
        #route is properties/(?P<number>[^/]+), and "3.14 +/- 2e-2" contains a
        #forward slash, so it cannot be carried in a path segment at all. It is
        #reachable through search above.
        for source, _ in self.DOCUMENTED_REALS:
            if '/' in source:
                continue
            with self.subTest(source=source):
                response = self.client.get(
                    reverse('db:properties', kwargs={'number': source}))
                self.assertEqual(
                    response.status_code, 200,
                    '%r is documented but the properties page returns %s'
                    % (source, response.status_code))


class CanonicalRenderingTestCase(TestCase):
    '''
    Displayed numbers must be written in the documented formats, with no
    notation the user-facing documents do not define.

    Sage's '?' is redundant under that convention: '.' or 'e' already means
    "interval, last digit may be off by one", and neither means "exact
    integer". Showing '3.14?' says it twice, in a notation appearing in no
    document.
    '''

    #Endpoints chosen to hit every branch of the pretty printer: exact,
    #contains zero, high relative precision, low relative precision (bracket
    #fallback), and scientific notation.
    SAMPLE_INTERVALS = [
        (3.13, 3.15),
        (5.4, 5.6),
        (1100.0, 1300.0),
        (2.0, 2.3728596),
        (3.0, 3.0),
        (-0.1, 0.1),
        (0.0, 0.0),
        (1e21, 1.0000001e21),
        (-2.5, -2.4999999),
    ]

    def test_no_rendering_contains_a_question_mark(self):
        from sage.rings.all import RIF, CIF
        from utils.utils import (complex_interval_to_pretty_string,
                                 real_interval_to_pretty_string)

        for low, high in self.SAMPLE_INTERVALS:
            with self.subTest(interval=(low, high)):
                rendered = real_interval_to_pretty_string(RIF(low, high))
                self.assertNotIn('?', rendered)

        rendered = complex_interval_to_pretty_string(
            CIF(RIF(3.13, 3.15), RIF(2.71, 2.73)))
        self.assertNotIn('?', rendered)

    def test_displayed_reals_parse_back_to_a_containing_interval(self):
        #The property that makes the rendering canonical: what is shown can be
        #pasted into the search bar, and reading it back never claims more
        #precision than was stored. Wider is sound; narrower would be a lie.
        from sage.rings.all import RIF
        from utils.utils import parse_real_interval, real_interval_to_pretty_string

        for low, high in self.SAMPLE_INTERVALS:
            with self.subTest(interval=(low, high)):
                original = RIF(low, high)
                rendered = real_interval_to_pretty_string(original)

                reparsed = parse_real_interval(rendered)
                self.assertIsNotNone(
                    reparsed, 'displayed %r does not parse back' % (rendered,))
                self.assertLessEqual(
                    reparsed.lower(), original.lower(),
                    'displayed %r excludes part of the stored interval' % (rendered,))
                self.assertGreaterEqual(
                    reparsed.upper(), original.upper(),
                    'displayed %r excludes part of the stored interval' % (rendered,))

    def test_exact_integers_render_without_a_period(self):
        #Documented: "If the decimal expansion does not contain '.' or 'e', it
        #will instead denote an exactly represented integer." So the period is
        #what distinguishes an interval from an exact value, and it must not
        #appear on exact ones.
        from sage.rings.all import RIF
        from utils.utils import real_interval_to_pretty_string

        for exact in (3, 0, -1729):
            with self.subTest(exact=exact):
                rendered = real_interval_to_pretty_string(RIF(exact, exact))
                self.assertNotIn('.', rendered)
                self.assertNotIn('e', rendered)

    COMPLEX_SAMPLES = [
        (0.8333, 0.8334, 5.4, 5.6),
        (3.13, 3.15, 2.71, 2.73),
        (-1.05, -1.04, -0.11, -0.10),
        (0.0, 0.0, 1.0, 1.0),
        (-0.1, 0.1, -0.1, 0.1),
    ]

    def test_imaginary_part_does_not_lose_a_digit(self):
        #Regression: an imaginary part of [5.4, 5.6] -- what "5.5" denotes --
        #rendered as "6.", which means [5, 7]. Sound but a digit poorer, and a
        #reader who typed 5.5 saw 6. The complex printer bypassed the real
        #printer's bracket fallback.
        from sage.rings.all import CIF, RIF
        from utils.utils import complex_interval_to_pretty_string

        rendered = complex_interval_to_pretty_string(
            CIF(RIF(0.8333, 0.8334), RIF(5.4, 5.6)))
        self.assertNotIn('6.*I', rendered)
        self.assertIn('[5.', rendered)

    def test_displayed_complex_numbers_parse_back_to_a_containing_box(self):
        from sage.rings.all import CIF, RIF
        from utils.utils import (complex_interval_to_pretty_string,
                                 parse_complex_interval)

        for re_low, re_high, im_low, im_high in self.COMPLEX_SAMPLES:
            with self.subTest(box=(re_low, re_high, im_low, im_high)):
                original = CIF(RIF(re_low, re_high), RIF(im_low, im_high))
                rendered = complex_interval_to_pretty_string(original)

                reparsed = parse_complex_interval(rendered)
                self.assertIsNotNone(
                    reparsed, 'displayed %r does not parse back' % (rendered,))
                for part in ('real', 'imag'):
                    shown = getattr(reparsed, part)()
                    stored = getattr(original, part)()
                    self.assertLessEqual(shown.lower(), stored.lower())
                    self.assertGreaterEqual(shown.upper(), stored.upper())

    def test_interval_components_parse_in_both_positions(self):
        #The term splitter used to look for (digit)(+|-), so a '+' after a ']'
        #was not a separator: intervals parsed in the imaginary position but
        #not the real one.
        from utils.utils import parse_complex_interval

        self.assertIsNotNone(parse_complex_interval('[0.833,0.834]+[5.399,5.601]*I'))
        self.assertIsNotNone(parse_complex_interval('0.8333+[5.399,5.601]*I'))
        self.assertIsNotNone(parse_complex_interval('[0.833,0.834]+5.5*I'))

    def test_imaginary_unit_without_an_asterisk(self):
        from utils.utils import parse_complex_interval

        #Compare endpoints: Sage interval equality is not structural, so two
        #identical-looking intervals need not compare equal.
        without_star = parse_complex_interval('5/6+5.5I')
        with_star = parse_complex_interval('5/6+5.5*I')
        self.assertIsNotNone(without_star)
        for part in ('real', 'imag'):
            self.assertEqual(getattr(without_star, part)().lower(),
                             getattr(with_star, part)().lower())
            self.assertEqual(getattr(without_star, part)().upper(),
                             getattr(with_star, part)().upper())

    def test_exponents_are_not_split_as_signs(self):
        #The separator rule requires a digit or ')' / ']' before the sign, so
        #the '-' in "1e-5" stays part of the number.
        from utils.utils import parse_complex_interval

        parsed = parse_complex_interval('1e-5+2e-5*I')
        self.assertIsNotNone(parsed)
        self.assertLess(abs(float(parsed.real().center()) - 1e-5), 1e-6)

    def test_stored_complex_numbers_render_in_the_documented_form(self):
        from numberdb_app.models import NumberComplex
        from sage.rings.all import CIF, RIF

        number = NumberComplex(sage_number=CIF(RIF(-1.05, -1.04), RIF(0.52, 0.53)))
        rendered = number.str_short()
        self.assertNotIn('?', rendered)
        self.assertIn('*I', rendered)


class TableHistoryViewTestCase(TestCase):
    '''
    TableCommit has no 'author' field -- it was dropped in migration 0011 in
    favour of the Contributor foreign key -- so sorting the history by author
    has to go through 'contributor__author'.
    '''

    def setUp(self):
        self.contributor = Contributor.objects.create(
            author_and_email='Alice <alice@example.com>',
            author='Alice',
            email='alice@example.com',
        )
        self.table = Table.objects.create(
            tid='T1',
            tid_int=1,
            url='table-1',
            path='table-1',
            title='Table 1',
        )
        self.commit = TableCommit.objects.create(
            hexsha='1' * 40,
            contributor=self.contributor,
            datetime=timezone.now(),
            timezone=0,
            summary='Initial commit',
            message='Initial commit',
        )
        self.commit.tables.add(self.table)

    def test_history_page_sorts_by_author(self):
        response = self.client.get(
            reverse('db:table-history', kwargs={'tid': self.table.tid}),
            {'sort_by': 'author'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['sortby'], 'author')

    def test_history_page_falls_back_for_unknown_sort(self):
        response = self.client.get(
            reverse('db:table-history', kwargs={'tid': self.table.tid}),
            {'sort_by': 'unknown'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['sortby'], 'time')
