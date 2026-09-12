"""Read the agent ledger and put its costs on the tables.

	manage.py import_agent_costs [--ledger PATH] [--dry-run]

The work is in `numberdb_app.costs`, shared with `POST /api/costs`, so a
ledger imported from a file and a ledger sent by a build machine mean the
same thing. This command stays because it is what a person runs on the
server, and because the file is beside ATTRIBUTION.tsv.
"""

import os

from django.core.management.base import BaseCommand, CommandError

from numberdb_app.costs import ingest


class Command(BaseCommand):
	help = "Import agent run costs from the ledger TSV."

	def add_arguments(self, parser):
		parser.add_argument('--ledger', default='agents/runs/COSTS.tsv')
		parser.add_argument('--dry-run', action='store_true')

	def handle(self, *args, **options):
		path = options['ledger']
		try:
			with open(path, encoding='utf8', newline='') as handle:
				ledger = handle.read()
		except OSError as problem:
			raise CommandError(str(problem))

		#Beside the ledger, and only consulted for a row that names no table.
		attribution = ''
		beside = os.path.join(os.path.dirname(path), 'ATTRIBUTION.tsv')
		try:
			with open(beside, encoding='utf8') as handle:
				attribution = handle.read()
		except OSError:
			pass

		summary = ingest(ledger, attribution, dry_run=options['dry_run'])
		self.stdout.write(
			'%d cost rows over %d tables; %d runs named no table%s%s'
			% (summary['rows'], summary['tables'], summary['unattributed'],
			   '; %d attributed from ATTRIBUTION.tsv' % summary['rescued']
			   if summary['rescued'] else '',
			   '' if summary['applied'] else ' (nothing written)'))
