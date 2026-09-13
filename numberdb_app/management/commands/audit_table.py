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


def _entry_records(tree):
	"""Every entry of a table, whatever shape its Numbers block has."""
	numbers = tree.get('Numbers')

	def walk(node):
		if isinstance(node, dict):
			if 'number' in node or 'numbers' in node or 'equals' in node:
				yield node
				return
			for value in node.values():
				yield from walk(value)
		elif isinstance(node, list):
			for value in node:
				yield from walk(value)

	return list(walk(numbers)) if numbers is not None else []


#: Words a title cannot begin or end with once its mathematics is stripped.
#: T61 is "$\\cos(\\pi x)$ for rational $x$", which bares to "for rational" --
#: a fragment, not a name. Matching prose against it reported that every
#: definition saying "for rational order" names a table and fails to link it.
_FRAGMENT = ('for', 'of', 'at', 'in', 'with', 'to', 'and', 'or', 'the', 'a',
             'an')


def _bare_title(title):
	"""A title without its LaTeX, for matching against prose.

	Empty when what is left does not read as a name on its own: the caller
	skips those rather than matching a fragment against every table's prose.
	"""
	import re

	bare = ' '.join(re.sub(r'\$[^$]*\$', ' ', title).split()).strip(' ,.')
	words = bare.lower().split()
	if words and (words[0] in _FRAGMENT or words[-1] in _FRAGMENT):
		return ''
	return bare


#: Prose that points down or up the page. The document has Comments before
#: Formulas; the page draws Formulas first, so "the class number formula
#: below" sends a reader past it to the Programs and back. Four tables said
#: it, and the author writing YAML cannot see the order the site will use.
#: Naming the thing, or citing its label -- which renders as its number --
#: is right whichever way round the sections end up.
_POINTING = re.compile(
	r'\b(formulas?|comments?|programs?|sections?|identit(?:y|ies))'
	r'\s+(?:below|above)\b', re.I)

#: A formula that ends by saying somebody checked it. That is a fact about
#: the build rather than about the mathematics, and in a Formulas section it
#: reads as an apology: "we did not prove this, we looked". Its home is
#: `rigour details`, which is the field for how the numbers were obtained.
#: Seven formulas across four tables ended this way.
_NARRATION = re.compile(
	r'\b(?:checked\s+(?:on|against|in|here|for)\b[^.]*\bevery\b'
	r'|(?:both\s+)?were\s+computed\s+for\s+every'
	r'|computed\s+for\s+every\s+entry'
	r'|was\s+recomputed\s+from)', re.I)


#: Titles too common to look for in prose: they would match ordinary sentences.
_GENERIC_TITLES = {
	'integers', 'one', 'pi', 'rational numbers', 'algebraic numbers',
	'mass ratios', 'hyperreal numbers', 'roots of unity',
}


