"""A table holds one named quantity; a parameter indexes arguments.

The skill has said so since the corpus was small -- "where several named
objects share a subject but not a name, make several tables", "seven functions
evaluated at the same rational $x$ are still seven functions" -- and ten of
the sixteen tables built in one week said the opposite with a parameter:
`form: ehrhart | h-star`, `quantity: psi | H`, `form: generating | signed`.
A rule that is only written gets followed until a build is in a hurry.

The tell is structural, so no prose is read: a parameter taking a handful of
names, orthogonal to every other parameter, is the same table copied once per
name. The good answers to that question -- one object in several parts, one
number in several conventions -- are what the exceptions below pin.
"""
from django.test import TestCase

from .editing import create_table
from .management.commands.audit_table import findings_for
from .models import Table


def splitting(findings):
	return [f for f in findings if 'sharing one title' in f]


class OneNamedQuantityPerTable(TestCase):

	def table(self, title, params, entries, header=None, published=False):
		tree = {'Title': title,
		        'Definition': 'These numbers, for a reason.',
		        'Data properties': {'type': 'R'},
		        'Parameters': {name: {'type': 'Symbolic'} for name in params},
		        'Numbers': [{'params': p, 'number': v} for p, v in entries]}
		if header:
			tree['Display properties'] = {'number-header': header}
		create_table(tree, via='orm')
		table = Table.objects.get(title=title)
		#`create_table` publishes, and this check asks only drafts, so the
		#state has to be set either way rather than only for the published
		#case -- which is what made the first version of these tests pass
		#nothing at all.
		table.published = published
		table.save(update_fields=['published'])
		return table

	def grid(self, index, names, labels):
		return [({index: str(n), names: label}, '%d.%d' % (n, i))
		        for n in range(1, 7) for i, label in enumerate(labels)]

	def test_two_quantities_under_one_title_are_reported(self):
		table = self.table('Ehrhart and h-star polynomials of something',
		                   ['n', 'form'],
		                   self.grid('n', 'form', ['ehrhart', 'h-star']))
		found = splitting(findings_for(table))
		self.assertEqual(len(found), 1, found)
		self.assertIn('form', found[0])
		self.assertIn('ehrhart', found[0])

	def test_a_numeric_parameter_is_an_index_and_not_a_name(self):
		#nu = 0, 1, 2 is one function at three orders, and T187 is right to
		#hold them together. This is the difference the check turns on.
		table = self.table('Values of a function', ['x', 'nu'],
		                   self.grid('x', 'nu', ['0', '1', '2']))
		self.assertEqual(splitting(findings_for(table)), [])

	def test_a_parameter_that_indexes_many_things_is_not_two_tables(self):
		#78 root systems or 22 distributions index a family; they do not
		#choose between a few quantities.
		entries = [({'n': str(n), 'type': 'A%d' % k}, '%d.%d' % (n, k))
		           for n in range(1, 4) for k in range(2, 12)]
		table = self.table('Something by root system', ['n', 'type'], entries)
		self.assertEqual(splitting(findings_for(table)), [])

	def test_a_label_carrying_one_entry_is_an_index_not_a_table(self):
		#A parameter whose values each hold a single row is naming objects,
		#not quantities: four distributions with one shape apiece is one
		#table of entropies, not four tables.
		entries = [({'d': 'normal', 'shape': '-'}, '1.0'),
		           ({'d': 'beta', 'shape': '1,1'}, '2.0'),
		           ({'d': 'cauchy', 'shape': '1'}, '4.0'),
		           ({'d': 'gamma', 'shape': '2'}, '5.0')]
		table = self.table('Something by distribution', ['d', 'shape'], entries)
		self.assertEqual(splitting(findings_for(table)), [])

	def test_it_asks_about_a_small_named_index_too_and_that_is_the_cost(self):
		#Honest about the false positives. Nothing structural separates
		#"three distributions, several shapes each" from "three quantities,
		#several n each" -- only what the names mean -- so the check asks and
		#a person answers. Missing T262 was worse than asking twice.
		entries = [({'d': d, 'shape': s}, '%s.%s' % (d, s))
		           for d in ('normal', 'beta', 'gamma')
		           for s in ('1', '2')]
		table = self.table('Something by three distributions',
		                   ['d', 'shape'], entries)
		self.assertEqual(len(splitting(findings_for(table))), 1)

	def test_a_shorter_range_under_one_name_does_not_disarm_it(self):
		#T262 held the $q,t$-Catalan numbers to n=6 and each of the two
		#specialisations to n=11, so the grid was ragged and the check --
		#which demanded every combination under every label -- stood down on
		#a table that was three tables. How far a quantity happens to have
		#been computed says nothing about whether it is the same quantity.
		entries = ([({'n': str(n), 'which': 'qt'}, '%d.0' % n)
		            for n in range(1, 5)]
		           + [({'n': str(n), 'which': 'carlitz'}, '%d.1' % n)
		              for n in range(1, 10)]
		           + [({'n': str(n), 'which': 'macmahon'}, '%d.2' % n)
		              for n in range(1, 10)])
		table = self.table('Something and its two specialisations',
		                   ['n', 'which'], entries)
		found = splitting(findings_for(table))
		self.assertEqual(len(found), 1, found)
		self.assertIn('which', found[0])

	def test_a_published_table_is_not_asked_again(self):
		#It was read and accepted as it is. Re-litigating that on every audit
		#is the fastest way to have a check turned off, and a published table
		#that grows a bundled parameter is caught in review, where the diff is
		#what a person reads.
		table = self.table('Nodes and weights of some quadrature',
		                   ['n', 'expression'],
		                   self.grid('n', 'expression', ['w', 'x']),
		                   published=True)
		self.assertEqual(splitting(findings_for(table)), [])


