"""What made a revision, recorded as a row rather than as a sentence.

The old field held eight spellings of "codex", no version of anything, and a
run identifier that joined to nothing. See docs/design/pipeline-provenance.md.
"""

import os
import tempfile

from django.contrib.auth.models import User
from django.test import Client, TestCase

from .models import AgentRun, Table, TableRevision


def document(title='A table'):
	return {'Title': title, 'Parameters': {'n': {'type': 'Z'}},
	        'Numbers': [{'params': {'n': '1'}, 'number': '2.5'}]}


class TheRunIsARow(TestCase):
	"""`provenance.run_for` on its own, without the HTTP layer."""

	def setUp(self):
		from . import provenance

		self.provenance = provenance
		self.user = User.objects.create_user('zeta3', password='x')

	def request(self, **headers):
		class Fake:
			GET = {}

			def __init__(self, headers):
				self.headers = headers
		return Fake(headers)

	def test_a_request_that_says_nothing_makes_no_run(self):
		#A person at a keyboard, and the absence is the record of one.
		self.assertIsNone(
			self.provenance.run_for(self.request(), self.user))

	def test_a_campaign_stage_is_recorded_whole(self):
		run = self.provenance.run_for(self.request(**{
			'X-Run-Id': '20260918T072306Z',
			'X-Pipeline': 'table-build@2.7+9f3ac1d2',
			'X-Stage': 'build', 'X-Engine': 'codex-cli', 'X-Model': 'gpt-5.5',
			'X-Campaign': '20260918T035359Z'}), self.user)
		self.assertEqual(run.run_id, '20260918T072306Z')
		self.assertEqual(run.pipeline, 'table-build')
		self.assertEqual(run.pipeline_version, '2.7')
		self.assertEqual(run.pipeline_digest, '9f3ac1d2')
		self.assertEqual(run.model, 'gpt-5.5')
		self.assertEqual(run.campaign, '20260918T035359Z')
		#A digest is computed by agents/pipeline.py and by nothing else, so a
		#label carrying one came from a runner that knows what it ran.
		self.assertEqual(run.source, 'run')

	def test_a_hand_typed_pipeline_is_declared_rather_than_run(self):
		run = self.provenance.run_for(
			self.request(**{'X-Pipeline': 'table-build', 'X-Engine': 'me'}),
			self.user)
		self.assertEqual(run.source, 'declared')

	def test_writes_naming_one_run_land_on_one_row(self):
		#A stage that sends fifty entries is one run, not fifty producers.
		first = self.provenance.run_for(
			self.request(**{'X-Run-Id': 'R1', 'X-Engine': 'codex-cli'}),
			self.user)
		second = self.provenance.run_for(
			self.request(**{'X-Run-Id': 'R1', 'X-Model': 'gpt-5.5'}),
			self.user)
		self.assertEqual(first.pk, second.pk)
		self.assertEqual(AgentRun.objects.count(), 1)
		#and the later write adds what the first did not know
		self.assertEqual(second.engine, 'codex-cli')
		self.assertEqual(second.model, 'gpt-5.5')

	def test_a_later_blank_does_not_erase_what_was_recorded(self):
		self.provenance.run_for(
			self.request(**{'X-Run-Id': 'R2', 'X-Model': 'gpt-5.5'}),
			self.user)
		again = self.provenance.run_for(
			self.request(**{'X-Run-Id': 'R2', 'X-Engine': 'codex-cli'}),
			self.user)
		self.assertEqual(again.model, 'gpt-5.5')

	def test_a_session_without_a_run_id_still_groups(self):
		#An interactive session that sends its engine and model and no id
		#should be one row for the day, not one row per edit.
		one = self.provenance.run_for(
			self.request(**{'X-Engine': 'claude-code',
			                'X-Pipeline': 'interactive'}), self.user)
		two = self.provenance.run_for(
			self.request(**{'X-Engine': 'claude-code',
			                'X-Pipeline': 'interactive'}), self.user)
		self.assertEqual(one.pk, two.pk)
		self.assertIn('zeta3', one.run_id)

	def test_the_person_at_the_keyboard_is_the_operator(self):
		run = self.provenance.run_for(
			self.request(**{'X-Pipeline': 'interactive',
			                'X-Engine': 'claude-code',
			                'X-Model': 'claude-opus-5'}), self.user)
		self.assertEqual(run.operator, self.user)
		self.assertIn('via claude-code', run.by)

	def test_the_sentence_still_reads_as_a_sentence(self):
		run = self.provenance.run_for(self.request(**{
			'X-Run-Id': 'R3', 'X-Pipeline': 'table-build@2.7+9f3ac1d2',
			'X-Engine': 'codex-cli', 'X-Model': 'gpt-5.5'}), self.user)
		self.assertEqual(self.provenance.sentence(run),
		                 'codex-cli gpt-5.5, table-build@2.7+9f3ac1d2')
		self.assertEqual(self.provenance.sentence(None), 'api')


