"""An account that is a program: what it may do, and what vouching for it means."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from .models import Table, TableRevision, UserProfile
from .permissions import (TRUSTED_GROUP, accepted_edit_count, board_group,
                          is_trusted, may_create_drafts_through_api,
                          may_create_tables_through_api, operator_of,
                          may_write_through_api)

User = get_user_model()


class AnOperatedAccountCannotLaunderItsEditsThroughItsOperator(TestCase):
	"""The counter refuses an assistant's revision that its own author
	confirmed. Giving the assistant its own username used to get round that,
	because author and reviewer were then two names for one judgement."""

	def setUp(self):
		self.operator = User.objects.create_user('operator')
		self.bot = User.objects.create_user('bot')
		self.bot.profile.operated_by = self.operator
		self.bot.profile.save()

	def reviewed_table(self, author, produced_by, reviewed_by):
		table = Table.objects.create(
			tid='T900', tid_int=900, url='t900', title='A table',
			published=True)
		revision = TableRevision.objects.create(
			table=table, author=author, content='Title: A table\n',
			produced_by=produced_by)
		table.reviewed_at_revision = revision
		table.reviewed_by = reviewed_by
		table.save()
		return table

	def test_the_operator_confirming_the_bot_does_not_count(self):
		self.reviewed_table(self.bot, 'assisted by Claude', self.operator)
		self.assertEqual(accepted_edit_count(self.bot), 0)

	def test_somebody_else_confirming_the_bot_does_count(self):
		stranger = User.objects.create_user('stranger')
		self.reviewed_table(self.bot, 'assisted by Claude', stranger)
		self.assertEqual(accepted_edit_count(self.bot), 1)

	def test_an_unassisted_revision_still_counts(self):
		#The exclusion is about assisted work, not about operated accounts.
		self.reviewed_table(self.bot, '', self.operator)
		self.assertEqual(accepted_edit_count(self.bot), 1)

	def test_an_account_with_no_operator_is_unaffected(self):
		plain = User.objects.create_user('plain')
		stranger = User.objects.create_user('stranger2')
		self.assertIsNone(operator_of(plain))
		self.reviewed_table(plain, 'assisted by Claude', stranger)
		self.assertEqual(accepted_edit_count(plain), 1)


class VouchingForAnAccountGrantsWritingAndNothingElse(TestCase):
	"""What the trusted group is for, and what it deliberately is not."""

	def setUp(self):
		self.bot = User.objects.create_user('bot2')
		self.bot.groups.add(Group.objects.get_or_create(name=TRUSTED_GROUP)[0])

	def test_it_may_write_through_the_api(self):
		self.assertTrue(is_trusted(self.bot))
		self.assertTrue(may_write_through_api(self.bot))

	def test_it_may_create_drafts(self):
		self.assertTrue(may_create_drafts_through_api(self.bot))

	def test_it_may_not_create_published_tables(self):
		#Publishing stays a person's act. This is the line that makes
		#vouching for a program a reasonable thing to do.
		self.assertFalse(may_create_tables_through_api(self.bot))

	def test_it_may_not_review(self):
		from .permissions import is_board_member
		self.assertFalse(is_board_member(self.bot))

	def test_its_edits_are_not_reviewed_on_save(self):
		from .permissions import edits_are_reviewed
		self.assertFalse(edits_are_reviewed(self.bot))

	def test_a_board_member_is_still_trusted_without_the_group(self):
		person = User.objects.create_user('boardie')
		person.groups.add(board_group())
		self.assertTrue(is_trusted(person))

	def test_vouching_does_not_exempt_it_from_review(self):
		#The whole point of letting it write is that somebody reads what it
		#wrote. This was `is_trusted` once, and vouching for the bot in order
		#to let it write would have marked everything it wrote reviewed.
		from .permissions import edits_are_reviewed, is_vouched_for
		self.assertTrue(is_vouched_for(self.bot))
		self.assertFalse(edits_are_reviewed(self.bot))

	def test_a_track_record_still_exempts(self):
		from .permissions import edits_are_reviewed
		person = User.objects.create_user('veteran')
		person.groups.add(board_group())
		self.assertTrue(edits_are_reviewed(person))
