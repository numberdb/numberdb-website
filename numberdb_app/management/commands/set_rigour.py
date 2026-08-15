"""Write the audited rigour level into each table's Data properties.

The audit itself is `docs/rigour-audit.tsv`: one line per table, with the
evidence for its level. It is a file rather than a script so that the
judgement can be read, argued with and corrected -- it is a claim about 88
tables, and most of it was made by reading one line of each generator.

Run it dry first. It writes a revision per table, and 88 revisions is not
something to discover afterwards:

    manage.py set_rigour --dry-run
    manage.py set_rigour --author bmatschke

A table that already states a level is left alone unless `--overwrite` says
otherwise: two tables were labelled by their generators, which know better than
this file does.
"""

import os

from django.core.management.base import BaseCommand, CommandError

#: What each level says, for the `rigour details` line.
#:
#: Every level has one, so the line can never be left over from a level the
#: table used to have. T61 said "proven" above "a fixed-precision value wrapped
#: in an interval field, which records no error of its own" for a day, because
#: the level was corrected upward and the sentence was not: a page contradicting
#: itself, and reading as though the proof were being retracted underneath.
DETAILS = {
	'exact':
		'An exact value -- an integer, a rational or a polynomial -- so there '
		'is no precision to choose and nothing to be wrong about.',
	'proven':
		'Computed in interval or ball arithmetic throughout, so the digits '
		'written follow from the width of the result rather than from a guard '
		'chosen in advance.',
	'heuristic (agreement-checked)':
		'Computed twice at different working precisions, keeping only the '
		'digits both computations support. That bounds the error from working '
		'precision and nothing else: two runs of the same method agree even '
		'when the method is wrong.',
	'measured':
		'Not computed: the value comes from experiment, and the interval is '
		'chosen to hold the measurements together with their stated '
		'uncertainties. See the reliability note for which measurements.',
	'assumed-bound':
		'The computed interval was widened by four units in the last place '
		'(blur_real_interval). That bound was asserted rather than derived, '
		'and the justification was not recorded.',
	'heuristic':
		'A fixed-precision value wrapped in an interval field, which records '
		'no error of its own. The working precision was half as many digits '
		'again as were written, and nothing checked that the margin sufficed.',
}

#: The sentences this command has written. Anything else in `rigour details` is
#: somebody's prose and is left alone; these are ours to replace when the level
#: changes under them.
OURS = frozenset(DETAILS.values())


class Command(BaseCommand):
	help = "Set each table's rigour from docs/rigour-audit.tsv."

	def add_arguments(self, parser):
		parser.add_argument('--file', default='docs/rigour-audit.tsv')
		parser.add_argument('--author', default='',
		                    help='username the revisions are attributed to')
		parser.add_argument('--dry-run', action='store_true')
		parser.add_argument('--overwrite', action='store_true',
		                    help='replace a level a table already states')

	def handle(self, *args, **options):
		from django.contrib.auth.models import User

		from numberdb_app.editing import commit_table, tree_of
		from numberdb_app.models import Table
		from numberdb_app.validate import RIGOUR_LEVELS

		path = options['file']
		if not os.path.exists(path):
			raise CommandError('No audit file at %s' % (path,))

		author = None
		if options['author']:
			try:
				author = User.objects.get(username=options['author'])
			except User.DoesNotExist:
				raise CommandError('No user %r' % (options['author'],))

		wanted = []
		for line in open(path, encoding='utf8'):
			line = line.rstrip('\n')
			if not line or line.startswith('#'):
				continue
			tid, level, evidence, detail = (line.split('\t') + ['', '', ''])[:4]
			if level not in RIGOUR_LEVELS:
				raise CommandError('%s: %r is not a rigour level' % (tid, level))
			wanted.append((tid, level, evidence, detail.strip()))

		set_ = skipped = missing = unchanged = 0
		for tid, level, evidence, detail in wanted:
			try:
				table = Table.objects.get(tid=tid)
			except Table.DoesNotExist:
				missing += 1
				self.stderr.write('  %-6s no such table' % (tid,))
				continue

			tree = tree_of(table.head_revision)
			properties = dict(tree.get('Data properties') or {})
			already = properties.get('rigour')

			if already and already != level and not options['overwrite']:
				skipped += 1
				self.stdout.write('  %-6s already says %r, leaving it'
				                  % (tid, already))
				continue

			properties['rigour'] = level

			#The detail must follow the level, or a corrected label leaves the
			#old explanation sitting under it. Only sentences this command
			#wrote are replaced; anything a person put there is theirs.
			#A fourth column in the audit gives this table its own sentence,
			#for the tables the generic one does not fit: `proven` usually
			#means ball arithmetic, but T5's interval is a pair of theorems and
			#T3's zeros were checked against arb's certified enclosures.
			#Neither is described by "computed in interval arithmetic
			#throughout", and a sentence that is nearly right is worse here
			#than none.
			existing = properties.get('rigour details')
			if not existing or existing in OURS:
				chosen = detail or DETAILS.get(level)
				if chosen:
					properties['rigour details'] = chosen
				else:
					properties.pop('rigour details', None)

			#Skip on nothing-to-change rather than on level-matches. The two are
			#not the same: a table whose level was corrected upward keeps the
			#right level and the wrong sentence, and an early continue on the
			#level alone is exactly why thirteen of them went out contradicting
			#themselves.
			if properties == (tree.get('Data properties') or {}):
				unchanged += 1
				continue

			tree = dict(tree)
			tree['Data properties'] = properties

			set_ += 1
			if options['dry_run']:
				self.stdout.write('  %-6s -> %-30s %s' % (tid, level, evidence))
				continue

			commit_table(
				table, tree, author=author, base=table.head_revision,
				produced_by='rigour-audit',
				message='how well the digits are known: %s (%s)'
				        % (level, evidence))

		self.stdout.write(
			'%s %d table(s); %d already correct, %d left alone, %d missing.'
			% ('would set' if options['dry_run'] else 'set',
			   set_, unchanged, skipped, missing))
