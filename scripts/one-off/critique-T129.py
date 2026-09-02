"""T129, from the stage-three critique of 2026-09-02.

Run with:  manage.py shell < critique-T129.py      (APPLY=1 to commit)

  1. The one famous number in the table is described with two signs wrong.
     $H_\\Delta(x)=x+640320^3$, so $H_\\Delta(0)=+640320^3$; it is
     $j\\bigl((1+\\sqrt{-163})/2\\bigr)$ that is negative. And
     $e^{\\pi\\sqrt{163}}=640320^3+744-7.5\\cdot10^{-13}$: the constant
     *exceeds* the integer by $744$, it does not fall short of it. The same
     slip is in Similar tables, which the site has only just begun to draw.
  2. Three formulas end with a sentence about the run. What was checked
     belongs in "How they were obtained", which is where the other four
     checks are; in a Formulas section it reads as an apology.
  3. Two comments end with counts and character lengths that are facts
     about this build, not about $H_\\Delta$; `complete-note` is their home.
  4. Formula (4) drops a hypothesis of the theorem it cites and offers a
     search over $p<400$ instead of saying why the hypothesis is free.
"""
import os

from django.contrib.auth.models import User

from agents.session_edit import edit_with_person
from numberdb_app.editing import tree_of
from numberdb_app.models import Table

APPLY = os.environ.get('APPLY') == '1'

table = Table.objects.get(tid='T129')
tree = dict(tree_of(table.head_revision))
changed = []


def swap(section, label, before, after):
	block = dict(tree.get(section) or {})
	text = block[label]
	if before not in text:
		raise SystemExit('T129 %s/%s: not found: %r' % (section, label, before))
	block[label] = text.replace(before, after)
	tree[section] = block
	changed.append('%s/%s' % (section, label))


# 1 --------------------------------------------------------------------------
numbers = dict(tree['Numbers'])
entry = dict(numbers['-163'])
was = entry['comment']
right = (r'$h(\Delta)=1$; maximal order of $\mathbb{Q}(\sqrt{-163})$; '
         r'$H_\Delta(0)=640320^3$, the integer that '
         r"HREF{Ramanujan_constant}[Ramanujan's constant $e^{\pi\sqrt{163}}$] "
         r'exceeds by $744$ to within $10^{-12}$; the root '
         r'$j\bigl(\tfrac{1+\sqrt{-163}}{2}\bigr)=-640320^3$')
entry['comment'] = right
numbers['-163'] = entry
tree['Numbers'] = numbers
changed.append('Numbers/-163')

similar = [dict(item) for item in (tree.get('Similar tables') or [])]
found = 0
for item in similar:
	if '744-H_{-163}(0)' in (item.get('relation') or ''):
		item['relation'] = (r'$e^{\pi\sqrt{163}}$ is within $10^{-12}$ of '
		                    r'$H_{-163}(0)+744=640320^3+744$')
		found += 1
if found != 1:
	raise SystemExit('T129 Similar tables: expected one relation, found %d'
	                 % (found,))
tree['Similar tables'] = similar
changed.append('Similar tables/Ramanujan')

# 2 --------------------------------------------------------------------------
swap('Formulas', 'formula-cube', ' Checked on every entry.', '')
swap('Formulas', 'formula-diagonal',
     r' Checked against the stored $\Phi_\ell$ for $\ell=2,3,5,7,11$.', '')
swap('Formulas', 'formula-splitting',
     ' Checked here for every $\\Delta$ in the table and every prime '
     '$p<400$, both directions, with no exception.', '')

# 4 --------------------------------------------------------------------------
swap('Formulas', 'formula-splitting',
     r'(CITE{Cox}, Theorem 9.2, stated there for $\Delta=-4n$)',
     r'(CITE{Cox}, Theorem 9.2, stated there for $\Delta=-4n$ and for '
     r'$p\nmid\operatorname{disc}H_\Delta$, a hypothesis that is automatic '
     r'once $p$ splits in $K$: two singular moduli of discriminant $\Delta$ '
     r'coincide modulo $p$ only at supersingular reduction)')

# 2, continued: the checks in the one place that is for them -----------------
properties = dict(tree['Data properties'])
properties['rigour details'] = properties['rigour details'] + (
	' The stored polynomials were also checked against the cube formula on '
	'every entry, against the diagonal of the modular polynomials '
	'HREF{Modular_polynomials_for_j-invariant} for $\\ell=2,3,5,7,11$, and '
	'against the splitting criterion for every $\\Delta$ here and every prime '
	'$p<400$, in both directions.')

# 3 --------------------------------------------------------------------------
properties['complete-note'] = (
	r'every such discriminant with $|\Delta|\leq 300$ is here, 94 fundamental '
	r'and 56 not; the range is set by how long an entry becomes')
tree['Data properties'] = properties
changed.append('Data properties')

#The growth rate is why the table stops where it does, and the OEIS entry is
#where a reader goes for more: both are for the reader. The length of the
#longest stored entry is a fact about this build. "Below" is a fact about a
#page order the author of the document cannot see.
swap('Comments', 'comment-size',
     r'; the longest entry here is $\Delta=-239$, of degree $15$ and $1106$ '
     'characters. The',
     '. The')
swap('Comments', 'comment-size',
     'the Sage and PARI programs below give any further one',
     'the Sage and PARI programs here give any further one')
swap('Comments', 'comment-orders',
     ' Of the 150 entries, 94 are fundamental and 56 are not.', '')

for name in changed:
	print('changed:', name)
print()
print('was  :', was)
print('now  :', tree['Numbers']['-163']['comment'])

if APPLY:
	edit_with_person(
		table, tree, User.objects.get(username='bmatschke'),
		("the -163 comment had the sign of H(0) wrong and the direction of "
		 "the 744 wrong: H(0)=+640320^3 and Ramanujan's constant exceeds it, "
		 "rather than falling short; the same slip in Similar tables. Also "
		 "take the run out of three formulas and two comments, put what was "
		 "checked in the rigour details, and say why Cox's extra hypothesis "
		 "is free"),
		assistant='claude-opus-5', via='orm')
	print('\ncommitted')
else:
	print('\ndry run; set APPLY=1 to commit')
