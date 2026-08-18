"""The drafts listing, and the cap on creating them with a program.

A draft's numbers are unreviewed and answer no search. That is the reason to
hide what is *in* a draft, and it is not a reason to hide that it exists --
hiding both is how two people end up making the same table without either
knowing.

See docs/design/drafts-and-duplicates.md.
"""

import json

from django.contrib.auth.models import Group, User
from django.test import TestCase

from .editing import create_table
from .permissions import BOARD_GROUP


def a_table(title, author, published=False):
	return create_table(
		{'Title': title,
		 'Data properties': {'type': 'Z[]'},
		 'Parameters': {'n': {'type': 'Z'}},
		 'Numbers': [{'params': {'n': '1'}, 'number': '1'}]},
		author=author, published=published)


class TheDraftsListing(TestCase):

	def setUp(self):
		self.author = User.objects.create_user('drafter', password='pw-123456')
		self.stranger = User.objects.create_user('passer_by', password='pw-123456')
		self.draft = a_table('Fibonacci polynomials', self.author)

	def test_a_stranger_is_asked_to_sign_in(self):
		response = self.client.get('/drafts')
		self.assertEqual(response.status_code, 302)
		self.assertIn('login', response['Location'])

	def test_a_signed_in_stranger_sees_that_it_exists(self):
		#The point of the page: somebody about to make this table finds out.
		self.client.force_login(self.stranger)
		body = self.client.get('/drafts').content.decode()
		self.assertIn('Fibonacci polynomials', body)
		self.assertIn('drafter', body)

	def test_a_stranger_still_cannot_read_the_draft_itself(self):
		self.client.force_login(self.stranger)
		self.assertEqual(self.client.get('/%s' % (self.draft.tid,)).status_code, 404)

	def test_the_numbers_stay_out_of_search(self):
		#Existence is public to members; values are not published.
		from .models import Number

		self.assertEqual(
			Number.objects.filter(table=self.draft, reviewed=True).count(), 0)

	def test_a_published_table_is_not_in_the_listing(self):
		a_table('Lucas polynomials', self.author, published=True)
		self.client.force_login(self.stranger)
		body = self.client.get('/drafts').content.decode()
		self.assertNotIn('Lucas polynomials', body)


class TheDraftCap(TestCase):

	def setUp(self):
		self.person = User.objects.create_user('capped', password='pw-123456')
		self.chair = User.objects.create_user('chair', password='pw-123456')
		self.chair.groups.add(Group.objects.get_or_create(name=BOARD_GROUP)[0])

	def test_an_ordinary_account_may_hold_a_few(self):
		from .permissions import DRAFTS_IN_FLIGHT, draft_allowance

		remaining, held = draft_allowance(self.person)
		self.assertEqual((remaining, held), (DRAFTS_IN_FLIGHT, 0))

	def test_the_allowance_falls_as_drafts_are_made(self):
		from .permissions import DRAFTS_IN_FLIGHT, draft_allowance

		a_table('One', self.person)
		a_table('Two', self.person)
		remaining, held = draft_allowance(self.person)
		self.assertEqual((remaining, held), (DRAFTS_IN_FLIGHT - 2, 2))

	def test_publishing_a_draft_gives_the_allowance_back(self):
		#The limit is on drafts in flight, not on drafts ever made.
		from .editing import publish_table
		from .permissions import DRAFTS_IN_FLIGHT, draft_allowance

		table = a_table('One', self.person)
		publish_table(table)
		remaining, _ = draft_allowance(self.person)
		self.assertEqual(remaining, DRAFTS_IN_FLIGHT)

	def test_a_full_account_may_not_create_another(self):
		from .permissions import (DRAFTS_IN_FLIGHT,
		                          may_create_drafts_through_api)

		for n in range(DRAFTS_IN_FLIGHT):
			a_table('Draft number %d' % n, self.person)
		self.assertFalse(may_create_drafts_through_api(self.person))

	def test_the_board_is_not_capped(self):
		#They are the ones who publish; a draft of theirs is one step from
		#being a table.
		from .permissions import DRAFTS_IN_FLIGHT, draft_allowance

		for n in range(DRAFTS_IN_FLIGHT + 2):
			a_table('Board draft %d' % n, self.chair)
		remaining, held = draft_allowance(self.chair)
		self.assertIsNone(remaining)
		self.assertEqual(held, DRAFTS_IN_FLIGHT + 2)


