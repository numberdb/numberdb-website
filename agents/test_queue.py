"""The queue's parsing, without GitHub.

    python3 agents/test_queue.py

Everything here is text in and text out: what a batch file says, what an issue
body says, and what happens when a box is ticked. The network is the part that
cannot be tested here and is also the part least likely to be wrong.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import queue as q  # noqa: E402  (the file under test, not the stdlib module)


BATCH = """# Batch: values of the special functions -- Bessel, Airy and the
rest of them

Written 2026-09-12 for numberdb-data#7, which asks for special function
values, and #60.

## How this run went

| step | done |
|---|---|
| read the skill | yes |

## Conventions shared by the tables

Every table uses the same grid of rational arguments, and every value is
computed in ball arithmetic.

## 1. Values of the Bessel functions at rational arguments

What it is. The first one.

## 2. Values of the Airy functions at rational arguments

What it is. The second one.

## Ranking

1 then 2.
"""


class WhatABatchSays(unittest.TestCase):

	def setUp(self):
		self.batch = q.parse_batch(BATCH, 'agents/table-ideas/BATCH-2026-09-12T1857.md')

	def test_the_proposals_come_out_in_the_order_the_batch_ranks_them(self):
		#The ranking is the batch's argument about what to build first, and
		#the build order is the one thing that would silently waste it.
		self.assertEqual(self.batch['proposals'], [
			'Values of the Bessel functions at rational arguments',
			'Values of the Airy functions at rational arguments'])

	def test_the_date_comes_from_the_name(self):
		self.assertEqual(self.batch['screened'], '2026-09-12')
		self.assertEqual(self.batch['batch'], 'BATCH-2026-09-12T1857')

	def test_the_conventions_are_carried_over(self):
		#What a build needs in front of it. Without this the family issue is
		#a list of titles and the tables stop agreeing with each other.
		self.assertIn('same grid of rational arguments',
		              self.batch['conventions'])
		self.assertNotIn('read the skill', self.batch['conventions'])

	def test_it_records_which_requests_it_answers(self):
		self.assertEqual(self.batch['draws_on'], [7, 60])

	def test_the_heading_loses_the_word_batch(self):
		#Both forms are in use -- `# Batch: volumes of...` and `# Batch
		#2026-09-12T1831: Lehmer's problem...` -- and an issue titled
		#"Family: Batch 2026-09-12T1831: ..." says the same thing three times.
		for heading in ('# Batch: Lehmer\'s problem and Mahler measures',
		                '# Batch 2026-09-12T1831: Lehmer\'s problem and '
		                'Mahler measures',
		                '# Lehmer\'s problem and Mahler measures, screened '
		                '2026-09-12'):
			batch = q.parse_batch(heading + '\n\n## 1. A table\n',
			                      'BATCH-2026-09-12T1831.md')
			self.assertEqual(batch['subject'],
			                 "Lehmer's problem and Mahler measures")

	def test_a_heading_that_names_five_families_is_shortened(self):
		long = ('volumes of hyperbolic manifolds and orbifolds -- the closed '
		        'and cusped census manifolds, the prime links, the Coxeter '
		        'simplices of dimensions 3 to 9, and the Bianchi orbifolds')
		self.assertLessEqual(len(q._short(long)), 90)
		self.assertTrue(q._short(long).startswith('volumes of hyperbolic'))


class WhatAnIssueSays(unittest.TestCase):

	def setUp(self):
		self.batch = q.parse_batch(BATCH, 'BATCH-2026-09-12T1857.md')
		self.body = q.issue_body(self.batch)
		self.family = q.parse_family({'number': 42, 'title': 'Family: x',
		                              'body': self.body})

	def test_an_issue_reads_back_as_the_family_it_was(self):
		self.assertEqual(self.family['batch'], 'BATCH-2026-09-12T1857')
		self.assertEqual(self.family['screened'], '2026-09-12')
		self.assertEqual([item['title'] for item in self.family['items']],
		                 self.batch['proposals'])
		self.assertEqual(len(q.waiting(self.family)), 2)

	def test_an_issue_nobody_wrote_as_a_family_is_not_one(self):
		#The label can be put on by hand, and a person's issue under it must
		#not be read as a checklist of work.
		self.assertIsNone(q.parse_family(
			{'number': 1, 'title': 'Cantor polynomial',
			 'body': 'It would be nice to have this table.'}))

	def test_ticking_a_box_records_the_table(self):
		body = q._tick(self.family, self.batch['proposals'][0], 'T226')
		self.assertIn('- [x] Values of the Bessel functions at rational '
		              'arguments -- T226', body)
		after = q.parse_family({'number': 42, 'title': 't', 'body': body})
		self.assertEqual(len(q.waiting(after)), 1)

	def test_a_title_may_drift_between_the_proposal_and_the_table(self):
		#Real drift: proposed as "Values of the digamma function at rational
		#numbers", built as "Values of the digamma function $\\psi(x)$ at
		#rational numbers". Requiring the string to match would leave the box
		#unticked and the family open for ever.
		body = q._tick(self.family,
		               'Values of the Bessel functions $J_\\nu$ and $Y_\\nu$ '
		               'at rational arguments', 'T226')
		self.assertIsNotNone(body)
		self.assertIn('-- T226', body)

	def test_an_en_dash_is_a_separator(self):
		#The batches write `Euler–Lehmer` and the table that answers it is
		#`Euler-Lehmer`: one token against two, and no match at all.
		self.assertTrue(q._same_subject('Euler–Lehmer constants',
		                                'Euler-Lehmer constants'))

	def test_a_proposal_carrying_its_own_commentary_still_matches(self):
		#"Rank last; the case against is real" is part of the heading, and
		#those words drag the overlap below any threshold.
		self.assertTrue(q._same_subject(
			'Volumes of the Birkhoff polytopes. Rank last; the case against '
			'is real', 'Volumes of the Birkhoff polytopes'))

	def test_a_distinguishing_word_keeps_two_titles_apart(self):
		#Containment is not "shares most words": the thing the title is *of*
		#has to be the same thing.
		self.assertFalse(q._same_subject(
			'Ehrhart polynomials of the permutohedra',
			'Ehrhart polynomials of the hypersimplices'))
		self.assertFalse(q._same_subject(
			'Values of the digamma function at rational numbers',
			'Zeros of the digamma function'))

	def test_a_two_word_title_is_not_matched_by_containment(self):
		#`Golden ratio` is inside `Pisot numbers less than the golden ratio`
		#and is not that table; `Rational numbers` is inside half the corpus.
		self.assertFalse(q._same_subject(
			'Pisot numbers less than the golden ratio', 'Golden ratio'))
		self.assertFalse(q._same_subject(
			'Values of the polygamma functions at rational numbers',
			'Rational numbers'))

	def test_a_two_word_title_matches_when_it_is_exact(self):
		#The notation in a proposal title may be the third word in human
		#terms, but the matcher strips it. Exact equality after stripping is
		#still the same table.
		self.assertTrue(q._same_subject(
			'Charlier polynomials $C_n(x;a)$',
			'Charlier polynomials $C_n(x;a)$'))

	#What this cannot do, written down rather than asserted: "Orders of the
	#finite groups of Lie type as polynomials in $q$" and "Orders of finite
	#simple groups of Lie type" are different tables -- one holds integers for
	#a given $q$, the other polynomials -- and they share every word but two.
	#No word-counting separates them. The build re-checks the corpus before it
	#spends anything, which is where that judgement belongs.

	def test_a_table_from_another_family_ticks_nothing(self):
		self.assertIsNone(q._tick(self.family, 'Salem numbers below 1.3',
		                          'T300'))

	def test_ticking_twice_moves_to_the_next_box(self):
		once = q._tick(self.family, self.batch['proposals'][0], 'T226')
		family = q.parse_family({'number': 42, 'title': 't', 'body': once})
		twice = q._tick(family, self.batch['proposals'][1], 'T227')
		self.assertIn('-- T226', twice)
		self.assertIn('-- T227', twice)
		after = q.parse_family({'number': 42, 'title': 't', 'body': twice})
		self.assertEqual(q.waiting(after), [])


class WhichTableIsNext(unittest.TestCase):

	def family(self, number, screened, done):
		batch = q.parse_batch(BATCH, 'BATCH-%s.md' % screened)
		body = q.issue_body(batch, done)
		return q.parse_family({'number': number, 'title': 'Family: x',
		                       'body': body})

	def setUp(self):
		self.started = self.family(10, '2026-09-01',
		                           [('Values of the Bessel functions at '
		                             'rational arguments', 'T226')])
		self.newer = self.family(20, '2026-09-12', [])
		self.asked = None
		self.real = q.families
		q.families = lambda state='open': [self.newer, self.started]

	def tearDown(self):
		q.families = self.real

	def test_a_half_built_family_is_finished_before_a_new_one_is_opened(self):
		#The debt first, even though family 20 was screened eleven days
		#later. The symmetric-function family sat five-for-five unbuilt while
		#newer batches were screened and built past it, and nothing was ever
		#going to come back for it.
		family, item = q.next_table()
		self.assertEqual(family['number'], 10)
		self.assertEqual(item['title'],
		                 'Values of the Airy functions at rational arguments')

	def test_an_untouched_family_is_taken_oldest_first_too(self):
		#A family nobody has started is a leftover as much as a half-built
		#one: #138 was screened on 2026-09-12 and was still waiting four days
		#later while two families screened after it went ahead.
		older = self.family(5, '2026-08-01', [])
		q.families = lambda state='open': [self.newer, older]
		family, _ = q.next_table()
		self.assertEqual(family['number'], 5)

	def test_the_family_already_started_is_finished_first(self):
		#Not the newest. A half-built family loses the thing that made the
		#batch worth screening as a batch: the tables share machinery and
		#point at each other, and T219 and T222 to T225 read as a family only
		#because one campaign happened to get through all of them.
		family, item = q.next_table(prefer=10)
		self.assertEqual(family['number'], 10)
		self.assertEqual(item['title'],
		                 'Values of the Airy functions at rational arguments')

	def test_a_finished_family_does_not_hold_the_queue(self):
		done = self.family(30, '2026-09-13',
		                   [('Values of the Bessel functions at rational '
		                     'arguments', 'T226'),
		                    ('Values of the Airy functions at rational '
		                     'arguments', 'T227')])
		q.families = lambda state='open': [done, self.newer]
		family, _ = q.next_table(prefer=30)
		self.assertEqual(family['number'], 20)

	def test_a_skipped_proposal_is_not_offered_again(self):
		#A build that looked at a proposal and declined it for a good reason
		#left an empty box, so the next campaign paid to reach the same
		#conclusion. `skipped` settles it without claiming a table was made.
		batch = q.parse_batch(BATCH, 'BATCH-2026-09-12T1857.md')
		body = q.issue_body(batch)
		family = q.parse_family({'number': 40, 'title': 'f', 'body': body})
		body = q._tick(family, batch['proposals'][0], None,
		               why='the corpus holds this as T187 under another name')
		after = q.parse_family({'number': 40, 'title': 'f', 'body': body})
		self.assertIn('- [-]', body)
		self.assertIn('skipped: the corpus holds this', body)
		self.assertEqual(len(q.waiting(after)), 1)
		settled = [i for i in after['items'] if i['done']][0]
		self.assertFalse(settled['built'])
		self.assertIsNone(settled['tid'])
		#and it counts as work done, so the family is finished before a new
		#one is opened
		self.assertTrue(q.started(after))

	def test_an_empty_queue_says_so_rather_than_raising(self):
		q.families = lambda state='open': []
		self.assertIsNone(q.next_table())


if __name__ == '__main__':
	unittest.main(verbosity=1)
