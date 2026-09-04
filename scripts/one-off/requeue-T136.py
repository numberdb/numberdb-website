"""Put T136 back in the review queue, where it should have stayed.

A repair through the API as bmatschke marked it reviewed up to its head, so
the queue -- which lists a table with entries outstanding or one never
reviewed at all -- stopped listing it while it stayed unpublished. The guard
is now in `write_table` and `_write_entries_locked`; this restores the one
table that got past it.

Nobody has actually reviewed T136, so the honest state is the one a fresh
draft has: reviewed by nobody, at no revision.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
	os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'numberdb.settings.prod')
import django

django.setup()

from numberdb_app.models import Table
from numberdb_app.review import sync_review_flags

APPLY = os.environ.get('APPLY') == '1'

table = Table.objects.get(tid='T136')
print('published        :', table.published)
print('ready_for_review :', table.ready_for_review)
print('reviewed_by      :', table.reviewed_by and table.reviewed_by.username)
print('reviewed_at      :', table.reviewed_at_revision_id)

if table.published:
	raise SystemExit('T136 is published; nothing to requeue')

if APPLY:
	table.reviewed_at_revision = None
	table.reviewed_by = None
	table.ready_for_review = True
	table.save(update_fields=['reviewed_at_revision', 'reviewed_by',
	                          'ready_for_review'])
	outstanding = sync_review_flags(table)
	table.refresh_from_db()
	print()
	print('now reviewed_at  :', table.reviewed_at_revision_id)
	print('now reviewed_by  :', table.reviewed_by_id)
	print('rows unreviewed  :', outstanding)
	print('\nrestored')
else:
	print('\ndry run; set APPLY=1 to restore')
