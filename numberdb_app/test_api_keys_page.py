"""Tests for issuing one's own API keys.

Keys used to be issued by hand, by email, which is a bottleneck in front of the
one thing the write API exists for. The model never needed changing; what was
missing was a page.

The property worth protecting is the one that makes a leaked database harmless:
the server stores a hash and cannot read a key back. So the token appears
exactly once, in the response to the request that created it, and nowhere else
-- not in a URL, not in the list, not on a refresh.
"""

from django.test import TestCase


class ApiKeysPage(TestCase):

	def setUp(self):
		from django.contrib.auth.models import User

		self.user = User.objects.create_user('keyholder',
		                                     password='pw-123456')
		self.client.login(username='keyholder', password='pw-123456')

	def create(self, label='the laptop'):
		return self.client.post('/profile/keys',
		                        {'action': 'create', 'label': label},
		                        follow=True)

	def keys(self):
		from .models import ApiKey

		return ApiKey.objects.filter(user=self.user)

	#-- issuing --------------------------------------------------------

	def test_a_key_can_be_created(self):
		self.create()
		self.assertEqual(self.keys().count(), 1)

	def test_the_token_is_shown_once(self):
		body = self.create().content.decode()
		token = self.keys().first().prefix
		self.assertIn(token, body)

	def test_and_not_again_on_a_refresh(self):
		"""A token that survives a refresh is a token in the browser's back
		button."""
		first = self.create().content.decode()
		token = self.keys().first().prefix
		self.assertIn(token, first)

		again = self.client.get('/profile/keys').content.decode()
		self.assertNotIn(token + '_', again)   # the full token, not the prefix
		self.assertNotIn('only time it will be shown', again)

	def test_the_token_never_reaches_the_url(self):
		"""Where it would land in the history, the server log and the Referer
		header of the next page."""
		answer = self.client.post('/profile/keys',
		                          {'action': 'create', 'label': 'x'})
		self.assertEqual(answer.status_code, 302)
		self.assertNotIn('key=', answer['Location'])
		self.assertEqual(answer['Location'], '/profile/keys')

	def test_the_server_cannot_read_it_back(self):
		"""Only a hash is stored, which is what makes a leaked database not a
		leaked set of credentials."""
		body = self.create().content.decode()
		key = self.keys().first()
		self.assertEqual(len(key.hashed_key), 64)
		self.assertNotIn(key.hashed_key, body)

	def test_the_label_is_kept(self):
		self.create(label='zeta-generator')
		self.assertEqual(self.keys().first().label, 'zeta-generator')

	def test_a_key_without_a_label_is_fine(self):
		self.create(label='')
		self.assertEqual(self.keys().count(), 1)

	#-- what it is good for --------------------------------------------

	def test_the_key_that_was_issued_actually_authenticates(self):
		"""The page and the API must agree, or this is a page that issues
		decorations."""
		from .models import ApiKey

		body = self.create().content.decode()
		#The token as shown, read back off the page the user was given.
		import re
		shown = re.search(r'<code id="fresh-key">([A-Za-z0-9_\-]{20,})</code>',
		                  body)
		self.assertIsNotNone(shown)
		self.assertEqual(ApiKey.authenticate(shown.group(1)).user, self.user)

	#-- revoking -------------------------------------------------------

	def test_a_key_can_be_revoked(self):
		self.create()
		key = self.keys().first()
		self.client.post('/profile/keys',
		                 {'action': 'revoke', 'key': key.pk}, follow=True)
		key.refresh_from_db()
		self.assertTrue(key.revoked)

	def test_a_revoked_key_stops_authenticating(self):
		from .models import ApiKey

		import re
		body = self.create().content.decode()
		token = re.search(r'<code id="fresh-key">([A-Za-z0-9_\-]{20,})</code>',
		                  body).group(1)
		self.client.post('/profile/keys',
		                 {'action': 'revoke', 'key': self.keys().first().pk})
		self.assertIsNone(ApiKey.authenticate(token))

	def test_it_is_revoked_rather_than_deleted(self):
		"""So one that turns up in a log can still be traced to when it was
		issued and last used."""
		self.create()
		self.client.post('/profile/keys',
		                 {'action': 'revoke', 'key': self.keys().first().pk})
		self.assertEqual(self.keys().count(), 1)

	def test_one_user_cannot_revoke_another_users_key(self):
		from django.contrib.auth.models import User

		from .models import ApiKey

		other = User.objects.create_user('someone_else', password='pw-123456')
		theirs, _token = ApiKey.issue(other, label='not yours')

		self.client.post('/profile/keys',
		                 {'action': 'revoke', 'key': theirs.pk})
		theirs.refresh_from_db()
		self.assertFalse(theirs.revoked)

	#-- limits and access ----------------------------------------------

	def test_there_is_a_cap_on_keys_in_use(self):
		from .views import MAX_ACTIVE_KEYS

		for _ in range(MAX_ACTIVE_KEYS + 3):
			self.create()
		self.assertEqual(self.keys().filter(revoked=False).count(),
		                 MAX_ACTIVE_KEYS)

	def test_revoking_one_makes_room_again(self):
		from .views import MAX_ACTIVE_KEYS

		for _ in range(MAX_ACTIVE_KEYS):
			self.create()
		self.client.post('/profile/keys',
		                 {'action': 'revoke', 'key': self.keys().first().pk})
		self.create()
		self.assertEqual(self.keys().filter(revoked=False).count(),
		                 MAX_ACTIVE_KEYS)

	def test_only_your_own_keys_are_listed(self):
		from django.contrib.auth.models import User

		from .models import ApiKey

		other = User.objects.create_user('third_party', password='pw-123456')
		ApiKey.issue(other, label='someone elses laptop')
		self.create(label='mine')

		body = self.client.get('/profile/keys').content.decode()
		self.assertIn('mine', body)
		self.assertNotIn('someone elses laptop', body)

	def test_it_needs_a_login(self):
		self.client.logout()
		answer = self.client.get('/profile/keys')
		self.assertEqual(answer.status_code, 302)
		self.assertIn('login', answer['Location'])


