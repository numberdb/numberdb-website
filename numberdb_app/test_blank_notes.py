"""A note made of spaces is not a note.

An entry's note is rendered as a line under its value. When the note is blank
the line is still drawn, and an empty line under a number reads as a value
that is missing something rather than as a value with nothing to say.
"""

from django.template.loader import render_to_string
from django.test import TestCase

SNIPPET = 'includes/number-extra-info-snippet.html'


class ABlankNoteIsNotShown(TestCase):

	def render(self, info):
		return render_to_string(SNIPPET, {'info': info}).strip()

	def test_a_real_note_is_shown(self):
		out = self.render({'comment': 'the Gaussian field'})
		self.assertIn('the Gaussian field', out)
		self.assertIn('comment', out)

	def test_a_note_of_spaces_is_not(self):
		out = self.render({'comment': '   '})
		self.assertNotIn('comment', out)

	def test_an_empty_note_is_not(self):
		self.assertNotIn('comment', self.render({'comment': ''}))

	def test_a_blank_one_does_not_hide_a_real_one(self):
		out = self.render({'comment': '  ', 'equals': 'HREF{Pi}'})
		self.assertNotIn('comment', out)
		self.assertIn('equals', out)

	def test_a_note_that_is_only_a_newline_is_not_shown(self):
		self.assertNotIn('comment', self.render({'comment': '\n'}))
