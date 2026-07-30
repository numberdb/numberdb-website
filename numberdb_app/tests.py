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
