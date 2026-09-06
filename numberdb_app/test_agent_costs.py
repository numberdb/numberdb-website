"""What a run cost, in money, whichever harness ran it.

Tokens do not compare. A cached input token on Fable 5.1 costs a fortieth of
a fresh one; the two harnesses cache differently; one counts a whole `exec`
as a turn where the other counts a message. Money is the only figure that
means the same on both sides, so every row carries it at list API prices.

The rate table is checked against a real run rather than trusted: the T160
build reports `costUSD` 13.9794595 at list basis, and the rates reproduce it.
"""
import importlib.util
import os

from django.conf import settings
from django.test import SimpleTestCase


def module():
	path = os.path.join(settings.BASE_DIR, 'agents', 'ledger.py')
	spec = importlib.util.spec_from_file_location('agent_ledger', path)
	loaded = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(loaded)
	return loaded


class TheRatesAreThePublishedOnes(SimpleTestCase):

	def setUp(self):
		self.ledger = module()

	def test_it_reproduces_a_real_run_to_the_cent(self):
		"""The T160 build, whose own report says 13.9794595 at list basis."""
		cost = self.ledger.price(
			'claude-fable-5-1', input_tokens=16389, cache_read=7004158,
			cache_write_1h=338589, output_tokens=105855)
		self.assertAlmostEqual(cost, 13.9794595, places=6)

	def test_a_dated_model_name_finds_its_rate(self):
		#The transcripts name claude-haiku-4-5-20251001, the table names the
		#model.
		rate = self.ledger.rate_for('claude-haiku-4-5-20251001')
		self.assertEqual(rate['input'], 1)

	def test_the_longest_match_wins(self):
		#Otherwise gpt-5.5-pro is priced as gpt-5, at a twenty-fourth of the
		#output rate.
		self.assertEqual(self.ledger.rate_for('gpt-5.5-pro')['output'], 180)
		self.assertEqual(self.ledger.rate_for('gpt-5.5')['output'], 30)

	def test_a_model_nobody_priced_gives_no_cost(self):
		#Rather than a plausible-looking wrong number.
		self.assertIsNone(self.ledger.rate_for('some-new-model'))
		self.assertIsNone(self.ledger.price('some-new-model', output_tokens=10))

	def test_the_cached_part_is_not_charged_twice(self):
		#`input_tokens` is the uncached input: codex reports a total that
		#includes the cached part, and the caller subtracts it.
		fresh = self.ledger.price('gpt-5.5', input_tokens=1000000)
		cached = self.ledger.price('gpt-5.5', cache_read=1000000)
		self.assertEqual(fresh, 5.0)
		self.assertEqual(cached, 0.5)

	def test_every_rate_row_is_complete(self):
		for name, rate in self.ledger.load_rates().items():
			with self.subTest(model=name):
				for field in ('input', 'cache_read', 'cache_write_5m',
				              'cache_write_1h', 'output'):
					self.assertGreater(rate[field], 0)
				self.assertGreaterEqual(rate['output'], rate['input'])
				self.assertLessEqual(rate['cache_read'], rate['input'])


class TheLedgerRowSaysWhatWasSpent(SimpleTestCase):

	def setUp(self):
		self.ledger = module()

	def test_the_columns_are_the_ones_the_file_has(self):
		for name in ('cost_usd', 'model', 'tokens_in', 'tokens_cached',
		             'tokens_out', 'cost_by_model'):
			self.assertIn(name, self.ledger.COLUMNS)

	def test_a_row_has_one_field_per_column(self):
		line = self.ledger.row('/nonexistent.log', '20260906T000000Z', 'build',
		                       'claude', 'p@abc', 'sess', 'no', 'gpt-5.5')
		self.assertEqual(len(line.split('\t')), len(self.ledger.COLUMNS))

	def test_codex_tokens_become_dollars(self):
		import json
		import tempfile

		events = [
			{'type': 'thread.started', 'thread_id': 'abc'},
			{'type': 'turn.completed',
			 'usage': {'input_tokens': 1000000, 'cached_input_tokens': 900000,
			           'output_tokens': 100000}},
		]
		with tempfile.NamedTemporaryFile('w', suffix='.log', delete=False) as handle:
			for event in events:
				handle.write(json.dumps(event) + '\n')
			path = handle.name
		try:
			found = self.ledger.codex_run(path, 'gpt-5.5')
		finally:
			os.unlink(path)
		#100k fresh input at $5, 900k cached at $0.50, 100k output at $30.
		self.assertAlmostEqual(found['cost'], 0.5 + 0.45 + 3.0, places=6)
		self.assertEqual(found['turns'], 1)
		self.assertEqual(found['thread'], 'abc')

	def test_a_run_with_no_events_records_no_result(self):
		line = self.ledger.row('/nonexistent.log', '20260906T000000Z', 'build',
		                       'codex', 'p@abc', 'sess', 'no', 'gpt-5.5')
		self.assertIn('no result record', line)
