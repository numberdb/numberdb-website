"""Tests for the privacy policy, the legal notice, and the claims they make.

Most of this file is not about the pages. It is about the sentences on them.
A privacy policy is a set of factual claims about a program, and the only ones
worth writing down are the ones something checks -- otherwise the page slowly
becomes fiction, one well-meant change at a time, and nobody finds out until it
matters.

The claims checked here:

  * reading the site sets no cookies at all
  * the cookies that do appear are the three the page names, and no others
  * deleting an account destroys the identity and keeps the contributions
  * the export contains no credential
"""

from django.test import TestCase


class TheLegalPagesExist(TestCase):

	def test_the_privacy_policy_is_reachable_without_an_account(self):
		answer = self.client.get('/privacy')
		self.assertEqual(answer.status_code, 200)

	def test_so_is_the_legal_notice(self):
		answer = self.client.get('/impressum')
		self.assertEqual(answer.status_code, 200)

	def test_the_legal_notice_says_who_is_responsible(self):
		body = self.client.get('/impressum').content.decode()
		self.assertIn('Benjamin Matschke', body)
		self.assertIn('matschke@numberdb.org', body)

	def test_every_page_links_to_both(self):
		"""A policy nobody can reach is not published."""
		for path in ('/', '/tables', '/help', '/privacy'):
			with self.subTest(page=path):
				body = self.client.get(path).content.decode()
				self.assertIn('/privacy', body)
				self.assertIn('/impressum', body)

	def test_they_link_to_each_other(self):
		self.assertIn('/impressum',
		              self.client.get('/privacy').content.decode())
		self.assertIn('/privacy',
		              self.client.get('/impressum').content.decode())


class ReadingTheSiteSetsNoCookies(TestCase):
	"""The claim that makes the missing cookie banner correct.

	Not a legal argument -- a fact about the program, which is what the legal
	argument rests on. Consent is needed for storage that is not strictly
	necessary; if nothing is stored, the question does not arise.
	"""

	def pages(self):
		return ['/', '/tables', '/tags', '/help', '/privacy',
		        '/impressum', '/advanced-search']

	def test_no_page_sets_a_cookie_for_a_reader(self):
		for path in self.pages():
			with self.subTest(page=path):
				self.client.cookies.clear()
				answer = self.client.get(path)
				self.assertEqual(
					sorted(answer.cookies.keys()), [],
					'%s set %s' % (path, list(answer.cookies.keys())))

	def test_searching_sets_none_either(self):
		self.client.cookies.clear()
		answer = self.client.get('/?q=3.14159')
		self.assertEqual(sorted(answer.cookies.keys()), [])

	def test_the_sign_in_page_sets_only_the_csrf_cookie(self):
		"""It has a form, and a form without this is a form that gets
		submitted by other websites."""
		self.client.cookies.clear()
		answer = self.client.get('/accounts/login/')
		self.assertEqual(sorted(answer.cookies.keys()), ['csrftoken'])

	def test_signing_in_sets_only_the_session_cookie(self):
		from django.contrib.auth.models import User

		User.objects.create_user('cookie_user', password='pw-123456')
		self.client.cookies.clear()
		self.client.login(username='cookie_user', password='pw-123456')
		answer = self.client.get('/')
		unexpected = set(answer.cookies.keys()) - {'sessionid', 'csrftoken',
		                                           'messages'}
		self.assertEqual(unexpected, set())

	def test_the_policy_names_exactly_the_cookies_that_exist(self):
		"""If a fourth is ever added, this is what says so."""
		body = self.client.get('/privacy').content.decode()
		for name in ('csrftoken', 'sessionid', 'messages'):
			self.assertIn(name, body)


