"""A reference identifier is text, in the corpus, where it is read from.

`arxiv: 0705.4325` without quotes is the float 705.4325 by the time YAML has
finished with it: the leading zero, which is the year, is gone. `zbl:
0668.12001` goes the same way.

This used to check the YAML files under `generators/`, which is the wrong
artefact. Those are working copies; what a reader follows is the table on the
site, and what a citation resolves against is the stored document. A repository
copy can be wrong while every table is right -- which is exactly what was true
when this was written -- and a table can be wrong while the repository is
right, which no test over files would ever see.
"""

from django.test import TestCase

from .models import Table
from .validate import malformed_identifiers

#: Fields whose value is an identifier rather than a quantity. Every one of
#: them can begin with a zero, and several routinely do.
IDENTIFIER_FIELDS = ('arxiv', 'mr', 'zbl', 'doi', 'isbn')


class StoredIdentifiersAreText(TestCase):
	"""The rule, on a constructed table.

	The corpus itself is swept by `manage.py audit_table`, which runs against
	the real database. A sweep here would run against the test database, which
	is empty, and pass for ever without looking at anything.
	"""

	def setUp(self):
		from django.contrib.auth import get_user_model

		self.user = get_user_model().objects.create_user('author')
		self.table = Table.objects.create(
			tid='T700', tid_int=700, url='t700', title='A table',
			published=True)

	def stored(self, references):
		from .editing import commit_table

		commit_table(self.table,
		             {'Title': 'A table', 'Numbers': {'1': '2'},
		              'References': references},
		             author=self.user, message='m', via='orm')
		self.table.refresh_from_db()
		return self.table.data.json.get('References') or {}

	def numeric(self, references):
		return [('%s.%s' % (label, field), value)
		        for label, body in references.items()
		        if isinstance(body, dict)
		        for field in IDENTIFIER_FIELDS
		        for value in [body.get(field)]
		        if value is not None and not isinstance(value, str)]

	def test_quoted_identifiers_survive_the_round_trip(self):
		stored = self.stored({'R': {'bib': 'A paper', 'arxiv': '0705.4325',
		                            'zbl': '0668.12001'}})
		self.assertEqual(stored['R']['arxiv'], '0705.4325')
		self.assertEqual(malformed_identifiers({'References': stored}), [])

	def test_the_site_stores_a_number_as_text_with_the_zero_already_gone(self):
		#Which is why a type check cannot find this: by the time it is stored
		#it is a string, correctly typed and quietly wrong.
		stored = self.stored({'R': {'bib': 'A paper', 'arxiv': 705.4325}})
		self.assertEqual(stored['R']['arxiv'], '705.4325')
		self.assertIsInstance(stored['R']['arxiv'], str)

	def test_the_shape_catches_what_the_type_cannot(self):
		stored = self.stored({'R': {'bib': 'A paper', 'arxiv': 705.4325}})
		found = malformed_identifiers({'References': stored})
		self.assertEqual([(label, field) for label, field, _, _ in found],
		                 [('R', 'arxiv')])

	def test_an_old_style_arxiv_identifier_is_left_alone(self):
		#math/0309285 is a real identifier and matches no modern shape.
		found = malformed_identifiers(
			{'References': {'R': {'arxiv': 'math/0309285'}}})
		self.assertEqual(found, [])

	def test_the_failure_this_guards_against(self):
		#The mechanism itself: the file on disk is right and the parse is not.
		import yaml
		loose = yaml.safe_load('References:\n  R:\n    arxiv: 0705.4325\n')
		self.assertEqual(loose['References']['R']['arxiv'], 705.4325)
		quoted = yaml.safe_load("References:\n  R:\n    arxiv: '0705.4325'\n")
		self.assertEqual(quoted['References']['R']['arxiv'], '0705.4325')
