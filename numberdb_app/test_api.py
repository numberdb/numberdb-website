"""Looking a table up through the API."""

from django.test import TestCase


class ATableIsFoundByNumberOrByAddress(TestCase):
	"""Both names a person might be holding.

	A table has a number and an address its title makes, and somebody reading
	`numberdb.org/Cyclotomic_polynomials` has the second one. Passing it as
	`id` used to reach `int()` and leave as HTTP 500 -- a crash, not an answer,
	and the only clue that the lookup wanted a different parameter.
	"""

	def setUp(self):
		from .editing import create_table

		self.table = create_table(
			{'Title': 'Cyclotomic polynomials of a sort',
			 'Data properties': {'type': 'Z[]'},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': 'x - 1'}]},
		via='orm')

	def ask(self, **parameters):
		return self.client.get('/api/table', parameters)

	def test_by_number(self):
		answer = self.ask(id=self.table.tid)
		self.assertEqual(answer.status_code, 200)
		self.assertEqual(answer.json()['Title'], self.table.title)

	def test_by_number_without_the_letter(self):
		answer = self.ask(id=self.table.tid.lstrip('T'))
		self.assertEqual(answer.json()['Title'], self.table.title)

	def test_by_address_passed_as_id(self):
		answer = self.ask(id=self.table.url)
		self.assertEqual(answer.status_code, 200)
		self.assertEqual(answer.json()['Title'], self.table.title)

	def test_by_address_passed_as_url(self):
		#The parameter that always worked, and still does.
		answer = self.ask(url=self.table.url)
		self.assertEqual(answer.json()['Title'], self.table.title)

	def test_an_address_nobody_has_is_an_error_not_a_crash(self):
		answer = self.ask(id='No_such_table_here')
		self.assertEqual(answer.status_code, 200)
		self.assertIn('error', answer.json())
		self.assertIn('No_such_table_here', answer.json()['error'])

	def test_a_number_nobody_has_is_an_error_not_a_crash(self):
		answer = self.ask(id='T999999')
		self.assertIn('error', answer.json())

	def test_something_that_is_neither_does_not_crash(self):
		for nonsense in ('', '../etc/passwd', 'T', '12x', '%%%'):
			with self.subTest(given=nonsense):
				answer = self.ask(id=nonsense)
				self.assertEqual(answer.status_code, 200, nonsense)
				self.assertIn('error', answer.json())
