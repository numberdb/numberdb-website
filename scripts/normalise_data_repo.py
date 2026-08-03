#!/usr/bin/env python3
"""Report, and optionally make, the schema normalisations in numberdb-data.

    scripts/normalise_data_repo.py                 # report only
    scripts/normalise_data_repo.py --write         # edit the files
    scripts/normalise_data_repo.py --write --only complete

Three changes, none of which alters what any table means:

  * `Data:` becomes `Numbers:`. One concept under two names, and every reader
    already accepts either, so this is about not having to explain it.
  * `arxiv:` becomes `arXiv:` and `mr:` becomes `MR:`. The renderer matches
    these case-insensitively now, so nothing is broken either way.
  * `complete: yes, assuming GRH` becomes `complete: yes` plus
    `complete-note: assuming GRH`, and likewise for `unknown (presumably not)`.
    The field is otherwise already `yes | no | unknown`; these two append a
    qualifier into the value, which no dropdown can represent.

Edits are made textually rather than by loading and re-dumping the YAML. A
round trip through a parser would rewrite all 109 files: it reorders nothing
but reflows block scalars, drops comments, and renormalises quoting, turning an
eighteen-file change into a diff nobody can review. Here the untouched lines
stay byte-identical.
"""

import argparse
import os
import re
import sys

#Only these keys are rewritten, and only where they begin a line at the
#indentation the corpus actually uses. A bare search-and-replace would also hit
#the word inside a bibliography entry or a comment.
REFERENCE_KEYS = {'arxiv': 'arXiv', 'mr': 'MR'}

#Split into (value, note). Anything not listed is already fine.
COMPLETE_SPLITS = {
	'yes, assuming GRH': ('yes', 'assuming GRH'),
	'unknown (presumably not)': ('unknown', 'presumably not'),
}


def find_tables(root):
	for dirpath, _, filenames in os.walk(root):
		if 'table.yaml' in filenames:
			yield os.path.join(dirpath, 'table.yaml')


def normalise(text):
	"""Return (new_text, [descriptions of what changed])."""
	changes = []
	lines = text.split('\n')

	for i, line in enumerate(lines):
		#`Data:` at column zero is the data-carrying key. Indented, it is
		#something else entirely, such as `Data properties:`.
		if re.match(r'^Data:\s*(#.*)?$', line) or re.match(r'^Data:\s+\S', line):
			lines[i] = line.replace('Data:', 'Numbers:', 1)
			changes.append('Data: -> Numbers:')
			continue

		m = re.match(r'^(\s+)([A-Za-z]+):(\s.*)$', line)
		if m and m.group(2).lower() in REFERENCE_KEYS:
			canonical = REFERENCE_KEYS[m.group(2).lower()]
			if m.group(2) != canonical:
				lines[i] = '%s%s:%s' % (m.group(1), canonical, m.group(3))
				changes.append('%s: -> %s:' % (m.group(2), canonical))
			continue

		m = re.match(r'^(\s+)complete:\s*(.+?)\s*$', line)
		if m and m.group(2) in COMPLETE_SPLITS:
			value, note = COMPLETE_SPLITS[m.group(2)]
			indent = m.group(1)
			lines[i] = '%scomplete: %s' % (indent, value)
			lines.insert(i + 1, '%scomplete-note: %s' % (indent, note))
			changes.append('complete: %r -> %r + note %r'
			               % (m.group(2), value, note))

	return '\n'.join(lines), changes


def main():
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument('--root', default='../numberdb-data/data')
	parser.add_argument('--write', action='store_true',
	                    help='edit the files; without it, nothing is written')
	parser.add_argument('--only', choices=['data-key', 'references', 'complete'],
	                    help='restrict to one kind of change')
	args = parser.parse_args()

	if not os.path.isdir(args.root):
		print('No such directory: %s' % (args.root,), file=sys.stderr)
		return 2

	touched = 0
	total = 0
	for path in sorted(find_tables(args.root)):
		original = open(path, encoding='utf8').read()
		new, changes = normalise(original)
		if args.only:
			wanted = {'data-key': 'Numbers:', 'references': '->',
			          'complete': 'complete:'}[args.only]
			changes = [c for c in changes if wanted in c]
			if not changes:
				continue
			new, _ = normalise(original)
		if not changes:
			continue
		touched += 1
		total += len(changes)
		print('  %s' % (os.path.relpath(path, args.root),))
		for c in changes:
			print('      %s' % (c,))
		if args.write:
			open(path, 'w', encoding='utf8').write(new)

	print()
	print('  %d change(s) across %d file(s)%s'
	      % (total, touched, '' if args.write else ' -- nothing written'))
	if not args.write and touched:
		print('  Re-run with --write to apply, then review with git diff.')
	return 0


if __name__ == '__main__':
	sys.exit(main())
