"""Looking a number up with a malformed record.

This is the one thing the site is for, and a record with the wrong field
names used to raise KeyError out of the decoder and answer 500 with an empty
body -- so somebody who mistyped a field learned nothing at all.
"""

import json

from django.test import Client, TestCase

from utils.number_json import UnsupportedNumber, decode_number


class AMalformedRecordSaysWhatIsMissing(TestCase):

	def test_a_real_interval_needs_bounds_not_a_value(self):
		with self.assertRaises(UnsupportedNumber) as caught:
			decode_number({'kind': 'RIF', 'value': '1.46'})
		message = str(caught.exception)
		self.assertIn('lower', message)
		self.assertIn('upper', message)

	def test_an_unknown_kind_lists_the_known_ones(self):
		with self.assertRaises(UnsupportedNumber) as caught:
			decode_number({'kind': 'R', 'value': '1.46'})
		self.assertIn('RIF', str(caught.exception))

	def test_a_complex_interval_names_all_four_bounds(self):
		with self.assertRaises(UnsupportedNumber) as caught:
			decode_number({'kind': 'CIF', 're_lower': '1'})
		self.assertIn('im_lower', str(caught.exception))

	def test_a_well_formed_record_still_decodes(self):
		value = decode_number({'kind': 'RIF', 'lower': '1.4', 'upper': '1.5'})
		self.assertTrue(1.46 in value)


class TheLookupEndpointAnswersRatherThanFailing(TestCase):

	def ask(self, record):
		return Client().get('/api/lookup', {'number': json.dumps(record)},
		                    HTTP_HOST='numberdb.org')

	def test_a_malformed_record_is_not_a_server_error(self):
		response = self.ask({'kind': 'RIF', 'value': '1.46'})
		self.assertNotEqual(response.status_code, 500)
		self.assertIn(b'lower', response.content)

	def test_an_unknown_kind_is_not_a_server_error(self):
		response = self.ask({'kind': 'nonsense', 'value': '1'})
		self.assertNotEqual(response.status_code, 500)
