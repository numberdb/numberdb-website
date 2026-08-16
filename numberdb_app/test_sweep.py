"""Tests for the arb sweep: mostly that it can say no.

A checker that never fires is indistinguishable from a clean corpus, and the
whole point of this one is the case where the database is wrong. T93 held 200
digits of which about 197 were right, and T32 stored the golden ratio's
conjugate under the label of its inverse; both had been public for years.

So the tests here corrupt a value on purpose and insist the sweep notices.
"""

from django.test import TestCase


def _check(stored, recompute, params=None):
	"""Run one entry through the sweep's comparison."""
	from .management.commands.sweep_arb import Command

	return Command()._check('T1', 'test', stored, params or {}, recompute)


class TheSweepCanSayNo(TestCase):

	def setUp(self):
		from sage.all import QQ

		#pi/4 as an ordinary irrational value to compare against.
		self.recompute = lambda params, field: field.pi() / QQ(4)
		self.true = ('0.78539816339744830961566084581987572104929234984377'
		             '64552437361480769541015715522496570087063355292669955')

	def test_a_correct_value_passes(self):
		self.assertEqual(_check(self.true, self.recompute)['verdict'], 'ok')

	def test_a_wrong_last_digit_is_within_the_convention(self):
		#`3.14` *is* (3.13, 3.15) here, so the final digit may be out by one
		#without the value being wrong. A checker that flagged this would
		#report most of the corpus.
		off_by_one = self.true[:-1] + str((int(self.true[-1]) + 1) % 10)
		self.assertEqual(_check(off_by_one, self.recompute)['verdict'], 'ok')

	def test_a_wrong_digit_further_in_is_caught(self):
		#The T93 shape: right for most of its length, wrong near the end by
		#much more than the last place allows.
		corrupted = self.true[:-6] + '999999'
		row = _check(corrupted, self.recompute)
		self.assertEqual(row['verdict'], 'wrong')
		self.assertGreater(row['ulps'], 1)

	def test_a_wrong_sign_is_caught(self):
		#The T32 shape: every digit right and the value still wrong.
		row = _check('-' + self.true, self.recompute)
		self.assertEqual(row['verdict'], 'wrong')

	def test_a_wrong_value_early_on_is_caught(self):
		row = _check('0.88539816339744830961566084581987572104929234984377',
		             self.recompute)
		self.assertEqual(row['verdict'], 'wrong')

	def test_a_complex_value_is_compared_in_both_parts(self):
		from sage.all import QQ, ComplexBallField

		def eighth_root(params, field):
			complex_field = ComplexBallField(field.precision())
			return (2 * complex_field.pi() * complex_field(0, 1)
			        * QQ(1) / 8).exp()

		true = ('0.70710678118654752440084436210484903928483593768847'
		        ' + i * 0.70710678118654752440084436210484903928483593768847')
		self.assertEqual(_check(true, eighth_root)['verdict'], 'ok')

		#Wrong only in the imaginary part, which a real-only comparison would
		#wave through -- and roots of unity are a whole table of these.
		wrong = true.replace(' + i * 0.7071', ' + i * 0.8071')
		self.assertEqual(_check(wrong, eighth_root)['verdict'], 'wrong')

	def test_an_entry_the_definition_cannot_do_is_skipped_not_passed(self):
		row = _check(self.true, lambda params, field: None)
		self.assertEqual(row['verdict'], 'skipped')

	def test_a_definition_that_raises_is_recorded_rather_than_swallowed(self):
		def broken(params, field):
			raise ValueError('no value for these parameters')

		row = _check(self.true, broken)
		self.assertEqual(row['verdict'], 'error')
		self.assertIn('no value', row['detail'])


