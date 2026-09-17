"""A section of prose holding something other than prose.

T313 was published with its Formulas written as

    mirror:
      display: mirror image
      formula: $\\operatorname{CS}(S^3\\setminus \\bar K)\\equiv ...$

a shape invented for a caption, which nothing on the site reads. The page
shows what it finds, so the table's Formulas section read

    (1) {'display': 'mirror image', 'formula': '

to every reader, with the LaTeX inside never set. Nothing refused the
document, and nothing noticed until a person opened the page.

The same failure as the eaten backslash in `test_eaten_backslash`: it parses,
it saves, and the damage is visible only to somebody reading the page.
"""

from django.test import TestCase

from .validate import check, problems
from .editing import InvalidDocument


def document(formulas):
	return {'Title': 'A table', 'Formulas': formulas, 'Numbers': {'1': '2'}}


CAPTIONED = {'mirror': {'display': 'mirror image',
                        'formula': '$\\operatorname{CS}(\\bar K)=-'
                                   '\\operatorname{CS}(K)$'}}


class ProseHasToBeProse(TestCase):

	def test_a_formula_written_as_a_mapping_is_refused(self):
		#Exactly what T313 held.
		with self.assertRaises(InvalidDocument):
			check(document(CAPTIONED))

	def test_it_names_the_label_and_offers_the_prose(self):
		found = problems(document(CAPTIONED))
		self.assertTrue(any('mirror' in p.message for p in found), found)
		#The strings inside are what the author wrote; giving them back saves
		#rereading the document to find out what was lost.
		self.assertTrue(any('mirror image' in p.message for p in found), found)

	def test_a_comment_written_as_a_mapping_is_refused_too(self):
		with self.assertRaises(InvalidDocument):
			check({'Title': 'A table', 'Numbers': {'1': '2'},
			       'Comments': {'c': ['one', 'two']}})

	def test_a_definition_that_is_not_a_sentence_is_refused(self):
		with self.assertRaises(InvalidDocument):
			check({'Title': 'A table', 'Numbers': {'1': '2'},
			       'Definition': {'text': 'what these numbers are'}})

	def test_prose_passes(self):
		self.assertEqual(
			check(document({'mirror': 'Mirror reversal changes the sign: '
			                          '$\\operatorname{CS}(\\bar K)\\equiv-'
			                          '\\operatorname{CS}(K)\\pmod{1/2}$.'})),
			[])

	def test_an_empty_section_is_not_a_fault(self):
		#`Formulas:` with nothing under it is how half the corpus writes a
		#section it has nothing to put in.
		self.assertEqual(check(document(None)), [])
		self.assertEqual(check(document({})), [])
