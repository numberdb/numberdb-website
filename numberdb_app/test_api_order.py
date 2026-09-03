"""The API serves a table's document in the order the table stores it.

`TableData.json` is a jsonb column and Postgres jsonb does not keep the order
of an object's keys -- it stores them by length, then bytewise. So a table
whose parameters are `n, k, expression` was served as `k, n, expression`.

Not cosmetic. An entry's identity is its parameter values, so reordering them
reassigns every identity in the table, and `write_table` refuses the write:
anyone reading a table through this API, changing it and writing it back got
a 409 they could not fix from outside. T135 hit exactly that. T128 shows the
other half of the same fault: entries running 5, 8, -3, -4, 12 -- by width,
then bytes -- an order that came back through the API and was stored.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .editing import commit_table
from .models import Table


class TheDocumentKeepsItsOrder(TestCase):

	def setUp(self):
		self.user = get_user_model().objects.create_user('reader')
		self.table = Table.objects.create(
			tid='T800', tid_int=800, url='t800', title='A table',
			published=True)

	def served(self, tree):
		commit_table(self.table, tree, author=self.user, message='m',
		             via='orm')
		response = Client().get('/api/table?id=T800', HTTP_HOST='numberdb.org')
		self.assertEqual(response.status_code, 200)
		return response.json()

	def test_parameters_keep_the_order_they_were_written_in(self):
		#jsonb would give k, n, expression: shortest first, then bytewise.
		document = self.served({
			'Title': 'A table',
			'Parameters': {'n': {'type': 'Z'}, 'k': {'type': 'Z'},
			               'expression': {'type': 'Z'}},
			'Numbers': {'1': {'1': {'1': '2'}}},
		})
		self.assertEqual(list(document['Parameters']),
		                 ['n', 'k', 'expression'])

	def test_entries_keep_the_order_they_were_written_in(self):
		#T128's case: signed values, where width-then-bytes puts every
		#negative after the positives of the same width.
		document = self.served({
			'Title': 'A table',
			'Parameters': {'D': {'type': 'Z'}},
			'Numbers': {'5': '1.1', '8': '1.2', '-3': '1.3', '-4': '1.4',
			            '12': '1.5'},
		})
		self.assertEqual(list(document['Numbers']),
		                 ['5', '8', '-3', '-4', '12'])

	def test_the_sections_keep_their_order(self):
		document = self.served({
			'Title': 'A table', 'Definition': 'd',
			'Numbers': {'1': '2'}, 'Comments': {'c': 'a comment'},
		})
		keys = [k for k in document if k in
		        ('Title', 'Definition', 'Numbers', 'Comments')]
		self.assertEqual(keys, ['Title', 'Definition', 'Numbers', 'Comments'])

	def test_what_it_serves_can_be_written_back(self):
		"""The whole point: read, change nothing, write, and be accepted."""
		tree = {
			'Title': 'A table',
			'Parameters': {'n': {'type': 'Z'}, 'k': {'type': 'Z'},
			               'expression': {'type': 'Z'}},
			'Numbers': {'1': {'1': {'1': '2'}}},
		}
		served = self.served(tree)

		#Writing through the API opens after five accepted edits. The board
		#has that standing from the start, which is what the concurrency
		#tests use; the point here is the 409, not the 403.
		from django.contrib.auth.models import Group

		from .models import ApiKey
		from .permissions import BOARD_GROUP
		self.user.groups.add(Group.objects.get_or_create(name=BOARD_GROUP)[0])
		_key, token = ApiKey.issue(user=self.user, label='round trip')
		import yaml
		response = Client().post(
			'/api/table/T800', yaml.dump(served, sort_keys=False),
			content_type='application/yaml', HTTP_HOST='numberdb.org',
			HTTP_AUTHORIZATION='Bearer %s' % (token,))
		self.assertNotEqual(response.status_code, 409, response.content)
		self.assertEqual(response.status_code, 200, response.content)

	def test_the_values_are_still_there(self):
		document = self.served({
			'Title': 'A table', 'Definition': 'what it is',
			'Numbers': {'1': '2'},
		})
		self.assertEqual(document['Definition'], 'what it is')
		self.assertEqual(document['Title'], 'A table')


class ThePageDoesNotCarryACopyOfTheDocument(TestCase):
	"""167 KB of T128's 566 KB page was a commented-out copy of its own data.

	30% of every byte served, to every reader, for a debugging aid that nobody
	reads in a browser -- and it made a test of mine pass for the wrong reason
	once, since the words were on the page whether or not the section that
	should show them was drawn.
	"""

	def setUp(self):
		self.user = get_user_model().objects.create_user('author')
		self.table = Table.objects.create(
			tid='T801', tid_int=801, url='t801', title='A table',
			published=True)

	def page(self, tree):
		commit_table(self.table, tree, author=self.user, message='m',
		             via='orm')
		return Client().get('/T801', HTTP_HOST='numberdb.org').content.decode()

	def test_the_document_is_not_dumped_into_a_comment(self):
		body = self.page({'Title': 'A table', 'Numbers': {'1': '2'},
		                  'Comments': {'c': 'a distinctive sentence'}})
		self.assertNotIn('<hr>Data:', body)

	def test_a_section_the_page_does_not_draw_is_not_on_the_page(self):
		#`Keywords` is not a rendered section. It used to reach the reader
		#anyway, inside the dump.
		body = self.page({'Title': 'A table', 'Numbers': {'1': '2'},
		                  'Keywords': 'sesquipedalian'})
		self.assertNotIn('sesquipedalian', body)

	def test_the_page_still_shows_what_it_should(self):
		body = self.page({'Title': 'A table', 'Numbers': {'1': '2'},
		                  'Comments': {'c': 'a distinctive sentence'}})
		self.assertIn('a distinctive sentence', body)