class CreatingADraftThroughTheApi(TestCase):
	"""Publishing stays a person's act; proposing does not have to be.

	The board-only rule on table creation is about permanence -- a T-number, a
	listing entry, a parameter order citations resolve on. A draft has none of
	those yet.
	"""

	def setUp(self):
		from .models import ApiKey
		from .permissions import board_group

		self.person = User.objects.create_user('api_drafter', password='pw-123456')
		self.person.groups.add(board_group())
		self.key, self.token = ApiKey.issue(self.person, label='drafting')

	def _create(self, title, draft=True):
		import json

		headers = {'HTTP_AUTHORIZATION': 'Bearer %s' % (self.token,)}
		if draft:
			headers['HTTP_X_DRAFT'] = 'yes'
		return self.client.post(
			'/api/tables',
			json.dumps({'Title': title,
			            'Data properties': {'type': 'Z[]'},
			            'Parameters': {'n': {'type': 'Z'}},
			            'Numbers': [{'params': {'n': '1'}, 'number': '1'}]}),
			content_type='application/json', **headers)

	def test_a_draft_is_created_unpublished(self):
		answer = self._create('Proposed by a program')
		self.assertEqual(answer.status_code, 201)
		body = answer.json()
		self.assertFalse(body['published'])
		self.assertTrue(body['tid'].startswith('T'))

	def test_the_answer_says_how_many_more_may_be_made(self):
		#So a caller filling several knows where it stands without being
		#refused first.
		body = self._create('Another proposal').json()
		self.assertIn('drafts_remaining', body)
		self.assertIn('drafts_held', body)

	def test_without_the_header_it_is_a_published_table(self):
		#Creating a table and proposing one are different acts, and a caller
		#says which it means rather than having it inferred.
		body = self._create('Made outright', draft=False).json()
		self.assertTrue(body['published'])

	def test_the_draft_is_invisible_to_a_stranger(self):
		tid = self._create('Quietly proposed').json()['tid']
		stranger = User.objects.create_user('nobody', password='pw-123456')
		self.client.force_login(stranger)
		self.assertEqual(self.client.get('/%s' % (tid,)).status_code, 404)

	def test_a_draft_may_have_no_numbers_yet(self):
		#The prose is written first and a generator fills it. The refusal that
		#used to fire here said "drafts are not published here", which was
		#true before drafts could be made this way and stale afterwards.
		import json

		answer = self.client.post(
			'/api/tables',
			json.dumps({'Title': 'Prose first',
			            'Data properties': {'type': 'Z[]'},
			            'Parameters': {'n': {'type': 'Z'}}}),
			content_type='application/json',
			HTTP_AUTHORIZATION='Bearer %s' % (self.token,),
			HTTP_X_DRAFT='yes')
		self.assertEqual(answer.status_code, 201, answer.content[:300])
		self.assertFalse(answer.json()['published'])

	def test_a_published_table_still_needs_numbers(self):
		import json

		answer = self.client.post(
			'/api/tables',
			json.dumps({'Title': 'Empty and public',
			            'Data properties': {'type': 'Z[]'},
			            'Parameters': {'n': {'type': 'Z'}}}),
			content_type='application/json',
			HTTP_AUTHORIZATION='Bearer %s' % (self.token,))
		self.assertEqual(answer.status_code, 400)
		self.assertIn('X-Draft', answer.json()['detail'])

	def test_the_owner_can_read_their_own_draft_through_the_api(self):
		#Otherwise a generator can create a draft and then not fill it, which
		#is the whole workflow drafts exist for.
		import json

		tid = self._create('Readable by its author').json()['tid']
		answer = self.client.get(
			'/api/table', {'id': tid},
			HTTP_AUTHORIZATION='Bearer %s' % (self.token,))
		self.assertEqual(answer.status_code, 200)
		self.assertIn('Title', answer.json())

	def test_a_key_less_request_still_cannot_read_it(self):
		tid = self._create('Not readable publicly').json()['tid']
		answer = self.client.get('/api/table', {'id': tid})
		self.assertIn('does not exist', json.dumps(answer.json()))

	def test_somebody_elses_key_cannot_read_it(self):
		from .models import ApiKey

		tid = self._create('Not readable by strangers').json()['tid']
		stranger = User.objects.create_user('other_holder', password='pw-123456')
		_, token = ApiKey.issue(stranger, label='theirs')
		answer = self.client.get(
			'/api/table', {'id': tid},
			HTTP_AUTHORIZATION='Bearer %s' % (token,))
		self.assertIn('does not exist', json.dumps(answer.json()))
