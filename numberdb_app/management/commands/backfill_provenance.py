"""Give every revision that has one a run, and say how sure we are.

    manage.py backfill_provenance --versions agents/backfill/versions.json \\
        --ledger agents/backfill/COSTS-builder.tsv:aws-builder \\
        --ledger agents/backfill/COSTS-laptop.tsv:laptop
    manage.py backfill_provenance ... --write      # without this, nothing is saved

The record this fills in was lost one field at a time: eight spellings of
"codex" in a free-text column, no version of any prompt anywhere, and a run
identifier on revisions that named a generator object while the cost ledger
keyed on a timestamp. See docs/design/pipeline-provenance.md.

**Four kinds of evidence, and a row is never better than its evidence.**
`AgentRun.source` says which was used:

  `ledger`   A cost ledger row: the run stamp, stage, engine, model, prompt
             version, harness session, campaign, batch, turns, tokens and cost.
             This is a contemporaneous record written by the runner, and it is
             the strongest thing here short of the run recording itself.

  `reconstructed`  A revision whose own message names what made it: the 268
             imported from numberdb-data say *"from the data repository,
             fc072a35"*, and a commit is a fact. Corpus-wide migrations
             (`rigour-audit`, `flattening`, `label hoist`) are the same case:
             a named one-off, by a person, on a day.

  `inferred` The revision's `produced_by` string and its timestamp, and
             nothing else. `assisted by Claude Opus 5` says a model and not a
             run; two revisions a minute apart under one account on one day are
             *probably* one session, and probably is what this level means.

  `declared` Reserved for what a submitter asserts through the API from now on.
             Never written here.

**Linking is by table and time, and refuses ties.** A ledger run that names
T219 claims the revisions of T219 between its start and its end. Where two
runs could claim one revision, neither does: a wrong link is worse than a
missing one, because a missing one is visibly missing.

The pipeline *version* comes from the reconstructed history in `--versions`,
produced by `agents/pipeline.py dump` on a machine that has the repository --
the deployed tree has no `.git`, so the history cannot be computed here. A run
is given the version that was in force when it started; where the ledger's own
`prompt@commit` disagrees, the disagreement is written into `notes` rather
than resolved silently.
"""

import csv
import io
import json
import os
import re
from collections import Counter, defaultdict
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from django.utils import timezone


#: Stage to pipeline. The stage is what the ledger records; the pipeline is
#: what declares a scope and therefore what has versions.
PIPELINE_OF = {
	'ideas': 'table-ideas',
	'build': 'table-build',
	'critique': 'table-critique',
	'repair': 'table-repair',
	'split': 'table-split',
	'triage': 'triage',
}

#: The harness, spelt one way. `claude` and `codex` in a ledger are the CLIs,
#: not the models; the model is its own column and its own field.
ENGINE_OF = {
	'claude': 'claude-code',
	'codex': 'codex-cli',
}

#: How long after a run started a revision may still be its work. A build run
#: takes minutes to an hour; the ledger records no end time, so this is the
#: window and it is deliberately generous, because the tie rule below is what
#: actually prevents a wrong link.
WINDOW = timedelta(hours=3)

#: `produced_by` strings that are a person's one-off over the whole corpus,
#: not a pipeline. Each becomes one run per day it touched anything.
MIGRATIONS = ('rigour-audit', 'flattening', 'label hoist',
              'data-repository import', 'correction')

#: What the eight spellings meant. Order matters: the longest match wins, so
#: `claude-opus-5` is not read as `claude`.
SPELLINGS = (
	('claude fable 5.1', ('claude-code', 'claude-fable-5-1')),
	('claude-fable-5', ('claude-code', 'claude-fable-5')),
	('claude opus 5', ('claude-code', 'claude-opus-5')),
	('claude-opus-5', ('claude-code', 'claude-opus-5')),
	('claude (opus 5)', ('claude-code', 'claude-opus-5')),
	('claude code', ('claude-code', '')),
	('claude-code', ('claude-code', '')),
	('codex-gpt-5', ('codex-cli', 'gpt-5')),
	('codex cli', ('codex-cli', '')),
	('codex-cli', ('codex-cli', '')),
	('codex', ('codex-cli', '')),
	('claude', ('claude-code', '')),
	('an assistant', ('', '')),
	('zeta3', ('', '')),
)