class TheValueColumnNamesTheQuantity(TestCase):

	def table(self, header):
		title = 'A table headed %s' % header
		create_table({'Title': title,
		              'Definition': 'These numbers, for a reason.',
		              'Data properties': {'type': 'R'},
		              'Parameters': {'n': {'type': 'Z'}},
		              'Display properties': {'number-header': header},
		              'Numbers': [{'params': {'n': '1'}, 'number': '1.5'}]},
		             via='orm')
		table = Table.objects.get(title=title)
		table.published = False
		table.save(update_fields=['published'])
		return table

	def headers(self, findings):
		return [f for f in findings if 'names no quantity' in f]

	def test_a_column_headed_value_is_reported(self):
		#A table of one thing can name it. A table of two falls back on a
		#word, because no symbol is true of every row -- which is how the
		#bundled tables were spotted by eye in the first place.
		self.assertEqual(len(self.headers(findings_for(self.table('value')))), 1)

	def test_a_column_headed_with_a_symbol_is_not(self):
		found = self.headers(findings_for(self.table('$\\gamma_K$')))
		self.assertEqual(found, [])


class ALabelMayNotStandWhereANumberShould(TestCase):
	"""`param-latex` replaces the label of its own parameter group.

	On a parameter whose values are words that is the point: `normalisation:
	relative` reads better as the symbol for that volume. On a numeric
	parameter the value *is* the label, and replacing it hides what the row
	is -- the hypersimplex tables put `$L_{\\Delta(2,4)}(t)$` in the column
	that should have read `2`, which is the table's own header restated once
	per row.
	"""

	def table(self, title, last_type, labelled):
		tree = {'Title': title,
		        'Definition': 'These numbers, for a reason.',
		        'Data properties': {'type': 'R'},
		        'Parameters': {'n': {'type': 'Z'}, 'which': {'type': last_type}},
		        'Numbers': []}
		for n in range(1, 5):
			for i, which in enumerate(('2', '3') if last_type == 'Z'
			                          else ('first', 'second')):
				entry = {'params': {'n': str(n), 'which': which},
				         'number': '%d.%d' % (n, i)}
				if labelled:
					entry['param-latex'] = '$f_{%s,%s}(t)$' % (which, n)
				tree['Numbers'].append(entry)
		create_table(tree, via='orm')
		table = Table.objects.get(title=title)
		table.published = False
		table.save(update_fields=['published'])
		return table

	def labels(self, findings):
		return [f for f in findings if 'param-latex' in f]

	def test_a_label_over_a_numeric_parameter_is_reported(self):
		table = self.table('Something indexed by two numbers', 'Z', True)
		found = self.labels(findings_for(table))
		self.assertEqual(len(found), 1, found)
		self.assertIn('which', found[0])

	def test_a_label_over_a_word_parameter_is_not(self):
		#The normalisations of the Birkhoff volumes are the case this is for.
		table = self.table('Something in two conventions', 'Symbolic', True)
		self.assertEqual(self.labels(findings_for(table)), [])

	def test_a_table_with_no_labels_is_not_reported(self):
		table = self.table('Something plain', 'Z', False)
		self.assertEqual(self.labels(findings_for(table)), [])
