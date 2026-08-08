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

#The package users install; tested from the source tree it ships from.
PACKAGE_PATH = '/app/clients/python'


def _client():
	"""The published package, loaded from the source tree it ships from.

	Loaded by path under an alias rather than by name: this repository's Django
	project is also called ``numberdb`` and is already imported, so ``import
	numberdb`` here would find the server, not the client. Users never have
	both, so the collision is ours alone.

	Loaded as a package, with submodule_search_locations set, so the relative
	imports inside it resolve -- importing a single module out of it would
	break on ``from ._errors import ...``.
	"""
	import sys
	if 'numberdb_client' in sys.modules:
		return sys.modules['numberdb_client']
	spec = importlib.util.spec_from_file_location(
		'numberdb_client', '%s/numberdb/__init__.py' % (PACKAGE_PATH,),
		submodule_search_locations=['%s/numberdb' % (PACKAGE_PATH,)])
	module = importlib.util.module_from_spec(spec)
	sys.modules['numberdb_client'] = module
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
		#Only when given: the constructor fills in a faithful default, and
		#clearing it would leave a row that cannot be read back.
		if exact_text:
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
		"""No file users install may turn a response into code."""
		import glob
		for path in glob.glob('%s/numberdb/*.py' % (PACKAGE_PATH,)):
			source = open(path).read()
			code = '\n'.join(line for line in source.split('\n')
			                 if not line.strip().startswith('#'))
			with self.subTest(module=path):
				#The operation, not the word: the module documents at length
				#why it does not unpickle, and should go on saying so.
				for forbidden in ['import pickle', 'pickle.loads', 'cPickle',
				                  'loads(bytes(', 'cp437', 'eval(', 'exec(']:
					self.assertNotIn(forbidden, code,
					                 '%s uses %s' % (path, forbidden))

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
				rebuilt = client.decode(payload['number'])
				self.assertIsNotNone(rebuilt)

	def test_the_client_refuses_a_kind_it_does_not_know(self):
		"""Dispatch is a fixed table, so a reply cannot name its own decoder."""
		client = _client()
		with self.assertRaises(client.UnsupportedNumberError):
			client.decode({'kind': 'os.system', 'value': 'rm -rf /'})
		with self.assertRaises(client.UnsupportedNumberError):
			client.decode('not even an object')

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


class ExactValuesAreSearchable(TestCase):
	"""Advanced search must not drop exactly-known values.

	The dispatch keys on the parent of what the sandbox returns. Integers and
	rationals used to arrive as RIF, because the wire format could not carry
	them and they were coerced; once ZZ and QQ crossed intact they matched no
	branch and every integer search returned nothing, with no error to show for
	it. Regression caught in production, not by a test.
	"""

	@classmethod
	def setUpTestData(cls):
		cls.table = Table.objects.create(tid='T1', tid_int=1, url='t1',
		                                 path='t1', title='Table 1')

	def store(self, value, param=b'x'):
		from .models import exact_relative_width
		number = Number(sage_number=value)
		number.table = self.table
		number.param = param
		number.exact_text = str(value)
		number.exact_relative_width = exact_relative_width(number.exact_text)
		number.save()
		return number

	def search(self, value):
		"""The dispatch in api.py, exercised through its own entry point."""
		from .api import advanced_search_results
		from django.test import RequestFactory
		from unittest.mock import patch
		request = RequestFactory().get('/api/search', {'expression': 'unused'})
		with patch('numberdb_app.api.evaluate_search_program',
		           return_value=([('', value)], [])):
			return advanced_search_results(request, return_type='dict')

	def test_an_integer_finds_the_stored_integer(self):
		stored = self.store(ZZ(7))
		results = self.search(ZZ(7))['results']
		self.assertIn(stored.id, [r['number'].id for r in results])

	def test_a_rational_finds_the_stored_rational(self):
		stored = self.store(QQ(2) / 3, param=b'r')
		results = self.search(QQ(2) / 3)['results']
		self.assertIn(stored.id, [r['number'].id for r in results])

	def test_a_real_still_works(self):
		stored = self.store(RIF(3.25), param=b's')
		results = self.search(RIF(3.25))['results']
		self.assertIn(stored.id, [r['number'].id for r in results])


class MultivariatePolynomials(TestCase):
	"""A polynomial must come back in a ring that can hold it.

	The decoder built a ring of x0, x1, ... and handed it text saying "x^2+y".
	Sage cannot map that -- "Could not find a mapping of the passed element to
	this ring" -- so every multivariate polynomial was undecodable: 87 of the
	1038 stored. Caught by round-tripping the real database rather than the two
	single-variable examples the tests had.
	"""

	def test_variables_are_named_as_the_text_names_them(self):
		from sage.rings.all import QQ, PolynomialRing
		ring = PolynomialRing(QQ, 2, ['x', 'y'])
		x, y = ring.gens()
		for polynomial in [x ** 2 + y, x * y - 1, x ** 2 * y - 2 * y + 1]:
			with self.subTest(polynomial=str(polynomial)):
				rebuilt = decode_number(encode_number(polynomial))
				self.assertEqual(str(rebuilt).replace(' ', ''),
				                 str(polynomial).replace(' ', ''))

	def test_three_variables_survive_too(self):
		from sage.rings.all import QQ, PolynomialRing
		ring = PolynomialRing(QQ, 3, ['x', 'y', 'z'])
		x, y, z = ring.gens()
		polynomial = x * y * z - x + 1
		self.assertEqual(
			str(decode_number(encode_number(polynomial))).replace(' ', ''),
			str(polynomial).replace(' ', ''))

	def test_a_single_variable_is_unaffected(self):
		from sage.rings.all import QQ
		polynomial = QQ['x']([-1, 1])
		self.assertEqual(
			str(decode_number(encode_number(polynomial))).replace(' ', ''),
			str(polynomial).replace(' ', ''))
