"""What to do next: build a table, or improve one that exists.

    python3 agents/work.py next            the next item, as JSON
    python3 agents/work.py next --kind demand|proposal|growth|sweep
    python3 agents/work.py demand 155      write one issue out as a critique
    python3 agents/work.py counts          how much of each kind is waiting

There is one pipeline, not four. Every kind of work ends in the same two
steps -- *a list of claims about one table*, then *an agent that checks each
claim and acts on it* -- which is what `agents/table-critique` and
`agents/table-repair` already are. The repair prompt says so itself: "the
report is a set of proposals, not a set of instructions". It does not care who
wrote the list.

So what differs between kinds of work is only where the list comes from:

    proposal   a screened family in the queue        -> build a new table
    demand     an `enhancement` issue, or a sentence -> critique file, repair
    growth     a table small for its subject         -> ask, then grow it
    sweep      a table nobody has ever read          -> critique, repair

`growth` and `sweep` exist because nobody files an issue for them. Of 293
tables, 88 had ever been through the critique stage and the lowest was T127 --
so every table made by hand, all 126 of them, had never been read by this
machinery. And the recent tables are small: the corpus median is 250 entries
and 44 KB, while the median since T240 is 87 entries and 19 KB, with 30 of 54
using less than a tenth of both soft limits. Neither fact will ever arrive as
a request; both are work.

The order is: a person's demand first, because somebody is waiting; then
proposals and reviews in turn, so a campaign does some of each rather than
spending itself entirely on new tables. `NUMBERDB_REVIEW_EVERY=3` makes it one
review in three; 1 makes every item a review; 0 turns reviewing off.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import queue as proposals  # noqa: E402  (the proposal queue, same directory)

#: The corpus's shape, refreshed by `scripts/review-queue.sh`.
SHAPE = os.path.join(HERE, 'review-queue.tsv')

#: Where a critique lands, and therefore how we know a table has been read.
#
# **Shared between workers, or it is not a memory at all.** Each worker has
# its own worktree, so this was four separate directories and each worker only
# knew what *it* had asked: 352 growth questions were put to about 115 tables,
# T293 was asked twelve times, and a campaign of 200 items spent most of itself
# re-asking questions another worker had already answered. Point every worker
# at one directory with NUMBERDB_CRITIQUES and "at most once per table" means
# what it says.
CRITIQUES = os.environ.get('NUMBERDB_CRITIQUES') or os.path.join(HERE,
                                                                'critiques')

#: A table under a tenth of both soft limits is small enough to ask about.
#: Not "small": the limits are 1200 entries and 320 KB, and a tenth of both is
#: the point at which a table is unlikely to be finished rather than merely
#: short. Some are finished anyway -- a named constant has one entry and is
#: complete -- which is why this asks rather than grows.
ROOM_ENTRIES, ROOM_BYTES = 120, 32 * 1024

#: One review in this many items. A campaign that only builds never returns to
#: what it built.
REVIEW_EVERY = int(os.environ.get('NUMBERDB_REVIEW_EVERY', '2'))


def shape():
	"""Every table, as (tid, entries, bytes, title)."""
	rows = []
	if not os.path.exists(SHAPE):
		return rows
	with io.open(SHAPE, encoding='utf-8') as handle:
		for line in handle:
			parts = line.rstrip('\n').split('\t')
			if len(parts) == 4 and re.match(r'^T\d+$', parts[0]):
				rows.append((parts[0], int(parts[1]), int(parts[2]), parts[3]))
	return rows


def _critique(tid, suffix=''):
	return os.path.join(CRITIQUES, '%s%s.md' % (tid, suffix))


def read(tid, suffix=''):
	"""Has this table been asked this question before?"""
	return os.path.exists(_critique(tid, suffix))


#---------------------------------------------------------------- the kinds

def demands():
	"""Open `enhancement` issues that name a table, and have not been acted on.

	**Once each.** Growth asks its question once (`<tid>-growth.md`) and a
	sweep reads a table once (`<tid>.md`); a demand had no such mark, so
	`pick()` -- which puts a person's demand before everything else -- handed
	the same issue back every time round the loop. A hundred-table campaign
	spent $58 repairing T293 twenty-six times and built nothing.

	The mark is the repair's own report, `<tid>-repaired.md`: written by the
	stage that acted on the demand, and the same file a person would read to
	see what was done. The issue stays open until somebody is satisfied, which
	is a person's judgement and not this loop's.
	"""
	found = []
	try:
		issues = proposals.api(
			'repos/%s/issues?labels=enhancement&state=open&per_page=100'
			% proposals.REPO) or []
	except SystemExit:
		return found
	for issue in issues:
		if 'pull_request' in issue:
			continue
		text = '%s\n%s' % (issue.get('title') or '', issue.get('body') or '')
		tids = re.findall(r'\bT(\d{1,4})\b', text)
		if not tids:
			continue
		#The first T-number in the title, or failing that in the body: an
		#issue about T293 may mention T137 in passing, and the one it is
		#*about* is the one it leads with.
		tid = 'T%s' % tids[0]
		if read(tid, '-repaired'):
			continue
		found.append({'kind': 'demand', 'issue': issue['number'],
		              'tid': tid, 'title': issue['title'],
		              'body': issue.get('body') or ''})
	return found


def growth():
	"""Tables small for their subject that have not been asked about it."""
	waiting = []
	for tid, entries, size, title in shape():
		if entries < ROOM_ENTRIES and size < ROOM_BYTES \
				and not read(tid, '-growth'):
			waiting.append({'kind': 'growth', 'tid': tid, 'title': title,
			                'entries': entries, 'bytes': size})
	#Newest first: a table built last week is the one whose generator is still
	#understood, and the one whose range was most likely chosen in a hurry.
	waiting.sort(key=lambda w: -int(w['tid'][1:]))
	return waiting


def sweep():
	"""Tables nobody has ever read."""
	waiting = [{'kind': 'sweep', 'tid': tid, 'title': title,
	            'entries': entries, 'bytes': size}
	           for tid, entries, size, title in shape() if not read(tid)]
	#Oldest first: these are the hand-made tables, and they have waited
	#longest.
	waiting.sort(key=lambda w: int(w['tid'][1:]))
	return waiting


def proposal():
	"""The next table to build, from the screened queue."""
	found = proposals.next_table(os.environ.get('NUMBERDB_FAMILY') or None)
	if found is None:
		return None
	family, item = found
	return {'kind': 'proposal', 'family': family['number'],
	        'title': item['title'], 'batch': family['batch'],
	        'screened': family['screened'],
	        'waiting': len(proposals.waiting(family))}


#---------------------------------------------------------------- choosing

def pick(done=0, kind=None):
	"""The next item of work.

	`done` is how many items this campaign has finished, which is all the
	state the alternation needs.
	"""
	if kind:
		chosen = {'demand': lambda: (demands() or [None])[0],
		          'growth': lambda: (growth() or [None])[0],
		          'sweep': lambda: (sweep() or [None])[0],
		          'proposal': proposal}[kind]()
		return chosen

	waiting = demands()
	if waiting:
		return waiting[0]

	reviewing = REVIEW_EVERY and (done % REVIEW_EVERY == REVIEW_EVERY - 1)
	order = ([growth, sweep, proposal] if reviewing
	         else [proposal, growth, sweep])
	for source in order:
		item = source()
		if isinstance(item, list):
			item = item[0] if item else None
		if item:
			return item
	return None


#---------------------------------------------------------------- a demand becomes a critique

HEADER = """# %(tid)s: %(what)s

