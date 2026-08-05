"""Tests for tables that are not published yet.

A draft keeps the T-number it was given at creation; publishing changes a flag
and nothing else. The alternative -- a draft number that becomes a T-number --
is the one that can go wrong, because a generator carries the identifier of the
table it fills and is written while the table is still being set up.

What is checked here is mostly that a draft is invisible. Half a gate is worse
than none: a table hidden from the listing but answering a search by number is
published in every way that matters.
"""

import yaml
from django.contrib.auth.models import Group, User
from django.test import TestCase

from .editing import (commit_table, create_table, may_see, publish_table,
                      tree_of)
from .models import Table
from .permissions import BOARD_GROUP


class DraftBase(TestCase):

	def setUp(self):
		self.author = User.objects.create_user('drafter', password='pw-123456')
		self.stranger = User.objects.create_user('stranger', password='pw-123456')
		self.chair = User.objects.create_user('draft_chair', password='pw-123456')
		self.chair.groups.add(Group.objects.get_or_create(name=BOARD_GROUP)[0])

	def make_draft(self, title='Unfinished', entries=None):
		return create_table(
			{'Title': title,
			 'Parameters': {'n': {'type': 'R'}},
			 'Numbers': entries if entries is not None else {}},
			author=self.author, published=False)


class MakingOne(DraftBase):

	def test_a_draft_may_be_empty(self):
		"""The one thing a draft is for: a table not finished yet."""
		draft = self.make_draft()
		self.assertFalse(draft.published)

	def test_it_gets_a_real_t_number_straight_away(self):
		"""Not a draft number that later changes into one."""
		draft = self.make_draft()
		self.assertTrue(draft.tid.startswith('T'))
		self.assertGreater(draft.tid_int, 0)

	def test_the_number_does_not_change_on_publication(self):
		"""The whole argument for one identifier: a generator names this."""
		draft = self.make_draft(entries={'1': '3.14'})
		before = draft.tid
		publish_table(draft)
		draft.refresh_from_db()
		self.assertEqual(draft.tid, before)
		self.assertTrue(draft.published)

	def test_a_public_table_still_needs_an_entry(self):
		with self.assertRaises(ValueError):
			create_table({'Title': 'Empty and public', 'Numbers': {}},
			             author=self.author)

	def test_publishing_an_empty_draft_is_refused(self):
		draft = self.make_draft()
		with self.assertRaises(ValueError) as raised:
			publish_table(draft)
		self.assertIn('nothing to publish', str(raised.exception))

	def test_the_author_is_recorded(self):
		self.assertEqual(self.make_draft().created_by_id, self.author.pk)


class WhoMaySeeIt(DraftBase):

	def test_its_author_may(self):
		self.assertTrue(may_see(self.make_draft(), self.author))

	def test_a_stranger_may_not(self):
		self.assertFalse(may_see(self.make_draft(), self.stranger))

	def test_a_signed_out_reader_may_not(self):
		from django.contrib.auth.models import AnonymousUser

		self.assertFalse(may_see(self.make_draft(), AnonymousUser()))

	def test_the_board_may(self):
		"""Somebody has to be able to find one that was abandoned."""
		self.assertTrue(may_see(self.make_draft(), self.chair))

	def test_everybody_may_see_a_published_table(self):
		from django.contrib.auth.models import AnonymousUser

		draft = self.make_draft(entries={'1': '3.14'})
		publish_table(draft)
		self.assertTrue(may_see(draft, AnonymousUser()))


class ADraftIsNotOnTheSite(DraftBase):

	def setUp(self):
		super().setUp()
		self.draft = self.make_draft(title='Secret work',
		                             entries={'1': '3.14159265358979323846'})

	def test_its_page_is_not_found_for_a_stranger(self):
		"""Not forbidden: saying "you may not" confirms it exists."""
		self.client.login(username='stranger', password='pw-123456')
		self.assertEqual(self.client.get('/%s' % (self.draft.url,)).status_code,
		                 404)
		self.assertEqual(self.client.get('/%s' % (self.draft.tid,)).status_code,
		                 404)

	def test_its_author_can_open_it(self):
		self.client.login(username='drafter', password='pw-123456')
		self.assertEqual(self.client.get('/%s' % (self.draft.url,)).status_code,
		                 200)

	def test_it_is_absent_from_the_tables_listing(self):
		self.assertNotContains(self.client.get('/tables'), 'Secret work')

	def test_the_api_does_not_return_it(self):
		response = self.client.get('/api/table?id=%s' % (self.draft.tid,))
		self.assertIn('does not exist', response.content.decode('utf8'))

	def test_publishing_puts_it_on_the_listing(self):
		publish_table(self.draft)
		self.assertContains(self.client.get('/tables'), 'Secret work')


class ADraftDoesNotAnswerASearch(DraftBase):
	"""Half a gate is worse than none.

	A table hidden from the listing that still answers a search by number is
	published in every way that matters to somebody looking for a value.
	"""

	def setUp(self):
		super().setUp()
		self.draft = self.make_draft(
			title='Hidden constant', entries={'1': '5.55555555555555555555'})
		self.draft.refresh_from_db()
		#As if a reviewer had confirmed it, which is the state that would
		#otherwise let it through the review gate.
		self.draft.reviewed_at_revision = self.draft.head_revision
		self.draft.save(update_fields=['reviewed_at_revision'])
		from .review import sync_review_flags
		sync_review_flags(self.draft)

	def test_its_numbers_are_not_searchable(self):
		from .search import search_by_term

		found = search_by_term('5.55555555555555555555', limit=20)
		tids = {n.table.tid for group in found.values() for n in group} \
			if isinstance(found, dict) else set()
		self.assertNotIn(self.draft.tid, tids)

	def test_its_title_is_not_searchable(self):
		from .search import search_metadata

		_tags, tables = search_metadata('Hidden constant')
		self.assertNotIn(self.draft.tid, {t.tid for t in tables})

	def test_publishing_makes_the_title_findable(self):
		from .search import search_metadata

		publish_table(self.draft)
		_tags, tables = search_metadata('Hidden constant')
		self.assertIn(self.draft.tid, {t.tid for t in tables})
