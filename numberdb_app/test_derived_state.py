"""Everything derived from a document must agree with it after an edit.

One bug, found by adding a tag: a tag lived in the document and as a Tag row,
and only the document was written. The shape is general -- a table's facts are
stored twice, once in the revision and once in whatever column, row or index
serves a page fast -- and every place that happens is somewhere an edit can be
recorded and invisible.

So this file does not test tags. It tests the invariant: after a commit, every
derived thing matches the document it was derived from. A new derived column
that nobody remembers to update fails here rather than in somebody's face.
"""

from django.test import TestCase


class DerivedStateAgreesWithTheDocument(TestCase):

	def setUp(self):
		from django.contrib.auth.models import User

		from .editing import create_table

		self.user = User.objects.create_user('deriver', password='pw-123456')
		self.table = create_table(
			{'Title': 'Derived probe',
			 'Definition': 'What these numbers are.',
			 'Tags': ['ring', 'analysis'],
			 'Parameters': {'n': {'type': 'Z'}},
			 'Data properties': {'type': 'R'},
			 'Numbers': [{'params': {'n': '1'}, 'number': '3.14'},
			             {'params': {'n': '2'}, 'number': '2.71'}]},
			author=self.user)

	def commit(self, changes):
		from .editing import commit_table, tree_of

		tree = dict(tree_of(self.table.head_revision))
		tree.update(changes)
		commit_table(self.table, tree, author=self.user, message='a change')
		self.table.refresh_from_db()
		return tree

	def document(self):
		from .editing import tree_of

		self.table.refresh_from_db()
		return tree_of(self.table.head_revision)

	#-- the invariants -------------------------------------------------

	def test_the_title_column_matches(self):
		self.commit({'Title': 'Renamed probe'})
		self.assertEqual(self.table.title, 'Renamed probe')
		self.assertEqual(self.table.title_lowercase, 'renamed probe')

	def test_the_tags_match(self):
		self.commit({'Tags': ['analysis', 'geometry']})
		self.assertEqual(sorted(t.name for t in self.table.tags.all()),
		                 ['analysis', 'geometry'])

	def test_the_number_count_matches(self):
		self.commit({'Numbers': [{'params': {'n': str(n)}, 'number': '1.%d' % n}
		                         for n in range(1, 6)]})
		self.assertEqual(self.table.number_count, 5)

	def test_the_stored_document_matches(self):
		"""TableData is what the page renders from; a revision the page does
		not show is an edit that was recorded and is invisible."""
		from .models import TableData

		self.commit({'Definition': 'Something else entirely.'})
		data = TableData.objects.get(table=self.table)
		self.assertIn('Something else entirely', data.full_yaml)

	def test_the_number_rows_match(self):
		from .models import Number

		self.commit({'Numbers': [{'params': {'n': '1'}, 'number': '9.99'}]})
		texts = [n.exact_text for n in Number.objects.filter(table=self.table)]
		self.assertEqual(texts, ['9.99'])

	def test_the_word_index_matches(self):
		"""Renaming a table used to change its page and nothing else."""
		self.commit({'Title': 'Findable by this word'})
		self.table.refresh_from_db()
		self.assertIn('Findable', self.table.search.weight_A_text)

	def test_every_tag_counter_matches(self):
		from django.db.models import Sum

		from .models import Tag

		self.commit({'Tags': ['analysis']})
		for tag in Tag.objects.all():
			with self.subTest(tag=tag.name):
				self.assertEqual(tag.table_count, tag.tables.count())
				self.assertEqual(
					tag.number_count,
					tag.tables.aggregate(t=Sum('number_count'))['t'] or 0)

	def test_a_tag_created_here_is_as_complete_as_one_the_pipeline_built(self):
		"""The test that would have caught the reported bug, stated as what it
		is: a tag made on the site must be a whole tag."""
		from .models import Tag

		self.commit({'Tags': ['ring', 'brand new subject']})
		made = Tag.objects.get(name='brand new subject')
		self.assertTrue(made.name_lowercase)
		self.assertTrue(made.search_vector)
		self.assertEqual(made.table_count, 1)
		self.assertIn(self.table, list(made.tables.all()))
