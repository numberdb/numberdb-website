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
		             author=self.chair,
		via='orm')
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
			                   author=self.user, base=base,
		via='orm')
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
		             author=self.user,
		via='orm')
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
		             author=self.chair, base=first,
		via='orm')
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
		             author=self.chair, base=first,
		via='orm')
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
		                   author=self.chair, base=self.table.head_revision,
		via='orm')
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


class EntriesOnly(WriteBase):
	"""The seam numbers.yaml used to be.

	A generator computes values. It has no opinion about the definition, the
	references or the tags, and under the old arrangement it could not touch
	them because it wrote its own file. Sending a whole document throws that
	away silently.
	"""

	def setUp(self):
		super().setUp()
		commit_table(self.table, {
			'Title': 'API probe',
			'Definition': 'A carefully written definition.',
			'Comments': {'comment-1': 'years of prose'},
			'References': {'reference-1': 'CITE{Someone}'},
			'Parameters': {'n': {'type': 'Z'}},
			'Numbers': [{'params': {'n': '1'}, 'number': '3.14'}],
		}, author=self.chair, base=self.table.head_revision,
		via='orm')
		self.table.refresh_from_db()

	def post(self, body, token=None, tid=None):
		kwargs = {'content_type': 'application/yaml'}
		if token:
			kwargs['HTTP_AUTHORIZATION'] = 'Bearer %s' % (token,)
		return self.client.post('/api/table/%s/entries'
		                        % (tid or self.table.tid,), body, **kwargs)

	def entries(self, value='2.71828'):
		return yaml.dump([{'params': {'n': '1'}, 'number': value}],
		                 sort_keys=False)

	def tree(self):
		self.table.refresh_from_db()
		return tree_of(self.table.head_revision)

	def test_the_entries_are_replaced(self):
		r = self.post(self.entries(), token=self.key_for(self.chair))
		self.assertEqual(r.status_code, 200)
		self.assertEqual(self.tree()['Numbers'][0]['number'], '2.71828')

	def test_the_prose_survives(self):
		"""The whole reason this endpoint exists."""
		self.post(self.entries(), token=self.key_for(self.chair))
		tree = self.tree()
		self.assertEqual(tree['Definition'], 'A carefully written definition.')
		self.assertEqual(tree['Comments'], {'comment-1': 'years of prose'})
		self.assertEqual(tree['References'], {'reference-1': 'CITE{Someone}'})
		self.assertEqual(tree['Parameters'], {'n': {'type': 'Z'}})

	def test_a_whole_document_sent_to_write_table_does_not(self):
		"""The contrast, so the difference cannot be lost by accident."""
		body = yaml.dump({'Title': 'API probe',
		                  'Parameters': {'n': {'type': 'Z'}},
		                  'Numbers': [{'params': {'n': '1'},
		                               'number': '2.71828'}]},
		                 sort_keys=False)
		self.send(body, token=self.key_for(self.chair))
		self.assertNotIn('Definition', self.tree())

	def test_an_untrusted_key_may_not_write_entries_either(self):
		r = self.post(self.entries(), token=self.key_for(self.newcomer))
		self.assertEqual(r.status_code, 403)
		self.assertEqual(self.tree()['Numbers'][0]['number'], '3.14')

	def test_no_key_is_refused(self):
		r = self.post(self.entries())
		self.assertEqual(r.status_code, 401)

	def test_the_nested_form_is_accepted_too(self):
		"""Both forms coexist by design, so both may be sent."""
		r = self.post(yaml.dump({'1': '1.61803'}, sort_keys=False),
		              token=self.key_for(self.chair))
		self.assertEqual(r.status_code, 200)

	def test_sending_the_same_entries_changes_nothing(self):
		before = TableRevision.objects.count()
		r = self.post(self.entries('3.14'), token=self.key_for(self.chair))
		self.assertTrue(json.loads(r.content)['unchanged'])
		self.assertEqual(TableRevision.objects.count(), before)

	def test_entries_over_a_limit_are_refused(self):
		body = yaml.dump([{'params': {'n': '1'},
		                   'number': '0.' + '1' * (limits.SOFT_DIGITS + 1)}],
		                 sort_keys=False)
		r = self.post(body, token=self.key_for(self.chair))
		self.assertEqual(r.status_code, 413)
		self.assertEqual(self.tree()['Numbers'][0]['number'], '3.14')

	def test_nonsense_is_refused(self):
		r = self.post('[unclosed', token=self.key_for(self.chair))
		self.assertEqual(r.status_code, 400)

	def test_an_unknown_table_is_a_404(self):
		r = self.post(self.entries(), token=self.key_for(self.chair),
		              tid='T99999')
		self.assertEqual(r.status_code, 404)