#: `Foo (numberdb=0.1.10, python=3.12.3, sage=10.9)` -- a generator publish.
GENERATOR = re.compile(r'^([A-Za-z_][\w-]*)\s*\((numberdb=[^)]*)\)')

#: `from the data repository, fc072a35`
FROM_REPO = re.compile(r'from the data repository,\s*([0-9a-f]{7,40})')

#: `..., table-build@0a2cd3e` -- what a run already recorded about its prompt.
PROMPT_AT = re.compile(r'\b(table-[a-z]+|triage)@([0-9a-f]{7,40}|uncommitted)')


def _decimal(text):
	try:
		return Decimal((text or '').strip() or '0')
	except InvalidOperation:
		return None


def _int(text):
	try:
		return int((text or '').strip())
	except (TypeError, ValueError):
		return None


def _breakdown(text):
	"""`gpt-5.5=4.7337;claude-haiku=0.005` -> {model: amount}."""
	found = {}
	for part in re.split(r'[;,]', text or ''):
		name, _, amount = part.partition('=')
		name = name.strip()
		value = _decimal(amount)
		if name and value is not None:
			found[name] = str(value)
	return found


def _when(stamp):
	"""`20260918T072306Z` -> an aware datetime, or None."""
	import datetime

	try:
		naive = datetime.datetime.strptime(stamp.strip(), '%Y%m%dT%H%M%SZ')
	except (AttributeError, ValueError):
		return None
	return naive.replace(tzinfo=datetime.timezone.utc)


def spelling(text):
	"""(engine, model) from a `produced_by` string, as far as it says."""
	low = (text or '').lower()
	for spelt, answer in SPELLINGS:
		if spelt in low:
			return answer
	return '', ''


