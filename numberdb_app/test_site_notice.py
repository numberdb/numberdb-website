"""Tests for the banner that says the site is not itself just now.

Written after a deploy drove the load average to ninety and left the site
crawling for eight minutes with nothing anywhere saying why. A visitor cannot
tell "slow because somebody is rebuilding every table" from "slow because it is
broken", and the second reading is the one they leave with.
"""

from django.core.management import call_command
from django.test import TestCase


class TheBanner(TestCase):

	def show(self, message='Rebuilding the tables; searches may be slow.'):
		call_command('notice', 'on', message)

	def hide(self):
		call_command('notice', 'off')

	def page(self):
		return self.client.get('/help').content.decode()

	def test_nothing_shows_by_default(self):
		self.assertNotIn('site-notice', self.page())

	def test_it_shows_when_turned_on(self):
		self.show()
		self.assertIn('Rebuilding the tables', self.page())

	def test_it_goes_away_when_turned_off(self):
		self.show()
		self.hide()
		self.assertNotIn('Rebuilding the tables', self.page())

	def test_it_shows_on_every_page(self):
		"""Including the ones somebody lands on from a search engine."""
		self.show()
		for path in ('/', '/help', '/tables', '/tags'):
			with self.subTest(path=path):
				self.assertIn('site-notice',
				              self.client.get(path).content.decode())

	def test_turning_it_on_twice_leaves_one(self):
		self.show('first')
		self.show('second')
		from .models import SiteNotice
		self.assertEqual(SiteNotice.objects.count(), 1)
		self.assertIn('second', self.page())

	def test_turning_it_on_again_reuses_the_last_words(self):
		"""So the obvious thing to say next time does not have to be retyped."""
		self.show('Rebuilding the tables.')
		self.hide()
		call_command('notice', 'on')
		self.assertIn('Rebuilding the tables.', self.page())

	def test_it_sits_above_the_navigation(self):
		"""A banner below the fold is a banner nobody reads."""
		self.show()
		body = self.page()
		self.assertLess(body.index('site-notice'), body.index('navbar-outer'))

	def test_a_broken_notice_does_not_break_the_page(self):
		"""During the migration that creates it, among other moments -- which
		is exactly when the site can least afford a banner that raises."""
		from unittest import mock

		with mock.patch('numberdb_app.models.SiteNotice.current',
		                side_effect=Exception('no such table')):
			self.assertEqual(self.client.get('/help').status_code, 200)
