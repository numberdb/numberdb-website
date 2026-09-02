"""Two corrections to how T32 presents the conjugate root.

Run with:  manage.py shell < fix-t32-conjugate-display.py     (APPLY=1 to commit)

  * The parameter display read `$\\hat{\\varphi} = 1-\\varphi$`. The column
    names which number an entry is, and a name is what belongs there; the
    equation is already in the formulas, where a reader can find it.

  * The conjugate formula ended "Note $\\varphi^{-1}$ is positive and
    $\\hat{\\varphi}$ is negative; they differ only in sign." Which follows
    from the equation it is appended to.

No values change.
"""
import os

from django.contrib.auth.models import User

from numberdb_app.editing import commit_table, tree_of
from numberdb_app.models import Table

APPLY = os.environ.get('APPLY') == '1'

table = Table.objects.get(tid='T32')
tree = dict(tree_of(table.head_revision))

parameters = dict(tree['Parameters'])
expression = dict(parameters['expression'])
values = dict(expression['values'])
before_display = values.get('phi_conj')
values['phi_conj'] = r'$\hat{\varphi}$'
expression['values'] = values
parameters['expression'] = expression
tree['Parameters'] = parameters

formulas = dict(tree['Formulas'])
before_formula = formulas.get('formula-conjugate', '')
formulas['formula-conjugate'] = r'$\hat{\varphi} = -\varphi^{-1} = 1-\varphi$.'
tree['Formulas'] = formulas

print('display was :', before_display)
print('display now :', values['phi_conj'])
print()
print('formula was :', before_formula)
print('formula now :', formulas['formula-conjugate'])

if APPLY:
	commit_table(
		table, tree, author=User.objects.get(username='bmatschke'),
		base=table.head_revision, produced_by='correction',
		message=('the conjugate column names the number rather than stating an '
		         'equation, and the formula drops a sentence that repeats it'),
		via='orm')
	print('\ncommitted')
else:
	print('\ndry run; set APPLY=1 to commit')
