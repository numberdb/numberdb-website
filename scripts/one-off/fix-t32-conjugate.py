"""Correct T32: phi_inv had the conjugate's sign, and two formulas said so too.

Run with:  manage.py shell < fix_t32.py          (add APPLY=1 to commit)
"""
import os

from django.contrib.auth.models import User

from numberdb_app.editing import commit_table, tree_of
from numberdb_app.models import Table

APPLY = os.environ.get('APPLY') == '1'

table = Table.objects.get(tid='T32')
tree = dict(tree_of(table.head_revision))

# -- the numbers -------------------------------------------------------
numbers = [dict(e) for e in tree['Numbers']]
by_name = {e['params']['expression']: e for e in numbers}
stored = by_name['phi_inv']['number']
assert stored.startswith('-'), 'phi_inv is not negative; has this already run?'

magnitude = stored[1:]                 # the digits are right, only the sign was not
by_name['phi_inv']['number'] = magnitude

conjugate = dict(by_name['phi_inv'])
conjugate['params'] = {'expression': 'phi_conj'}
conjugate['number'] = stored           # kept exactly, under a label that is true
numbers.append(conjugate)
tree['Numbers'] = numbers

# -- what the parameter may be ----------------------------------------
parameters = dict(tree['Parameters'])
expression = dict(parameters['expression'])
values = dict(expression['values'])
values['phi_conj'] = r'$\hat{\varphi} = 1-\varphi$'
expression['values'] = values
parameters['expression'] = expression
tree['Parameters'] = parameters

# -- the formulas that caused it --------------------------------------
#
# phi^2 - phi - 1 = 0 has roots (1 +/- sqrt 5)/2. The second is 1 - phi,
# which is -1/phi, not 1/phi: the table named the wrong one, and the stored
# value followed the prose rather than the definition.
formulas = dict(tree['Formulas'])
formulas['formula-polynomial-root'] = (
    r'$\varphi^2-\varphi-1=0$, which has two roots, $\varphi$ and its '
    r'conjugate $\hat{\varphi} = 1-\varphi$.')
formulas['formula-inverse'] = r'$\varphi^{-1} = \varphi - 1$.'
formulas['formula-conjugate'] = (
    r'$\hat{\varphi} = -\varphi^{-1} = 1-\varphi$. Note $\varphi^{-1}$ is '
    r'positive and $\hat{\varphi}$ is negative; they differ only in sign.')
tree['Formulas'] = formulas

# -- what may now be claimed about the digits -------------------------
properties = dict(tree['Data properties'])
properties['rigour details'] = (
    'Checked here against ball arithmetic at 4000 bits, which covers every '
    'stored digit rather than the first hundred: all three entries agree to '
    'within one unit in the last place of the 300 digits held. The values are '
    'algebraic, so any number of further digits can be had on demand.')
tree['Data properties'] = properties

print('phi      :', by_name['phi']['number'][:44])
print('phi_inv  :', by_name['phi_inv']['number'][:44], '  (sign corrected)')
print('phi_conj :', conjugate['number'][:44], '  (new entry)')
print()
for key in ('formula-polynomial-root', 'formula-inverse', 'formula-conjugate'):
    print('%s: %s' % (key, formulas[key]))

if APPLY:
    author = User.objects.get(username='bmatschke')
    commit_table(
        table, tree, author=author, base=table.head_revision,
        produced_by='correction',
        message=('phi_inv held the conjugate root: its sign was wrong, and so '
                 'were the two formulas that said phi^-1 is a root of '
                 'x^2-x-1. The value is kept as phi_conj, which is what it is.'))
    print('\ncommitted')
else:
    print('\ndry run; set APPLY=1 to commit')
