"""The two stages, and the lessons each carries.

Every line asserted here is a mistake that was actually made. The prompts are
instructions to a program that starts knowing nothing, so a line quietly
dropped from one is a mistake waiting to be repeated -- which is the same
argument as `test_skill.py`, applied one level out.
"""

import os

from django.conf import settings
from django.test import TestCase


def prompt(stage):
	"""The prompt as one line of prose.

	Whitespace is collapsed because these are wrapped paragraphs: asserting on
	a phrase that happens to straddle a line break tests the wrapping rather
	than the instruction, and re-wrapping a paragraph would then fail a test
	for no reason.
	"""
	with open(os.path.join(settings.BASE_DIR, 'agents', stage, 'PROMPT.md'),
	          encoding='utf8') as handle:
		return ' '.join(handle.read().split())


class ProposingTablesKnowsWhatEarnsOne(TestCase):

	def setUp(self):
		self.body = prompt('table-ideas')

	def test_it_states_the_use_case_the_judgement_follows_from(self):
		self.assertIn('already known', self.body)

	def test_it_says_what_not_to_propose(self):
		#A table of monomials would match everything and tell nobody anything.
		self.assertIn('monomials', self.body.lower())

	def test_it_requires_a_way_to_check_the_result(self):
		self.assertIn('independent fact', self.body)

	def test_it_requires_the_conventions_to_be_named(self):
		self.assertIn('has to be decided', self.body)

	def test_it_says_to_search_the_corpus_and_the_issues_first(self):
		self.assertIn('Search the corpus', self.body)
		self.assertIn('table wanted', self.body)

	def test_it_knows_some_things_cannot_be_a_table(self):
		#A general point set is a parameter with infinitely many values.
		self.assertIn('can be a table at all', self.body)

	def test_it_forbids_building_anything(self):
		self.assertIn('do not publish', self.body.lower())


class BuildingATableCarriesEveryLessonSoFar(TestCase):

	def setUp(self):
		self.body = prompt('table-build')

	def test_it_will_not_publish(self):
		self.assertIn('not publish', self.body)

	def test_it_warns_about_float_division(self):
		#factorial(n) is a Python int in sage -python, so / is float division.
		self.assertIn('2^53', self.body)
		self.assertIn('float division', self.body)

	def test_it_warns_that_the_machinery_may_be_missing(self):
		for missing in ('.log()', 'determinant', 'expand()'):
			with self.subTest(call=missing):
				self.assertIn(missing, self.body)

	def test_it_says_to_measure_before_choosing_a_range(self):
		self.assertIn('Measure before choosing a range', self.body)
		self.assertIn('1107', self.body)

	def test_it_says_to_check_identities_before_writing_them(self):
		self.assertIn('before you write it down', self.body)
		self.assertIn('hypothesis', self.body)

	def test_it_says_to_verify_against_something_outside(self):
		self.assertIn('outside the family', self.body)
		self.assertIn('cannot catch a generator', self.body)

	def test_it_says_not_to_guess_an_address(self):
		self.assertIn('never derive a slug from a title', self.body)

	def test_it_names_the_two_limits_that_bite(self):
		self.assertIn('Six variables', self.body)
		self.assertIn('Entry comments are shown', self.body)

	def test_it_requires_the_audit(self):
		self.assertIn('audit_table', self.body)

	def test_it_sends_new_lessons_to_the_proposals_file(self):
		self.assertIn('agents/lessons/PROPOSALS.md', self.body)
		self.assertIn('Do not edit the skill yourself', self.body)


class TheLessonsLoopSaysHowALessonLands(TestCase):

	def test_a_lesson_must_arrive_with_a_test(self):
		with open(os.path.join(settings.BASE_DIR, 'agents', 'lessons',
		                       'PROPOSALS.md'), encoding='utf8') as handle:
			body = ' '.join(handle.read().split())
		self.assertIn('test_skill.py', body)
		self.assertIn('Nothing in this file is in force', body)

	def test_the_skill_is_still_asserted_line_by_line(self):
		#The guard the whole arrangement rests on: a lesson dropped from the
		#skill fails CI rather than passing quietly.
		with open(os.path.join(settings.BASE_DIR, 'numberdb_app',
		                       'test_skill.py'), encoding='utf8') as handle:
			source = handle.read()
		self.assertGreaterEqual(source.count('def test_'), 30)


class TheCheckingToolkitCatchesWhatItWasBuiltFor(TestCase):
	"""Each of these reproduces an error that was actually made.

	The toolkit exists because prose asking a run to "make sure the arithmetic
	is exact" gets a confident answer, and a function that inspects the
	coefficients does not.
	"""

	def toolkit(self):
		import importlib.util

		path = os.path.join(settings.BASE_DIR, 'agents', 'table-build',
		                    'check.py')
		spec = importlib.util.spec_from_file_location('agent_check', path)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
		return module

	def test_it_catches_a_float_pretending_to_be_an_integer(self):
		#The Bessel bug: Python ints divided with / give floats that are
		#exact to 2^53 and wrong after, and `c in ZZ` says nothing is wrong.
		complaints = self.toolkit().exactness({16: [1.0, 2.0, 92854250304440624.0]})
		self.assertTrue(complaints)
		self.assertIn('float', complaints[0])

	def test_it_looks_at_the_numbers_not_the_container(self):
		#Its first version reported "unexpected type list" for a list of
		#floats, which is a check stumbling on the shape instead of doing its
		#job.
		complaints = self.toolkit().exactness({1: [[1.5], [2.5]]})
		self.assertTrue(complaints)
		self.assertIn('float', complaints[0])

	def test_it_passes_exact_values(self):
		from fractions import Fraction

		self.assertEqual(self.toolkit().exactness({1: 3, 2: 4}), [])

	def test_it_measures_the_longest_entry(self):
		measured = self.toolkit().measure({1: 'x', 2: 'x^2 + 3*x + 1'})
		self.assertEqual(measured['entries'], 2)
		self.assertEqual(measured['longest'], len('x^2 + 3*x + 1'))
		self.assertEqual(measured['longest_at'], 2)

	def test_it_reports_a_disagreement_with_an_independent_computation(self):
		found = self.toolkit().agrees_with({1: 10, 2: 20}, lambda k: k * 10 + 1)
		self.assertEqual(len(found), 2)

	def test_it_refuses_a_generator_that_imports_sage_all(self):
		import tempfile

		with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as f:
			f.write('import numberdb.sage\nfrom sage.all import QQ\n')
			path = f.name
		complaints = self.toolkit().names_its_rings(path)
		self.assertTrue(any('sage.all' in c for c in complaints))

	def test_it_requires_the_generator_to_initialise_sage(self):
		import tempfile

		with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as f:
			f.write('from sage.rings.rational_field import QQ\n')
			path = f.name
		complaints = self.toolkit().names_its_rings(path)
		self.assertTrue(any('numberdb.sage' in c for c in complaints))


class TheRulesThatAreNotChecksAreStated(TestCase):

	def setUp(self):
		self.body = prompt('table-build')

	def test_disagreement_must_be_chased_to_a_cause(self):
		self.assertIn('neither is right until you know why', self.body)

	def test_a_measurement_needs_a_working_control(self):
		self.assertIn('control that returns an answer you already know',
		              self.body)

	def test_declining_is_allowed_and_expected(self):
		self.assertIn('Declining is a good outcome', self.body)

	def test_it_points_at_the_toolkit_rather_than_asking_for_prose(self):
		self.assertIn('check.py', self.body)
		self.assertIn('exactness', self.body)
