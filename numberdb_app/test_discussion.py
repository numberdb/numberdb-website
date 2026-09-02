"""Tests for a table's discussion.

The models for this were designed long ago and sat in the database unused; what
was added is the pages. Two of their decisions look like limitations and are
not, so they are pinned here: hidden rather than deleted, and one thread per
table with a pointer to an entry rather than a thread per entry.

The rest of the file is about a box that strangers type into. Everything that
goes wrong with one of those goes wrong quietly: markup that turns out to be
executable, a draft table discussed in public, a moderator who cannot undo
themselves, a thousand messages at three in the morning.
"""

from django.test import TestCase


class Discussing(TestCase):

	def setUp(self):
		from django.contrib.auth.models import User

		from .editing import create_table

		self.author = User.objects.create_user('table_author',
		                                       password='pw-123456')
		self.table = create_table(
			{'Title': 'Discussion probe',
			 'Data properties': {'type': 'R'},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '3.11'}]},
			author=self.author,
		via='orm')
		self.talker = User.objects.create_user('talker', password='pw-123456')

	def url(self):
		return '/discuss/%s' % (self.table.tid,)

	def say(self, body='Where did this value come from?', **extra):
		data = {'action': 'post', 'body': body}
		data.update(extra)
		return self.client.post(self.url(), data, follow=True)

	def bodies(self):
		from .models import Comment

		return [c.body for c in Comment.objects.filter(
			thread__table=self.table).order_by('created')]

	#-- reading ---------------------------------------------------------

	def test_anyone_can_read_it(self):
		answer = self.client.get(self.url())
		self.assertEqual(answer.status_code, 200)

	def test_the_table_links_to_it(self):
		body = self.client.get('/%s' % (self.table.tid,)).content.decode()
		self.assertIn('/discuss/%s' % (self.table.tid,), body)

	def test_an_empty_thread_says_so_rather_than_erroring(self):
		"""Nothing exists until somebody speaks: no thread row is made with
		the table, since most tables will never have one."""
		from .models import TableThread

		answer = self.client.get(self.url())
		self.assertContains(answer, 'Nothing has been said')
		self.assertEqual(TableThread.objects.count(), 0)

	#-- posting ---------------------------------------------------------

	def test_a_signed_in_editor_can_post(self):
		self.client.login(username='talker', password='pw-123456')
		self.say('The last two digits look wrong to me.')
		self.assertEqual(self.bodies(), ['The last two digits look wrong to me.'])

	def test_it_appears_on_the_page(self):
		self.client.login(username='talker', password='pw-123456')
		self.say('A remark worth reading.')
		answer = self.client.get(self.url())
		self.assertContains(answer, 'A remark worth reading.')
		self.assertContains(answer, 'talker')

	def test_a_stranger_cannot_post(self):
		self.say('spam')
		self.assertEqual(self.bodies(), [])

	def test_and_is_invited_to_sign_in(self):
		answer = self.client.get(self.url())
		self.assertContains(answer, 'Sign in')

	def test_an_empty_message_is_refused(self):
		self.client.login(username='talker', password='pw-123456')
		self.say('    ')
		self.assertEqual(self.bodies(), [])

	def test_an_enormous_message_is_refused(self):
		from .discussion import BODY_LIMIT

		self.client.login(username='talker', password='pw-123456')
		self.say('x' * (BODY_LIMIT + 1))
		self.assertEqual(self.bodies(), [])

	def test_there_is_an_hourly_allowance(self):
		"""Not moderation -- what stops a script, or a very bad afternoon."""
		from .discussion import PER_HOUR

		self.client.login(username='talker', password='pw-123456')
		for i in range(PER_HOUR + 5):
			self.say('message number %d' % (i,))
		self.assertEqual(len(self.bodies()), PER_HOUR)

	#-- what a message may contain --------------------------------------

	def test_markup_is_shown_rather_than_run(self):
		"""The single most important line in this file. A comment box that
		renders HTML is a comment box that runs somebody else's JavaScript in
		a reader's browser, as that reader."""
		self.client.login(username='talker', password='pw-123456')
		self.say('<script>alert("x")</script> and <b>bold</b>')
		body = self.client.get(self.url()).content.decode()
		self.assertNotIn('<script>alert', body)
		self.assertIn('&lt;script&gt;', body)

	def test_line_breaks_survive(self):
		"""Without them a worked calculation becomes one paragraph."""
		self.client.login(username='talker', password='pw-123456')
		self.say('First line.\nSecond line.')
		self.assertIn('First line.\nSecond line.', self.bodies()[0])

	#-- pointing at one entry -------------------------------------------

	def test_a_message_can_be_about_one_entry(self):
		"""One thread per table, because every entry already has a permanent
		anchor -- so a comment points at an entry instead of living there."""
		self.client.login(username='talker', password='pw-123456')
		self.say('This one.', about_param='1')
		answer = self.client.get(self.url())
		self.assertContains(answer, 'about')
		self.assertContains(answer, '?entry=1')

	#-- editing one's own -----------------------------------------------

	def test_the_author_can_correct_their_own(self):
		from .models import Comment

		self.client.login(username='talker', password='pw-123456')
		self.say('teh value')
		comment = Comment.objects.first()
		self.client.post(self.url(), {'action': 'save-edit',
		                              'comment': comment.pk,
		                              'body': 'the value'}, follow=True)
		self.assertEqual(self.bodies(), ['the value'])

	def test_and_the_change_is_visible(self):
		from .models import Comment

		self.client.login(username='talker', password='pw-123456')
		self.say('first thought')
		comment = Comment.objects.first()
		self.client.post(self.url(), {'action': 'save-edit',
		                              'comment': comment.pk,
		                              'body': 'second thought'}, follow=True)
		comment.refresh_from_db()
		self.assertIsNotNone(comment.edited)
		self.assertContains(self.client.get(self.url()), 'edited')

	def test_nobody_can_edit_somebody_elses(self):
		from django.contrib.auth.models import User

		from .models import Comment

		self.client.login(username='talker', password='pw-123456')
		self.say('mine')
		comment = Comment.objects.first()

		User.objects.create_user('interloper', password='pw-123456')
		self.client.login(username='interloper', password='pw-123456')
		self.client.post(self.url(), {'action': 'save-edit',
		                              'comment': comment.pk,
		                              'body': 'not mine'}, follow=True)
		self.assertEqual(self.bodies(), ['mine'])

	#-- moderation ------------------------------------------------------

	def board(self):
		from django.contrib.auth.models import User

		from .permissions import board_group

		moderator = User.objects.create_user('moderator',
		                                     password='pw-123456')
		moderator.groups.add(board_group())
		return moderator

	def test_the_board_can_hide_a_message(self):
		from .models import Comment

		self.client.login(username='talker', password='pw-123456')
		self.say('something regrettable')
		comment = Comment.objects.first()

		self.board()
		self.client.login(username='moderator', password='pw-123456')
		self.client.post(self.url(), {'action': 'hide',
		                              'comment': comment.pk}, follow=True)
		comment.refresh_from_db()
		self.assertTrue(comment.hidden)

	def test_a_hidden_message_is_not_shown_to_readers(self):
		from .models import Comment

		self.client.login(username='talker', password='pw-123456')
		self.say('something regrettable')
		comment = Comment.objects.first()
		self.board()
		self.client.login(username='moderator', password='pw-123456')
		self.client.post(self.url(), {'action': 'hide', 'comment': comment.pk})

		self.client.logout()
		body = self.client.get(self.url()).content.decode()
		self.assertNotIn('something regrettable', body)
		self.assertIn('hidden by a moderator', body)

	def test_but_it_is_kept_rather_than_deleted(self):
		"""A removed message leaves replies to nothing, and moderation that
		cannot be undone is moderation nobody dares use."""
		from .models import Comment

		self.client.login(username='talker', password='pw-123456')
		self.say('something regrettable')
		comment = Comment.objects.first()
		self.board()
		self.client.login(username='moderator', password='pw-123456')
		self.client.post(self.url(), {'action': 'hide', 'comment': comment.pk})

		self.assertTrue(Comment.objects.filter(pk=comment.pk).exists())
		self.client.post(self.url(), {'action': 'unhide',
		                              'comment': comment.pk}, follow=True)
		comment.refresh_from_db()
		self.assertFalse(comment.hidden)

	def test_an_ordinary_account_cannot_hide_anything(self):
		from django.contrib.auth.models import User

		from .models import Comment

		self.client.login(username='talker', password='pw-123456')
		self.say('a message')
		comment = Comment.objects.first()

		User.objects.create_user('nosy', password='pw-123456')
		self.client.login(username='nosy', password='pw-123456')
		self.client.post(self.url(), {'action': 'hide',
		                              'comment': comment.pk}, follow=True)
		comment.refresh_from_db()
		self.assertFalse(comment.hidden)

	def test_the_count_beside_the_title_ignores_hidden_ones(self):
		"""A badge saying 3 over a thread showing 2 asks exactly the question
		hiding it was meant to close."""
		from .models import Comment

		self.client.login(username='talker', password='pw-123456')
		self.say('one')
		self.say('two')
		self.assertEqual(self.table.discussion_count, 2)

		self.board()
		self.client.login(username='moderator', password='pw-123456')
		self.client.post(self.url(), {'action': 'hide',
		                              'comment': Comment.objects.first().pk})
		self.assertEqual(self.table.discussion_count, 1)

	#-- one table's discussion is not another's -------------------------

	def test_a_message_cannot_be_moderated_through_the_wrong_table(self):
		from .editing import create_table
		from .models import Comment

		other = create_table(
			{'Title': 'Another table',
			 'Data properties': {'type': 'R'},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '2.71'}]},
			author=self.author,
		via='orm')

		self.client.login(username='talker', password='pw-123456')
		self.say('belongs to the first table')
		comment = Comment.objects.first()

		self.board()
		self.client.login(username='moderator', password='pw-123456')
		answer = self.client.post('/discuss/%s' % (other.tid,),
		                          {'action': 'hide', 'comment': comment.pk})
		self.assertEqual(answer.status_code, 404)
		comment.refresh_from_db()
		self.assertFalse(comment.hidden)


