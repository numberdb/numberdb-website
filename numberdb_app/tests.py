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

from db_builder.build import numberdb_data_repository, build_numberdb_data

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