class TheCheckpointResumes(TestCase):
	"""The sweep runs for hours on a machine that may be restarted."""

	def test_a_finished_entry_is_not_done_again(self):
		import json
		import os
		import tempfile
		from unittest import mock

		from django.core.management import call_command

		from .editing import create_table

		table = create_table(
			{'Title': 'Sweep probe',
			 'Data properties': {'type': 'R'},
			 'Parameters': {'s': {'type': 'Q'}},
			 'Numbers': [{'params': {'s': '1/2'}, 'number': '1.7724538509'},
			             {'params': {'s': '3/2'}, 'number': '0.8862269254'}]})

		#The registry is keyed by the real table ids, and a test database has
		#none of them. Point it at the table just made, or this checks that
		#nothing happens twice -- which it did, silently, when first written.
		def registry():
			from sage.all import QQ

			return {table.tid: ('real',
			                    lambda params, field: field(QQ(params['s'])).gamma())}

		with tempfile.TemporaryDirectory() as tmp:
			path = os.path.join(tmp, 'sweep.jsonl')
			with mock.patch(
					'numberdb_app.management.commands.sweep_arb._recomputations',
					registry):
				call_command('sweep_arb', only=table.tid, out=path, verbosity=0)
				rows = open(path).readlines()
				self.assertEqual(len(rows), 2, rows)
				self.assertTrue(all(json.loads(r)['verdict'] == 'ok'
				                    for r in rows), rows)

				#Second run adds nothing: both entries are already decided.
				call_command('sweep_arb', only=table.tid, out=path, verbosity=0)
				self.assertEqual(len(open(path).readlines()), 2)

				#And --restart does them again, which is the other half of
				#being resumable: a checkpoint you cannot discard is a cache.
				call_command('sweep_arb', only=table.tid, out=path,
				             restart=True, verbosity=0)
				self.assertEqual(len(open(path).readlines()), 2)

	def test_a_torn_line_does_not_stop_the_resume(self):
		"""A process killed mid-write leaves half a line. It costs that entry
		and nothing else."""
		import os
		import tempfile
		from unittest import mock

		from django.core.management import call_command

		from .editing import create_table

		table = create_table(
			{'Title': 'Torn line probe',
			 'Data properties': {'type': 'R'},
			 'Parameters': {'s': {'type': 'Q'}},
			 'Numbers': [{'params': {'s': '1/2'}, 'number': '1.7724538509'}]})

		def registry():
			from sage.all import QQ

			return {table.tid: ('real',
			                    lambda params, field: field(QQ(params['s'])).gamma())}

		with tempfile.TemporaryDirectory() as tmp:
			path = os.path.join(tmp, 'sweep.jsonl')
			with open(path, 'w') as handle:
				handle.write('{"table": "%s", "identity": "{\\"s\\": ' % table.tid)

			with mock.patch(
					'numberdb_app.management.commands.sweep_arb._recomputations',
					registry):
				call_command('sweep_arb', only=table.tid, out=path, verbosity=0)

			lines = [l for l in open(path).readlines() if l.strip()]
			self.assertEqual(len(lines), 2)      # the torn one, and the redone entry


class ThePAdicSideCanSayNo(TestCase):
	"""The p-adic engine has no tolerance in it, and should not need one.

	A p-adic value states how far it is known -- `... + O(2^167)` -- so there
	is no judgement about how many digits to compare: the difference must
	vanish to exactly that precision.
	"""

	def _check(self, stored, recompute, params=None):
		from .management.commands.sweep_arb import Command

		return Command()._check_p_adic('T44', 'test', stored, params or {},
		                               recompute)

	def setUp(self):
		from sage.all import Qp

		#The Teichmueller representative of 3 in Z_5, to 20 places.
		self.true = str(Qp(5, 20).teichmuller(3))
		self.recompute = lambda params, prec: Qp(5, prec + 5).teichmuller(3)

	def test_a_matching_value_passes(self):
		self.assertEqual(self._check(self.true, self.recompute)['verdict'], 'ok')

	def test_a_value_wrong_in_its_last_place_is_caught(self):
		from sage.all import Qp

		#Not "close enough": p-adically, differing at 5^19 within a value
		#claiming O(5^20) is simply a different number.
		wrong = str(Qp(5, 20).teichmuller(3) + Qp(5, 20)(5) ** 19)
		row = self._check(wrong, self.recompute)
		self.assertEqual(row['verdict'], 'wrong')
		self.assertEqual(row['agrees_to'], 19)

	def test_the_comparison_uses_the_stored_precision(self):
		#A value known to fewer places is not wrong for being vaguer, so long
		#as it agrees as far as it claims.
		from sage.all import Qp

		shorter = str(Qp(5, 8).teichmuller(3))
		self.assertEqual(self._check(shorter, self.recompute)['verdict'], 'ok')

	def test_a_definition_that_cannot_do_the_entry_is_skipped(self):
		row = self._check(self.true, lambda params, prec: None)
		self.assertEqual(row['verdict'], 'skipped')
