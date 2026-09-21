"""What a search engine is told about this site.

Google had indexed 85 pages and passed over 137. The largest reason was that
nothing told it what exists -- `/sitemap.xml` and `/robots.txt` both answered
404 -- and the next was that two hosts each declared themselves canonical.
"""

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from .editing import create_table


def document(title):
	return {'Title': title, 'Parameters': {'n': {'type': 'Z'}},
	        'Numbers': {'1': '2'}}


class TheSiteSaysWhatItHolds(TestCase):

	def setUp(self):
		self.user = User.objects.create_user('indexer', password='x')
		self.table = create_table(document('A published table'),
		                          author=self.user, via='api')
		self.draft = create_table(document('A draft table'),
		                          author=self.user, via='api',
		                          published=False)

	def test_the_sitemap_lists_a_published_table(self):
		body = self.client.get('/sitemap-tables.xml',
		                       HTTP_HOST='numberdb.org').content.decode()
		self.assertIn('/%s<' % self.table.tid, body)

	def test_the_sitemap_leaves_drafts_out(self):
		#A draft answers 404 to a reader, so listing one would be an
		#invitation to a page that does not exist -- which is how a soft 404
		#is earned.
		body = self.client.get('/sitemap-tables.xml',
		                       HTTP_HOST='numberdb.org').content.decode()
		self.assertNotIn('/%s<' % self.draft.tid, body)

	def test_the_sitemap_says_when_a_table_last_changed(self):
		body = self.client.get('/sitemap-tables.xml',
		                       HTTP_HOST='numberdb.org').content.decode()
		self.assertIn('<lastmod>', body)

	def test_the_index_offers_every_section(self):
		body = self.client.get('/sitemap.xml',
		                       HTTP_HOST='numberdb.org').content.decode()
		for section in ('tables', 'tags', 'pages'):
			self.assertIn('sitemap-%s.xml' % section, body)

	def test_robots_points_at_the_sitemap_and_keeps_crawlers_out_of_the_private_parts(self):
		body = self.client.get('/robots.txt',
		                       HTTP_HOST='numberdb.org').content.decode()
		self.assertIn('Sitemap: http://numberdb.org/sitemap.xml', body)
		for private in ('/api/', '/accounts/', '/overview', '/review'):
			self.assertIn('Disallow: %s' % private, body)


@override_settings(NUMBERDB_CANONICAL_ORIGIN='https://numberdb.org')
class OneHostIsCanonical(TestCase):

	def setUp(self):
		self.user = User.objects.create_user('canon', password='x')
		self.table = create_table(document('A canonical table'),
		                          author=self.user, via='api')

	def canonical(self, host):
		body = self.client.get('/%s' % self.table.tid,
		                       HTTP_HOST=host).content.decode()
		import re

		found = re.search(r'<link rel="canonical" href="([^"]+)"', body)
		return found.group(1) if found else None

	def test_the_same_address_whichever_host_was_asked(self):
		#Built from the request until now, so www declared itself canonical
		#while the apex declared itself: two complete copies of the site, each
		#insisting it was the original.
		self.assertEqual(self.canonical('numberdb.org'),
		                 self.canonical('www.numberdb.org'))
		self.assertTrue(
			self.canonical('www.numberdb.org').startswith(
				'https://numberdb.org/'))


class AMissingTagIsNotAnError(TestCase):

	def test_a_tag_nobody_has_used_answers_404(self):
		#It answered 500, which is a claim that the site is broken.
		answer = self.client.get('/tags/no-such-tag-here',
		                         HTTP_HOST='numberdb.org')
		self.assertEqual(answer.status_code, 404)
