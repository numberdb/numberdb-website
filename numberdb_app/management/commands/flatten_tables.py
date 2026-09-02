"""Convert tables to flat records, only where the rendering does not change.

The conversion is only worth anything if it is invisible. An entry's identity
is its parameter values, and every anchor, `?entry=`, cross-reference and
search result is built from it, so a flattening that quietly renumbered things
would break nothing visibly while pointing thousands of citations at the wrong
numbers.

So each table is converted, rendered both ways, and compared. A table whose
rendered page differs by so much as a character is left alone and reported.
Nothing is written until the comparison passes.
"""

import difflib

import yaml
from django.core.management.base import BaseCommand

from numberdb_app import flatten
from numberdb_app.editing import commit_table, dump_tree, without_managed_keys
from numberdb_app.models import Table


class Command(BaseCommand):
	help = 'Rewrite tables as flat records where rendering is unaffected.'

	def add_arguments(self, parser):
		parser.add_argument('--table', default='', help='one T-number')
		parser.add_argument('--check', action='store_true',
		                    help='compare only; write nothing')
		parser.add_argument('--limit', type=int, default=0)

	def handle(self, *args, **options):
		from numberdb_app.views import build_preview_context

		tables = Table.objects.select_related('data')
		if options['table']:
			tables = tables.filter(tid=options['table'])
		tables = tables.order_by('tid_int')
		if options['limit']:
			tables = tables[:options['limit']]

		same = differ = skipped = written = 0
		for table in tables:
			tree = yaml.load(table.data.full_yaml, Loader=yaml.BaseLoader) or {}
			block = flatten.entries_block(tree)
			if block is None:
				skipped += 1
				continue
			if flatten.is_flat(block):
				skipped += 1
				continue

			groups = flatten.parameter_groups(tree)
			records = flatten.to_records(tree)
			flat = dict(tree)
			flat.pop('Data', None)
			flat['Numbers'] = records

			try:
				before = build_preview_context(
					yaml.dump(tree, sort_keys=False))
				after = build_preview_context(
					yaml.dump(flat, sort_keys=False))
			except Exception as e:
				differ += 1
				self.stderr.write('%-6s could not render: %s' % (table.tid, e))
				continue

			if self.rendered(before) == self.rendered(after):
				same += 1
				if not options['check']:
					commit_table(
						table, without_managed_keys(flat),
						author=None, base=table.head_revision,
						produced_by='flattening',
						message='entries rewritten as records with named '
						        'parameters',
		via='orm')
					written += 1
			else:
				differ += 1
				self.report(table, self.rendered(before), self.rendered(after))

		self.stdout.write(self.style.SUCCESS(
			'%d identical, %d differ, %d skipped, %d written'
			% (same, differ, skipped, written)))

	def rendered(self, context):
		"""The parts of a rendered table that a reader actually sees."""
		return {k: v for k, v in context.items()
		        if k in ('sections', 'number_table_html', 'title',
		                 'param_groups_display', 'number_header')}

	def report(self, table, before, after):
		self.stderr.write('%-6s renders differently:' % (table.tid,))
		a = yaml.dump(before, default_flow_style=False).split('\n')
		b = yaml.dump(after, default_flow_style=False).split('\n')
		for line in list(difflib.unified_diff(a, b, 'nested', 'flat',
		                                      lineterm='', n=1))[:14]:
			self.stderr.write('    %s' % (line[:130],))
