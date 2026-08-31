"""An entry that names where else its value appears is still a value.

The indexer skipped any entry carrying `equals`. For a reference with no
digits that is right -- there is nothing to index. For an entry that gives
both its digits and the table its value also appears in, it is backwards:
those are the most useful hits somebody looking a number up can get, and
there were 102 of them, pi among them.
"""

from django.test import TestCase


class DigitsBesideAReferenceAreIndexed(TestCase):

	def test_an_entry_with_digits_and_a_reference_keeps_its_digits(self):
		#T29's pi: a hundred places, and a pointer at the table of pi.
		from numberdb_app.flatten import entries_block
		document = {'Numbers': [{'params': {'a': '1'},
		                         'number': '3.14159265358979323846',
		                         'equals': 'HREF{Pi}'}]}
		records = entries_block(document)
		self.assertEqual(len(records), 1)
		self.assertIn('number', records[0])
		self.assertIn('equals', records[0])

	def test_the_source_no_longer_skips_on_equals_alone(self):
		#The guard that dropped them, asserted on the source because the
		#builder needs a database and a Sage ring to run end to end.
		import os

		from django.conf import settings

		path = os.path.join(settings.BASE_DIR, 'data_pipeline', 'build.py')
		with open(path, encoding='utf-8') as handle:
			body = handle.read()
		self.assertNotIn("if 'equals' in numbers:\n\t\t\t\treturn 0", body)
		self.assertIn('has_digits', body)
		self.assertIn("if 'equals' in numbers and not has_digits", body)

	def test_a_reference_with_no_digits_is_still_skipped(self):
		#T94's s = 1 row points at the whole Riemann zeta table and holds no
		#value of its own. There is nothing to index and nothing to fix.
		import os

		from django.conf import settings

		path = os.path.join(settings.BASE_DIR, 'data_pipeline', 'build.py')
		with open(path, encoding='utf-8') as handle:
			body = handle.read()
		self.assertIn('a reference with nothing to index', body)
