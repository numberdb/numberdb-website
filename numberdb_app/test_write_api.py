"""Tests for writing tables with a program, and for who is allowed to.

The gate is the point. A person editing a table exercises judgement about that
table; a script exercises none and writes faster than a reviewer can read. So
the tests here are mostly about refusals: no key, an untrusted key, a stale
base, a document over a limit with nothing said about why.
"""

import json

import yaml
from django.contrib.auth.models import Group, User
from django.test import TestCase

from . import limits
from .editing import commit_table, tree_of
from .models import ApiKey, Table, TableRevision
from .permissions import BOARD_GROUP, TRUSTED_AFTER, accepted_edit_count


class WriteBase(TestCase):

	def setUp(self):
		self.table = Table.objects.create(tid='T950', tid_int=950,
		                                  title='API probe', url='API950')
		self.author = User.objects.create_user('api_author')
		self.newcomer = User.objects.create_user('api_newcomer')
		self.chair = User.objects.create_user('api_chair')
		self.chair.groups.add(Group.objects.get_or_create(name=BOARD_GROUP)[0])
		commit_table(self.table, {'Title': 'API probe',
		                          'Numbers': {'1': '3.14'}},
		             author=self.chair)
		self.table.refresh_from_db()

	def key_for(self, user):
		key, token = ApiKey.issue(user=user, label='test')
		return token

	def send(self, body, token=None, tid=None, headers=None, method='post'):
		kwargs = {'content_type': 'application/yaml'}
		if token:
			kwargs['HTTP_AUTHORIZATION'] = 'Bearer %s' % (token,)
		kwargs.update(headers or {})
		url = '/api/table/%s' % (tid or self.table.tid,)
		if method == 'get':
			return self.client.get(url, **kwargs)
		return getattr(self.client, method)(url, body, **kwargs)

	def document(self, value='2.71828'):
		#sort_keys=False, because section order is part of the document: a
		#caller whose serialiser sorts will rewrite the table without having
		#changed a value.
		return yaml.dump({'Title': 'API probe', 'Numbers': {'1': value}},
		                 sort_keys=False)

	def head_numbers(self):
		self.table.refresh_from_db()
		return tree_of(self.table.head_revision)['Numbers']


class Trust(TestCase):

	def setUp(self):
		self.user = User.objects.create_user('trust_probe')
		self.table = Table.objects.create(tid='T951', tid_int=951,
		                                  title='Trust probe', url='Trust951')

	def make_accepted(self, n):
		"""n revisions by the user, all of them reviewed afterwards."""
		base = None
		for i in range(n):
			out = commit_table(self.table,
			                   {'Title': 'Trust probe',
			                    'Numbers': {'1': '3.%d' % (i,)}},
			                   author=self.user, base=base)
			base = out.revision
		self.table.refresh_from_db()
		self.table.reviewed_at_revision = self.table.head_revision
		self.table.save(update_fields=['reviewed_at_revision'])

	def test_a_new_account_has_no_accepted_edits(self):
		self.assertEqual(accepted_edit_count(self.user), 0)

	def test_unreviewed_edits_do_not_count(self):
		"""Otherwise trust is a measure of typing rather than of correctness."""
		commit_table(self.table, {'Title': 'Trust probe',
		                          'Numbers': {'1': '9.9'}},
		             author=self.user)
		self.assertEqual(accepted_edit_count(self.user), 0)

	def test_reviewed_edits_count(self):
		self.make_accepted(3)
		self.assertEqual(accepted_edit_count(self.user), 3)

	def test_trust_arrives_at_the_threshold(self):
		from .permissions import is_trusted

		self.make_accepted(TRUSTED_AFTER - 1)
		self.assertFalse(is_trusted(self.user))
		self.make_accepted(1)
		self.assertTrue(is_trusted(self.user))

	def test_a_board_member_is_trusted_without_a_track_record(self):
		from .permissions import is_trusted

		chair = User.objects.create_user('trust_chair')
		chair.groups.add(Group.objects.get_or_create(name=BOARD_GROUP)[0])
		self.assertTrue(is_trusted(chair))

	def test_anonymous_is_not_trusted(self):
		from django.contrib.auth.models import AnonymousUser

		from .permissions import is_trusted, may_write_through_api

		self.assertFalse(is_trusted(AnonymousUser()))
		self.assertFalse(may_write_through_api(AnonymousUser()))