def findings_for(table, fetch=False):
	"""What the audit says about one table, as a list of sentences.

	Extracted so the checks have one implementation and two ways in: this
	command, run by a person on the server, and `GET /api/table/<tid>/audit`,
	run by a build machine that has no database and should not have one.

	That gap was not theoretical. The run that built T223 reported "I could not
	run `manage.py audit_table T223` because this checkout has no Django
	installed", so the prose audit never ran on it -- and an overreaching
	sentence about Salem numbers reached a reader, which the audit's own
	unlinked-constant check would have caught.
	"""
	#Imported here rather than at the top, as `handle` does: these models are
	#loaded when the app is, and a management command's module is imported
	#early enough for that to matter.
	from numberdb_app.editing import tree_of
	from numberdb_app.models import Table

	#A cross-reference may name a table by its address or by its number:
	#HREF{Integers} and HREF{T13} both resolve.
	urls = set(Table.objects.values_list('url', flat=True))
	urls |= set(Table.objects.values_list('tid', flat=True))
	public = set(Table.objects.filter(published=True)
	             .values_list('url', flat=True))
	public |= set(Table.objects.filter(published=True)
	              .values_list('tid', flat=True))
	titles = {t.title.lower(): t for t in Table.objects.all()}
	tree = tree_of(table.head_revision)
	command = Command()
	return list(command._check(table, tree, urls, titles,
	                           fetch=fetch, public=public))


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

	def _shared_values(self, table, original):
		"""How many stored values the two tables write identically.

		A repetition that shares nothing is not a repetition. The comparison
		is on the stored text rather than on parsed values, because that is
		what search compares: two tables holding one number to different
		precision do not collide there and will not fold here either, which is
		worth being told.

		Returns (shared, mine), so a table with no values of these kinds says
		nothing rather than complaining.
		"""
		from numberdb_app.models import Number, NumberComplex

		shared = 0
		mine = 0
		for model in (Number, NumberComplex):
			ours = set(model.objects.filter(table=table)
			           .exclude(exact_text='')
			           .values_list('exact_text', flat=True))
			mine += len(ours)
			if not ours:
				continue
			theirs = set(model.objects.filter(table=original)
			             .exclude(exact_text='')
			             .values_list('exact_text', flat=True))
			shared += len(ours & theirs)
		return shared, mine

	def _check(self, table, tree, urls, titles, fetch=False, public=None):
		from numberdb_app.validate import DATA_TYPES, RIGOUR_LEVELS

		import json
		#`ensure_ascii=False`: HREF{Lévy's_constant} is a real address in
		#this corpus, and an escaped dump turns it into a name no table has.
		prose = json.dumps({k: v for k, v in tree.items() if k != 'Numbers'},
		                   ensure_ascii=False)

		#Every entry that holds digits should be findable by them. Nothing
		#checked this, and it went wrong quietly: the number builder skipped
		#any entry carrying `equals`, so 101 values across 16 tables were
		#stored, displayed and correct while answering no search at all --
		#pi among them, in the table of rational multiples of pi, and the
		#whole of T60 whose every entry carries one. The values were right, so
		#no check that looked at values could have noticed.
		for complaint in self._indexed_as_many_as_written(table, tree):
			yield complaint

		#The same numbers under another title. Prose cannot catch this and
		#digits can, which is a thing only a database of numbers can do.
		for complaint in self._values_also_in_another_table(table, prose):
			yield complaint

		#Prose faults, each one found by a person reading a rendered page and
		#none of them by any check. They are mechanical; they were simply not
		#looked for.
		for complaint in self._prose_faults(table, tree, urls, titles):
			yield complaint

		#References that go nowhere. A CITE may name a Link, a Reference, or a
		#label defined elsewhere in the same table -- CITE{formula-recurrence}
		#is how a comment points at a formula on the same page, and the first
		#version of this check called all fourteen of those broken.
		#A reference identifier that has lost a digit. Checked by shape, not
		#by type: `arxiv: 0705.4325` unquoted in YAML is the float 705.4325,
		#and by the time it is stored it is the string "705.4325" -- correctly
		#typed and quietly wrong. Three digits before the dot is not a month.
		from ...validate import malformed_identifiers
		for label, field, text, shape in malformed_identifiers(tree):
			yield ('%s of reference %s is %s, which is not %s; a leading zero '
			       'is the usual casualty' % (field, label, text, shape))

		#Numbers with no code beside them. A table whose entries were computed
		#by a program should carry that program: the client attaches the
		#generator's own file automatically, so an empty manifest means the
		#attach step did not happen -- an older client (0.1.0 attached nothing
		#for five tables) or a run that died between sending the numbers and
		#sending the code.
		#
		#Any script counts, not `generate.py` by name. Seventeen tables attach
		#theirs as `touchard_gen.py` and the like, from before the convention,
		#and they are not missing anything.
		revision_now = table.head_revision
		if revision_now is not None:
			names = [a.name for a in revision_now.attachments.all()]
			computed = any('numberdb=' in (r.produced_by or '')
			               for r in table.revisions.all())
			if computed and not any(n.endswith(('.py', '.sage')) for n in names):
				yield ('the entries were computed by a program and no script '
				       'is attached, so the numbers here have no code beside '
				       'them; attach the generator that produced them')

		#A generator nobody can run. The file is downloaded from the table by
		#somebody who has neither the repository nor a way to guess the
		#command, so the commands belong in it, near the top.
		revision = table.head_revision
		if revision is not None:
			for attachment in revision.attachments.select_related('blob').all():
				if not attachment.name.endswith('generate.py'):
					continue
				text = bytes(attachment.blob.content).decode('utf-8', 'replace')
				if 'sage -pip install numberdb' not in text[:4000]:
					yield ('%s does not say how to install what it imports; '
					       'put the run commands in its docstring'
					       % attachment.name)
				if 'sage -python generate.py' not in ''.join(
						text.splitlines(True)[:40]):
					yield ('%s does not give the command to run it in its '
					       'first forty lines' % attachment.name)

		#The same function `commit_table` gates on and `validate` warns about,
		#so an audit and a refusal cannot come to different answers about the
		#same document.
		from ...validate import unresolved_citations
		for cite in unresolved_citations(tree):
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

		#A repetition that was declared and did not take. `_sync_repeats`
		#refuses a declaration that would leave a chain -- a table that some
		#other table repeats may not itself repeat a third -- and refuses
		#silently, because a save must not fail over what is in the end a
		#presentation hint. This is where the refusal becomes visible.
		from numberdb_app.editing import _repeats_slug

		properties = tree.get('Data properties')
		properties = properties if isinstance(properties, dict) else {}
		raw = str(properties.get('repeats') or '')
		declared = _repeats_slug(raw)
		if raw and not declared:
			yield ('Data properties: repeats is not a table reference; write '
			       'it as HREF{slug}, the way every other reference here is '
			       'written')
		elif declared:
			if '#' in raw:
				yield ('Data properties: repeats names an entry. The claim is '
				       'that one table repeats another, so it takes a table '
				       'address and no entry')
			if declared == table.url:
				yield 'Data properties: repeats names this table itself'
			elif table.repeats_id is None:
				yield ('Data properties: repeats was not recorded. Either %s '
				       'is itself a repetition or another table repeats this '
				       'one; the relation is kept one hop deep, so point at '
				       'the table that states the values first'
				       % (declared,))
			else:
				shared, mine = self._shared_values(table, table.repeats)
				if mine and not shared:
					yield ('Data properties: repeats %s, and the two tables '
					       'hold no value in common, so the declaration folds '
					       'nothing. Either it names the wrong table or the '
					       'values are written to different precision'
					       % (declared,))

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

		#An identifier a reader can see and cannot click. A reference may
		#carry `arxiv`, `doi`, `zbl` or `mr` beside its `bib`, and the page
		#renders each as a link. Nine tables built in three days put the arXiv
		#number in the sentence instead -- fifty-two references, every one of
		#them a number the reader has to retype.
		for name, reference in (tree.get('References') or {}).items():
			if not isinstance(reference, dict):
				continue
			fields = {key.lower() for key in reference}
			bib = str(reference.get('bib') or '').lower()
			for spelling, field in (('arxiv:', 'arxiv'), ('doi.org', 'doi'),
			                        ('doi:', 'doi'), ('zbl ', 'zbl'),
			                        ('mr ', 'mr')):
				if spelling in bib and field not in fields:
					yield ('References[%s] gives its %s in the text, where it '
					       'is not a link. Put it in a `%s:` field beside the '
					       'bib and the page renders it as one'
					       % (name, field, field))
					break

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

	#: How many of a table's values to look up elsewhere. Each is one indexed
	#: query, and a table that shares its subject with another shares far more
	#: than eight values with it.
	SAMPLE = 8

	#: How many of the sample must land in the same other table before this is
	#: worth a reader's time. Half, and at least three: two tables genuinely
	#: about different things share a value here and there -- zero, one, pi --
	#: and a check that reported those would be ignored within a week.
	ENOUGH = 3

	#: An integer or a rational smaller than this is not evidence of anything
	#: either, however few tables happen to hold it. The highest known ranks of
	#: elliptic curves are 28, 20, 15, 13, 9; the Dedekind zeta values at
	#: negative odd integers include those too, and the check announced that
	#: one of the two tables should not exist. Small numbers collide because
	#: there are not many of them, not because two tables are the same table.
	SMALL = 1000

	#: A value in more tables than this identifies nothing, so it is not
	#: evidence of anything and is dropped before the counting. Without this
	#: the check reported that the diagonal Ramsey numbers are the values of
	#: the Gamma function, because both contain 6 and 18: the first version
	#: made 51 findings on this corpus and perhaps three of them meant
	#: something. What makes two tables the same table is sharing the values
	#: that are *hard to share*.
	COMMON = 4

	def _distinctive_value(self, value):
		"""Is hitting this number by accident unlikely?

		Only exact small numbers are excluded. A real number written to
		fifteen digits is shared because it is the same number -- which is the
		question this check asks -- and how common *that* is, is what COMMON
		is for.
		"""
		try:
			from sage.rings.all import QQ, ZZ
			if value in ZZ:
				return abs(ZZ(value)) >= self.SMALL
			if value in QQ:
				exact = QQ(value)
				return max(abs(exact.numerator()),
				           exact.denominator()) >= self.SMALL
		except Exception:                                    # noqa: BLE001
			return True
		return True

	def _values_also_in_another_table(self, table, prose):
		"""Another table holding the same numbers, under another name.

		T219 and T225 were nearly the same table and a reader noticed, not a
		check: the titles shared no distinctive word -- the Hodgson-Weeks
		census and the Callahan-Hildebrand-Weeks census -- while the numbers
		were volumes of hyperbolic 3-manifolds either way. Every check we had
		read prose, and prose is exactly what two independent agents proposing
		the same family will write differently.

		A finding here is not a verdict. Two tables may legitimately share a
		subfamily -- the Bianchi covolumes are multiples of Dedekind zeta
		values that this corpus also holds -- and the answer then is a line in
		Similar tables saying so, which is why a table that already names the
		other is not reported.
		"""
		from numberdb_app.models import Number

		#Only what the index can answer, and only from this table's own rows:
		#the document may be huge and the index is what a reader searching by
		#digits would hit anyway.
		rows = list(Number.objects.filter(table=table).order_by('pk')
		            [:self.SAMPLE * 40])
		if len(rows) < self.ENOUGH:
			return
		#Spread through the table rather than the first eight: the first rows
		#of a family are its small cases, which are the ones most likely to be
		#shared with everything (the first Bessel zero, the first prime).
		step = max(1, len(rows) // self.SAMPLE)
		sample = rows[::step][:self.SAMPLE]

		from ...search import search_number
		elsewhere = {}
		distinctive = 0
		for row in sample:
			try:
				value = row.to_sage()
				found = search_number(value, per_table=True)
			except Exception:                                # noqa: BLE001
				#A type the search cannot hold, or a value it cannot parse.
				#Not this check's complaint, and not worth failing an audit.
				continue
			if not self._distinctive_value(value):
				continue
			holders = {}
			for other in found:
				if other.table_id != table.pk:
					holders[other.table_id] = other.table
			if len(holders) > self.COMMON:
				continue                    #a number everybody has says nothing
			distinctive += 1
			for table_id, other in holders.items():
				elsewhere.setdefault(table_id, [other, 0])
				elsewhere[table_id][1] += 1
		if distinctive < self.ENOUGH:
			return

		for other, count in sorted(elsewhere.values(), key=lambda p: -p[1]):
			if count < self.ENOUGH or count * 2 < distinctive:
				continue
			if other.tid in prose or other.url in prose:
				continue                                     #already says so
			yield ('%d of the %d distinctive values sampled here are also in '
			       '%s (%s); if these are the same numbers, one of the two '
			       'tables should not exist, and if they are not, say how they '
			       'differ in Similar tables'
			       % (count, distinctive, other.tid, other.title))

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

	#: Sentences that say something about this website rather than about the
	#: mathematics. A table full of them reads as apology, and four carried
	#: one before anybody noticed.
	EDITORIAL = (
		'identifies nothing', 'identify nothing', 'weak evidence',
		'tells the reader nothing', 'means nothing on its own',
		'should not lead here', 'is not distinctive',
	)

	#: Pointing at a thing instead of naming it. The symbol is shorter than
	#: the phrase pointing at it and stays right when the formula is edited.
	POSITIONAL = (
		'the first factor', 'the second factor', 'the former', 'the latter',
		'the first one', 'the second one', 'as above', 'the latter two',
		#"beside it" points at a *table*, not at a term in a formula, and a
		#reader has no "beside": the page is one table and the corpus is not
		#laid out. T110's provenance note said its transcription was "the
		#difference between this table and the twin prime constant beside it",
		#which names a table here, does not link it, and tells a reader
		#nothing about where to look.
		'beside it', 'beside this', 'next to it',
	)

	def _prose_faults(self, table, tree, urls, titles):
		"""What a reader would notice and no other check does."""
		import json
		import re

		sections = ('Definition', 'Comments', 'Formulas', 'Similar tables')
		texts = []
		for name in sections:
			blob = tree.get(name)
			if isinstance(blob, str):
				texts.append((name, blob))
			elif isinstance(blob, dict):
				texts.extend(('%s[%s]' % (name, key), value)
				             for key, value in blob.items()
				             if isinstance(value, str))

		#`rigour details` and `complete-note` are prose too -- the reader
		#meets them under "How they were obtained" and beside "complete: no"
		#-- and they were not read at all. That is where T110 named the twin
		#prime constant without linking it and pointed at it as "beside it",
		#and neither check saw the sentence. Kept apart from `texts` because
		#one check does not apply to them: a fact about the build reads as
		#narration in a comment and is the whole point of a provenance note.
		provenance = []
		properties = tree.get('Data properties')
		if isinstance(properties, dict):
			for key in ('rigour details', 'complete-note'):
				value = properties.get(key)
				if isinstance(value, str) and value.strip():
					provenance.append(('Data properties[%s]' % key, value))

		#And the comment on each entry, which is prose a reader meets more
		#often than the sections: it sits under the value they came for. This
		#read only the sections at first, so entry comments saying a value
		#"identifies nothing" survived a cleanup that removed the same
		#sentence from the sections above them.
		for record in _entry_records(tree):
			note = record.get('comment')
			if isinstance(note, str) and note.strip():
				where = 'entry %s' % (record.get('params') or '')
				texts.append((where.strip(), note))

		for where, text in texts + provenance:
			lowered = text.lower()
			for phrase in self.EDITORIAL:
				if phrase in lowered:
					yield ('%s says %r. A comment states a fact about the '
					       'mathematics; how good a search hit would be is a '
					       'remark about this website' % (where, phrase))
			for phrase in self.POSITIONAL:
				if phrase in lowered:
					yield ('%s says %r. Name the symbol instead: it is shorter '
					       'than the phrase pointing at it, and it stays right '
					       'when the formula is edited' % (where, phrase))
			for match in _POINTING.finditer(text):
				yield ('%s says %r. The page draws Formulas before Comments, '
				       'whatever order the document is written in, so a '
				       'reader who looks where they are told may not find it. '
				       'Name it, or CITE its label, which renders as its '
				       'number' % (where, match.group(0)))
			if (where, text) in provenance:
				#"computed twice and they agreed" is what this field is for.
				continue
			for match in _NARRATION.finditer(text):
				yield ('%s says %r. That is a fact about the build, not about '
				       'the mathematics; "rigour details" is the field for '
				       'how the numbers were obtained' % (where,
				                                          match.group(0)))

		#A family the corpus holds, named in prose and not linked. Titles are
		#matched without their LaTeX, and only the distinctive ones.
		#
		#`titles` maps a lowercased title to its table, so the slug and the
		#name for matching both come off the object.
		own = _bare_title(tree.get('Title') or '')
		families = sorted(((other.url, _bare_title(other.title))
		                   for other in titles.values()
		                   if other.pk != table.pk),
		                  key=lambda pair: -len(pair[1]))
		for slug, name in families:
			if len(name) < 9 or name.lower() in _GENERIC_TITLES:
				continue
			#`own` is empty when this table's own title bares to a fragment,
			#and `'' in anything` is true -- which skipped every family and
			#turned the check off altogether for such a table.
			if own and (name.lower() in own.lower()
			            or own.lower() in name.lower()):
				continue
			for where, text in texts + provenance:
				if 'HREF{%s}' % slug in text:
					continue
				masked = re.sub(r'HREF\{[^}]*\}(\[[^\]]*\])?', ' ', text)
				if re.search(r'(?<![\w-])%s(?![\w-])' % re.escape(name),
				             masked, re.I):
					yield ('%s names %s and does not link it: '
					       'HREF{%s}[%s]' % (where, name, slug, name))
					break

		#A link sitting after the name instead of on it.
		for where, text in texts + provenance:
			by_slug = {other.url: _bare_title(other.title)
			           for other in titles.values()}
			for match in re.finditer(r'HREF\{([^}]*)\}(?!\[)', text):
				name = by_slug.get(match.group(1))
				if not name:
					continue
				head = text[:match.start()]
				if re.search(r'%s\s*$' % re.escape(name), head, re.I):
					yield ('%s writes "%s HREF{%s}" -- put the link on the '
					       'name: HREF{%s}[%s]'
					       % (where, name, match.group(1), match.group(1), name))

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
