"""Move a repeated parameter label off the entries and onto the parameter.

An entry's identity is its plain parameter value -- `v: b`, which is what a
citation resolves on -- and `$b$` is how that value is displayed. Both are
needed. What is not needed is a copy of the display on every record: it is a
property of the value rather than of the entry, so one statement on the
parameter says what 723 copies were saying in T62.

All 5178 records in the corpus that carry `param-latex` have it determined
entirely by one parameter's value. T34 keeps 1002 copies of a label that takes
two distinct forms.

The labels move into the parameter's `values`, which doubles as the list of
values that parameter may take -- so a table that says how its values are
written has also said what they are.

Nothing is written unless the rendered table comes out identical.
"""

import yaml
from django.core.management.base import BaseCommand

from numberdb_app import flatten
from numberdb_app.editing import commit_table, tree_of, without_managed_keys
from numberdb_app.models import Table

LABEL = 'param-latex'


class Command(BaseCommand):
	help = 'Move repeated param-latex labels onto the parameter they describe.'

	def add_arguments(self, parser):
		parser.add_argument('--table', default='')
		parser.add_argument('--check', action='store_true')

	def handle(self, *args, **options):
		from numberdb_app.views import build_preview_context

		tables = Table.objects.exclude(head_revision=None)
		if options['table']:
			tables = tables.filter(tid=options['table'])

		moved = skipped = differed = 0
		for table in tables.select_related('head_revision').order_by('tid_int'):
			tree = tree_of(table.head_revision)
			hoisted = self.hoist(tree)
			if hoisted is None:
				skipped += 1
				continue

			try:
				before = build_preview_context(yaml.dump(tree, sort_keys=False))
				after = build_preview_context(yaml.dump(hoisted, sort_keys=False))
			except Exception as e:
				differed += 1
				self.stderr.write('%-6s could not render: %s' % (table.tid, e))
				continue

			if self.rendered(before) != self.rendered(after):
				differed += 1
				self.stderr.write('%-6s renders differently; left alone'
				                  % (table.tid,))
				continue

			labels = sum(1 for r in flatten.entries_block(tree) or []
			             if isinstance(r, dict) and LABEL in r)
			self.stdout.write('%-6s %4d copies -> %d statements'
			                  % (table.tid, labels,
			                     sum(len(v.get('values', {}))
			                         for v in hoisted['Parameters'].values()
			                         if isinstance(v, dict))))
			moved += 1
			if not options['check']:
				commit_table(table, without_managed_keys(hoisted),
				             author=None, base=table.head_revision,
				             produced_by='label hoist',
				             message='moved the parameter labels onto the '
				                     'parameter they describe')

		self.stdout.write(self.style.SUCCESS(
			'%d table(s) %s, %d unaffected, %d left alone'
			% (moved, 'would change' if options['check'] else 'changed',
			   skipped, differed)))

	def hoist(self, tree):
		"""The tree with the labels moved up, or None if there is nothing to do."""
		block = flatten.entries_block(tree)
		if not isinstance(block, list) or not isinstance(tree.get('Parameters'),
		                                                 dict):
			return None
		carrying = [r for r in block if isinstance(r, dict) and LABEL in r]
		if not carrying:
			return None

		names = [n for g in flatten.parameter_groups(tree) for n in g]
		for name in names:
			seen = {}
			consistent = True
			for record in carrying:
				value = str((record.get('params') or {}).get(name, ''))
				if not value:
					consistent = False
					break
				if seen.setdefault(value, record[LABEL]) != record[LABEL]:
					#Two records give the same value different labels, so the
					#label is not a property of the value after all.
					consistent = False
					break
			if not consistent or not seen:
				continue

			out = {k: (dict(v) if isinstance(v, dict) else v)
			       for k, v in tree.items()}
			out['Parameters'] = {
				k: (dict(v) if isinstance(v, dict) else v)
				for k, v in tree['Parameters'].items()}
			spec = out['Parameters'].get(name)
			if not isinstance(spec, dict):
				continue
			spec['values'] = dict(seen)
			out[_entries_key(tree)] = [
				{k: v for k, v in record.items() if k != LABEL}
				if isinstance(record, dict) else record
				for record in block]
			return out
		return None

	def rendered(self, context):
		return {k: v for k, v in context.items()
		        if k in ('sections', 'number_table_html', 'title',
		                 'param_groups_display', 'number_header')}


def _entries_key(tree):
	for name in ('Numbers', 'Data'):
		if name in tree:
			return name
	return 'Numbers'