class WhoMayWrite(WriteBase):

	def test_no_key_is_refused(self):
		r = self.send(self.document())
		self.assertEqual(r.status_code, 401)
		self.assertEqual(self.head_numbers(), {'1': '3.14'})

	def test_a_bad_key_is_refused(self):
		r = self.send(self.document(), token='nb_notarealkey')
		self.assertEqual(r.status_code, 403)

	def test_a_session_alone_does_not_write(self):
		"""A cookie would make every page a logged-in user visits a write."""
		self.client.force_login(self.chair)
		r = self.send(self.document())
		self.assertEqual(r.status_code, 401)
		self.assertEqual(self.head_numbers(), {'1': '3.14'})

	def test_an_untrusted_key_is_refused_and_told_why(self):
		r = self.send(self.document(), token=self.key_for(self.newcomer))
		self.assertEqual(r.status_code, 403)
		body = json.loads(r.content)
		self.assertIn('%d edits' % (TRUSTED_AFTER,), body['detail'])
		self.assertEqual(self.head_numbers(), {'1': '3.14'})

	def test_a_trusted_key_writes(self):
		r = self.send(self.document(), token=self.key_for(self.chair))
		self.assertEqual(r.status_code, 200)
		self.assertEqual(self.head_numbers(), {'1': '2.71828'})

	def test_a_get_does_not_write(self):
		r = self.send(self.document(), token=self.key_for(self.chair),
		              method='get')
		self.assertEqual(r.status_code, 405)


class WhatIsWritten(WriteBase):

	def token(self):
		return self.key_for(self.chair)

	def test_the_revision_is_flagged_as_machine_made(self):
		"""Readers are entitled to know; reviewers triage these differently."""
		self.send(self.document(), token=self.token(),
		          headers={'HTTP_X_PRODUCED_BY': 'tidy-script v2'})
		self.table.refresh_from_db()
		self.assertEqual(self.table.head_revision.produced_by, 'tidy-script v2')

	def test_an_unnamed_program_is_still_flagged(self):
		self.send(self.document(), token=self.token())
		self.table.refresh_from_db()
		self.assertEqual(self.table.head_revision.produced_by, 'api')

	def test_the_identifier_is_not_accepted_from_a_caller(self):
		body = yaml.dump({'Title': 'API probe', 'ID': 'T999',
		                  'Numbers': {'1': '1.5'}})
		self.send(body, token=self.token())
		self.table.refresh_from_db()
		self.assertNotIn('ID', tree_of(self.table.head_revision))
		self.assertEqual(self.table.tid, 'T950')

	def test_writing_the_same_document_changes_nothing(self):
		before = TableRevision.objects.count()
		r = self.send(self.document('3.14'), token=self.token())
		self.assertTrue(json.loads(r.content)['unchanged'])
		self.assertEqual(TableRevision.objects.count(), before)

	def test_json_is_accepted_as_well_as_yaml(self):
		body = json.dumps({'Title': 'API probe', 'Numbers': {'1': '1.61803'}},
		                  sort_keys=False)
		r = self.send(body, token=self.token())
		self.assertEqual(r.status_code, 200)
		self.assertEqual(self.head_numbers(), {'1': '1.61803'})

	def test_nonsense_is_refused_rather_than_stored(self):
		r = self.send('this: [is: not: valid', token=self.token())
		self.assertEqual(r.status_code, 400)

	def test_a_document_without_a_title_is_refused(self):
		r = self.send(yaml.dump({'Numbers': {'1': '1'}}), token=self.token())
		self.assertEqual(r.status_code, 400)

	def test_an_unknown_table_is_a_404(self):
		r = self.send(self.document(), token=self.token(), tid='T99999')
		self.assertEqual(r.status_code, 404)


