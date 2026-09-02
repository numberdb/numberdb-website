"""T127, from the stage-three critique of 2026-09-02.

Run with:  manage.py shell < critique-T127.py      (APPLY=1 to commit)

  1. "Table is complete: no" and nothing more. What it does hold -- every
     even $n\\leq 40$, fifty zeros each -- can only be learnt by scrolling
     1050 rows to see where they stop.
  2. Comment (5) compares this table with six others and links none of
     them; its mathematical content is the comment before it, and the
     rigour details already say the index is proven.
  3. Two thirds of the values are half-integers to twenty digits and
     nothing on the page says why. It is one line of mathematics: the two
     poles either side dominate and cancel at their midpoint, and the
     imbalance comes from the terms with no partner, the ones the series
     would need at $j<0$.
  4. Comment (1) ends with a sentence about this table.
"""
import os

from django.contrib.auth.models import User

from agents.session_edit import edit_with_person
from numberdb_app.editing import tree_of
from numberdb_app.models import Table

APPLY = os.environ.get('APPLY') == '1'

table = Table.objects.get(tid='T127')
tree = dict(tree_of(table.head_revision))
comments = dict(tree['Comments'])

# 1 --------------------------------------------------------------------------
properties = dict(tree['Data properties'])
properties['complete-note'] = (
	r'every even $n\leq 40$ is here, with the $50$ largest zeros of each')
tree['Data properties'] = properties

# 2 --------------------------------------------------------------------------
if 'comment-index-is-proven' not in comments:
	raise SystemExit('T127: comment-index-is-proven is already gone')
del comments['comment-index-is-proven']

# 4 --------------------------------------------------------------------------
tail = (' So the odd orders are absent from this table rather than missing '
        'from it.')
if tail not in comments['comment-only-even-n']:
	raise SystemExit('T127: the closing sentence of comment-only-even-n moved')
comments['comment-only-even-n'] = comments['comment-only-even-n'].replace(
	tail, '')

# 3 --------------------------------------------------------------------------
# Placed after the comment that says where the zeros are, since it says where
# in that interval they sit.
comments['comment-half-integers'] = (
	r'For even $n\geq 2$ the $k$-th largest zero tends to $-k+\tfrac12$ as '
	r'$n\to\infty$, which is why so many entries here are half-integers to '
	r'many digits. In the series of CITE{comment-only-even-n} the terms '
	r'$j=k-1-m$ and $j=k+m$ cancel in pairs at the midpoint of $(-k,-k+1)$, '
	r'since $n+1$ is odd; what is left are the terms $j\geq 2k$, which have '
	r'no partner because the sum starts at $j=0$. Balancing that remainder '
	r'against the two nearest poles puts the zero above the midpoint by '
	r'about $\dfrac{(2k+1)^{-(n+1)}}{4(n+1)}$.')

tree['Comments'] = comments

print('complete-note:', properties['complete-note'])
print()
print('comment-only-even-n:', comments['comment-only-even-n'])
print()
print('comment-half-integers:', comments['comment-half-integers'])
print()
print('comments now:', list(comments.keys()))

if APPLY:
	edit_with_person(
		table, tree, User.objects.get(username='bmatschke'),
		("say what the table covers instead of only that it is "
		 "incomplete; say why the entries are so near half-integers; "
		 "drop the comparison with six tables it does not link"),
		assistant='claude-opus-5', via='orm')
	print('\ncommitted')
else:
	print('\ndry run; set APPLY=1 to commit')
