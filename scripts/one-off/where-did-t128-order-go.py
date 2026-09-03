"""When did T128's entries stop being in the generator's order?

The generator yields fundamental discriminants ordered by |D| with -D first.
The stored document had them ordered by (width, string). Something between
the two lost it, and the next table with signed parameters will meet it too.
Read-only.
"""
#Run directly under `sage -python`, where sys.path[0] is this file's own
#directory rather than the project root, and Django is not set up yet.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
	os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'numberdb.settings.prod')
import django

django.setup()

from numberdb_app.models import Table
from numberdb_app.editing import tree_of


def shape(keys):
	"""Which order is this?"""
	if not keys:
		return 'no entries'
	by_abs = sorted(keys, key=lambda k: (abs(int(k)), int(k)))
	by_width = sorted(keys, key=lambda k: (len(k), k))
	if keys == by_abs:
		return 'by |D|, -D first  (the generator says this)'
	if keys == by_width:
		return 'by (width, string)  <-- the fault'
	return 'neither'


table = Table.objects.get(tid='T128')
for revision in table.revisions.order_by('created'):
	tree = tree_of(revision)
	numbers = tree.get('Numbers') or {}
	keys = list(numbers.keys()) if isinstance(numbers, dict) else []
	print('%s  %-11s %4d entries  %s'
	      % (revision.created.strftime('%m-%d %H:%M'),
	         revision.author.username if revision.author else '-',
	         len(keys), shape(keys)))
	if keys:
		print('        first: %s' % (' '.join(keys[:10]),))
