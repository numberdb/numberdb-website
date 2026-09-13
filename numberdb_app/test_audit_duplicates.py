"""The audit looks for the same numbers under another title.

T219 and T225 were nearly the same table -- volumes of hyperbolic 3-manifolds,
one census each -- and the person who noticed was the person reading the site,
not any check. The titles share no distinctive word, so nothing that reads
prose could have found it. The numbers are the same numbers, and this database
can look those up.
"""
from django.test import TestCase

from .editing import create_table
from .management.commands.audit_table import findings_for
from .models import Number, Table


def duplicate_findings(findings):
	return [f for f in findings if 'values sampled here' in f]


VOLUMES = ['2.0298832128193', '2.5689706009', '2.9441064866', '3.1772932501',
           '3.3317944998', '3.4741205', '3.6638623']


class TheSameNumbersUnderAnotherTitle(TestCase):

	def table(self, title, values, extra=None):
		tree = {'Title': title,
		        'Definition': 'These numbers, for a reason.',
		        'Data properties': {'type': 'R'},
		        'Parameters': {'n': {'type': 'Z'}},
		        'Numbers': [{'params': {'n': str(i)}, 'number': v}
		                    for i, v in enumerate(values)]}
		if extra:
			tree.update(extra)
		create_table(tree, via='orm')
		table = Table.objects.get(title=title)
		table.published = True
		table.save(update_fields=['published'])
		#Search by digits answers only from reviewed rows of published tables
		#(`_identifiable` in search.py), which is the state a real corpus is
		#in and the state this check compares a new table against.
		Number.objects.filter(table=table).update(reviewed=True)
		return table

	def test_a_table_of_the_same_values_is_reported(self):
		first = self.table('Volumes of one census', VOLUMES)
		other = self.table('Volumes of another census', VOLUMES)
		found = duplicate_findings(findings_for(other))
		self.assertEqual(len(found), 1, found)
		self.assertIn(first.tid, found[0])

	def test_a_table_that_already_says_so_is_not_reported(self):
		#The answer to a real overlap is a line in Similar tables saying how
		#the two differ. Once it is there, repeating the finding is noise, and
		#noise is how a check comes to be ignored.
		first = self.table('Volumes of one census', VOLUMES)
		other = self.table(
			'Volumes of another census', VOLUMES,
			{'Similar tables': [
				{'table': 'HREF{%s}[Volumes of one census]' % first.url,
				 'relation': 'holds the same manifolds by another census'}]})
		self.assertEqual(duplicate_findings(findings_for(other)), [])

	def test_tables_that_share_a_value_or_two_are_not_reported(self):
		#Zero, one and pi are in everything. A check that reported those would
		#be turned off within a week.
		self.table('Some constants',
		           ['1.0', '2.0', '3.14159265358979', '7.3890560989',
		            '20.085536923187', '54.598150033144', '148.41315910258'])
		other = self.table('Other constants',
		                   ['1.0', '2.0', '1.7724538509055', '1.2020569031595',
		                    '2.6854520010653', '4.6692016091029',
		                    '0.91596559417721'])
		self.assertEqual(duplicate_findings(findings_for(other)), [])

	def test_a_table_too_small_to_judge_is_left_alone(self):
		self.table('One value', ['1.7724538509055'])
		other = self.table('The same one value', ['1.7724538509055'])
		self.assertEqual(duplicate_findings(findings_for(other)), [])

	def test_small_integers_are_not_evidence_however_many_agree(self):
		#The highest known ranks of elliptic curves are 28, 20, 15, 13, 9, and
		#the values of Dedekind zeta functions at negative odd integers include
		#those too. The first version of this check announced that one of the
		#two tables should not exist. Small numbers collide because there are
		#not many of them.
		ranks = ['28', '20', '19', '15', '13', '9', '6', '3']
		self.table('Highest known ranks', ranks)
		other = self.table('Small values of something else', ranks)
		self.assertEqual(duplicate_findings(findings_for(other)), [])

	def test_large_exact_values_are_evidence(self):
		#Singular moduli are j-invariants, and the corpus holds both. Nothing
		#hits -884736000 by accident.
		moduli = ['-884736000', '-147197952000', '-262537412640768000',
		          '54000', '287496', '16581375', '-3375', '8000']
		first = self.table('Rational singular moduli', moduli)
		other = self.table('$j$-invariants with good reduction', moduli)
		found = duplicate_findings(findings_for(other))
		self.assertEqual(len(found), 1, found)
		self.assertIn(first.tid, found[0])