class ConcurrencyThroughTheApi(WriteBase):

	def test_naming_a_stale_base_is_refused_rather_than_merged_blindly(self):
		first = self.table.head_revision
		commit_table(self.table, {'Title': 'API probe',
		                          'Numbers': {'1': '3.14', '2': '9.9'}},
		             author=self.chair, base=first)
		r = self.send(yaml.dump({'Title': 'API probe',
		                         'Numbers': {'1': '3.14', '2': '8.8'}},
		                        sort_keys=False),
		              token=self.key_for(self.chair),
		              headers={'HTTP_X_BASE_REVISION': first.digest})
		self.assertEqual(r.status_code, 409)
		self.assertIn('conflicts', json.loads(r.content))

	def test_an_unknown_base_is_refused(self):
		r = self.send(self.document(), token=self.key_for(self.chair),
		              headers={'HTTP_X_BASE_REVISION': 'deadbeef'})
		self.assertEqual(r.status_code, 409)

	def test_a_disjoint_edit_from_an_old_base_still_merges(self):
		first = self.table.head_revision
		commit_table(self.table, {'Title': 'API probe',
		                          'Numbers': {'1': '3.14', '2': '9.9'}},
		             author=self.chair, base=first)
		r = self.send(yaml.dump({'Title': 'API probe',
		                         'Numbers': {'1': '7.77'}}, sort_keys=False),
		              token=self.key_for(self.chair),
		              headers={'HTTP_X_BASE_REVISION': first.digest})
		self.assertEqual(r.status_code, 200)
		self.assertTrue(json.loads(r.content)['merged'])
		self.assertEqual(self.head_numbers(), {'1': '7.77', '2': '9.9'})


class LimitsAreEnforcedNotWarned(WriteBase):
	"""A warning shown to nobody is not a limit."""

	def big(self):
		return yaml.dump({
			'Title': 'API probe',
			'Numbers': {'1': '0.' + '1' * (limits.SOFT_DIGITS + 1)}})

	def test_an_unexplained_soft_breach_is_refused(self):
		r = self.send(self.big(), token=self.key_for(self.chair))
		self.assertEqual(r.status_code, 413)
		self.assertEqual(self.head_numbers(), {'1': '3.14'})

	def test_the_same_document_with_a_reason_is_accepted(self):
		body = yaml.dump({
			'Title': 'API probe',
			'Data properties': {
				limits.EXCEPTION_KEY: 'these digits took three CPU-months'},
			'Numbers': {'1': '0.' + '1' * (limits.SOFT_DIGITS + 1)}})
		r = self.send(body, token=self.key_for(self.chair))
		self.assertEqual(r.status_code, 200)

	def test_the_same_edit_made_on_the_site_is_only_warned_about(self):
		"""The asymmetry is deliberate: a person has judgement to exercise."""
		out = commit_table(self.table,
		                   {'Title': 'API probe',
		                    'Numbers': {'1': '0.' + '1' * (limits.SOFT_DIGITS + 1)}},
		                   author=self.chair, base=self.table.head_revision)
		self.assertIsNotNone(out.revision)
		self.assertEqual([b.kind for b in out.breaches], ['digits'])


class CreatingThroughTheApi(WriteBase):

	def create(self, body, token=None):
		kwargs = {'content_type': 'application/yaml'}
		if token:
			kwargs['HTTP_AUTHORIZATION'] = 'Bearer %s' % (token,)
		return self.client.post('/api/tables', body, **kwargs)

	def test_an_untrusted_key_may_not_create(self):
		r = self.create(yaml.dump({'Title': 'Brand new', 'Numbers': {'1': '1'}}),
		                token=self.key_for(self.newcomer))
		self.assertEqual(r.status_code, 403)
		self.assertFalse(Table.objects.filter(title='Brand new').exists())

	def test_a_trusted_key_creates_and_is_told_the_number(self):
		r = self.create(yaml.dump({'Title': 'Brand new', 'Numbers': {'1': '1'}}),
		                token=self.key_for(self.chair))
		self.assertEqual(r.status_code, 201)
		body = json.loads(r.content)
		table = Table.objects.get(title='Brand new')
		self.assertEqual(body['tid'], table.tid)
		self.assertIsNotNone(body['revision'])

	def test_a_duplicate_title_is_refused(self):
		r = self.create(yaml.dump({'Title': 'API probe', 'Numbers': {'1': '1'}}),
		                token=self.key_for(self.chair))
		self.assertEqual(r.status_code, 400)

	def test_a_refused_document_leaves_no_half_made_table(self):
		"""Otherwise a T-number is burnt on a table that never existed."""
		before = Table.objects.count()
		body = yaml.dump({
			'Title': 'Far too big',
			'Numbers': {'1': '0.' + '1' * (limits.HARD_DIGITS + 1)}})
		r = self.create(body, token=self.key_for(self.chair))
		self.assertEqual(r.status_code, 413)
		self.assertEqual(Table.objects.count(), before)
