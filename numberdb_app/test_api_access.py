"""API keys and rate limiting.

The API is the cheapest way to make the server work hard -- /api/search runs
the sandboxed evaluator -- and it runs on a machine with no headroom to absorb
a script in a loop.
"""

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
