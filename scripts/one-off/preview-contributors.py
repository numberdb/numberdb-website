import os, sys
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'numberdb.settings.prod')
import django; django.setup()
from numberdb_app.views import _contributors
for row in _contributors():
    print('%-22s %5d %s' % (row['name'], row['count'],
                            '(a program)' if row['program'] else ''))
