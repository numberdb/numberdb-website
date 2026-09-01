"""Two pages that looked like duplicates.

They answer different questions -- unpublished *tables* against unconfirmed
*entries* -- and a table being filled appears on both. That was invisible when
the only unconfirmed entries in the corpus happened to be inside the only two
drafts, and the pages read as duplicates of each other.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .permissions import board_group


class EachPageSaysHowItDiffersFromTheOther(TestCase):

	def board_client(self):
		user = get_user_model().objects.create_user('reviewer')
		user.groups.add(board_group())
		client = Client()
		client.force_login(user)
		return client

	def test_drafts_points_at_the_review_queue(self):
		body = self.board_client().get(reverse('db:drafts'),
		                               HTTP_HOST='numberdb.org').content.decode()
		self.assertIn(reverse('db:review-queue'), body)
		self.assertIn('not published yet', body)

	def test_the_review_queue_points_at_the_drafts(self):
		body = self.board_client().get(reverse('db:review-queue'),
		                               HTTP_HOST='numberdb.org').content.decode()
		self.assertIn(reverse('db:drafts'), body)
		self.assertIn('nobody has confirmed', body)

	def test_an_ordinary_account_is_not_told_about_a_page_it_cannot_see(self):
		#The review queue answers 404 to anybody not on the board, so a link
		#to it would be a dead end.
		user = get_user_model().objects.create_user('ordinary')
		client = Client()
		client.force_login(user)
		body = client.get(reverse('db:drafts'),
		                  HTTP_HOST='numberdb.org').content.decode()
		self.assertNotIn(reverse('db:review-queue'), body)
