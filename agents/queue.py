"""The queue of screened proposals, kept as issues.

    python3 agents/queue.py open                 how many tables are waiting
    python3 agents/queue.py next [--family N]    the next one to build
    python3 agents/queue.py show N               one family, for a build prompt
    python3 agents/queue.py post BATCH.md        a batch becomes a family issue
    python3 agents/queue.py built N "Title" T226 tick the box
    python3 agents/queue.py skipped N "Title" "why"  settle it without a table
    python3 agents/queue.py stale [--weeks 6]    families that have aged out

Why issues rather than the file the ideation stage writes: that file is
excluded by `.gitignore` as data, so a batch lived on exactly one disk, and
`batch_file()` in `campaign.sh` read only the newest of them. A campaign that
exhausted a batch abandoned every proposal in every earlier file. On
2026-09-13 that had stranded about 39 screened proposals across two machines,
including all five of a symmetric-function family of which none was built --
at about $1.50 of screening each. The other half of the reason is that the
screening asks GitHub what has already been asked for (`already_asked` in
`table-ideas/screen.py`) and wrote its answers somewhere GitHub cannot see, so
it proposed the Bianchi covolumes twice, on two machines, a day apart.

What is *not* here: any claim on a table. The claim is the draft, because
`Table.title` is unique and the database settles a race whoever wins it; see
`docs/design/where-ideas-live.md`. This file only keeps us from paying twice
to have the same idea.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

#: Where the content backlog lives. `table wanted` issues are written there by
#: people, and the screening already reads them; proposals join them under
#: their own label rather than in a tracker of their own, so that a person
#: asking for a table and a machine proposing one are one conversation.
REPO = os.environ.get('NUMBERDB_IDEAS_REPO', 'numberdb/numberdb-data')

#: The label that says a machine screened this and would build it.
LABEL = 'proposal'

#: Written into the issue so a parser never has to guess which fenced block is
#: the checklist. An HTML comment is invisible to a reader and survives
#: editing by hand, which a table of contents or a fence would not.
MARKER = '<!-- numberdb-family: %s -->'
MARKER_FINDER = re.compile(r'<!-- numberdb-family: ([^\s>]+) -->')
SCREENED_FINDER = re.compile(r'<!-- screened: (\d{4}-\d{2}-\d{2}) -->')

#: A checklist line. Three states, not two:
#:
#:     - [ ] Some table                        waiting
#:     - [x] Some table -- T226                built
#:     - [-] Some table -- skipped: <why>      settled, and not to be retried
#:
#: The third is the one that was missing. A proposal a build looked at and
#: declined for a good reason -- the corpus already holds it under another
#: name, the sources disagree about the definition, the data is not public --
#: stayed an empty box, so the next campaign picked it up and paid to reach
#: the same conclusion.
ITEM = re.compile(r'^- \[([ xX\-~])\] (.+?)'
                  r'(?:\s+\(answers ([^)]+)\))?'
                  r'(?:\s+--\s+(\[?T\d+\]?(?:\([^)]*\))?'
                  r'|skipped:.*?|claimed.*?))?\s*$')

#: How long a screening stays believable. Six weeks is not a measurement; it
#: is the age at which this corpus has visibly moved -- of 89 proposals
#: screened here over a fortnight, only about 19 had no table like them by the
#: end of it.
STALE_WEEKS = 6


def gh(*args, **kwargs):
	"""Run `gh` and return its output, or raise with what it said."""
	done = subprocess.run(('gh',) + args, capture_output=True, text=True,
	                      input=kwargs.get('input'))
	if done.returncode != 0:
		raise SystemExit('gh %s: %s' % (' '.join(args[:2]),
		                                (done.stderr or done.stdout).strip()))
	return done.stdout


def api(path, method='GET', payload=None):
	args = ['api', '-X', method, path]
	if payload is not None:
		args += ['--input', '-']
	return json.loads(gh(*args, input=json.dumps(payload) if payload else None)
	                  or 'null')


#---------------------------------------------------------------- reading a batch

def _screened_on(name):
	"""The date out of `BATCH-2026-09-12T1922.md`."""
	found = re.search(r'(\d{4}-\d{2}-\d{2})', name)
	return found.group(1) if found else str(datetime.date.today())


def _section(text, heading):
	"""One `## heading` section, without its heading line."""
	lines = text.splitlines()
	for start, line in enumerate(lines):
		if line.strip().lower() == ('## ' + heading).lower():
			break
	else:
		return ''
	body = []
	for line in lines[start + 1:]:
		if line.startswith('## '):
			break
		body.append(line)
	return '\n'.join(body).strip()


def parse_batch(text, name):
	"""What a batch file says, as far as the queue needs it.

	The proposals are the `## 1. Title` headings, in the order the batch ranks
	them, and that order is the build order: a batch argues its ranking and
	throwing it away would waste the argument.
	"""
	first = text.lstrip().splitlines()[0] if text.strip() else ''
	#`# Batch: volumes of...` and `# Batch 2026-09-12T1831: Lehmer's...`
	#are both in use, and neither prefix belongs in an issue title: the
	#issue already says which batch it is, in the marker and in the link
	#to the report.
	subject = re.sub(r'^#\s*Batch\b[^:]*:\s*', '', first)
	subject = re.sub(r'^#\s*', '', subject).strip()
	subject = re.sub(r',?\s*screened\s+\d{4}-\d{2}-\d{2}\s*$', '',
	                 subject, flags=re.I)
	proposals = [(int(n), title.strip())
	             for n, title in re.findall(r'^## (\d+)\.\s+(.+?)\s*$', text,
	                                        re.M)]
	#Which request each proposal answers, from the `#N` in its own section.
	#Batch-level `draws_on` below says the family answers somebody; this says
	#*which table* does, which is what lets the build close the issue and cite
	#it. Of 24 families screened before this existed, four cited a request at
	#all -- and one of them built exactly what numberdb-data#110 asked for
	#while #110 stayed open.
	answers = {}
	sections = re.split(r'^## \d+\.\s+', text, flags=re.M)[1:]
	for (_rank, title), section in zip(sorted(proposals), sections):
		found = sorted({int(n) for n in
		                re.findall(r'(?:numberdb-data)?#(\d{1,4})\b', section)})
		if found:
			answers[title] = found
	#`(#134)` in a proposal heading and `numberdb-data#134` in the prose are
	#the same reference written two ways, and both mean "this is what somebody
	#asked for".
	draws_on = sorted({int(n) for n in
	                   re.findall(r'(?:numberdb-data)?#(\d{1,4})\b', text)})
	return {
		'batch': re.sub(r'\.md$', '', os.path.basename(name)),
		'subject': subject,
		'screened': _screened_on(name),
		'proposals': [title for _, title in sorted(proposals)],
		'answers': answers,
		'conventions': _section(text, 'Conventions shared by the tables'),
		'draws_on': draws_on,
	}


def _short(subject, limit=90):
	"""An issue title a person can read in a list.

	Batch headings run to two hundred characters -- the hyperbolic one names
	five families and their dimensions -- and a tracker shows about ninety.
	"""
	subject = subject.split(' -- ')[0].strip()
	if len(subject) <= limit:
		return subject
	cut = subject[:limit].rsplit(' ', 1)[0]
	return cut + '...'


def issue_body(batch, done=()):
	"""The issue a family becomes.

	An index and a place to argue, not the report: the screening report itself
	is 32 KB of machine prose on average and lives in `numberdb-runs/ideas/`,
	where machine prose belongs. What is copied here is the part a build needs
	in front of it -- the conventions the tables share -- and the list.
	"""
	done = {title: tid for title, tid in done}
	lines = ['Screened by the ideation stage on %s.' % batch['screened'], '']
	lines.append('The tables, in the order the batch ranks them:')
	lines.append('')
	for title in batch['proposals']:
		tid = done.get(title)
		asked = (batch.get('answers') or {}).get(title) or []
		wanted = (' (answers %s)' % ', '.join('#%d' % n for n in asked)
		          if asked else '')
		lines.append('- [%s] %s%s%s' % ('x' if tid else ' ', title, wanted,
		                                ' -- %s' % tid if tid else ''))
	lines.append('')
	if batch['draws_on']:
		lines.append('Draws on: %s.'
		             % ', '.join('#%d' % n for n in batch['draws_on']))
		lines.append('')
	if batch['conventions']:
		lines.append('## Conventions shared by these tables')
		lines.append('')
		lines.append(batch['conventions'])
		lines.append('')
	lines.append('The full screening report, with what was checked and what '
	             'was looked at and not proposed, is `ideas/%s.md.gz` in '
	             '`numberdb/numberdb-runs`.' % batch['batch'])
	lines.append('')
	lines.append('A proposal is a claim about the corpus on the day it was '
	             'screened, so a build re-checks the cheap half before '
	             'building: `already_here`, `already_asked`, `api/lookup` on '
	             'the sample values, and whether the tag exists. See '
	             '`docs/design/where-ideas-live.md`.')
	lines.append('')
	lines.append(MARKER % batch['batch'])
	lines.append('<!-- screened: %s -->' % batch['screened'])
	return '\n'.join(lines)


#---------------------------------------------------------------- reading a family

def parse_family(issue):
	"""An issue back into a family, or None if it is not one."""
	body = issue.get('body') or ''
	marker = MARKER_FINDER.search(body)
	if marker is None:
		return None
	screened = SCREENED_FINDER.search(body)
	items = []
	for line in body.splitlines():
		found = ITEM.match(line)
		if found:
			mark, title, asked, tail = found.groups()
			settled = mark.lower() in ('x', '-', '~')
			items.append({'title': title.strip(),
			              'done': settled,
			              'built': mark.lower() == 'x',
			              'claimed': (tail or '') if (tail or '').startswith(
				              'claimed') else '',
			              'answers': [int(n) for n in
			                          re.findall(r'\d+', asked or '')],
			              'tid': _tid_in(tail),
			              'why': tail if (tail or '').startswith('skipped') else None})
	return {'number': issue['number'], 'title': issue['title'],
	        'batch': marker.group(1), 'body': body, 'items': items,
	        'screened': screened.group(1) if screened else None}


def families(state='open'):
	"""Every family issue, newest screening first."""
	found = []
	page = 1
	while True:
		issues = api('repos/%s/issues?labels=%s&state=%s&per_page=100&page=%d'
		             % (REPO, LABEL, state, page)) or []
		if not issues:
			break
		for issue in issues:
			if 'pull_request' in issue:
				continue
			family = parse_family(issue)
			if family is not None:
				found.append(family)
		page += 1
	return sorted(found, key=lambda f: (f['screened'] or '', f['number']),
	              reverse=True)


#: How long a claim holds a proposal. A worker that dies mid-build leaves its
#: claim behind, and with four workers that is not a rare event: on
#: 2026-09-20 all four died within an hour and every remaining proposal was
#: held by one of them, so the queue read empty and each new campaign exited
#: on the banner. A claim is a courtesy between workers, not a lock, and a
#: courtesy that outlives its worker is just a stuck queue.
#:
#: Ninety minutes is longer than any build measured here -- the slowest was
#: 67 -- and short enough that a machine restarted at lunch is working again
#: by the time anybody looks.
CLAIM_MINUTES = 90


def _claim_age(item):
	"""Minutes since a claim was made, or None if it carries no time."""
	found = re.search(r'at (\d{4}-\d{2}-\d{2}T\d{2}:\d{2})Z',
	                  item.get('claimed') or '')
	if not found:
		return None
	try:
		when = datetime.datetime.strptime(found.group(1), '%Y-%m-%dT%H:%M')
	except ValueError:
		return None
	return (datetime.datetime.utcnow() - when).total_seconds() / 60.0


def stale_claim(item):
	"""Is this claim old enough that the worker holding it is gone?"""
	if not (item.get('claimed') or ''):
		return False
	age = _claim_age(item)
	#A claim with no time on it was written before claims were timed; treat it
	#as stale rather than letting it hold a proposal for ever.
	return age is None or age > CLAIM_MINUTES


def waiting(family):
	"""Proposals nobody is building: unsettled, or claimed and abandoned.

	Reads the checklist and nothing else, so that anything asking "what is
	left in this family" -- a report, a test, a person -- gets an answer
	without a network call. What the *site* holds is consulted where the
	choice is actually made, in `next_table`.
	"""
	return [item for item in family['items']
	        if not item['done'] or stale_claim(item)]


def unheld(family, mine=''):
	"""The same, minus whatever another worker is holding on the site.

	The checklist is what a person reads; the site is what decides. A
	proposal claimed there a second ago has no mark on its line yet, and two
	workers reading the line would both take it.
	"""
	free = waiting(family)
	if not free or os.environ.get('NUMBERDB_CLAIM_SITE') == '0':
		return free
	held = held_by_others(family['number'], mine)
	if not held:
		return free
	return [item for item in free
	        if not any(_same_subject(item['title'], title) for title in held)]


def started(family):
	"""Has anything in this family been settled already?"""
	return any(item['done'] for item in family['items'])


def next_table(prefer=None):
	"""The next table to build.

	**Finish the family you are in**, and failing that, finish one somebody
	else started. The tables of a batch share machinery and cross-reference
	each other, which is most of why the batches have been good, and a family
	left half-built loses that -- the symmetric-function family sat five-for-
	five unbuilt while newer batches were screened and built past it.

	So the order is: the family named by `prefer`; then families with work
	already done in them; then the rest -- and both by oldest screening
	first, because the oldest debt is the one nobody will come back to. A
	family nobody has started is a leftover too: #138 was screened on
	2026-09-12 and was still waiting four days later while two families
	screened after it went ahead, which is how the first pile got made.

	What guards against building a stale plan is not the order but the
	screening date on the family and the cheap re-check a build runs before
	it spends anything.
	"""
	open_ones = [f for f in families() if waiting(f)]
	if not open_ones:
		return None
	#What another worker is holding on the site is not offered here: the
	#checklist mark is written after the claim, so a line can look free for
	#the second it takes to write it.
	mine = os.environ.get('NUMBERDB_CAMPAIGN', '')
	if prefer is not None:
		for family in open_ones:
			if family['number'] == int(prefer):
				free = unheld(family, mine)
				if free:
					return family, free[0]

	by_age = sorted(open_ones, key=lambda f: (f['screened'] or '', f['number']))
	half_built = [f for f in by_age if started(f)]
	for family in (half_built + [f for f in by_age if f not in half_built]):
		free = unheld(family, mine)
		if free:
			return family, free[0]
	return None


#---------------------------------------------------------------- the commands

def cmd_open(args):
	total = 0
	for family in families():
		left = waiting(family)
		if left:
			total += len(left)
			print('#%-5d %2d left  %s' % (family['number'], len(left),
			                              family['title'][:60]))
	print('%d waiting' % total)
	return 0 if total else 1


def cmd_next(args):
	found = next_table(args.family)
	if found is None:
		print('nothing waiting')
		return 1
	family, item = found
	print(json.dumps({'family': family['number'], 'title': item['title'],
	                  'batch': family['batch'],
	                  'screened': family['screened'],
	                  'waiting': len(waiting(family))}))
	return 0


def cmd_show(args):
	issue = api('repos/%s/issues/%d' % (REPO, args.number))
	print('#%d %s\n' % (issue['number'], issue['title']))
	print(issue.get('body') or '')
	return 0


def cmd_post(args):
	with open(args.batch, encoding='utf-8') as handle:
		text = handle.read()
	batch = parse_batch(text, args.batch)
	if not batch['proposals']:
		print('%s: no `## 1. Title` proposals in it' % args.batch,
		      file=sys.stderr)
		return 2
	done = []
	if args.built:
		#At backfill a table may already exist for a proposal, and the tick
		#has to be inferred by title. At run time it never is: the build knows
		#the T-number it just created.
		for pair in args.built:
			title, _, tid = pair.rpartition('=')
			done.append((title, tid))
	for family in families(state='all'):
		if family['batch'] == batch['batch']:
			print('#%d is already that family' % family['number'])
			return 0
	body = issue_body(batch, done)
	if args.dry_run:
		print(body)
		return 0
	issue = api('repos/%s/issues' % REPO, 'POST',
	            {'title': 'Family: %s' % _short(batch['subject']),
	             'body': body, 'labels': [LABEL]})
	print('#%d %s' % (issue['number'], issue['html_url']))
	return 0


def _tid_in(tail):
	"""The T-number a checklist tail *names*, plainly or as a link.

	Anchored at the start, because a skip reason mentions tables too --
	`skipped: the corpus holds this as T187 under another name` -- and a
	search anywhere in the tail read that proposal as built, as T187.
	"""
	found = re.match(r'\[?(T\d+)\]?(?:\(|$|\s)', (tail or '').strip())
	return found.group(1) if found else None


def _tick(family, title, tid, why=None):
	"""The checklist with one more box settled, or None if nothing matched."""
	lines = []
	hit = False
	for line in family['body'].splitlines():
		found = ITEM.match(line)
		if found and not hit and found.group(1) in (' ', '~'):
			#Titles drift between the proposal and the table -- "Values of the
			#digamma function at rational numbers" was proposed and built as
			#"Values of the digamma function $\\psi(x)$ at rational numbers" --
			#so an exact match cannot be required. The words that carry the
			#subject have to agree; the decoration does not.
			if _same_subject(found.group(2), title):
				#The request this proposal answers is kept on the line: it is
				#how a reader of the family sees who asked, and how the build
				#knows which issue to close.
				asked = (' (answers %s)' % found.group(3)
				         if found.group(3) else '')
				if why:
					line = '- [-] %s%s -- skipped: %s' % (
						found.group(2).strip(), asked, why)
				else:
					#A link, not a bare number: the family issue is where
					#somebody looks to see what became of a batch, and four
					#hops to find out where T226 lives is three too many.
					line = '- [x] %s%s -- [%s](%s/%s)' % (
						found.group(2).strip(), asked, tid, SITE, tid)
				hit = True
		lines.append(line)
	return '\n'.join(lines) if hit else None


STOP = set('of the at and in a an with to for by as its from on'.split())


def _words(text):
	text = re.sub(r'\$[^$]*\$', ' ', text)
	#Every dash is a separator, not a letter. The batches write
	#`Euler–Lehmer` with an en-dash and the tables that answer them write
	#`Euler-Lehmer` with a hyphen, so one side had a single token and the
	#other two and the titles did not match at all. Splitting both ways makes
	#them the same two words -- and two words are more to match on than one.
	text = re.sub(r'[\u2010-\u2015-]', ' ', text)
	return {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z']+", text)
	        if w.lower() not in STOP and len(w) > 2}


def _same_subject(one, other):
	r"""Do two titles name the same table?

	One title wholly inside the other, and nothing else. Not "most words in
	common": two tables that differ in the single word that matters score
	exactly one half -- `Ehrhart polynomials of the permutohedra` against
	`Ehrhart polynomials of the hypersimplices` -- and a sweep run on that
	rule ticked the permutohedra off as built when it was the hypersimplices
	that existed.

	Containment is what the real cases need. A proposal's heading carries its
	own commentary (`Volumes of the Birkhoff polytopes. Rank last; the case
	against is real`), and a built table carries notation the proposal did not
	(`Values of the digamma function $\psi(x)$ at rational numbers`); the
	words of the shorter are in the longer either way, and a word that
	distinguishes -- permutohedra, hypersimplices, zeros, values -- is a word
	the other does not have.
	"""
	first, second = _words(one), _words(other)
	if not first or not second:
		return False
	if first == second and len(first) >= 2:
		return True
	#Three words, not two. A two-word title is contained in half the corpus:
	#`Golden ratio` sits inside `Pisot numbers less than the golden ratio`,
	#and `Rational numbers` inside `Values of the polygamma functions at
	#rational numbers`, neither of which is the same table. A short title
	#that cannot be matched this way is one a person ticks by hand, which is
	#the safe direction to fail in.
	smaller, larger = sorted((first, second), key=len)
	return len(smaller) >= 3 and smaller <= larger


def cmd_built(args):
	issue = api('repos/%s/issues/%d' % (REPO, args.number))
	family = parse_family(issue)
	if family is None:
		print('#%d is not a family' % args.number, file=sys.stderr)
		return 2
	body = _tick(family, args.title, args.tid, getattr(args, 'why', None))
	if body is None:
		print('#%d has no unbuilt table like %r' % (args.number, args.title),
		      file=sys.stderr)
		return 1
	api('repos/%s/issues/%d' % (REPO, args.number), 'PATCH', {'body': body})
	family = parse_family(api('repos/%s/issues/%d' % (REPO, args.number)))
	if getattr(args, 'why', None):
		print('#%d: %s left alone (%s)' % (args.number, args.title, args.why))
	else:
		print('#%d: %s is %s' % (args.number, args.tid, args.title))
		for asked in _answered(family, args.title):
			answer_request(asked, args.tid, args.number)
	if not waiting(family):
		#With the list, so the issue closes as a page somebody can read: what
		#was proposed, what it became, and which request it answered.
		lines = ['Every table in this family now exists. '
		         'Closing; the tables are the record.', '']
		for item in family['items']:
			if item.get('tid'):
				answered = (' (asked for in %s)'
				            % ', '.join('#%d' % n for n in item['answers'])
				            if item.get('answers') else '')
				lines.append('- [%s](%s/%s) -- %s%s'
				             % (item['tid'], SITE, item['tid'],
				                item['title'], answered))
			elif item.get('done'):
				lines.append('- %s -- %s' % (item['title'],
				                             item.get('why') or 'settled'))
		api('repos/%s/issues/%d/comments' % (REPO, args.number), 'POST',
		    {'body': '\n'.join(lines)})
		api('repos/%s/issues/%d' % (REPO, args.number), 'PATCH',
		    {'state': 'closed'})
		print('#%d closed; the family is built' % args.number)
	return 0


def _answered(family, title):
	"""The requests the proposal just built was answering."""
	for item in family['items']:
		if _same_subject(item['title'], title):
			return item.get('answers') or []
	return []


def answer_request(number, tid, family_number=None):
	"""Tell whoever asked that the table exists, and close their issue.

	The backlog is unusable while this does not happen. 81 `table wanted`
	issues were open when this was written and 17 of them already had their
	table -- Shapiro polynomials had been built three days earlier as T319 and
	#110 was still open -- so the count said nothing about what was left, and
	a later screening could pay to propose a table the corpus already had.
	"""
	site = os.environ.get('NUMBERDB_HOST', 'https://numberdb.org')
	body = ['This is now %s/%s.' % (site.rstrip('/'), tid)]
	if family_number:
		body.append('')
		body.append('Built from the screened family #%d.' % (family_number,))
	body.append('')
	body.append('Closing: the table is the record, and anything left to say '
	            'about it belongs on the table rather than here.')
	api('repos/%s/issues/%d/comments' % (REPO, number), 'POST',
	    {'body': '\n'.join(body)})
	api('repos/%s/issues/%d' % (REPO, number), 'PATCH', {'state': 'closed'})
	print('  #%d answered by %s; closed' % (number, tid))


#: Whether the site answered the last time it was asked. None until it has
#: been tried; False stops the rest of this process asking again, because a
#: campaign that waits ten seconds per family for a site that is down is
#: slower than having no lock at all.
_SITE_IS_THERE = None

#: Where the site is, and the key that may claim on it.
SITE = os.environ.get('NUMBERDB_HOST', 'https://numberdb.org').rstrip('/')
KEY_FILE = os.environ.get('NUMBERDB_KEY',
                          os.path.expanduser('~/.config/numberdb/zeta3-key'))


def _site(path, method='GET', payload=None):
	"""One request to numberdb.org, or None if it could not be made.

	Small and dependency-free on purpose: this module runs on build machines
	that carry no client library, and the only thing it needs from the site is
	the claim endpoint.
	"""
	import urllib.error
	import urllib.request

	data = json.dumps(payload).encode() if payload is not None else None
	request = urllib.request.Request(SITE + path, data=data, method=method)
	request.add_header('Content-Type', 'application/json')
	try:
		with open(KEY_FILE) as handle:
			token = handle.read().strip()
		if token:
			request.add_header('Authorization', 'Bearer %s' % (token,))
	except OSError:
		pass
	proxy = os.environ.get('ALL_PROXY') or ''
	if proxy:
		#The laptop reaches the site only through a tunnel; a build machine
		#does not and must not try.
		pass
	global _SITE_IS_THERE
	if _SITE_IS_THERE is False:
		#Asked once and it was not. A queue that waits thirty seconds per
		#family for a site that is down is slower than no lock at all.
		return None, None
	try:
		with urllib.request.urlopen(request, timeout=10) as answer:
			_SITE_IS_THERE = True
			return answer.status, json.loads(answer.read() or b'null')
	except urllib.error.HTTPError as refused:
		try:
			return refused.code, json.loads(refused.read() or b'null')
		except ValueError:
			return refused.code, None
	except Exception:                                    # noqa: BLE001
		_SITE_IS_THERE = False
		return None, None


def held_by_others(family_number, mine=''):
	"""Proposals of this family that somebody else is holding, by title."""
	status, answer = _site('/api/claim?family=%d' % (family_number,))
	if status != 200 or not isinstance(answer, dict):
		return set()
	return {row['proposal'] for row in answer.get('claims') or []
	        if not mine or row.get('worker') != mine}


def take(family_number, title, worker=''):
	"""Claim a proposal on the site. True if it is ours.

	The site is the lock: `(family, proposal)` is unique there, so exactly one
	worker's insert succeeds and the rest are told who holds it. The checklist
	mark below is written afterwards for whoever reads the issue -- it is a
	trace, not the decision, because rewriting an issue body is a read, an
	edit and a write, and two workers doing that in the same second lose one
	another's edit. Every proposal of #178 was claimed that way in one minute
	and none was built.
	"""
	status, answer = _site('/api/claim', 'POST',
	                       {'family': family_number, 'proposal': title,
	                        'worker': worker})
	if status == 201:
		return True
	if status == 409:
		return False
	#The site could not be asked. Refusing to work because the lock is
	#unreachable would stop the campaign for an outage; the duplicate-title
	#refusal still stands behind us, so this falls through to the checklist
	#and carries on.
	return status is None


def give_back(family_number, title):
	"""Release a claim on the site."""
	_site('/api/claim', 'DELETE',
	      {'family': family_number, 'proposal': title})


def claim(family, title, worker=''):
	"""Mark a proposal as being built, so another worker takes a different one.

	`- [~] Title -- claimed by <worker>`. The parser has always read `~` as
	settled, so a claimed proposal drops out of `waiting()` at once and
	`next_table()` hands the next worker something else. Nothing else changes:
	the box is ticked properly when the table exists.

	Claiming is what makes more than one worker possible. Without it two
	workers read the same checklist, pick the same first unbuilt title, and
	spend fifteen minutes each discovering that the other has taken the draft
	-- the site refuses the second title, which is safe and wasteful.

	Not a lock. A claim that is never settled leaves `- [~]` behind, and
	`release` clears it; a campaign that dies mid-build leaves one for a
	person to look at, which is the right amount of ceremony for a checklist
	in an issue.
	"""
	lines, hit = [], False
	for line in family['body'].splitlines():
		found = ITEM.match(line)
		stale = found and found.group(1) == '~' and stale_claim(
			{'claimed': (found.group(4) or '')})
		if found and not hit and (found.group(1) == ' ' or stale) \
				and _same_subject(found.group(2), title):
			asked = (' (answers %s)' % found.group(3)
			         if found.group(3) else '')
			line = '- [~] %s%s -- claimed%s at %s' % (
				found.group(2).strip(), asked,
				' by %s' % worker if worker else '',
				datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%MZ'))
			hit = True
		lines.append(line)
	return '\n'.join(lines) if hit else None


def release(family, title):
	"""Give a claimed proposal back, unbuilt."""
	lines, hit = [], False
	for line in family['body'].splitlines():
		found = ITEM.match(line)
		if found and not hit and found.group(1) == '~' \
				and _same_subject(found.group(2), title):
			asked = (' (answers %s)' % found.group(3)
			         if found.group(3) else '')
			line = '- [ ] %s%s' % (found.group(2).strip(), asked)
			hit = True
		lines.append(line)
	return '\n'.join(lines) if hit else None


def cmd_claim(args):
	if not take(args.number, args.title, getattr(args, 'worker', '')):
		print('#%d: %s is held by another worker' % (args.number, args.title),
		      file=sys.stderr)
		return 1
	issue = api('repos/%s/issues/%d' % (REPO, args.number))
	family = parse_family(issue)
	if family is None:
		print('#%d is not a family' % args.number, file=sys.stderr)
		return 2
	body = claim(family, args.title, getattr(args, 'worker', ''))
	if body is None:
		print('#%d has no unclaimed table like %r'
		      % (args.number, args.title), file=sys.stderr)
		return 1
	api('repos/%s/issues/%d' % (REPO, args.number), 'PATCH', {'body': body})
	print('#%d: %s claimed%s' % (args.number, args.title,
	                             ' by %s' % args.worker if args.worker else ''))
	return 0


def cmd_release(args):
	give_back(args.number, args.title)
	issue = api('repos/%s/issues/%d' % (REPO, args.number))
	family = parse_family(issue)
	if family is None:
		print('#%d is not a family' % args.number, file=sys.stderr)
		return 2
	body = release(family, args.title)
	if body is None:
		print('#%d has nothing claimed like %r' % (args.number, args.title),
		      file=sys.stderr)
		return 1
	api('repos/%s/issues/%d' % (REPO, args.number), 'PATCH', {'body': body})
	print('#%d: %s released' % (args.number, args.title))
	return 0


def cmd_answered(args):
	"""Close a request by hand, for a table that answered it long ago."""
	answer_request(args.number, args.tid)
	return 0


def cmd_stale(args):
	cutoff = (datetime.date.today()
	          - datetime.timedelta(weeks=args.weeks)).isoformat()
	late = [f for f in families() if waiting(f) and (f['screened'] or '') < cutoff]
	for family in late:
		print('#%-5d screened %s  %d left  %s'
		      % (family['number'], family['screened'], len(waiting(family)),
		         family['title'][:52]))
	return 0 if late else 1


def main(argv=None):
	parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
	sub = parser.add_subparsers(dest='command')

	sub.add_parser('open').set_defaults(run=cmd_open)

	after = sub.add_parser('next')
	after.add_argument('--family', default=None,
	                   help='stay in this family if it has work left')
	after.set_defaults(run=cmd_next)

	show = sub.add_parser('show')
	show.add_argument('number', type=int)
	show.set_defaults(run=cmd_show)

	post = sub.add_parser('post')
	post.add_argument('batch')
	post.add_argument('--built', action='append', metavar='TITLE=TID',
	                  help='tick this one at creation (backfill only)')
	post.add_argument('--dry-run', action='store_true')
	post.set_defaults(run=cmd_post)

	built = sub.add_parser('built')
	built.add_argument('number', type=int)
	built.add_argument('title')
	built.add_argument('tid')
	built.set_defaults(run=cmd_built, why=None)

	#Settled without a table, and on purpose. Without this a proposal declined
	#for a good reason looks exactly like one nobody has reached yet.
	skipped = sub.add_parser('skipped')
	skipped.add_argument('number', type=int)
	skipped.add_argument('title')
	skipped.add_argument('why')
	skipped.set_defaults(run=cmd_built, tid=None)

	claiming = sub.add_parser('claim')
	claiming.add_argument('number', type=int)
	claiming.add_argument('title')
	claiming.add_argument('--worker', default='')
	claiming.set_defaults(run=cmd_claim)

	releasing = sub.add_parser('release')
	releasing.add_argument('number', type=int)
	releasing.add_argument('title')
	releasing.set_defaults(run=cmd_release)

	answered = sub.add_parser('answered')
	answered.add_argument('number', type=int, help='the table wanted issue')
	answered.add_argument('tid', help='the table that answers it')
	answered.set_defaults(run=cmd_answered)

	stale = sub.add_parser('stale')
	stale.add_argument('--weeks', type=int, default=STALE_WEEKS)
	stale.set_defaults(run=cmd_stale)

	args = parser.parse_args(argv)
	if not getattr(args, 'run', None):
		parser.print_help()
		return 2
	return args.run(args)


if __name__ == '__main__':
	sys.exit(main())
