"""Check a table against the things that have gone wrong before.

    manage.py audit_table T108
    manage.py audit_table --all
    manage.py audit_table T108 --links      # also fetch the external links

Every check here is deterministic and every one of them corresponds to a
mistake that was made and had to be found by a person reading the table:

  * a CITE pointing at nothing, or a HREF at a table that does not exist
  * an external link to something this database holds itself -- the Chebyshev
    polynomials were cited as a Wikipedia article by a table whose own
    database has them as T99
  * a tag nobody else uses, which is a tag that leads nowhere
  * a definition that has grown into a definition plus three other things
  * notation used in a formula and defined nowhere in the table
  * a Programs snippet naming a range that no longer matches the table

It reports and changes nothing. What to do about a finding is a judgement, and
several of these are worth overruling: a definition may genuinely need three
sentences, and a tag has to be new once.
"""

import re

from django.core.management.base import BaseCommand

#: A definition that says what the object is, and then keeps going. Measured
#: over the corpus the median is 195 characters; the two tables that had to be
#: taken apart were 320 and 400.
LONG_DEFINITION = 320

#: Phrases that belong in a comment rather than a definition. Each one appeared
#: in a definition that later had to be split up.
COMMENT_PHRASES = ('note that', 'some authors', 'elsewhere they', 'listed '
                   'separately', 'which is why')


