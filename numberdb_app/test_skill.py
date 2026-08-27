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


class EveryGeneratorSaysHowToRunIt(TestCase):
	"""A generator is downloaded from the table it made, by somebody who has
	neither this repository nor a way to guess the command.

	Fourteen of fifteen said it and one did not, which is what a convention
	kept by hand looks like just before it stops being one.
	"""

	def generators(self):
		import glob
		import os

		from django.conf import settings

		found = sorted(glob.glob(os.path.join(settings.BASE_DIR, 'generators',
		                                      '*', 'generate.py')))
		self.assertTrue(found, 'no generators found -- is the directory mounted?')
		return found

	def test_each_one_gives_the_terminal_commands(self):
		for path in self.generators():
			with self.subTest(generator=path.split('/')[-2]):
				with open(path, encoding='utf8') as handle:
					head = handle.read(4000)
				self.assertIn('sage -pip install numberdb', head)
				self.assertIn('sage -python generate.py', head)
				self.assertIn('--publish', head)

	def test_the_commands_are_in_the_docstring_not_buried(self):
		#First forty lines, so it is the first thing read rather than a note
		#somewhere after two pages of reasoning.
		for path in self.generators():
			with self.subTest(generator=path.split('/')[-2]):
				with open(path, encoding='utf8') as handle:
					head = ''.join(handle.readlines()[:40])
				self.assertIn('sage -python generate.py', head)


class TheSkillSaysWhenToStop(TestCase):
	"""Size advice that says only "500 to 1000" is wrong for half the corpus.

	The polynomial tables run to n = 50 or 100, because entries that grow make
	a table expensive cubically -- and, before that, because nobody looks up
	the 500th Chebyshev polynomial. A skill that gives one number teaches an
	assistant to fill a table with values nobody was looking for.
	"""

	def setUp(self):
		self.body = self.client.get('/skill').content.decode()

	def test_it_says_a_table_is_a_reference_not_a_dump(self):
		self.assertIn('reference, not a dump', self.body)

	def test_it_says_to_measure_before_choosing_a_range(self):
		self.assertIn('largest entry', self.body)

	def test_it_gives_the_measured_cost_of_growing_entries(self):
		#The numbers, so the advice can be checked rather than believed.
		for measured in ('472 KB', '6639 KB'):
			with self.subTest(measured=measured):
				self.assertIn(measured, self.body)

	def test_it_aims_below_the_soft_limit_rather_than_at_it(self):
		#A table that only just fits cannot be extended without breaching the
		#limit, which makes the limit a target instead of a margin.
		self.assertIn('half the soft block limit', self.body)
		self.assertIn('160 KB', self.body)

	def test_it_requires_a_generator_to_say_how_it_is_run(self):
		self.assertIn('sage -pip install numberdb', self.body)
		self.assertIn('Open the file with the commands to run it', self.body)


class TheSkillCarriesWhatTheFirstTablesTaught(TestCase):
	"""T108 and T109 were made with this skill and needed six rounds of
	correction. Each round that was the skill's fault, rather than a mistake
	anybody could make once, is a line in it now."""

	def setUp(self):
		self.body = self.client.get('/skill').content.decode()

	def test_it_says_to_search_the_database_first(self):
		#Wikipedia was cited for the Chebyshev polynomials, which are T99.
		self.assertIn('Look at the database before writing anything', self.body)
		self.assertIn('lands on the numbers', self.body)

	def test_it_says_where_each_thing_goes(self):
		#The definitions grew to hold conventions, caveats and cross-links.
		self.assertIn('Where each thing goes', self.body)
		for section in ('Definition', 'Comments', 'Formulas', 'Similar tables',
		                'References'):
			with self.subTest(section=section):
				self.assertIn(section, self.body)

	def test_it_says_notation_must_be_defined(self):
		#A comment said the values are U_n(x,-1) and never said what U was.
		self.assertIn('Define notation where you use it', self.body)

	def test_it_puts_readability_before_the_size_limit(self):
		#150 fitted every limit and was still too long to read.
		self.assertIn('readability, not size', self.body)

	def test_it_says_a_measurement_needs_a_control(self):
		#The control returned zero for everything and confirmed nothing.
		self.assertIn('control', self.body)
		self.assertIn('answer you already know', self.body)

	def test_it_treats_a_suggestion_as_a_hypothesis(self):
		#"Tag them as orthogonal polynomials" was reasonable and false.
		self.assertIn('a hypothesis', self.body)

	def test_it_describes_the_four_acts(self):
		for act in ('X-Draft: yes', 'review queue', 'answer search by number'):
			with self.subTest(act=act):
				self.assertIn(act, self.body)


class TheSkillWarnsAboutDivision(TestCase):
	"""A generator that divides can be exact up to 2^53 and wrong after it.

	`sage -python` has no preparser, so `factorial(30)` is a Python int and
	`factorial(n) / k` is float division. A Bessel polynomial built that way
	was right to n = 15 and wrong from n = 16, in the last two digits.
	"""

	def setUp(self):
		self.body = self.client.get('/skill').content.decode()

	def test_it_says_what_goes_wrong(self):
		self.assertIn('float', self.body)
		self.assertIn('2^53', self.body)

	def test_it_gives_both_ways_out(self):
		self.assertIn('recurrence that only multiplies and adds', self.body)
		self.assertIn('QQ(a) / QQ(b)', self.body)

	def test_it_says_the_obvious_check_does_not_catch_it(self):
		self.assertIn('float that', self.body)


class TheSkillSaysNotToGuessAnAddress(TestCase):
	"""A slug is not the title with underscores: the mathematics is dropped,
	it is truncated, and a clash appends a number. A link written to
	`Power_sum_polynomials` for a table at `Power_sum_symmetric_polynomials`
	points at nothing, and the audit only catches it afterwards."""

	def test_it_says_to_read_the_address_rather_than_derive_it(self):
		body = self.client.get('/skill').content.decode()
		self.assertIn("Never guess a table's address", body)
		self.assertIn('audit_table', body)