class DeletingAnAccount(TestCase):

	def setUp(self):
		from django.contrib.auth.models import User

		from .editing import create_table

		self.user = User.objects.create_user('leaving_user',
		                                     email='leaving@example.org',
		                                     password='pw-123456')
		self.table = create_table(
			{'Title': 'Departure probe',
			 'Data properties': {'type': 'R'},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '3.11'}]},
			author=self.user,
		via='orm')
		self.client.login(username='leaving_user', password='pw-123456')

	def delete(self):
		return self.client.post('/profile/delete',
		                        {'confirm': 'leaving_user'}, follow=True)

	def test_the_account_is_gone(self):
		from django.contrib.auth.models import User

		self.delete()
		self.assertFalse(User.objects.filter(username='leaving_user').exists())

	def test_the_edits_survive(self):
		"""They are the provenance of numbers other people cite. Removing them
		would silently rewrite published mathematics."""
		from .models import TableRevision

		before = TableRevision.objects.filter(table=self.table).count()
		self.delete()
		self.assertEqual(TableRevision.objects.filter(table=self.table).count(),
		                 before)

	def test_and_are_reattributed_rather_than_left_unowned(self):
		from .account_data import TOMBSTONE_NAME
		from .models import TableRevision

		self.delete()
		revision = TableRevision.objects.filter(table=self.table).first()
		self.assertIsNotNone(revision.author)
		self.assertEqual(revision.author.username, TOMBSTONE_NAME)

	def test_the_table_still_reads(self):
		"""A history page that 500s because its author is missing is a
		deletion that broke the site for everyone else."""
		self.delete()
		self.assertEqual(self.client.get('/%s' % (self.table.tid,)).status_code,
		                 200)
		self.assertEqual(
			self.client.get('/history/%s' % (self.table.tid,)).status_code, 200)

	def test_the_keys_are_destroyed(self):
		from .models import ApiKey

		key, token = ApiKey.issue(self.user, label='leaving laptop')
		self.delete()
		self.assertIsNone(ApiKey.authenticate(token))
		self.assertFalse(ApiKey.objects.filter(pk=key.pk).exists())

	def test_the_placeholder_cannot_be_signed_into(self):
		from django.contrib.auth.models import User

		from .account_data import TOMBSTONE_NAME

		self.delete()
		keeper = User.objects.get(username=TOMBSTONE_NAME)
		self.assertFalse(keeper.has_usable_password())
		self.assertFalse(keeper.is_active)

	def test_it_needs_the_username_typed(self):
		"""One click away from irreversible is too close."""
		from django.contrib.auth.models import User

		self.client.post('/profile/delete', {'confirm': 'something else'})
		self.assertTrue(User.objects.filter(username='leaving_user').exists())

	def test_a_get_deletes_nothing(self):
		from django.contrib.auth.models import User

		self.client.get('/profile/delete')
		self.assertTrue(User.objects.filter(username='leaving_user').exists())

	def test_one_account_cannot_delete_another(self):
		from django.contrib.auth.models import User

		User.objects.create_user('bystander', password='pw-123456')
		self.client.post('/profile/delete', {'confirm': 'bystander'})
		self.assertTrue(User.objects.filter(username='bystander').exists())


class ExportingAnAccount(TestCase):

	def setUp(self):
		from django.contrib.auth.models import User

		from .editing import create_table

		self.user = User.objects.create_user('exporting_user',
		                                     email='export@example.org',
		                                     password='pw-123456')
		create_table(
			{'Title': 'Export probe',
			 'Data properties': {'type': 'R'},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '3.11'}]},
			author=self.user,
		via='orm')
		self.client.login(username='exporting_user', password='pw-123456')

	def export(self):
		import json

		answer = self.client.get('/profile/export')
		self.assertEqual(answer.status_code, 200)
		return answer, json.loads(answer.content.decode())

	def test_it_gives_back_the_account(self):
		_answer, data = self.export()
		self.assertEqual(data['account']['username'], 'exporting_user')
		self.assertEqual(data['account']['email'], 'export@example.org')

	def test_it_includes_what_they_published(self):
		_answer, data = self.export()
		self.assertTrue(data['edits'])
		self.assertIn('revision', data['edits'][0])

	def test_it_arrives_as_a_file(self):
		answer, _data = self.export()
		self.assertIn('attachment', answer['Content-Disposition'])

	def test_it_carries_no_credential(self):
		"""An export is downloaded, emailed and left in folders. A password
		hash or an API token in it is a credential in all three places."""
		from .models import ApiKey

		_key, token = ApiKey.issue(self.user, label='laptop')
		answer, data = self.export()
		blob = answer.content.decode()

		self.assertNotIn(token, blob)
		self.assertNotIn(self.user.password, blob)
		self.assertNotIn('password', blob.lower())
		#The key is listed, so its owner can see it exists -- by its label and
		#its visible prefix only.
		self.assertEqual(data['api_keys'][0]['label'], 'laptop')

	def test_it_needs_a_login(self):
		self.client.logout()
		answer = self.client.get('/profile/export')
		self.assertEqual(answer.status_code, 302)
		self.assertIn('login', answer['Location'])


