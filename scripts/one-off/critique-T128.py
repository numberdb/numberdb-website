"""T128, from the stage-three critique of 2026-09-02.

Run with:  manage.py shell < critique-T128.py      (APPLY=1 to commit)

  1. Six Similar tables, none of them with a caption. The section was never
     drawn until today, so nobody saw that they would render as their own
     slugs, underscores and all. Captions, and the two tables the corpus
     has grown since -- the regulators this table's comment names, and the
     values of the same $\\zeta_K$ at negative odd integers.
  2. Comment (6) says "the class number formula below", and the page draws
     Formulas above Comments. Named by CITE, which renders as its number
     and stays right whatever the order.
  3. Two sentences about the run: a count in comment (9), and comment (5)
     turning "these are all the $L(1,\\chi)$ for real primitive $\\chi$"
     into a statement about a conductor bound.
  4. The program promises 38 digits from PARI and gives 15 in Sage.
  5. A double hyphen, which the site does not turn into a dash.
"""
import os

from django.contrib.auth.models import User

from agents.session_edit import edit_with_person
from numberdb_app.editing import tree_of
from numberdb_app.models import Table

APPLY = os.environ.get('APPLY') == '1'

table = Table.objects.get(tid='T128')
tree = dict(tree_of(table.head_revision))
changed = []


def swap(section, label, before, after):
	block = dict(tree.get(section) or {})
	text = block[label]
	if before not in text:
		raise SystemExit('T128 %s/%s: not found: %r' % (section, label, before))
	block[label] = text.replace(before, after)
	tree[section] = block
	changed.append('%s/%s' % (section, label))


# 1 --------------------------------------------------------------------------
CAPTIONS = {
	'Rational_multiples_of_pi': 'Rational multiples of $\\pi$',
	'Golden_ratio': 'Golden ratio',
	'Values_of_the_Riemann_zeta_function_at_rational_numbers':
		'Values of the Riemann zeta function at rational numbers',
	'Zeros_of_Dirichlet_L_functions': 'Zeros of Dirichlet $L$-functions',
	'Generalized_Bernoulli_numbers': 'Generalized Bernoulli numbers',
	'J-invariants_of_elliptic_curves_over_quadratic_fields_with_everywere_'
	'good_reduction':
		'$j$-invariants of elliptic curves over quadratic fields with '
		'everywhere good reduction',
}
similar = [dict(item) for item in (tree.get('Similar tables') or [])]
for item in similar:
	named = item.get('table', '')
	if not (named.startswith('HREF{') and named.endswith('}')):
		continue                      # already carries a caption
	slug = named[len('HREF{'):-1]
	if slug not in CAPTIONS:
		raise SystemExit('T128 Similar tables: no caption for %r' % (slug,))
	item['table'] = 'HREF{%s}[%s]' % (slug, CAPTIONS[slug])
similar.append({
	'table': 'HREF{Values_of_Dedekind_zeta_functions_of_real_quadratic_'
	         'fields_at_negative_odd_integers}[Values of Dedekind zeta '
	         'functions of real quadratic fields at negative odd integers]',
	'relation': r'the same $\zeta_K$ for the real fields, at $s=-1,-3,-5$',
})
similar.append({
	'table': 'HREF{Regulators_of_real_quadratic_fields}[Regulators of real '
	         'quadratic fields]',
	'relation': r'$\log\varepsilon_K$, the other factor of the class number '
	            r'formula for $D>0$',
})
tree['Similar tables'] = similar
changed.append('Similar tables')

# 2 and 5 --------------------------------------------------------------------
swap('Comments', 'comment-notation',
     'so that the class number formula below turns the value into a closed '
     'form',
     'so that the class number formula CITE{formula-class-number-real} or '
     'CITE{formula-class-number-imaginary} turns the value into a closed '
     'form')
swap('Comments', 'comment-notation',
     'the ring of integers of $K$ -- of the maximal order,',
     'the ring of integers of $K$, that is of the maximal order,')

# 3 --------------------------------------------------------------------------
swap('Comments', 'comment-discriminant',
     r' Every fundamental discriminant with $|D|\leq 1000$ is listed: 305 '
     'negative and 302 positive.', '')
swap('Comments', 'comment-L-value',
     'for all real primitive characters $\\chi$ of conductor at most $1000$',
     'for every real primitive character $\\chi$, whose conductor is $|D|$')

properties = dict(tree['Data properties'])
properties['complete-note'] = (
	r'every fundamental discriminant with $|D|\leq 1000$ is here, 305 '
	r'negative and 302 positive')
tree['Data properties'] = properties
changed.append('Data properties')

# 4 --------------------------------------------------------------------------
programs = dict(tree['Programs'])
sage = dict(programs['program-sage'])
before = '# or, as a 38-digit float from PARI:  pari.lfun(D, 1)'
if before not in sage['code']:
	raise SystemExit('T128: the PARI line moved')
sage['code'] = sage['code'].replace(
	before, "# or, as a float at PARI's working precision:  pari.lfun(D, 1)")
programs['program-sage'] = sage
tree['Programs'] = programs
changed.append('Programs/program-sage')

for name in changed:
	print('changed:', name)
print()
for item in tree['Similar tables']:
	print(' *', item['table'])

if APPLY:
	edit_with_person(
		table, tree, User.objects.get(username='bmatschke'),
		('the six related tables had no captions and the site has only just '
		 'begun to draw that section, so they would have rendered as their '
		 'slugs; add captions and the two tables the corpus has grown since. '
		 'Also name the class number formula instead of pointing below at '
		 'what the page draws above, move a count into complete-note, say '
		 'what the L-values are rather than what conductor was reached, and '
		 'stop promising 38 digits from PARI, which gives 15 through Sage'),
		assistant='claude-opus-5', via='orm')
	print('\ncommitted')
else:
	print('\ndry run; set APPLY=1 to commit')
