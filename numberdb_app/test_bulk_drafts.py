"""The draft ceiling is per account, not one number for everybody.

The ceiling bounds a runaway, so it has to be low for an account nobody has
looked at. A campaign reaches it legitimately -- fifteen tables built in a
night, held until they are reviewed together -- and stopping that is the
ceiling working as designed against a workflow somebody chose to run. So a
group raises it for the accounts that run campaigns, and for nobody else.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from .models import Table
from .permissions import (BULK_DRAFTS_IN_FLIGHT, DRAFTS_IN_FLIGHT,
                          board_group, bulk_drafts_group, draft_allowance,
                          draft_ceiling, is_bulk_drafter,
                          may_create_drafts_through_api, trusted_group)


class TheDraftCeilingIsPerAccount(TestCase):

	def setUp(self):
		self.ordinary = User.objects.create_user('ordinary')
		self.builder = User.objects.create_user('builder')
		self.builder.groups.add(bulk_drafts_group())

	def hold(self, user, how_many, published=False):
		for n in range(how_many):
			Table.objects.create(
				tid='T%d' % (9000 + n), tid_int=9000 + n,
				url='t%d' % (9000 + n), title='Draft %d' % (n,),
				published=published, created_by=user)

	def test_an_ordinary_account_keeps_the_ordinary_ceiling(self):
		self.assertFalse(is_bulk_drafter(self.ordinary))
		self.assertEqual(draft_ceiling(self.ordinary), DRAFTS_IN_FLIGHT)

	def test_a_member_gets_the_larger_ceiling(self):
		self.assertTrue(is_bulk_drafter(self.builder))
		self.assertEqual(draft_ceiling(self.builder), BULK_DRAFTS_IN_FLIGHT)
		self.assertGreater(BULK_DRAFTS_IN_FLIGHT, DRAFTS_IN_FLIGHT)

	def test_the_allowance_counts_against_the_larger_ceiling(self):
		self.hold(self.builder, DRAFTS_IN_FLIGHT + 3)
		remaining, held = draft_allowance(self.builder)
		self.assertEqual(held, DRAFTS_IN_FLIGHT + 3)
		self.assertEqual(remaining, BULK_DRAFTS_IN_FLIGHT - held)

	def test_a_member_past_the_ordinary_ceiling_may_still_create(self):
		"""The wall the campaign hit, and the reason for the group."""
		self.hold(self.builder, DRAFTS_IN_FLIGHT)
		self.builder.groups.add(trusted_group())
		self.assertTrue(may_create_drafts_through_api(self.builder))

	def test_the_larger_ceiling_is_still_a_ceiling(self):
		self.hold(self.builder, BULK_DRAFTS_IN_FLIGHT)
		remaining, held = draft_allowance(self.builder)
		self.assertEqual((remaining, held), (0, BULK_DRAFTS_IN_FLIGHT))

	def test_published_tables_do_not_count(self):
		self.hold(self.builder, 4, published=True)
		remaining, held = draft_allowance(self.builder)
		self.assertEqual(held, 0)
		self.assertEqual(remaining, BULK_DRAFTS_IN_FLIGHT)

	def test_the_board_is_still_uncapped(self):
		self.ordinary.groups.add(board_group())
		remaining, _held = draft_allowance(self.ordinary)
		self.assertIsNone(remaining)

	def test_taking_the_group_away_restores_the_ordinary_ceiling(self):
		self.builder.groups.remove(bulk_drafts_group())
		self.builder = User.objects.get(pk=self.builder.pk)
		self.assertEqual(draft_ceiling(self.builder), DRAFTS_IN_FLIGHT)
