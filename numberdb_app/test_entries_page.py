"""Tests for editing a table's numbers as rows.

The numbers were the last part of a table that could only be edited as YAML,
and the part a mathematician is most likely to want to touch: one wrong digit.

Nearly everything here is about what a save does to the rows it did **not**
show. A table of a thousand entries is edited two hundred at a time, and a page
that rebuilt the entries from its own fields would delete the other eight
hundred -- silently, from a save that looked like correcting one digit.
"""

from django.test import TestCase


class EntriesPage(TestCase):

	def setUp(self):
		from django.contrib.auth.models import User

		from .editing import create_table

		self.user = User.objects.create_user('entries_user',
		                                     password='pw-123456')
		self.table = create_table(
			{'Title': 'Entries probe',
			 'Definition': 'What these numbers are.',
			 'Data properties': {'type': 'R'},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': str(n)}, 'number': '3.1%d' % (n,)}
			             for n in range(1, 6)]},
			author=self.user)
		self.client.login(username='entries_user', password='pw-123456')

	def url(self, extra=''):
		return '/edit/%s%s' % (self.table.tid, extra)

	def head(self):
		from .editing import tree_of

		self.table.refresh_from_db()
		return tree_of(self.table.head_revision)

	def entries(self):
		return {record['params']['n']: record.get('number')
		        for record in self.head()['Numbers']}

	def fields(self, rows, page=1, covered=None):
		"""What the page would submit for the rows given.

		``covered`` is the identities the page displayed. Everything else in
		the table is left alone, which is what makes paging safe, so a test
		that forgets it is testing a page that showed nothing.
		"""
		if covered is None:
			#A page covers what it showed. Taken from the rows themselves so a
			#test cannot accidentally claim to have displayed entries it never
			#sent -- which reads as "shown and deleted".
			covered = [value for key, value in rows.items()
			           if key.endswith('.was') and value]
		data = {'action': 'save-entries',
		        'entries.present': '1',
		        'page': str(page),
		        'base': self.table.head_revision.digest,
		        'entries.covered': list(covered)}
		data.update(rows)
		return data

	def row(self, index, was, n, number, comment=''):
		return {'entry.%s.was' % (index,): was,
		        'entry.%s.param.n' % (index,): n,
		        'entry.%s.number' % (index,): number,
		        'entry.%s.comment' % (index,): comment,
		        'entry.%s.extra' % (index,): ''}

	#-- the page -------------------------------------------------------

	def test_it_draws_a_row_per_entry(self):
		page = self.client.get(self.url('?form=entries'))
		self.assertEqual(page.status_code, 200)
		body = page.content.decode()
		#Not the blank row in the <template>, which is not an entry.
		self.assertEqual(body.count('name="entry.') - body.count('entry.NEW.'),
		                 5 * 5)
		self.assertIn('entries.present', body)

	def test_every_row_carries_the_identity_it_was_drawn_with(self):
		"""Which is how a save finds it again among rows it never showed."""
		body = self.client.get(self.url('?form=entries')).content.decode()
		for n in range(1, 6):
			self.assertIn('name="entry.%d.was" value="%d"' % (n - 1, n), body)

	def test_it_is_reachable_from_the_other_editors(self):
		for where in ('?form=1', '?form=sections', ''):
			with self.subTest(where=where):
				body = self.client.get(self.url(where)).content.decode()
				self.assertIn('form=entries', body)

	#-- saving ---------------------------------------------------------

	def test_a_changed_number_is_saved(self):
		data = self.fields(self.row(0, '1', '1', '3.14159'))
		self.client.post(self.url(), data)
		self.assertEqual(self.entries()['1'], '3.14159')

	def test_the_rows_the_page_did_not_show_are_left_alone(self):
		"""The whole reason each row carries its identity."""
		data = self.fields(self.row(0, '1', '1', '3.14159'))
		self.client.post(self.url(), data)
		kept = self.entries()
		self.assertEqual(len(kept), 5)
		self.assertEqual(kept['5'], '3.15')

	def test_a_row_left_out_of_the_submission_is_removed(self):
		"""Removing a row means not submitting it, which is what the page's
		remove button does by disabling its fields."""
		rows = {}
		for index, n in enumerate(['1', '2', '4', '5']):
			rows.update(self.row(index, n, n, '3.1%s' % (n,)))
		#The page showed all five and sent four back: the fifth was removed.
		self.client.post(self.url(),
		                 self.fields(rows, covered=['1', '2', '3', '4', '5']))
		self.assertNotIn('3', self.entries())
		self.assertEqual(len(self.entries()), 4)

	def test_a_new_row_is_appended(self):
		rows = {}
		for index, n in enumerate(['1', '2', '3', '4', '5']):
			rows.update(self.row(index, n, n, '3.1%s' % (n,)))
		rows.update(self.row('new1', '', '9', '3.19'))
		self.client.post(self.url(), self.fields(rows))
		self.assertEqual(self.entries()['9'], '3.19')
		self.assertEqual(len(self.entries()), 6)

	def test_two_new_rows_in_one_save_both_survive(self):
		"""They have no identity yet, so both carried the empty string, and
		keying the submission on that made the second overwrite the first."""
		rows = {}
		rows.update(self.row('new1', '', '8', '3.18'))
		rows.update(self.row('new2', '', '9', '3.19'))
		self.client.post(self.url(), self.fields(rows))
		kept = self.entries()
		self.assertEqual(kept.get('8'), '3.18')
		self.assertEqual(kept.get('9'), '3.19')

	def test_a_comment_rides_along(self):
		data = self.fields(self.row(0, '1', '1', '3.11', 'conjectural'))
		self.client.post(self.url(), data)
		record = self.head()['Numbers'][0]
		self.assertEqual(record.get('comment'), 'conjectural')

	def test_a_save_with_no_rows_at_all_changes_nothing(self):
		"""A form that failed to render its rows must not read as "every entry
		was deleted". That is what entries.present is for, and this is the
		case where it earns its keep."""
		data = {'action': 'save-entries', 'page': '1',
		        'base': self.table.head_revision.digest}
		self.client.post(self.url(), data)
		self.assertEqual(len(self.entries()), 5)

	#-- identities -----------------------------------------------------

	def test_a_parameter_may_not_be_retyped_on_a_published_table(self):
		"""Its citations would not break -- they would resolve and point at a
		different number."""
		data = self.fields(self.row(0, '1', '99', '3.11'))
		self.client.post(self.url(), data)
		self.assertIn('1', self.entries())
		self.assertNotIn('99', self.entries())

	def test_the_page_shows_that_by_making_them_read_only(self):
		body = self.client.get(self.url('?form=entries')).content.decode()
		self.assertIn('readonly>', body)

	def test_on_a_draft_a_parameter_may_be_retyped(self):
		from .editing import create_table

		draft = create_table(
			{'Title': 'Draft probe',
			 'Data properties': {'type': 'R'},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '3.11'}]},
			author=self.user, published=False)

		body = self.client.get('/edit/%s?form=entries'
		                       % (draft.tid,)).content.decode()
		#'readonly' also appears in this page's stylesheet, so the attribute
		#is what is looked for and not the word.
		self.assertNotIn('readonly>', body)

		self.client.post('/edit/%s' % (draft.tid,), {
			'action': 'save-entries', 'entries.present': '1', 'page': '1',
			'entries.covered': ['1'],
			'base': draft.head_revision.digest,
			'entry.0.was': '1', 'entry.0.param.n': '7',
			'entry.0.number': '3.11', 'entry.0.comment': '',
			'entry.0.extra': ''})

		from .editing import tree_of
		draft.refresh_from_db()
		stored = tree_of(draft.head_revision)['Numbers']
		self.assertEqual(stored[0]['params']['n'], '7')

	#-- the ordinary path ----------------------------------------------

	def test_a_save_goes_through_the_same_machinery_as_the_source_editor(self):
		"""One way through, so the review rules, the size limits and the stale
		check cannot drift between the two."""
		self.client.post(self.url(),
		                 self.fields(self.row(0, '1', '1', '3.14159')))
		self.table.refresh_from_db()
		self.assertEqual(self.table.head_revision.author, self.user)

	def test_it_returns_to_the_page_that_was_being_edited(self):
		"""On a table of a thousand entries, coming back to page one is the
		difference between an edit and a search."""
		data = self.fields(self.row(0, '1', '1', '3.14159'), page=1)
		data['page'] = '3'
		answer = self.client.post(self.url(), data)
		self.assertEqual(answer.status_code, 302)
		self.assertIn('form=entries', answer['Location'])
		self.assertIn('page=3', answer['Location'])
