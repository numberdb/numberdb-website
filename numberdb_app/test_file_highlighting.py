"""A generator is the most-read code on the site and was shown as grey text.

It is what somebody opens to find out how a number was made. The table page
has highlighted its Programs block for a long time; the file view, which shows
the whole generator, did not.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .editing import attach_files, commit_table
from .models import Table


class AGeneratorIsShownAsCode(TestCase):

	def setUp(self):
		self.user = get_user_model().objects.create_user('filer')
		self.table = Table.objects.create(
			tid='T750', tid_int=750, url='t750', title='A table with a file',
			published=True)
		commit_table(self.table, {'Title': 'A table with a file',
		                          'Numbers': {'1': '2'}},
		             author=self.user, message='m', via='orm',
		             files={'generate.py': b'x = 1\nprint(x)\n',
		                    'notes.txt': b'plain words\n'})

	def page(self, name):
		return Client().get('/files/%s/%s' % (self.table.tid, name),
		                    HTTP_HOST='numberdb.org').content.decode()

	def test_python_is_marked_as_python(self):
		body = self.page('generate.py')
		self.assertIn('language-python', body)

	def test_the_highlighter_is_loaded(self):
		self.assertIn('highlight.min.js', self.page('generate.py'))

	def test_a_plain_file_is_not_guessed_at(self):
		#highlight.js guesses when it is given nothing, and guesses badly on
		#a table of numbers.
		body = self.page('notes.txt')
		self.assertIn('language-none', body)
		self.assertNotIn('language-python', body)

	def test_the_source_is_still_shown(self):
		self.assertIn('print(x)', self.page('generate.py'))
