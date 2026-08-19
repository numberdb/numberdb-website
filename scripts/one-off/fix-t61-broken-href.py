"""T61 links to Roots_or_unity, which is not a table. Roots_of_unity is.

    manage.py shell < scripts/one-off/fix-t61-broken-href.py    (APPLY=1)

Found by `manage.py audit_table --all`, which is the point of it: one
character, in a comment, on a table nobody had reason to re-read.
"""
import os

from django.contrib.auth.models import User

from numberdb_app.editing import commit_table, tree_of
from numberdb_app.models import Table

APPLY = os.environ.get('APPLY') == '1'

table = Table.objects.get(tid='T61')
tree = dict(tree_of(table.head_revision))
comments = dict(tree['Comments'])
changed = []
for key, text in comments.items():
	if 'Roots_or_unity' in text:
		comments[key] = text.replace('Roots_or_unity', 'Roots_of_unity')
		changed.append(key)
tree['Comments'] = comments

target = Table.objects.filter(url='Roots_of_unity').first()
print('the link now points at:', target.tid if target else 'NOTHING -- stop')
for key in changed:
	print('  %s: %s' % (key, comments[key][:120]))

if APPLY and target and changed:
	commit_table(
		table, tree, author=User.objects.get(username='bmatschke'),
		base=table.head_revision, produced_by='correction',
		message='the link to the roots of unity said Roots_or_unity and went '
		        'nowhere')
	print('committed')
elif not APPLY:
	print('\ndry run; set APPLY=1 to commit')
