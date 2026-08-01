"""The API must not ask its clients to unpickle anything.

The payload used to carry ``value.dumps()`` -- a Sage pickle -- and the shipped
client called ``loads()`` on it. Unpickling runs whatever the bytes say, so
every consumer executed code chosen by whoever answered the request. It also
tied the wire format to Sage: the bytes are Sage objects, so no client without
Sage could read a number and the server could not stop producing them.

Run inside the web container:

    docker compose exec -T web sage -python manage.py test numberdb_app.test_api_wire
"""

import importlib.util
import json

from django.test import TestCase
from sage.rings.all import CIF, QQ, RBF, RIF, ZZ, Qp

from .models import Number, NumberComplex, NumberPAdic, Polynomial, Table
from utils.number_json import decode_number, encode_number

CLIENT_PATH = '/app/clients/sage/numberdb-sage-interface.py'


def _client():
	"""The shipped client, loaded from the file users actually get."""
	spec = importlib.util.spec_from_file_location('nbclient', CLIENT_PATH)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


class WireFormat(TestCase):

	@classmethod
	def setUpTestData(cls):
		cls.table = Table.objects.create(tid='T1', tid_int=1, url='t1',
		                                 path='t1', title='Table 1')

	def store(self, model, sage_number, exact_text='', param=b'x'):
		#Polynomial names its constructor argument differently.
		if model is Polynomial:
			obj = model(sage_polynomial=sage_number)
		else:
			obj = model(sage_number=sage_number)
		obj.table = self.table
		obj.param = param
		obj.exact_text = exact_text
		obj.save()
		return obj

	def test_no_payload_carries_a_pickle(self):
		cases = [
			(Number, RIF(3.25), '3.25'),
			(NumberComplex, CIF(RIF(0.5), RIF(1.5)), '0.5 + 1.5*I'),
			(NumberPAdic, Qp(5, 20)(1 + 5), '1 + O(5^20)'),
			(Polynomial, QQ['x']([-1, 1]), 'x - 1'),
		]
		for model, value, text in cases:
			with self.subTest(model=model.__name__):
				payload = self.store(model, value, text).to_serializable_dict()
				self.assertNotIn('sage', payload,
				                 '%s still ships a pickle' % (model.__name__,))
				self.assertIn('number', payload)
				self.assertIn('exact_text', payload)

	def test_the_shipped_client_no_longer_unpickles(self):
		source = open(CLIENT_PATH).read()
		code = '\n'.join(line for line in source.split('\n')
		                 if not line.strip().startswith('#'))
		self.assertNotIn('loads(bytes(', code)
		self.assertNotIn('cp437', code)

	def test_the_client_rebuilds_every_kind_the_server_sends(self):
		cases = [
			(Number, RIF(3.25)),
			(Number, ZZ(7)),
			(Number, QQ(2) / 3),
			(Number, RBF(1.5)),
			(NumberComplex, CIF(RIF(0.5), RIF(1.5))),
			(NumberPAdic, Qp(5, 20)(1 + 5)),
			(Polynomial, QQ['x']([-1, 1])),
		]
		client = _client()
		for model, value in cases:
			with self.subTest(value=str(value)):
				payload = self.store(model, value).to_serializable_dict()
				rebuilt = client.decode_number(payload['number'])
				self.assertIsNotNone(rebuilt)

	def test_the_client_refuses_a_kind_it_does_not_know(self):
		"""Dispatch is a fixed table, so a reply cannot name its own decoder."""
		client = _client()
		with self.assertRaises(client.UnsupportedNumber):
			client.decode_number({'kind': 'os.system', 'value': 'rm -rf /'})
		with self.assertRaises(client.UnsupportedNumber):
			client.decode_number('not even an object')

	def test_the_payload_is_json(self):
		"""It has to survive JsonResponse; a pickle only did via cp437."""
		payload = self.store(Number, RIF(3.25), '3.25').to_serializable_dict()
		self.assertEqual(json.loads(json.dumps(payload))['number'],
		                 payload['number'])


class RoundTrip(TestCase):
	"""Encoding must never narrow a value: a client would then hold a number
	the database does not claim."""

	def assert_contains(self, original, rebuilt):
		self.assertLessEqual(RIF(rebuilt).lower(), RIF(original).lower())
		self.assertGreaterEqual(RIF(rebuilt).upper(), RIF(original).upper())

	def test_intervals_and_balls_only_ever_widen(self):
		for value in [RIF(3.25), RIF(3.1, 3.2), RBF(1.5), RBF(0.5281),
		              ZZ(7), QQ(2) / 3]:
			with self.subTest(value=str(value)):
				self.assert_contains(value, decode_number(encode_number(value)))

	def test_a_ball_is_not_narrowed_by_a_rounded_radius(self):
		"""Encoding centre and radius rounds the radius, sometimes downward,
		which yields a ball narrower than the value it describes.

		These are the stored center and radius of a real row -- the radius
		serialises through str() as '2.0000000e-7', dropping the tail. 28 of
		the 73 balls in the database were narrowed this way. Synthetic balls do
		not reproduce it: the radius has to carry more significant digits than
		str() keeps.
		"""
		ball = RBF(8.880243369999997).add_error(2.0000000433562093e-07)
		rebuilt = decode_number(encode_number(ball))
		self.assert_contains(ball, rebuilt)

	def test_exact_values_survive_exactly(self):
		for value in [ZZ(10) ** 40 + 1, QQ(355) / 113]:
			with self.subTest(value=str(value)):
				self.assertEqual(decode_number(encode_number(value)), value)
