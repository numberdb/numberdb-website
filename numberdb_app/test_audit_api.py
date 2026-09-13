"""A machine with no database can still audit the table it just built.

The checks need the database, so they live in a management command -- and a
build machine has no database and should not have one: it reaches this site
over the public API like any outside contributor. So the run that built T223
reported "I could not run `manage.py audit_table T223` because this checkout
has no Django installed", the prose audit never ran on it, and a sentence
claiming more than it should have reached a reader. The audit's own check for
a named constant with no link would have caught it.
"""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .editing import commit_table
from .models import Table


class TheAuditAnswersOverTheApi(TestCase):

	def setUp(self):
		self.user = get_user_model().objects.create_user('author')
		self.table = Table.objects.create(
			tid='T700', tid_int=700, url='t700', title='A table',
			published=True)

	def write(self, tree):
		commit_table(self.table, tree, author=self.user, message='m', via='orm')
		self.table.refresh_from_db()

	def audit(self, tid='T700'):
		return Client().get('/api/table/%s/audit' % tid, HTTP_HOST='numberdb.org')

	def test_a_clean_table_says_so(self):
		self.write({'Title': 'A table', 'Numbers': {'1': '2'},
		            'Definition': 'A short definition of the numbers here.'})
		answer = self.audit()
		self.assertEqual(answer.status_code, 200)
		self.assertEqual(answer.json()['clean'], True)
		self.assertEqual(answer.json()['findings'], [])

	def test_a_dangling_citation_is_reported(self):
		self.write({'Title': 'A table', 'Numbers': {'1': '2'},
		            'Comments': {'c': 'as in CITE{nowhere}'}})
		findings = self.audit().json()['findings']
		self.assertTrue(any('nowhere' in f for f in findings), findings)
		self.assertEqual(self.audit().json()['clean'], False)

	def test_it_names_the_table_it_audited(self):
		self.write({'Title': 'A table', 'Numbers': {'1': '2'}})
		body = self.audit().json()
		self.assertEqual(body['tid'], 'T700')
		self.assertEqual(body['title'], 'A table')

	def test_an_unknown_table_is_a_404(self):
		self.assertEqual(self.audit('T9999').status_code, 404)

	def test_a_draft_is_not_audited_for_a_stranger(self):
		#The same answer the table itself gives: a draft does not exist for
		#somebody who may not see it.
		draft = Table.objects.create(tid='T701', tid_int=701, url='t701',
		                             title='A draft', published=False)
		commit_table(draft, {'Title': 'A draft', 'Numbers': {'1': '2'}},
		             author=self.user, message='m', via='orm')
		self.assertEqual(self.audit('T701').status_code, 404)
