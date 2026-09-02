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
			author=self.author, published=False,
		via='orm')


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
			             author=self.author,
		via='orm')

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


class ParametersAreSettledWhileDrafting(DraftBase):
	"""The freeze protects citations, and a draft has none.

	Choosing the parameters is most of what setting a table up consists of, so
	refusing to change them before anybody can see the table would make drafts
	nearly useless -- and the protection would be protecting nothing.
	"""

	def setUp(self):
		super().setUp()
		self.draft = create_table(
			{'Title': 'Settling down',
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '3.14'}]},
			author=self.author, published=False,
		via='orm')

	def edit(self, tree):
		return commit_table(self.draft, tree, author=self.author,
		                    base=self.draft.head_revision,
		via='orm')

	def test_a_parameter_may_be_renamed(self):
		self.edit({'Title': 'Settling down',
		           'Parameters': {'m': {'type': 'Z'}},
		           'Numbers': [{'params': {'m': '1'}, 'number': '3.14'}]})
		self.draft.refresh_from_db()
		self.assertEqual(list(tree_of(self.draft.head_revision)['Parameters']),
		                 ['m'])

	def test_a_parameter_may_be_added(self):
		self.edit({'Title': 'Settling down',
		           'Parameters': {'n': {'type': 'Z'}, 'k': {'type': 'Z'}},
		           'Numbers': [{'params': {'n': '1', 'k': '2'},
		                        'number': '3.14'}]})
		self.draft.refresh_from_db()
		self.assertEqual(list(tree_of(self.draft.head_revision)['Parameters']),
		                 ['n', 'k'])

	def test_once_published_the_names_are_fixed(self):
		from .editing import ParametersChanged

		publish_table(self.draft)
		self.draft.refresh_from_db()
		with self.assertRaises(ParametersChanged):
			self.edit({'Title': 'Settling down',
			           'Parameters': {'m': {'type': 'Z'}},
			           'Numbers': [{'params': {'m': '1'}, 'number': '3.14'}]})

	def test_but_constraints_and_type_stay_editable(self):
		"""Neither enters an identity, so neither can move a citation."""
		publish_table(self.draft)
		self.draft.refresh_from_db()
		self.edit({'Title': 'Settling down',
		           'Parameters': {'n': {'type': 'R', 'constraints': '$n > 0$'}},
		           'Numbers': [{'params': {'n': '1'}, 'number': '3.14'}]})
		self.draft.refresh_from_db()
		spec = tree_of(self.draft.head_revision)['Parameters']['n']
		self.assertEqual(spec['type'], 'R')
		self.assertEqual(spec['constraints'], '$n > 0$')


class ADraftsAddressFollowsItsTitle(DraftBase):
	"""The slug of a published table is frozen because links point at it.
	Nobody can have linked to a draft: it is invisible, in no listing, and
	answers no search. So while a table is being set up its address follows its
	title, and freezes at publication when the address starts to matter.
	"""

	def setUp(self):
		super().setUp()
		self.table = create_table(
			{'Title': 'Fibonacci polynomials',
			 'Data properties': {'type': 'Z[]'},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '1'}]},
			author=self.author, published=False,
		via='orm')

	def _retitle(self, title):
		tree = dict(tree_of(self.table.head_revision))
		tree['Title'] = title
		commit_table(self.table, tree, author=self.author,
		             base=self.table.head_revision, message='renamed',
		via='orm')
		self.table.refresh_from_db()

	def test_a_draft_renamed_gets_the_new_address(self):
		self.assertEqual(self.table.url, 'Fibonacci_polynomials')
		self._retitle('Lucas polynomials')
		self.assertEqual(self.table.url, 'Lucas_polynomials')
		self.assertEqual(self.table.title, 'Lucas polynomials')

	def test_the_number_never_moves(self):
		#The whole reason drafts keep their T-number: a generator carries the
		#identifier of the table it fills, written while the table is still
		#being set up.
		before = self.table.tid
		self._retitle('Something else entirely')
		self.assertEqual(self.table.tid, before)

	def test_a_published_table_keeps_its_address(self):
		publish_table(self.table)
		self.table.refresh_from_db()
		self._retitle('Renamed after publication')
		self.assertEqual(self.table.url, 'Fibonacci_polynomials')
		self.assertEqual(self.table.title, 'Renamed after publication')

	def test_a_rename_cannot_take_another_tables_address(self):
		#Two tables cannot share a *title* -- the column is unique, which the
		#first version of this test discovered by violating it. They can still
		#collide on an *address*, because slugification maps several titles
		#onto one: punctuation becomes an underscore.
		create_table(
			{'Title': 'Lucas polynomials!',
			 'Data properties': {'type': 'Z[]'},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '1'}]},
			author=self.author,
		via='orm')
		self._retitle('Lucas polynomials')
		self.assertNotEqual(self.table.url, 'Lucas_polynomials')
		self.assertTrue(self.table.url.startswith('Lucas_polynomials'))

	def test_renaming_twice_does_not_accumulate_suffixes(self):
		#It would, if the table's own address counted as a collision with
		#itself.
		self._retitle('Chebyshev polynomials')
		self._retitle('Chebyshev polynomials')
		self.assertEqual(self.table.url, 'Chebyshev_polynomials')


class TitlesWithMathematicsGetReadableAddresses(DraftBase):
	"""`Chebyshev polynomials of the first kind $T_n$` lives at
	`Chebyshev_polynomials_of_the_first_kind`, and a table created today wrote
	its title the same way and got `Fibonacci_polynomials_F_n`. The slug is
	what people paste into papers."""

	def test_the_latex_is_left_out_of_the_address(self):
		from .editing import slug_for

		self.assertEqual(slug_for('Fibonacci polynomials $F_n$', taken=set()),
		                 'Fibonacci_polynomials')
		self.assertEqual(
			slug_for('Chebyshev polynomials of the first kind $T_n$', taken=set()),
			'Chebyshev_polynomials_of_the_first_kind')

	def test_a_title_that_is_only_mathematics_still_gets_an_address(self):
		from .editing import slug_for

		self.assertTrue(slug_for('$\\pi$', taken=set()))

	def test_a_draft_renamed_takes_the_readable_form(self):
		table = create_table(
			{'Title': 'Working name',
			 'Data properties': {'type': 'Z[]'},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '1'}]},
			author=self.author, published=False,
		via='orm')
		tree = dict(tree_of(table.head_revision))
		tree['Title'] = 'Lucas polynomials $L_n$'
		commit_table(table, tree, author=self.author,
		             base=table.head_revision, message='renamed',
		via='orm')
		table.refresh_from_db()
		self.assertEqual(table.url, 'Lucas_polynomials')