class ThePlaceholderNameIsReserved(TestCase):
	"""It is found by username, so a person who could register it would
	inherit every departed contributor's revisions -- and the history would
	credit them with edits they had never seen."""

	def test_it_cannot_be_registered(self):
		from django.contrib.auth.models import User

		answer = self.client.post('/accounts/signup/', {
			'username': 'deleted-user',
			'email': 'someone@example.org',
			'password1': 'a-long-enough-password-1',
			'password2': 'a-long-enough-password-1'})
		self.assertFalse(User.objects.filter(username='deleted-user').exists())
		self.assertEqual(answer.status_code, 200)   # the form came back

	def test_the_settings_say_so(self):
		from django.conf import settings

		from .account_data import TOMBSTONE_NAME

		self.assertIn(TOMBSTONE_NAME,
		              getattr(settings, 'ACCOUNT_USERNAME_BLACKLIST', []))

	def test_a_real_account_under_that_name_is_refused_rather_than_adopted(self):
		from django.contrib.auth.models import User

		from .account_data import TOMBSTONE_NAME, tombstone

		User.objects.create_user(TOMBSTONE_NAME, password='pw-123456')
		with self.assertRaises(ValueError):
			tombstone()


class TheAboutPageWasFoldedIntoHelp(TestCase):
	"""It duplicated the help page's Welcome and Acknowledgements, in stale
	copies whose example links had 404'd since tables were renumbered to
	T-ids. Its only unique content was the roadmap, which moved."""

	def test_about_still_resolves_rather_than_404ing(self):
		"""It was linked to for years, including from other sites."""
		answer = self.client.get('/about')
		self.assertEqual(answer.status_code, 302)
		self.assertIn('help', answer['Location'])

	def test_the_roadmap_landed_on_the_help_page(self):
		body = self.client.get('/help').content.decode()
		self.assertIn('id="section-work-in-progress"', body)
		self.assertIn('Work in progress', body)

	def test_the_beta_link_leads_there(self):
		"""The superscript beta on the front page pointed at the old page's
		roadmap, which is the one link that would have died quietly."""
		for path in ('/', '/advanced-search'):
			with self.subTest(page=path):
				body = self.client.get(path).content.decode()
				self.assertIn('/help#section-work-in-progress', body)

	def test_the_help_page_does_not_credit_what_was_removed(self):
		"""Pyro5 went when the sandboxed evaluator replaced it; the credit
		stayed behind."""
		body = self.client.get('/help').content.decode()
		self.assertNotIn('Pyro5', body)

	def test_the_example_tables_it_used_to_link_to_resolve(self):
		"""The old page pointed at /C1, /C2 and /C9. Help says T1, T2, T9."""
		body = self.client.get('/help').content.decode()
		self.assertNotIn('"/C1"', body)
		self.assertIn('/T1', body)


class TheFooter(TestCase):
	"""What the footer must carry, what it must not repeat, and the one
	structural fact the stylesheet depends on."""

	def body_children(self):
		import re

		html = self.client.get('/impressum').content.decode()
		body = html.split('<body', 1)[1].split('>', 1)[1]
		children, depth = [], 0
		for match in re.finditer(r'<(/?)div\b([^>]*)>', body):
			closing, attrs = match.groups()
			if closing:
				depth -= 1
			else:
				if depth == 0:
					found = re.search(r'class="([^"]*)"', attrs)
					children.append(found.group(1) if found else '')
				depth += 1
		return children

	def test_it_is_the_last_child_of_body(self):
		"""`margin-top: auto` only takes the slack if the footer is a flex item
		of <body>. Wrapped in one more div and it silently stops working, on
		short pages only, which is where nobody looks."""
		self.assertEqual(self.body_children()[-1], 'site-footer')

	def footer(self):
		return self.client.get('/').content.decode().split('site-footer', 1)[1]

	def test_its_links_are_styled_as_the_navigation_is(self):
		"""Same class, not a copy of the rules, so the two cannot drift."""
		footer = self.footer()
		self.assertIn('class="navbar-field" href="/privacy"', footer)
		self.assertIn('class="navbar-field" href="/impressum"', footer)

	def test_it_points_at_the_published_package(self):
		"""The one way to use the data that neither the navigation nor any
		page of the site leads to."""
		self.assertIn('pypi.org/project/numberdb', self.footer())

	def test_it_does_not_repeat_the_navigation(self):
		"""Help is at the top of every page. A footer that echoes the header
		is a footer people stop reading."""
		self.assertNotIn('>Help<', self.footer())