class SendingEntriesOneAtATime(WriteBase):
	"""What a generator computing expensive values needs.

	Without it a script must compute everything before sending anything, so a
	crash at entry 900 loses all 900 -- and a revision per entry would be
	unreadable as history and ruinous as storage, since every revision holds
	the whole document.
	"""

	def setUp(self):
		super().setUp()
		commit_table(self.table, {
			'Title': 'API probe',
			'Parameters': {'n': {'type': 'Z'}},
			'Numbers': [{'params': {'n': '1'}, 'number': '1.1'}],
		}, author=self.chair, base=self.table.head_revision,
		via='orm')
		self.table.refresh_from_db()
		self.token = self.key_for(self.chair)

	def send(self, entries, mode='upsert', run='run-1'):
		headers = {'HTTP_AUTHORIZATION': 'Bearer %s' % (self.token,),
		           'HTTP_X_ENTRIES_MODE': mode}
		if run:
			headers['HTTP_X_RUN_ID'] = run
		return self.client.post('/api/table/%s/entries' % (self.table.tid,),
		                        yaml.dump(entries, sort_keys=False),
		                        content_type='application/yaml', **headers)

	def entries(self):
		self.table.refresh_from_db()
		return tree_of(self.table.head_revision)['Numbers']

	def test_one_entry_is_added_without_replacing_the_rest(self):
		self.send([{'params': {'n': '2'}, 'number': '2.2'}])
		self.assertEqual([e['params']['n'] for e in self.entries()], ['1', '2'])

	def test_sending_the_same_identity_updates_it(self):
		self.send([{'params': {'n': '1'}, 'number': '9.9'}])
		self.assertEqual(self.entries()[0]['number'], '9.9')
		self.assertEqual(len(self.entries()), 1)

	def test_the_response_says_what_happened(self):
		body = json.loads(self.send(
			[{'params': {'n': '2'}, 'number': '2.2'},
			 {'params': {'n': '1'}, 'number': '1.9'}]).content)
		self.assertEqual(body['added'], 1)
		self.assertEqual(body['updated'], 1)

	def test_a_run_grows_one_revision_rather_than_adding_many(self):
		"""A thousand entries would otherwise be a thousand whole documents."""
		before = TableRevision.objects.filter(table=self.table).count()
		for n in range(2, 8):
			self.send([{'params': {'n': str(n)}, 'number': '%d.1' % (n,)}])
		after = TableRevision.objects.filter(table=self.table).count()
		self.assertEqual(after - before, 1)
		self.assertEqual(len(self.entries()), 7)

	def test_a_different_run_starts_a_new_revision(self):
		self.send([{'params': {'n': '2'}, 'number': '2.2'}], run='run-1')
		before = TableRevision.objects.filter(table=self.table).count()
		self.send([{'params': {'n': '3'}, 'number': '3.3'}], run='run-2')
		self.assertEqual(
			TableRevision.objects.filter(table=self.table).count(), before + 1)

	def test_without_a_run_every_submission_is_its_own_revision(self):
		before = TableRevision.objects.filter(table=self.table).count()
		self.send([{'params': {'n': '2'}, 'number': '2.2'}], run='')
		self.send([{'params': {'n': '3'}, 'number': '3.3'}], run='')
		self.assertEqual(
			TableRevision.objects.filter(table=self.table).count(), before + 2)

	def test_replace_is_still_the_default(self):
		"""Upsert and replace are each wrong as a default for the other."""
		self.send([{'params': {'n': '5'}, 'number': '5.5'}], mode='replace')
		self.assertEqual([e['params']['n'] for e in self.entries()], ['5'])

	def test_what_was_sent_earlier_in_a_run_survives_a_later_failure(self):
		"""The crash-safety this exists for."""
		self.send([{'params': {'n': '2'}, 'number': '2.2'}])
		self.send([{'params': {'n': '3'}, 'number': 'not a number'}])
		self.assertEqual([e['params']['n'] for e in self.entries()], ['1', '2'])


