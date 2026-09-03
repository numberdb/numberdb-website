"""How many unpublished drafts are in flight, against the ceiling. Read-only."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
	os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'numberdb.settings.prod')
import django

django.setup()

from django.conf import settings
from numberdb_app.models import Table

ceiling = getattr(settings, 'NUMBERDB_DRAFTS_IN_FLIGHT', 15)
drafts = Table.objects.filter(published=False).order_by('tid_int')
print('ceiling      :', ceiling)
print('drafts       :', drafts.count())
for table in drafts:
	print('   %-6s %s' % (table.tid, table.title[:60]))
print('published    :', Table.objects.filter(published=True).count())
