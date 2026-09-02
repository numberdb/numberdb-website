"""T45 says its arguments are 1 mod p. 702 of its 856 are not.

Run with:  manage.py shell < fix-t45-constraint.py      (APPLY=1 to commit)

The values are right -- all 856 were recomputed from the series and agree --
so this corrects the claim, not the data. What the table actually holds is
every integer coprime to p, in every residue class: at p = 7 all six of them.

The logarithm is defined there because it extends from the residue class of 1,
where the series converges, to every unit:

    log_p(k) = log_p(k^(p-1)) / (p-1)

since k^(p-1) = 1 mod p whatever k was. Worth saying in the table, because
without it a reader who knows only the series will think two thirds of these
entries cannot exist.
"""
import os

from django.contrib.auth.models import User

from numberdb_app.editing import commit_table, tree_of
from numberdb_app.models import Table

APPLY = os.environ.get('APPLY') == '1'

table = Table.objects.get(tid='T45')
tree = dict(tree_of(table.head_revision))

parameters = dict(tree['Parameters'])
k = dict(parameters['k'])
before = k.get('constraints')
k['constraints'] = r'$p \nmid k$'
parameters['k'] = k
tree['Parameters'] = parameters

formulas = dict(tree.get('Formulas') or {})
formulas['formula-extension'] = (
	r'$\log_p(k) = \frac{1}{p-1}\log_p(k^{p-1})$. The series '
	r'$\log_p(1+u) = \sum_{n\geq1} (-1)^{n+1} u^n/n$ converges only for '
	r'$k \equiv 1 \bmod p$; this extends it to every unit, since '
	r'$k^{p-1} \equiv 1 \bmod p$ whatever $k$ was.')
tree['Formulas'] = formulas

print('constraint was:', before)
print('constraint now:', k['constraints'])
print('formula added :', formulas['formula-extension'][:70], '...')

if APPLY:
	commit_table(
		table, tree, author=User.objects.get(username='bmatschke'),
		base=table.head_revision, produced_by='correction',
		message=('the constraint said k = 1 mod p and 702 of the 856 entries '
		         'are not; they are the integers coprime to p, and the '
		         'logarithm reaches them through log(k^(p-1))/(p-1)'),
		via='orm')
	print('\ncommitted')
else:
	print('\ndry run; set APPLY=1 to commit')
