"""Every routed API view still carries the decorators it needs.

This exists because the decorators are easy to steal and nothing notices.

A new view is written directly above an existing one, anchored on the blank
lines between them -- and the anchor lands *between* the old view's decorators
and its `def`. The decorators stay where they were, which is now above the new
function, and the old one silently loses them. It happened twice:

    499a72e  table_lease gets @csrf_exempt @rate_limited
    45a54ba  costs is inserted above it, and takes them
    c354f45  claim is inserted above costs, and takes them again

The symptom is not an error anywhere near the change. `csrf_exempt` is what
lets a machine with an API key POST at all, so losing it turns every write
from the build machines into HTTP 403 with Django's CSRF page -- HTML, not
JSON, so `sync-costs.sh` logged "refused: <!DOCTYPE html>" and carried on,
being deliberately non-fatal. Between 2026-09-21 and 2026-09-22 ten tables
(T392-T401) were built and published with their costs stranded in four
ledgers on the builder, and the overview showed no cost for any of them.

So the rule is checked rather than remembered: a view that is routed and
accepts an unsafe method is `csrf_exempt`, a view that is routed is
`rate_limited`, and no view carries the same decorator twice -- the duplicate
is the fingerprint of a stack that was absorbed from the function below.
"""

import ast
import os
import re
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
UNSAFE = ("'POST'", "'PUT'", "'DELETE'", "'PATCH'",
          '"POST"', '"PUT"', '"DELETE"', '"PATCH"')


def _routed():
	"""The api.* names urls.py actually routes."""
	with open(os.path.join(HERE, 'urls.py')) as handle:
		return set(re.findall(r'\bapi\.(\w+)', handle.read()))


def _views():
	"""Each routed view as (name, decorators, whether it writes)."""
	with open(os.path.join(HERE, 'api.py')) as handle:
		tree = ast.parse(handle.read())
	routed = _routed()
	for node in tree.body:
		if not isinstance(node, ast.FunctionDef) or node.name not in routed:
			continue
		source = ast.unparse(node)
		yield (node.name,
		       [ast.unparse(d) for d in node.decorator_list],
		       any(method in source for method in UNSAFE))


class TheDecoratorsAreWhereTheyBelong(unittest.TestCase):

	def test_there_are_routed_views_to_check(self):
		#Guard against the parsing quietly finding nothing, which would make
		#every other test here pass for the wrong reason.
		self.assertGreater(len(list(_views())), 8)

	def test_a_view_that_writes_is_csrf_exempt(self):
		#Without it the write answers 403 to every key-authenticated caller,
		#and answers it in HTML, which is why no client reported it as an
		#error worth stopping for.
		missing = [name for name, decorators, writes in _views()
		           if writes and 'csrf_exempt' not in decorators]
		self.assertEqual(missing, [], 'these views write and are not '
		                             'csrf_exempt: %s' % (missing,))

	def test_a_routed_view_is_rate_limited(self):
		missing = [name for name, decorators, _ in _views()
		           if 'rate_limited' not in decorators]
		self.assertEqual(missing, [], 'these routed views are not '
		                              'rate_limited: %s' % (missing,))

	def test_no_view_carries_a_decorator_twice(self):
		#Harmless in itself -- `csrf_exempt` twice is `csrf_exempt`. It is
		#checked because of what it means: a function whose stack is doubled
		#has absorbed the decorators of the function under it, which is now
		#bare. Both times this happened, the duplicate was visible in the
		#diff and nobody read it as a symptom.
		doubled = [(name, decorators) for name, decorators, _ in _views()
		           if len(decorators) != len(set(decorators))]
		self.assertEqual(doubled, [], 'a doubled decorator means the view '
		                              'below it lost one: %s' % (doubled,))


if __name__ == '__main__':
	unittest.main(verbosity=2)