class DraftsAreNotDiscussedInPublic(TestCase):
	"""A draft table is visible only to its author. Its discussion must not be
	the way round that."""

	def setUp(self):
		from django.contrib.auth.models import User

		from .editing import create_table

		self.author = User.objects.create_user('draft_author',
		                                       password='pw-123456')
		self.draft = create_table(
			{'Title': 'Secret draft',
			 'Data properties': {'type': 'R'},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '3.11'}]},
			author=self.author, published=False,
		via='orm')

	def test_a_stranger_cannot_read_it(self):
		from django.contrib.auth.models import User

		User.objects.create_user('outsider', password='pw-123456')
		self.client.login(username='outsider', password='pw-123456')
		answer = self.client.get('/discuss/%s' % (self.draft.tid,))
		self.assertEqual(answer.status_code, 404)

	def test_the_author_can(self):
		self.client.login(username='draft_author', password='pw-123456')
		answer = self.client.get('/discuss/%s' % (self.draft.tid,))
		self.assertEqual(answer.status_code, 200)


class WhatIsRecordedAboutDiscussion(TestCase):

	def setUp(self):
		from django.contrib.auth.models import User

		from .editing import create_table

		self.user = User.objects.create_user('recorded_user',
		                                     password='pw-123456')
		self.table = create_table(
			{'Title': 'Record probe',
			 'Data properties': {'type': 'R'},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '3.11'}]},
			author=self.user,
		via='orm')
		self.client.login(username='recorded_user', password='pw-123456')

	def test_a_message_reaches_the_activity_log(self):
		"""Discussion is the part of a site that goes wrong quietly, and the
		first question is always what happened and when."""
		from .test_activity_log import CapturedLog

		with CapturedLog('numberdb.edit') as log:
			self.client.post('/discuss/%s' % (self.table.tid,),
			                 {'action': 'post', 'body': 'a message'})
		events = [line for line in log.lines if line.get('event') == 'comment']
		self.assertEqual(len(events), 1)
		self.assertEqual(events[0]['author'], 'recorded_user')

	def test_the_export_includes_what_you_wrote(self):
		import json

		self.client.post('/discuss/%s' % (self.table.tid,),
		                 {'action': 'post', 'body': 'my own words'})
		data = json.loads(
			self.client.get('/profile/export').content.decode())
		self.assertEqual(len(data['comments']), 1)
		self.assertEqual(data['comments'][0]['body'], 'my own words')
		self.assertEqual(data['comments'][0]['table'], self.table.tid)

	def test_closing_an_account_keeps_the_conversation_readable(self):
		"""A conversation with one side removed misleads everyone who reads it
		afterwards."""
		from .account_data import TOMBSTONE_NAME
		from .models import Comment

		self.client.post('/discuss/%s' % (self.table.tid,),
		                 {'action': 'post', 'body': 'still worth reading'})
		self.client.post('/profile/delete', {'confirm': 'recorded_user'})

		comment = Comment.objects.get()
		self.assertEqual(comment.body, 'still worth reading')
		self.assertEqual(comment.author.username, TOMBSTONE_NAME)

	def test_the_privacy_policy_mentions_it(self):
		body = self.client.get('/privacy').content.decode()
		self.assertIn('discussion', body.lower())
