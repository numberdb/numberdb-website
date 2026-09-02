"""T133: comment (12) ends with a dangling comma.

Run with:  manage.py shell < critique-T133.py      (APPLY=1 to commit)

The edit of 2026-09-02 cut the instruction to whoever builds a Hermite table
("must divide the density by $\\sqrt\\pi$ and say so") and the closing "None
of those is tabulated here", both of which were addressed to the corpus
rather than to a reader. It cut the Laguerre clause with them, and left the
sentence ending on a comma. The Laguerre case is the third of the three
families the comment is about, and it is the one where the answer is
rational as it stands.
"""
import os

from django.contrib.auth.models import User

from agents.session_edit import edit_with_person
from numberdb_app.editing import tree_of
from numberdb_app.models import Table

APPLY = os.environ.get('APPLY') == '1'

table = Table.objects.get(tid='T133')
tree = dict(tree_of(table.head_revision))

comments = dict(tree['Comments'])
text = comments['comment-other-families']
tail = r'($2$, $4x$, $8x^2-8$, $16x^3-40x$),'
if not text.rstrip().endswith(tail):
	raise SystemExit('T133: comment-other-families does not end as expected:\n'
	                 + repr(text[-120:]))
comments['comment-other-families'] = text.rstrip()[:-1] + (
	r'; for the HREF{Laguerre_polynomials}[Laguerre polynomials $L_n$] with '
	r'$e^{-x}$ the result is rational as it stands ($-1$, '
	r'$\frac12x-\frac32$, $-\frac16x^2+\frac43x-\frac{11}{6}$).')
tree['Comments'] = comments

print('now:', comments['comment-other-families'][-230:])

if APPLY:
	edit_with_person(
		table, tree, User.objects.get(username='bmatschke'),
		('restore the Laguerre clause, which went with the sentence about '
		 'how a Hermite table ought to be normalised and left the comment '
		 'ending on a comma'),
		assistant='claude-opus-5', via='orm')
	print('\ncommitted')
else:
	print('\ndry run; set APPLY=1 to commit')
