"""Exactly one worker may hold a proposal.

The queue is a checklist in a GitHub issue, and claiming a line of it means
rewriting the body -- which two workers can do in the same second, each losing
the other's edit. Every proposal of numberdb-data#178 was claimed within one
minute that way, and none was built.
"""

import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from .models import ApiKey, ProposalClaim


class OnlyOneWorkerGetsIt(TestCase):

	def setUp(self):
		from django.contrib.auth.models import Group

		from .permissions import TRUSTED_GROUP

		self.user = User.objects.create_user('claimer', password='x')
		#Trust is a group, not a flag on the profile: see permissions.py.
		self.user.groups.add(Group.objects.get_or_create(
			name=TRUSTED_GROUP)[0])
		_, self.token = ApiKey.issue(user=self.user, label='test')

	def claim(self, worker, proposal='Weight enumerators', family=178):
		return self.client.post(
			'/api/claim',
			data=json.dumps({'family': family, 'proposal': proposal,
			                 'worker': worker}),
			content_type='application/json', HTTP_HOST='numberdb.org',
			HTTP_AUTHORIZATION='Bearer %s' % (self.token,))

	def release(self, proposal='Weight enumerators', family=178):
		return self.client.delete(
			'/api/claim',
			data=json.dumps({'family': family, 'proposal': proposal}),
			content_type='application/json', HTTP_HOST='numberdb.org',
			HTTP_AUTHORIZATION='Bearer %s' % (self.token,))

	def test_the_first_worker_takes_it(self):
		answer = self.claim('w2')
		self.assertEqual(answer.status_code, 201)
		self.assertTrue(answer.json()['claimed'])

	def test_the_second_is_told_who_has_it(self):
		self.claim('w2')
		answer = self.claim('w4')
		self.assertEqual(answer.status_code, 409)
		self.assertFalse(answer.json()['claimed'])
		self.assertEqual(answer.json()['worker'], 'w2')

	def test_a_different_proposal_is_free(self):
		self.claim('w2')
		self.assertEqual(self.claim('w4', proposal='Eberlein polynomials')
		                 .status_code, 201)

	def test_releasing_gives_it_back(self):
		self.claim('w2')
		self.assertTrue(self.release().json()['released'])
		self.assertEqual(self.claim('w4').status_code, 201)

	def test_an_expired_claim_is_taken_over(self):
		#A worker that died holding a proposal must not keep it out of the
		#queue for ever.
		self.claim('w2')
		held = ProposalClaim.objects.get()
		ProposalClaim.objects.filter(pk=held.pk).update(
			claimed_at=timezone.now()
			- timezone.timedelta(minutes=ProposalClaim.MINUTES + 1))
		answer = self.claim('w4')
		self.assertEqual(answer.status_code, 201)
		self.assertEqual(answer.json()['took_over_from'], 'w2')
		self.assertEqual(ProposalClaim.objects.count(), 1)

	def test_what_is_held_can_be_read_without_a_key(self):
		self.claim('w2')
		answer = self.client.get('/api/claim?family=178',
		                         HTTP_HOST='numberdb.org')
		self.assertEqual(answer.status_code, 200)
		self.assertEqual([c['worker'] for c in answer.json()['claims']], ['w2'])

	def test_an_expired_claim_is_not_listed_as_held(self):
		self.claim('w2')
		ProposalClaim.objects.update(
			claimed_at=timezone.now()
			- timezone.timedelta(minutes=ProposalClaim.MINUTES + 1))
		answer = self.client.get('/api/claim?family=178',
		                         HTTP_HOST='numberdb.org')
		self.assertEqual(answer.json()['claims'], [])

	def test_a_stranger_may_not_claim(self):
		answer = self.client.post(
			'/api/claim',
			data=json.dumps({'family': 1, 'proposal': 'anything',
			                 'worker': 'nobody'}),
			content_type='application/json', HTTP_HOST='numberdb.org')
		self.assertIn(answer.status_code, (401, 403))
