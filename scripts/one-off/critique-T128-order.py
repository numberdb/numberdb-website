"""T128 lists its discriminants in an order no reader expects.

Run with:  sage -python ... shell -c  (APPLY=1 to commit)

The page runs 5, 8, -3, -4, -7, -8, 12, 13, ..., 97, -11, -15, ..., 101,
104, ..., 997, -101, ..., -996: sorted by number of characters and then as
strings, so the negatives sit in three blocks after the positives of the
same width. Somebody looking for $D=-101$ scrolls past $D=997$.

The generator meant better -- `fundamental_discriminants` says "ordered by
$|D|$, $-D$ first" and does that -- and somewhere between it and the stored
document the order became (length, string).

Only a table with discriminants of both signs is affected: for positives
alone, and for negatives alone, (length, string) is already ascending in
$|D|$. So this reorders one table rather than changing how the site sorts
every table, which is a larger decision and belongs to a person.
"""
import os

from django.contrib.auth.models import User

from agents.session_edit import edit_with_person
from numberdb_app.editing import tree_of
from numberdb_app.models import Table

APPLY = os.environ.get('APPLY') == '1'

table = Table.objects.get(tid='T128')
tree = dict(tree_of(table.head_revision))

numbers = tree['Numbers']
if not isinstance(numbers, dict):
	raise SystemExit('T128: Numbers is a %s, not a mapping' % (
		type(numbers).__name__,))

before = list(numbers.keys())
#By |D|, the negative one first, which is what the generator says it does.
order = sorted(before, key=lambda key: (abs(int(key)), int(key)))
if order == before:
	raise SystemExit('T128: the entries are already in that order')

tree['Numbers'] = {key: numbers[key] for key in order}

print('entries      :', len(order))
print('was, first 12:', ' '.join(before[:12]))
print('now, first 12:', ' '.join(order[:12]))
print('was, last 6  :', ' '.join(before[-6:]))
print('now, last 6  :', ' '.join(order[-6:]))
assert sorted(before) == sorted(order), 'an entry was lost'
print('same entries : yes')

if APPLY:
	edit_with_person(
		table, tree, User.objects.get(username='bmatschke'),
		("the 607 discriminants were ordered by width and then as strings, "
		 "so the negative ones sat in blocks after the positive ones and a "
		 "reader looking for D=-101 scrolled past D=997; order them by |D| "
		 "with the negative one first, as the generator says it does"),
		assistant='claude-opus-5', via='orm')
	print('\ncommitted')
else:
	print('\ndry run; set APPLY=1 to commit')
