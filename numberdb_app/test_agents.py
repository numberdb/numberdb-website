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
