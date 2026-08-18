"""Who made a revision, and what the trust ladder counts.

The author of a submission is the person whose key published it: authorship is
accountability, and a model can neither answer for a wrong value nor agree to
the licence. What an assistant did is disclosed as a method, in `produced_by`,
which readers already see in the blame and history views.

See docs/design/ai-provenance.md.
"""

from django.test import TestCase


class TheTrustLadderCountsPeople(TestCase):
	"""`accepted_edit_count` opens API write access, and was built against
	farming: it counts reviews rather than approvals, because "a script can
	farm" approval. An assistant whose operator reviews its own output farms it
	just as effectively and more politely.
	"""

	def setUp(self):
		from django.contrib.auth.models import User

		from .editing import create_table

		self.author = User.objects.create_user('agent_operator', password='pw-123456')
		self.other = User.objects.create_user('somebody_else', password='pw-123456')
		self.table = create_table(
			{'Title': 'Ladder probe',
			 'Data properties': {'type': 'R'},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '3.14'}]},
			author=self.author,
			produced_by='Probe (numberdb=0.1.2), assisted by claude-opus-5')

	def _review(self, reviewer):
		self.table.reviewed_at_revision = self.table.head_revision
		self.table.reviewed_by = reviewer
		self.table.save(update_fields=['reviewed_at_revision', 'reviewed_by'])

	def test_an_assisted_revision_the_author_reviewed_does_not_count(self):
		from .permissions import accepted_edit_count

		self._review(self.author)
		self.assertEqual(accepted_edit_count(self.author), 0)

	def test_an_assisted_revision_somebody_else_reviewed_does_count(self):
		#The point is not to penalise using a tool. It is to require that
		#somebody other than its operator looked.
		from .permissions import accepted_edit_count

		self._review(self.other)
		self.assertEqual(accepted_edit_count(self.author), 1)

	def test_a_hand_made_revision_counts_however_it_was_reviewed(self):
		from django.contrib.auth.models import User

		from .editing import create_table
		from .permissions import accepted_edit_count

		person = User.objects.create_user('by_hand', password='pw-123456')
		table = create_table(
			{'Title': 'Hand made probe',
			 'Data properties': {'type': 'R'},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '2.71'}]},
			author=person, produced_by='web')
		table.reviewed_at_revision = table.head_revision
		table.reviewed_by = person
		table.save(update_fields=['reviewed_at_revision', 'reviewed_by'])

		self.assertEqual(accepted_edit_count(person), 1)

	def test_reviews_from_before_the_reviewer_was_recorded_still_count(self):
		#Null reviewer means the review predates this field. Those were the
		#board's, and refusing them would rewrite history to punish it.
		from .permissions import accepted_edit_count

		self.table.reviewed_at_revision = self.table.head_revision
		self.table.reviewed_by = None
		self.table.save(update_fields=['reviewed_at_revision', 'reviewed_by'])
		self.assertEqual(accepted_edit_count(self.author), 1)


class TheDisclosureIsVisible(TestCase):
	"""A disclosure nobody sees is not one.

	The history showed the *author* instead of the producer when a revision had
	one, so an assisted publish under somebody's key looked exactly like their
	own work -- which is the only case the disclosure exists for.
	"""

	def setUp(self):
		from django.contrib.auth.models import User

		from .editing import create_table

		self.user = User.objects.create_user('publisher', password='pw-123456')
		self.table = create_table(
			{'Title': 'Disclosure probe',
			 'Data properties': {'type': 'R'},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '3.14'}]},
			author=self.user,
			produced_by='Probe (numberdb=0.1.2, sage=10.9), assisted by claude-opus-5')

	def test_the_property_pulls_out_the_tool(self):
		self.assertEqual(self.table.head_revision.assisted_by, 'claude-opus-5')

	def test_a_revision_nobody_assisted_names_no_tool(self):
		from .editing import create_table

		table = create_table(
			{'Title': 'Unassisted probe',
			 'Data properties': {'type': 'R'},
			 'Parameters': {'n': {'type': 'Z'}},
			 'Numbers': [{'params': {'n': '1'}, 'number': '2.71'}]},
			author=self.user, produced_by='Probe (numberdb=0.1.2)')
		self.assertEqual(table.head_revision.assisted_by, '')

	def test_the_history_shows_the_tool_next_to_the_author(self):
		body = self.client.get('/revisions/%s' % (self.table.tid,)).content.decode()
		self.assertIn('publisher', body)
		self.assertIn('claude-opus-5', body)
