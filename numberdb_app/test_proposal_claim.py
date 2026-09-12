"""Creating a draft is how a campaign claims a proposal.

Two campaigns run in separate worktrees and cannot see each other's
`generators/` directory, so "no generator answers this yet" cannot tell them
apart -- both would build the same table and one of the two builds, hours of
Sage and model spend, would be thrown away.

The database can tell them apart: `Table.title` is unique, so the first
creation wins and the second is refused, whichever order they arrive in. This
pins that, because the whole scheme rests on it.
"""

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from .editing import make_table
from .models import Table


def a_draft(title):
	return {'Title': title, 'Numbers': {}}


class ATitleCanOnlyBeClaimedOnce(TestCase):

	def setUp(self):
		self.first = get_user_model().objects.create_user('campaign-one')
		self.second = get_user_model().objects.create_user('campaign-two')

	def claim(self, user, title):
		return make_table(a_draft(title), author=user, via='api',
		                  published=False, message='claiming')

	def test_the_first_campaign_gets_it(self):
		table = self.claim(self.first, 'Values of the Airy function')
		self.assertFalse(table.published)
		self.assertEqual(table.title, 'Values of the Airy function')

	def test_the_second_is_refused_and_told_which_table_took_it(self):
		taken = self.claim(self.first, 'Values of the Airy function')
		with self.assertRaises(ValueError) as caught:
			self.claim(self.second, 'Values of the Airy function')
		#The refusal has to name it, or the second campaign cannot report
		#what happened or check whether the other build is real.
		self.assertIn(taken.tid, str(caught.exception))

	def test_the_database_refuses_it_even_without_the_check(self):
		#The check in make_table is for the message. This is what actually
		#closes the race between two campaigns creating at the same moment.
		self.claim(self.first, 'Values of the Airy function')
		with self.assertRaises(IntegrityError):
			with transaction.atomic():
				Table.objects.create(
					tid='T9001', tid_int=9001, url='some_other_slug',
					title='Values of the Airy function',
					title_lowercase='values of the airy function',
					number_count=0, published=False)

	def test_a_different_title_is_not_blocked(self):
		self.claim(self.first, 'Values of the Airy function')
		other = self.claim(self.second,
		                   'Values of the derivative of the Airy function')
		self.assertTrue(Table.objects.filter(pk=other.pk).exists())

	def test_claiming_leaves_a_draft_with_no_numbers(self):
		#The claim must cost nothing but the prose revision, or builders will
		#skip it to keep a table's history short.
		table = self.claim(self.first, 'Values of the Airy function')
		self.assertEqual(table.number_count, 0)
		self.assertEqual(table.revisions.count(), 1)
