import os
import django

os.environ["DJANGO_SETTINGS_MODULE"] = 'numberdb.settings'
django.setup()

from django.test import TestCase

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

from db_builder.build import numberdb_data_repository, build_numberdb_data

class NumberDBTestCase(TestCase):
    def setUp(self):
        
        print(" --- SETTING UP TEST DATABASE ---")
        
        data_repo = numberdb_data_repository()
        build_numberdb_data(data_repo, test_data=True)        

        print(" --- DONE: SETUP OF TEST DATABASE ---")
        
    def test_animals_can_speak(self):
        #lion = Animal.objects.get(name="lion")
        #cat = Animal.objects.get(name="cat")
        #self.assertEqual(lion.speak(), 'The lion says "roar"')
        #self.assertEqual(cat.speak(), 'The cat says "meow"')
        pass