class ClaimingATableForARun(WriteBase):
	"""A lease covers the run; the write lock covers one write.

	Without it two generators on one table interleave, neither can amend its
	own revision, and a thousand entries each becomes two thousand revisions of
	the whole document. With it, the second generator is told in its first
	second rather than discovering the collision by colliding.
	"""

	def setUp(self):
		super().setUp()
		self.other = User.objects.create_user('api_other')
		self.other.groups.add(Group.objects.get_or_create(name=BOARD_GROUP)[0])
		self.mine = self.key_for(self.chair)
		self.theirs = self.key_for(self.other)

	def lease(self, token, method='post', run='run-1', note=''):
		headers = {'HTTP_AUTHORIZATION': 'Bearer %s' % (token,)}
		if run:
			headers['HTTP_X_RUN_ID'] = run
		if note:
			headers['HTTP_X_LEASE_NOTE'] = note
		return getattr(self.client, method)(
			'/api/table/%s/lease' % (self.table.tid,), '',
			content_type='application/yaml', **headers)

	def write(self, token, number='2.2', run='run-1'):
		headers = {'HTTP_AUTHORIZATION': 'Bearer %s' % (token,),
		           'HTTP_X_ENTRIES_MODE': 'upsert'}
		if run:
			headers['HTTP_X_RUN_ID'] = run
		return self.client.post(
			'/api/table/%s/entries' % (self.table.tid,),
			yaml.dump([{'params': {}, 'number': number}], sort_keys=False),
			content_type='application/yaml', **headers)

	def test_a_lease_can_be_taken(self):
		response = self.lease(self.mine)
		self.assertEqual(response.status_code, 200)
		self.assertTrue(json.loads(response.content)['held'])

	def test_somebody_else_is_refused_and_told_who_holds_it(self):
		self.lease(self.mine, note='regenerating to 200 digits')
		response = self.lease(self.theirs, run='run-2')
		self.assertEqual(response.status_code, 409)
		body = json.loads(response.content)
		self.assertIn('api_chair', body['detail'])
		self.assertIn('regenerating to 200 digits', body['detail'])

	def test_a_held_table_refuses_another_run_s_writes(self):
		"""The point: found out at once, not after hours of computing."""
		self.lease(self.mine)
		response = self.write(self.theirs, run='run-2')
		self.assertEqual(response.status_code, 409)

	def test_the_holder_may_still_write(self):
		self.lease(self.mine)
		self.assertEqual(self.write(self.mine).status_code, 200)

	def test_the_run_may_write_whoever_sends_it(self):
		"""A run is the unit, so a resumed run keeps its claim."""
		self.lease(self.mine, run='run-1')
		self.assertEqual(self.write(self.theirs, run='run-1').status_code, 200)

	def test_dropping_it_lets_the_next_run_in(self):
		self.lease(self.mine)
		self.lease(self.mine, method='delete')
		self.assertEqual(self.lease(self.theirs, run='run-2').status_code, 200)

	def test_an_expired_lease_is_not_a_locked_table(self):
		"""A generator that dies must not hold a table for good."""
		from datetime import timedelta

		from django.utils import timezone

		from .models import TableLease

		self.lease(self.mine)
		TableLease.objects.filter(table=self.table).update(
			expires=timezone.now() - timedelta(minutes=1))
		self.assertEqual(self.lease(self.theirs, run='run-2').status_code, 200)

	def test_a_submission_pushes_the_expiry_out(self):
		"""So a run whose entries are quicker than the lease needs no heartbeat."""
		from datetime import timedelta

		from django.utils import timezone

		from .models import TableLease

		self.lease(self.mine)
		TableLease.objects.filter(table=self.table).update(
			expires=timezone.now() + timedelta(minutes=1))
		self.write(self.mine)
		lease = TableLease.objects.get(table=self.table)
		self.assertGreater(lease.expires, timezone.now() + timedelta(minutes=5))

	def test_a_person_editing_on_the_site_is_never_refused(self):
		"""A generator's claim is against other generators."""
		from .editing import commit_table

		self.lease(self.mine)
		outcome = commit_table(
			self.table, {'Title': 'API probe', 'Numbers': [
				{'params': {}, 'number': '7.7'}]},
			author=self.newcomer, base=self.table.head_revision,
		via='orm')
		self.assertIsNotNone(outcome.revision)


