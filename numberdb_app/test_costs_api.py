"""A build machine reports what it spent, over the API.

Costs used to reach the site by ssh: copy the ledger to the server, run a
management command there. That works from the one laptop with a key for that
server and from nowhere else, so the AWS builder's costs never arrived and the
overview under-counted everything it had spent.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .models import ApiKey, Table, TableCost
from .permissions import bulk_drafts_group

LEDGER = (
	"started\tstage\tengine\tturns\tcost_usd\tresult\tlog\tmodel\tprompt\t"
	"session\tresumed\ttokens_in\ttokens_cached\ttokens_out\tcost_by_model\ttable\n"
	"20260912T100000Z\tbuild\tcodex\t12\t3.50\tsuccess\tl\tgpt-5.5\t\t\t\t\t\t\t\tT700\n"
	"20260912T110000Z\tcritique\tclaude\t4\t1.25\tsuccess\tl\topus\t\t\t\t\t\t\t\tT700\n"
)


class ACostReportGoesThroughTheApi(TestCase):

	def setUp(self):
		self.table = Table.objects.create(
			tid='T700', tid_int=700, url='t700', title='A table',
			published=True)
		self.agent = get_user_model().objects.create_user('an-agent')
		self.agent.groups.add(bulk_drafts_group())
		self.outsider = get_user_model().objects.create_user('somebody-else')

	def key_for(self, user):
		key, raw = ApiKey.issue(user=user, name='test')
		return raw

	def post(self, user, body=LEDGER, **extra):
		return Client().post(
			'/api/costs', data=body.encode('utf8'),
			content_type='text/tab-separated-values',
			HTTP_AUTHORIZATION='Bearer ' + self.key_for(user),
			HTTP_HOST='numberdb.org', **extra)

	def test_the_costs_land_on_the_table(self):
		answer = self.post(self.agent)
		self.assertEqual(answer.status_code, 200)
		self.assertEqual(answer.json()['tables'], 1)
		rows = TableCost.objects.filter(table=self.table)
		self.assertEqual(rows.count(), 2)
		self.assertEqual(sum(r.cost_usd for r in rows), Decimal('4.75'))

	def test_sending_it_twice_is_not_paying_twice(self):
		self.post(self.agent)
		self.post(self.agent)
		rows = TableCost.objects.filter(table=self.table)
		self.assertEqual(rows.count(), 2)
		self.assertEqual(sum(r.cost_usd for r in rows), Decimal('4.75'))

	def test_a_run_naming_no_table_is_counted_as_unattributed(self):
		orphan = LEDGER + ("20260912T120000Z\tideas\tclaude\t9\t2.00\tsuccess"
		                   "\tl\topus\t\t\t\t\t\t\t\t\n")
		answer = self.post(self.agent, orphan)
		self.assertEqual(answer.json()['unattributed'], 1)

	def test_attribution_rescues_one(self):
		orphan = LEDGER + ("20260912T120000Z\tideas\tclaude\t9\t2.00\tsuccess"
		                   "\tl\topus\t\t\t\t\t\t\t\t\n")
		#Newlines cannot travel in a header; the sender swaps them for record
		#separators, which is the part most likely to be got wrong.
		answer = self.post(self.agent, orphan,
		                   HTTP_X_ATTRIBUTION='20260912T120000Z\tT700')
		self.assertEqual(answer.json()['rescued'], 1)
		self.assertEqual(answer.json()['unattributed'], 0)

	def test_an_ordinary_writer_may_not_rewrite_what_things_cost(self):
		answer = self.post(self.outsider)
		self.assertEqual(answer.status_code, 403)
		self.assertEqual(TableCost.objects.count(), 0)

	def test_a_dry_run_writes_nothing(self):
		answer = Client().post(
			'/api/costs?dry=1', data=LEDGER.encode('utf8'),
			content_type='text/tab-separated-values',
			HTTP_AUTHORIZATION='Bearer ' + self.key_for(self.agent),
			HTTP_HOST='numberdb.org')
		self.assertEqual(answer.json()['applied'], False)
		self.assertEqual(TableCost.objects.count(), 0)

	def test_an_empty_body_is_refused_rather_than_wiping_anything(self):
		self.post(self.agent)
		answer = self.post(self.agent, '   ')
		self.assertEqual(answer.status_code, 400)
		self.assertEqual(TableCost.objects.filter(table=self.table).count(), 2)
