"""Making a table from a title.

The page used to ask for a whole YAML document and publish it on save. Both
asked for everything before anything could be looked at: a title is all that
is genuinely needed, because it is what the address is built from, and
nothing about a draft is frozen -- not even its parameters -- so the rest is
better decided in the editor, next to the entries that motivate it.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Table


class ATitleIsEnoughToBegin(TestCase):

	def setUp(self):
		self.user = get_user_model().objects.create_user('maker')
		self.client = Client()
		self.client.force_login(self.user)

	def create(self, **fields):
		fields.setdefault('form', 'simple')
		return self.client.post(reverse('db:new-table'), fields,
		                        HTTP_HOST='numberdb.org')

	def test_a_title_alone_makes_a_table(self):
		response = self.create(title='Zeros of the Airy function Ai')
		table = Table.objects.get(title='Zeros of the Airy function Ai')
		self.assertEqual(response.status_code, 302)
		self.assertIn(table.tid, response['Location'])

	def test_it_is_a_draft(self):
		#So a half-written table is not published to anybody meanwhile.
		self.create(title='A new family')
		self.assertFalse(Table.objects.get(title='A new family').published)

	def test_it_lands_in_the_editor(self):
		response = self.create(title='Another family')
		table = Table.objects.get(title='Another family')
		self.assertEqual(response['Location'],
		                 reverse('db:edit-table', kwargs={'tid': table.tid}))

	def test_the_definition_is_kept_when_given(self):
		from .editing import tree_of
		self.create(title='With a definition',
		            definition='The list contains the things.')
		table = Table.objects.get(title='With a definition')
		self.assertEqual(tree_of(table.head_revision).get('Definition'),
		                 'The list contains the things.')

	def test_the_definition_is_optional(self):
		from .editing import tree_of
		self.create(title='Without a definition')
		table = Table.objects.get(title='Without a definition')
		self.assertNotIn('Definition', tree_of(table.head_revision))

	def test_a_title_of_spaces_is_refused(self):
		self.create(title='   ')
		self.assertFalse(Table.objects.filter(published=False).exists())

	def test_the_parameters_may_still_change_afterwards(self):
		#The reason the form does not ask for them. Nothing is frozen while a
		#table is a draft; the freeze protects citations, and a draft has none.
		from .editing import commit_table, tree_of
		self.create(title='Parameters later')
		table = Table.objects.get(title='Parameters later')
		tree = tree_of(table.head_revision)
		tree['Parameters'] = {'n': {'type': 'Z'}}
		commit_table(table, tree, author=self.user, message='add n')
		tree = tree_of(Table.objects.get(pk=table.pk).head_revision)
		tree['Parameters'] = {'m': {'type': 'Z'}, 'k': {'type': 'Z'}}
		commit_table(table, tree, author=self.user, message='rename and add')
		table.refresh_from_db()
		self.assertEqual(list(tree_of(table.head_revision)['Parameters']),
		                 ['m', 'k'])

	def test_parameter_names_are_kept(self):
		#What fixes the shape of the entry form: the columns an entry is
		#identified by are the declared parameters.
		from .editing import tree_of
		self.create(title='Indexed by two things', parameters='n, alpha')
		table = Table.objects.get(title='Indexed by two things')
		self.assertEqual(list(tree_of(table.head_revision)['Parameters']),
		                 ['n', 'alpha'])

	def test_parameters_may_be_separated_by_spaces(self):
		from .editing import tree_of
		self.create(title='Spaces between', parameters='n k')
		table = Table.objects.get(title='Spaces between')
		self.assertEqual(list(tree_of(table.head_revision)['Parameters']),
		                 ['n', 'k'])

	def test_no_parameters_leaves_the_section_out(self):
		#Rather than an empty Parameters section nobody asked for.
		from .editing import tree_of
		self.create(title='No parameters at all')
		table = Table.objects.get(title='No parameters at all')
		self.assertNotIn('Parameters', tree_of(table.head_revision))

	def test_a_declared_parameter_needs_no_type_to_be_valid(self):
		#Which is why only the names are asked for here.
		from .validate import check
		self.assertEqual(check({'Title': 'A table', 'Numbers': {'1': '2'},
		                        'Parameters': {'n': {}}}), [])