class AttachingTheCodeThatProducedTheNumbers(WriteBase):
	"""A program could send its results but not itself.

	So generate.sage was put in the repository by hand and drifted from
	whatever had actually run. Carrying the same run puts the code on the same
	revision as the entries, so somebody looking at where a number came from
	finds the code that made it.
	"""

	def setUp(self):
		super().setUp()
		self.token = self.key_for(self.chair)

	def send_file(self, name, body, run='run-1'):
		headers = {'HTTP_AUTHORIZATION': 'Bearer %s' % (self.token,)}
		if run:
			headers['HTTP_X_RUN_ID'] = run
		return self.client.post('/api/table/%s/file/%s' % (self.table.tid, name),
		                        body, content_type='text/plain', **headers)

	def send_entries(self, run='run-1'):
		return self.client.post(
			'/api/table/%s/entries' % (self.table.tid,),
			yaml.dump([{'params': {}, 'number': '2.2'}], sort_keys=False),
			content_type='application/yaml',
			HTTP_AUTHORIZATION='Bearer %s' % (self.token,),
			HTTP_X_ENTRIES_MODE='upsert', HTTP_X_RUN_ID=run)

	def test_a_file_can_be_attached(self):
		response = self.send_file('generate.py', 'print(1)\n')
		self.assertEqual(response.status_code, 200)
		self.table.refresh_from_db()
		names = {a.name for a in self.table.head_revision.attachments.all()}
		self.assertIn('generate.py', names)

	def test_it_lands_on_the_same_revision_as_the_entries(self):
		"""The point: the code beside the numbers it produced."""
		self.send_entries()
		self.send_file('generate.py', 'print(1)\n')
		self.table.refresh_from_db()
		revision = self.table.head_revision
		self.assertIn('generate.py',
		              {a.name for a in revision.attachments.all()})
		self.assertEqual(tree_of(revision)['Numbers'][0]['number'], '2.2')

	def test_a_run_attaching_its_source_adds_no_extra_revision(self):
		before = TableRevision.objects.filter(table=self.table).count()
		self.send_entries()
		self.send_file('generate.py', 'print(1)\n')
		self.assertEqual(
			TableRevision.objects.filter(table=self.table).count(), before + 1)

	def test_an_empty_file_is_refused(self):
		self.assertEqual(self.send_file('generate.py', '').status_code, 400)

	def test_a_key_is_required(self):
		response = self.client.post(
			'/api/table/%s/file/generate.py' % (self.table.tid,),
			'print(1)', content_type='text/plain')
		self.assertEqual(response.status_code, 401)

	def test_a_table_held_by_another_run_refuses_it(self):
		other = User.objects.create_user('file_other')
		other.groups.add(Group.objects.get_or_create(name=BOARD_GROUP)[0])
		self.client.post('/api/table/%s/lease' % (self.table.tid,), '',
		                 content_type='application/yaml',
		                 HTTP_AUTHORIZATION='Bearer %s' % (self.key_for(other),),
		                 HTTP_X_RUN_ID='their-run')
		self.assertEqual(self.send_file('generate.py', 'x').status_code, 409)


