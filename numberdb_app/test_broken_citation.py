"""A citation that points at nothing must not take the page down.

T197 answered 500 for a day. Its `formula-fresnel-erf` cited
`formula-fresnel-definitions`, which had gone to the Fresnel tables when the
table was split, and the renderer raised `ValueError: unknown label` on it --
so a thousand values, every formula and the whole definition were unreadable
because of one footnote.

Two things follow, and this tests both: the renderer serves the page and marks
the citation, and `commit_table` refuses the document from a writer that
cannot be shown a warning.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .editing import InvalidDocument, commit_table
from .models import Table
from .validate import problems, unresolved_citations


def a_table(**extra):
	tree = {'Title': 'A table', 'Numbers': {'1': '2'}}
	tree.update(extra)
	return tree


class ABrokenCitationStillRenders(TestCase):

	def setUp(self):
		self.user = get_user_model().objects.create_user('author')
		self.table = Table.objects.create(
			tid='T700', tid_int=700, url='t700', title='A table',
			published=True)

	def page(self, tree):
		commit_table(self.table, tree, author=self.user, message='m', via='orm')
		answer = Client().get('/T700', HTTP_HOST='numberdb.org')
		self.assertEqual(answer.status_code, 200)
		return answer.content.decode()

	def test_the_page_is_served(self):
		body = self.page(a_table(Comments={
			'c': 'as shown in CITE{formula-that-moved}, the value is small'}))
		self.assertIn('the value is small', body)

	def test_the_label_is_shown_and_marked(self):
		body = self.page(a_table(Comments={
			'c': 'as shown in CITE{formula-that-moved}, the value is small'}))
		self.assertIn('formula-that-moved', body)
		self.assertIn('CITE-broken', body)

	def test_a_citation_that_resolves_is_a_link_as_before(self):
		body = self.page(a_table(
			Comments={'c': 'see CITE{formula-recurrence} for the rest'},
			Formulas={'formula-recurrence': '$a_{n+1}=2a_n$'}))
		self.assertIn('class="CITE"', body)
		self.assertNotIn('CITE-broken', body)

	def test_an_unclosed_citation_does_not_raise(self):
		body = self.page(a_table(Comments={'c': 'a stray CITE{ and more text'}))
		self.assertIn('and more text', body)

	def test_a_comment_on_an_entry_is_checked_too(self):
		#Entry comments are prose and are rendered by the same function.
		tree = a_table(Numbers={'1': {'number': '2', 'comment': 'CITE{gone}'}})
		self.assertEqual(unresolved_citations(tree), ['gone'])


class TheDocumentIsRefusedBeforeItIsStored(TestCase):

	def setUp(self):
		self.user = get_user_model().objects.create_user('writer')
		self.table = Table.objects.create(
			tid='T701', tid_int=701, url='t701', title='A table')

	def test_a_strict_writer_is_refused(self):
		tree = a_table(Comments={'c': 'see CITE{nothing-here}'})
		with self.assertRaises(InvalidDocument) as caught:
			commit_table(self.table, tree, author=self.user, message='m',
			             via='api', strict=True)
		self.assertIn('nothing-here', str(caught.exception))

	def test_a_person_on_the_site_is_warned_and_saved(self):
		tree = a_table(Comments={'c': 'see CITE{nothing-here}'})
		outcome = commit_table(self.table, tree, author=self.user,
		                       message='m', via='web')
		self.assertTrue(any('nothing-here' in p.message
		                    for p in outcome.problems))
		self.assertIsNotNone(outcome.revision)

	def test_a_resolving_citation_passes_the_gate(self):
		tree = a_table(Comments={'c': 'see CITE{Ref1}'},
		               References={'Ref1': 'A paper'})
		outcome = commit_table(self.table, tree, author=self.user,
		                       message='m', via='api', strict=True)
		self.assertIsNotNone(outcome.revision)

	def test_the_labels_a_citation_may_name(self):
		tree = a_table(
			Links={'Wiki': 'https://example.invalid'},
			References={'Pla15': 'A paper'},
			Formulas={'formula-a': '$x$'},
			Comments={'comment-b': 'CITE{Wiki} CITE{Pla15} CITE{formula-a} '
			                       'CITE{comment-b} CITE{missing}'})
		self.assertEqual(unresolved_citations(tree), ['missing'])

	def test_it_is_a_warning_and_not_fatal(self):
		found = [p for p in problems(a_table(Comments={'c': 'CITE{nope}'}))
		         if 'nope' in p.message]
		self.assertEqual(len(found), 1)
		self.assertFalse(found[0].fatal)
