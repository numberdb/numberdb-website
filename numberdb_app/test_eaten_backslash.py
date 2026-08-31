"""A backslash eaten by a JSON escape, which is silent and unrepairable.

`\f` is a valid JSON escape, so a document written with `"$\frac{1}{3}$"`
rather than `"$\\frac{1}{3}$"` arrives holding a form feed and the letters
`rac`. It parses, it saves, and the page renders "Math input error" with the
macro simply gone. The stored value cannot be repaired from itself, because
the backslash never arrived.

T128 was filled with two of its three fractions eaten this way, and nothing
noticed until a person read the page.
"""

import json

from django.test import TestCase

from .validate import check, problems
from .editing import InvalidDocument


def document(formula):
	return {'Title': 'A table', 'Formulas': {'formula-a': formula},
	        'Numbers': {'1': '2'}}


class AnEatenBackslashIsRefused(TestCase):

	def test_a_form_feed_is_fatal(self):
		#Exactly what happened to T128.
		eaten = json.loads(r'"$1-\frac{1}{3}$"')
		self.assertIn('\x0c', eaten)
		with self.assertRaises(InvalidDocument):
			check(document(eaten))

	def test_it_says_which_macro_was_probably_meant(self):
		found = problems(document('$1-\x0crac{1}{3}$'))
		self.assertTrue(any('frac' in p.message for p in found), found)

	def test_it_names_where(self):
		found = problems(document('$1-\x0crac{1}{3}$'))
		self.assertTrue(any('Formulas' in p.message for p in found), found)

	def test_backspace_and_carriage_return_too(self):
		for character in ('\x08', '\r', '\x0b'):
			with self.assertRaises(InvalidDocument):
				check(document('$x %s eta$' % character))

	def test_newlines_and_tabs_are_ordinary(self):
		#Prose wraps and tables indent; only the escapes nobody types are
		#evidence of damage.
		self.assertEqual(check(document('a formula\nover two lines\tindented')),
		                 [])

	def test_a_correct_document_passes(self):
		self.assertEqual(check(document(r'$1-\frac{1}{3}+\frac{1}{5}$')), [])

	def test_it_looks_inside_entry_comments_too(self):
		tree = {'Title': 'A table',
		        'Numbers': {'1': {'number': '2',
		                          'comment': 'the \x0crac{1}{2} case'}}}
		with self.assertRaises(InvalidDocument):
			check(tree)
