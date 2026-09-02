"""T132, from the stage-three critique of 2026-09-02.

Run with:  manage.py shell < critique-T132.py      (APPLY=1 to commit)

  1. Comment (11) says that from $n=4$ on the weights have degree at least
     $2$. Two rows up the page, $n=5$, $k=3$ has weight $128/225$, and the
     comment before it says every odd rule has a rational central weight.
  2. Comment (8) says any other $n$ points give at most $n-1$. Any $n$
     distinct points reach $n-1$ -- that is the floor, not the ceiling --
     and Simpson's three points reach $3$.
  3. A clause about what the search box returns, in comment (9).
  4. Two formulas end with a sentence about the run.
  5. Two sentences addressed to whoever builds tables rather than to the
     reader; one of the five rules named in the second is now a table.
  6. "Asked for in [2], for the Legendre polynomials" only parses for
     somebody who has already read the issue.
"""
import os

from django.contrib.auth.models import User

from agents.session_edit import edit_with_person
from numberdb_app.editing import tree_of
from numberdb_app.models import Table

APPLY = os.environ.get('APPLY') == '1'

table = Table.objects.get(tid='T132')
tree = dict(tree_of(table.head_revision))
changed = []


def swap(section, label, before, after):
	block = dict(tree.get(section) or {})
	text = block[label]
	if before not in text:
		raise SystemExit('T132 %s/%s: not found: %r' % (section, label, before))
	block[label] = text.replace(before, after)
	tree[section] = block
	changed.append('%s/%s' % (section, label))


# 1 --------------------------------------------------------------------------
# Scoped to the rules that are here, because it rests on the even part of
# $P_n$ being irreducible over $\mathbb{Q}$, which is checked for these and
# not a theorem.
swap('Comments', 'comment-closed-forms',
     r'From $n=4$ on the nodes have degree at least $4$ over $\mathbb{Q}$ '
     r'and the weights degree at least $2$',
     r'For the rules here with $n\geq 4$ the nonzero nodes have degree $n$ '
     r'over $\mathbb{Q}$ when $n$ is even and $n-1$ when $n$ is odd, and the '
     r'weights other than the central one have degree $\lfloor n/2\rfloor$')

# 2 --------------------------------------------------------------------------
swap('Comments', 'comment-nodes',
     'any other $n$ points give at most $n-1$ in general',
     'no other $n$ points reach $2n-1$, and $n$ points in general position '
     'reach only $n-1$')

# 3 --------------------------------------------------------------------------
swap('Comments', 'comment-both-halves',
     r': a reader holding $-0.7745966692\ldots$ finds it with its sign', '')

# 4 --------------------------------------------------------------------------
swap('Formulas', 'formula-weights',
     ' Both were computed for every entry and agree.', '')
swap('Formulas', 'formula-exactness',
     ' Checked in ball arithmetic on every rule here, the failure at $m=2n$ '
     'included.', '')

# 5 --------------------------------------------------------------------------
swap('Comments', 'comment-unit-interval',
     ' Those values are an affine image of the entries here rather than a '
     'multiple of them, and they are not listed separately.', '')
swap('Comments', 'comment-other-rules',
     'The Gauss–Hermite, Gauss–Laguerre, Gauss–Lobatto, Gauss–Radau and '
     'Gauss–Kronrod rules are different tables.',
     'HREF{Nodes_and_weights_of_Gauss_Hermite_quadrature}[Gauss–Hermite '
     r'quadrature] is the same construction for $e^{-x^2}$ on the whole '
     'line; the Gauss–Laguerre, Gauss–Lobatto, Gauss–Radau and '
     'Gauss–Kronrod rules are not tabulated here.')

# 6 --------------------------------------------------------------------------
swap('Comments', 'comment-requested',
     'Asked for in CITE{issue11}, for the Legendre polynomials.',
     'Asked for in CITE{issue11}, which wants the roots of the classical '
     'orthogonal polynomials; this is the Legendre case.')

for name in changed:
	print('changed:', name)
print()
print('comment-nodes:', tree['Comments']['comment-nodes'][-160:])
print()
print('comment-closed-forms:', tree['Comments']['comment-closed-forms'])

if APPLY:
	edit_with_person(
		table, tree, User.objects.get(username='bmatschke'),
		('comment (11) said the weights have degree at least 2 from n=4 on, '
		 'which the rational central weights two rows up contradict; '
		 'comment (8) had "at most n-1" where n-1 is the floor and Simpson '
		 'reaches 3; drop a clause about the search box, the run from two '
		 'formulas, and two sentences addressed to table builders; link '
		 'Gauss-Hermite, which is now a table'),
		assistant='claude-opus-5', via='orm')
	print('\ncommitted')
else:
	print('\ndry run; set APPLY=1 to commit')