class ReadingTheOldRecord(TestCase):
	"""The backfill's judgement, without a database full of history."""

	def test_the_eight_spellings_of_codex_mean_two_things(self):
		from .management.commands.backfill_provenance import spelling

		for text in ('assisted by codex-cli', 'codex-cli', 'codex',
		             'codex-cli table-build', 'assisted by Codex CLI, '
		             'table-split@c049f25'):
			self.assertEqual(spelling(text)[0], 'codex-cli', text)
		for text in ('assisted by Claude Opus 5', 'assisted by claude-opus-5',
		             'assisted by Claude (Opus 5)', 'assisted by Claude Code'):
			self.assertEqual(spelling(text)[0], 'claude-code', text)
		#A model is read where the string names one, and not invented where it
		#does not.
		self.assertEqual(spelling('assisted by Claude Opus 5')[1],
		                 'claude-opus-5')
		self.assertEqual(spelling('assisted by codex-cli')[1], '')
		self.assertEqual(spelling('api'), ('', ''))

	def test_a_data_repository_message_names_its_commit(self):
		from .management.commands.backfill_provenance import FROM_REPO

		found = FROM_REPO.search('from the data repository, fc072a35')
		self.assertEqual(found.group(1), 'fc072a35')

	def test_a_generator_publish_is_recognised_with_its_environment(self):
		from .management.commands.backfill_provenance import GENERATOR

		found = GENERATOR.match(
			'ChernSimonsKnotComplements (numberdb=0.1.10, python=3.12.3, '
			'sage=10.9), assisted by codex-cli')
		self.assertEqual(found.group(1), 'ChernSimonsKnotComplements')
		self.assertIn('sage=10.9', found.group(2))

	def test_the_ledger_is_read_positionally_past_its_header(self):
		#The header names sixteen columns and the rows carry eighteen: the
		#campaign and the batch were appended without being named, and a reader
		#that trusts the header loses exactly the two fields that say which
		#campaign a table came from.
		from .management.commands.backfill_provenance import Command

		handle = tempfile.NamedTemporaryFile('w', suffix='.tsv', delete=False,
		                                     encoding='utf-8')
		handle.write('started\tstage\tengine\tturns\tcost_usd\tresult\tlog\t'
		             'model\tprompt\tsession\tresumed\ttokens_in\t'
		             'tokens_cached\ttokens_out\tcost_by_model\ttable\n')
		handle.write('20260918T072306Z\tbuild\tcodex\t1\t8.32\tsuccess\tl.log\t'
		             'gpt-5.5\ttable-build@0a2cd3e\tsess\tno\t1\t2\t3\t'
		             'gpt-5.5=8.32\tT324\t20260918T035359Z\tBATCH-1\n')
		handle.close()
		try:
			rows = Command().read_ledger(handle.name, 'aws-builder')
		finally:
			os.unlink(handle.name)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]['campaign'], '20260918T035359Z')
		self.assertEqual(rows[0]['batch'], 'BATCH-1')
		self.assertEqual(rows[0]['table'], 'T324')
		self.assertEqual(rows[0]['machine'], 'aws-builder')

	def test_a_run_reconstructed_from_a_ledger_says_so(self):
		from .management.commands.backfill_provenance import Command

		command = Command()
		command.write = False
		command.versions = {'table-build': [
			{'major': '2', 'minor': 0, 'version': '2.0', 'digest': 'abc123def',
			 'commit': 'deadbeef', 'when': 1_700_000_000}]}
		run, _created = command.run_from_ledger({
			'started': '20260918T072306Z', 'stage': 'build', 'engine': 'codex',
			'model': 'gpt-5.5', 'cost_usd': '8.32',
			'cost_by_model': 'gpt-5.5=8.32', 'campaign': 'C1', 'batch': 'B1',
			'machine': 'aws-builder', 'prompt': 'table-build@0a2cd3e',
			'session': 's', 'turns': '1', 'result': 'success'})
		self.assertEqual(run.pipeline, 'table-build')
		self.assertEqual(run.engine, 'codex-cli')
		self.assertEqual(run.source, 'ledger')
		self.assertEqual(run.pipeline_version, '2.0')
		self.assertEqual(run.cost_by_model, {'gpt-5.5': '8.32'})
		#The ledger's own prompt commit and the scope's version are different
		#facts, and where they differ the difference is written down.
		self.assertIn('ledger recorded prompt', run.notes)


class TheRevisionPointsAtTheRun(TestCase):

	def test_a_revision_can_name_its_run(self):
		from .editing import create_table

		user = User.objects.create_user('maker', password='x')
		run = AgentRun.objects.create(
			run_id='20260918T072306Z', started='2026-09-18T07:23:06Z',
			pipeline='table-build', pipeline_version='2.7',
			pipeline_digest='9f3ac1d2', engine='codex-cli', model='gpt-5.5')
		table = create_table(document('Another table'), author=user, via='api',
		                     agent_run=run)
		revision = table.head_revision
		self.assertEqual(revision.agent_run, run)
		self.assertEqual(revision.agent_run.label,
		                 'table-build@2.7+9f3ac1d2')
		self.assertEqual(list(run.revisions.all()), [revision])