class KeyExpiry(TestCase):
	"""Optional, and off by default, which is the opposite of what most sites
	do. The runs this exists for take hours or days with nobody watching, and a
	key that lapses part way through costs the run."""

	def setUp(self):
		from django.contrib.auth.models import User

		self.user = User.objects.create_user('expiry_user',
		                                     password='pw-123456')
		self.client.login(username='expiry_user', password='pw-123456')

	def test_a_key_does_not_expire_unless_asked(self):
		self.client.post('/profile/keys', {'action': 'create', 'label': 'x'})
		self.assertIsNone(self.user.api_keys.first().expires)

	def test_an_expiry_can_be_chosen(self):
		self.client.post('/profile/keys',
		                 {'action': 'create', 'label': 'x', 'days': '30'})
		key = self.user.api_keys.first()
		self.assertIsNotNone(key.expires)
		self.assertFalse(key.expired)

	def test_an_expired_key_stops_authenticating(self):
		from django.utils import timezone

		from .models import ApiKey

		key, token = ApiKey.issue(self.user, label='old', days=1)
		self.assertEqual(ApiKey.authenticate(token), key)

		key.expires = timezone.now() - timezone.timedelta(seconds=1)
		key.save(update_fields=['expires'])
		self.assertIsNone(ApiKey.authenticate(token))

	def test_an_expired_key_is_still_listed(self):
		"""So it can be told apart from one that was revoked, and from one that
		simply never worked."""
		from django.utils import timezone

		from .models import ApiKey

		key, _token = ApiKey.issue(self.user, label='lapsed', days=1)
		key.expires = timezone.now() - timezone.timedelta(seconds=1)
		key.save(update_fields=['expires'])

		body = self.client.get('/profile/keys').content.decode()
		self.assertIn('lapsed', body)
		self.assertIn('expired', body)


class WhatTheKeyPageSays(TestCase):

	def setUp(self):
		from django.contrib.auth.models import User

		self.user = User.objects.create_user('saying_user',
		                                     password='pw-123456')
		self.client.login(username='saying_user', password='pw-123456')

	def fresh(self):
		return self.client.post('/profile/keys',
		                        {'action': 'create', 'label': 'x'},
		                        follow=True).content.decode()

	def test_a_new_key_can_be_copied(self):
		body = self.fresh()
		self.assertIn('Copy to clipboard', body)
		self.assertIn('id="fresh-key"', body)

	def test_it_says_where_to_put_it(self):
		"""Including the .env the package actually reads, with the key already
		written into the line to paste."""
		body = self.fresh()
		self.assertIn('.env', body)
		self.assertIn('NUMBERDB_API_KEY=', body)
		self.assertIn('.gitignore', body)

	def test_it_says_a_key_is_not_permission_to_write(self):
		"""Which saves finding out from a refusal at the end of a long
		computation."""
		body = self.client.get('/profile/keys').content.decode()
		self.assertIn('Writing needs more than a key', body)


class ProfileShowsStanding(TestCase):
	"""It appeared nowhere, so an account learned it could not write by being
	refused, and could not learn what would change that."""

	def setUp(self):
		from django.contrib.auth.models import User

		self.user = User.objects.create_user('standing_user',
		                                     password='pw-123456')
		self.client.login(username='standing_user', password='pw-123456')

	def test_a_new_account_is_told_what_is_needed(self):
		from .permissions import TRUSTED_AFTER

		body = self.client.get('/profile').content.decode()
		self.assertIn('No edits reviewed yet', body)
		self.assertIn(str(TRUSTED_AFTER), body)

	def test_a_board_member_is_told_they_are_one(self):
		from .permissions import board_group

		self.user.groups.add(board_group())
		body = self.client.get('/profile').content.decode()
		self.assertIn('Board member', body)

	def test_it_links_to_the_keys_page(self):
		self.assertIn('/profile/keys',
		              self.client.get('/profile').content.decode())
