"""API keys and rate limiting.

The API is the cheapest way to make the server work hard -- /api/search runs
the sandboxed evaluator -- and it runs on a machine with no headroom to absorb
a script in a loop.
"""

import json

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings

from .models import ApiKey
from .throttle import requester_of


class Keys(TestCase):

	def setUp(self):
		self.user = User.objects.create_user('alice', password='x')

	def test_a_key_is_shown_once_and_never_stored(self):
		"""A leaked database must not hand out working credentials."""
		record, token = ApiKey.issue(self.user, 'laptop')
		self.assertNotIn(token, record.hashed_key)
		self.assertEqual(
			ApiKey.objects.filter(hashed_key=token).count(), 0)
		self.assertTrue(record.prefix and token.startswith(record.prefix))

	def test_a_token_authenticates_to_its_own_key(self):
		record, token = ApiKey.issue(self.user)
		self.assertEqual(ApiKey.authenticate(token), record)

	def test_a_wrong_or_revoked_token_authenticates_to_nothing(self):
		record, token = ApiKey.issue(self.user)
		self.assertIsNone(ApiKey.authenticate(token + 'x'))
		self.assertIsNone(ApiKey.authenticate(''))
		self.assertIsNone(ApiKey.authenticate(None))
		record.revoked = True
		record.save()
		self.assertIsNone(ApiKey.authenticate(token))

	def test_sharing_a_prefix_does_not_share_an_identity(self):
		"""Lookup is by prefix, so a collision must still be rejected."""
		record, token = ApiKey.issue(self.user)
		impostor = ApiKey.objects.create(
			user=self.user, prefix=record.prefix,
			hashed_key=ApiKey.hash_token('something else'))
		self.assertEqual(ApiKey.authenticate(token), record)
		self.assertNotEqual(ApiKey.authenticate(token), impostor)


@override_settings(NUMBERDB_ANONYMOUS_RATE_LIMIT=3,
                   NUMBERDB_IDENTIFIED_RATE_LIMIT=10,
                   NUMBERDB_RATE_LIMIT_WINDOW=3600)
class Throttling(TestCase):

	def setUp(self):
		cache.clear()
		self.user = User.objects.create_user('bob', password='x')

	def get(self, **extra):
		return self.client.get('/api/tag', {'url': 'nope'}, **extra)

	def test_an_anonymous_caller_is_cut_off_at_the_limit(self):
		for _ in range(3):
			self.assertNotEqual(self.get().status_code, 429)
		response = self.get()
		self.assertEqual(response.status_code, 429)
		self.assertIn('Retry-After', response)
		self.assertIn('API key', response.json()['error'])

	def test_a_key_raises_the_limit(self):
		_, token = ApiKey.issue(self.user)
		auth = {'HTTP_AUTHORIZATION': 'Bearer %s' % (token,)}
		for _ in range(8):
			self.assertNotEqual(self.get(**auth).status_code, 429)

	def test_two_callers_do_not_share_an_allowance(self):
		for _ in range(3):
			self.get(REMOTE_ADDR='10.0.0.1')
		self.assertEqual(self.get(REMOTE_ADDR='10.0.0.1').status_code, 429)
		self.assertNotEqual(self.get(REMOTE_ADDR='10.0.0.2').status_code, 429)

	def test_a_bad_key_is_refused_rather_than_demoted(self):
		"""Silently dropping to the anonymous limit would look like a slow day."""
		response = self.get(HTTP_AUTHORIZATION='Bearer not-a-real-key')
		self.assertEqual(response.status_code, 403)

	def test_a_forged_forwarded_header_cannot_reset_the_counter(self):
		"""Only the last hop is ours; earlier entries are caller-supplied."""
		for _ in range(3):
			self.get(HTTP_X_FORWARDED_FOR='1.2.3.4, 10.0.0.9')
		self.assertEqual(
			self.get(HTTP_X_FORWARDED_FOR='9.9.9.9, 10.0.0.9').status_code,
			429)

	def test_a_logged_in_session_gets_the_larger_allowance(self):
		self.client.force_login(self.user)
		for _ in range(8):
			self.assertNotEqual(self.get().status_code, 429)

	def test_the_site_itself_is_not_throttled(self):
		"""Ordinary browsing must not consume an API allowance."""
		for _ in range(6):
			self.assertEqual(self.client.get('/').status_code, 200)


@override_settings(NUMBERDB_ANONYMOUS_RATE_LIMIT=60,
                   NUMBERDB_IDENTIFIED_RATE_LIMIT=1000,
                   NUMBERDB_RATE_LIMIT_WINDOW=3600)
class BatchCost(TestCase):
	"""A batch is worth more than one request, and less than its size.

	One unit for the request and half per number, so batching is worth doing --
	it saves a handshake and a round trip -- without letting a caller fetch a
	thousand numbers for the price of one.
	"""

	def setUp(self):
		cache.clear()

	def test_the_price_grows_with_the_batch(self):
		from .throttle import batch_cost
		self.assertEqual([batch_cost(n) for n in (0, 1, 2, 10, 100)],
		                 [1, 2, 2, 6, 51])

	def test_a_batch_costs_more_than_a_single_lookup(self):
		from .throttle import batch_cost
		self.assertGreater(batch_cost(100), batch_cost(1))
		self.assertLess(batch_cost(100), 100)

	def test_a_batch_is_charged_against_the_allowance(self):
		numbers = json.dumps([{'kind': 'ZZ', 'value': '1'}] * 20)
		before = self.client.get('/api/lookup', {'text': '3.14'})
		self.assertNotEqual(before.status_code, 429)
		#A batch of twenty costs eleven units; a handful of them exhausts an
		#allowance that single lookups would barely dent.
		for _ in range(6):
			self.client.get('/api/lookup', {'numbers': numbers})
		self.assertEqual(
			self.client.get('/api/lookup', {'text': '3.14'}).status_code, 429)

	def test_an_oversized_batch_is_refused_rather_than_truncated(self):
		numbers = json.dumps([{'kind': 'ZZ', 'value': '1'}] * 101)
		response = self.client.get('/api/lookup', {'numbers': numbers})
		self.assertIn('at most 100', response.json()['error'])

	def test_results_say_which_number_they_answer(self):
		numbers = json.dumps([{'kind': 'ZZ', 'value': '3'},
		                      {'kind': 'QQ', 'value': '1/3'}])
		payload = self.client.get('/api/lookup', {'numbers': numbers}).json()
		for record in payload.get('results') or []:
			self.assertIn(record['index'], {'0', '1'})

	def test_a_number_that_cannot_be_read_does_not_spoil_the_batch(self):
		numbers = json.dumps([{'kind': 'ZZ', 'value': '3'},
		                      {'kind': 'NoSuchKind'}])
		payload = self.client.get('/api/lookup', {'numbers': numbers}).json()
		self.assertNotIn('error', payload)
		self.assertTrue(any('could not be read' in m['text']
		                    for m in payload['messages']))
