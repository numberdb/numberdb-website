"""Make the Programs snippets answer the question that section is for.

    manage.py shell < scripts/one-off/fix-polynomial-programs.py   (APPLY=1)

They read `polynomials = {n: fibonacci_polynomial(n) for n in [0..150]}` --
a range that was cut to 100 afterwards and that nothing updated, so the
published code claimed a table half again as large as the one it was attached
to. `Programs` is for a reader who wants *one more value*, so it now ends with
one call rather than a range that can drift.
"""
import os

from django.contrib.auth.models import User

from numberdb_app.editing import commit_table, tree_of
from numberdb_app.models import Table

APPLY = os.environ.get('APPLY') == '1'
AUTHOR = User.objects.get(username='bmatschke')

SNIPPETS = {
	'T108': """R.<x> = ZZ[]
def fibonacci_polynomial(n):
    a, b = R(0), R(1)
    for _ in range(n):
        a, b = b, x*b + a
    return a

fibonacci_polynomial(101)        # the next one after this table""",
	'T109': """R.<x> = ZZ[]
def lucas_polynomial(n):
    a, b = R(2), x
    for _ in range(n):
        a, b = b, x*b + a
    return a

lucas_polynomial(101)            # the next one after this table""",
}

for tid, code in SNIPPETS.items():
	table = Table.objects.get(tid=tid)
	tree = dict(tree_of(table.head_revision))
	tree['Programs'] = {'program-sage': {'language': 'Sage', 'code': code}}
	print('%s:' % tid)
	print('   ' + code.replace('\n', '\n   '))
	if APPLY:
		commit_table(
			table, tree, author=AUTHOR, base=table.head_revision,
			produced_by='table document, assisted by claude-opus-5',
			message='the Sage snippet gives the next value rather than a '
			        'range that goes stale when the table changes')
		print('   committed')

if not APPLY:
	print('\ndry run; set APPLY=1 to commit')