class Command(BaseCommand):
	help = 'Reconstruct AgentRun rows for revisions made before runs recorded themselves.'

	def add_arguments(self, parser):
		parser.add_argument('--ledger', action='append', default=[],
		                    help='path[:machine], repeatable')
		parser.add_argument('--versions', default='',
		                    help='JSON from `agents/pipeline.py dump`')
		parser.add_argument('--write', action='store_true',
		                    help='save; without it nothing is written')
		parser.add_argument('--operator', default='',
		                    help='the account that started these campaigns; a '
		                         'run has an operator even when an agent wrote '
		                         'what it published')
		parser.add_argument('--verbose-report', action='store_true')

	#---------------------------------------------------------------- versions

	def load_versions(self, path):
		if not path or not os.path.exists(path):
			self.stderr.write('no version history given; runs will carry none')
			return {}
		with io.open(path, encoding='utf-8') as handle:
			found = json.load(handle)
		for name in found:
			found[name].sort(key=lambda v: v['when'])
		return found

	def version_at(self, name, when):
		"""The version in force when a run started: (version, digest, commit)."""
		history = self.versions.get(name) or []
		stamp = when.timestamp() if when else 0
		chosen = None
		for entry in history:
			if entry['when'] <= stamp:
				chosen = entry
			else:
				break
		if chosen is None:
			return '', '', ''
		return chosen['version'], chosen['digest'], chosen['commit']

	#---------------------------------------------------------------- the ledgers

	def read_ledger(self, path, machine):
		"""Ledger rows as dicts, with the two columns its header forgot.

		The header names sixteen columns and the rows carry eighteen: `campaign`
		and `batch` were appended without being named. Read positionally rather
		than by name, since a reader that trusts the header loses them.
		"""
		rows = []
		with io.open(path, encoding='utf-8') as handle:
			reader = csv.reader(handle, delimiter='\t')
			header = next(reader, None) or []
			for raw in reader:
				if not raw or not raw[0].strip():
					continue
				row = dict(zip(header, raw))
				row['campaign'] = raw[16] if len(raw) > 16 else ''
				row['batch'] = raw[17] if len(raw) > 17 else ''
				row['machine'] = machine
				rows.append(row)
		return rows

	def run_from_ledger(self, row):
		from numberdb_app.models import AgentRun

		started = _when(row.get('started'))
		if started is None:
			return None, False
		stage = (row.get('stage') or '').strip()
		pipeline = PIPELINE_OF.get(stage, stage)
		version, digest, commit = self.version_at(pipeline, started)

		notes = []
		said = PROMPT_AT.search(row.get('prompt') or '')
		if said and commit and not commit.startswith(said.group(2)):
			#Not an error: the prompt's own commit is the last one that touched
			#the prompt, and the version is the state of the whole scope. They
			#differ whenever anything else in scope moved later. Recorded so the
			#difference is visible rather than smoothed over.
			notes.append('ledger recorded prompt %s; scope version %s at %s'
			             % (said.group(0), version, commit[:8]))

		fields = dict(
			started=started,
			operator=self.operator,
			pipeline=pipeline,
			pipeline_version=version,
			pipeline_digest=digest,
			stage=stage,
			engine=ENGINE_OF.get((row.get('engine') or '').strip(),
			                     (row.get('engine') or '').strip()),
			model=(row.get('model') or '').strip()[:80],
			session=(row.get('session') or '').strip()[:80],
			campaign=(row.get('campaign') or '').strip()[:64],
			batch=(row.get('batch') or '').strip()[:80],
			machine=row.get('machine', '')[:64],
			turns=_int(row.get('turns')),
			cost_usd=_decimal(row.get('cost_usd')),
			tokens_in=_int(row.get('tokens_in')),
			tokens_cached=_int(row.get('tokens_cached')),
			tokens_out=_int(row.get('tokens_out')),
			cost_by_model=_breakdown(row.get('cost_by_model')),
			result=(row.get('result') or '').strip()[:16],
			source='ledger',
			notes='\n'.join(notes),
		)
		run_id = (row.get('started') or '').strip()[:80]
		if not self.write:
			return AgentRun(run_id=run_id, **fields), True
		run, created = AgentRun.objects.get_or_create(run_id=run_id,
		                                             defaults=fields)
		if not created and run.source in ('ledger', 'inferred'):
			for field, value in fields.items():
				setattr(run, field, value)
			run.save()
		return run, created

	#---------------------------------------------------------------- linking

	def link_ledger_runs(self, runs, rows):
		"""Revisions each table-naming run claims, where nothing else claims them."""
		from numberdb_app.models import Table, TableRevision

		claims = defaultdict(list)          # revision id -> [run]
		for run, row in zip(runs, rows):
			tid = (row.get('table') or '').strip()
			if not run or not tid:
				continue
			table = Table.objects.filter(tid=tid).first()
			if table is None:
				continue
			for revision in TableRevision.objects.filter(
					table=table, created__gte=run.started,
					created__lt=run.started + WINDOW):
				claims[revision.id].append(run)

		#A run that named no table is not lost: 36 of them, $174 of spend, and
		#the revisions of one table sitting inside the run's window with nobody
		#else claiming them. That is evidence, and one table's worth of it or
		#none -- a window holding two tables says nothing about which was this
		#run's work.
		for run, row in zip(runs, rows):
			if not run or (row.get('table') or '').strip():
				continue
			nearby = TableRevision.objects.filter(
				created__gte=run.started,
				created__lt=run.started + WINDOW).exclude(
				id__in=list(claims)).only('id', 'table_id')
			tables = {revision.table_id for revision in nearby}
			if len(tables) != 1:
				continue
			for revision in nearby:
				claims[revision.id].append(run)
			if self.write:
				run.notes = ('\n'.join(filter(None, [
					run.notes, 'the ledger recorded no table; linked to the '
					'only one edited inside this run\'s window.'])))
				run.save(update_fields=['notes'])

		linked = contested = 0
		for revision_id, found in claims.items():
			names = {r.run_id for r in found}
			if len(names) != 1:
				contested += 1
				continue
			#Remembered either way, so that a dry run's later passes do not
			#count a revision twice: without this the report says the sessions
			#pass would claim revisions the ledger has already claimed.
			self.claimed.add(revision_id)
			if self.write:
				TableRevision.objects.filter(id=revision_id,
				                             agent_run__isnull=True).update(
					agent_run=found[0])
			linked += 1
		return linked, contested

	def link_data_repository(self):
		"""The hand-made past: one run per commit of numberdb-data."""
		from numberdb_app.models import AgentRun, TableRevision

		made = linked = 0
		by_commit = defaultdict(list)
		for revision in TableRevision.objects.filter(
				produced_by='data-repository history').only(
				'id', 'message', 'created', 'author'):
			found = FROM_REPO.search(revision.message or '')
			if found:
				by_commit[found.group(1)].append(revision)

		for commit, revisions in by_commit.items():
			revisions.sort(key=lambda r: r.created)
			fields = dict(
				started=revisions[0].created,
				finished=revisions[-1].created,
				pipeline='data-repository',
				pipeline_version=commit[:12],
				stage='edit',
				engine='',
				model='',
				machine='',
				operator=revisions[0].author,
				source='reconstructed',
				notes='numberdb-data commit %s, when that repository was the '
				      'source of truth; edited by hand.' % (commit,),
			)
			if not self.write:
				made += 1
				linked += len(revisions)
				continue
			run, created = AgentRun.objects.get_or_create(
				run_id='data-repo:%s' % (commit,), defaults=fields)
			made += 1 if created else 0
			linked += TableRevision.objects.filter(
				id__in=[r.id for r in revisions],
				agent_run__isnull=True).update(agent_run=run)
		return made, linked

	def link_migrations(self):
		"""A person's one-off over the corpus: one run per name per day."""
		from numberdb_app.models import AgentRun, TableRevision

		made = linked = 0
		for name in MIGRATIONS:
			groups = defaultdict(list)
			for revision in TableRevision.objects.filter(
					produced_by=name).only('id', 'created', 'author'):
				groups[revision.created.date()].append(revision)
			for day, revisions in groups.items():
				revisions.sort(key=lambda r: r.created)
				run_id = 'migration:%s:%s' % (name.replace(' ', '-'), day)
				fields = dict(
					started=revisions[0].created,
					finished=revisions[-1].created,
					pipeline='migration',
					stage=name,
					operator=revisions[0].author,
					source='reconstructed',
					notes='a one-off over the corpus, run by hand on %s; %d '
					      'revisions.' % (day, len(revisions)),
				)
				if not self.write:
					made += 1
					linked += len(revisions)
					continue
				run, created = AgentRun.objects.get_or_create(
					run_id=run_id[:80], defaults=fields)
				made += 1 if created else 0
				linked += TableRevision.objects.filter(
					id__in=[r.id for r in revisions],
					agent_run__isnull=True).update(agent_run=run)
		return made, linked

	def link_sessions(self):
		"""What is left that names a tool: a session, grouped by day.

		The weakest level, and the commonest: `assisted by Claude Opus 5` says
		a model and not a run. One row per (account, engine, model, day), which
		is a claim about a working session and is labelled `inferred` because
		that is all it is.
		"""
		from numberdb_app.models import AgentRun, TableRevision

		made = linked = 0
		groups = defaultdict(list)
		for revision in TableRevision.objects.filter(
				agent_run__isnull=True).only(
				'id', 'created', 'author', 'produced_by', 'via', 'run'):
			produced = revision.produced_by or ''
			generator = GENERATOR.match(produced)
			engine, model = spelling(produced)
			if generator:
				key = ('generator', revision.run or generator.group(1),
				       revision.author_id, revision.created.date())
			elif engine or model:
				key = ('interactive', '%s/%s' % (engine, model),
				       revision.author_id, revision.created.date())
			else:
				continue
			if revision.id in self.claimed:
				continue
			groups[key].append((revision, generator, engine, model, produced))

		for (kind, what, author_id, day), found in groups.items():
			found.sort(key=lambda pair: pair[0].created)
			first, generator, engine, model, produced = found[0]
			if kind == 'generator':
				fields = dict(
					pipeline='generator',
					stage='publish',
					engine='numberdb-python',
					model=model,
					notes='%s; environment as the publish recorded it: %s'
					      % (produced, generator.group(2) if generator else ''),
				)
				run_id = 'generator:%s:%s' % (what, day)
			else:
				fields = dict(
					pipeline='interactive',
					stage='edit',
					engine=engine,
					model=model,
					notes='grouped by account and day from %r; the revisions '
					      'themselves recorded no run.' % (produced[:60],),
				)
				run_id = 'interactive:%s:%s:%s' % (author_id, what, day)
			fields.update(started=first.created,
			              finished=found[-1][0].created,
			              operator=first.author,
			              source='inferred')
			if not self.write:
				made += 1
				linked += len(found)
				continue
			run, created = AgentRun.objects.get_or_create(
				run_id=run_id[:80], defaults=fields)
			made += 1 if created else 0
			linked += TableRevision.objects.filter(
				id__in=[pair[0].id for pair in found],
				agent_run__isnull=True).update(agent_run=run)
		return made, linked

	#---------------------------------------------------------------- report

	def handle(self, *args, **options):
		from numberdb_app.models import AgentRun, TableRevision

		from django.contrib.auth.models import User

		self.write = options['write']
		self.claimed = set()
		#Who started the campaigns. The author of what a run published is the
		#agent's own account -- that is what answers for the digits -- and the
		#person who set it going is a different fact, recorded here because
		#"nobody started this" is not true of any run in the ledgers.
		self.operator = (User.objects.filter(
			username=options['operator']).first()
			if options['operator'] else None)
		if options['operator'] and self.operator is None:
			self.stderr.write('no account called %r' % (options['operator'],))
		self.versions = self.load_versions(options['versions'])

		runs, rows = [], []
		for given in options['ledger']:
			path, _, machine = given.partition(':')
			if not os.path.exists(path):
				self.stderr.write('no ledger at %s' % (path,))
				continue
			for row in self.read_ledger(path, machine or 'unknown'):
				run, _created = self.run_from_ledger(row)
				if run is not None:
					runs.append(run)
					rows.append(row)
		self.stdout.write('ledger runs:        %d' % (len(runs),))

		linked, contested = self.link_ledger_runs(runs, rows)
		self.stdout.write('  revisions linked: %d  (contested, left alone: %d)'
		                  % (linked, contested))

		made, linked = self.link_data_repository()
		self.stdout.write('data-repository:    %d runs, %d revisions'
		                  % (made, linked))

		made, linked = self.link_migrations()
		self.stdout.write('migrations:         %d runs, %d revisions'
		                  % (made, linked))

		made, linked = self.link_sessions()
		self.stdout.write('sessions inferred:  %d runs, %d revisions'
		                  % (made, linked))

		total = TableRevision.objects.count()
		if self.write:
			with_run = TableRevision.objects.filter(
				agent_run__isnull=False).count()
			self.stdout.write('\n%d of %d revisions now name a run (%.0f%%)'
			                  % (with_run, total, 100.0 * with_run / total))
			by_source = Counter(AgentRun.objects.values_list('source',
			                                                 flat=True))
			for source, count in by_source.most_common():
				self.stdout.write('   %-14s %d runs' % (source, count))
			left = Counter(
				(r.via, (r.produced_by or '')[:30])
				for r in TableRevision.objects.filter(agent_run__isnull=True)
				.only('via', 'produced_by'))
			if options['verbose_report'] and left:
				self.stdout.write('\nstill without a run:')
				for key, count in left.most_common(15):
					self.stdout.write('   %5d %s' % (count, key))
		else:
			self.stdout.write('\nnothing written (--write to save); %d revisions'
			                  % (total,))