class WhatMayBeAttached(WriteBase):
	"""A table's files are flat and small.

	Flat so there is one place to look and no question about where a path
	leads; small because a table holds the code that produced its numbers and
	the notes that explain them, and anything larger is a dataset -- and a
	dataset wants to be a table.
	"""

	def setUp(self):
		super().setUp()
		self.token = self.key_for(self.chair)

	def send(self, name, body):
		return self.client.post('/api/table/%s/file/%s' % (self.table.tid, name),
		                        body, content_type='text/plain',
		                        HTTP_AUTHORIZATION='Bearer %s' % (self.token,))

	def test_a_plain_name_is_accepted(self):
		self.assertEqual(self.send('generate.sage', 'x').status_code, 200)

	def test_a_directory_is_refused(self):
		response = self.send('data/values.txt', 'x')
		self.assertEqual(response.status_code, 400)
		self.assertIn('flat', json.loads(response.content)['error'])

	def test_climbing_out_is_refused(self):
		"""Refused by the name check rather than by the router, so the answer
		says what is wrong with the name."""
		response = self.send('..%2Ffoo.txt', 'x')
		self.assertEqual(response.status_code, 400)
		self.assertIn('flat', json.loads(response.content)['error'])

	def test_a_hidden_file_is_refused(self):
		self.assertEqual(self.send('.env', 'x').status_code, 400)

	def test_a_file_over_the_limit_is_refused(self):
		from .api import MAX_ATTACHMENT_BYTES

		response = self.send('big.txt', 'x' * (MAX_ATTACHMENT_BYTES + 1))
		self.assertEqual(response.status_code, 413)

	def test_the_total_is_limited_too(self):
		"""Otherwise a thousand small files do what one large one may not."""
		from .api import MAX_ATTACHMENTS_BYTES

		self.assertGreater(MAX_ATTACHMENTS_BYTES, 0)


class CreatingTablesNeedsMoreThanWriting(TestCase):
	"""Writing numbers to a table is bounded; creating tables is not.

	A loop that means to make three tables and makes three hundred leaves three
	hundred permanent T-numbers, each a title in every listing and a parameter
	order that can never change because citations resolve on it. Reverting a
	table's existence is not something the history model does.
	"""

	def setUp(self):
		from django.contrib.auth.models import User

		from .models import ApiKey

		self.writer = User.objects.create_user('bulk_writer')
		_key, self.writer_token = ApiKey.issue(self.writer)
		self.board = User.objects.create_user('board_writer')
		_key, self.board_token = ApiKey.issue(self.board)

		from .permissions import board_group
		self.board.groups.add(board_group())

	def make(self, token):
		import json

		return self.client.post(
			'/api/tables',
			data=json.dumps({'Title': 'Made by a program',
			                 'Data properties': {'type': 'R'},
			                 'Numbers': [{'params': {}, 'number': '3.14'}]}),
			content_type='application/json',
			HTTP_AUTHORIZATION='Bearer %s' % (self.writer_token
			                                  if token == 'writer'
			                                  else self.board_token,))

	def test_a_board_member_may(self):
		self.assertEqual(self.make('board').status_code, 201)

	def test_somebody_who_may_write_numbers_may_not(self):
		answer = self.make('writer')
		self.assertEqual(answer.status_code, 403)

	def test_the_refusal_says_where_to_do_it_instead(self):
		"""Not just no: the site's form is the answer, and then a program may
		fill the table with numbers."""
		answer = self.make('writer')
		self.assertIn('site', answer.json().get('detail', ''))
