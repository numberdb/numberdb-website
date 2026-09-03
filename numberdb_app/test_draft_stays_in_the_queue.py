"""A draft edited by a trusted account must not leave the review queue.

The queue lists a table that has entries outstanding, or one that has never
been reviewed at all:

    count = outstanding.get(table.pk, 0)
    whole = table.reviewed_at_revision_id is None
    if not count and not whole:
        continue

A draft marked reviewed up to its head is in neither state, so it stops being
listed -- while staying unpublished. Not public, not queued, and nothing says
so. T136 spent a morning like that after a board member repaired it through
the API between the build that made it and the review that would have
published it.

Creating a draft already had this guard (`not wants_draft` in `create_table`).
Writing to one did not, on either of the two paths that write.
"""

import yaml
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .editing import create_table
from .models import ApiKey, Table
from .permissions import BOARD_GROUP


class ADraftKeepsWaitingForItsReview(TestCase):

	def setUp(self):
		self.chair = get_user_model().objects.create_user('queue_chair')
		self.chair.groups.add(Group.objects.get_or_create(name=BOARD_GROUP)[0])
		self.table = create_table(
			{'Title': 'Queue probe', 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '1.1'}]},
			author=self.chair, via='orm')
		self.table.published = False
		self.table.ready_for_review = True
		self.table.reviewed_at_revision = None
		self.table.save()
		_key, self.token = ApiKey.issue(user=self.chair, label='queue')

	def write(self, tree, path=None):
		return Client().post(
			path or ('/api/table/%s' % (self.table.tid,)),
			yaml.dump(tree, sort_keys=False),
			content_type='application/yaml', HTTP_HOST='numberdb.org',
			HTTP_AUTHORIZATION='Bearer %s' % (self.token,))

	def queued(self):
		"""Whether the queue would list it, by the queue's own rule."""
		self.table.refresh_from_db()
		if not self.table.published and not self.table.ready_for_review:
			return False
		from .models import Number
		outstanding = Number.objects.filter(table=self.table,
		                                    reviewed=False).count()
		whole = self.table.reviewed_at_revision_id is None
		return bool(outstanding or whole)

	def test_it_is_queued_to_begin_with(self):
		self.assertTrue(self.queued())

	def test_editing_the_document_does_not_take_it_out(self):
		response = self.write({
			'Title': 'Queue probe', 'Parameters': {'n': {'type': 'Z'}},
			'Numbers': {'1': '1.1'}, 'Definition': 'what it is'})
		self.assertEqual(response.status_code, 200, response.content)
		self.assertTrue(self.queued(),
		                'the draft left the queue and is still unpublished')

	def test_writing_entries_does_not_take_it_out(self):
		response = self.write(
			[{'params': {'n': '2'}, 'number': '2.1'}],
			path='/api/table/%s/entries' % (self.table.tid,))
		self.assertEqual(response.status_code, 200, response.content)
		self.assertTrue(self.queued(),
		                'the draft left the queue and is still unpublished')

	def test_a_draft_is_never_marked_reviewed_by_an_edit(self):
		self.write({'Title': 'Queue probe',
		            'Parameters': {'n': {'type': 'Z'}},
		            'Numbers': {'1': '1.1'}, 'Definition': 'd'})
		self.table.refresh_from_db()
		self.assertIsNone(self.table.reviewed_at_revision_id)
		self.assertIsNone(self.table.reviewed_by_id)


class APublishedTableStillAutoReviews(TestCase):
	"""The guard is about drafts, and must not cost a trusted author theirs."""

	def setUp(self):
		self.chair = get_user_model().objects.create_user('published_chair')
		self.chair.groups.add(Group.objects.get_or_create(name=BOARD_GROUP)[0])
		self.table = create_table(
			{'Title': 'Published probe', 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '1.1'}]},
			author=self.chair, via='orm')
		self.table.published = True
		self.table.save()
		_key, self.token = ApiKey.issue(user=self.chair, label='published')

	def test_an_edit_to_a_published_table_is_reviewed(self):
		response = Client().post(
			'/api/table/%s' % (self.table.tid,),
			yaml.dump({'Title': 'Published probe',
			           'Parameters': {'n': {'type': 'Z'}},
			           'Numbers': {'1': '1.1'}, 'Definition': 'd'},
			          sort_keys=False),
			content_type='application/yaml', HTTP_HOST='numberdb.org',
			HTTP_AUTHORIZATION='Bearer %s' % (self.token,))
		self.assertEqual(response.status_code, 200, response.content)
		self.table.refresh_from_db()
		self.assertEqual(self.table.reviewed_at_revision_id,
		                 self.table.head_revision_id)
		self.assertEqual(self.table.reviewed_by_id, self.chair.pk)
