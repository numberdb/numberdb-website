"""Which work comes next, and why.

    python3 agents/test_work.py

One pipeline, four sources. The ordering is the whole of the policy, and it
is the kind of thing that looks obviously right and is quietly wrong: the
first version of the proposal queue preferred the newest family, and stranded
the one nobody had started.
"""
import io
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import work  # noqa: E402


class WhatComesNext(unittest.TestCase):

	def setUp(self):
		self.room = tempfile.mkdtemp()
		self.real = (work.SHAPE, work.CRITIQUES, work.demands, work.proposal,
		             work.REVIEW_EVERY)
		work.SHAPE = os.path.join(self.room, 'shape.tsv')
		work.CRITIQUES = os.path.join(self.room, 'critiques')
		os.makedirs(work.CRITIQUES)
		with io.open(work.SHAPE, 'w', encoding='utf-8') as handle:
			handle.write('tid\tentries\tbytes\ttitle\n')
			#Two hand-made tables, one small new one, one full new one.
			handle.write('T3\t40\t9000\tAn old table\n')
			handle.write('T4\t50\t9000\tAnother old table\n')
			handle.write('T280\t20\t6000\tA new small table\n')
			handle.write('T281\t900\t200000\tA new full table\n')
		work.demands = lambda: []
		work.proposal = lambda: {'kind': 'proposal', 'title': 'a new table'}

	def tearDown(self):
		(work.SHAPE, work.CRITIQUES, work.demands, work.proposal,
		 work.REVIEW_EVERY) = self.real

	def test_a_demand_from_a_person_comes_first(self):
		#Somebody is waiting, and nobody waits for a sweep.
		work.demands = lambda: [{'kind': 'demand', 'issue': 1, 'tid': 'T3',
		                         'title': 'make it longer', 'body': 'please'}]
		self.assertEqual(work.pick(done=0)['kind'], 'demand')
		self.assertEqual(work.pick(done=1)['kind'], 'demand')

	def test_building_and_reviewing_take_turns(self):
		#A campaign that only builds never returns to what it built.
		work.REVIEW_EVERY = 2
		self.assertEqual(work.pick(done=0)['kind'], 'proposal')
		self.assertIn(work.pick(done=1)['kind'], ('growth', 'sweep'))
		self.assertEqual(work.pick(done=2)['kind'], 'proposal')

	def test_reviewing_can_be_turned_off(self):
		work.REVIEW_EVERY = 0
		for done in range(4):
			self.assertEqual(work.pick(done=done)['kind'], 'proposal')

	def test_growth_asks_the_newest_small_table(self):
		#The one whose generator is still understood, and whose range was
		#most likely chosen in a hurry.
		self.assertEqual(work.growth()[0]['tid'], 'T280')

	def test_a_full_table_is_not_asked_to_grow(self):
		self.assertNotIn('T281', [w['tid'] for w in work.growth()])

	def test_the_sweep_starts_at_the_oldest(self):
		self.assertEqual(work.sweep()[0]['tid'], 'T3')

	def test_a_table_already_read_is_not_read_again(self):
		io.open(os.path.join(work.CRITIQUES, 'T3.md'), 'w').write('read')
		self.assertEqual(work.sweep()[0]['tid'], 'T4')

	def test_a_table_already_asked_about_growth_is_not_asked_again(self):
		io.open(os.path.join(work.CRITIQUES, 'T280-growth.md'), 'w').write('x')
		self.assertNotIn('T280', [w['tid'] for w in work.growth()])

	def test_a_demand_is_written_where_repair_looks(self):
		#With its provenance: a person is authoritative about what is wanted
		#and not about what is true.
		path = work.write_demand({'kind': 'demand', 'issue': 155, 'tid': 'T9',
		                          'title': 'Extend it', 'body': 'More D.'})
		body = io.open(path, encoding='utf-8').read()
		self.assertTrue(path.endswith('T9.md'))
		self.assertIn('numberdb-data#155', body)
		self.assertIn('claim', body)
		self.assertIn('More D.', body)


if __name__ == '__main__':
	unittest.main(verbosity=1)
