"""Tests for checking a document before it becomes a table.

Every case here was accepted silently before, and the results looked ordinary:
a made-up type stored as though it meant something, an entry that displayed and
answered no search, a misspelt key that reached the number builder and came
back as a parse error on an error page.

The calibration matters as much as the checks. A validator that refuses what is
already stored teaches people to work around it, so what the corpus does today
is at worst a warning.
"""

import yaml
from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase

from . import validate
from .editing import InvalidDocument, commit_table, create_table
from .models import Table


def fatal(tree):
	return [p for p in validate.problems(tree) if p.fatal]


def warnings(tree):
	return [p for p in validate.problems(tree) if not p.fatal]


class Types(SimpleTestCase):

	def doc(self, declared):
		return {'Title': 'x', 'Data properties': {'type': declared},
		        'Numbers': [{'params': {}, 'number': '1'}]}

	def test_every_type_the_corpus_uses_is_allowed(self):
		for declared in ('Z', 'Q', 'R', 'C', 'Qp', 'Z[]', 'Q[]', '*R'):
			self.assertEqual(fatal(self.doc(declared)), [], declared)

	def test_a_made_up_type_is_refused(self):
		self.assertEqual(len(fatal(self.doc('Wombat'))), 1)

	def test_a_near_miss_suggests_the_right_one(self):
		self.assertIn("'Qp'", str(fatal(self.doc('QP'))[0]))

	def test_an_unknown_parameter_type_is_refused(self):
		tree = {'Title': 'x', 'Parameters': {'n': {'type': 'Integer'}},
		        'Numbers': [{'params': {'n': '1'}, 'number': '1'}]}
		self.assertEqual(len(fatal(tree)), 1)

	def test_symbolic_is_a_parameter_type(self):
		"""27 declarations; its values are names rather than numbers."""
		tree = {'Title': 'x', 'Parameters': {'G': {'type': 'Symbolic'}},
		        'Numbers': [{'params': {'G': 'Co1'}, 'number': '1'}]}
		self.assertEqual(fatal(tree), [])


class Parameters(SimpleTestCase):

	def doc(self, params):
		return {'Title': 'x',
		        'Parameters': {'n': {'type': 'Z'}, 'k': {'type': 'Z'}},
		        'Numbers': [{'params': params, 'number': '1'}]}

	def test_the_declared_parameters_are_fine(self):
		self.assertEqual(fatal(self.doc({'n': '1', 'k': '2'})), [])

	def test_an_undeclared_parameter_is_refused(self):
		"""It saved happily and then indexed nothing at all."""
		problems = fatal(self.doc({'n': '1', 'k': '2', 'zzz': '3'}))
		self.assertEqual(len(problems), 1)
		self.assertIn('does not declare', str(problems[0]))

	def test_a_misspelt_parameter_suggests_the_right_one(self):
		self.assertIn("'k'", str(fatal(self.doc({'n': '1', 'kk': '2'}))[0]))

	def test_a_missing_parameter_is_only_a_warning(self):
		"""Seven such entries exist, and each names a family, not a value."""
		self.assertEqual(fatal(self.doc({'n': '1'})), [])
		self.assertEqual(len(warnings(self.doc({'n': '1'}))), 1)


