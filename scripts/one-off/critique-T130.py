"""T130, from the stage-three critique of 2026-09-02.

Run with:  manage.py shell < critique-T130.py      (APPLY=1 to commit)

Four things, none of them about the numbers:

  1. Two formulas end with a sentence about what the generator did on
     2026-09-01. "How they were obtained" already says it, in more detail,
     and in a Formulas section it reads as an apology for not proving.
  2. Two comments say "below" about formulas the page draws above. The
     document has Comments before Formulas; the page does not. A CITE of a
     formula label renders as its number and stays right either way.
  3. The definition carries the range that was computed, s = -1,-3,-5. The
     parameter says the family and `complete` says the coverage; the
     definition should say what the numbers are.
  4. Three families are named in comment (7) and none is linked.
"""
import os

from django.contrib.auth.models import User

from agents.session_edit import edit_with_person
from numberdb_app.editing import tree_of
from numberdb_app.models import Table

APPLY = os.environ.get('APPLY') == '1'

table = Table.objects.get(tid='T130')
tree = dict(tree_of(table.head_revision))

changed = []


def cut(section, label, ending, keep=''):
	"""Drop `ending` from one field, or say loudly that it is not there."""
	block = dict(tree.get(section) or {})
	text = block[label]
	if ending not in text:
		raise SystemExit('T130 %s/%s: not found: %r' % (section, label, ending))
	block[label] = text.replace(ending, keep)
	tree[section] = block
	changed.append('%s/%s' % (section, label))


def swap(section, label, before, after):
	block = dict(tree.get(section) or {})
	text = block[label]
	if before not in text:
		raise SystemExit('T130 %s/%s: not found: %r' % (section, label, before))
	block[label] = text.replace(before, after)
	tree[section] = block
	changed.append('%s/%s' % (section, label))


# 1 --------------------------------------------------------------------------
cut('Formulas', 'formula-siegel',
    ' Checked against the Bernoulli formula on every entry at $s=-1$.')
cut('Formulas', 'formula-functional-equation',
    ' Checked in ball arithmetic on every entry, with '
    r'$\zeta_K(2m)=\zeta(2m)L(2m,\chi_D)$ computed from the Hurwitz zeta '
    'function.')

# 2 --------------------------------------------------------------------------
swap('Comments', 'comment-rational',
     'and the Bernoulli-number formulas below',
     'and the Bernoulli-number formula CITE{formula-bernoulli}')
swap('Comments', 'comment-small-values',
     "by Siegel's formula below",
     "by Siegel's formula CITE{formula-siegel}")

# 3 --------------------------------------------------------------------------
definition = tree['Definition']
before = 'at the negative odd integers $s=-1,-3,-5$, where it is'
after = 'at negative odd integers $s$, where it is'
if before not in definition:
	raise SystemExit('T130 Definition: not found: %r' % (before,))
tree['Definition'] = definition.replace(before, after)
changed.append('Definition')

# 4 --------------------------------------------------------------------------
# Only the polynomials. The page draws Formulas above Comments, and
# formula-bernoulli already links the Bernoulli numbers and the generalized
# Bernoulli numbers where it names them, which is their first mention as a
# reader meets them. $B_n(x)$ is linked nowhere, and it is the one a reader is
# least likely to know.
swap('Comments', 'comment-notation',
     '$B_n(x)$ the Bernoulli polynomials',
     '$B_n(x)$ HREF{Bernoulli_polynomials}[the Bernoulli polynomials]')

for name in changed:
	print('changed:', name)
print()
print('Definition now:', tree['Definition'])
print()
print('formula-siegel now:', tree['Formulas']['formula-siegel'][-90:])

if APPLY:
	edit_with_person(
		table, tree, User.objects.get(username='bmatschke'),
		('take the run out of two formulas, point at the formulas by number '
		 'rather than by "below", let the definition say the family instead '
		 'of the computed range, and link the Bernoulli polynomials, which '
		 'were named nowhere with a link'),
		assistant='claude-opus-5', via='orm')
	print('\ncommitted')
else:
	print('\ndry run; set APPLY=1 to commit')
