"""The queue of screened proposals, kept as issues.

    python3 agents/queue.py open                 how many tables are waiting
    python3 agents/queue.py next [--family N]    the next one to build
    python3 agents/queue.py show N               one family, for a build prompt
    python3 agents/queue.py post BATCH.md        a batch becomes a family issue
    python3 agents/queue.py built N "Title" T226 tick the box
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

#: A checklist line: `- [ ] Some table` or `- [x] Some table -- T226`.
ITEM = re.compile(r'^- \[([ xX])\] (.+?)(?:\s+--\s+(T\d+))?\s*$')

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
		lines.append('- [%s] %s%s' % ('x' if tid else ' ', title,
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
			items.append({'title': found.group(2).strip(),
			              'done': found.group(1).lower() == 'x',
			              'tid': found.group(3)})
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


def waiting(family):
	return [item for item in family['items'] if not item['done']]


def next_table(prefer=None):
	"""The next table to build.

	**Finish the family you are in.** The tables of a batch share machinery
	and cross-reference each other, which is most of why the batches have been
	good, and a family left half-built loses that. Only when the current one
	is done does this move to the newest family with work left.
	"""
	open_ones = [f for f in families() if waiting(f)]
	if not open_ones:
		return None
	if prefer is not None:
		for family in open_ones:
			if family['number'] == int(prefer):
				return family, waiting(family)[0]
	return open_ones[0], waiting(open_ones[0])[0]


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


def _tick(family, title, tid):
	"""The checklist with one more box ticked, or None if nothing matched."""
	lines = []
	hit = False
	for line in family['body'].splitlines():
		found = ITEM.match(line)
		if found and not hit and found.group(1) == ' ':
			#Titles drift between the proposal and the table -- "Values of the
			#digamma function at rational numbers" was proposed and built as
			#"Values of the digamma function $\\psi(x)$ at rational numbers" --
			#so an exact match cannot be required. The words that carry the
			#subject have to agree; the decoration does not.
			if _same_subject(found.group(2), title):
				line = '- [x] %s -- %s' % (found.group(2).strip(), tid)
				hit = True
		lines.append(line)
	return '\n'.join(lines) if hit else None


STOP = set('of the at and in a an with to for by as its from on'.split())


def _words(text):
	text = re.sub(r'\$[^$]*\$', ' ', text)
	return {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z'-]+", text)
	        if w.lower() not in STOP and len(w) > 2}


def _same_subject(one, other, enough=0.5):
	first, second = _words(one), _words(other)
	if not first or not second:
		return False
	return len(first & second) / float(len(first | second)) >= enough


def cmd_built(args):
	issue = api('repos/%s/issues/%d' % (REPO, args.number))
	family = parse_family(issue)
	if family is None:
		print('#%d is not a family' % args.number, file=sys.stderr)
		return 2
	body = _tick(family, args.title, args.tid)
	if body is None:
		print('#%d has no unbuilt table like %r' % (args.number, args.title),
		      file=sys.stderr)
		return 1
	api('repos/%s/issues/%d' % (REPO, args.number), 'PATCH', {'body': body})
	family = parse_family(api('repos/%s/issues/%d' % (REPO, args.number)))
	print('#%d: %s is %s' % (args.number, args.tid, args.title))
	if not waiting(family):
		api('repos/%s/issues/%d/comments' % (REPO, args.number), 'POST',
		    {'body': 'Every table in this family now exists. '
		             'Closing; the tables are the record.'})
		api('repos/%s/issues/%d' % (REPO, args.number), 'PATCH',
		    {'state': 'closed'})
		print('#%d closed; the family is built' % args.number)
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
	built.set_defaults(run=cmd_built)

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