class EntryKeys(SimpleTestCase):

	def doc(self, record):
		return {'Title': 'x', 'Numbers': [record]}

	def test_a_misspelt_structural_key_is_refused(self):
		"""`numbr` is not prose about the entry, it is a value that vanishes."""
		problems = fatal(self.doc({'params': {}, 'numbr': '3.14'}))
		self.assertTrue(any('number' in str(p) for p in problems))

	def test_an_entry_with_no_value_at_all_is_refused(self):
		self.assertTrue(fatal(self.doc({'params': {}, 'comment': 'hello'})))

	def test_an_unknown_annotation_is_kept_without_complaint(self):
		"""The format has been extended four times exactly this way."""
		tree = self.doc({'params': {}, 'number': '1',
		                 'provenance': 'measured in 1987'})
		self.assertEqual(fatal(tree), [])
		self.assertEqual(warnings(tree), [])

	def test_a_near_miss_annotation_is_a_warning_only(self):
		tree = self.doc({'params': {}, 'number': '1', 'commnt': 'typo'})
		self.assertEqual(fatal(tree), [])
		self.assertEqual(len(warnings(tree)), 1)

	def test_an_equals_without_a_number_is_allowed_and_noted(self):
		tree = self.doc({'params': {}, 'equals': 'HREF{Pi}'})
		self.assertEqual(fatal(tree), [])
		self.assertEqual(len(warnings(tree)), 1)


class ThroughTheWritePath(TestCase):

	def setUp(self):
		self.author = User.objects.create_user('validating')
		self.table = create_table(
			{'Title': 'Validation probe',
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '3.14159'}]},
			author=self.author,
		via='orm')

	def edit(self, tree):
		return commit_table(self.table, tree, author=self.author,
		                    base=self.table.head_revision,
		via='orm')

	def test_a_bad_type_never_reaches_the_table(self):
		with self.assertRaises(InvalidDocument):
			self.edit({'Title': 'Validation probe',
			           'Data properties': {'type': 'Wombat'},
			           'Parameters': {'n': {'type': 'Z'}},
			           'Numbers': [{'params': {'n': '1'}, 'number': '2'}]})
		self.table.refresh_from_db()
		self.assertEqual(
			[p for p in validate.problems(
				yaml.load(self.table.head_revision.content,
				          Loader=yaml.BaseLoader)) if p.fatal], [])

	def test_an_undeclared_parameter_never_reaches_the_table(self):
		with self.assertRaises(InvalidDocument):
			self.edit({'Title': 'Validation probe',
			           'Parameters': {'n': {'type': 'Z'}},
			           'Numbers': [{'params': {'n': '1', 'q': '9'},
			                        'number': '2'}]})

	def test_a_warning_is_saved_and_carried_back(self):
		outcome = self.edit(
			{'Title': 'Validation probe',
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '2',
			              'commnt': 'typo'}]})
		self.assertIsNotNone(outcome.revision)
		self.assertEqual(len(outcome.problems), 1)


class TheCorpusPasses(TestCase):
	"""A validator that refuses what is already stored is worked around."""

	def test_no_stored_table_is_refused(self):
		from .models import TableData

		data = list(TableData.objects.all()[:200])
		if not data:
			self.skipTest('no tables loaded')
		for td in data:
			tree = yaml.load(td.full_yaml, Loader=yaml.BaseLoader) or {}
			self.assertEqual(fatal(tree), [], str(td.table))


class ADeclaredValueList(SimpleTestCase):
	"""A parameter that says how its values are written has said what they are.

	`values: {a: $a$, b: $b$}` is both the display and the vocabulary, so a
	third value is a typo -- and a typo here does not fail. It creates an entry
	nobody meant, under an identity nobody will ever cite.
	"""

	def tree(self, value):
		return {'Title': 'x',
		        'Parameters': {'v': {'type': 'Symbolic',
		                             'values': {'a': '$a$', 'b': '$b$'}}},
		        'Numbers': [{'params': {'v': value}, 'number': '1'}]}

	def test_a_declared_value_is_fine(self):
		self.assertEqual(fatal(self.tree('a')), [])

	def test_a_value_outside_the_list_is_refused(self):
		problems = fatal(self.tree('z'))
		self.assertEqual(len(problems), 1)
		self.assertIn("not one of its values", str(problems[0]))

	def test_a_parameter_without_a_list_accepts_anything(self):
		tree = {'Title': 'x',
		        'Parameters': {'v': {'type': 'Symbolic'}},
		        'Numbers': [{'params': {'v': 'anything'}, 'number': '1'}]}
		self.assertEqual(fatal(tree), [])
