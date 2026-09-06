"""An arXiv number in the prose is not a link.

    ALL_PROXY=socks5h://127.0.0.1:1080 python3 scripts/one-off/arxiv-ids-out-of-the-bib.py [apply]

A reference may carry `arxiv:` beside its `bib`, and the page then renders
"(arXiv)" as a link to the abstract -- the mechanism has been there for years
and eighteen references in the older corpus use it. Nine tables built by
agents wrote the identifier into the sentence instead, where it is text:
"..., Journal of Statistical Physics 88 (1997), 567-615, arXiv:hep-lat/9607030."

That is fifty-two references a reader can see the number of and not click.
This moves each identifier into the field and takes it out of the sentence,
because the renderer prints the link itself and leaving it in both places says
it twice.
"""
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(
	os.path.dirname(os.path.abspath(__file__)))))

from agents.api_edit import edit_over_api, use_socks_proxy_if_set

APPLY = 'apply' in sys.argv[1:]
KEY = os.path.expanduser('~/.config/numberdb/bmatschke-key')
TABLES = ('T148', 'T150', 'T151', 'T152', 'T153', 'T154', 'T155', 'T156',
          'T157')

#: Both spellings of an identifier: the old archive/number form, which most of
#: these are, and the modern one. A version suffix is kept off the field --
#: /abs/ resolves to the latest without it.
IDENTIFIER = re.compile(
	r',?\s*arXiv:\s*('
	r'[a-z-]+(?:\.[A-Z]{2})?/\d{7}'
	r'|\d{4}\.\d{4,5}'
	r')(v\d+)?\.?',
	re.IGNORECASE)

use_socks_proxy_if_set()
token = open(KEY, encoding='utf8').read().strip()


def document(tid):
	request = urllib.request.Request(
		'https://numberdb.org/api/table?id=%s' % (tid,),
		headers={'Authorization': 'Bearer %s' % (token,)})
	with urllib.request.urlopen(request, timeout=120) as response:
		return json.loads(response.read().decode('utf8'))


def lift(bib):
	"""(bib without the identifier, the identifier) or (bib, None)."""
	found = IDENTIFIER.search(bib)
	if not found:
		return bib, None
	rest = (bib[:found.start()] + bib[found.end():]).rstrip()
	#The sentence ended at the identifier as often as not, so it needs its
	#full stop back; and a comma left dangling before it is not punctuation.
	rest = rest.rstrip(',').rstrip()
	if rest and not rest.endswith('.'):
		rest += '.'
	return rest, found.group(1)


for tid in TABLES:
	tree = document(tid)
	references = dict(tree.get('References') or {})
	moved = []
	for label, reference in list(references.items()):
		if not isinstance(reference, dict) or 'bib' not in reference:
			continue
		if any(k.lower() == 'arxiv' for k in reference):
			continue
		bib, identifier = lift(str(reference['bib']))
		if identifier is None:
			continue
		#Rebuilt in order, so `arxiv` follows `bib` rather than landing
		#wherever a dict happens to put it.
		updated = {}
		for key, value in reference.items():
			updated[key] = bib if key == 'bib' else value
			if key == 'bib':
				updated['arxiv'] = identifier
		references[label] = updated
		moved.append((label, identifier))
	if not moved:
		print('%s: nothing buried' % (tid,))
		continue
	tree['References'] = references
	print('%s: %d' % (tid, len(moved)))
	for label, identifier in moved:
		print('    %-16s %s' % (label, identifier))
	if APPLY:
		edit_over_api(
			tid, tree,
			('the arXiv number of %d references was in the sentence, where it '
			 'is text; moved to the `arxiv` field, which the page renders as '
			 'a link to the abstract' % (len(moved),)),
			assistant='claude-opus-5', key_file=KEY)
		print('  committed')

if not APPLY:
	print('\ndry run; pass "apply" to send them')
