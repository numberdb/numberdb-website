"""Offering a filled draft for review, through the API.

The workflow has three steps -- create the draft, fill it, ask for review --
and the API had routes for two. `X-Draft: ready` offers a table at creation,
which is before anything has been computed into it.
"""

import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase

from .models import ApiKey, Table, TableRevision
from .permissions import TRUSTED_GROUP, board_group

User = get_user_model()

DOCUMENT = 'Title: A draft\nNumbers:\n  "1": "2"\n'


class OfferingADraftForReview(TestCase):

	def setUp(self):
		self.bot = User.objects.create_user('bot')
		self.bot.groups.add(Group.objects.get_or_create(name=TRUSTED_GROUP)[0])
		_, self.token = ApiKey.issue(self.bot, label='test')
		self.client = Client()

	def draft(self, owner=None, content=DOCUMENT, tid='T500', number=500):
		table = Table.objects.create(
			tid=tid, tid_int=number, url=tid.lower(), title='A draft %s' % tid,
			published=False, created_by=owner or self.bot)
		revision = TableRevision.objects.create(
			table=table, author=owner or self.bot, content=content)
		table.head_revision = revision
		table.save()
		return table

	def offer(self, tid, token=None):
		return self.client.post(
			'/api/table/%s/offer' % tid,
			HTTP_AUTHORIZATION='Bearer %s' % (token or self.token))

	def test_it_offers_a_filled_draft(self):
		table = self.draft()
		response = self.offer(table.tid)
		self.assertEqual(response.status_code, 200)
		self.assertTrue(json.loads(response.content)['ready_for_review'])
		table.refresh_from_db()
		self.assertTrue(table.ready_for_review)
		#Offering is not publishing.
		self.assertFalse(table.published)

	def test_it_refuses_a_draft_with_no_numbers(self):
		#An empty table is exactly what the queue should not be shown, which
		#is why the form on the site refuses it too.
		table = self.draft(content='Title: A draft\n')
		response = self.offer(table.tid)
		self.assertEqual(response.status_code, 409)
		table.refresh_from_db()
		self.assertFalse(table.ready_for_review)

	def test_it_refuses_a_published_table(self):
		table = self.draft()
		table.published = True
		table.save()
		self.assertEqual(self.offer(table.tid).status_code, 409)

	def test_somebody_elses_draft_is_not_found_rather_than_forbidden(self):
		#A 403 would confirm the draft exists to an account that may not see it.
		stranger = User.objects.create_user('stranger')
		table = self.draft(owner=stranger)
		self.assertEqual(self.offer(table.tid).status_code, 404)
		table.refresh_from_db()
		self.assertFalse(table.ready_for_review)

	def test_a_board_member_may_offer_a_draft_they_did_not_make(self):
		stranger = User.objects.create_user('stranger2')
		table = self.draft(owner=stranger)
		self.bot.groups.add(board_group())
		self.assertEqual(self.offer(table.tid).status_code, 200)

	def test_it_needs_a_key(self):
		table = self.draft()
		self.assertEqual(self.client.post('/api/table/%s/offer' % table.tid)
		                 .status_code, 401)

	def test_a_bad_key_is_refused(self):
		table = self.draft()
		self.assertEqual(self.offer(table.tid, token='nonsense').status_code, 403)

	def test_it_is_a_post(self):
		table = self.draft()
		response = self.client.get(
			'/api/table/%s/offer' % table.tid,
			HTTP_AUTHORIZATION='Bearer %s' % self.token)
		self.assertEqual(response.status_code, 405)

	def test_an_unknown_table_is_not_found(self):
		self.assertEqual(self.offer('T999').status_code, 404)
