import os
import django

os.environ["DJANGO_SETTINGS_MODULE"] = 'numberdb.settings'
django.setup()

from django.test import TestCase
from django.urls import reverse

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
