"""`rigour details` may have paragraphs, bullets and a fold.

It is the one metadata field with something long to say: 139 tables carry it,
the median is 199 characters and the longest five run to three thousand. Every
one of those 139 was written as a single paragraph, because a newline was the
only structure the field offered and nobody reached for it.
"""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .editing import commit_table
from .models import Table
from .prose import render


class TheProseRenderer(TestCase):

	def renderer(self, text, line_breaks=True):
		#Stands in for the page's own, which escapes and resolves CITE/HREF.
		return text.replace('<', '&lt;')

	def test_a_short_note_is_not_folded(self):
		#A field of one sentence should look like a field, not like a
		#disclosure with nothing worth disclosing.
		head, rest = render('The values come from arb.', self.renderer)
		self.assertIn('The values come from arb.', head)
		self.assertEqual(rest, '')

	def test_blank_lines_make_paragraphs(self):
		head, rest = render('One.\n\nTwo.', self.renderer)
		self.assertEqual((head + rest).count('<p class="prose-paragraph">'), 2)

	def test_dashes_make_a_list(self):
		head, rest = render('Checked:\n\n- against PARI\n- against OEIS',
		                    self.renderer)
		body = head + rest
		self.assertIn('<ul class="prose-list">', body)
		self.assertEqual(body.count('<li>'), 2)

	def test_backticks_make_code(self):
		head, _ = render('Computed with `qfminim`.', self.renderer)
		self.assertIn('<code class="prose-code">qfminim</code>', head)

	def test_a_long_note_keeps_its_first_paragraph_and_folds_the_rest(self):
		text = ('The summary sentence.\n\n' + 'x' * 500)
		head, rest = render(text, self.renderer)
		self.assertIn('The summary sentence.', head)
		self.assertNotIn('x' * 500, head)
		self.assertIn('x' * 500, rest)

	def test_nothing_gives_nothing(self):
		self.assertEqual(render('', self.renderer), ('', ''))


class TheTablePageShowsIt(TestCase):

	def setUp(self):
		self.user = get_user_model().objects.create_user('prose_author')
		self.table = Table.objects.create(
			tid='T770', tid_int=770, url='t770', title='A table',
			published=True)

	def page(self, details):
		commit_table(self.table,
		             {'Title': 'A table', 'Numbers': {'1': '2'},
		              'Data properties': {'type': 'Z', 'rigour': 'proven',
		                                  'rigour details': details}},
		             author=self.user, message='m', via='orm')
		return Client().get('/T770', HTTP_HOST='numberdb.org').content.decode()

	def test_a_short_one_renders_inline(self):
		#The element, not the class name: the stylesheet names the class on
		#every page whether or not anything is folded.
		body = self.page('Exact integers from a recurrence.')
		self.assertIn('<p class="prose-paragraph">Exact integers from a '
		              'recurrence.</p>', body)
		self.assertNotIn('<details class="prose-more">', body)

	def test_a_long_one_is_folded_behind_a_disclosure(self):
		body = self.page('The short version.\n\n' + 'Detail. ' * 80)
		self.assertIn('The short version.', body)
		self.assertIn('<details class="prose-more">', body)
		self.assertIn('<summary>more</summary>', body)

	def test_mathematics_still_works_inside_it(self):
		body = self.page('Balls in arb, so $\\delta^2$ is exact.')
		self.assertIn('\\delta^2', body)
