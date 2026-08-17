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


class TheSkillIsFindableByToolsThatAreNotThisOne(TestCase):
	"""`.claude/skills/` is one tool's convention, and nothing else looks
	there. The pointers that make the file findable otherwise are worth a test,
	because they are the kind of line that survives a rewrite by luck."""

	def test_agents_md_points_at_the_skill(self):
		import os

		from django.conf import settings

		with open(os.path.join(settings.BASE_DIR, 'AGENTS.md'),
		          encoding='utf8') as handle:
			body = handle.read()
		self.assertIn('.claude/skills/numberdb-table/SKILL.md', body)
		self.assertIn('numberdb.org/skill', body)

	def test_the_help_page_points_at_it_too(self):
		body = self.client.get('/help').content.decode()
		self.assertIn('/skill', body)


class TheSkillSaysTheThingsThatWentWrong(TestCase):
	"""Each of these is in the skill because it happened, and none of them was
	caught by a test at the time. If the skill loses them it is a description
	of the interface rather than of the work."""

	def setUp(self):
		self.body = self.client.get('/skill').content.decode()

	def test_it_says_the_database_is_not_only_real_numbers(self):
		#The opening said "number" twice and quietly excluded half the corpus:
		#12 polynomial tables, 6 p-adic, 4 complex.
		for kind in ('polynomial', 'p-adic', 'complex'):
			with self.subTest(kind=kind):
				self.assertIn(kind, self.body)

	def test_it_lists_every_type_a_table_may_declare(self):
		from .validate import DATA_TYPES

		for declared in DATA_TYPES:
			with self.subTest(type=declared):
				self.assertIn('`%s`' % (declared,), self.body)

	def test_it_says_what_a_written_real_means(self):
		#The convention the whole database rests on: 3.14 *is* an interval.
		self.assertIn('[3.13, 3.15]', self.body)

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


class TheSkillCanBeFound(TestCase):
	"""Nothing makes `/skill` discoverable by itself.

	A path is not a convention. `/llms.txt` is as close as there is to one --
	a root-level index of a site's documents for a language model -- and a
	footer link is how a person finds it. Both are one line and both are the
	kind of line that disappears in a redesign.
	"""

	def test_llms_txt_is_served_and_points_at_the_skill(self):
		response = self.client.get('/llms.txt')
		self.assertEqual(response.status_code, 200)
		self.assertTrue(response['Content-Type'].startswith('text/markdown'))
		body = response.content.decode()
		self.assertIn('numberdb.org/skill', body)

	def test_llms_txt_describes_what_the_database_holds(self):
		body = self.client.get('/llms.txt').content.decode()
		for kind in ('polynomial', 'p-adic', 'complex'):
			with self.subTest(kind=kind):
				self.assertIn(kind, body)

	def test_the_footer_links_the_skill_on_every_page(self):
		for path in ('/', '/help', '/tables'):
			with self.subTest(path=path):
				body = self.client.get(path).content.decode()
				self.assertIn('/skill', body)


class NoTemplateSyntaxReachesTheReader(TestCase):
	"""A `{# ... #}` comment is read only to the end of its line.

	A multi-line one is not a comment at all: Django prints it. One shipped in
	the site footer and so appeared on every page. Nothing failed -- the page
	was valid, the link worked, the tests passed -- and it was visible to
	anybody who scrolled down.
	"""

	def test_no_page_shows_its_own_markup(self):
		for path in ('/', '/help', '/tables', '/privacy', '/impressum'):
			with self.subTest(path=path):
				body = self.client.get(path).content.decode()
				for leak in ('{#', '{%', '#}'):
					self.assertNotIn(leak, body,
					                 '%s leaks %r' % (path, leak))
