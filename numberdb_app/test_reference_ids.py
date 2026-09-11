"""A reference identifier is text, and YAML will not agree unless told.

`arxiv: 0705.4325` without quotes is the float 705.4325: the leading zero,
which is the year 2007, is gone by the time anything reads it. `zbl:
0668.12001` goes the same way. The file on disk is right and every reader of
it is wrong, which is the part that makes this worth a test -- it is invisible
in a diff and in review, and surfaces only when something loads the document
and writes it back, at which point the identifier points nowhere.

Found when a push of T219 showed the live table and the repository disagreeing
about an arXiv id that both of them stored correctly.
"""

import glob
import os

import yaml
from django.test import SimpleTestCase

#: Fields whose value is an identifier rather than a quantity. Every one of
#: them can begin with a zero, and several routinely do.
IDENTIFIER_FIELDS = ('arxiv', 'mr', 'zbl', 'doi', 'isbn')


def generator_tables():
	here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	return sorted(glob.glob(os.path.join(here, 'generators', '*', 'table.yaml')))


class ReferenceIdentifiersAreText(SimpleTestCase):

	def test_there_are_tables_to_check(self):
		#A glob that matches nothing passes every test below it.
		self.assertGreater(len(generator_tables()), 50)

	def test_no_identifier_is_read_as_a_number(self):
		wrong = []
		for path in generator_tables():
			with open(path, encoding='utf-8') as handle:
				document = yaml.safe_load(handle) or {}
			references = document.get('References') or {}
			if not isinstance(references, dict):
				continue
			for label, body in references.items():
				if not isinstance(body, dict):
					continue
				for field in IDENTIFIER_FIELDS:
					value = body.get(field)
					if value is not None and not isinstance(value, str):
						wrong.append('%s: %s.%s is %r' % (
							os.path.basename(os.path.dirname(path)),
							label, field, value))
		self.assertEqual(wrong, [], 'quote these: ' + '; '.join(wrong))

	def test_the_check_would_catch_one(self):
		#The failure mode itself, so the test cannot pass by looking at nothing.
		parsed = yaml.safe_load('References:\n  R:\n    arxiv: 0705.4325\n')
		self.assertEqual(parsed['References']['R']['arxiv'], 705.4325)
		self.assertNotIsInstance(parsed['References']['R']['arxiv'], str)
		quoted = yaml.safe_load("References:\n  R:\n    arxiv: '0705.4325'\n")
		self.assertEqual(quoted['References']['R']['arxiv'], '0705.4325')
