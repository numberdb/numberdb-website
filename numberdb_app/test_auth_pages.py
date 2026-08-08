"""Tests for the two ways in.

Signing in with a provider was a link, and a link to allauth's provider login
lands on a page whose whole content is a form with a Continue button. That page
is not decoration -- starting an OAuth flow from a GET means any site can send
a visitor into one, and a browser prefetching a link would begin one unasked --
but the protection is the POST and its CSRF token, not the extra click. So the
buttons post, and the interstitial is never reached.
"""

from django.test import TestCase


class WaysIn(TestCase):

	def pages(self):
		return {'sign in': '/accounts/login/',
		        'sign up': '/accounts/signup/'}

	def body(self, url):
		answer = self.client.get(url)
		self.assertEqual(answer.status_code, 200)
		return answer.content.decode()

	#-- the provider ---------------------------------------------------

	def test_both_pages_offer_the_provider(self):
		"""Sign-up offered no provider at all, so the one-click route existed
		for people who already had an account and not for anyone getting one --
		which is backwards."""
		for what, url in self.pages().items():
			with self.subTest(page=what):
				self.assertIn('github/login', self.body(url))

	def test_the_button_posts(self):
		import re

		for what, url in self.pages().items():
			with self.subTest(page=what):
				body = self.body(url)
				form = re.search(
					r'<form[^>]*method="post"[^>]*action="([^"]*github[^"]*)"',
					body)
				self.assertIsNotNone(form, 'no POST form for the provider')

	def test_there_is_no_link_that_would_land_on_the_interstitial(self):
		import re

		for what, url in self.pages().items():
			with self.subTest(page=what):
				body = self.body(url)
				self.assertIsNone(
					re.search(r'<a[^>]*href="[^"]*github/login', body),
					'a GET link to the provider brings back the extra click')

	def test_posting_goes_straight_to_the_provider(self):
		"""Which is what removes the click. If allauth ever stops accepting the
		POST directly, this fails rather than the button quietly returning to
		showing a Continue page."""
		answer = self.client.post('/accounts/github/login/?process=login')
		self.assertEqual(answer.status_code, 302)
		self.assertIn('github.com', answer['Location'])

	def test_a_get_still_shows_the_confirmation(self):
		"""Unchanged, and deliberately so: that page is what protects anyone
		who arrives at the URL from somewhere else."""
		answer = self.client.get('/accounts/github/login/?process=login')
		self.assertEqual(answer.status_code, 200)

	#-- the form -------------------------------------------------------

	def test_the_password_rules_are_available(self):
		"""Not deleted -- they are the answer when a password is refused."""
		self.assertIn('8 characters', self.body('/accounts/signup/'))

	def test_but_they_wait_until_the_field_is_being_used(self):
		"""Four sentences about passwords before a character has been typed
		read as a warning; in the field they are about, they read as help."""
		body = self.body('/accounts/signup/')
		self.assertIn('.form-text { display: none', body)
		self.assertIn(':focus-within .form-text { display: block', body)

	def test_a_rejected_password_shows_them_again(self):
		"""Where the rules are the answer rather than the noise."""
		body = self.body('/accounts/signup/')
		self.assertIn(':has(.is-invalid) .form-text { display: block', body)

	def test_signing_up_with_a_password_still_works(self):
		"""The provider is first on the page; it is not the only way."""
		from django.contrib.auth.models import User

		self.client.post('/accounts/signup/', {
			'username': 'new_person',
			'email': 'new_person@example.org',
			'password1': 'a-long-enough-passphrase',
			'password2': 'a-long-enough-passphrase'})
		self.assertTrue(User.objects.filter(username='new_person').exists())

	def test_each_page_points_at_the_other(self):
		self.assertIn('signup', self.body('/accounts/login/'))
		self.assertIn('login', self.body('/accounts/signup/'))

	def test_a_forgotten_password_is_reachable_from_sign_in(self):
		self.assertIn('password/reset', self.body('/accounts/login/'))
