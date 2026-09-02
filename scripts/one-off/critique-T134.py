"""T134, from the stage-three critique of 2026-09-02.

Run with:  manage.py shell < critique-T134.py      (APPLY=1 to commit)

  1. The Sage program's weights print as a multiple of $\\sqrt\\pi$. `nodes`
     are intervals as intended, but `sqrt(pi)` is symbolic, so every weight
     is a symbolic expression and the first prints as
     `0.000112614...*sqrt(pi)`, not as the `0.000199604...` the comment on
     that very line promises. A reader who runs it concludes the table is
     wrong. Taking the square root inside the interval field fixes it and
     matches how the table was actually built.
  2. Two formulas end with a sentence about the run.
  3. Two comments explain a listing choice by what a search returns, and
     describe how many digits a number is printed with.
  4. "any other $n$ points give at most $n-1$ in general": $n-1$ is the
     floor for any $n$ distinct points, and Lobatto reaches $2n-3$.
"""
import os

from django.contrib.auth.models import User

from agents.session_edit import edit_with_person
from numberdb_app.editing import tree_of
from numberdb_app.models import Table

APPLY = os.environ.get('APPLY') == '1'

table = Table.objects.get(tid='T134')
tree = dict(tree_of(table.head_revision))
changed = []


def swap(section, label, before, after):
	block = dict(tree.get(section) or {})
	text = block[label]
	if before not in text:
		raise SystemExit('T134 %s/%s: not found: %r' % (section, label, before))
	block[label] = text.replace(before, after)
	tree[section] = block
	changed.append('%s/%s' % (section, label))


# 2 --------------------------------------------------------------------------
swap('Formulas', 'formula-weights',
     '; both were computed for every entry and agree', '')
swap('Formulas', 'formula-exactness',
     ' Checked in ball arithmetic on every rule here, the failure at $m=2n$ '
     'included.', '')

# 3 --------------------------------------------------------------------------
swap('Comments', 'comment-both-halves',
     r': a reader holding $-1.2247448713\ldots$ finds it with its sign', '')
swap('Comments', 'comment-size',
     ' Every approximate entry carries $100$ significant digits, so such a '
     'weight is written with an exponent.', '')

# 4 --------------------------------------------------------------------------
swap('Comments', 'comment-nodes',
     'any other $n$ points give at most $n-1$ in general',
     'a generic choice of $n$ points gives exactly $n-1$')

# 1 --------------------------------------------------------------------------
programs = dict(tree['Programs'])
sage = dict(programs['program-sage'])
was = sage['code']
sage['code'] = (
	'R.<x> = ZZ[]\n'
	'RIF400 = RealIntervalField(400)\n'
	'p = R(hermite(8, x))\n'
	'nodes = p.roots(RIF400, multiplicities=False)   '
	'# x_1 = -2.93063742025724401922...\n'
	'weights = [2^7*factorial(8)*RIF400(pi).sqrt()/(64*R(hermite(7, x))(r)^2) '
	'for r in nodes]   # w_1 = 0.000199604072211367619...')
programs['program-sage'] = sage
tree['Programs'] = programs
changed.append('Programs/program-sage')

for name in changed:
	print('changed:', name)
print()
print('was:\n' + was)
print()
print('now:\n' + tree['Programs']['program-sage']['code'])

if APPLY:
	edit_with_person(
		table, tree, User.objects.get(username='bmatschke'),
		("the Sage program's sqrt(pi) was symbolic, so every weight "
		 "printed as a multiple of sqrt(pi) rather than as the number "
		 "written beside it; take the square root in the interval "
		 "field. Also fix at most n-1, which is the floor for n "
		 "distinct points"),
		assistant='claude-opus-5', via='orm')
	print('\ncommitted')
else:
	print('\ndry run; set APPLY=1 to commit')
