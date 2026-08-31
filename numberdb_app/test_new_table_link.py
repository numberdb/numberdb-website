"""Making a table should be reachable from the site, not only from the help."""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class TheHeaderOffersANewTable(TestCase):

	def page(self, signed_in):
		client = Client()
		if signed_in:
			user = get_user_model().objects.create_user('someone')
			client.force_login(user)
		return client.get(reverse('db:tables'), HTTP_HOST='numberdb.org')

	def test_a_signed_in_person_sees_it(self):
		body = self.page(signed_in=True).content.decode('utf8', 'replace')
		self.assertIn(reverse('db:new-table'), body)

	def test_a_visitor_does_not(self):
		#The form needs an account, and a link that always refuses teaches
		#people to stop clicking.
		body = self.page(signed_in=False).content.decode('utf8', 'replace')
		self.assertNotIn('New&nbsp;table', body)
