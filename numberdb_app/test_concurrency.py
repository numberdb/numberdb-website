"""Tests for two writers arriving at once.

Everything else in this suite runs one request at a time, which is exactly the
condition under which a lost update cannot be observed. These use real threads
and real transactions, so they are slower and they are the only ones that can
tell whether the locking works.

The case that matters is a generator sending expensive values one at a time.
Adding entry 2 and entry 3 is not a conflict, and before the lock it was
treated as one: the second submission was refused, and in the variant where a
request merged against one moment and claimed a base from another, the first
entry was simply overwritten.

Checked by taking the lock out again: all three of these fail, and the table
comes back holding ['1', '3'] -- entry 2 accepted with a 200 and gone.
"""

import threading

import yaml
from django.contrib.auth.models import Group, User
from django.db import connections
from django.test import TransactionTestCase

from .editing import create_table, tree_of
from .models import ApiKey, Table, TableRevision
from .permissions import BOARD_GROUP


class TwoWritersAtOnce(TransactionTestCase):

	def setUp(self):
		self.chair = User.objects.create_user('race_chair')
		self.chair.groups.add(Group.objects.get_or_create(name=BOARD_GROUP)[0])
		self.table = create_table(
			{'Title': 'Race probe',
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '1.1'}]},
			author=self.chair,
		via='orm')
		_key, self.token = ApiKey.issue(user=self.chair, label='race')

	def send(self, number, results, run='run-1'):
		"""One submission, from its own thread and its own connection."""
		from django.test import Client

		try:
			response = Client().post(
				'/api/table/%s/entries' % (self.table.tid,),
				yaml.dump([{'params': {'n': str(number)},
				            'number': '%d.1' % (number,)}], sort_keys=False),
				content_type='application/yaml',
				HTTP_AUTHORIZATION='Bearer %s' % (self.token,),
				HTTP_X_ENTRIES_MODE='upsert',
				HTTP_X_RUN_ID=run)
			results.append((number, response.status_code))
		finally:
			#Each thread has its own connection; leaving it open holds the
			#transaction and the next test blocks on it.
			connections.close_all()

	def entries(self):
		self.table.refresh_from_db()
		return [e['params']['n']
		        for e in tree_of(self.table.head_revision)['Numbers']]

	def test_two_entries_sent_at_once_both_survive(self):
		"""The property the lock exists for."""
		results = []
		threads = [threading.Thread(target=self.send, args=(n, results))
		           for n in (2, 3)]
		for thread in threads:
			thread.start()
		for thread in threads:
			thread.join(timeout=30)

		self.assertEqual(sorted(code for _n, code in results), [200, 200])
		self.assertEqual(sorted(self.entries()), ['1', '2', '3'])

	def test_many_at_once_all_survive(self):
		results = []
		threads = [threading.Thread(target=self.send, args=(n, results))
		           for n in range(2, 8)]
		for thread in threads:
			thread.start()
		for thread in threads:
			thread.join(timeout=60)

		#Whatever order they arrived in, none was lost.
		self.assertEqual(sorted(self.entries()),
		                 sorted(str(n) for n in range(1, 8)))

	def test_they_still_land_in_one_revision(self):
		"""Serialising must not turn one run into six revisions."""
		before = TableRevision.objects.filter(table=self.table).count()
		results = []
		threads = [threading.Thread(target=self.send, args=(n, results))
		           for n in range(2, 6)]
		for thread in threads:
			thread.start()
		for thread in threads:
			thread.join(timeout=60)
		after = TableRevision.objects.filter(table=self.table).count()
		self.assertEqual(after - before, 1)
