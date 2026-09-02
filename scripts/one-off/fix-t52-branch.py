"""T52 defines the p-adic agm by an iteration that does not determine it.

Run with:  manage.py shell < fix-t52-branch.py           (APPLY=1 to commit)

    a_{n+1} = (a_n + g_n)/2,   g_{n+1} = sqrt(a_n g_n)

Over the reals the positive root is meant and nobody has to say so. Over Q_p
both roots are there, and they lead to *different limits* -- not a sign
difference, a different number. So the table as written does not determine its
own values, and a reader following it can compute something else. That is what
happened here: reading it the natural way gave a different answer for every
entry at every odd prime.

The values are PARI's, and PARI's rule was established by asking it rather
than by guessing. The agm is unchanged by one step of the iteration, so

    agm(a, b) == agm((a+b)/2, r)

holds for the root PARI took and fails for the other. At every prime tried it
takes the root nearer to the new arithmetic mean, and with that rule all 990
entries of this table reproduce, p = 2 included.

This writes that into the definition. The data is untouched.
"""
import os

from django.contrib.auth.models import User

from numberdb_app.editing import commit_table, tree_of
from numberdb_app.models import Table

APPLY = os.environ.get('APPLY') == '1'

table = Table.objects.get(tid='T52')
tree = dict(tree_of(table.head_revision))

BRANCH = (
	r' Over $\mathbb{Q}_p$ the equation $g_{n+1}^2 = a_n g_n$ has two '
	r'solutions and they lead to different limits, so the iteration alone '
	r'does not determine the value: here $g_{n+1}$ is the square root nearer '
	r'to $a_{n+1}$, that is the one for which $|g_{n+1} - a_{n+1}|_p$ is '
	r'smaller. This is the convention used by PARI, whose $\texttt{agm}$ '
	r'produced the values below.')

definition = tree['Definition']
if BRANCH.strip()[:40] in definition:
	print('the definition already says which root; nothing to do')
	raise SystemExit(0)
tree['Definition'] = definition.rstrip() + BRANCH

formulas = dict(tree.get('Formulas') or {})
formulas['formula-step-invariance'] = (
	r'$\text{agm}_p(a,b) = \text{agm}_p\left(\frac{a+b}{2}, \sqrt{ab}\right)$ '
	r'for the same choice of root, which is what makes the choice checkable: '
	r'only one of the two satisfies it.')
tree['Formulas'] = formulas

print('Definition now ends:')
print('   ...', tree['Definition'][-260:])
print()
print('formula added:', formulas['formula-step-invariance'][:70], '...')

if APPLY:
	commit_table(
		table, tree, author=User.objects.get(username='bmatschke'),
		base=table.head_revision, produced_by='correction',
		message=('the definition did not say which square root the iteration '
		         'takes, and over Q_p the two choices give different limits; '
		         'it now states the convention the values follow'),
		via='orm')
	print('\ncommitted')
else:
	print('\ndry run; set APPLY=1 to commit')
