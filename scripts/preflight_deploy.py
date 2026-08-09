"""What to check before deploying, run against the database being deployed to.

Written after a near miss. `_sync_tags` makes the document authoritative for a
table's tags, and it runs on every edit. Any table whose stored tags are not in
its document therefore loses them the first time somebody edits it -- quietly,
as a side effect of an unrelated change. On the development database exactly
one table was in that state and the bug had put it there; production was built
by the data pipeline and may have more.

    sage -python manage.py shell < scripts/preflight_deploy.py
"""

from django.db.migrations.executor import MigrationExecutor
from django.db import connection

from numberdb_app.editing import _tag_names, tree_of
from numberdb_app.models import Table, Tag

print('=' * 68)
print('PRE-DEPLOY CHECK')
print('=' * 68)

executor = MigrationExecutor(connection)
plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
print('\nmigrations still to apply: %d' % (len(plan),))
for migration, _backwards in plan:
    print('   %s.%s' % (migration.app_label, migration.name))

print('\ntables whose stored tags are not in their document:')
mismatched = 0
for table in Table.objects.all().prefetch_related('tags'):
    if table.head_revision is None:
        continue
    in_document = set(_tag_names(tree_of(table.head_revision).get('Tags')))
    stored = {tag.name for tag in table.tags.all()}
    if in_document != stored:
        mismatched += 1
        lost = stored - in_document
        print('   %-6s document=%-40s would lose=%s'
              % (table.tid, sorted(in_document), sorted(lost) or 'nothing'))
print('   %d of %d tables' % (mismatched, Table.objects.count()))
if mismatched:
    print('\n   Those tags exist only in the database. Editing such a table')
    print('   drops them. Put them in the documents first, or decide they')
    print('   were never meant to be there.')

print('\ntables with no revision at all: %d'
      % (Table.objects.filter(head_revision__isnull=True).count(),))
print('tags nothing points at: %d'
      % (Tag.objects.filter(tables__isnull=True).count(),))
print('\n' + '=' * 68)
