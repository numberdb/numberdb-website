"""One row per number, where two tables hold it for the same reason.

Three lattice tables hold the centre density of the Leech lattice. Two of them
hold it *because* the third does: the densest-known table's value for dimension
24 is the value the family table lists for the Leech lattice, transcribed
rather than recomputed. A reader who types those digits is answered once.

What is deliberately not folded is the case that looks identical in the data:
Hermite's constant in dimension 8 equals the Hermite number of $E_8$ because
somebody proved the supremum is attained there. Two constructions meeting is
most of what a database of constants is for, and nothing in the values tells
the two cases apart -- so the tables declare which they are, and search reads
the declaration rather than guessing from equality.
"""

from django.test import TestCase

from .models import Number, Table


class Repetitions(TestCase):

	def setUp(self):
		self.original = self.table(0, 'Classical lattices')
		self.copy = self.table(1, 'Densest known packings')
		self.other = self.table(2, "Hermite's constants")

	def table(self, i, title):
		return Table.objects.create(
			tid='T81%d' % i, tid_int=810 + i, url='t81%d' % i,
			title=title, published=True)

	def store(self, table, text='0.001929', low=1.0, high=1.0):
		return Number.objects.create(
			table=table, lower=low, upper=high, frac_lower=0.0,
			frac_upper=0.0, exact_relative_width=0.0, reviewed=True,
			exact_text=text)

	def search(self, limit=10):
		from .search import one_per_table

		return one_per_table(Number.objects.filter(lower=1.0), limit)

	def tables_found(self, rows):
		return {row.table_id for row in rows}

	def test_a_declared_repetition_folds_into_its_original(self):
		self.copy.repeats = self.original
		self.copy.save(update_fields=['repeats'])
		self.store(self.original)
		self.store(self.copy)
		rows = self.search()
		self.assertEqual(self.tables_found(rows), {self.original.pk})

	def test_the_folded_table_is_still_named(self):
		self.copy.repeats = self.original
		self.copy.save(update_fields=['repeats'])
		self.store(self.original)
		self.store(self.copy)
		[row] = self.search()
		self.assertEqual([t.pk for t in row.also_in], [self.copy.pk])

	def test_equality_alone_folds_nothing(self):
		"""$\\gamma_8 = \\gamma(E_8)$ is a theorem, and both rows stay."""
		self.store(self.original)
		self.store(self.other)
		rows = self.search()
		self.assertEqual(self.tables_found(rows),
		                 {self.original.pk, self.other.pk})

	def test_a_repetition_holding_a_different_value_stays(self):
		#The declaration is about the tables; the fold is about one number.
		#Where they do not agree there is nothing to fold.
		self.copy.repeats = self.original
		self.copy.save(update_fields=['repeats'])
		self.store(self.original, text='0.001929')
		self.store(self.copy, text='0.002127')
		rows = self.search()
		self.assertEqual(self.tables_found(rows),
		                 {self.original.pk, self.copy.pk})

	def test_the_copy_stands_alone_when_the_original_is_not_an_answer(self):
		#Folding may not remove the only answer: if the original table holds
		#no matching value, the copy is what there is to say.
		self.copy.repeats = self.original
		self.copy.save(update_fields=['repeats'])
		self.store(self.copy)
		rows = self.search()
		self.assertEqual(self.tables_found(rows), {self.copy.pk})

	def test_a_value_with_no_stored_text_is_never_folded(self):
		#Empty text means the value could not be written faithfully, and two
		#empties are not evidence of anything.
		self.copy.repeats = self.original
		self.copy.save(update_fields=['repeats'])
		self.store(self.original, text='')
		self.store(self.copy, text='')
		rows = self.search()
		self.assertEqual(self.tables_found(rows),
		                 {self.original.pk, self.copy.pk})


class TheRelationStaysShallow(TestCase):
	"""A table that is repeated may not repeat a third.

	Depth one is what lets a fold resolve in a single lookup, and it is also
	what makes a cycle impossible: every table in a cycle would have to both
	repeat and be repeated.
	"""

	def setUp(self):
		self.a = Table.objects.create(tid='T820', tid_int=820, url='t820',
		                              title='A', published=True)
		self.b = Table.objects.create(tid='T821', tid_int=821, url='t821',
		                              title='B', published=True)
		self.c = Table.objects.create(tid='T822', tid_int=822, url='t822',
		                              title='C', published=True)

	def sync(self, table, slug):
		from .editing import _sync_repeats

		_sync_repeats(table, {'Data properties':
		                       {'repeats': 'HREF{%s}' % (slug,)}})
		table.refresh_from_db()

	def test_a_declaration_is_recorded(self):
		self.sync(self.b, 't820')
		self.assertEqual(self.b.repeats_id, self.a.pk)

	def test_a_caption_after_the_reference_is_ignored(self):
		from .editing import _repeats_slug

		self.assertEqual(_repeats_slug('HREF{t820}[Table A]'), 't820')

	def test_an_entry_reference_names_the_table(self):
		from .editing import _repeats_slug

		#The claim is about two tables, so a `#entry` is narrower than the
		#field can mean and the table is what is taken from it.
		self.assertEqual(_repeats_slug('HREF{t820#n=24}'), 't820')

	def test_a_table_cannot_repeat_itself(self):
		self.sync(self.a, 't820')
		self.assertIsNone(self.a.repeats_id)

	def test_a_chain_is_refused(self):
		self.sync(self.b, 't820')
		self.sync(self.c, 't821')
		self.assertIsNone(self.c.repeats_id)

	def test_a_table_that_is_repeated_cannot_become_a_repetition(self):
		self.sync(self.b, 't820')
		self.sync(self.a, 't822')
		self.assertIsNone(self.a.repeats_id)

	def test_a_cycle_cannot_be_declared(self):
		self.sync(self.b, 't820')
		self.sync(self.a, 't821')
		self.assertIsNone(self.a.repeats_id)
		self.assertEqual(self.b.repeats_id, self.a.pk)

	def test_an_unknown_table_leaves_it_unset(self):
		self.sync(self.b, 'no_such_table')
		self.assertIsNone(self.b.repeats_id)

	def test_a_removed_declaration_clears_the_field(self):
		from .editing import _sync_repeats

		self.sync(self.b, 't820')
		_sync_repeats(self.b, {'Data properties': {}})
		self.b.refresh_from_db()
		self.assertIsNone(self.b.repeats_id)
