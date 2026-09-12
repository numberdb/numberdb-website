"""The skill a program downloads is the skill in this repository.

`views.skill` reads `.claude/skills/numberdb-table/SKILL.md` at request time
rather than copying it, so the two cannot drift -- which is the right design
and is why this does not test for drift. What it tests is the thing that can
still go wrong: the file not being where the view looks, on a server where
nobody would notice until an agent fetched the page and got a 404 in the
middle of a campaign.

Every build run fetches this page. `run.sh` refuses to start when it cannot,
so a missing file stops the work rather than quietly building tables against
whatever the agent already believed.
"""

import os

from django.conf import settings
from django.test import Client, TestCase


def skill_path():
	return os.path.join(settings.BASE_DIR, '.claude', 'skills',
	                    'numberdb-table', 'SKILL.md')


class TheSkillIsWhereTheSiteLooksForIt(TestCase):

	def get(self, url):
		return Client().get(url, HTTP_HOST='numberdb.org')

	def test_the_file_is_installed(self):
		self.assertTrue(os.path.exists(skill_path()),
		                '%s is missing; /skill will 404 and every build run '
		                'will refuse to start' % skill_path())

	def test_the_page_is_the_file(self):
		with open(skill_path(), encoding='utf8') as handle:
			expected = handle.read()
		answer = self.get('/skill.md')
		self.assertEqual(answer.status_code, 200)
		self.assertEqual(answer.content.decode('utf-8'), expected)

	def test_both_addresses_serve_it(self):
		#`/skill` is what the prompts cite and what a person follows; `/skill.md`
		#is the same text at a name that says what it is.
		for url in ('/skill', '/skill.md'):
			with self.subTest(url=url):
				self.assertEqual(self.get(url).status_code, 200)

	def test_it_is_markdown_and_not_a_rendered_page(self):
		answer = self.get('/skill.md')
		self.assertIn('text/markdown', answer['Content-Type'])
		self.assertNotIn(b'<html', answer.content[:200].lower())

	def test_it_carries_the_rules_a_build_depends_on(self):
		#Not the whole text -- that would fail on every edit -- but the two
		#things a run is told to look for, so an empty or truncated file is
		#caught rather than served.
		body = self.get('/skill.md').content.decode('utf-8')
		self.assertGreater(len(body), 5000)
		self.assertIn('numberdb', body)
