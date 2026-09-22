"""What the pipeline offers next, and what it must not offer twice.

    python3 agents/test_work.py

The network is not exercised: `demands()` is given issues, and the rest reads
files in a temporary directory. What is tested is the part that went wrong --
whether an item that has been acted on comes back.
"""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import work  # noqa: E402  (the file under test)


ISSUES = [{'number': 155, 'title': 'Extend T293 (regulators over real '
                                   'quadratic fields): raise the bound',
           'body': 'More fields, please.'},
          {'number': 160, 'title': 'T137 wants a reference', 'body': ''},
          {'number': 161, 'title': 'nothing to do with a table', 'body': ''}]


class ADemandIsActedOnOnce(unittest.TestCase):

	def setUp(self):
		self.critiques = tempfile.mkdtemp()
		self.real_critiques, work.CRITIQUES = work.CRITIQUES, self.critiques
		self.real_api = work.proposals.api
		work.proposals.api = lambda path: list(ISSUES)

	def tearDown(self):
		work.CRITIQUES = self.real_critiques
		work.proposals.api = self.real_api
		shutil.rmtree(self.critiques, ignore_errors=True)

	def wrote(self, name):
		with open(os.path.join(self.critiques, name), 'w') as handle:
			handle.write('# a report\n')

	def test_an_issue_naming_a_table_is_work(self):
		found = work.demands()
		self.assertEqual([item['tid'] for item in found], ['T293', 'T137'])
		#The third issue names no table, so there is nothing to act on.
		self.assertEqual(len(found), 2)

	def test_a_demand_whose_repair_has_reported_is_done(self):
		#The fault this exists for: `pick()` puts a person's demand before
		#everything else, and nothing marked one as acted on -- so a campaign
		#repaired T293 twenty-six times for $58 and built no table. The mark is
		#the repair's own report, which is also what a person would read.
		self.wrote('T293-repaired.md')
		self.assertEqual([item['tid'] for item in work.demands()], ['T137'])

	def test_a_critique_without_a_repair_is_not_done(self):
		#Written but not acted on: the work is still waiting.
		self.wrote('T293.md')
		self.assertIn('T293', [item['tid'] for item in work.demands()])

	def test_the_demand_comes_before_the_other_kinds(self):
		#Somebody is waiting for it, which is the whole of the ordering rule.
		self.assertEqual(work.pick(done=0)['kind'], 'demand')

	def test_and_when_every_demand_is_done_the_other_kinds_run(self):
		self.wrote('T293-repaired.md')
		self.wrote('T137-repaired.md')
		self.assertEqual(work.demands(), [])


class TheMemoryIsShared(unittest.TestCase):
	"""Four workers, one record of what has been asked."""

	def setUp(self):
		self.shared = tempfile.mkdtemp()
		self.real = work.CRITIQUES

	def tearDown(self):
		work.CRITIQUES = self.real
		shutil.rmtree(self.shared, ignore_errors=True)

	def test_the_directory_comes_from_the_environment(self):
		#Each worker has its own worktree, so a per-tree directory is four
		#separate memories: 352 growth questions went to about 115 tables and
		#T293 was asked twelve times before this.
		import importlib
		import os

		os.environ['NUMBERDB_CRITIQUES'] = self.shared
		try:
			importlib.reload(work)
			self.assertEqual(work.CRITIQUES, self.shared)
			open(os.path.join(self.shared, 'T99-growth.md'), 'w').close()
			self.assertTrue(work.read('T99', '-growth'))
		finally:
			del os.environ['NUMBERDB_CRITIQUES']
			importlib.reload(work)


class ATableIsReviewedOnce(unittest.TestCase):
	"""One critique and one repair, not one of each kind of question."""

	def setUp(self):
		self.critiques = tempfile.mkdtemp()
		self.real, work.CRITIQUES = work.CRITIQUES, self.critiques

	def tearDown(self):
		work.CRITIQUES = self.real
		shutil.rmtree(self.critiques, ignore_errors=True)

	def wrote(self, name):
		open(os.path.join(self.critiques, name), 'w').close()

	def test_a_table_nobody_has_read_is_waiting(self):
		self.assertFalse(work.considered('T50'))

	def test_any_of_the_three_marks_it_read(self):
		#Each kind used to look only for its own file, so a table that had
		#been swept and repaired was still offered as one nobody had asked
		#about growing. 117 of 404 tables went through twice that way.
		for suffix in ('', '-growth', '-repaired'):
			with self.subTest(suffix=suffix):
				self.wrote('T60%s.md' % suffix)
				self.assertTrue(work.considered('T60'))
				os.remove(os.path.join(self.critiques, 'T60%s.md' % suffix))

	def test_a_swept_table_is_not_then_asked_about_growth(self):
		#The sweep read the whole table, its range included. Asking
		#afterwards whether the range could grow is the same reader meeting
		#the same table a second time, at a critique and a repair apiece.
		self.wrote('T70.md')
		self.assertTrue(work.considered('T70'))

	def test_a_person_may_still_ask_about_a_table_that_was_read(self):
		#A demand is not one of the pipeline's own questions: somebody opened
		#an issue, and "we have already looked at that one" is not an answer
		#to a person. `demands()` stays gated on the repair alone.
		self.assertNotIn('demand', work.QUESTIONS)
		self.wrote('T80.md')
		self.assertTrue(work.considered('T80'))
		self.assertFalse(work.read('T80', '-repaired'))


if __name__ == '__main__':
	unittest.main(verbosity=1)
