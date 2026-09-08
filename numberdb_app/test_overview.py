"""One row per table, for somebody deciding where to look next.

The corpus grows by a handful of tables a night and the only way to see its
shape was to open them one at a time. The cost is stored split by model and by
role because "what did this table cost", "what has that model cost us" and
"what does critiquing cost against building" are three questions about the
same money, and a single total answers none of them.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .editing import commit_table
from .models import Table, TableCost, TableMetrics


class TheOverviewShowsTheCorpus(TestCase):

	def setUp(self):
		User = get_user_model()
		self.editor = User.objects.create_user('overview_editor', password='x')
		self.author = User.objects.create_user('overview_author')
		self.table = Table.objects.create(
			tid='T750', tid_int=750, url='t750', title='A measured table',
			title_lowercase='a measured table', published=True)
		commit_table(self.table,
		             {'Title': 'A measured table',
		              'Parameters': {'n': {'type': 'Z'}},
		              'Data properties': {'type': 'Z'},
		              'Numbers': {'1': '2', '2': '4'}},
		             author=self.author, message='m', via='orm')

	def refresh(self):
		from .management.commands.refresh_table_metrics import refresh

		return refresh(self.table)

	def page(self, query=''):
		client = Client()
		client.force_login(self.editor)
		return client.get('/overview' + query, HTTP_HOST='numberdb.org')

	def test_it_counts_entries_and_edits(self):
		metrics = self.refresh()
		self.assertEqual(metrics.entry_count, 2)
		self.assertEqual(metrics.edit_count, self.table.revisions.count())
		self.assertEqual(metrics.data_type, 'Z')

	def test_the_row_is_on_the_page(self):
		self.refresh()
		body = self.page().content.decode()
		self.assertIn('T750', body)
		self.assertIn('A measured table', body)

	def test_the_cost_is_the_sum_of_its_parts(self):
		TableCost.objects.create(table=self.table, model='claude-fable-5-1',
		                         role='build', engine='claude',
		                         cost_usd=Decimal('10.50'), runs=1)
		TableCost.objects.create(table=self.table, model='gpt-5.5',
		                         role='critique', engine='codex',
		                         cost_usd=Decimal('2.25'), runs=1)
		metrics = self.refresh()
		self.assertEqual(metrics.agent_cost_usd, Decimal('12.75'))
		self.assertIn('12.75', self.page().content.decode())

	def test_the_breakdown_answers_three_questions(self):
		TableCost.objects.create(table=self.table, model='claude-fable-5-1',
		                         role='build', engine='claude',
		                         cost_usd=Decimal('10'), runs=1)
		TableCost.objects.create(table=self.table, model='gpt-5.5',
		                         role='critique', engine='codex',
		                         cost_usd=Decimal('3'), runs=2)
		self.refresh()
		for granularity, expected in (('role', {'build', 'critique'}),
		                              ('model', {'claude-fable-5-1', 'gpt-5.5'}),
		                              ('engine', {'claude', 'codex'})):
			with self.subTest(by=granularity):
				response = self.page('?by=' + granularity)
				names = {item['name'] for item in response.context['breakdown']}
				self.assertEqual(names, expected)

	def test_a_table_nobody_paid_for_shows_a_dash(self):
		self.refresh()
		self.assertIn('&mdash;', self.page().content.decode())

	def test_it_sorts(self):
		other = Table.objects.create(
			tid='T751', tid_int=751, url='t751', title='Another',
			title_lowercase='another', published=True)
		TableMetrics.objects.create(table=other, entry_count=99, edit_count=1)
		self.refresh()
		rows = list(self.page('?sort_by=entries').context['rows'])
		self.assertEqual(rows[0].table.tid, 'T751')

	def test_a_stranger_cannot_see_it(self):
		#Not secret, but it is a workbench: it names drafts and what they cost.
		self.assertEqual(Client().get('/overview', HTTP_HOST='numberdb.org')
		                 .status_code, 302)


class ImportingTheLedger(TestCase):
	"""The runs' ledger is the source; importing it twice is not paying twice."""

	def setUp(self):
		self.table = Table.objects.create(
			tid='T752', tid_int=752, url='t752', title='Imported',
			title_lowercase='imported', published=True)

	def ledger(self, rows):
		import tempfile

		columns = ['started', 'stage', 'engine', 'turns', 'cost_usd', 'result',
		           'log', 'model', 'prompt', 'session', 'resumed', 'tokens_in',
		           'tokens_cached', 'tokens_out', 'cost_by_model', 'table']
		handle = tempfile.NamedTemporaryFile('w', suffix='.tsv', delete=False)
		handle.write('\t'.join(columns) + '\n')
		for row in rows:
			handle.write('\t'.join(str(row.get(name, '')) for name in columns)
			             + '\n')
		handle.close()
		return handle.name

	def run_import(self, path):
		import os

		from django.core.management import call_command

		try:
			call_command('import_agent_costs', path, verbosity=0)
		finally:
			os.unlink(path)

	def test_the_per_model_split_is_kept(self):
		self.run_import(self.ledger([{
			'started': '20260908T000000Z', 'stage': 'build', 'engine': 'claude',
			'cost_usd': '13.98', 'model': 'claude-fable-5-1', 'table': 'T752',
			'cost_by_model': 'claude-fable-5-1=13.9795;claude-haiku-4-5=0.0053',
		}]))
		got = {(c.model, c.role): c.cost_usd
		       for c in TableCost.objects.filter(table=self.table)}
		self.assertEqual(set(got), {('claude-fable-5-1', 'build'),
		                            ('claude-haiku-4-5', 'build')})
		self.assertEqual(got[('claude-haiku-4-5', 'build')], Decimal('0.0053'))

	def test_importing_twice_is_not_paying_twice(self):
		rows = [{'started': '20260908T000000Z', 'stage': 'build',
		         'engine': 'codex', 'cost_usd': '10.85', 'model': 'gpt-5.5',
		         'table': 'T752', 'cost_by_model': 'gpt-5.5=10.8540'}]
		self.run_import(self.ledger(rows))
		self.run_import(self.ledger(rows))
		self.assertEqual(TableCost.objects.filter(table=self.table).count(), 1)
		self.assertEqual(
			TableCost.objects.get(table=self.table).cost_usd,
			Decimal('10.8540'))

	def test_a_run_about_no_table_is_skipped(self):
		self.run_import(self.ledger([{
			'started': '20260908T000000Z', 'stage': 'ideas', 'engine': 'claude',
			'cost_usd': '8.70', 'model': 'claude-fable-5-1', 'table': '',
		}]))
		self.assertEqual(TableCost.objects.count(), 0)

	def test_the_total_lands_on_the_table(self):
		self.run_import(self.ledger([
			{'started': '20260908T000000Z', 'stage': 'build', 'engine': 'codex',
			 'cost_usd': '10', 'model': 'gpt-5.5', 'table': 'T752',
			 'cost_by_model': 'gpt-5.5=10'},
			{'started': '20260908T010000Z', 'stage': 'critique',
			 'engine': 'claude', 'cost_usd': '3', 'model': 'claude-fable-5-1',
			 'table': 'T752', 'cost_by_model': 'claude-fable-5-1=3'},
		]))
		self.assertEqual(TableMetrics.objects.get(table=self.table)
		                 .agent_cost_usd, Decimal('13'))
