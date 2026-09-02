"""The Sage wrappers read with the key the package was configured with.

`numberdb.sage` held a client of its own, made at import time with no key, so
`numberdb.configure(api_key=...)` had no effect on any search through it and
an authenticated run read the corpus anonymously -- sixty requests an hour.
Three runs met that as a mysterious throttle, and one could not walk the
corpus at all, which the skill asks it to do.
"""

import unittest


class TheSageWrappersFollowConfigure(unittest.TestCase):

	def setUp(self):
		import numberdb

		self.numberdb = numberdb
		self.before = numberdb._default_client

	def tearDown(self):
		self.numberdb._default_client = self.before

	def flavoured(self):
		from numberdb import sage

		return sage._flavoured(None)

	def test_it_uses_the_configured_key(self):
		self.numberdb.configure(api_key='a-key-for-this-test')
		self.assertEqual(self.flavoured().api_key, 'a-key-for-this-test')

	def test_reconfiguring_is_picked_up(self):
		#The failure was that it never was: the client was fixed at import.
		self.numberdb.configure(api_key='first')
		self.numberdb.configure(api_key='second')
		self.assertEqual(self.flavoured().api_key, 'second')

	def test_an_explicit_client_still_wins(self):
		from numberdb import Client

		self.numberdb.configure(api_key='configured')
		mine = Client(api_key='mine')
		from numberdb import sage

		self.assertEqual(sage._flavoured(mine).api_key, 'mine')

	def test_it_still_returns_sage_objects(self):
		self.numberdb.configure(api_key='k')
		self.assertTrue(getattr(self.flavoured(), 'as_sage', False))


if __name__ == '__main__':
	unittest.main()
