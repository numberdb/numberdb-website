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


class TheNavbarLink(TestCase):
	"""Somebody about to make a table should not have to know that /drafts
	exists in order to find out that it is already being made."""

	def setUp(self):
		self.person = User.objects.create_user('navigator', password='pw-123456')

	def test_a_stranger_is_not_told_that_work_is_happening(self):
		a_table('Quietly in progress', self.person)
		body = self.client.get('/').content.decode()
		self.assertNotIn('/drafts', body)

	def test_a_signed_in_account_gets_the_link_with_a_count(self):
		a_table('One in progress', self.person)
		a_table('Two in progress', self.person)
		self.client.force_login(self.person)
		body = self.client.get('/').content.decode()
		self.assertIn('/drafts', body)
		self.assertIn('Drafts', body)
		self.assertIn('(2)', body)

	def test_no_link_when_nothing_is_in_progress(self):
		#A link that is usually a dead end teaches people to stop clicking it.
		self.client.force_login(self.person)
		body = self.client.get('/').content.decode()
		self.assertNotIn('>Drafts', body)

	def test_the_link_is_on_every_page(self):
		a_table('In progress', self.person)
		self.client.force_login(self.person)
		for path in ('/', '/tables', '/help'):
			with self.subTest(path=path):
				self.assertIn('/drafts', self.client.get(path).content.decode())


class PublishingIsAReview(TestCase):
	"""A draft becomes public by being reviewed, because that is what the two
	acts have in common: somebody competent has looked.

	Anything else means either a table going public that nobody read, or a
	reviewer confirming values on a page the public cannot reach.
	"""

	def setUp(self):
		from django.contrib.auth.models import Group

		from .permissions import BOARD_GROUP

		self.author = User.objects.create_user('proposer', password='pw-123456')
		self.chair = User.objects.create_user('reviewer', password='pw-123456')
		self.chair.groups.add(Group.objects.get_or_create(name=BOARD_GROUP)[0])
		self.draft = a_table('Proposed table', self.author)

	def _offer(self, table=None):
		table = table or self.draft
		return self.client.post('/drafts/%s/offer' % (table.tid,),
		                        {'ready': 'yes'})

	def test_a_draft_in_progress_does_not_ask_for_attention(self):
		#Every draft used to enter the queue the moment it existed, so a title
		#with no numbers in it sat beside a finished table asking for the same
		#thing.
		self.client.force_login(self.chair)
		self.assertNotIn('Proposed table',
		                 self.client.get('/review').content.decode())

	def test_an_offered_draft_waits_in_the_review_queue(self):
		self.client.force_login(self.author)
		self._offer()
		self.client.force_login(self.chair)
		body = self.client.get('/review').content.decode()
		self.assertIn('Proposed table', body)
		self.assertIn('waiting to be published', body)

	def test_confirming_publishes_it(self):
		self.client.force_login(self.author)
		self._offer()
		self.client.force_login(self.chair)
		head = self.draft.head_revision
		answer = self.client.post('/review/%s' % (self.draft.tid,),
		                          {'head': head.digest})
		self.assertEqual(answer.status_code, 302)
		self.draft.refresh_from_db()
		self.assertTrue(self.draft.published)
		self.assertEqual(self.draft.reviewed_by, self.chair)

	def test_the_number_and_address_do_not_change(self):
		#The whole reason a draft keeps its T-number from creation: a
		#generator was written against it while the table was being set up.
		was_tid, was_url = self.draft.tid, self.draft.url
		self.client.force_login(self.chair)
		self.client.post('/review/%s' % (self.draft.tid,),
		                 {'head': self.draft.head_revision.digest})
		self.draft.refresh_from_db()
		self.assertEqual((self.draft.tid, self.draft.url), (was_tid, was_url))

	def test_its_values_answer_search_afterwards(self):
		from .models import Number

		self.client.force_login(self.chair)
		self.client.post('/review/%s' % (self.draft.tid,),
		                 {'head': self.draft.head_revision.digest})
		self.assertEqual(
			Number.objects.filter(table=self.draft, reviewed=False).count(), 0)

	def test_a_stranger_cannot_publish(self):
		self.client.force_login(self.author)
		answer = self.client.post('/review/%s' % (self.draft.tid,),
		                          {'head': self.draft.head_revision.digest})
		self.assertEqual(answer.status_code, 404)
		self.draft.refresh_from_db()
		self.assertFalse(self.draft.published)

	def test_a_draft_made_by_a_trusted_account_still_waits(self):
		#The shortcut that publishes a trusted account's edits as already
		#reviewed is meant for edits to existing tables. Applied to a draft it
		#skips the only look anybody gets at a new table.
		import json

		from .models import ApiKey, Table
		from .permissions import board_group

		self.chair.groups.add(board_group())
		_, token = ApiKey.issue(self.chair, label='drafting')
		answer = self.client.post(
			'/api/tables',
			json.dumps({'Title': 'Trusted proposal',
			            'Data properties': {'type': 'Z[]'},
			            'Parameters': {'n': {'type': 'Z'}},
			            'Numbers': [{'params': {'n': '1'}, 'number': '1'}]}),
			content_type='application/json',
			HTTP_AUTHORIZATION='Bearer %s' % (token,), HTTP_X_DRAFT='yes')
		table = Table.objects.get(tid=answer.json()['tid'])
		self.assertIsNone(table.reviewed_at_revision)