class Command(BaseCommand):
	help = 'Check a table for the mistakes that have been made before.'

	def add_arguments(self, parser):
		parser.add_argument('tids', nargs='*')
		parser.add_argument('--all', action='store_true')
		parser.add_argument('--links', action='store_true',
		                    help='fetch external links and report dead ones')

	def handle(self, *args, **options):
		from numberdb_app.editing import tree_of
		from numberdb_app.models import Table

		if options['all']:
			tables = list(Table.objects.exclude(head_revision=None)
			              .order_by('tid_int'))
		else:
			tables = [Table.objects.get(tid=t) for t in options['tids']]
		if not tables:
			self.stdout.write('Name a table, or pass --all.')
			return

		#A cross-reference may name a table by its address or by its number:
		#HREF{Integers} and HREF{T13} both resolve.
		urls = set(Table.objects.values_list('url', flat=True))
		urls |= set(Table.objects.values_list('tid', flat=True))

		#Which of those a *published* table may point at is narrower. A draft
		#answers 404 to everybody, so a published table linking to one gives
		#every visitor a dead link -- and this check passed it, because the
		#draft's address exists in the database. Two drafts may link to each
		#other: they become visible together.
		public = set(Table.objects.filter(published=True)
		             .values_list('url', flat=True))
		public |= set(Table.objects.filter(published=True)
		              .values_list('tid', flat=True))
		titles = {t.title.lower(): t for t in Table.objects.all()}
		found_any = False

		for table in tables:
			tree = tree_of(table.head_revision)
			findings = list(self._check(table, tree, urls, titles,
			                            fetch=options['links'],
			                            public=public))
			if not findings:
				continue
			found_any = True
			self.stdout.write('%s  %s' % (table.tid, table.title[:60]))
			for finding in findings:
				self.stdout.write('   %s' % finding)

		if not found_any:
			self.stdout.write('Nothing to report.')

	def _check(self, table, tree, urls, titles, fetch=False, public=None):
		from numberdb_app.validate import DATA_TYPES, RIGOUR_LEVELS

		import json
		prose = json.dumps({k: v for k, v in tree.items() if k != 'Numbers'})

		#Every entry that holds digits should be findable by them. Nothing
		#checked this, and it went wrong quietly: the number builder skipped
		#any entry carrying `equals`, so 101 values across 16 tables were
		#stored, displayed and correct while answering no search at all --
		#pi among them, in the table of rational multiples of pi, and the
		#whole of T60 whose every entry carries one. The values were right, so
		#no check that looked at values could have noticed.
		for complaint in self._indexed_as_many_as_written(table, tree):
			yield complaint

		#References that go nowhere. A CITE may name a Link, a Reference, or a
		#label defined elsewhere in the same table -- CITE{formula-recurrence}
		#is how a comment points at a formula on the same page, and the first
		#version of this check called all fourteen of those broken.
		keys = set(tree.get('Links') or {}) | set(tree.get('References') or {})
		for section in ('Formulas', 'Comments', 'Programs', 'Display properties'):
			keys |= set(tree.get(section) or {})
		for cite in sorted(set(re.findall(r'CITE\{([^}\]]+)\}', prose))):
			if cite not in keys:
				yield 'CITE{%s} is not a Link or a Reference' % cite
		for href in sorted(set(re.findall(r'HREF\{([^}\]]+)\}', prose))):
			target = href.split('#')[0]
			if target and not target.startswith(('http://', 'https://')):
				if target not in urls:
					yield 'HREF{%s} names no table here' % target
				elif (table.published and public is not None
						and target not in public):
					yield ('HREF{%s} points at a draft, which answers 404 to '
					       'everybody; a published table must not link to one'
					       % target)

		#An external link to something the database holds itself.
		for name, link in (tree.get('Links') or {}).items():
			title = (link.get('title') or '') if isinstance(link, dict) else ''
			for other_title, other in titles.items():
				#By primary key, not by identity: these came from a different
				#queryset, so `is` never matched and every table was told to
				#link to itself.
				if other.pk == table.pk or len(other_title) < 12:
					continue
				if other_title in title.lower():
					yield ('Links[%s] points outside for "%s", which this '
					       'database holds as %s -- prefer HREF{%s}'
					       % (name, other.title[:40], other.tid, other.url))

		#Tags that lead nowhere.
		#
		#Not "the tag does not exist": committing a table creates its tags, so
		#by the time anything looks, every tag exists and the check fires
		#never. What matters is how many tables a tag reaches, since a tag is
		#a way through the corpus and one that reaches a single table is not.
		from numberdb_app.models import Tag

		reach = dict(Tag.objects.values_list('name', 'table_count'))
		for tag in (tree.get('Tags') or []):
			if reach.get(tag, 0) <= 1:
				yield ('Tags: "%s" reaches only this table; a tag that leads '
				       'nowhere else leads nowhere' % tag)

		#A definition that has grown into several things.
		definition = (tree.get('Definition') or '').strip()
		if not definition:
			yield 'Definition is empty'
		else:
			if len(definition) > LONG_DEFINITION:
				yield ('Definition is %d characters (median here is 195); check '
				       'whether part of it belongs in Comments or Formulas'
				       % len(definition))
			for phrase in COMMENT_PHRASES:
				if phrase in definition.lower():
					yield ('Definition contains "%s", which reads like a '
					       'comment rather than a definition' % phrase)
			if 'HREF{' in definition:
				yield ('Definition links to another table; a cross-reference '
				       'belongs in Similar tables or a comment')

		#Declared type and rigour.
		properties = tree.get('Data properties') or {}
		if properties.get('type') not in DATA_TYPES:
			yield ('Data properties: type %r is not one of %s'
			       % (properties.get('type'), ', '.join(sorted(DATA_TYPES))))
		if properties.get('rigour') and properties['rigour'] not in RIGOUR_LEVELS:
			yield 'Data properties: rigour %r is not a level' % properties['rigour']

		#A Programs snippet with a range in it, which is what goes stale.
		for name, program in (tree.get('Programs') or {}).items():
			code = (program.get('code') or '') if isinstance(program, dict) else ''
			ranges = re.findall(r'\[0\.\.(\d+)\]|range\(0,\s*(\d+)\)', code)
			held = len([e for e in (tree.get('Numbers') or [])
			            if isinstance(e, dict) and e.get('number')])
			for pair in ranges:
				number = int(pair[0] or pair[1])
				if abs(number + 1 - held) > 1:
					yield ('Programs[%s] computes %d values and the table holds '
					       '%d; a range in a snippet goes stale when the table '
					       'changes' % (name, number + 1, held))

		#Size.
		from numberdb_app.limits import check as size_check

		for breach in size_check(tree) or []:
			yield 'size: %s' % getattr(breach, 'message', breach)

		if fetch:
			for name, link in (tree.get('Links') or {}).items():
				url = (link.get('url') or '') if isinstance(link, dict) else ''
				if not url.startswith(('http://', 'https://')):
					continue
				status = self._fetch(url)
				if status != 200:
					yield 'Links[%s] answered %s: %s' % (name, status, url)

	def _indexed_as_many_as_written(self, table, tree):
		"""Distinct values in the document, against rows in the index.

		Distinct, and not the number of entries, because the index holds a row
		per value: the Bernoulli numbers write 101 entries of which 49 are
		zero, the chromatic polynomials write 996 of which many graphs share
		one, and both are indexed correctly at 52 and 304. Counting entries
		called nineteen tables broken and would have taught everybody to
		ignore this.

		Tables whose type the search cannot hold are skipped -- the hyperreals
		of T41 are recorded and cited and were never findable by their digits.
		"""
		from numberdb_app.flatten import to_records
		from numberdb_app.models import (Number, NumberComplex, NumberPAdic,
		                                 Polynomial)
		from numberdb_app.validate import SEARCHABLE_TYPES

		declared = str((tree.get('Data properties') or {}).get('type') or '')
		if declared and declared not in SEARCHABLE_TYPES:
			return

		try:
			records = to_records(tree)
		except Exception:                                    # noqa: BLE001
			return                                           # not our complaint
		if not records:
			return

		DIGITS = ('number', 'numbers', 'polynomial', 'polynomials')
		values = set()
		for record in records:
			if not isinstance(record, dict):
				if record is not None:
					values.add(str(record))
				continue
			for key in DIGITS:
				held = record.get(key)
				if held is None:
					continue
				if isinstance(held, (list, tuple)):
					values.update(str(one) for one in held)
				else:
					values.add(str(held))
		if not values:
			return

		indexed = sum(model.objects.filter(table=table).count()
		              for model in (Number, NumberComplex, NumberPAdic,
		                            Polynomial))
		if indexed < len(values):
			yield ('%d distinct values are written but only %d are in the '
			       'search index: %d cannot be found by their digits. This is '
			       'how pi came to be missing from the table of rational '
			       'multiples of pi. Rebuild with '
			       'build_number_table(only_table=...); if the gap stays, '
			       'something is skipping them.'
			       % (len(values), indexed, len(values) - indexed))

	def _fetch(self, url):
		import urllib.error
		import urllib.request

		request = urllib.request.Request(
			url, headers={'User-Agent': 'numberdb-audit'})
		try:
			with urllib.request.urlopen(request, timeout=20) as answer:
				return answer.status
		except urllib.error.HTTPError as trouble:
			return trouble.code
		except Exception as trouble:
			return type(trouble).__name__
