"""A draft that answers "not found" must not read as a draft that was deleted.

Somebody who had made the drafts was signed out, clicked the tables he had
been reading, and got Django's "The requested resource was not found on this
server" -- the same answer a stranger gets, for the good reason that saying
"you may not see this" would confirm the table exists. He spent a few minutes
believing the server had lost them.

So the page says what that answer covers, and it says it to everybody: an
address that never existed, a table that was never made, and a private draft
all render the same page. That is what keeps it from leaking.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from .editing import create_table
from .models import Table


class TheNotFoundPageExplainsItself(TestCase):

	def setUp(self):
		self.author = get_user_model().objects.create_user('author')
		create_table({'Title': 'A private draft of something',
		              'Definition': 'These numbers, for a reason.',
		              'Data properties': {'type': 'R'},
		              'Parameters': {'n': {'type': 'Z'}},
		              'Numbers': [{'params': {'n': '1'}, 'number': '1.5'}]},
		             via='orm')
		self.draft = Table.objects.get(title='A private draft of something')
		self.draft.published = False
		self.draft.save(update_fields=['published'])

	def body(self, path):
		answer = self.client.get(path)
		self.assertEqual(answer.status_code, 404)
		return answer.content.decode()

	def test_a_signed_out_reader_is_told_they_are_signed_out(self):
		body = self.body('/%s' % self.draft.url)
		self.assertIn('not signed in', body)
		self.assertIn('have not been deleted', body)

	def test_the_way_back_returns_to_the_address_asked_for(self):
		#Signing in and landing on the front page means finding the draft
		#again by hand, which is the moment this was supposed to save.
		body = self.body('/%s' % self.draft.url)
		self.assertIn('next=%%2F%s' % self.draft.url, body)

	def test_an_address_with_an_apostrophe_survives_the_round_trip(self):
		#`Lévy's_constant` is a real address here. An unescaped one would be
		#cut in half by the first `?` or `&` a title ever carries.
		create_table({'Title': "Someone's other draft",
		              'Definition': 'These numbers, for a reason.',
		              'Data properties': {'type': 'R'},
		              'Parameters': {'n': {'type': 'Z'}},
		              'Numbers': [{'params': {'n': '1'}, 'number': '2.5'}]},
		             via='orm')
		other = Table.objects.get(title="Someone's other draft")
		other.published = False
		other.save(update_fields=['published'])
		body = self.body('/%s' % other.url)
		self.assertIn('%27', body)
		self.assertNotIn("next=/Someone's", body)

	def test_an_address_that_never_existed_says_the_same_thing(self):
		#The whole safety of the message: a reader cannot tell which of the
		#two they are looking at, so it confirms nothing about the draft.
		invented = self.body('/An_address_nobody_ever_used')
		private = self.body('/%s' % self.draft.url)
		self.assertIn('not signed in', invented)
		for page in (invented, private):
			self.assertNotIn('A private draft of something', page)

	def test_it_does_not_tell_a_signed_in_reader_to_sign_in(self):
		self.client.force_login(self.author)
		body = self.body('/An_address_nobody_ever_used')
		self.assertNotIn('You are not signed in', body)
		self.assertIn('drafts', body)


class ASessionLastsFromItsLastUse(TestCase):
	"""Two weeks after signing in is a deadline that arrives mid-afternoon."""

	def test_every_request_pushes_the_expiry_forward(self):
		from django.conf import settings

		self.assertTrue(settings.SESSION_SAVE_EVERY_REQUEST)
