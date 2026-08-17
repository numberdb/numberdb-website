"""The agent skill, and the one thing that can go wrong with publishing it.

Instructions kept in two places drift, and the copy that drifts is the one
somebody is reading. So the site serves the repository's file rather than a
copy of it, and this holds that arrangement in place.
"""

import os

from django.conf import settings
from django.test import TestCase

SKILL_PATH = os.path.join(settings.BASE_DIR, '.claude', 'skills',
                          'numberdb-table', 'SKILL.md')


class TheSkillIsServed(TestCase):

	def test_it_is_the_repositorys_own_file(self):
		with open(SKILL_PATH, encoding='utf8') as handle:
			on_disk = handle.read()
		served = self.client.get('/skill').content.decode()
		self.assertEqual(served, on_disk)

	def test_it_is_served_as_markdown(self):
		response = self.client.get('/skill')
		self.assertEqual(response.status_code, 200)
		self.assertTrue(response['Content-Type'].startswith('text/markdown'))

	def test_the_dotted_form_works_too(self):
		#Whatever a program guesses at, it should land.
		self.assertEqual(self.client.get('/skill.md').status_code, 200)

	def test_it_carries_the_frontmatter_a_skill_needs(self):
		body = self.client.get('/skill').content.decode()
		self.assertTrue(body.startswith('---'))
		self.assertIn('name: numberdb-table', body)
		self.assertIn('description:', body)


class TheSkillSaysTheThingsThatWentWrong(TestCase):
	"""Each of these is in the skill because it happened, and none of them was
	caught by a test at the time. If the skill loses them it is a description
	of the interface rather than of the work."""

	def setUp(self):
		self.body = self.client.get('/skill').content.decode()

	def test_it_warns_about_the_point_interval_trap(self):
		self.assertIn('width zero', self.body)

	def test_it_requires_the_convention_to_be_stated(self):
		for needed in ('branch', 'normalisation', 'indexing'):
			with self.subTest(needed=needed):
				self.assertIn(needed, self.body)

	def test_it_lists_every_enforced_level(self):
		from .validate import RIGOUR_LEVELS

		for level in RIGOUR_LEVELS:
			with self.subTest(level=level):
				self.assertIn(level, self.body)

	def test_it_says_publishing_needs_a_key_and_review_follows(self):
		self.assertIn('API key', self.body)
		self.assertIn('review', self.body)

	def test_it_quotes_the_limits_that_are_enforced(self):
		from .limits import (HARD_ENTRY_COUNT, RECOMMENDED_DIGITS,
		                     SOFT_DIGITS, SOFT_ENTRY_COUNT)

		self.assertIn(str(RECOMMENDED_DIGITS), self.body)
		self.assertIn(str(SOFT_ENTRY_COUNT), self.body)
		self.assertIn(str(SOFT_DIGITS), self.body)
		self.assertIn('{:,}'.format(HARD_ENTRY_COUNT), self.body)
