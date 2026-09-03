"""The credits page counts every table edit, not only the ones from GitHub.

`Contributor` is built from commits in the data repository, so the list
stopped counting the day the site could be edited without GitHub. It also
showed one person once per email address they had committed under.

Counted from the revisions instead, which is where an edit is recorded
whatever it arrived through. Contributors with no account are kept from the
old table: two people contributed before accounts existed, and a credits page
that drops somebody because of how they contributed is worse than a stale one.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .editing import commit_table
from .models import Contributor, Table


class WhoTheCreditsPageCounts(TestCase):

	def setUp(self):
		from .views import _contributors

		self.contributors = _contributors
		self.person = get_user_model().objects.create_user(
			'ada', email='ada@example.com', first_name='Ada',
			last_name='Lovelace')
		self.table = Table.objects.create(
			tid='T900', tid_int=900, url='t900', title='A table',
			published=True)

	def edit(self, author, n):
		for i in range(n):
			commit_table(self.table,
			             {'Title': 'A table', 'Numbers': {str(i + 1): '2'}},
			             author=author, message='m', via='orm')

	def named(self):
		return {row['name']: row['count'] for row in self.contributors()}

	def test_an_edit_that_never_touched_github_is_counted(self):
		self.edit(self.person, 3)
		self.assertEqual(self.named().get('Ada Lovelace'), 3)

	def test_a_person_is_named_once_however_many_emails_they_committed_under(self):
		self.edit(self.person, 2)
		for email in ('ada@example.com', 'ada@users.noreply.github.com'):
			Contributor.objects.create(
				author_and_email='Ada Lovelace | %s' % (email,),
				author='Ada Lovelace', email=email, table_commit_count=5)
		names = [row['name'] for row in self.contributors()]
		self.assertEqual(names.count('Ada Lovelace'), 1)

	def test_a_contributor_with_no_account_is_kept(self):
		Contributor.objects.create(
			author_and_email='Grace Hopper | grace@example.com',
			author='Grace Hopper', email='grace@example.com',
			table_commit_count=4)
		self.assertEqual(self.named().get('Grace Hopper'), 4)

	def test_their_commits_are_not_counted_twice(self):
		#The account's own edits come from the revisions; the old table is
		#only consulted for emails no account has.
		self.edit(self.person, 3)
		Contributor.objects.create(
			author_and_email='Ada Lovelace | ada@example.com',
			author='Ada Lovelace', email='ada@example.com',
			table_commit_count=99)
		self.assertEqual(self.named().get('Ada Lovelace'), 3)

	def test_a_program_says_so(self):
		from .models import UserProfile

		bot = get_user_model().objects.create_user('probe3')
		UserProfile.objects.update_or_create(
			user=bot, defaults={'operated_by': self.person})
		self.edit(bot, 1)
		rows = {row['name']: row for row in self.contributors()}
		self.assertTrue(rows['probe3']['program'])
		self.assertFalse(rows['Ada Lovelace']['program']
		                 if 'Ada Lovelace' in rows else False)

	def test_the_page_renders_them(self):
		self.edit(self.person, 2)
		body = Client().get('/help', HTTP_HOST='numberdb.org').content.decode()
		self.assertIn('Ada Lovelace', body)

	def test_nobody_with_no_edits_is_listed(self):
		Contributor.objects.create(
			author_and_email='Nobody | nobody@example.com',
			author='Nobody', email='nobody@example.com', table_commit_count=0)
		self.assertNotIn('Nobody', self.named())

	def test_the_busiest_contributor_is_first(self):
		other = get_user_model().objects.create_user(
			'bob', email='bob@example.com', first_name='Bob', last_name='B')
		self.edit(self.person, 1)
		self.edit(other, 4)
		self.assertEqual(self.contributors()[0]['name'], 'Bob B')
