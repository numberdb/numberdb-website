"""T131, from the stage-three critique of 2026-09-02.

Run with:  manage.py shell < critique-T131.py      (APPLY=1 to commit)

  1. Two comments point "below" at formulas the page draws above. Named
     instead of pointed at, which survives any reordering.
  2. $d$ is used in two formulas and the entry comments, and the first
     sentence that says what it is comes two sections later. For $D=12$ it
     is not $D$, so a reader who guesses guesses wrong.
  3. "it is not the smallest solution of a Pell equation" is false for 225
     of the 302 entries. The sentence after it says what was meant.
  4. Three formulas end with a sentence about the run.
"""
import os

from django.contrib.auth.models import User

from agents.session_edit import edit_with_person
from numberdb_app.editing import tree_of
from numberdb_app.models import Table

APPLY = os.environ.get('APPLY') == '1'

table = Table.objects.get(tid='T131')
tree = dict(tree_of(table.head_revision))
changed = []


def swap(section, label, before, after):
	if label is None:
		text = tree[section]
		if before not in text:
			raise SystemExit('T131 %s: not found: %r' % (section, before))
		tree[section] = text.replace(before, after)
		changed.append(section)
		return
	block = dict(tree.get(section) or {})
	text = block[label]
	if before not in text:
		raise SystemExit('T131 %s/%s: not found: %r' % (section, label, before))
	block[label] = text.replace(before, after)
	tree[section] = block
	changed.append('%s/%s' % (section, label))


# 4 --------------------------------------------------------------------------
swap('Formulas', 'formula-pell', ' Checked on every entry.', '')
swap('Formulas', 'formula-trace',
     ' Checked in ball arithmetic on every entry.', '')
swap('Formulas', 'formula-class-number',
     ' Checked against every stored entry of that table.', '')

# 1 --------------------------------------------------------------------------
swap('Comments', 'comment-normalisation',
     'the one under which the class number formula below holds as written',
     'the one under which the class number formula '
     r'$\kappa_D=2h_KR_K/\sqrt{D}$ holds as written')
swap('Comments', 'comment-recognisable',
     r'In general $R_K$ is $\operatorname{arcosh}$ or '
     r'$\operatorname{arsinh}$ of half the trace of $\varepsilon_K$, by the '
     'formula below.',
     r'In general $R_K=\operatorname{arcosh}(t/2)$ or '
     r'$\operatorname{arsinh}(t/2)$, where $t$ is the trace of '
     r'$\varepsilon_K$.')

# 2 --------------------------------------------------------------------------
# Both symbols in the sentence that introduces the field, since the formulas
# and every entry comment use both.
swap('Definition', None,
     r'Let $K=\mathbb{Q}(\sqrt{D})$ be the real quadratic field of '
     'fundamental discriminant $D>1$',
     r'Let $K=\mathbb{Q}(\sqrt{d})$, with $d>1$ squarefree, be the real '
     'quadratic field of fundamental discriminant $D$')

# 3 --------------------------------------------------------------------------
swap('Comments', 'comment-maximal-order',
     'and it is not the smallest solution of a Pell equation',
     'and it need not be the smallest solution of a Pell equation')

for name in changed:
	print('changed:', name)
print()
print('Definition:', tree['Definition'])
print()
print('formula-pell ends:', tree['Formulas']['formula-pell'][-70:])

if APPLY:
	edit_with_person(
		table, tree, User.objects.get(username='bmatschke'),
		('say what d is where K is introduced, name the formulas instead of '
		 'pointing below at what the page draws above, take the run out of '
		 'three formulas, and stop claiming of every entry that the '
		 'fundamental unit is not a smallest Pell solution -- for 225 of '
		 'the 302 it is'),
		assistant='claude-opus-5', via='orm')
	print('\ncommitted')
else:
	print('\ndry run; set APPLY=1 to commit')