*Written by %(who)s, not by a critique run.* %(why)s

"""


def write_demand(item):
	"""Put a demand where `repair` looks for its findings.

	With its provenance, because the difference matters to whoever acts on it:
	a person is authoritative about **what is wanted** and not about **what is
	true**. "Make this table longer" is an instruction; "there are no curves
	for D=5" is a claim to be checked like any other.
	"""
	os.makedirs(CRITIQUES, exist_ok=True)
	path = _critique(item['tid'])
	if item['kind'] == 'demand':
		who = 'a person, in numberdb-data#%d' % item['issue']
		why = ('What it asks for is wanted. What it asserts is a claim: check '
		       'each one against the live table before acting on it, and say '
		       'so in your report if it turns out to be wrong.')
		body = item['body']
	else:
		who = 'the reviewing loop'
		why = 'It is a question, not a finding.'
		body = item.get('question', '')
	with io.open(path, 'w', encoding='utf-8') as handle:
		handle.write(HEADER % {'tid': item['tid'], 'what': item['title'],
		                       'who': who, 'why': why})
		handle.write(body.rstrip() + '\n')
	return path


#---------------------------------------------------------------- commands

def cmd_next(args):
	item = pick(done=args.done, kind=args.kind)
	if item is None:
		print('nothing waiting', file=sys.stderr)
		return 1
	if item['kind'] == 'demand':
		item['critique'] = write_demand(item)
	print(json.dumps(item))
	return 0


def cmd_demand(args):
	issue = proposals.api('repos/%s/issues/%d' % (proposals.REPO, args.number))
	text = '%s\n%s' % (issue.get('title') or '', issue.get('body') or '')
	tids = re.findall(r'\bT(\d{1,4})\b', text)
	if not tids:
		print('#%d names no table' % args.number, file=sys.stderr)
		return 2
	print(write_demand({'kind': 'demand', 'issue': args.number,
	                    'tid': 'T%s' % tids[0], 'title': issue['title'],
	                    'body': issue.get('body') or ''}))
	return 0


def cmd_counts(args):
	print('demands   %d' % len(demands()))
	print('proposals %s' % ('some' if proposal() else 0))
	print('growth    %d' % len(growth()))
	print('sweep     %d' % len(sweep()))
	return 0


def main(argv=None):
	parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
	sub = parser.add_subparsers(dest='command')

	after = sub.add_parser('next')
	after.add_argument('--done', type=int, default=0,
	                   help='items finished so far, for the alternation')
	after.add_argument('--kind', choices=('demand', 'proposal', 'growth',
	                                      'sweep'))
	after.set_defaults(run=cmd_next)

	demand = sub.add_parser('demand')
	demand.add_argument('number', type=int)
	demand.set_defaults(run=cmd_demand)

	sub.add_parser('counts').set_defaults(run=cmd_counts)

	args = parser.parse_args(argv)
	if not getattr(args, 'run', None):
		parser.print_help()
		return 2
	return args.run(args)


if __name__ == '__main__':
	sys.exit(main())