class OfferingADraftForReview(TestCase):
	"""A draft in progress and a draft that is finished are different things,
	and only its author can tell them apart."""

	def setUp(self):
		from django.contrib.auth.models import Group

		from .permissions import BOARD_GROUP

		self.author = User.objects.create_user('drafter2', password='pw-123456')
		self.stranger = User.objects.create_user('bystander', password='pw-123456')
		self.chair = User.objects.create_user('chair2', password='pw-123456')
		self.chair.groups.add(Group.objects.get_or_create(name=BOARD_GROUP)[0])
		self.draft = a_table('Work in progress', self.author)

	def _offer(self, ready='yes'):
		return self.client.post('/drafts/%s/offer' % (self.draft.tid,),
		                        {'ready': ready})

	def test_a_new_draft_starts_in_progress(self):
		self.assertFalse(self.draft.ready_for_review)

	def test_the_author_may_offer_it(self):
		self.client.force_login(self.author)
		self._offer()
		self.draft.refresh_from_db()
		self.assertTrue(self.draft.ready_for_review)

	def test_the_author_may_take_it_back(self):
		#Offering is a statement, and a statement can be withdrawn while the
		#table is still a draft.
		self.client.force_login(self.author)
		self._offer()
		self._offer(ready='no')
		self.draft.refresh_from_db()
		self.assertFalse(self.draft.ready_for_review)

	def test_a_stranger_may_not_offer_somebody_elses_draft(self):
		self.client.force_login(self.stranger)
		self.assertEqual(self._offer().status_code, 404)
		self.draft.refresh_from_db()
		self.assertFalse(self.draft.ready_for_review)

	def test_the_board_may_offer_an_abandoned_one(self):
		self.client.force_login(self.chair)
		self._offer()
		self.draft.refresh_from_db()
		self.assertTrue(self.draft.ready_for_review)

	def test_an_empty_draft_cannot_be_offered(self):
		#Publishing would refuse it, so offering it would put a table in the
		#queue that nobody can act on.
		from .editing import create_table

		empty = create_table(
			{'Title': 'Nothing in it yet',
			 'Data properties': {'type': 'Z[]'},
			 'Parameters': {'n': {'type': 'Z'}}},
			author=self.author, published=False)
		self.client.force_login(self.author)
		self.client.post('/drafts/%s/offer' % (empty.tid,), {'ready': 'yes'})
		empty.refresh_from_db()
		self.assertFalse(empty.ready_for_review)

	def test_the_state_is_shown_on_the_drafts_page(self):
		self.client.force_login(self.author)
		self.assertIn('in progress', self.client.get('/drafts').content.decode())
		self._offer()
		self.assertIn('offered for review',
		              self.client.get('/drafts').content.decode())

	def test_the_api_can_propose_and_offer_in_one_step(self):
		import json

		from .models import ApiKey
		from .permissions import board_group

		self.author.groups.add(board_group())
		_, token = ApiKey.issue(self.author, label='one step')
		answer = self.client.post(
			'/api/tables',
			json.dumps({'Title': 'Proposed and offered',
			            'Data properties': {'type': 'Z[]'},
			            'Parameters': {'n': {'type': 'Z'}},
			            'Numbers': [{'params': {'n': '1'}, 'number': '1'}]}),
			content_type='application/json',
			HTTP_AUTHORIZATION='Bearer %s' % (token,), HTTP_X_DRAFT='ready')
		body = answer.json()
		self.assertFalse(body['published'])
		self.assertTrue(body['ready_for_review'])


class ADraftAnswersNoSearch(TestCase):
	"""A draft is invisible, and that has to include the search box.

	`search.py` had this from the start. The suggestions dropdown -- older,
	and a separate query -- did not, so an anonymous request for "Fibonacci"
	came back with two unpublished tables, their titles, their addresses and
	how many entries they held. The page behind them was properly refused,
	which made the leak quieter rather than smaller.
	"""

	def setUp(self):
		self.author = User.objects.create_user('hidden', password='pw-123456')
		self.draft = a_table('Quite unpublished Zebras', self.author)
		self.published = a_table('Quite published Zebras', self.author)
		from .editing import publish_table

		publish_table(self.published)

	def test_the_dropdown_does_not_name_a_draft(self):
		body = self.client.get('/suggestions', {'term': 'Zebras'}).content.decode()
		self.assertIn('Quite published Zebras', body)
		self.assertNotIn('Quite unpublished Zebras', body)

	def test_the_search_page_does_not_name_a_draft(self):
		body = self.client.get('/', {'q': 'Zebras'}).content.decode()
		self.assertNotIn('Quite unpublished Zebras', body)

	def test_not_even_for_its_own_author(self):
		#Not a permission question: the index is public, and a draft that
		#appears for one signed-in person appears in a cache for everybody.
		self.client.force_login(self.author)
		body = self.client.get('/suggestions', {'term': 'Zebras'}).content.decode()
		self.assertNotIn('Quite unpublished Zebras', body)
